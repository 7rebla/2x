import { useQuery } from "@tanstack/react-query";
import { type ReactElement, type ReactNode, useDeferredValue, useId, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import type { Area, Device, DeviceClassEnum, Plant, Site } from "../api/generated";
import {
  areasListOptions,
  devicesListOptions,
  plantsListOptions,
  sitesListOptions,
} from "../api/generated/@tanstack/react-query.gen.ts";
import { AnimatedHeading } from "../components/TextMotion.tsx";
import { ErrorMessage } from "../components/ErrorMessage.tsx";
import { Loading } from "../components/Loading.tsx";
import { Button } from "../components/ui/Button.tsx";
import { Input } from "../components/ui/fields.tsx";
import { Icon } from "../icons/Icon.tsx";
import type { IconName } from "../icons/names.ts";
import { useRole } from "../session.ts";
import { areaKey, type BranchKey, plantKey, readCollapsed, withKey, writeCollapsed } from "./structure/collapse.ts";
import { deviceClassIcon } from "./structure/deviceClass.ts";
import { AreaForm, DeviceForm, PlantForm, SiteForm } from "./structure/forms.tsx";
import {
  type AreaNode,
  buildTree,
  filterTree,
  normaliseQuery,
  type PlantNode,
  type SiteNode,
} from "./structure/tree.ts";

/**
 * Which form is open and where it shows: a new site above the tree, every
 * other form below the row it belongs to. Only one form is open at a time.
 */
type Editor =
  | { readonly form: "site"; readonly site?: Site }
  | { readonly form: "area"; readonly siteId: number; readonly area?: Area }
  | { readonly form: "plant"; readonly areaId: number; readonly plant?: Plant }
  | { readonly form: "device"; readonly plantId: number };

/** Row below which the open form is shown. */
function anchorOf(editor: Editor): string {
  switch (editor.form) {
    case "site":
      return editor.site === undefined ? "top" : `site:${String(editor.site.id)}`;
    case "area":
      return editor.area === undefined ? `site:${String(editor.siteId)}` : `area:${String(editor.area.id)}`;
    case "plant":
      return editor.plant === undefined ? `area:${String(editor.areaId)}` : `plant:${String(editor.plant.id)}`;
    case "device":
      return `plant:${String(editor.plantId)}`;
  }
}

interface EditorControl {
  readonly editor: Editor | null;
  readonly open: (editor: Editor) => void;
  readonly close: () => void;
  readonly canManage: boolean;
}

/**
 * Folding of areas and plants (work order 083). Outside a search the choice is
 * stored per browser (structure/collapse.ts). A search unfolds every hit; what
 * is folded during a search lasts only for that search text.
 */
interface Disclosure {
  readonly isOpen: (key: BranchKey) => boolean;
  readonly setOpen: (key: BranchKey, open: boolean) => void;
}

const NOTHING_FOLDED: ReadonlySet<BranchKey> = new Set();

function useDisclosure(needle: string): Disclosure {
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [searchFolded, setSearchFolded] = useState<{ needle: string; keys: ReadonlySet<BranchKey> }>({
    needle: "",
    keys: NOTHING_FOLDED,
  });
  const searching = needle !== "";
  const folded = searching ? (searchFolded.needle === needle ? searchFolded.keys : NOTHING_FOLDED) : collapsed;

  return {
    isOpen: (key) => !folded.has(key),
    setOpen: (key, open) => {
      if (searching) {
        setSearchFolded({ needle, keys: withKey(folded, key, !open) });
        if (!open) {
          // Folding a hit does not change the stored choice.
          return;
        }
      }
      const next = withKey(collapsed, key, !open);
      if (next !== collapsed) {
        writeCollapsed(next);
        setCollapsed(next);
      }
    },
  };
}

/** Structure of sites, areas, plants and devices (address /). */
export function StructurePage(): ReactElement {
  const { t } = useTranslation(["nav", "assets"]);
  const { canManage } = useRole();
  const [editor, setEditor] = useState<Editor | null>(null);
  const control: EditorControl = {
    editor,
    open: setEditor,
    close: () => {
      setEditor(null);
    },
    canManage,
  };

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <AnimatedHeading text={t("nav:structure")} />
        {canManage ? (
          <Button
            type="button"
            variant="primary"
            icon="create"
            onClick={() => {
              setEditor({ form: "site" });
            }}
          >
            {t("assets:actions.newSite")}
          </Button>
        ) : null}
      </div>
      <p className="text-fg-muted">{t("assets:structure.intro")}</p>
      <EditorSlot control={control} anchor="top" />
      <StructureContent control={control} />
    </section>
  );
}

