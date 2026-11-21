// Configuration of every API call of the web UI (not part of the generated code).
//
// - Writing requests send the CSRF token from the cookie `csrftoken` in the
//   header X-CSRFToken (Django, session sign-in, E-38).
// - Every request sends Accept-Language with the language shown.
// - A 403 of any call (except GET /api/v1/me/ itself) is reported to the
//   listeners of onForbidden; the session code then asks /api/v1/me/ again
//   to tell an expired session from a missing permission.
import { currentLanguage } from "../i18n.ts";
import { client as defaultClient } from "./generated/client.gen.ts";

export const CSRF_COOKIE_NAME = "csrftoken";
export const CSRF_HEADER_NAME = "X-CSRFToken";

/** Path of the endpoint that names the signed-in user and the role. */
export const ME_PATH = "/api/v1/me/";

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS", "TRACE"]);

/** Value of the CSRF cookie, or null if the page has none (yet). */
export function csrfToken(): string | null {
  for (const part of document.cookie.split(";")) {
    const separator = part.indexOf("=");
    if (separator === -1) {
      continue;
    }
    if (part.slice(0, separator).trim() === CSRF_COOKIE_NAME) {
      const value = part.slice(separator + 1).trim();
      try {
        return value === "" ? null : decodeURIComponent(value);
      } catch {
        return null;
      }
    }
  }
  return null;
}

/** True for methods that change data on the server (Django checks CSRF for these). */
export function isWritingMethod(method: string): boolean {
  return !SAFE_METHODS.has(method.toUpperCase());
}

/**
 * Sets Accept-Language and, for writing methods, X-CSRFToken on the given
 * headers. Used by the generated client and by the sign-in calls (auth.ts).
 */
export function addApiHeaders(headers: Headers, method: string): void {
  headers.set("Accept-Language", currentLanguage());
  if (isWritingMethod(method)) {
    const token = csrfToken();
    if (token !== null) {
      headers.set(CSRF_HEADER_NAME, token);
    }
  }
}

type ForbiddenListener = () => void;

const forbiddenListeners = new Set<ForbiddenListener>();

/** Calls `listener` after every 403 of an API call; returns the function that unsubscribes. */
export function onForbidden(listener: ForbiddenListener): () => void {
  forbiddenListeners.add(listener);
  return () => {
    forbiddenListeners.delete(listener);
  };
}

function isMeRequest(request: Request): boolean {
  try {
    return new URL(request.url, window.location.href).pathname === ME_PATH;
  } catch {
    return false;
  }
}

/** Tells the listeners about a 403; the answer itself passes through unchanged. */
export function reportForbidden(response: Response, request: Request): Response {
  if (response.status === 403 && !isMeRequest(request)) {
    for (const listener of forbiddenListeners) {
      listener();
    }
  }
  return response;
}

type ApiClient = typeof defaultClient;

const configured = new WeakSet<ApiClient>();

/** Registers the header and 403 handling on the generated client, once per client. */
export function installClientConfig(apiClient: ApiClient = defaultClient): void {
  if (configured.has(apiClient)) {
    return;
  }
  configured.add(apiClient);
  apiClient.interceptors.request.use((request) => {
    addApiHeaders(request.headers, request.method);
    return request;
  });
  apiClient.interceptors.response.use((response, request) => reportForbidden(response, request));
}
