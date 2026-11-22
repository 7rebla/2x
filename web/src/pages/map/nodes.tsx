// Node components of the map. One uniform shape per kind (no icons by device
// type yet, see docs/design/icon-bedarfsanalyse.md). Every text from the data
// is rendered as text.
import { Handle, type NodeProps, type NodeTypes, Position } from "@xyflow/react";
import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";

import type { DeviceNode, GroupKind, GroupNode, NetworkNode } from "./graph.ts";

const GROUP_STYLE: Record<GroupKind, string> = {
  site: "border-slate-400 bg-slate-100/70",
  area: "border-slate-300 bg-white/80",
  plant: "border-slate-300 bg-slate-50",
};

// Handles only anchor the network edges; nobody can draw connections.
const HIDDEN_HANDLE = "!h-1 !w-1 !min-h-0 !min-w-0 !border-0 !bg-transparent";

function matchRing(match: boolean | undefined): string {
  return match === true ? "ring-4 ring-amber-400" : "";
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
        <div className="text-xs uppercase tracking-wide text-slate-500">{t(`kind.${data.kind}`)}</div>
        <div className="truncate font-semibold text-slate-900" title={data.name}>
          {data.name}
        </div>
        {data.key === null ? null : (
          <div className="truncate font-mono text-xs text-slate-600" title={data.key}>
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
      className={`flex h-full w-full cursor-pointer flex-col justify-center rounded-md border bg-white px-3 py-2 shadow-sm ${
        active ? "border-slate-900 border-2" : "border-slate-300"
      } ${matchRing(data.match)}`}
    >
      <div className="truncate font-semibold text-slate-900" title={data.name}>
        {data.name}
      </div>
      <div className="truncate font-mono text-xs text-slate-600" title={data.key}>
        {data.key}
      </div>
      {data.ip === null ? null : (
        <div className="truncate font-mono text-xs text-slate-700" title={data.ip}>
          {data.ip}
        </div>
      )}
      {data.model === "" ? null : (
        <div className="truncate text-xs text-slate-500" title={data.model}>
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
      className={`flex h-full w-full flex-col justify-center rounded-full border-2 border-dashed bg-sky-50 px-5 ${
        active ? "border-slate-900" : "border-sky-400"
      } ${matchRing(data.match)}`}
    >
      <Handle type="target" position={Position.Left} isConnectable={false} className={HIDDEN_HANDLE} />
      <div className="text-xs uppercase tracking-wide text-sky-800">{t("kind.network")}</div>
      <div className="truncate font-mono text-sm font-semibold text-slate-900" title={data.cidr}>
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
