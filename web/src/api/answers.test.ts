import { QueryClient } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { changeLanguage } from "../i18n.ts";
import type { AnswerEvent } from "../pages/answer/events.ts";
import { deltaEvent, doneEvent, errorEvent, sourcesEvent } from "../pages/answer/testData.ts";
import { type Handler, fakeApi, fakeEventStream, jsonResponse, manager } from "../test/fakeApi.ts";
import {
  ANSWERS_PATH,
  type AnswerRequest,
  type AnswerStreamOutcome,
  answersStatusQueryOptions,
  streamAnswer,
} from "./answers.ts";
import { installClientConfig, onForbidden } from "./client.ts";
import { ApiError } from "./errors.ts";

const QUESTION = "Test question about inspection?";

function setCsrfCookie(value: string): void {
  document.cookie = `csrftoken=${value}; path=/`;
}

function clearCsrfCookie(): void {
  document.cookie = "csrftoken=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
}

/** A handler that answers with a finished stream of `pieces`. */
function streamOf(...pieces: string[]): Handler {
  return () => {
    const stream = fakeEventStream();
    for (const piece of pieces) {
      stream.send(piece);
    }
    stream.close();
    return stream.response();
  };
}

async function run(
  handler: Handler,
  request: AnswerRequest = { question: QUESTION },
  signal: AbortSignal = new AbortController().signal,
): Promise<{ outcome: AnswerStreamOutcome; events: AnswerEvent[]; fetchCount: number }> {
  const api = fakeApi(manager, handler);
  const events: AnswerEvent[] = [];
  const outcome = await streamAnswer(request, {
    signal,
    onEvent: (event) => {
      events.push(event);
    },
  });
  return { outcome, events, fetchCount: api.fetch.mock.calls.length };
}

beforeEach(() => {
  installClientConfig();
});

afterEach(async () => {
  clearCsrfCookie();
  vi.unstubAllGlobals();
  await changeLanguage("en");
  window.localStorage.clear();
});