function shownDevices(tree: readonly SiteNode[]): number {
  let count = 0;
  for (const siteNode of tree) {
    for (const areaNode of siteNode.areas) {
      for (const plantNode of areaNode.plants) {
        count += plantNode.devices.length;
      }
    }
  }
  return count;
}

function StructureContent({ control }: { control: EditorControl }): ReactElement {
  const { t } = useTranslation("assets");
  const searchId = useId();
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const needle = normaliseQuery(deferredQuery);
  const disclosure = useDisclosure(needle);
  const sites = useQuery(sitesListOptions());
  const areas = useQuery(areasListOptions());
  const plants = useQuery(plantsListOptions());
  const devices = useQuery(devicesListOptions());

  const tree = useMemo(
    () =>
      sites.data === undefined || areas.data === undefined || plants.data === undefined || devices.data === undefined
        ? null
        : buildTree(sites.data, areas.data, plants.data, devices.data),
    [sites.data, areas.data, plants.data, devices.data],
  );
  const shown = useMemo(() => (tree === null ? null : filterTree(tree, deferredQuery)), [tree, deferredQuery]);

  const error = sites.error ?? areas.error ?? plants.error ?? devices.error;
  if (shown === null || tree === null) {
    return error === null ? <Loading /> : <ErrorMessage error={error} />;
  }
  const searching = needle !== "" && tree.length > 0;

  return (
    <div className="space-y-4">
      {/* A failed reload keeps the last data on screen and says so. */}
      {error === null ? null : <ErrorMessage error={error} />}
      <div className="space-y-1">
        <label htmlFor={searchId} className="block text-sm text-fg-muted">
          <Icon name="search" className="mr-1.5" decorative />
          {t("search.label")}
        </label>
        <Input
          id={searchId}
          type="search"
          value={query}
          placeholder={t("search.placeholder")}
          onChange={(event) => {
            setQuery(event.target.value);
          }}
          data-testid="structure-search"
          className="w-full max-w-md"
        />
      </div>
      {/* The result of the search, announced to screen readers; empty without a search. */}
      <div role="status" data-testid="structure-search-status">
        {!searching ? null : shown.length === 0 ? (
          <p data-testid="structure-no-match" className="text-fg-muted">
            {t("structure.noMatch")}
          </p>
        ) : (
          <p data-testid="structure-match-count" className="text-sm text-fg-muted">
            {t("structure.matchCount", { count: shownDevices(shown) })}
          </p>
        )}
      </div>
      {tree.length === 0 ? (
        <p data-testid="structure-empty" className="text-fg-muted">
          {t("structure.empty")}
        </p>
      ) : shown.length === 0 ? null : (
        <ul aria-label={t("structure.treeLabel")} data-testid="structure-tree" className="space-y-4">
          {shown.map((node) => (
            <SiteItem key={node.site.id} node={node} control={control} disclosure={disclosure} />
          ))}
        </ul>
      )}
    </div>
  );
}

/** Shows the open form if it belongs below the row `anchor`. */
function EditorSlot({ control, anchor }: { control: EditorControl; anchor: string }): ReactElement | null {
  const { editor } = control;
  if (editor === null || anchorOf(editor) !== anchor) {
    return null;
  }
  // The key gives each target a fresh form (start values, errors).
  switch (editor.form) {
    case "site":
      return <SiteForm key={anchor} site={editor.site} onDone={control.close} />;
    case "area":
      return (
        <AreaForm key={`${anchor}:area`} area={editor.area} siteId={editor.siteId} onDone={control.close} />
      );
    case "plant":
      return (
        <PlantForm key={`${anchor}:plant`} plant={editor.plant} areaId={editor.areaId} onDone={control.close} />
      );
    case "device":
      return <DeviceForm key={`${anchor}:device`} plantId={editor.plantId} onDone={control.close} />;
  }
}

function DeviceCount({ count }: { count: number }): ReactElement {
  const { t } = useTranslation("assets");
  return (
    <span data-testid="device-count" className="text-sm text-fg-muted">
      {t("structure.deviceCount", { count })}
    </span>
  );
}

/**
 * An action of a row as an icon button (pencil, plus). The label names the
 * action and the item; it is the accessible name and the tooltip.
 */
function RowAction({ label, icon, onClick }: { label: string; icon: IconName; onClick: () => void }): ReactElement {
  return <Button type="button" size="sm" variant="ghost" icon={icon} aria-label={label} title={label} onClick={onClick} />;
}

/**
 * The actions stand at the right end of their row. With a mouse they show
 * clearly only while the row is hovered or holds the focus; on touch screens
 * (no fine pointer) they always show. The fade stops with reduced motion.
 */
