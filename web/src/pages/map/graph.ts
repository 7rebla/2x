// The map as nodes and edges (work order 039, E-48): the structure of the
// database and the IP networks of the devices, nothing else.
//
// Sites, areas and plants are groups (parent nodes), devices are nodes in their
// plant. Each IPv4 /24 and IPv6 /64 network that holds at least one device
// address is a network node; the only edges are "device is in network". No
// edge is ever drawn between devices and nothing is derived from configuration
// files (that comes with M5/M7).
//
// The layout is a small grid per group, computed bottom-up from fixed node
// sizes. It uses no randomness and sorts every input first, so the same data
// always gives the same positions. Positions are never stored.
import type { Edge, Node } from "@xyflow/react";

import type { Area, Device, DeviceClassEnum, Plant, Site } from "../../api/generated";
import { type AreaNode, buildTree, normaliseQuery, type PlantNode, type SiteNode } from "../structure/tree.ts";

export type GroupKind = "site" | "area" | "plant";

/** Data of a site, area or plant node. Types, not interfaces: React Flow wants plain records. */
export type GroupData = {
  readonly kind: GroupKind;
  readonly name: string;
  /** Key of a plant; sites and areas have none. */
  readonly key: string | null;
  readonly deviceCount: number;
  /** Set by the page while the node matches the search. */
  readonly match?: boolean;
};

export type DeviceData = {
  readonly kind: "device";
  readonly deviceId: number;
  readonly name: string;
  readonly key: string;
  readonly ip: string | null;
  readonly model: string;
  /** Class of the device (E-53); chooses the icon and is named in the tooltip and the label. */
  readonly deviceClass: DeviceClassEnum;
  /** Network node of the device's address, null without an address. */
  readonly network: string | null;
  readonly match?: boolean;
  /** Set by the page while the device is selected, focused or found. */
  readonly highlighted?: boolean;
};

export type NetworkData = {
  readonly kind: "network";
  /** The network in CIDR notation, for example 192.168.0.0/24. */
  readonly cidr: string;
  readonly family: 4 | 6;
  readonly deviceCount: number;
  readonly match?: boolean;
  readonly highlighted?: boolean;
};

export type GroupNode = Node<GroupData, GroupKind>;
export type DeviceNode = Node<DeviceData, "device">;
export type NetworkNode = Node<NetworkData, "network">;
export type MapNode = GroupNode | DeviceNode | NetworkNode;

export type MembershipData = {
  readonly deviceId: number;
  readonly cidr: string;
};

/** "Device is in network": the only kind of edge on the map. */
export type MembershipEdge = Edge<MembershipData, "default">;

export interface MapGraph {
  /** Parents always come before their children. */
  readonly nodes: readonly MapNode[];
  readonly edges: readonly MembershipEdge[];
}

// Sizes in flow coordinates (pixels at zoom 1).
export const DEVICE_SIZE = { width: 220, height: 96 } as const;
export const NETWORK_SIZE = { width: 200, height: 60 } as const;
/** Height of the title rows of a group (kind and name, and the key of a plant). */
export const GROUP_HEADER = { site: 52, area: 52, plant: 68 } as const;
/** Inner space of a group around its children. */
export const GROUP_PADDING = 16;
/** Space between children of a group. */
export const GAP = 16;
/** Space between sites, and between the sites and the network column. */
export const OUTER_GAP = 64;
/** Most children side by side in one row of a group. */
const MAX_COLUMNS = { root: 2, site: 3, area: 4, plant: 3 } as const;

interface Size {
  readonly width: number;
  readonly height: number;
}

interface Point {
  readonly x: number;
  readonly y: number;
}

/** Number of columns for `count` children: about square, at most `max`. */
function columnsFor(count: number, max: number): number {
  return Math.max(1, Math.min(max, Math.ceil(Math.sqrt(count))));
}

/**
 * Places children of the given sizes in a grid, row by row. Each column is as
 * wide as its widest child, each row as high as its highest child, so no two
 * children overlap. Returns the top-left corner of each child and the size of
 * the whole grid ({0, 0} without children).
 */
