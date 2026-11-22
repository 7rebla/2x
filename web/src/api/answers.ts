// Client of the answers (work order 131): POST /api/v1/answers/ as a stream of
// server-sent events, and the query options of GET /api/v1/answers/status/.
//
// The stream uses the generated SDK function `answer()` (`client.sse.post`),
// with these rules:
//
// - Never again on its own: `sseMaxRetryAttempts: 1`. A second request would
//   let the model compute the answer again, and differently. There is no
//   Last-Event-ID either (the server sends no `id:`).
// - Same headers as every other call: the request interceptors of
//   installClientConfig() (X-CSRFToken, Accept-Language) run for the stream
//   too. Its response and error interceptors do not, so the fetch wrapper
//   below reports a 403 to onForbidden and turns a failed answer into an
//   ApiError itself, before the generated code drops the body.
// - Cancelling through `signal` is not an error: the outcome is "aborted".
// - The question travels in the body only, never in the address.
//
// Nothing here logs or stores the question, the answer or a source text.
import {
  type AnswerErrorCode,
  type AnswerEvent,
  type AnswerRefusalCode,
  parseAnswerEvent,
  toAnswerRefusalCode,
} from "../pages/answer/events.ts";
import { reportForbidden } from "./client.ts";
import { ApiError, MAX_DETAIL_LENGTH } from "./errors.ts";
import { answerStatusOptions } from "./generated/@tanstack/react-query.gen.ts";
import { answer } from "./generated/sdk.gen.ts";
import type { AnswerRequest } from "./generated/types.gen.ts";

export type { AnswerRequest };

/** Path of the answer stream (relative: same origin as the page). */
export const ANSWERS_PATH = "/api/v1/answers/";

/** How long the status counts as fresh; the server keeps its own check for 30 s. */
export const ANSWER_STATUS_STALE_MS = 15_000;

/**
 * How a stream ended:
 * - "completed": a `done` event came (it went to `onEvent`),
 * - "stream-error": an `error` event came (it went to `onEvent`); `code` is its code,
 * - "ai-disabled": the AI features are off (409 `ai_disabled` before the stream,
 *   or an `error` event with that code),
 * - "aborted": cancelled through `signal`; no error,
 * - "interrupted": the stream ended without `done` or `error` (connection lost),
 * - "failed": no stream or an unreadable one; `error` says why, `code` is the
 *   `code` of a refusal (409, 503) if the server sent a known one.
 */
export type AnswerStreamOutcome =
  | { kind: "completed" }
  | { kind: "stream-error"; code: Exclude<AnswerErrorCode, "ai_disabled">; detail: string }
  | { kind: "ai-disabled" }
  | { kind: "aborted" }
  | { kind: "interrupted" }
  | { kind: "failed"; error: ApiError; code: AnswerRefusalCode | null };

export interface StreamAnswerOptions {
  /** Cancels the request or the stream; afterwards nothing is fetched again. */
  signal: AbortSignal;
  /** Gets every checked event, in order. Not called after an abort. */
  onEvent: (event: AnswerEvent) => void;
}

/** ApiError of a failed answer, with the `code` of a refusal. */
class RefusedAnswerError extends ApiError {
  readonly code: AnswerRefusalCode | null;

  constructor(status: number, detail: string | null, code: AnswerRefusalCode | null) {
    super("http", status, detail);
    this.code = code;
  }
}

/** By name, not by class: a DOMException of another realm (tests) counts too. */
function isAbortError(error: unknown): boolean {
  return typeof error === "object" && error !== null && "name" in error && error.name === "AbortError";
}

function shorten(text: string): string | null {
  const trimmed = text.trim();
  if (trimmed === "") {
    return null;
  }
  return trimmed.length > MAX_DETAIL_LENGTH ? `${trimmed.slice(0, MAX_DETAIL_LENGTH)}…` : trimmed;
}

/**
 * The ApiError of an answer outside 2xx, by the rules of errors.ts (`toApiError`,
 * `errorDetail`): DRF's `detail`, a body as text only for text/plain, cut to
 * MAX_DETAIL_LENGTH. Rebuilt here because errors.ts keeps those helpers to
 * itself and stays unchanged in this work order; additionally reads `code`.
 */
async function refusedAnswerError(response: Response): Promise<RefusedAnswerError> {
  let text = "";
  try {
    text = await response.text();
  } catch {
    // An unreadable body leaves the status alone.
  }
  let body: unknown = text;
  try {
    body = JSON.parse(text);
  } catch {
    // Not JSON: stays text.
  }
  if (typeof body === "object" && body !== null) {
    const detail: unknown = "detail" in body ? body.detail : null;
    const code: unknown = "code" in body ? body.code : null;
    return new RefusedAnswerError(
      response.status,
      typeof detail === "string" ? shorten(detail) : null,
      toAnswerRefusalCode(code),
    );
  }
  const contentType = (response.headers.get("Content-Type") ?? "").toLowerCase();
  return new RefusedAnswerError(response.status, contentType.startsWith("text/plain") ? shorten(text) : null, null);
}