const ACTIONS_CLASS =
  "flex shrink-0 items-center gap-0.5 transition-opacity pointer-fine:opacity-0 pointer-fine:group-hover:opacity-100 pointer-fine:group-focus-within:opacity-100";

/**
 * A row of a site, area or plant: the fold button (or its space), the
 * describing parts, which wrap on narrow screens, and the actions on the right.
 */
function Row({ lead, children, actions }: { lead?: ReactNode; children: ReactNode; actions?: ReactNode }): ReactElement {
  return (
    <div className="group flex items-start gap-1">
      {lead}
      <div className="flex min-h-7 min-w-0 flex-1 flex-wrap items-center gap-x-3 gap-y-0.5">{children}</div>
      {actions === undefined ? null : <div className={ACTIONS_CLASS}>{actions}</div>}
    </div>
  );
}

/** Folds an area or a plant in and out; `aria-expanded` says which. */
function BranchToggle({
  label,
  open,
  controls,
  onToggle,
}: {
  label: string;
  open: boolean;
  controls: string;
  onToggle: () => void;
}): ReactElement {
  return (
    <Button
      type="button"
      size="sm"
      variant="ghost"
      aria-label={label}
      title={label}
      aria-expanded={open}
      aria-controls={open ? controls : undefined}
      onClick={onToggle}
    >
      <Icon name="disclosure" className={open ? "transition-transform" : "-rotate-90 transition-transform"} decorative />
    </Button>
  );
}

/** Keeps the place of the fold button in a row without children, so names stay aligned. */
function TogglePlace(): ReactElement {
  return <span aria-hidden="true" className="w-[34px] shrink-0" />;
}

const BRANCH_LIST_CLASS = "space-y-2 border-l border-line pl-3 sm:pl-4";

const KIND_LABEL_CLASS = "inline-flex items-center gap-1 self-center text-xs uppercase tracking-wide text-fg-muted";

function KindLabel({ kind }: { kind: "site" | "area" | "plant" }): ReactElement {
  const { t } = useTranslation("assets");
  // The kind's icon (16 px) before its name; the icon name equals the kind.
  return (
    <span className={KIND_LABEL_CLASS}>
      <Icon name={kind} decorative />
      {t(`kind.${kind}`)}
    </span>
  );
}

/**
 * A device row names its class (E-53) with the icon of the class (work order
 * 074). The text shows from 640 px; below it stays for screen readers and as
 * tooltip, so the icon alone keeps the row short (work order 083).
 */
function DeviceClassLabel({ deviceClass }: { deviceClass: DeviceClassEnum }): ReactElement {
  const { t } = useTranslation("assets");
  const label = t(`deviceClass.${deviceClass}`);
  return (
    <span data-testid="device-class" title={label} className={KIND_LABEL_CLASS}>
      <Icon name={deviceClassIcon(deviceClass)} decorative />
      <span className="sr-only sm:not-sr-only">{label}</span>
    </span>
  );
}

