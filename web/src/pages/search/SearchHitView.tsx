// One hit of the search page (work order 054): page or pages, heading path,
// how it was found, the snippet with the found places marked, and the places
// the text is stored at (file, version, device, plant) with links. The first
// place is always shown; further places (the same file on more devices) are
// behind a "+N more devices" button (work order 087), so they do not push the
// snippet away.
//
// Everything from the hit (snippet, headings, titles, file names, device and
// plant names) is data: React renders it as text, never as HTML, and it never
// goes through the interpolation of i18next.
import { type ReactElement, useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import type { MatchKindsEnum, SearchHit, SearchLocation } from "../../api/generated";
import { devicePath, documentPath } from "../../components/files/format.ts";
import { Button } from "../../components/ui/Button.tsx";
import { Icon } from "../../icons/Icon.tsx";
import { pageRange, snippetPieces } from "./snippet.ts";

const LINK_CLASS = "text-accent underline hover:text-accent-strong";

/** Order of the kinds of a hit, as the API ranks them. */
const MATCH_KIND_ORDER: readonly MatchKindsEnum[] = ["exact", "keyword", "semantic"];

/**
 * Classes of a found place in the snippet. No side padding (px-0): padding
 * inside a word such as "IP-Addresses" would show as gaps; box-decoration-clone
 * keeps the background on every line when a mark wraps.
 */
export const MARK_CLASS = "rounded-sm bg-accent-soft px-0 font-semibold text-fg box-decoration-clone";

/** The snippet as text nodes, the found places in <mark>. */
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
        // The short name stays visible; the explanation is the tooltip and is
        // read out after the name.
        <li
          key={kind}
          data-testid="search-match-kind-item"
          title={t(`matchKind.hint.${kind}`)}
          className="cursor-help rounded-full border border-line-strong bg-surface-muted px-2 text-xs text-fg-muted"
        >
          <span data-testid="search-match-kind" data-kind={kind}>
            {t(`matchKind.${kind}`)}
          </span>
          <span className="sr-only">: {t(`matchKind.hint.${kind}`)}</span>
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

function locationKey(location: SearchLocation, index: number): string {
  return `${String(location.version.id)}-${String(location.device.id)}-${String(index)}`;
}

/**
 * How the button names the hidden places: "devices" when every place is on a
 * device of its own (the usual case: one file stored for several devices),
 * else "places" (a device holds the text in more than one file or version).
 */
export function hiddenPlacesKind(locations: readonly SearchLocation[]): "devices" | "places" {
  const devices = new Set(locations.map((location) => location.device.id));
  return devices.size === locations.length ? "devices" : "places";
}

/** The places of a hit: the first one, the others behind a button that opens and closes them. */
function Locations({ locations }: { locations: readonly SearchLocation[] }): ReactElement {
  const { t } = useTranslation("search");
  const [open, setOpen] = useState(false);
  const listId = useId();
  const hidden = locations.length - 1;
  const shown = open ? locations : locations.slice(0, 1);
  return (
    <div className="border-t border-line">
      <ul id={listId} aria-label={t("locations")} className="divide-y divide-line">
        {shown.map((location, index) => (
          <LocationView key={locationKey(location, index)} location={location} />
        ))}
      </ul>
      {hidden > 0 ? (
        <Button
          type="button"
          size="sm"
          variant="ghost"
          data-testid="search-more-locations"
          aria-expanded={open}
          aria-controls={listId}
          className="-ml-2"
          onClick={() => {
            setOpen(!open);
          }}
        >
          {open ? t("moreLocations.hide") : t(`moreLocations.${hiddenPlacesKind(locations)}`, { count: hidden })}
        </Button>
      ) : null}
    </div>
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
      <Locations locations={hit.locations} />
    </li>
  );
}
