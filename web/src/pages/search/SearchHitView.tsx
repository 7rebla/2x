// One hit of the search page (work order 054): page or pages, heading path,
// how it was found, the snippet with the found places marked, and every place
// the text is stored at (file, version, device, plant) with links.
//
// Everything from the hit (snippet, headings, titles, file names, device and
// plant names) is data: React renders it as text, never as HTML, and it never
// goes through the interpolation of i18next.
import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import type { MatchKindsEnum, SearchHit, SearchLocation } from "../../api/generated";
import { devicePath, documentPath } from "../../components/files/format.ts";
import { Icon } from "../../icons/Icon.tsx";
import { pageRange, snippetPieces } from "./snippet.ts";

const LINK_CLASS = "text-accent underline hover:text-accent-strong";

/** Order of the kinds of a hit, as the API ranks them. */
const MATCH_KIND_ORDER: readonly MatchKindsEnum[] = ["exact", "keyword", "semantic"];

/** The snippet as text nodes, the found places in <mark>. */
export function Snippet({ hit }: { hit: Pick<SearchHit, "snippet" | "highlights"> }): ReactElement {
  return (
    <p data-testid="search-snippet" className="leading-relaxed break-words">
      {snippetPieces(hit.snippet, hit.highlights).map((piece, index) =>
        piece.marked ? (
          <mark key={index} className="rounded-sm bg-accent-soft px-0.5 font-semibold text-fg">
            {piece.text}
          </mark>
        ) : (
          piece.text
        ),
      )}
    </p>
  );
}

function PageLabel({ hit }: { hit: SearchHit }): ReactElement | null {
  const { t } = useTranslation("search");
  const range = pageRange(hit.page_start, hit.page_end);
  if (range === null) {
    return null;
  }
  const text =
    range.length === 1
      ? t("page.one", { page: range[0] })
      : t("page.range", { start: range[0], end: range[1] });
  return (
    <span data-testid="search-hit-page" className="font-semibold text-fg tabular-nums">
      {text}
    </span>
  );
}

function MatchKinds({ kinds }: { kinds: readonly MatchKindsEnum[] }): ReactElement {
  const { t } = useTranslation("search");
  const shown = MATCH_KIND_ORDER.filter((kind) => kinds.includes(kind));
  return (
    <ul aria-label={t("matchKind.label")} className="flex flex-wrap gap-1 sm:ml-auto">
      {shown.map((kind) => (
        <li
          key={kind}
          data-testid="search-match-kind"
          data-kind={kind}
          className="rounded-full border border-line-strong bg-surface-muted px-2 text-xs text-fg-muted"
        >
          {t(`matchKind.${kind}`)}
        </li>
      ))}
    </ul>
  );
}

function LocationView({ location }: { location: SearchLocation }): ReactElement {
  const { t } = useTranslation("search");
  const { document, version, device, plant } = location;
  return (
    <li
      data-testid="search-location"
      data-latest={version.is_latest ? "true" : "false"}
      className="flex flex-wrap items-center gap-x-3 gap-y-1 py-1.5 text-sm"
    >
      <span className="inline-flex items-center gap-1">
        <Icon name="document" decorative />
        <Link to={documentPath(document.id)} className={LINK_CLASS} data-testid="search-location-document">
          {document.title}
        </Link>
      </span>
      <span className="inline-flex items-center gap-1 text-fg-muted">
        <Icon name="version" decorative />
        <span className="tabular-nums">{t("version", { number: version.number })}</span>
        <span aria-hidden="true">·</span>
        <span data-testid="search-location-filename" className="break-all">
          {version.original_filename}
        </span>
      </span>
      {version.is_latest ? null : (
        <span
          data-testid="search-older-version"
          title={t("olderVersionHint")}
          className="inline-flex items-center gap-1 rounded border border-warning-line bg-warning-soft px-1.5 text-xs text-warning"
        >
          <Icon name="warning" decorative />
          {t("olderVersion")}
        </span>
      )}
      <span className="inline-flex items-center gap-1">
        <Icon name="device" decorative />
        <span className="sr-only">{t("device")}: </span>
        <Link to={devicePath(device.id)} className={LINK_CLASS} data-testid="search-location-device">
          {device.name}
        </Link>
        <span className="text-fg-muted tabular-nums slashed-zero">({device.key})</span>
      </span>
      <span className="inline-flex items-center gap-1 text-fg-muted" data-testid="search-location-plant">
        <Icon name="plant" decorative />
        <span className="sr-only">{t("plant")}: </span>
        {plant.name}
      </span>
    </li>
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
        <PageLabel hit={hit} />
        {headingPath.length === 0 ? null : (
          <span data-testid="search-hit-heading-path" className="break-words">
            <span className="sr-only">{t("headingPath")}: </span>
            {headingPath.join(" › ")}
          </span>
        )}
        <MatchKinds kinds={hit.match_kinds} />
      </div>
      <Snippet hit={hit} />
      <ul aria-label={t("locations")} className="divide-y divide-line border-t border-line">
        {hit.locations.map((location, index) => (
          <LocationView key={`${String(location.version.id)}-${String(location.device.id)}-${String(index)}`} location={location} />
        ))}
      </ul>
    </li>
  );
}
