import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { AnswerStreamOutcome } from "../../api/answers.ts";
import { installClientConfig, onForbidden } from "../../api/client.ts";
import { ApiError } from "../../api/errors.ts";
import { type FakeEventStream, type Handler, fakeApi, fakeEventStream, jsonResponse, manager } from "../../test/fakeApi.ts";
import { deltaEvent, doneEvent, errorEvent, sourcesEvent, answerSource } from "./testData.ts";
import {
  type AnswerStreamState,
  answerStreamReducer,
  initialAnswerStreamState,
  useAnswerStream,
} from "./useAnswerStream.ts";

const REQUEST = { question: "Test question about inspection?" };

/** A fake server whose answer stream the test drives; counts the requests. */
function fakeStreamServer(): { stream: FakeEventStream; fetchCount: () => number } {
  const stream = fakeEventStream();
  const api = fakeApi(manager, (request) => stream.response(request));
  return { stream, fetchCount: () => api.fetch.mock.calls.length };
}

function serverAnswering(handler: Handler): () => number {
  const api = fakeApi(manager, handler);
  return () => api.fetch.mock.calls.length;
}

beforeEach(() => {
  installClientConfig();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useAnswerStream", () => {
  it("goes idle → streaming → done and takes sources, pieces and the checked text", async () => {
    const { stream, fetchCount } = fakeStreamServer();
    const { result } = renderHook(() => useAnswerStream());
    expect(result.current.state).toEqual(initialAnswerStreamState);

    act(() => {
      result.current.ask(REQUEST);
    });
    expect(result.current.state.phase).toBe("streaming");

    const sources = [answerSource(1), answerSource(2)];
    stream.send(sourcesEvent(sources) + deltaEvent("Provisional "));
    stream.send(deltaEvent("text [1]"));
    await waitFor(() => {
      expect(result.current.state.text).toBe("Provisional text [1]");
    });
    expect(result.current.state).toMatchObject({ phase: "streaming", sources, verified: false });

    stream.send(doneEvent({ status: "contradiction", cited: [1, 2], removed_sentences: 1, final_text: "Checked [1] [2]." }));
    stream.close();
    await waitFor(() => {
      expect(result.current.state.phase).toBe("done");
    });

    expect(result.current.state).toEqual({
      phase: "done",
      sources,
      text: "Checked [1] [2].",
      verified: true,
      status: "contradiction",
      cited: [1, 2],
      removedSentences: 1,
    });
    expect(fetchCount()).toBe(1);
  });

  it("keeps the text a plain string, markup included", async () => {
    const markup = '<img src=x onerror="alert(1)">';
    const { stream } = fakeStreamServer();
    const { result } = renderHook(() => useAnswerStream());

    act(() => {
      result.current.ask(REQUEST);
    });
    stream.send(sourcesEvent() + deltaEvent(markup));
    await waitFor(() => {
      expect(result.current.state.text).toBe(markup);
    });
    expect(typeof result.current.state.text).toBe("string");
  });

  it("ignores a second ask while streaming", async () => {
    const { stream, fetchCount } = fakeStreamServer();
    const { result } = renderHook(() => useAnswerStream());

    act(() => {
      result.current.ask(REQUEST);
    });
    act(() => {
      result.current.ask({ question: "Another question?" });
    });
    stream.send(sourcesEvent() + doneEvent());
    stream.close();
    await waitFor(() => {
      expect(result.current.state.phase).toBe("done");
    });

    expect(fetchCount()).toBe(1);
  });

  it("asks again after done, with a fresh state", async () => {
    let count = 0;
    const fetchCount = serverAnswering((request) => {
      count += 1;
      const stream = fakeEventStream();
      stream.send(sourcesEvent([]) + doneEvent({ status: "no_evidence", cited: [], final_text: `Answer ${String(count)}` }));
      stream.close();
      return stream.response(request);
    });
    const { result } = renderHook(() => useAnswerStream());

    act(() => {
      result.current.ask(REQUEST);
    });
    await waitFor(() => {
      expect(result.current.state.text).toBe("Answer 1");
    });
    act(() => {
      result.current.ask(REQUEST);
    });
    expect(result.current.state).toMatchObject({ phase: "streaming", text: "", sources: null });
    await waitFor(() => {
      expect(result.current.state.text).toBe("Answer 2");
    });
    expect(fetchCount()).toBe(2);
  });

  it("cancel() stops the stream; nothing is fetched or changed afterwards", async () => {
    const { stream, fetchCount } = fakeStreamServer();
    const { result } = renderHook(() => useAnswerStream());

    act(() => {
      result.current.ask(REQUEST);
    });
    stream.send(sourcesEvent() + deltaEvent("Partial"));
    await waitFor(() => {
      expect(result.current.state.text).toBe("Partial");
    });

    act(() => {
      result.current.cancel();
    });
    const cancelled = result.current.state;
    expect(cancelled).toMatchObject({ phase: "idle", cancelled: true, text: "Partial", verified: false });

    stream.send(deltaEvent(" more") + doneEvent());
    await new Promise((resolve) => setTimeout(resolve, 30));

    expect(result.current.state).toBe(cancelled);
    expect(stream.stopped).toBe(true);
    expect(fetchCount()).toBe(1);
  });

  it("unmount aborts the stream; nothing is fetched or dispatched afterwards", async () => {
    const { stream, fetchCount } = fakeStreamServer();
    const consoleError = vi.spyOn(console, "error");
    const { result, unmount } = renderHook(() => useAnswerStream());

    act(() => {
      result.current.ask(REQUEST);
    });
    stream.send(sourcesEvent());
    await waitFor(() => {
      expect(result.current.state.sources).not.toBeNull();
    });
    const before = result.current.state;

    unmount();
    stream.send(deltaEvent("late") + doneEvent());
    await new Promise((resolve) => setTimeout(resolve, 30));

    expect(stream.stopped).toBe(true);
    expect(fetchCount()).toBe(1);
    expect(result.current.state).toBe(before);
    expect(consoleError).not.toHaveBeenCalled();
    consoleError.mockRestore();
  });

  it.each<[string, Handler, AnswerStreamState["phase"], string]>([
    ["a network error", () => Promise.reject(new TypeError("Failed to fetch")), "error", "network"],
    ["a 503", () => jsonResponse({ detail: "No chat model.", code: "chat_not_configured" }, 503), "error", "http"],
    [
      "a stream that ends without done",
      (request) => {
        const stream = fakeEventStream();
        stream.send(sourcesEvent() + deltaEvent("a"));
        stream.close();
        return stream.response(request);
      },
      "error",
      "interrupted",
    ],
  ])("after %s there was exactly one request", async (_name, handler, phase, cause) => {
    const fetchCount = serverAnswering(handler);
    const { result } = renderHook(() => useAnswerStream());

    act(() => {
      result.current.ask(REQUEST);
    });
    await waitFor(() => {
      expect(result.current.state.phase).toBe(phase);
    });
    await new Promise((resolve) => setTimeout(resolve, 30));

    expect(result.current.state).toMatchObject({ failure: { cause } });
    expect(fetchCount()).toBe(1);
  });

  it("calls a 403 forbidden and tells onForbidden", async () => {
    serverAnswering(() => jsonResponse({ detail: "You do not have permission to perform this action." }, 403));
    const listener = vi.fn();
    const stop = onForbidden(listener);
    const { result } = renderHook(() => useAnswerStream());

    act(() => {
      result.current.ask(REQUEST);
    });
    await waitFor(() => {
      expect(result.current.state.phase).toBe("error");
    });
    stop();

    expect(result.current.state).toMatchObject({ failure: { cause: "forbidden", error: { status: 403 } } });
    expect(listener).toHaveBeenCalledOnce();
  });

  it("gives a 400 as ApiError with status and text", async () => {
    serverAnswering(() => jsonResponse({ detail: "The question must not be empty." }, 400));
    const { result } = renderHook(() => useAnswerStream());

    act(() => {
      result.current.ask(REQUEST);
    });
    await waitFor(() => {
      expect(result.current.state.phase).toBe("error");
    });

    const { state } = result.current;
    expect(state.phase === "error" && state.failure.cause === "http" ? state.failure.error : null).toEqual(
      new ApiError("http", 400, "The question must not be empty."),
    );
    expect(state).toMatchObject({ failure: { error: { status: 400, detail: "The question must not be empty." } } });
  });

  it.each<[string, Handler]>([
    ["a 409 ai_disabled", () => jsonResponse({ detail: "The AI features are switched off.", code: "ai_disabled" }, 409)],
    [
      "an error event ai_disabled",
      (request) => {
        const stream = fakeEventStream();
        stream.send(errorEvent("ai_disabled"));
        stream.close();
        return stream.response(request);
      },
    ],
  ])("recognises %s as ai-disabled after one request", async (_name, handler) => {
    const fetchCount = serverAnswering(handler);
    const { result } = renderHook(() => useAnswerStream());

    act(() => {
      result.current.ask(REQUEST);
    });
    await waitFor(() => {
      expect(result.current.state.phase).toBe("error");
    });

    expect(result.current.state).toMatchObject({ failure: { cause: "ai-disabled" } });
    expect(fetchCount()).toBe(1);
  });

  it("gives an error event with its fixed code", async () => {
    const { stream } = fakeStreamServer();
    const { result } = renderHook(() => useAnswerStream());

    act(() => {
      result.current.ask(REQUEST);
    });
    stream.send(sourcesEvent() + deltaEvent("Some text") + errorEvent("model_unavailable", "The model is not there."));
    stream.close();
    await waitFor(() => {
      expect(result.current.state.phase).toBe("error");
    });

    expect(result.current.state).toMatchObject({
      text: "Some text",
      verified: false,
      failure: { cause: "stream", code: "model_unavailable", detail: "The model is not there." },
    });
  });

  it.each([
    ["a wrong type", sourcesEvent() + 'data: {"type":"progress","text":"a"}\n\n'],
    ["an unknown status", sourcesEvent() + doneEvent({ status: "probably" })],
  ])("ends with invalid-answer on %s", async (_name, text) => {
    const { stream } = fakeStreamServer();
    const { result } = renderHook(() => useAnswerStream());

    act(() => {
      result.current.ask(REQUEST);
    });
    stream.send(text);
    await waitFor(() => {
      expect(result.current.state.phase).toBe("error");
    });

    expect(result.current.state).toMatchObject({ failure: { cause: "invalid-answer" }, verified: false });
  });
});

