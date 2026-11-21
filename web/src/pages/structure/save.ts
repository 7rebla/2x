// Saving a form of the structure pages and reading DRF's field errors.
//
// DRF answers an invalid entry with 400 and a body like
//   {"ip_address": ["Enter a valid IPv4 or IPv6 address."], "non_field_errors": ["…"]}
// The shared error handling (api/errors.ts) keeps only the status and a
// "detail" text, so the call is sent with a fetch of its own that keeps a copy
// of a 400 answer; its body is read only when the call failed with 400.
import type { QueryClient } from "@tanstack/react-query";

import { ApiError } from "../../api/errors.ts";
import { sessionQueryKey } from "../../session.ts";

/** Messages of the API per field name; other keys (non_field_errors, detail) concern the whole entry. */
export type FieldErrors = Readonly<Record<string, readonly string[]>>;

function messages(value: unknown): string[] {
  if (typeof value === "string") {
    return value.trim() === "" ? [] : [value];
  }
  if (Array.isArray(value)) {
    return value.flatMap((item) => messages(item));
  }
  if (typeof value === "object" && value !== null) {
    return Object.values(value).flatMap((item) => messages(item));
  }
  return [];
}

/** Reads a DRF error body; anything that is not an object of messages gives no field errors. */
export function parseFieldErrors(body: unknown): FieldErrors {
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    return {};
  }
  const result: Record<string, readonly string[]> = {};
  for (const [field, value] of Object.entries(body)) {
    const list = messages(value);
    if (list.length > 0) {
      result[field] = list;
    }
  }
  return result;
}

export type SaveOutcome<T> =
  | { readonly kind: "saved"; readonly data: T }
  /** 400: the API named what is wrong (possibly nothing readable: then the map is empty). */
  | { readonly kind: "invalid"; readonly fieldErrors: FieldErrors }
  /** Anything else: no permission, no answer, server error … */
  | { readonly kind: "failed"; readonly error: unknown };

/**
 * Sends one write call. `send` must pass the given fetch to the generated
 * client (option `fetch`), so that the body of a 400 answer can be read.
 */
export async function save<T>(send: (fetchFn: typeof fetch) => Promise<T>): Promise<SaveOutcome<T>> {
  const captured: { badRequest: Response | null } = { badRequest: null };
  const capturingFetch: typeof fetch = async (input, init) => {
    // Looked up at call time, like the generated client does (tests replace it).
    const response = await globalThis.fetch(input, init);
    captured.badRequest = response.status === 400 ? response.clone() : null;
    return response;
  };

  try {
    return { kind: "saved", data: await send(capturingFetch) };
  } catch (error) {
    const answer = captured.badRequest;
    if (error instanceof ApiError && error.kind === "http" && error.status === 400 && answer !== null) {
      let body: unknown = null;
      try {
        body = await answer.json();
      } catch {
        // Not JSON: the form shows the general error text.
      }
      return { kind: "invalid", fieldErrors: parseFieldErrors(body) };
    }
    return { kind: "failed", error };
  }
}

/** After saving: every cached answer except the sign-in state is fetched again. */
export async function reloadAfterSave(queryClient: QueryClient): Promise<void> {
  await queryClient.invalidateQueries({ predicate: (query) => query.queryKey[0] !== sessionQueryKey[0] });
}
