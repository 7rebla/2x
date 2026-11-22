// Node components of the map. One uniform shape per kind, each with the icon
// of its kind (work order 071); devices show the generic device icon until
// work order 074 adds one per device class. Every text from the data is
// rendered as text; the icons are decorative, the kind is also written out.
import { Handle, type NodeProps, type NodeTypes, Position } from "@xyflow/react";
import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";

import { Icon } from "../../icons/Icon.tsx";
import type { DeviceNode, GroupKind, GroupNode, NetworkNode } from "./graph.ts";

const GROUP_STYLE: Record<GroupKind, string> = {
  site: "border-line-strong bg-surface-muted",
  area: "border-line bg-surface",
  plant: "border-line bg-canvas",
};

// Handles only anchor the network edges; nobody can draw connections.
const HIDDEN_HANDLE = "!h-1 !w-1 !min-h-0 !min-w-0 !border-0 !bg-transparent";

function matchRing(match: boolean | undefined): string {
  return match === true ? "ring-4 ring-accent" : "";
}

function GroupNodeView({ data }: NodeProps<GroupNode>): ReactElement {
  const { t } = useTranslation("map");
  return (
    <div
      data-testid={`map-${data.kind}`}
      data-match={data.match === true ? "true" : undefined}
      className={`h-full w-full rounded-lg border-2 ${GROUP_STYLE[data.kind]} ${matchRing(data.match)}`}
    >
      <div className="px-4 pt-2">
        <div className="flex items-center gap-1 text-xs uppercase tracking-wide text-fg-muted">
          <Icon name={data.kind} decorative />
          {t(`kind.${data.kind}`)}
        </div>
        <div className="truncate font-semibold text-fg" title={data.name}>
          {data.name}
        </div>
        {data.key === null ? null : (
          <div className="truncate text-xs tabular-nums slashed-zero text-fg-muted" title={data.key}>
            {data.key}
          </div>
        )}
      </div>
    </div>
  );
}

function DeviceNodeView({ data, selected }: NodeProps<DeviceNode>): ReactElement {
  const active = selected || data.highlighted === true;
  return (
    <div
      data-testid="map-device"
      data-match={data.match === true ? "true" : undefined}
      data-highlighted={active ? "true" : undefined}
      className={`flex h-full w-full cursor-pointer flex-col justify-center rounded-md border bg-surface px-3 py-2 shadow-sm ${
        active ? "border-fg border-2" : "border-line-strong"
      } ${matchRing(data.match)}`}
    >
      <div className="flex min-w-0 items-center gap-1.5 font-semibold text-fg">
        <Icon name="device" className="text-fg-muted" decorative />
        <span className="truncate" title={data.name}>
          {data.name}
        </span>
      </div>
      <div className="truncate text-xs tabular-nums slashed-zero text-fg-muted" title={data.key}>
        {data.key}
      </div>
      {data.ip === null ? null : (
        <div className="truncate text-xs tabular-nums slashed-zero text-fg" title={data.ip}>
          {data.ip}
        </div>
      )}
      {data.model === "" ? null : (
        <div className="truncate text-xs text-fg-muted" title={data.model}>
          {data.model}
        </div>
      )}
      <Handle type="source" position={Position.Right} isConnectable={false} className={HIDDEN_HANDLE} />
    </div>
  );
}

function NetworkNodeView({ data }: NodeProps<NetworkNode>): ReactElement {
  const { t } = useTranslation("map");
  const active = data.highlighted === true;
  return (
    <div
      data-testid="map-network"
      data-match={data.match === true ? "true" : undefined}
      data-highlighted={active ? "true" : undefined}
      className={`flex h-full w-full flex-col justify-center rounded-full border-2 border-dashed bg-surface-muted px-5 ${
        active ? "border-fg" : "border-line-strong"
      } ${matchRing(data.match)}`}
    >
      <Handle type="target" position={Position.Left} isConnectable={false} className={HIDDEN_HANDLE} />
      <div className="flex items-center gap-1 text-xs uppercase tracking-wide text-fg-muted">
        <Icon name="network" decorative />
        {t("kind.network")}
      </div>
      <div className="truncate text-sm tabular-nums slashed-zero font-semibold text-fg" title={data.cidr}>
        {data.cidr}
      </div>
    </div>
  );
}

/** Node types of the map; defined once, outside any component (React Flow compares the object). */
export const nodeTypes: NodeTypes = {
  site: GroupNodeView,
  area: GroupNodeView,
  plant: GroupNodeView,
  device: DeviceNodeView,
  network: NetworkNodeView,
};
