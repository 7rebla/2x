import { QueryClientProvider, useQuery } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ErrorMessage } from "../components/ErrorMessage.tsx";
import { Loading } from "../components/Loading.tsx";
import { changeLanguage } from "../i18n.ts";
import { selftestRetrieveOptions } from "./generated/@tanstack/react-query.gen.ts";
import { ApiError, installApiErrorHandling, MAX_DETAIL_LENGTH, toApiError } from "./errors.ts";
import { createQueryClient, NETWORK_RETRIES, shouldRetry } from "./queryClient.ts";

const request = new Request("http://localhost/api/v1/selftest/");

function answer(status: number, body = "", contentType = "application/json"): Response {
  return new Response(body === "" ? null : body, { status, headers: { "Content-Type": contentType } });
}

afterEach(async () => {
  cleanup();
  vi.unstubAllGlobals();
  await changeLanguage("en");
  window.localStorage.clear();
});

describe("toApiError", () => {
  it("keeps HTTP status and DRF detail", () => {
    const error = toApiError({ detail: "Not found." }, answer(404), request);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ kind: "http", status: 404, detail: "Not found." });
  });

  it("has no detail for JSON bodies without a detail text", () => {
    expect(toApiError({ name: ["This field is required."] }, answer(400), request)).toMatchObject({
      kind: "http",
      status: 400,
      detail: null,
    });
    expect(toApiError({ detail: 42 }, answer(400), request)).toMatchObject({ detail: null });
  });

  it("shows plain text bodies, but not HTML pages", () => {
    expect(toApiError(" Bad gateway \n", answer(502, "x", "text/plain; charset=utf-8"), request)).toMatchObject({
      kind: "http",
      status: 502,
      detail: "Bad gateway",
    });
    expect(toApiError("<html>proxy</html>", answer(502, "x", "text/html"), request)).toMatchObject({
      status: 502,
      detail: null,
    });
    expect(toApiError("   ", answer(500, "x", "text/plain"), request)).toMatchObject({ detail: null });
  });

  it("cuts long texts", () => {
    const error = toApiError({ detail: "x".repeat(MAX_DETAIL_LENGTH + 10) }, answer(500), request);

    expect((error as ApiError).detail).toBe(`${"x".repeat(MAX_DETAIL_LENGTH)}…`);
  });

  it("marks a missing answer as network error", () => {
    const cause = new TypeError("Failed to fetch");
    const error = toApiError(cause, undefined, request);

    expect(error).toMatchObject({ kind: "network", status: null, detail: null, cause });
  });

  it("marks an unreadable 2xx answer as invalid answer", () => {
    expect(toApiError(new SyntaxError("Unexpected token <"), answer(200), request)).toMatchObject({
      kind: "invalid-answer",
      status: 200,
    });
  });

  it("leaves cancellations, errors before the request and ApiErrors unchanged", () => {
    const abort = new DOMException("aborted", "AbortError");
    const early = new TypeError("Invalid URL");
    const apiError = new ApiError("http", 500, null);

    expect(toApiError(abort, undefined, request)).toBe(abort);
    expect(toApiError(early, undefined, undefined)).toBe(early);
    expect(toApiError(apiError, answer(500), request)).toBe(apiError);
  });
});

describe("shouldRetry", () => {
  it("retries only a missing answer, and only a few times", () => {
    const network = new ApiError("network", null, null);

    expect(shouldRetry(0, network)).toBe(true);
    expect(shouldRetry(NETWORK_RETRIES, network)).toBe(false);
    expect(shouldRetry(0, new ApiError("http", 503, null))).toBe(false);
    expect(shouldRetry(0, new ApiError("invalid-answer", 200, null))).toBe(false);
    expect(shouldRetry(0, new Error("other"))).toBe(false);
  });
});

/** A page as later work orders write it: generated query options, Loading and ErrorMessage. */
function SelftestProbe(): ReactElement {
  const query = useQuery({ ...selftestRetrieveOptions(), retry: false });
  if (query.isPending) {
    return <Loading />;
  }
  if (query.isError) {
    return <ErrorMessage error={query.error} />;
  }
  return <p data-testid="probe-result">{query.data.worker.result}</p>;
}

function renderProbe(fetchAnswer: () => Promise<Response>): void {
  installApiErrorHandling();
  // Node's Request rejects relative URLs; the browser resolves them against the page address.
  vi.stubGlobal(
    "Request",
    class extends Request {
      constructor(input: RequestInfo | URL, init?: RequestInit) {
        super(typeof input === "string" ? new URL(input, window.location.href) : input, init);
      }
    },
  );
  vi.stubGlobal("fetch", vi.fn(fetchAnswer));
  render(
    <QueryClientProvider client={createQueryClient()}>
      <SelftestProbe />
    </QueryClientProvider>,
  );
}

describe("generated query options with Loading and ErrorMessage", () => {
  it("shows Loading, then the data", async () => {
    renderProbe(() =>
      Promise.resolve(
        answer(
          200,
          JSON.stringify({
            database: { ok: true, server_version: "18.7", error: "" },
            worker: { ok: true, result: "pong", duration_ms: 3, error: "" },
          }),
        ),
      ),
    );

    expect(screen.getByTestId("loading").textContent).toBe("Loading…");
    expect((await screen.findByTestId("probe-result")).textContent).toBe("pong");
  });

  it("shows HTTP status and the API's text", async () => {
    renderProbe(() =>
      Promise.resolve(answer(403, JSON.stringify({ detail: "Authentication credentials were not provided." }))),
    );

    expect((await screen.findByTestId("error-summary")).textContent).toBe(
      "The API answered with HTTP status 403.",
    );
    expect(screen.getByTestId("error-detail").textContent).toBe(
      "Authentication credentials were not provided.",
    );
    expect(screen.getByRole("alert")).toBeDefined();
  });

  it("shows a missing answer in German", async () => {
    await changeLanguage("de");
    renderProbe(() => Promise.reject(new TypeError("Failed to fetch")));

    expect((await screen.findByTestId("error-summary")).textContent).toBe(
      "Die API hat nicht geantwortet. Läuft der Server?",
    );
    expect(screen.queryByTestId("error-detail")).toBeNull();
  });

  it("shows an unreadable answer", async () => {
    renderProbe(() => Promise.resolve(answer(200, "<!doctype html>", "application/json")));

    expect((await screen.findByTestId("error-summary")).textContent).toBe(
      "The API sent an answer this page cannot read.",
    );
  });
});
