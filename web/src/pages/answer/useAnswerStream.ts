// State of one answer of the answer page (work order 131): asks through
// api/answers.ts and keeps what the page shows. The page (work order 132)
// only renders this state.
//
// - `ask()` starts a stream from "idle", "done" or "error"; while one runs a
//   second call does nothing (the server allows one answer per user anyway).
// - Nothing is ever asked again on its own, not even after a network error.
// - `cancel()` and leaving the page (unmount) abort the stream; afterwards
//   nothing changes the state any more.
// - The text is a plain string: no HTML, no Markdown, `[n]` stays as it is.
//   While streaming it is provisional (`verified: false`); only `done` brings
//   the checked text, which replaces the pieces (D9 (a)).
import { useCallback, useEffect, useReducer, useRef } from "react";

import { type AnswerRequest, type AnswerStreamOutcome, streamAnswer } from "../../api/answers.ts";
import type { ApiError } from "../../api/errors.ts";
import type { AnswerSource } from "../../api/generated";
import type { AnswerErrorCode, AnswerEvent, AnswerRefusalCode, AnswerResultStatus } from "./events.ts";

/**
 * Why an answer failed:
 * - "ai-disabled": the AI features are off (409 before the stream, or an `error` event),
 * - "forbidden": 403 (the session code has been told through onForbidden),
 * - "http": another status outside 2xx (400 with the server's text, 409
 *   `answer_in_progress`, 429, 503 `chat_not_configured` …),
 * - "network": no answer from the server,
 * - "invalid-answer": an answer or event that does not match the contract,
 * - "interrupted": the stream ended without `done` or `error`,
 * - "stream": the server ended the answer with an `error` event.
 */
export type AnswerFailure =
  | { cause: "ai-disabled" }
  | { cause: "forbidden"; error: ApiError }
  | { cause: "http"; error: ApiError; code: AnswerRefusalCode | null }
  | { cause: "network"; error: ApiError }
  | { cause: "invalid-answer"; error: ApiError }
  | { cause: "interrupted" }
  | { cause: "stream"; code: Exclude<AnswerErrorCode, "ai_disabled">; detail: string };

interface AnswerContent {
  /** The sources of the `sources` event; null until it came. */
  sources: readonly AnswerSource[] | null;
  /** The answer text: the streamed pieces, or after `done` the checked text. */
  text: string;
  /** True only in "done": `text` is the checked answer. */
  verified: boolean;
}

export type AnswerStreamState =
  | ({ phase: "idle"; cancelled: boolean } & AnswerContent)
  | ({ phase: "streaming" } & AnswerContent)
  | ({
      phase: "done";
      status: AnswerResultStatus;
      /** Valid source numbers cited by the text. */
      cited: readonly number[];
      /** Sentences the citation check dropped or flagged. */
      removedSentences: number;
    } & AnswerContent)
  | ({ phase: "error"; failure: AnswerFailure } & AnswerContent);

export type AnswerStreamAction =
  | { type: "start" }
  | { type: "event"; event: AnswerEvent }
  | { type: "finish"; outcome: AnswerStreamOutcome }
  | { type: "cancel" };

export const initialAnswerStreamState: AnswerStreamState = {
  phase: "idle",
  cancelled: false,
  sources: null,
  text: "",
  verified: false,
};

function failureOf(outcome: AnswerStreamOutcome): AnswerFailure | null {
  switch (outcome.kind) {
    case "completed":
    case "aborted":
      return null;
    case "ai-disabled":
      return { cause: "ai-disabled" };
    case "interrupted":
      return { cause: "interrupted" };
    case "stream-error":
      return { cause: "stream", code: outcome.code, detail: outcome.detail };
    case "failed": {
      const { error } = outcome;
      if (error.kind === "network") {
        return { cause: "network", error };
      }
      if (error.kind === "invalid-answer") {
        return { cause: "invalid-answer", error };
      }
      if (error.status === 403) {
        return { cause: "forbidden", error };
      }
      return { cause: "http", error, code: outcome.code };
    }
  }
}

function applyEvent(state: AnswerStreamState & { phase: "streaming" }, event: AnswerEvent): AnswerStreamState {
  switch (event.type) {
    case "sources":
      return { ...state, sources: event.sources };
    case "delta":
      return { ...state, text: state.text + event.text };
    case "done":
      return {
        phase: "done",
        sources: state.sources,
        text: event.final_text,
        verified: true,
        status: event.status,
        cited: event.cited,
        removedSentences: event.removed_sentences,
      };
    case "error":
      return {
        phase: "error",
        sources: state.sources,
        text: state.text,
        verified: false,
        failure:
          event.code === "ai_disabled"
            ? { cause: "ai-disabled" }
            : { cause: "stream", code: event.code, detail: event.detail },
      };
  }
}

/** Pure state transition of the answer; events and outcomes count only while streaming. */
export function answerStreamReducer(state: AnswerStreamState, action: AnswerStreamAction): AnswerStreamState {
  switch (action.type) {
    case "start":
      return state.phase === "streaming" ? state : { phase: "streaming", sources: null, text: "", verified: false };
    case "event":
      return state.phase === "streaming" ? applyEvent(state, action.event) : state;
    case "finish": {
      if (state.phase !== "streaming") {
        return state;
      }
      if (action.outcome.kind === "aborted") {
        return { ...state, phase: "idle", cancelled: true, verified: false };
      }
      const failure = failureOf(action.outcome);
      // "completed" without a `done` event cannot happen; keep streaming rather than guess.
      return failure === null ? state : { ...state, phase: "error", verified: false, failure };
    }
    case "cancel":
      // The text so far stays visible but is not a checked answer.
      return state.phase === "streaming" ? { ...state, phase: "idle", cancelled: true, verified: false } : state;
  }
}

export interface AnswerStream {
  state: AnswerStreamState;
  /** Asks `request`; does nothing while an answer streams. */
  ask: (request: AnswerRequest) => void;
  /** Stops the running answer; the state goes back to "idle" with `cancelled`. */
  cancel: () => void;
}

/** One answer at a time, with cancel; aborted when the component unmounts. */
export function useAnswerStream(): AnswerStream {
  const [state, dispatch] = useReducer(answerStreamReducer, initialAnswerStreamState);
  /** Controller of the running stream; null when none runs. */
  const running = useRef<AbortController | null>(null);
  const mounted = useRef(false);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      running.current?.abort();
      running.current = null;
    };
  }, []);

  const ask = useCallback((request: AnswerRequest): void => {
    if (running.current !== null || !mounted.current) {
      return;
    }
    const controller = new AbortController();
    running.current = controller;
    // Only the stream of this call may change the state, and only while it is current.
    const current = (): boolean => mounted.current && running.current === controller;
    dispatch({ type: "start" });
    void streamAnswer(request, {
      signal: controller.signal,
      onEvent: (event) => {
        if (current()) {
          dispatch({ type: "event", event });
        }
      },
    }).then((outcome) => {
      if (current()) {
        running.current = null;
        dispatch({ type: "finish", outcome });
      }
    });
  }, []);

  const cancel = useCallback((): void => {
    const controller = running.current;
    if (controller === null) {
      return;
    }
    running.current = null;
    controller.abort();
    if (mounted.current) {
      dispatch({ type: "cancel" });
    }
  }, []);

  return { state, ask, cancel };
}
