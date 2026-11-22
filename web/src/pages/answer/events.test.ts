import { describe, expect, it } from "vitest";

import { parseAnswerEvent, toAnswerRefusalCode, toSearchLocation } from "./events.ts";
import { answerLocation, answerSource } from "./testData.ts";

describe("parseAnswerEvent", () => {
  it("accepts the four events of the contract", () => {
    const sources = [answerSource(1), answerSource(2, { page_start: null, page_end: null })];

    expect(parseAnswerEvent({ type: "sources", sources })).toEqual({ type: "sources", sources });
    expect(parseAnswerEvent({ type: "sources", sources: [] })).toEqual({ type: "sources", sources: [] });
    expect(parseAnswerEvent({ type: "delta", text: "Part [1]" })).toEqual({ type: "delta", text: "Part [1]" });
    expect(
      parseAnswerEvent({ type: "done", status: "no_evidence", cited: [], removed_sentences: 2, final_text: "x" }),
    ).toEqual({ type: "done", status: "no_evidence", cited: [], removed_sentences: 2, final_text: "x" });
    expect(parseAnswerEvent({ type: "error", code: "timeout", detail: "Too slow." })).toEqual({
      type: "error",
      code: "timeout",
      detail: "Too slow.",
    });
  });

  it("drops unknown extra fields", () => {
    expect(parseAnswerEvent({ type: "delta", text: "a", extra: "<b>" })).toEqual({ type: "delta", text: "a" });
  });

  it("keeps text as it is, markup included", () => {
    const text = '<img src=x onerror="alert(1)"> **bold** [1](https://example.invalid)';

    expect(parseAnswerEvent({ type: "delta", text })).toEqual({ type: "delta", text });
  });

  it.each([
    ["no object", "delta"],
    ["null", null],
    ["an array", [{ type: "delta", text: "a" }]],
    ["an unknown type", { type: "progress", text: "a" }],
    ["a delta without text", { type: "delta" }],
    ["a delta with a number", { type: "delta", text: 1 }],
    ["an unknown status", { type: "done", status: "maybe", cited: [], removed_sentences: 0, final_text: "" }],
    ["a status of another case", { type: "done", status: "ANSWERED", cited: [], removed_sentences: 0, final_text: "" }],
    ["cited with a string", { type: "done", status: "answered", cited: ["1"], removed_sentences: 0, final_text: "" }],
    ["cited with zero", { type: "done", status: "answered", cited: [0], removed_sentences: 0, final_text: "" }],
    ["negative removed_sentences", { type: "done", status: "answered", cited: [], removed_sentences: -1, final_text: "" }],
    ["fractional removed_sentences", { type: "done", status: "answered", cited: [], removed_sentences: 0.5, final_text: "" }],
    ["done without final_text", { type: "done", status: "answered", cited: [], removed_sentences: 0 }],
    ["an error without detail", { type: "error", code: "timeout" }],
    ["an error with a numeric code", { type: "error", code: 5, detail: "" }],
    ["sources that are no list", { type: "sources", sources: {} }],
    ["a source without places", { type: "sources", sources: [answerSource(1, { locations: [] })] }],
    ["a source with number 0", { type: "sources", sources: [answerSource(0)] }],
    ["a source with a page as text", { type: "sources", sources: [{ ...answerSource(1), page_start: "3" }] }],
    ["a source without snippet", { type: "sources", sources: [{ ...answerSource(1), snippet: undefined }] }],
    [
      "a place with a wrong field",
      { type: "sources", sources: [{ ...answerSource(1), locations: [{ ...answerLocation(), device_id: "1000" }] }] },
    ],
  ])("rejects %s", (_name, data) => {
    expect(parseAnswerEvent(data)).toBeNull();
  });

  it("treats an unknown error code as internal", () => {
    expect(parseAnswerEvent({ type: "error", code: "new_code", detail: "Something new." })).toEqual({
      type: "error",
      code: "internal",
      detail: "Something new.",
    });
  });
});

describe("toAnswerRefusalCode", () => {
  it("knows the refusals before the stream and nothing else", () => {
    expect(["ai_disabled", "answer_in_progress", "chat_not_configured"].map(toAnswerRefusalCode)).toEqual([
      "ai_disabled",
      "answer_in_progress",
      "chat_not_configured",
    ]);
    expect([undefined, null, "timeout", 409].map(toAnswerRefusalCode)).toEqual([null, null, null, null]);
  });
});

describe("toSearchLocation", () => {
  it("turns the flat place of a source into the place of a search hit", () => {
    expect(toSearchLocation(answerLocation())).toEqual({
      document: { id: 7, title: "Test manual" },
      version: { id: 71, number: 2, original_filename: "test-manual-v2.pdf", is_latest: true },
      device: { id: 1000, key: "test-plc-1", name: "Test controller" },
      plant: { id: 100, key: "test-plant-1", name: "Test plant one" },
    });
  });
});
