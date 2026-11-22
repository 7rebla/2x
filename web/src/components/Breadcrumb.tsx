import type { ReactElement, ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import type { Device } from "../api/generated";
import { Icon } from "../icons/Icon.tsx";
import type { IconName } from "../icons/names.ts";
import { deviceClassIcon, PLANT_ICON } from "../pages/structure/deviceClass.ts";
import { devicePath } from "./files/format.ts";

// Breadcrumb of the device and the file page (work order 089): where an object
// sits in the structure, site › area › plant › device, and on the file page
// the file after it. Names come from the data and are rendered as text.

/** One level of a breadcrumb. */
export interface Crumb {
  /** React key; unique within the trail. */
  readonly key: string;
  /** Icon of the kind of the level (decorative; the text names the level). */
  readonly icon: IconName;
  readonly label: ReactNode;
  /** Address of the level; no link without one. The last level is never a link. */
  readonly to?: string;
  readonly testId?: string;
}

const LINK_CLASS = "text-accent underline hover:text-accent-strong";

/**
 * A breadcrumb: a named navigation with an ordered list. The last level is the
 * page itself (`aria-current="page"`, bold, no link). Levels are separated by
 * "›" from the style sheet, so the text of a level is its name only. Long names
 * wrap; the trail wraps between levels on narrow screens.
 */
export function Breadcrumb({
  label,
  testId,
  crumbs,
}: {
  /** Accessible name of the navigation ("Location of the device"). */
  label: string;
  testId?: string;
  crumbs: readonly Crumb[];
}): ReactElement {
  const lastIndex = crumbs.length - 1;
  return (
    <nav aria-label={label} data-testid={testId}>
      <ol className="flex flex-wrap gap-x-2 text-sm text-fg-muted">
        {crumbs.map((crumb, index) =>
          index === lastIndex ? (
            <li key={crumb.key} data-testid={crumb.testId} aria-current="page" className="min-w-0 font-semibold break-words text-fg">
              <Icon name={crumb.icon} className="mr-1" decorative />
              {crumb.label}
            </li>
          ) : (
            <li key={crumb.key} data-testid={crumb.testId} className="min-w-0 break-words after:ml-2 after:content-['›']">
              {crumb.to === undefined ? (
                <>
                  <Icon name={crumb.icon} className="mr-1" decorative />
                  {crumb.label}
                </>
              ) : (
                <Link to={crumb.to} className={LINK_CLASS}>
                  <Icon name={crumb.icon} className="mr-1" decorative />
                  {crumb.label}
                </Link>
              )}
            </li>
          ),
        )}
      </ol>
    </nav>
  );
}

/** What the trail needs of a device: the fields of the device API. */
export type TrailDevice = Pick<Device, "id" | "name" | "device_class" | "site" | "area" | "plant">;

/**
 * The levels from the structure down to a device: Structure (link to /), site,
 * area, plant with its key, the device (link to its page, unless it is the
 * last level of the trail).
 */
export function useDeviceCrumbs(device: TrailDevice): Crumb[] {
  const { t } = useTranslation("nav");
  return [
    { key: "structure", icon: "structure", label: t("structure"), to: "/" },
    { key: "site", icon: "site", label: device.site.name, testId: "breadcrumb-site" },
    { key: "area", icon: "area", label: device.area.name, testId: "breadcrumb-area" },
    {
      key: "plant",
      icon: PLANT_ICON,
      label: (
        <>
          {device.plant.name} <span className="tabular-nums slashed-zero">({device.plant.key})</span>
        </>
      ),
      testId: "breadcrumb-plant",
    },
    {
      key: "device",
      icon: deviceClassIcon(device.device_class),
      label: device.name,
      to: devicePath(device.id),
      testId: "breadcrumb-device",
    },
  ];
}
