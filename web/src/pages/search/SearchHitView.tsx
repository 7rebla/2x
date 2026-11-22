// One hit of the search page (work order 054): page or pages, heading path,
// how it was found, the snippet with the found places marked, and the places
// the text is stored at (file, version, device, plant) with links. The first
// place is always shown; further places (the same file on more devices) are
// behind a "+N more devices" button (work order 087), so they do not push the
// snippet away. Page, snippet and places are building blocks in
// components/sources/ (work order 132), shared with the answer page.
//
// Everything from the hit (snippet, headings, titles, file names, device and
// plant names) is data: React renders it as text, never as HTML, and it never
// goes through the interpolation of i18next.
import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";

import type { MatchKindsEnum, SearchHit } from "../../api/generated";
import { Locations, PageLabel, Snippet } from "../../components/sources";

/** Order of the kinds of a hit, as the API ranks them. */
const MATCH_KIND_ORDER: readonly MatchKindsEnum[] = ["exact", "keyword", "semantic"];

function MatchKinds({ kinds }: { kinds: readonly MatchKindsEnum[] }): ReactElement {
  const { t } = useTranslation("search");
  const shown = MATCH_KIND_ORDER.filter((kind) => kinds.includes(kind));
  return (
    <ul aria-label={t("matchKind.label")} className="flex flex-wrap gap-1 sm:ml-auto">
      {shown.map((kind) => (
        // The short name stays visible; the explanation is its tooltip (on the
        // name, so the list item gets no accessible name of its own) and is
        // read out once, after the name.
        <li
          key={kind}
          data-testid="search-match-kind-item"
          className="cursor-help rounded-full border border-line-strong bg-surface-muted px-2 text-meta text-fg-muted"
        >
          <span data-testid="search-match-kind" data-kind={kind} title={t(`matchKind.hint.${kind}`)}>
            {t(`matchKind.${kind}`)}
          </span>
          <span className="sr-only">: {t(`matchKind.hint.${kind}`)}</span>
        </li>
      ))}
    </ul>
  );
}

/** A hit as a card. */
export function SearchHitView({ hit }: { hit: SearchHit }): ReactElement {
  const { t } = useTranslation("search");
  const headingPath = hit.heading_path.filter((heading) => heading.trim() !== "");
  return (
    <li
      data-testid="search-hit"
      data-section={hit.section_id}
      className="space-y-2 rounded border border-line bg-surface p-4"
    >
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm text-fg-muted">
        <PageLabel pages={hit} />
        {headingPath.length === 0 ? null : (
          <span data-testid="search-hit-heading-path" className="break-words">
            <span className="sr-only">{t("headingPath")}: </span>
            {headingPath.join(" › ")}
          </span>
        )}
        <MatchKinds kinds={hit.match_kinds} />
      </div>
      <Snippet hit={hit} />
      <Locations locations={hit.locations} />
    </li>
  );
}
