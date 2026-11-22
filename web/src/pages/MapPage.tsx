// Map of the recorded structure (address /map, work order 039, E-48): an
// interactive preview of milestone M7, drawn with React Flow.
//
// The page reads the same four lists as the structure page and shows only what
// is stored: sites, areas and plants as groups, devices inside their plant, and
// the IP networks of the devices with dashed "device is in network" lines. The
// layout comes from pages/map/graph.ts; moved nodes are not saved.
import "@xyflow/react/dist/style.css";

import { useQuery } from "@tanstack/react-query";
import {
  Background,
  Controls,
  MiniMap,
  type NodeMouseHandler,
  ReactFlow,
  ReactFlowProvider,
  useNodesState,
  useReactFlow,
} from "@xyflow/react";
import {
  type FocusEvent,
  type KeyboardEvent,
  type ReactElement,
  useCallback,
  useDeferredValue,
  useEffect,
  useId,
  useMemo,
  useState,
} from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router";

import {
  areasListOptions,
  devicesListOptions,
  plantsListOptions,
  sitesListOptions,
} from "../api/generated/@tanstack/react-query.gen.ts";
import { ErrorMessage } from "../components/ErrorMessage.tsx";
import { Loading } from "../components/Loading.tsx";
import { AnimatedHeading } from "../components/TextMotion.tsx";
import { usePageTitle } from "../hooks/usePageTitle.ts";
import { Button } from "../components/ui/Button.tsx";
import { Input } from "../components/ui/fields.tsx";
import { Icon } from "../icons/Icon.tsx";
import { useDisplay } from "../theme/store.ts";
import {
  buildMapGraph,
  graphSignature,
  isEdgeHighlighted,
  type MapGraph,
  type MapNode,
  matchingNodeIds,
  type MembershipEdge,
} from "./map/graph.ts";
import { nodeTypes } from "./map/nodes.tsx";

/** Map of sites, areas, plants, devices and their networks. */
export function MapPage(): ReactElement {
  const { t } = useTranslation(["nav", "map"]);
  usePageTitle(t("nav:map"));
  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <AnimatedHeading text={t("nav:map")} />
        {/* The map does not replace the tree: the list view stays one click away. */}
        <Link to="/" data-testid="map-list-link" className="text-accent underline hover:text-accent-strong">
          <Icon name="structure" className="mr-1.5" decorative />
          {t("map:listLink")}
        </Link>
      </div>
      <p className="text-fg-muted">{t("map:intro")}</p>
      <MapContent />
    </section>
  );
}

function MapContent(): ReactElement {
  const { t } = useTranslation("map");
  const sites = useQuery(sitesListOptions());
  const areas = useQuery(areasListOptions());
  const plants = useQuery(plantsListOptions());
  const devices = useQuery(devicesListOptions());

  const graph = useMemo(
    () =>
      sites.data === undefined || areas.data === undefined || plants.data === undefined || devices.data === undefined
        ? null
        : buildMapGraph(sites.data, areas.data, plants.data, devices.data),
    [sites.data, areas.data, plants.data, devices.data],
  );
  // A new canvas only when the layout really changes, not on every reload of the same data.
  const signature = useMemo(() => (graph === null ? null : graphSignature(graph)), [graph]);

  const error = sites.error ?? areas.error ?? plants.error ?? devices.error;
  if (graph === null || signature === null) {
    return error === null ? <Loading /> : <ErrorMessage error={error} />;
  }
  return (
    <div className="space-y-4">
      {/* A failed reload keeps the last data on screen and says so. */}
      {error === null ? null : <ErrorMessage error={error} />}
      {graph.nodes.length === 0 ? (
        <div data-testid="map-empty" className="space-y-2">
          <p className="text-fg-muted">{t("empty")}</p>
          <Link to="/" className="text-accent underline hover:text-accent-strong">
            {t("emptyLink")}
          </Link>
        </div>
      ) : (
        <ReactFlowProvider key={signature}>
          <MapCanvas graph={graph} />
        </ReactFlowProvider>
      )}
    </div>
  );
}

const DIRECTIONS = ["up", "down", "left", "right"] as const;
type Direction = (typeof DIRECTIONS)[number];

function isDirection(value: string): value is Direction {
  return (DIRECTIONS as readonly string[]).includes(value);
}

/** Id of the map node an event happened on, if it is a node element. */
function nodeIdOf(target: EventTarget): string | null {
  if (!(target instanceof Element) || !target.classList.contains("react-flow__node")) {
    return null;
  }
  return target.getAttribute("data-id");
}

