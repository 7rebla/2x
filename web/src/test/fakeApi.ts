// Test helper: a fake of the server behind fetch (API and allauth).
import { type Mock, vi } from "vitest";

import type { Me } from "../api/generated";

/** Test users; the names only ever appear in tests. */
export const manager: Me = { username: "test-manager", role: "manage", is_superuser: false };
export const reader: Me = { username: "test-reader", role: "read", is_superuser: false };
export const roleless: Me = { username: "test-no-role", role: null, is_superuser: false };

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** DRF's answer without a session (SessionAuthentication answers 403, not 401). */
export function notSignedIn(): Response {
  return jsonResponse({ detail: "Authentication credentials were not provided." }, 403);
}

/**
 * Node's Request (used under jsdom) rejects relative URLs, a browser resolves them
 * against the page address. This subclass does what the browser does.
 */
class PageRelativeRequest extends Request {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(typeof input === "string" ? new URL(input, window.location.href) : input, init);
  }
}

export type Handler = (request: Request) => Promise<Response> | Response;

export interface FakeApi {
  readonly fetch: Mock<(request: Request) => Promise<Response>>;
  /** Changes who /api/v1/me/ reports from now on (null: nobody, 403). */
  setMe: (me: Me | null) => void;
  /** All requests to `path`, in order. */
  requestsTo: (path: string) => Request[];
}

/**
 * Replaces fetch. GET /api/v1/me/ answers with `me` (null: 403); every other
 * request goes to `other`, or fails like a server that does not answer.
 */
export function fakeApi(me: Me | null, other?: Handler): FakeApi {
  let current = me;
  const fetchMock = vi.fn((request: Request): Promise<Response> => {
    const path = new URL(request.url).pathname;
    if (path === "/api/v1/me/") {
      return Promise.resolve(current === null ? notSignedIn() : jsonResponse(current));
    }
    if (other === undefined) {
      return Promise.reject(new TypeError("Failed to fetch"));
    }
    return Promise.resolve(other(request));
  });
  vi.stubGlobal("Request", PageRelativeRequest);
  vi.stubGlobal("fetch", fetchMock);
  return {
    fetch: fetchMock,
    setMe: (value) => {
      current = value;
    },
    requestsTo: (path) =>
      fetchMock.mock.calls.map(([request]) => request).filter((request) => new URL(request.url).pathname === path),
  };
}
