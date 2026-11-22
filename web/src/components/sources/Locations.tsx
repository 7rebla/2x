// The places a section is stored at: file (link), version and file name,
// "Older version", device (link) and plant (work order 054). The first place
// is always shown; further places (the same file on more devices) are behind a
// "+N more devices" button (work order 087). Shared by the search and the
// answer page since work order 132.
//
// Titles, file names, device and plant names are data: React renders them as
// text and they never go through the interpolation of i18next.
import { type ReactElement, useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import type { SearchLocation } from "../../api/generated";
import { Icon } from "../../icons/Icon.tsx";
import { devicePath, documentPath } from "../files/format.ts";
import { Button } from "../ui/Button.tsx";

const LINK_CLASS = "text-accent underline hover:text-accent-strong";

export function LocationView({ location }: { location: SearchLocation }): ReactElement {
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
          className="inline-flex items-center gap-1 rounded border border-warning-line bg-warning-soft px-1.5 text-meta text-warning"
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

/** The places of a section: the first one, the others behind a button that opens and closes them. */
export function Locations({ locations }: { locations: readonly SearchLocation[] }): ReactElement {
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
