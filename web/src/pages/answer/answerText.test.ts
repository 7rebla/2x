import { describe, expect, it } from "vitest";

import { type AnswerPiece, answerPieces } from "./answerText.ts";

function joined(pieces: readonly AnswerPiece[]): string {
  return pieces.map((piece) => piece.text).join("");
}

describe("answerPieces", () => {
  it("cuts single numbers into citation pieces", () => {
    expect(answerPieces("The check is due yearly [2]. Next [10].")).toEqual([
      { kind: "text", text: "The check is due yearly " },
      { kind: "citation", n: 2, text: "[2]" },
      { kind: "text", text: ". Next " },
      { kind: "citation", n: 10, text: "[10]" },
      { kind: "text", text: "." },
    ]);
  });

  it("splits a bracket with several numbers and keeps brackets and separators as text", () => {
    expect(answerPieces("Both [1, 3] and [2;4].")).toEqual([
      { kind: "text", text: "Both [" },
      { kind: "citation", n: 1, text: "1" },
      { kind: "text", text: ", " },
      { kind: "citation", n: 3, text: "3" },
      { kind: "text", text: "] and [" },
      { kind: "citation", n: 2, text: "2" },
      { kind: "text", text: ";" },
      { kind: "citation", n: 4, text: "4" },
      { kind: "text", text: "]." },
    ]);
  });

  it("accepts spaces inside a bracket, as the server does", () => {
    expect(answerPieces("[ 5 ]")).toEqual([{ kind: "citation", n: 5, text: "[ 5 ]" }]);
  });

  it("leaves everything else as text: words, empty brackets, too many digits, markup", () => {
    for (const text of [
      "No source here.",
      "Empty [] and [a] and [1a].",
      "Seven digits [1234567].",
      "Range [1-2].",
      '<img src=x onerror="alert(1)"> [link](https://example.invalid/)',
    ]) {
      expect(answerPieces(text)).toEqual([{ kind: "text", text }]);
    }
  });

  it("gives nothing for an empty text and the text back when joined", () => {
    expect(answerPieces("")).toEqual([]);
    for (const text of ["[1][2]", "A [1, 2]\nB [3]", "Emoji 😀 before [7] and after."]) {
      expect(joined(answerPieces(text))).toBe(text);
    }
  });

  it("finds adjacent brackets as separate citations", () => {
    expect(answerPieces("[1][2]")).toEqual([
      { kind: "citation", n: 1, text: "[1]" },
      { kind: "citation", n: 2, text: "[2]" },
    ]);
  });
});
