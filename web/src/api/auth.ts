// Small typed wrapper around the browser API of django-allauth (headless).
//
// allauth is not part of the OpenAPI schema, so these calls do not go through
// the generated client. They send the same headers (CSRF token, language) via
// addApiHeaders. Endpoints (allauth 65.22, client "browser"):
//   POST   /_allauth/browser/v1/auth/login    sign in with username and password
//   DELETE /_allauth/browser/v1/auth/session  sign out
import { addApiHeaders } from "./client.ts";

export const AUTH_BASE_PATH = "/_allauth/browser/v1";
export const LOGIN_PATH = `${AUTH_BASE_PATH}/auth/login`;
export const SESSION_PATH = `${AUTH_BASE_PATH}/auth/session`;

/**
 * Outcome of a sign-in attempt:
 * - "signed-in": the session cookie is set (also when allauth reports 409, already signed in),
 * - "wrong-credentials": unknown username or wrong password (400),
 * - "locked": too many failed attempts for this account (400, too_many_login_attempts),
 * - "rate-limited": too many sign-in attempts from this address (429),
 * - "invalid": another 400, for example an empty field,
 * - "expired-page": the CSRF check failed (403), the page has to be reloaded,
 * - "http-error": any other status,
 * - "network": no answer at all.
 */
export type SignInResult =
  | { kind: "signed-in" }
  | { kind: "wrong-credentials" }
  | { kind: "locked" }
  | { kind: "rate-limited" }
  | { kind: "invalid" }
  | { kind: "expired-page" }
  | { kind: "http-error"; status: number }
  | { kind: "network" };

/** Outcome of a sign-out: done, or why not. */
export type SignOutResult = { kind: "signed-out" } | { kind: "http-error"; status: number } | { kind: "network" };

/** Error codes of allauth that the sign-in page tells apart. */
export const LOCKED_CODE = "too_many_login_attempts";
export const WRONG_CREDENTIALS_CODE = "username_password_mismatch";

async function send(path: string, method: string, body?: unknown): Promise<Response> {
  const headers = new Headers({ Accept: "application/json" });
  if (body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  addApiHeaders(headers, method);
  const request = new Request(new URL(path, window.location.href), {
    method,
    headers,
    body: body === undefined ? null : JSON.stringify(body),
    credentials: "same-origin",
  });
  return fetch(request);
}

/** The error codes of an allauth error answer ({"errors": [{"code": …}]}); empty if unreadable. */
export async function errorCodes(response: Response): Promise<string[]> {
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return [];
  }
  if (typeof body !== "object" || body === null || !("errors" in body) || !Array.isArray(body.errors)) {
    return [];
  }
  const codes: string[] = [];
  for (const error of body.errors as unknown[]) {
    if (typeof error === "object" && error !== null && "code" in error && typeof error.code === "string") {
      codes.push(error.code);
    }
  }
  return codes;
}

/** Signs in through allauth. The password goes into the request body only. */
export async function signIn(username: string, password: string): Promise<SignInResult> {
  let response: Response;
  try {
    response = await send(LOGIN_PATH, "POST", { username, password });
  } catch {
    return { kind: "network" };
  }
  switch (response.status) {
    case 200:
    case 409:
      return { kind: "signed-in" };
    case 429:
      return { kind: "rate-limited" };
    case 403:
      return { kind: "expired-page" };
    case 400: {
      const codes = await errorCodes(response);
      if (codes.includes(LOCKED_CODE)) {
        return { kind: "locked" };
      }
      if (codes.includes(WRONG_CREDENTIALS_CODE)) {
        return { kind: "wrong-credentials" };
      }
      return { kind: "invalid" };
    }
    default:
      return { kind: "http-error", status: response.status };
  }
}

/** Signs out through allauth. allauth answers a successful sign-out with 401 (no session any more). */
export async function signOut(): Promise<SignOutResult> {
  let response: Response;
  try {
    response = await send(SESSION_PATH, "DELETE");
  } catch {
    return { kind: "network" };
  }
  if (response.status === 401 || response.ok) {
    return { kind: "signed-out" };
  }
  return { kind: "http-error", status: response.status };
}
