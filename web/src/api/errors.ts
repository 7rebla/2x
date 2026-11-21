import { client as defaultClient } from "./generated/client.gen.ts";

/**
 * What went wrong with an API call:
 * - "http": the API answered with a status outside 2xx,
 * - "network": no answer at all (server down, connection lost),
 * - "invalid-answer": a 2xx answer that could not be read (for example an HTML page of a proxy).
 */
export type ApiErrorKind = "http" | "network" | "invalid-answer";

/** Longest plain-text error body shown to the user; longer bodies are cut. */
export const MAX_DETAIL_LENGTH = 500;

/** Error of an API call as thrown by the generated client (and seen by TanStack Query). */
export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  /** HTTP status of the answer, null if there was no answer. */
  readonly status: number | null;
  /** Error text sent by the API (DRF "detail" or a plain-text body), null if there is none. */
  readonly detail: string | null;

  constructor(kind: ApiErrorKind, status: number | null, detail: string | null, options?: ErrorOptions) {
    super(
      status === null ? `API call failed (${kind})` : `API call failed (${kind}, HTTP ${String(status)})`,
      options,
    );
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Turns whatever the generated client caught into an ApiError.
 *
 * `error` is the parsed error body (JSON or text) for a non-2xx answer, or the
 * exception from fetch or from reading the answer. Cancelled requests
 * (AbortError) and errors raised before a request existed stay unchanged, so
 * that TanStack Query still recognises a cancellation.
 */
export function toApiError(
  error: unknown,
  response: Response | undefined,
  request: Request | undefined,
): unknown {
  if (error instanceof ApiError || isAbortError(error)) {
    return error;
  }
  if (response === undefined) {
    return request === undefined ? error : new ApiError("network", null, null, { cause: error });
  }
  if (response.ok) {
    return new ApiError("invalid-answer", response.status, null, { cause: error });
  }
  return new ApiError("http", response.status, errorDetail(error, response));
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

/** DRF puts its message into {"detail": "..."}; other bodies are shown only as plain text. */
function errorDetail(body: unknown, response: Response): string | null {
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail: unknown = body.detail;
    return typeof detail === "string" ? shorten(detail) : null;
  }
  const contentType = response.headers.get("Content-Type") ?? "";
  if (typeof body === "string" && contentType.toLowerCase().startsWith("text/plain")) {
    return shorten(body);
  }
  return null;
}

function shorten(text: string): string | null {
  const trimmed = text.trim();
  if (trimmed === "") {
    return null;
  }
  return trimmed.length > MAX_DETAIL_LENGTH ? `${trimmed.slice(0, MAX_DETAIL_LENGTH)}…` : trimmed;
}

type ApiClient = typeof defaultClient;

const prepared = new WeakSet<ApiClient>();

/**
 * Registers toApiError as error interceptor of the generated client, once per client.
 * Calls without throwOnError keep their result shape ({ error, response }); only the
 * error value becomes an ApiError.
 */
export function installApiErrorHandling(apiClient: ApiClient = defaultClient): void {
  if (prepared.has(apiClient)) {
    return;
  }
  prepared.add(apiClient);
  apiClient.interceptors.error.use((error, response, request) => toApiError(error, response, request));
}