function SiteItem({
  node,
  control,
  disclosure,
}: {
  node: SiteNode;
  control: EditorControl;
  disclosure: Disclosure;
}): ReactElement {
  const { t } = useTranslation("assets");
  const { site } = node;
  return (
    <li data-testid="site-item" className="space-y-2 rounded border border-line bg-surface p-3 sm:p-4">
      <Row
        actions={
          control.canManage ? (
            <>
              <RowAction
                label={t("actions.editSite", { name: site.name })}
                icon="edit"
                onClick={() => {
                  control.open({ form: "site", site });
                }}
              />
              <RowAction
                label={t("actions.newAreaIn", { name: site.name })}
                icon="create"
                onClick={() => {
                  control.open({ form: "area", siteId: site.id });
                }}
              />
            </>
          ) : undefined
        }
      >
        <KindLabel kind="site" />
        <span data-testid="site-name" className="text-lg font-semibold">
          {site.name}
        </span>
        <DeviceCount count={node.deviceCount} />
      </Row>
      <EditorSlot control={control} anchor={`site:${String(site.id)}`} />
      {node.areas.length > 0 ? (
        <ul className={BRANCH_LIST_CLASS}>
          {node.areas.map((areaNode) => (
            <AreaItem key={areaNode.area.id} node={areaNode} control={control} disclosure={disclosure} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

function AreaItem({
  node,
  control,
  disclosure,
}: {
  node: AreaNode;
  control: EditorControl;
  disclosure: Disclosure;
}): ReactElement {
  const { t } = useTranslation("assets");
  const listId = useId();
  const { area } = node;
  const key = areaKey(area.id);
  const open = disclosure.isOpen(key);
  return (
    <li data-testid="area-item" className="space-y-2">
      <Row
        lead={
          node.plants.length > 0 ? (
            <BranchToggle
              label={t("structure.toggleArea", { name: area.name })}
              open={open}
              controls={listId}
              onToggle={() => {
                disclosure.setOpen(key, !open);
              }}
            />
          ) : (
            <TogglePlace />
          )
        }
        actions={
          control.canManage ? (
            <>
              <RowAction
                label={t("actions.editArea", { name: area.name })}
                icon="edit"
                onClick={() => {
                  control.open({ form: "area", siteId: area.site, area });
                }}
              />
              <RowAction
                label={t("actions.newPlantIn", { name: area.name })}
                icon="create"
                onClick={() => {
                  // The new plant will show below its area.
                  disclosure.setOpen(key, true);
                  control.open({ form: "plant", areaId: area.id });
                }}
              />
            </>
          ) : undefined
        }
      >
        <KindLabel kind="area" />
        <span data-testid="area-name" className="font-semibold">
          {area.name}
        </span>
        <DeviceCount count={node.deviceCount} />
      </Row>
      <EditorSlot control={control} anchor={`area:${String(area.id)}`} />
      {node.plants.length > 0 && open ? (
        <ul id={listId} className={BRANCH_LIST_CLASS}>
          {node.plants.map((plantNode) => (
            <PlantItem key={plantNode.plant.id} node={plantNode} control={control} disclosure={disclosure} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

function PlantItem({
  node,
  control,
  disclosure,
}: {
  node: PlantNode;
  control: EditorControl;
  disclosure: Disclosure;
}): ReactElement {
  const { t } = useTranslation("assets");
  const listId = useId();
  const { plant } = node;
  const key = plantKey(plant.id);
  const open = disclosure.isOpen(key);
  return (
    <li data-testid="plant-item" className="space-y-2">
      <Row
        lead={
          node.devices.length > 0 ? (
            <BranchToggle
              label={t("structure.togglePlant", { name: plant.name })}
              open={open}
              controls={listId}
              onToggle={() => {
                disclosure.setOpen(key, !open);
              }}
            />
          ) : (
            <TogglePlace />
          )
        }
        actions={
          control.canManage ? (
            <>
              <RowAction
                label={t("actions.editPlant", { name: plant.name })}
                icon="edit"
                onClick={() => {
                  control.open({ form: "plant", areaId: plant.area, plant });
                }}
              />
              <RowAction
                label={t("actions.newDeviceIn", { name: plant.name })}
                icon="create"
                onClick={() => {
                  // The new device will show below its plant.
                  disclosure.setOpen(key, true);
                  control.open({ form: "device", plantId: plant.id });
                }}
              />
            </>
          ) : undefined
        }
      >
        <KindLabel kind="plant" />
        <span data-testid="plant-name" className="font-semibold">
          {plant.name}
        </span>
        <span data-testid="plant-key" className="tabular-nums slashed-zero text-sm">
          {plant.key}
        </span>
        <DeviceCount count={node.deviceCount} />
      </Row>
      <EditorSlot control={control} anchor={`plant:${String(plant.id)}`} />
      {node.devices.length > 0 && open ? (
        // One grid for the devices of a plant: class, name, key and address
        // stand in the same columns on every row (rows are subgrids). Below
        // 640 px key and address go to a second line under the name. From
        // 1024 px the columns have a least width, so that plants with short
        // and long class names line up as well.
        <ul
          id={listId}
          data-testid="device-list"
          className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 border-l border-line pl-3 sm:grid-cols-[auto_minmax(0,1fr)_auto_auto] sm:pl-4 lg:grid-cols-[minmax(11rem,auto)_minmax(0,1fr)_minmax(8rem,auto)_minmax(8rem,auto)]"
        >
          {node.devices.map((device) => (
            <DeviceItem key={device.id} device={device} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

function DeviceItem({ device }: { device: Device }): ReactElement {
  return (
    <li data-testid="device-item" className="col-span-full grid grid-cols-subgrid items-center">
      <DeviceClassLabel deviceClass={device.device_class} />
      <Link to={`/devices/${String(device.id)}`} className="break-words text-accent underline hover:text-accent-strong">
        {device.name}
      </Link>
      <div className="col-start-2 flex flex-wrap gap-x-3 sm:contents">
        <span data-testid="device-key" className="tabular-nums slashed-zero text-sm">
          {device.key}
        </span>
        {device.ip_address === null ? (
          // Keeps the address column in place.
          <span />
        ) : (
          <span data-testid="device-ip" className="tabular-nums slashed-zero text-sm text-fg-muted">
            {device.ip_address}
          </span>
        )}
      </div>
    </li>
  );
}