function isEventStream(response: Response): boolean {
  return (response.headers.get("Content-Type") ?? "").toLowerCase().startsWith("text/event-stream");
}

/**
 * fetch for the SSE client: reports a 403, reads a failed answer before the
 * generated code drops it, and throws ApiError for every failure except a
 * cancellation (that AbortError passes unchanged).
 */
async function answerFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const request = input instanceof Request ? input : new Request(input, init);
  let response: Response;
  try {
    // Looked up at call time, so a test can replace fetch.
    response = await globalThis.fetch(request);
  } catch (error) {
    if (isAbortError(error) || request.signal.aborted) {
      throw error;
    }
    throw new ApiError("network", null, null, { cause: error });
  }
  reportForbidden(response, request);
  if (!response.ok) {
    throw await refusedAnswerError(response);
  }
  if (!isEventStream(response) || response.body === null) {
    await response.body?.cancel().catch(() => undefined);
    throw new ApiError("invalid-answer", response.status, null);
  }
  return response;
}

/** Where an event may come: `sources` first, then `delta`, then `done`; `error` at any time. */
function fitsOrder(event: AnswerEvent, sourcesSeen: boolean): boolean {
  switch (event.type) {
    case "sources":
      return !sourcesSeen;
    case "delta":
    case "done":
      return sourcesSeen;
    case "error":
      return true;
  }
}

/**
 * Asks for the answer to `request` and passes its events to `onEvent`. Sends
 * exactly one request (none if `signal` is already aborted) and never tries
 * again. Resolves with how the stream ended; never rejects for a failure of
 * the API.
 */
export async function streamAnswer(request: AnswerRequest, options: StreamAnswerOptions): Promise<AnswerStreamOutcome> {
  const { signal, onEvent } = options;
  // A function, so the type checker does not keep the first answer for later checks.
  const aborted = (): boolean => signal.aborted;
  if (aborted()) {
    return { kind: "aborted" };
  }
  // Own controller: also stops the connection when this side ends the
  // stream (after `done` or `error`, or after an event that breaks the contract).
  const controller = new AbortController();
  const abort = (): void => {
    controller.abort();
  };
  signal.addEventListener("abort", abort, { once: true });

  let failure: unknown = undefined;
  let terminal: AnswerStreamOutcome | null = null;
  let sourcesSeen = false;
  try {
    const { stream } = await answer({
      body: request,
      signal: controller.signal,
      fetch: answerFetch,
      sseMaxRetryAttempts: 1,
      onSseError: (error) => {
        failure ??= error;
      },
    });
    for await (const data of stream) {
      if (aborted()) {
        break;
      }
      const event = parseAnswerEvent(data);
      if (event === null || !fitsOrder(event, sourcesSeen)) {
        terminal = { kind: "failed", error: new ApiError("invalid-answer", 200, null), code: null };
        break;
      }
      onEvent(event);
      if (event.type === "sources") {
        sourcesSeen = true;
      } else if (event.type === "done") {
        terminal = { kind: "completed" };
        break;
      } else if (event.type === "error") {
        terminal =
          event.code === "ai_disabled"
            ? { kind: "ai-disabled" }
            : { kind: "stream-error", code: event.code, detail: event.detail };
        break;
      }
    }
  } catch (error) {
    failure ??= error;
  } finally {
    signal.removeEventListener("abort", abort);
    // Ends the connection if the loop stopped early; no effect after the end.
    controller.abort();
  }

  if (terminal !== null) {
    return terminal;
  }
  if (aborted()) {
    return { kind: "aborted" };
  }
  if (failure instanceof RefusedAnswerError) {
    // The page gets a plain ApiError, like from every other call.
    return failure.code === "ai_disabled"
      ? { kind: "ai-disabled" }
      : { kind: "failed", error: new ApiError("http", failure.status, failure.detail), code: failure.code };
  }
  if (failure instanceof ApiError) {
    return { kind: "failed", error: failure, code: null };
  }
  // No event that ends the answer: the connection broke off or the server
  // stopped (also when reading the stream failed).
  return { kind: "interrupted" };
}

/**
 * Query options of GET /api/v1/answers/status/: `enabled`, `chat_model_configured`,
 * `available`. The answer page uses them to tell whether it can ask at all.
 */
export function answersStatusQueryOptions(): ReturnType<typeof answerStatusOptions> {
  return { ...answerStatusOptions(), staleTime: ANSWER_STATUS_STALE_MS };
}
