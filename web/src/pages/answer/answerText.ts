// The answer text cut into plain text and source numbers (work order 132).
//
// The model cites a source as "[2]", several as "[2, 3]" or "[2; 3]" (the
// pattern of the citation check, backend/twox/answers/citations.py). The page
// turns a number into a link only when the server confirmed it (`cited` of
// `done`); this file only finds the numbers. Nothing here reads the text as
// HTML or Markdown: every piece stays a plain string, and joining the texts
// of all pieces gives the answer back unchanged.

/** A run of plain text, or one source number with the characters that show it. */
export type AnswerPiece =
  | { readonly kind: "text"; readonly text: string }
  | { readonly kind: "citation"; readonly n: number; readonly text: string };

/** "[2]", "[2, 3]", "[2;3]": one to six digits per number, as the server checks them. */
const CITATION = /\[[ \t]*\d{1,6}(?:[ \t]*[,;][ \t]*\d{1,6})*[ \t]*\]/g;
const NUMBER = /\d{1,6}/g;

function pushText(pieces: AnswerPiece[], text: string): void {
  if (text === "") {
    return;
  }
  const last = pieces.at(-1);
  if (last?.kind === "text") {
    pieces[pieces.length - 1] = { kind: "text", text: last.text + text };
  } else {
    pieces.push({ kind: "text", text });
  }
}

/**
 * The pieces of `text`. A bracket with one number is one citation piece
 * ("[2]"); in a bracket with several numbers each number is a citation piece
 * of its own and the brackets and separators are text ("[", "2", ", ", "3", "]").
 */
export function answerPieces(text: string): AnswerPiece[] {
  const pieces: AnswerPiece[] = [];
  let position = 0;
  for (const bracket of text.matchAll(CITATION)) {
    const start = bracket.index;
    const group = bracket[0];
    pushText(pieces, text.slice(position, start));
    position = start + group.length;
    const numbers = [...group.matchAll(NUMBER)];
    const [only] = numbers;
    if (numbers.length === 1 && only !== undefined) {
      pieces.push({ kind: "citation", n: Number(only[0]), text: group });
      continue;
    }
    let inner = 0;
    for (const number of numbers) {
      pushText(pieces, group.slice(inner, number.index));
      pieces.push({ kind: "citation", n: Number(number[0]), text: number[0] });
      inner = number.index + number[0].length;
    }
    pushText(pieces, group.slice(inner));
  }
  pushText(pieces, text.slice(position));
  return pieces;
}