export function gridLayout(sizes: readonly Size[], maxColumns: number, gap: number): { positions: Point[]; size: Size } {
  if (sizes.length === 0) {
    return { positions: [], size: { width: 0, height: 0 } };
  }
  const columns = columnsFor(sizes.length, maxColumns);
  const columnWidths: number[] = [];
  const rowHeights: number[] = [];
  sizes.forEach((size, index) => {
    const column = index % columns;
    const row = Math.floor(index / columns);
    columnWidths[column] = Math.max(columnWidths[column] ?? 0, size.width);
    rowHeights[row] = Math.max(rowHeights[row] ?? 0, size.height);
  });
  const columnStarts = offsets(columnWidths, gap);
  const rowStarts = offsets(rowHeights, gap);
  const positions = sizes.map((_, index) => ({
    x: columnStarts[index % columns] ?? 0,
    y: rowStarts[Math.floor(index / columns)] ?? 0,
  }));
  return {
    positions,
    size: { width: total(columnWidths, gap), height: total(rowHeights, gap) },
  };
}

function offsets(lengths: readonly number[], gap: number): number[] {
  const result: number[] = [];
  let position = 0;
  for (const length of lengths) {
    result.push(position);
    position += length + gap;
  }
  return result;
}

function total(lengths: readonly number[], gap: number): number {
  return lengths.reduce((sum, length) => sum + length, 0) + gap * Math.max(0, lengths.length - 1);
}

/** A group laid out with its children; positions of the children are relative to the group. */
interface Placed {
  readonly size: Size;
  /** Nodes of this group and everything inside it, parents first; positions relative to their parent. */
  readonly build: (position: Point, parentId: string | undefined) => MapNode[];
}

/** Size of a group around a grid of children, never narrower than one device. */
function groupSize(kind: GroupKind, inner: Size): Size {
  const width = Math.max(DEVICE_SIZE.width, inner.width) + 2 * GROUP_PADDING;
  const height = GROUP_HEADER[kind] + inner.height + GROUP_PADDING;
  return { width, height };
}

function placeGroup(
  kind: GroupKind,
  id: string,
  data: Omit<GroupData, "kind">,
  children: readonly Placed[],
): Placed {
  const grid = gridLayout(
    children.map((child) => child.size),
    MAX_COLUMNS[kind],
    GAP,
  );
  const size = groupSize(kind, grid.size);
  return {
    size,
    build: (position, parentId) => {
      const node: GroupNode = {
        id,
        type: kind,
        position,
        data: { kind, ...data },
        width: size.width,
        height: size.height,
        draggable: false,
        selectable: false,
        ...(parentId === undefined ? {} : { parentId, extent: "parent" as const }),
      };
      const inner = children.flatMap((child, index) => {
        const at = grid.positions[index] ?? { x: 0, y: 0 };
        return child.build({ x: GROUP_PADDING + at.x, y: GROUP_HEADER[kind] + at.y }, id);
      });
      return [node, ...inner];
    },
  };
}

function placeDevice(device: Device): Placed {
  return {
    size: DEVICE_SIZE,
    build: (position, parentId) => {
      const node: DeviceNode = {
        id: deviceNodeId(device.id),
        type: "device",
        position,
        data: {
          kind: "device",
          deviceId: device.id,
          name: device.name,
          key: device.key,
          ip: device.ip_address,
          model: device.model,
          deviceClass: device.device_class,
          network: networkOf(device.ip_address)?.cidr ?? null,
        },
        width: DEVICE_SIZE.width,
        height: DEVICE_SIZE.height,
        ...(parentId === undefined ? {} : { parentId, extent: "parent" as const }),
      };
      return [node];
    },
  };
}

function placePlant(node: PlantNode): Placed {
  return placeGroup(
    "plant",
    `plant:${String(node.plant.id)}`,
    { name: node.plant.name, key: node.plant.key, deviceCount: node.deviceCount },
    node.devices.map(placeDevice),
  );
}

function placeArea(node: AreaNode): Placed {
  return placeGroup(
    "area",
    `area:${String(node.area.id)}`,
    { name: node.area.name, key: null, deviceCount: node.deviceCount },
    node.plants.map(placePlant),
  );
}