// Theme colours (index.css); React Flow sets them as inline styles, where var() works.
const MINIMAP_COLORS: Record<MapNode["type"], string> = {
  site: "var(--twox-line)",
  area: "var(--twox-surface-muted)",
  plant: "var(--twox-canvas)",
  device: "var(--twox-fg-muted)",
  network: "var(--twox-accent)",
};

function minimapColor(node: MapNode): string {
  return MINIMAP_COLORS[node.type];
}

function MapCanvas({ graph }: { graph: MapGraph }): ReactElement {
  const { t } = useTranslation(["map", "assets"]);
  const navigate = useNavigate();
  const searchId = useId();
  const networksId = useId();
  const { fitView } = useReactFlow<MapNode, MembershipEdge>();
  const [nodes, , onNodesChange] = useNodesState<MapNode>([...graph.nodes]);
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const [showNetworks, setShowNetworks] = useState(true);
  const [focusedId, setFocusedId] = useState<string | null>(null);
  // React Flow's own colours (controls, minimap) follow the shown colour mode.
  const { theme } = useDisplay();

  const deviceIdByNode = useMemo(
    () =>
      new Map(
        graph.nodes.flatMap((node) => (node.type === "device" ? [[node.id, node.data.deviceId] as const] : [])),
      ),
    [graph],
  );

  const matches = useMemo(
    () =>
      matchingNodeIds(
        showNetworks ? graph.nodes : graph.nodes.filter((node) => node.type !== "network"),
        deferredQuery,
      ),
    [graph, deferredQuery, showNetworks],
  );
  const matchSet = useMemo(() => new Set(matches), [matches]);

  // Selected, focused and found devices are highlighted together with their network line.
  const highlightedDevices = useMemo(() => {
    const ids = new Set<number>();
    for (const node of nodes) {
      if (node.type === "device" && (node.selected === true || matchSet.has(node.id) || node.id === focusedId)) {
        ids.add(node.data.deviceId);
      }
    }
    return ids;
  }, [nodes, matchSet, focusedId]);

  const highlightedNetworks = useMemo(() => {
    const cidrs = new Set<string>();
    for (const node of nodes) {
      if (node.type === "device" && node.data.network !== null && highlightedDevices.has(node.data.deviceId)) {
        cidrs.add(node.data.network);
      }
    }
    return cidrs;
  }, [nodes, highlightedDevices]);

  const shownNodes = useMemo(
    () =>
      nodes.map((node): MapNode => {
        const match = matchSet.has(node.id);
        switch (node.type) {
          case "device": {
            const { data } = node;
            const deviceClass = t(`assets:deviceClass.${data.deviceClass}`);
            return {
              ...node,
              ariaRole: "link",
              ariaLabel:
                data.ip === null || data.network === null
                  ? t("aria.device", { name: data.name, key: data.key, deviceClass })
                  : t("aria.deviceWithIp", {
                      name: data.name,
                      key: data.key,
                      deviceClass,
                      ip: data.ip,
                      network: data.network,
                    }),
              // A device node acts as a link; React Flow's "node" description would hide that.
              domAttributes: { "aria-roledescription": undefined },
              data: { ...data, match, highlighted: highlightedDevices.has(data.deviceId) },
            };
          }
          case "network":
            return {
              ...node,
              hidden: !showNetworks,
              ariaLabel: t("aria.network", { cidr: node.data.cidr, count: node.data.deviceCount }),
              domAttributes: { "aria-roledescription": t("aria.node") },
              data: { ...node.data, match, highlighted: highlightedNetworks.has(node.data.cidr) },
            };
          default:
            return {
              ...node,
              ariaLabel:
                node.data.key === null
                  ? t("aria.group", { kind: t(`kind.${node.data.kind}`), name: node.data.name })
                  : t("aria.plant", { name: node.data.name, key: node.data.key }),
              domAttributes: { "aria-roledescription": t("aria.node") },
              data: { ...node.data, match },
            };
        }
      }),
    [nodes, matchSet, highlightedDevices, highlightedNetworks, showNetworks, t],
  );

  const shownEdges = useMemo(
    () =>
      graph.edges.map((edge): MembershipEdge => {
        const active = isEdgeHighlighted(edge, highlightedDevices);
        return {
          ...edge,
          hidden: !showNetworks,
          label: t("edge.inNetwork"),
          className: active ? "map-membership map-membership-active" : "map-membership",
          focusable: false,
          selectable: false,
          style: {
            strokeDasharray: "6 4",
            stroke: active ? "var(--twox-fg)" : "var(--twox-fg-muted)",
            strokeWidth: active ? 2.5 : 1.25,
          },
          labelStyle: { fontSize: 11, fill: active ? "var(--twox-fg)" : "var(--twox-fg-muted)" },
          labelBgStyle: { fill: "var(--twox-surface)" },
        };
      }),
    [graph, highlightedDevices, showNetworks, t],
  );

  const ariaLabelConfig = useMemo(
    () => ({
      "node.a11yDescription.default": t("aria.nodeHelp"),
      "node.a11yDescription.keyboardDisabled": t("aria.nodeHelp"),
      "node.a11yDescription.ariaLiveMessage": ({ direction, x, y }: { direction: string; x: number; y: number }) =>
        t("aria.moved", { direction: isDirection(direction) ? t(`aria.direction.${direction}`) : direction, x, y }),
      "edge.a11yDescription.default": t("aria.edgeHelp"),
      "controls.ariaLabel": t("aria.controls"),
      "controls.zoomIn.ariaLabel": t("aria.zoomIn"),
      "controls.zoomOut.ariaLabel": t("aria.zoomOut"),
      "controls.fitView.ariaLabel": t("aria.fitView"),
      "minimap.ariaLabel": t("aria.minimap"),
      "handle.ariaLabel": t("aria.handle"),
    }),
    [t],
  );

  // The search centres the view on its matches.
  useEffect(() => {
    if (matches.length > 0) {
      void fitView({ nodes: matches.map((id) => ({ id })), maxZoom: 1.25 });
    }
  }, [matches, fitView]);

  const openDevice = useCallback(
    (nodeId: string): void => {
      const deviceId = deviceIdByNode.get(nodeId);
      if (deviceId !== undefined) {
        void navigate(`/devices/${String(deviceId)}`);
      }
    },
    [deviceIdByNode, navigate],
  );

  const onNodeClick: NodeMouseHandler<MapNode> = (_event, node) => {
    openDevice(node.id);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>): void => {
    const nodeId = nodeIdOf(event.target);
    if (event.key === "Enter" && nodeId !== null) {
      openDevice(nodeId);
    }
  };

  const onFocus = (event: FocusEvent<HTMLDivElement>): void => {
    setFocusedId(nodeIdOf(event.target));
  };

  const onBlur = (): void => {
    setFocusedId(null);
  };

  const status =
    deferredQuery.trim() === ""
      ? ""
      : matches.length === 0
        ? t("search.noMatch")
        : t("search.matches", { count: matches.length });

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-x-6 gap-y-3">
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
            data-testid="map-search"
            className="w-72 max-w-full"
          />
        </div>
        <p role="status" data-testid="map-search-status" className="min-h-6 text-sm text-fg-muted">
          {status}
        </p>
        {/* As high as the controls next to it (36 px), so the check box sits on their middle line. */}
        <div className="flex min-h-9 items-center gap-2">
          <input
            id={networksId}
            type="checkbox"
            checked={showNetworks}
            onChange={(event) => {
              setShowNetworks(event.target.checked);
            }}
            data-testid="map-show-networks"
          />
          <label htmlFor={networksId} className="text-sm">
            <Icon name="network" className="mr-1.5" decorative />
            {t("showNetworks")}
          </label>
        </div>
        {/* The only "fit view" control (the one of React Flow's control bar is switched off below). */}
        <Button
          type="button"
          icon="fitView"
          onClick={() => {
            void fitView();
          }}
        >
          {t("aria.fitView")}
        </Button>
      </div>
      <p className="text-sm text-fg-muted">{t("legend")}</p>
      <div
        role="region"
        aria-label={t("label")}
        data-testid="map-canvas"
        onKeyDown={onKeyDown}
        onFocus={onFocus}
        onBlur={onBlur}
        className="twox-map h-[70vh] min-h-[28rem] w-full overflow-hidden rounded border border-line bg-surface"
      >
        <ReactFlow
          nodes={shownNodes}
          edges={shownEdges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onNodeClick={onNodeClick}
          fitView
          minZoom={0.05}
          maxZoom={2}
          nodesConnectable={false}
          edgesFocusable={false}
          edgesReconnectable={false}
          deleteKeyCode={null}
          forceColorMode={theme}
          ariaLabelConfig={ariaLabelConfig}
        >
          <Background gap={24} />
          <Controls showInteractive={false} showFitView={false} />
          <MiniMap<MapNode> pannable zoomable nodeColor={minimapColor} />
        </ReactFlow>
      </div>
    </div>
  );
}