describe("streamAnswer", () => {
  it("sends one POST with CSRF token, language and the question in the body only", async () => {
    setCsrfCookie("csrf-answer-value");
    await changeLanguage("de");
    const api = fakeApi(manager, streamOf(sourcesEvent([]), doneEvent({ status: "no_evidence", cited: [] })));

    await streamAnswer(
      { question: QUESTION, device: [1000], plant: [100] },
      { signal: new AbortController().signal, onEvent: () => undefined },
    );

    expect(api.fetch).toHaveBeenCalledOnce();
    const [request] = api.requestsTo(ANSWERS_PATH);
    expect(request?.method).toBe("POST");
    expect(request?.headers.get("X-CSRFToken")).toBe("csrf-answer-value");
    expect(request?.headers.get("Accept-Language")).toBe("de");
    expect(request?.headers.get("Content-Type")).toBe("application/json");
    expect(request?.headers.get("Last-Event-ID")).toBeNull();
    const url = new URL(request?.url ?? "");
    expect(url.origin).toBe(window.location.origin);
    expect(url.search).toBe("");
    expect(decodeURIComponent(url.href)).not.toContain("question");
    expect(await request?.json()).toEqual({ question: QUESTION, device: [1000], plant: [100] });
  });

  it("reads events cut anywhere, with CRLF line ends, and passes them in order", async () => {
    const text = sourcesEvent() + deltaEvent("Grüße ") + deltaEvent("First part ") + deltaEvent("[1].") + doneEvent();
    const bytes = new TextEncoder().encode(text.replaceAll("\n", "\r\n"));
    // Cuts inside a line, between CR and LF, and inside the two bytes of "ü".
    const crlf = bytes.indexOf(0x0d) + 1;
    const umlaut = bytes.indexOf(0xc3) + 1;
    const cuts = [0, 5, crlf, crlf + 40, umlaut, umlaut + 3, bytes.length - 2, bytes.length];

    const { outcome, events } = await run(() => {
      const stream = fakeEventStream();
      for (const [start, end] of cuts.slice(0, -1).map((cut, index) => [cut, cuts[index + 1] ?? cut] as const)) {
        stream.sendBytes(bytes.slice(start, end));
      }
      stream.close();
      return stream.response();
    });

    expect(outcome).toEqual({ kind: "completed" });
    expect(events.map((event) => event.type)).toEqual(["sources", "delta", "delta", "delta", "done"]);
    expect(events.filter((event) => event.type === "delta").map((event) => event.text)).toEqual([
      "Grüße ",
      "First part ",
      "[1].",
    ]);
  });

  it("passes the error event and reports its code", async () => {
    const { outcome, events } = await run(streamOf(sourcesEvent(), deltaEvent("a"), errorEvent("timeout", "Too slow.")));

    expect(outcome).toEqual({ kind: "stream-error", code: "timeout", detail: "Too slow." });
    expect(events.at(-1)).toEqual({ type: "error", code: "timeout", detail: "Too slow." });
  });

  it("recognises ai_disabled as a refusal (409) and as an error event", async () => {
    const refused = await run(() =>
      jsonResponse({ detail: "The AI features are switched off.", code: "ai_disabled" }, 409),
    );
    const event = await run(streamOf(errorEvent("ai_disabled")));

    expect(refused.outcome).toEqual({ kind: "ai-disabled" });
    expect(refused.fetchCount).toBe(1);
    expect(event.outcome).toEqual({ kind: "ai-disabled" });
  });

  it("turns a 400 into an ApiError with the text of the server", async () => {
    const { outcome } = await run(() => jsonResponse({ detail: "The question is too long." }, 400));

    expect(outcome.kind).toBe("failed");
    const error = outcome.kind === "failed" ? outcome.error : null;
    expect(error).toBeInstanceOf(ApiError);
    expect(error?.kind).toBe("http");
    expect(error?.status).toBe(400);
    expect(error?.detail).toBe("The question is too long.");
  });

  it.each([
    [409, "answer_in_progress"],
    [503, "chat_not_configured"],
  ] as const)("gives the code of a refusal %s %s", async (status, code) => {
    const { outcome, fetchCount } = await run(() => jsonResponse({ detail: "Not now.", code }, status));

    expect(outcome).toMatchObject({ kind: "failed", code, error: { kind: "http", status, detail: "Not now." } });
    expect(fetchCount).toBe(1);
  });

  it("reads a plain-text error body, cut, and ignores an HTML one", async () => {
    const long = await run(() => new Response("x".repeat(600), { status: 502, headers: { "Content-Type": "text/plain" } }));
    const html = await run(() => new Response("<h1>Bad gateway</h1>", { status: 502, headers: { "Content-Type": "text/html" } }));

    expect(long.outcome).toMatchObject({ kind: "failed", error: { status: 502, detail: `${"x".repeat(500)}…` } });
    expect(html.outcome).toMatchObject({ kind: "failed", code: null, error: { status: 502, detail: null } });
  });

  it("reports a 403 to onForbidden", async () => {
    const listener = vi.fn();
    const stop = onForbidden(listener);

    const { outcome } = await run(() => jsonResponse({ detail: "CSRF Failed." }, 403));
    stop();

    expect(listener).toHaveBeenCalledOnce();
    expect(outcome).toMatchObject({ kind: "failed", error: { kind: "http", status: 403, detail: "CSRF Failed." } });
  });

  it.each<[string, Handler, AnswerStreamOutcome["kind"]]>([
    ["a network error", () => Promise.reject(new TypeError("Failed to fetch")), "failed"],
    ["a 503", () => jsonResponse({ detail: "Unavailable." }, 503), "failed"],
    ["a stream closed without done", streamOf(sourcesEvent(), deltaEvent("a")), "interrupted"],
    [
      "a stream broken off",
      () => {
        const stream = fakeEventStream();
        stream.send(sourcesEvent());
        stream.fail();
        return stream.response();
      },
      "interrupted",
    ],
  ])("fetches exactly once after %s", async (_name, handler, kind) => {
    const { outcome, fetchCount } = await run(handler);
    // Give a retry loop (if a newer generator had one) the chance to fire.
    await new Promise((resolve) => setTimeout(resolve, 20));

    expect(outcome.kind).toBe(kind);
    expect(fetchCount).toBe(1);
  });

  it("calls a missing answer a network error", async () => {
    const { outcome } = await run(() => Promise.reject(new TypeError("Failed to fetch")));

    expect(outcome).toMatchObject({ kind: "failed", error: { kind: "network", status: null } });
  });

  it("rejects a 2xx that is no event stream", async () => {
    const { outcome } = await run(() => fakeEventStream().response(undefined, "application/json"));

    expect(outcome).toMatchObject({ kind: "failed", error: { kind: "invalid-answer", status: 200 } });
  });

  it.each([
    ["an unknown type", sourcesEvent() + 'event: x\ndata: {"type":"progress"}\n\n'],
    ["an unknown status", sourcesEvent() + doneEvent({ status: "maybe" })],
    ["data that is no JSON", sourcesEvent() + "data: not json\n\n"],
    ["a delta before the sources", deltaEvent("a") + sourcesEvent()],
    ["sources twice", sourcesEvent() + sourcesEvent()],
  ])("ends with invalid-answer on %s and stops reading", async (_name, text) => {
    const stream = fakeEventStream();
    const { outcome, events, fetchCount } = await run((request) => {
      stream.send(text);
      stream.send(deltaEvent("after the break"));
      return stream.response(request);
    });

    expect(outcome).toMatchObject({ kind: "failed", error: { kind: "invalid-answer" } });
    expect(events.some((event) => event.type === "delta" && event.text === "after the break")).toBe(false);
    expect(stream.stopped).toBe(true);
    expect(fetchCount).toBe(1);
  });

  it("ends as aborted without error when the signal fires during the stream", async () => {
    const controller = new AbortController();
    const stream = fakeEventStream();
    const events: AnswerEvent[] = [];
    const api = fakeApi(manager, (request) => stream.response(request));

    const pending = streamAnswer(
      { question: QUESTION },
      {
        signal: controller.signal,
        onEvent: (event) => {
          events.push(event);
          if (event.type === "delta") {
            controller.abort();
          }
        },
      },
    );
    stream.send(sourcesEvent() + deltaEvent("a"));
    await vi.waitFor(() => {
      expect(events).toHaveLength(2);
    });
    stream.send(deltaEvent("b") + doneEvent());

    expect(await pending).toEqual({ kind: "aborted" });
    expect(events.map((event) => event.type)).toEqual(["sources", "delta"]);
    expect(stream.stopped).toBe(true);
    expect(api.fetch).toHaveBeenCalledOnce();
  });

  it("ends as aborted when the signal fires before the answer", async () => {
    const controller = new AbortController();
    const api = fakeApi(manager, (request) =>
      new Promise<Response>((_resolve, reject) => {
        request.signal.addEventListener("abort", () => {
          reject(new DOMException("The operation was aborted.", "AbortError"));
        });
        controller.abort();
      }),
    );

    expect(await streamAnswer({ question: QUESTION }, { signal: controller.signal, onEvent: () => undefined })).toEqual({
      kind: "aborted",
    });
    expect(api.fetch).toHaveBeenCalledOnce();
  });

  it("does not fetch with a signal that is already aborted", async () => {
    const controller = new AbortController();
    controller.abort();
    const api = fakeApi(manager, streamOf(doneEvent()));

    expect(await streamAnswer({ question: QUESTION }, { signal: controller.signal, onEvent: () => undefined })).toEqual({
      kind: "aborted",
    });
    expect(api.fetch).not.toHaveBeenCalled();
  });
});

describe("answersStatusQueryOptions", () => {
  it("reads GET /api/v1/answers/status/ and keeps it fresh for a short time", async () => {
    const status = { enabled: true, chat_model_configured: false, available: false };
    const api = fakeApi(manager, () => jsonResponse(status));
    const queryClient = new QueryClient();

    const options = answersStatusQueryOptions();

    expect(options.staleTime).toBe(15_000);
    expect(await queryClient.query(options)).toEqual(status);
    expect(api.requestsTo("/api/v1/answers/status/")).toHaveLength(1);
  });
});