function placeSite(node: SiteNode): Placed {
  return placeGroup(
    "site",
    `site:${String(node.site.id)}`,
    { name: node.site.name, key: null, deviceCount: node.deviceCount },
    node.areas.map(placeArea),
  );
}

export function deviceNodeId(deviceId: number): string {
  return `device:${String(deviceId)}`;
}

export function networkNodeId(cidr: string): string {
  return `network:${cidr}`;
}

// ---------------------------------------------------------------------------
// Networks from addresses

export interface Network {
  readonly cidr: string;
  readonly family: 4 | 6;
  /** Sort key: IPv4 before IPv6, then by address. */
  readonly order: string;
}

const IPV4 = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/;
const HEX_GROUP = /^[0-9a-f]{1,4}$/;

function parseIpv4(text: string): number[] | null {
  const parts = IPV4.exec(text);
  if (parts === null) {
    return null;
  }
  const octets = parts.slice(1).map(Number);
  return octets.every((octet) => octet <= 255) ? octets : null;
}

/** The eight 16-bit groups of an IPv6 address, or null if it is not one. */
export function parseIpv6(text: string): number[] | null {
  let address = text.toLowerCase();
  // An IPv4 address in the last 32 bits (for example ::ffff:192.0.2.1).
  const lastColon = address.lastIndexOf(":");
  const tail = address.slice(lastColon + 1);
  if (tail.includes(".")) {
    const octets = parseIpv4(tail);
    if (octets === null) {
      return null;
    }
    const [a = 0, b = 0, c = 0, d = 0] = octets;
    address = `${address.slice(0, lastColon + 1)}${((a << 8) | b).toString(16)}:${((c << 8) | d).toString(16)}`;
  }
  const halves = address.split("::");
  if (halves.length > 2) {
    return null;
  }
  const head = halves[0] === "" || halves[0] === undefined ? [] : halves[0].split(":");
  const rest = halves.length === 2 && halves[1] !== "" && halves[1] !== undefined ? halves[1].split(":") : [];
  if (![...head, ...rest].every((group) => HEX_GROUP.test(group))) {
    return null;
  }
  const missing = 8 - head.length - rest.length;
  if (halves.length === 2 ? missing < 1 : missing !== 0) {
    return null;
  }
  return [...head, ...new Array<string>(missing).fill("0"), ...rest].map((group) => parseInt(group, 16));
}

/** Text form of eight IPv6 groups after RFC 5952: lower case, longest run of zero groups as "::". */
export function formatIpv6(groups: readonly number[]): string {
  let bestStart = -1;
  let bestLength = 0;
  for (let start = 0; start < groups.length; start += 1) {
    let length = 0;
    while (start + length < groups.length && groups[start + length] === 0) {
      length += 1;
    }
    if (length > bestLength) {
      bestStart = start;
      bestLength = length;
    }
  }
  const hex = groups.map((group) => group.toString(16));
  if (bestLength < 2) {
    return hex.join(":");
  }
  const before = hex.slice(0, bestStart).join(":");
  const after = hex.slice(bestStart + bestLength).join(":");
  return `${before}::${after}`;
}

/**
 * The network of an address: IPv4 by /24, IPv6 by /64. Null without an
 * address or for a value that is not an IP address.
 */
export function networkOf(address: string | null): Network | null {
  if (address === null) {
    return null;
  }
  const text = address.trim();
  const v4 = parseIpv4(text);
  if (v4 !== null) {
    const [a = 0, b = 0, c = 0] = v4;
    return {
      cidr: `${String(a)}.${String(b)}.${String(c)}.0/24`,
      family: 4,
      order: `4:${[a, b, c].map((octet) => octet.toString(16).padStart(2, "0")).join("")}`,
    };
  }
  const v6 = parseIpv6(text);
  if (v6 !== null) {
    const prefix = [...v6.slice(0, 4), 0, 0, 0, 0];
    return {
      cidr: `${formatIpv6(prefix)}/64`,
      family: 6,
      order: `6:${prefix.map((group) => group.toString(16).padStart(4, "0")).join("")}`,
    };
  }
  return null;
}

// ---------------------------------------------------------------------------
// The whole map

function byId<T extends { readonly id: number }>(items: readonly T[]): T[] {
  return [...items].sort((left, right) => left.id - right.id);
}