describe("answerStreamReducer", () => {
  const streaming = answerStreamReducer(initialAnswerStreamState, { type: "start" });

  it("replaces the streamed text with final_text on done", () => {
    const withText = answerStreamReducer(streaming, { type: "event", event: { type: "delta", text: "Unchecked [9]" } });
    const done = answerStreamReducer(withText, {
      type: "event",
      event: { type: "done", status: "answered", cited: [1], removed_sentences: 1, final_text: "Checked [1]." },
    });

    expect(withText).toMatchObject({ text: "Unchecked [9]", verified: false });
    expect(done).toMatchObject({ phase: "done", text: "Checked [1].", verified: true, removedSentences: 1 });
  });

  it("ignores events and outcomes when not streaming", () => {
    const delta = { type: "event", event: { type: "delta", text: "x" } } as const;
    const finish = { type: "finish", outcome: { kind: "interrupted" } } as const;

    expect(answerStreamReducer(initialAnswerStreamState, delta)).toBe(initialAnswerStreamState);
    expect(answerStreamReducer(initialAnswerStreamState, finish)).toBe(initialAnswerStreamState);
    expect(answerStreamReducer(initialAnswerStreamState, { type: "cancel" })).toBe(initialAnswerStreamState);
    expect(answerStreamReducer(streaming, { type: "start" })).toBe(streaming);
  });

  it.each<[AnswerStreamOutcome, unknown]>([
    [{ kind: "aborted" }, { phase: "idle", cancelled: true }],
    [{ kind: "interrupted" }, { phase: "error", failure: { cause: "interrupted" } }],
    [{ kind: "ai-disabled" }, { phase: "error", failure: { cause: "ai-disabled" } }],
    [
      { kind: "stream-error", code: "timeout", detail: "Too slow." },
      { phase: "error", failure: { cause: "stream", code: "timeout" } },
    ],
    [
      { kind: "failed", error: new ApiError("network", null, null), code: null },
      { phase: "error", failure: { cause: "network" } },
    ],
    [
      { kind: "failed", error: new ApiError("invalid-answer", 200, null), code: null },
      { phase: "error", failure: { cause: "invalid-answer" } },
    ],
    [
      { kind: "failed", error: new ApiError("http", 403, null), code: null },
      { phase: "error", failure: { cause: "forbidden" } },
    ],
    [
      { kind: "failed", error: new ApiError("http", 409, "Busy."), code: "answer_in_progress" },
      { phase: "error", failure: { cause: "http", code: "answer_in_progress" } },
    ],
  ])("maps the outcome %j", (outcome, expected) => {
    expect(answerStreamReducer(streaming, { type: "finish", outcome })).toMatchObject(expected as object);
  });
});
