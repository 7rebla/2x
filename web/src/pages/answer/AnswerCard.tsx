// The answer of the answer page (work order 132).
//
// - While it streams, the collected text stands in an article with
//   aria-busy="true" and without aria-live; no typing animation. Numbers are
//   plain text then: nothing is a link before the server has checked it.
// - After `done` the checked text replaces the pieces (D9). A number links to
//   its source only if `cited` holds it and the source is evidence (page or
//   heading path); every other number stays text.
// - The text is data (guard rail 4): rendered as text only, no HTML, no
//   Markdown, no links of its own, never through the interpolation of i18next.
import type { MouseEvent, ReactElement } from "react";
import { useTranslation } from "react-i18next";

import type { AnswerSource } from "../../api/generated";
import { pageRange } from "../../components/sources";
import { Icon } from "../../icons/Icon.tsx";
import type { IconName } from "../../icons/names.ts";
import { answerPieces } from "./answerText.ts";
import { headingsOf } from "./answerView.ts";
import { sourceAnchor } from "./SourceList.tsx";

const LINK_CLASS = "font-semibold text-accent underline hover:text-accent-strong tabular-nums";

/** "Source 2: Test manual, page 14"; a Markdown source names its headings in place of the page. */
function useCitationName(): (source: AnswerSource) => string {
  const { t } = useTranslation("answers");
  return (source) => {
    const title = source.locations[0]?.document_title ?? "";
    const range = pageRange(source.page_start, source.page_end);
    let where: string;
    if (range === null) {
      where = headingsOf(source).join(" › ");
    } else if (range.length === 1) {
      where = t("citation.page", { page: range[0] });
    } else {
      where = t("citation.pages", { start: range[0], end: range[1] });
    }
    // Title and headings are data: joined here, not handed to i18next.
    return `${t("sources.source", { n: source.n })}: ${title}, ${where}`;
  };
}

/** Moves to the card of a source without changing the address. */
function jumpToSource(event: MouseEvent<HTMLAnchorElement>, n: number): void {
  const card = document.getElementById(sourceAnchor(n));
  if (card === null) {
    return;
  }
  event.preventDefault();
  // Focusing scrolls the card into view; the address keeps no #hash, so Back
  // leaves the page instead of jumping between sources.
  card.focus();
}

/** The text with links to the sources in `targets`; null: no links at all (not checked yet). */
function AnswerText({
  text,
  targets,
}: {
  text: string;
  targets: ReadonlyMap<number, AnswerSource> | null;
}): ReactElement {
  const citationName = useCitationName();
  return (
    <div data-testid="answer-text" className="leading-relaxed break-words whitespace-pre-line">
      {targets === null
        ? text
        : answerPieces(text).map((piece, index) => {
            const source = piece.kind === "citation" ? targets.get(piece.n) : undefined;
            if (source === undefined) {
              return piece.text;
            }
            return (
              <a
                key={index}
                href={`#${sourceAnchor(source.n)}`}
                data-testid="answer-citation"
                aria-label={citationName(source)}
                className={LINK_CLASS}
                onClick={(event) => {
                  jumpToSource(event, source.n);
                }}
              >
                {piece.text}
              </a>
            );
          })}
    </div>
  );
}

export interface AnswerCardProps {
  readonly text: string;
  /** The answer streams: aria-busy, no links. */
  readonly busy: boolean;
  /** Line above the text: icon and short label. */
  readonly label: { readonly icon: IconName; readonly text: string };
  /** Links of a checked answer; null before `done`. */
  readonly targets: ReadonlyMap<number, AnswerSource> | null;
  /** Further lines below the text (statements removed, cancelled). */
  readonly notes?: readonly string[];
}

/** The answer as an article (no chat bubble, no avatar, D17). */
export function AnswerCard({ text, busy, label, targets, notes = [] }: AnswerCardProps): ReactElement {
  const { t } = useTranslation("answers");
  return (
    <article
      aria-label={t("answer.label")}
      aria-busy={busy}
      data-testid="answer-card"
      className="max-w-prose space-y-3 rounded border border-line bg-surface p-4"
    >
      <p data-testid="answer-label" className="flex items-center gap-2 text-sm text-fg-muted">
        <Icon name={label.icon} decorative />
        {label.text}
      </p>
      <AnswerText text={text} targets={targets} />
      {notes.map((note) => (
        <p key={note} data-testid="answer-note" className="flex items-center gap-2 text-sm text-fg-muted">
          <Icon name="info" decorative />
          {note}
        </p>
      ))}
    </article>
  );
}
