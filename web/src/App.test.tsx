import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Selftest } from "./api/generated";
import { App } from "./App.tsx";
import { changeLanguage } from "./i18n.ts";

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

afterEach(async () => {
  cleanup();
  vi.unstubAllGlobals();
  await changeLanguage("en");
  window.localStorage.clear();
});

describe("self-test page", () => {
  it("renders the heading", () => {
    stubApi(() => Promise.resolve(jsonResponse(healthy)));
    render(<App />);

    expect(screen.getByRole("heading", { level: 1, name: "2x" })).toBeDefined();
  });

  it("shows database version and worker result when everything is fine", async () => {
    stubApi(() => Promise.resolve(jsonResponse(healthy)));
    render(<App />);

    expect(screen.getByTestId("selftest-loading").textContent).toBe("Checking…");
    expect((await screen.findByTestId("database-version")).textContent).toBe(
      "18.7 (Debian 18.7-1.pgdg12+2)",
    );
    expect(screen.getByTestId("worker-result").textContent).toBe("pong");
    expect(screen.getByTestId("worker-duration").textContent).toBe("15 ms");
    expect(screen.getByTestId("database-status").textContent).toBe("OK");
    expect(screen.getByTestId("worker-status").textContent).toBe("OK");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows the API's error text when the worker is down", async () => {
    stubApi(() => Promise.resolve(jsonResponse(workerDown)));
    render(<App />);

    expect((await screen.findByTestId("worker-error")).textContent).toBe(
      "no result from a worker within 5 seconds",
    );
    expect(screen.getByTestId("worker-status").textContent).toBe("Failed");
    expect(screen.getByTestId("worker-duration").textContent).toBe("5,019 ms");
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
    expect(error.textContent).toBe("The API did not respond. Is the server running?");
    expect(error.getAttribute("role")).toBe("alert");
    expect(screen.queryByTestId("database-check")).toBeNull();
    expect(screen.queryByTestId("worker-check")).toBeNull();
  });

  it("shows the HTTP status when the API answers with an error", async () => {
    stubApi(() => Promise.resolve(jsonResponse({ detail: "Server Error" }, 502)));
    render(<App />);

    expect((await screen.findByTestId("selftest-error")).textContent).toBe(
      "The API answered with HTTP status 502.",
    );
  });

  it("shows an error when the answer is not the expected JSON", async () => {
    stubApi(
      () =>
        Promise.resolve(
          new Response("<!doctype html><title>x</title>", {
            status: 200,
            headers: { "Content-Type": "text/html" },
          }),
        ),
      () => Promise.resolve(jsonResponse({ detail: "unexpected" })),
    );
    render(<App />);

    expect((await screen.findByTestId("selftest-error")).textContent).toBe(
      "The API sent an answer this page cannot read.",
    );

    fireEvent.click(screen.getByRole("button", { name: "Check again" }));

    expect(await screen.findByRole("button", { name: "Check again" })).toBeDefined();
    expect(screen.getByTestId("selftest-error").textContent).toBe("The API sent an answer this page cannot read.");
  });

  it("fetches again when the user clicks the recheck button", async () => {
    const fetchMock = stubApi(
      () => Promise.reject(new TypeError("Failed to fetch")),
      () => Promise.resolve(jsonResponse(healthy)),
    );
    render(<App />);
    await screen.findByTestId("selftest-error");
    const callsBefore = fetchMock.mock.calls.length;

    fireEvent.click(screen.getByRole("button", { name: "Check again" }));

    expect((await screen.findByTestId("worker-result")).textContent).toBe("pong");
    expect(fetchMock.mock.calls.length).toBe(callsBefore + 1);
    expect(screen.queryByTestId("selftest-error")).toBeNull();
  });
});

describe("language switch", () => {
  it("switches texts, number format and <html lang> to German and back", async () => {
    stubApi(() => Promise.resolve(jsonResponse(workerDown)));
    render(<App />);
    expect(await screen.findByTestId("worker-duration")).toBeDefined();
    expect(document.documentElement.lang).toBe("en");
    expect(screen.getByTestId("worker-duration").textContent).toBe("5,019 ms");

    fireEvent.change(screen.getByTestId("language-switch"), { target: { value: "de" } });

    expect(await screen.findByRole("heading", { level: 2, name: "Selbsttest" })).toBeDefined();
    expect(document.documentElement.lang).toBe("de");
    expect(screen.getByTestId("database-heading").textContent).toBe("Datenbank");
    expect(screen.getByTestId("worker-heading").textContent).toBe("Hintergrunddienst");
    expect(screen.getByTestId("worker-status").textContent).toBe("Fehlgeschlagen");
    expect(screen.getByTestId("worker-duration").textContent).toBe("5.019 ms");
    expect(screen.getByRole("button", { name: "Erneut prüfen" })).toBeDefined();
    expect(screen.getByText("Sprache")).toBeDefined();
    // The API's own error text is data and stays as sent.
    expect(screen.getByTestId("worker-error").textContent).toBe(
      "no result from a worker within 5 seconds",
    );
    expect(window.localStorage.getItem("twox.language")).toBe("de");

    fireEvent.change(screen.getByTestId("language-switch"), { target: { value: "en" } });

    expect(await screen.findByRole("heading", { level: 2, name: "Self-test" })).toBeDefined();
    expect(document.documentElement.lang).toBe("en");
    expect(window.localStorage.getItem("twox.language")).toBe("en");
  });

  it("shows German error texts with the HTTP status", async () => {
    await changeLanguage("de");
    stubApi(() => Promise.resolve(jsonResponse({ detail: "Server Error" }, 502)));
    render(<App />);

    expect((await screen.findByTestId("selftest-error")).textContent).toBe(
      "Die API hat mit dem HTTP-Status 502 geantwortet.",
    );
  });

  it("ignores values that are not a supported language", async () => {
    stubApi(() => Promise.resolve(jsonResponse(healthy)));
    render(<App />);
    await screen.findByTestId("worker-result");

    fireEvent.change(screen.getByTestId("language-switch"), { target: { value: "fr" } });

    expect(document.documentElement.lang).toBe("en");
    expect(screen.getByRole("heading", { level: 2, name: "Self-test" })).toBeDefined();
    expect(window.localStorage.getItem("twox.language")).toBeNull();
  });
});