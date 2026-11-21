import { afterEach, describe, expect, it, vi } from "vitest";

import { loadSelftest, SELFTEST_TIMEOUT_MS } from "./selftest.ts";

/** Node's Request rejects relative URLs; resolve them against the page like a browser does. */
class PageRelativeRequest extends Request {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    super(typeof input === "string" ? new URL(input, window.location.href) : input, init);
  }
}

/** A fetch that never answers and only ends when its request is aborted. */
function hangingFetch(request: Request): Promise<Response> {
  return new Promise((_resolve, reject) => {
    request.signal.addEventListener("abort", () => {
      reject(new DOMException("aborted", "AbortError"));
    });
  });
}

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("loadSelftest", () => {
  it("reports an API that never answers as unreachable after the timeout", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("Request", PageRelativeRequest);
    vi.stubGlobal("fetch", vi.fn(hangingFetch));

    const outcome = loadSelftest(new AbortController().signal);
    await vi.advanceTimersByTimeAsync(SELFTEST_TIMEOUT_MS);

    await expect(outcome).resolves.toEqual({ kind: "unreachable" });
  });

  it("stops the request when the caller aborts", async () => {
    vi.stubGlobal("Request", PageRelativeRequest);
    const fetchMock = vi.fn(hangingFetch);
    vi.stubGlobal("fetch", fetchMock);
    const caller = new AbortController();

    const outcome = loadSelftest(caller.signal);
    await vi.waitFor(() => {
      expect(fetchMock).toHaveBeenCalledOnce();
    });
    caller.abort();

    await expect(outcome).resolves.toEqual({ kind: "unreachable" });
  });
});
