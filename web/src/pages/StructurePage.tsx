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
import { deviceClassIcon } from "./structure/deviceClass.ts";
import { AreaForm, DeviceForm, PlantForm, SiteForm } from "./structure/forms.tsx";
import { type AreaNode, buildTree, filterTree, type PlantNode, type SiteNode } from "./structure/tree.ts";

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

function StructureContent({ control }: { control: EditorControl }): ReactElement {
  const { t } = useTranslation("assets");
  const searchId = useId();
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
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
      {tree.length === 0 ? (
        <p data-testid="structure-empty" className="text-fg-muted">
          {t("structure.empty")}
        </p>
      ) : shown.length === 0 ? (
        <p data-testid="structure-no-match" className="text-fg-muted">
          {t("structure.noMatch")}
        </p>
      ) : (
        <ul aria-label={t("structure.treeLabel")} data-testid="structure-tree" className="space-y-4">
          {shown.map((node) => (
            <SiteItem key={node.site.id} node={node} control={control} />
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

function SmallButton({
  label,
  icon,
  onClick,
  children,
}: {
  label: string;
  icon: IconName;
  onClick: () => void;
  children: ReactNode;
}): ReactElement {
  return (
    <Button type="button" size="sm" icon={icon} aria-label={label} onClick={onClick} className="self-center">
      {children}
    </Button>
  );
}

function Row({ children }: { children: ReactNode }): ReactElement {
  return <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">{children}</div>;
}

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

/** A device row names its class (E-53) instead of the kind, with the icon of the class (work order 074). */
function DeviceClassLabel({ deviceClass }: { deviceClass: DeviceClassEnum }): ReactElement {
  const { t } = useTranslation("assets");
  return (
    <span data-testid="device-class" className={KIND_LABEL_CLASS}>
      <Icon name={deviceClassIcon(deviceClass)} decorative />
      {t(`deviceClass.${deviceClass}`)}
    </span>
  );
}

function SiteItem({ node, control }: { node: SiteNode; control: EditorControl }): ReactElement {
  const { t } = useTranslation("assets");
  const { site } = node;
  return (
    <li data-testid="site-item" className="space-y-2 rounded border border-line bg-surface p-4">
      <Row>
        <KindLabel kind="site" />
        <span data-testid="site-name" className="text-lg font-semibold">
          {site.name}
        </span>
        <DeviceCount count={node.deviceCount} />
        {control.canManage ? (
          <>
            <SmallButton
              label={t("actions.editSite", { name: site.name })}
              onClick={() => {
                control.open({ form: "site", site });
              }}
              icon="edit"
            >
              {t("actions.edit")}
            </SmallButton>
            <SmallButton
              label={t("actions.newAreaIn", { name: site.name })}
              onClick={() => {
                control.open({ form: "area", siteId: site.id });
              }}
              icon="create"
            >
              {t("actions.newArea")}
            </SmallButton>
          </>
        ) : null}
      </Row>
      <EditorSlot control={control} anchor={`site:${String(site.id)}`} />
      {node.areas.length > 0 ? (
        <ul className="space-y-2 border-l border-line pl-4">
          {node.areas.map((areaNode) => (
            <AreaItem key={areaNode.area.id} node={areaNode} control={control} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

function AreaItem({ node, control }: { node: AreaNode; control: EditorControl }): ReactElement {
  const { t } = useTranslation("assets");
  const { area } = node;
  return (
    <li data-testid="area-item" className="space-y-2">
      <Row>
        <KindLabel kind="area" />
        <span data-testid="area-name" className="font-semibold">
          {area.name}
        </span>
        <DeviceCount count={node.deviceCount} />
        {control.canManage ? (
          <>
            <SmallButton
              label={t("actions.editArea", { name: area.name })}
              onClick={() => {
                control.open({ form: "area", siteId: area.site, area });
              }}
              icon="edit"
            >
              {t("actions.edit")}
            </SmallButton>
            <SmallButton
              label={t("actions.newPlantIn", { name: area.name })}
              onClick={() => {
                control.open({ form: "plant", areaId: area.id });
              }}
              icon="create"
            >
              {t("actions.newPlant")}
            </SmallButton>
          </>
        ) : null}
      </Row>
      <EditorSlot control={control} anchor={`area:${String(area.id)}`} />
      {node.plants.length > 0 ? (
        <ul className="space-y-2 border-l border-line pl-4">
          {node.plants.map((plantNode) => (
            <PlantItem key={plantNode.plant.id} node={plantNode} control={control} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

function PlantItem({ node, control }: { node: PlantNode; control: EditorControl }): ReactElement {
  const { t } = useTranslation("assets");
  const { plant } = node;
  return (
    <li data-testid="plant-item" className="space-y-2">
      <Row>
        <KindLabel kind="plant" />
        <span data-testid="plant-name" className="font-semibold">
          {plant.name}
        </span>
        <span data-testid="plant-key" className="tabular-nums slashed-zero text-sm">
          {plant.key}
        </span>
        <DeviceCount count={node.deviceCount} />
        {control.canManage ? (
          <>
            <SmallButton
              label={t("actions.editPlant", { name: plant.name })}
              onClick={() => {
                control.open({ form: "plant", areaId: plant.area, plant });
              }}
              icon="edit"
            >
              {t("actions.edit")}
            </SmallButton>
            <SmallButton
              label={t("actions.newDeviceIn", { name: plant.name })}
              onClick={() => {
                control.open({ form: "device", plantId: plant.id });
              }}
              icon="create"
            >
              {t("actions.newDevice")}
            </SmallButton>
          </>
        ) : null}
      </Row>
      <EditorSlot control={control} anchor={`plant:${String(plant.id)}`} />
      {node.devices.length > 0 ? (
        <ul className="space-y-1 border-l border-line pl-4">
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
    <li data-testid="device-item">
      <Row>
        <DeviceClassLabel deviceClass={device.device_class} />
        <Link to={`/devices/${String(device.id)}`} className="text-accent underline hover:text-accent-strong">
          {device.name}
        </Link>
        <span data-testid="device-key" className="tabular-nums slashed-zero text-sm">
          {device.key}
        </span>
        {device.ip_address === null ? null : (
          <span data-testid="device-ip" className="tabular-nums slashed-zero text-sm text-fg-muted">
            {device.ip_address}
          </span>
        )}
      </Row>
    </li>
  );
}
