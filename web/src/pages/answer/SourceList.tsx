// The sources of a checked answer (work order 132): one card per source with
// its number, page or pages, heading path, snippet and the places it is stored
// at. A number in the answer text links to the card (`#source-n`), which takes
// the focus then (tabIndex -1).
//
// Everything from a source is data: React renders it as text, never as HTML,
// and it never goes through the interpolation of i18next.
import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";

import type { AnswerSource } from "../../api/generated";
import { Locations, PageLabel, Snippet } from "../../components/sources";
import { joinClasses } from "../../components/ui/classes.ts";
import { Icon } from "../../icons/Icon.tsx";
import { headingsOf, isEvidence } from "./answerView.ts";
import { toSearchLocation } from "./events.ts";

/** Id of the card of source `n`; the target of its citations. */
export function sourceAnchor(n: number): string {
  return `source-${String(n)}`;
}

function SourceCard({ source, contradicting }: { source: AnswerSource; contradicting: boolean }): ReactElement {
  const { t } = useTranslation(["answers", "search"]);
  const headings = headingsOf(source);
  const evidence = isEvidence(source);
  const marked = contradicting && evidence;
  return (
    <li
      id={sourceAnchor(source.n)}
      tabIndex={-1}
      data-testid="answer-source"
      data-n={source.n}
      data-contradicting={marked ? "true" : undefined}
      className={joinClasses(
        "scroll-mt-4 space-y-2 rounded border p-4",
        marked ? "border-2 border-warning bg-surface" : "border-line bg-surface",
      )}
    >
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm text-fg-muted">
        <span data-testid="answer-source-number" className="font-semibold text-fg tabular-nums">
          <span aria-hidden="true">[{source.n}]</span>
          <span className="sr-only">{t("answers:sources.source", { n: source.n })}</span>
        </span>
        <PageLabel pages={source} />
        {headings.length === 0 ? null : (
          <span data-testid="search-hit-heading-path" className="break-words">
            <span className="sr-only">{t("search:headingPath")}: </span>
            {headings.join(" › ")}
          </span>
        )}
        {evidence ? null : (
          <span data-testid="answer-source-without-page" className="inline-flex items-center gap-1">
            <Icon name="info" decorative />
            {t("answers:sources.withoutPage")}
          </span>
        )}
        {marked ? (
          <span
            data-testid="answer-source-contradiction"
            className="inline-flex items-center gap-1 rounded border border-warning-line bg-warning-soft px-1.5 text-meta text-warning"
          >
            <Icon name="contradiction" decorative />
            {t("answers:contradiction.place")}
          </span>
        ) : null}
      </div>
      <Snippet hit={{ snippet: source.snippet, highlights: [] }} />
      <Locations locations={source.locations.map(toSearchLocation)} />
    </li>
  );
}

/**
 * The list "Sources". With `contradiction` every source that is evidence is
 * marked: a contradiction is only reported when the answer cites at least two
 * sources, and those are the places that disagree.
 */
export function SourceList({
  sources,
  contradiction,
}: {
  sources: readonly AnswerSource[];
  contradiction: boolean;
}): ReactElement {
  const { t } = useTranslation("answers");
  return (
    <ol aria-label={t("sources.label")} data-testid="answer-sources" className="space-y-3">
      {sources.map((source) => (
        <SourceCard key={source.n} source={source} contradicting={contradiction} />
      ))}
    </ol>
  );
}
