// The text of a section as a snippet, with found places marked (work order
// 054; shared by the search and the answer page since work order 132). The
// snippet is data: React renders it as text, never as HTML.
import type { ReactElement } from "react";

import type { SearchHit } from "../../api/generated";
import { snippetPieces } from "./snippet.ts";

/**
 * Classes of a found place in the snippet. No side padding (px-0): padding
 * inside a word such as "IP-Addresses" would show as gaps; box-decoration-clone
 * keeps the background on every line when a mark wraps.
 */
export const MARK_CLASS = "rounded-sm bg-accent-soft px-0 font-semibold text-fg box-decoration-clone";

/** The snippet as text nodes, the found places in <mark> (none with empty `highlights`). */
export function Snippet({ hit }: { hit: Pick<SearchHit, "snippet" | "highlights"> }): ReactElement {
  return (
    <p data-testid="search-snippet" className="leading-relaxed break-words">
      {snippetPieces(hit.snippet, hit.highlights).map((piece, index) =>
        piece.marked ? (
          <mark key={index} className={MARK_CLASS}>
            {piece.text}
          </mark>
        ) : (
          piece.text
        ),
      )}
    </p>
  );
}
