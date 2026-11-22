import { describe, expect, it } from "vitest";

import { ApiError } from "../../api/errors.ts";
import type { AnswerStatus } from "../../api/generated";
import { answerRequest, NO_SCOPE, questionLength } from "./AnswerForm.tsx";
import { availabilityOf, citationTargets, citedSources, isEvidence, statusKeyOf } from "./answerView.ts";
import { answerSource } from "./testData.ts";
import { type AnswerStreamState, initialAnswerStreamState } from "./useAnswerStream.ts";

const AVAILABLE: AnswerStatus = { enabled: true, chat_model_configured: true, available: true };
const STREAMING: AnswerStreamState = { phase: "streaming", sources: null, text: "", verified: false };

function failed(failure: Extract<AnswerStreamState, { phase: "error" }>["failure"]): AnswerStreamState {
  return { phase: "error", sources: null, text: "", verified: false, failure };
}

describe("availabilityOf", () => {
  it("follows the status", () => {
    expect(availabilityOf(AVAILABLE, false, initialAnswerStreamState)).toBe("available");
    expect(availabilityOf({ ...AVAILABLE, enabled: false }, false, initialAnswerStreamState)).toBe("off");
    expect(availabilityOf({ ...AVAILABLE, chat_model_configured: false }, false, initialAnswerStreamState)).toBe(
      "unavailable",
    );
    expect(availabilityOf({ ...AVAILABLE, available: false }, false, initialAnswerStreamState)).toBe("unavailable");
  });

  it("waits for the status, but lets the server decide when the status cannot be read", () => {
    expect(availabilityOf(undefined, false, initialAnswerStreamState)).toBe("pending");
    expect(availabilityOf(undefined, true, initialAnswerStreamState)).toBe("available");
  });

  it("takes a refusal of the stream over the status", () => {
    expect(availabilityOf(AVAILABLE, false, failed({ cause: "ai-disabled" }))).toBe("off");
    const refused = new ApiError("http", 503, "No chat model.");
    expect(availabilityOf(AVAILABLE, false, failed({ cause: "http", error: refused, code: "chat_not_configured" }))).toBe(
      "unavailable",
    );
    expect(availabilityOf(AVAILABLE, false, failed({ cause: "interrupted" }))).toBe("available");
  });
});

describe("statusKeyOf", () => {
  it("names only changes of state", () => {
    expect(statusKeyOf(initialAnswerStreamState)).toBeNull();
    expect(statusKeyOf({ phase: "idle", cancelled: true, sources: null, text: "", verified: false })).toBe("cancelled");
    expect(statusKeyOf(STREAMING)).toBe("searching");
    expect(statusKeyOf({ ...STREAMING, sources: [] })).toBe("writing");
    expect(
      statusKeyOf({
        phase: "done",
        sources: [],
        text: "",
        verified: true,
        status: "answered",
        cited: [],
        removedSentences: 0,
      }),
    ).toBe("done");
    expect(statusKeyOf(failed({ cause: "interrupted" }))).toBeNull();
  });
});

describe("sources", () => {
  it("counts a source with a page or a heading path as evidence, not one without both", () => {
    expect(isEvidence({ page_start: 3, heading_path: [] })).toBe(true);
    expect(isEvidence({ page_start: null, heading_path: ["Setup"] })).toBe(true);
    expect(isEvidence({ page_start: null, heading_path: [] })).toBe(false);
    expect(isEvidence({ page_start: null, heading_path: [" ", ""] })).toBe(false);
  });

  it("keeps the cited sources in the order of their numbers and links only evidence", () => {
    const sources = [
      answerSource(3),
      answerSource(1),
      answerSource(2, { page_start: null, page_end: null, heading_path: [] }),
      answerSource(4),
    ];
    expect(citedSources(sources, [2, 1, 3, 9]).map((source) => source.n)).toEqual([1, 2, 3]);
    expect([...citationTargets(sources, [2, 1, 3, 9]).keys()]).toEqual([1, 3]);
    expect(citationTargets(sources, []).size).toBe(0);
  });
});

describe("the request of the form", () => {
  it("trims the question and leaves an empty limit out", () => {
    expect(answerRequest("  Test question?\n", NO_SCOPE)).toEqual({ question: "Test question?" });
    expect(answerRequest("Q", { device: [4], plant: [] })).toEqual({ question: "Q", device: [4] });
    expect(answerRequest("Q", { device: [], plant: [2, 3] })).toEqual({ question: "Q", plant: [2, 3] });
  });

  it("counts characters like the server: trimmed, by code point", () => {
    expect(questionLength("  abc  ")).toBe(3);
    expect(questionLength("😀😀")).toBe(2);
  });
});