/**
 * Nodes and edges of the map. Sites and areas are sorted by name, plants and
 * devices by key (as on the structure page), ties by id. Networks follow the
 * sites in one column on the right, IPv4 first, each sorted by address.
 */
export function buildMapGraph(
  sites: readonly Site[],
  areas: readonly Area[],
  plants: readonly Plant[],
  devices: readonly Device[],
): MapGraph {
  // Sorting by id first makes the order of equal names independent of the order of the input.
  const tree = buildTree(byId(sites), byId(areas), byId(plants), byId(devices));
  const placedSites = tree.map(placeSite);
  const grid = gridLayout(
    placedSites.map((site) => site.size),
    MAX_COLUMNS.root,
    OUTER_GAP,
  );
  const structureNodes = placedSites.flatMap((site, index) =>
    site.build(grid.positions[index] ?? { x: 0, y: 0 }, undefined),
  );

  const shownDevices = structureNodes.filter((node): node is DeviceNode => node.type === "device");
  const networks = new Map<string, { network: Network; deviceIds: number[] }>();
  for (const node of shownDevices) {
    const network = networkOf(node.data.ip);
    if (network === null) {
      continue;
    }
    const entry = networks.get(network.cidr);
    if (entry === undefined) {
      networks.set(network.cidr, { network, deviceIds: [node.data.deviceId] });
    } else {
      entry.deviceIds.push(node.data.deviceId);
    }
  }
  const sortedNetworks = [...networks.values()].sort((left, right) =>
    left.network.order < right.network.order ? -1 : left.network.order > right.network.order ? 1 : 0,
  );
  const networkX = grid.size.width + (grid.size.width > 0 ? OUTER_GAP * 2 : 0);
  const networkNodes = sortedNetworks.map(
    ({ network, deviceIds }, index): NetworkNode => ({
      id: networkNodeId(network.cidr),
      type: "network",
      position: { x: networkX, y: index * (NETWORK_SIZE.height + OUTER_GAP / 2) },
      data: { kind: "network", cidr: network.cidr, family: network.family, deviceCount: deviceIds.length },
      width: NETWORK_SIZE.width,
      height: NETWORK_SIZE.height,
    }),
  );

  const edges = shownDevices.flatMap((node): MembershipEdge[] => {
    const cidr = node.data.network;
    if (cidr === null) {
      return [];
    }
    return [
      {
        id: `member:${node.id}`,
        type: "default",
        source: node.id,
        target: networkNodeId(cidr),
        data: { deviceId: node.data.deviceId, cidr },
      },
    ];
  });

  return { nodes: [...structureNodes, ...networkNodes], edges };
}

// ---------------------------------------------------------------------------
// Search and highlighting

/** Texts a node is found by: names, keys, IP addresses, the network. */
function searchTexts(node: MapNode): readonly (string | null)[] {
  switch (node.type) {
    case "device":
      return [node.data.name, node.data.key, node.data.ip];
    case "network":
      return [node.data.cidr];
    default:
      return [node.data.name, node.data.key];
  }
}

/** Ids of the nodes whose name, key or IP address contains the query, in node order; none for an empty query. */
export function matchingNodeIds(nodes: readonly MapNode[], query: string): string[] {
  const needle = normaliseQuery(query);
  if (needle === "") {
    return [];
  }
  return nodes
    .filter((node) =>
      searchTexts(node).some((text) => text !== null && text.toLocaleLowerCase().includes(needle)),
    )
    .map((node) => node.id);
}

/** True for edges of the given highlighted devices. */
export function isEdgeHighlighted(edge: MembershipEdge, highlightedDeviceIds: ReadonlySet<number>): boolean {
  return edge.data !== undefined && highlightedDeviceIds.has(edge.data.deviceId);
}

/** A stable text for "the layout is the same": ids, positions, sizes and data of all nodes and edges. */
export function graphSignature(graph: MapGraph): string {
  return JSON.stringify([
    graph.nodes.map((node) => [node.id, node.parentId ?? null, node.position, node.width, node.height, node.data]),
    graph.edges.map((edge) => [edge.id, edge.source, edge.target]),
  ]);
}
