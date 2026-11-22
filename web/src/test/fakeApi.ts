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

/** One server-sent event as the answer API writes it (`event:` and `data:` lines, empty line). */
export function sseEvent(data: { type: string } & Record<string, unknown>): string {
  return `event: ${data.type}\ndata: ${JSON.stringify(data)}\n\n`;
}

/** A stream of server-sent events whose pieces the test sends one by one. */
export interface FakeEventStream {
  /**
   * Answer 200 with this stream as body (Content-Type text/event-stream unless
   * given). Like a real fetch, aborting the signal of `request` breaks the body off.
   */
  response: (request?: Request, contentType?: string) => Response;
  /** Sends a piece of text (any cut: lines may be split between pieces). */
  send: (text: string) => void;
  /** Sends raw bytes (a character may be split between two pieces). */
  sendBytes: (bytes: Uint8Array) => void;
  /** Ends the stream normally (the server closed it). */
  close: () => void;
  /** Breaks the stream off with an error (connection lost). */
  fail: () => void;
  /** True once the client stopped the stream (cancelled the body or aborted the request). */
  readonly stopped: boolean;
}

export function fakeEventStream(): FakeEventStream {
  const encoder = new TextEncoder();
  let controller: ReadableStreamDefaultController<Uint8Array> | null = null;
  let stopped = false;
  let finished = false;
  const body = new ReadableStream<Uint8Array>({
    start(streamController) {
      controller = streamController;
    },
    cancel() {
      stopped = true;
      finished = true;
    },
  });
  const withController = (action: (streamController: ReadableStreamDefaultController<Uint8Array>) => void): void => {
    if (controller !== null && !finished) {
      action(controller);
    }
  };
  const end = (action: (streamController: ReadableStreamDefaultController<Uint8Array>) => void): void => {
    withController(action);
    finished = true;
  };
  return {
    response: (request, contentType = "text/event-stream; charset=utf-8") => {
      request?.signal.addEventListener("abort", () => {
        if (!finished) {
          stopped = true;
        }
        end((streamController) => {
          streamController.error(new DOMException("The operation was aborted.", "AbortError"));
        });
      });
      return new Response(body, { status: 200, headers: { "Content-Type": contentType } });
    },
    send: (text) => {
      withController((streamController) => {
        streamController.enqueue(encoder.encode(text));
      });
    },
    sendBytes: (bytes) => {
      withController((streamController) => {
        streamController.enqueue(bytes);
      });
    },
    close: () => {
      end((streamController) => {
        streamController.close();
      });
    },
    fail: () => {
      end((streamController) => {
        streamController.error(new TypeError("network error"));
      });
    },
    get stopped() {
      return stopped;
    },
  };
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
