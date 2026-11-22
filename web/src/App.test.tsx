import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Selftest } from "./api/generated";
import { changeLanguage } from "./i18n.ts";
import { fakeApi, jsonResponse, manager } from "./test/fakeApi.ts";
import { renderApp } from "./test/renderApp.tsx";

const healthy: Selftest = {
  database: { ok: true, server_version: "18.7 (Debian 18.7-1.pgdg12+2)", error: "" },
  worker: { ok: true, result: "pong", duration_ms: 15, error: "" },
  ai: { enabled: false },
};

const workerDown: Selftest = {
  database: { ok: true, server_version: "18.7 (Debian 18.7-1.pgdg12+2)", error: "" },
  worker: {
    ok: false,
    result: "",
    duration_ms: 5019,
    error: "no result from a worker within 5 seconds",
  },
  ai: { enabled: false },
};

/**
 * Replaces the browser's fetch; the generated client looks it up on every call.
 * The page is signed in as a manager; the self-test calls get `answers` in order
 * (the last one repeats). Returns the self-test calls made so far.
 */
function stubApi(...answers: (() => Promise<Response>)[]): () => Request[] {
  let selftestCalls = 0;
  const api = fakeApi(manager, (request) => {
    expect(new URL(request.url).pathname).toBe("/api/v1/selftest/");
    const answer = answers[Math.min(selftestCalls, answers.length - 1)];
    selftestCalls += 1;
    if (answer === undefined) {
      throw new Error("no stubbed answer");
    }
    return answer();
  });
  return () => api.requestsTo("/api/v1/selftest/");
}

afterEach(async () => {
  cleanup();
  vi.unstubAllGlobals();
  await changeLanguage("en");
  window.localStorage.clear();
});

describe("self-test page at /selftest", () => {
  it("renders the heading", () => {
    stubApi(() => Promise.resolve(jsonResponse(healthy)));
    renderApp("/selftest");

    expect(screen.getByRole("heading", { level: 1, name: "2x" })).toBeDefined();
  });

  it("shows that it is checking while the API has not answered", async () => {
    stubApi(() => new Promise<Response>(() => undefined));
    renderApp("/selftest");

    expect((await screen.findByTestId("selftest-loading")).textContent).toBe("Checking…");
  });

  it("shows database version and worker result when everything is fine", async () => {
    stubApi(() => Promise.resolve(jsonResponse(healthy)));
    renderApp("/selftest");

    expect((await screen.findByTestId("database-version")).textContent).toBe(
      "18.7 (Debian 18.7-1.pgdg12+2)",
    );
    expect(screen.getByTestId("worker-result").textContent).toBe("pong");
    expect(screen.getByTestId("worker-duration").textContent).toBe("15 ms");
    expect(screen.getByTestId("database-status").textContent).toBe("OK");
    expect(screen.getByTestId("worker-status").textContent).toBe("OK");
    expect(screen.getByTestId("ai-status").textContent).toBe("Not enabled");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows the API's error text when the worker is down", async () => {
    stubApi(() => Promise.resolve(jsonResponse(workerDown)));
    renderApp("/selftest");

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
    const selftestCalls = stubApi(() => Promise.reject(new TypeError("Failed to fetch")));
    renderApp("/selftest");

    const error = await screen.findByTestId("selftest-error");
    expect(selftestCalls().length).toBeGreaterThan(0);
    expect(error.textContent).toBe("The API did not respond. Is the server running?");
    expect(error.getAttribute("role")).toBe("alert");
    expect(screen.queryByTestId("database-check")).toBeNull();
    expect(screen.queryByTestId("worker-check")).toBeNull();
    expect(screen.queryByTestId("ai-check")).toBeNull();
  });

  it("does not accept an answer without the AI part", async () => {
    stubApi(() =>
      Promise.resolve(jsonResponse({ database: healthy.database, worker: healthy.worker })),
    );
    renderApp("/selftest");

    expect((await screen.findByTestId("selftest-error")).textContent).toBe(
      "The API sent an answer this page cannot read.",
    );
  });

  it("shows the HTTP status when the API answers with an error", async () => {
    stubApi(() => Promise.resolve(jsonResponse({ detail: "Server Error" }, 502)));
    renderApp("/selftest");

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
    renderApp("/selftest");

    expect((await screen.findByTestId("selftest-error")).textContent).toBe(
      "The API sent an answer this page cannot read.",
    );

    fireEvent.click(screen.getByRole("button", { name: "Check again" }));

    expect(await screen.findByRole("button", { name: "Check again" })).toBeDefined();
    expect(screen.getByTestId("selftest-error").textContent).toBe("The API sent an answer this page cannot read.");
  });

  it("fetches again when the user clicks the recheck button", async () => {
    const selftestCalls = stubApi(
      () => Promise.reject(new TypeError("Failed to fetch")),
      () => Promise.resolve(jsonResponse(healthy)),
    );
    renderApp("/selftest");
    await screen.findByTestId("selftest-error");
    const callsBefore = selftestCalls().length;

    fireEvent.click(screen.getByRole("button", { name: "Check again" }));

    expect((await screen.findByTestId("worker-result")).textContent).toBe("pong");
    expect(selftestCalls().length).toBe(callsBefore + 1);
    expect(screen.queryByTestId("selftest-error")).toBeNull();
  });
});

describe("language switch", () => {
  it("switches texts, number format and <html lang> to German and back", async () => {
    stubApi(() => Promise.resolve(jsonResponse(workerDown)));
    renderApp("/selftest");
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
    renderApp("/selftest");

    expect((await screen.findByTestId("selftest-error")).textContent).toBe(
      "Die API hat mit dem HTTP-Status 502 geantwortet.",
    );
  });

  it("ignores values that are not a supported language", async () => {
    stubApi(() => Promise.resolve(jsonResponse(healthy)));
    renderApp("/selftest");
    await screen.findByTestId("worker-result");

    fireEvent.change(screen.getByTestId("language-switch"), { target: { value: "fr" } });

    expect(document.documentElement.lang).toBe("en");
    expect(screen.getByRole("heading", { level: 2, name: "Self-test" })).toBeDefined();
    expect(window.localStorage.getItem("twox.language")).toBeNull();
  });
});