import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Selftest } from "./api/generated";
import { App } from "./App.tsx";
import { texts } from "./texts.ts";

const healthy: Selftest = {
  database: { ok: true, server_version: "18.7 (Debian 18.7-1.pgdg12+2)", error: "" },
  worker: { ok: true, result: "pong", duration_ms: 15, error: "" },
};

const workerDown: Selftest = {
  database: { ok: true, server_version: "18.7 (Debian 18.7-1.pgdg12+2)", error: "" },
  worker: {
    ok: false,
    result: "",
    duration_ms: 5019,
    error: "no result from a worker within 5 seconds",
  },
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
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

/** Replaces the browser's fetch; the generated client looks it up on every call. */
function stubApi(...answers: (() => Promise<Response>)[]): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn((request: Request): Promise<Response> => {
    const answer = answers[Math.min(fetchMock.mock.calls.length - 1, answers.length - 1)];
    if (answer === undefined) {
      throw new Error("no stubbed answer");
    }
    expect(new URL(request.url).pathname).toBe("/api/v1/selftest/");
    return answer();
  });
  vi.stubGlobal("Request", PageRelativeRequest);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("self-test page", () => {
  it("renders the heading", () => {
    stubApi(() => Promise.resolve(jsonResponse(healthy)));
    render(<App />);

    expect(screen.getByRole("heading", { level: 1, name: texts.appTitle })).toBeDefined();
  });

  it("shows database version and worker result when everything is fine", async () => {
    stubApi(() => Promise.resolve(jsonResponse(healthy)));
    render(<App />);

    expect(screen.getByTestId("selftest-loading").textContent).toBe(texts.selftest.checking);
    expect((await screen.findByTestId("database-version")).textContent).toBe(
      "18.7 (Debian 18.7-1.pgdg12+2)",
    );
    expect(screen.getByTestId("worker-result").textContent).toBe("pong");
    expect(screen.getByTestId("worker-duration").textContent).toBe("15 ms");
    expect(screen.getByTestId("database-status").textContent).toBe(texts.selftest.statusOk);
    expect(screen.getByTestId("worker-status").textContent).toBe(texts.selftest.statusOk);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows the API's error text when the worker is down", async () => {
    stubApi(() => Promise.resolve(jsonResponse(workerDown)));
    render(<App />);

    expect((await screen.findByTestId("worker-error")).textContent).toBe(
      "no result from a worker within 5 seconds",
    );
    expect(screen.getByTestId("worker-status").textContent).toBe(texts.selftest.statusFailed);
    expect(screen.getByTestId("worker-duration").textContent).toBe("5019 ms");
    expect(screen.queryByTestId("worker-result")).toBeNull();
    expect(screen.getByTestId("database-version").textContent).toBe(
      "18.7 (Debian 18.7-1.pgdg12+2)",
    );
    expect(screen.queryByTestId("selftest-error")).toBeNull();
  });

  it("shows a separate state when the API does not respond", async () => {
    const fetchMock = stubApi(() => Promise.reject(new TypeError("Failed to fetch")));
    render(<App />);

    const error = await screen.findByTestId("selftest-error");
    expect(fetchMock).toHaveBeenCalled();
    expect(error.textContent).toBe(texts.selftest.apiUnreachable);
    expect(error.getAttribute("role")).toBe("alert");
    expect(screen.queryByTestId("database-check")).toBeNull();
    expect(screen.queryByTestId("worker-check")).toBeNull();
  });

  it("shows the HTTP status when the API answers with an error", async () => {
    stubApi(() => Promise.resolve(jsonResponse({ detail: "Server Error" }, 502)));
    render(<App />);

    expect((await screen.findByTestId("selftest-error")).textContent).toBe(
      texts.selftest.apiHttpError(502),
    );
  });

  it("fetches again when the user clicks the recheck button", async () => {
    const fetchMock = stubApi(
      () => Promise.reject(new TypeError("Failed to fetch")),
      () => Promise.resolve(jsonResponse(healthy)),
    );
    render(<App />);
    await screen.findByTestId("selftest-error");
    const callsBefore = fetchMock.mock.calls.length;

    fireEvent.click(screen.getByRole("button", { name: texts.selftest.recheck }));

    expect((await screen.findByTestId("worker-result")).textContent).toBe("pong");
    expect(fetchMock.mock.calls.length).toBe(callsBefore + 1);
    expect(screen.queryByTestId("selftest-error")).toBeNull();
  });
});
