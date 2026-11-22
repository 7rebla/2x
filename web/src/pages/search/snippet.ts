// Pieces of a search snippet with the found places marked (work order 054).
//
// The API sends the snippet as plain text and the found places as
// {start, end} in Unicode code points (Python string positions, work order
// 052). JavaScript strings count UTF-16 units, so the snippet is split into
// code points with Array.from first; otherwise every mark after a character
// outside the Basic Multilingual Plane (an emoji, for example) would slip.
// The pieces are rendered as text; nothing here produces HTML.
import type { SearchHighlight } from "../../api/generated";

/** A run of snippet text, marked when it is a found place. */
export interface SnippetPiece {
  readonly text: string;
  readonly marked: boolean;
}

/**
 * The snippet cut into marked and unmarked pieces, in order. Places outside
 * the snippet are clipped, empty or reversed places are dropped, and
 * overlapping or touching places are merged. Joining all pieces gives the
 * snippet back unchanged.
 */
export function snippetPieces(snippet: string, highlights: readonly SearchHighlight[]): SnippetPiece[] {
  const points = Array.from(snippet);
  const ranges = highlights
    .map(({ start, end }) => ({
      start: Math.max(0, Math.min(points.length, Math.trunc(start))),
      end: Math.max(0, Math.min(points.length, Math.trunc(end))),
    }))
    .filter(({ start, end }) => Number.isFinite(start) && Number.isFinite(end) && end > start)
    .sort((a, b) => a.start - b.start || a.end - b.end);

  const merged: { start: number; end: number }[] = [];
  for (const range of ranges) {
    const last = merged.at(-1);
    if (last !== undefined && range.start <= last.end) {
      last.end = Math.max(last.end, range.end);
    } else {
      merged.push({ ...range });
    }
  }

  const pieces: SnippetPiece[] = [];
  let position = 0;
  for (const { start, end } of merged) {
    if (start > position) {
      pieces.push({ text: points.slice(position, start).join(""), marked: false });
    }
    pieces.push({ text: points.slice(start, end).join(""), marked: true });
    position = end;
  }
  if (position < points.length) {
    pieces.push({ text: points.slice(position).join(""), marked: false });
  }
  return pieces;
}

/** The page range of a hit: [start] for one page, [start, end] for several, null without a page. */
export function pageRange(pageStart: number | null, pageEnd: number | null): readonly [number] | readonly [number, number] | null {
  if (pageStart === null) {
    return null;
  }
  if (pageEnd === null || pageEnd <= pageStart) {
    return [pageStart];
  }
  return [pageStart, pageEnd];
}
