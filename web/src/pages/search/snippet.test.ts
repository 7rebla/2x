import { describe, expect, it } from "vitest";

import { pageRange, snippetPieces } from "./snippet.ts";

function marked(snippet: string, highlights: { start: number; end: number }[]): string[] {
  return snippetPieces(snippet, highlights)
    .filter((piece) => piece.marked)
    .map((piece) => piece.text);
}

describe("snippetPieces", () => {
  it("cuts the snippet into unmarked and marked pieces", () => {
    expect(snippetPieces("The inspection is due.", [{ start: 4, end: 14 }])).toEqual([
      { text: "The ", marked: false },
      { text: "inspection", marked: true },
      { text: " is due.", marked: false },
    ]);
  });

  it("gives the whole snippet unmarked without places, and nothing for an empty snippet", () => {
    expect(snippetPieces("Plain text.", [])).toEqual([{ text: "Plain text.", marked: false }]);
    expect(snippetPieces("", [{ start: 0, end: 3 }])).toEqual([]);
  });

  it("counts Unicode code points, so a mark after an emoji does not slip", () => {
    // Each emoji is one code point but two UTF-16 units.
    const snippet = "\u{1F600}\u{1F600} check the inspection now";
    expect(snippet.indexOf("inspection")).toBe(15);
    expect(marked(snippet, [{ start: 13, end: 23 }])).toEqual(["inspection"]);
  });

  it("marks characters outside the Basic Multilingual Plane as a whole", () => {
    const snippet = "Symbol \u{1D538} and the word";
    expect(marked(snippet, [{ start: 7, end: 8 }])).toEqual(["\u{1D538}"]);
    expect(marked(snippet, [{ start: 17, end: 21 }])).toEqual(["word"]);
  });

  it("marks several places in order, also when they arrive unsorted", () => {
    const snippet = "alpha beta gamma delta";
    expect(
      marked(snippet, [
        { start: 17, end: 22 },
        { start: 0, end: 5 },
        { start: 11, end: 16 },
      ]),
    ).toEqual(["alpha", "gamma", "delta"]);
  });

  it("merges overlapping and touching places", () => {
    const snippet = "abcdefghij";
    expect(marked(snippet, [{ start: 1, end: 4 }, { start: 3, end: 6 }])).toEqual(["bcdef"]);
    expect(marked(snippet, [{ start: 0, end: 2 }, { start: 2, end: 3 }])).toEqual(["abc"]);
  });

  it("clips places outside the snippet and drops empty or reversed ones", () => {
    const snippet = "short";
    expect(marked(snippet, [{ start: 3, end: 99 }])).toEqual(["rt"]);
    expect(marked(snippet, [{ start: -4, end: 2 }])).toEqual(["sh"]);
    expect(marked(snippet, [{ start: 2, end: 2 }, { start: 4, end: 1 }, { start: 10, end: 12 }])).toEqual([]);
  });

  it("always gives back the whole snippet when the pieces are joined", () => {
    const snippet = "\u{1F600} a <b>tag</b> & \u{1D538} text";
    const pieces = snippetPieces(snippet, [{ start: 4, end: 14 }, { start: 17, end: 18 }]);
    expect(pieces.map((piece) => piece.text).join("")).toBe(snippet);
    expect(pieces.filter((piece) => piece.marked).map((piece) => piece.text)).toEqual(["<b>tag</b>", "\u{1D538}"]);
  });
});

describe("pageRange", () => {
  it("gives one page, a range, or nothing", () => {
    expect(pageRange(31, 31)).toEqual([31]);
    expect(pageRange(31, null)).toEqual([31]);
    expect(pageRange(31, 32)).toEqual([31, 32]);
    expect(pageRange(null, null)).toBeNull();
    expect(pageRange(null, 4)).toBeNull();
  });
});
