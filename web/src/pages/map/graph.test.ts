import { describe, expect, it } from "vitest";

import type { Device } from "../../api/generated";
import { area, device, plant, sampleStructure, site, type Structure } from "../structure/testData.ts";
import {
  buildMapGraph,
  formatIpv6,
  graphSignature,
  gridLayout,
  isEdgeHighlighted,
  type MapGraph,
  type MapNode,
  matchingNodeIds,
  networkOf,
  parseIpv6,
} from "./graph.ts";

function graphOf(structure: Structure): MapGraph {
  return buildMapGraph(structure.sites, structure.areas, structure.plants, structure.devices);
}

function nodeById(graph: MapGraph, id: string): MapNode {
  const node = graph.nodes.find((candidate) => candidate.id === id);
  if (node === undefined) {
    throw new Error(`no node ${id}`);
  }
  return node;
}

interface Box {
  readonly id: string;
  readonly x: number;
  readonly y: number;
  readonly width: number;
  readonly height: number;
}

/** Position of every node in flow coordinates (positions of children are relative to their parent). */
function absoluteBoxes(graph: MapGraph): Map<string, Box> {
  const boxes = new Map<string, Box>();
  for (const node of graph.nodes) {
    const parent = node.parentId === undefined ? undefined : boxes.get(node.parentId);
    if (node.parentId !== undefined && parent === undefined) {
      throw new Error(`parent ${node.parentId} of ${node.id} comes later`);
    }
    boxes.set(node.id, {
      id: node.id,
      x: (parent?.x ?? 0) + node.position.x,
      y: (parent?.y ?? 0) + node.position.y,
      width: node.width ?? 0,
      height: node.height ?? 0,
    });
  }
  return boxes;
}

function overlap(left: Box, right: Box): boolean {
  return (
    left.x < right.x + right.width &&
    right.x < left.x + left.width &&
    left.y < right.y + right.height &&
    right.y < left.y + left.height
  );
}

/** Siblings never overlap, every child lies inside its parent, every size is positive. */
function expectReadableLayout(graph: MapGraph): void {
  const boxes = absoluteBoxes(graph);
  const siblings = new Map<string, Box[]>();
  for (const node of graph.nodes) {
    const box = boxes.get(node.id);
    if (box === undefined) {
      throw new Error(`no box for ${node.id}`);
    }
    expect(box.width, node.id).toBeGreaterThan(0);
    expect(box.height, node.id).toBeGreaterThan(0);
    const parentKey = node.parentId ?? "(top)";
    siblings.set(parentKey, [...(siblings.get(parentKey) ?? []), box]);
    if (node.parentId !== undefined) {
      const parent = boxes.get(node.parentId);
      if (parent === undefined) {
        throw new Error(`no parent box for ${node.id}`);
      }
      expect(box.x, `${node.id} left`).toBeGreaterThanOrEqual(parent.x);
      expect(box.y, `${node.id} top`).toBeGreaterThanOrEqual(parent.y);
      expect(box.x + box.width, `${node.id} right`).toBeLessThanOrEqual(parent.x + parent.width);
      expect(box.y + box.height, `${node.id} bottom`).toBeLessThanOrEqual(parent.y + parent.height);
    }
  }
  for (const group of siblings.values()) {
    for (const [index, left] of group.entries()) {
      for (const right of group.slice(index + 1)) {
        expect(overlap(left, right), `${left.id} overlaps ${right.id}`).toBe(false);
      }
    }
  }
}

/** Fisher-Yates with a fixed sequence, so the test itself stays deterministic. */
function shuffled<T>(items: readonly T[], seed: number): T[] {
  const result = [...items];
  let state = seed;
  for (let index = result.length - 1; index > 0; index -= 1) {
    state = (state * 1103515245 + 12345) % 2147483648;
    const other = state % (index + 1);
    const current = result[index] as T;
    result[index] = result[other] as T;
    result[other] = current;
  }
  return result;
}

describe("networkOf", () => {
  it.each([
    ["192.0.2.10", "192.0.2.0/24", 4],
    ["192.0.2.255", "192.0.2.0/24", 4],
    ["10.1.2.3", "10.1.2.0/24", 4],
    ["2001:db8:0:1::5", "2001:db8:0:1::/64", 6],
    ["2001:DB8::1", "2001:db8::/64", 6],
    ["2001:db8:aa:bb:cc:dd:ee:ff", "2001:db8:aa:bb::/64", 6],
    ["fe80::1", "fe80::/64", 6],
    ["::1", "::/64", 6],
    ["::ffff:192.0.2.1", "::/64", 6],
  ] as const)("puts %s into %s", (address, cidr, family) => {
    expect(networkOf(address)).toMatchObject({ cidr, family });
  });

  it.each([null, "", "not an address", "192.0.2.256", "192.0.2", "2001:db8::1::2", "2001:db8:0:0:0:0:0:0:1", "12345::"])(
    "has no network for %s",
    (address) => {
      expect(networkOf(address)).toBeNull();
    },
  );

  it("reads IPv6 addresses with and without an IPv4 tail", () => {
    expect(parseIpv6("::")).toEqual([0, 0, 0, 0, 0, 0, 0, 0]);
    expect(parseIpv6("::ffff:192.0.2.1")).toEqual([0, 0, 0, 0, 0, 0xffff, 0xc000, 0x0201]);
    expect(parseIpv6("1:2:3:4:5:6:7:8")).toEqual([1, 2, 3, 4, 5, 6, 7, 8]);
    expect(parseIpv6("1:2:3:4:5:6:7")).toBeNull();
  });

  it("writes IPv6 networks as RFC 5952 recommends", () => {
    expect(formatIpv6([0, 0, 0, 0, 0, 0, 0, 0])).toBe("::");
    expect(formatIpv6([0x2001, 0xdb8, 0, 0, 1, 0, 0, 1])).toBe("2001:db8::1:0:0:1");
    expect(formatIpv6([0x2001, 0xdb8, 0, 1, 0, 0, 0, 0])).toBe("2001:db8:0:1::");
    expect(formatIpv6([1, 0, 2, 0, 3, 0, 4, 0])).toBe("1:0:2:0:3:0:4:0");
  });
});

describe("gridLayout", () => {
  it("places children in an about square grid without overlap", () => {
    const sizes = [
      { width: 100, height: 50 },
      { width: 60, height: 80 },
      { width: 100, height: 50 },
      { width: 40, height: 20 },
      { width: 100, height: 50 },
    ];
    const { positions, size } = gridLayout(sizes, 4, 10);
    expect(positions).toEqual([
      { x: 0, y: 0 },
      { x: 110, y: 0 },
      { x: 220, y: 0 },
      { x: 0, y: 90 },
      { x: 110, y: 90 },
    ]);
    expect(size).toEqual({ width: 320, height: 140 });
  });

  it("is empty without children and respects the column limit", () => {
    expect(gridLayout([], 3, 10)).toEqual({ positions: [], size: { width: 0, height: 0 } });
    const many = Array.from({ length: 9 }, () => ({ width: 10, height: 10 }));
    expect(new Set(gridLayout(many, 2, 0).positions.map((position) => position.x))).toEqual(new Set([0, 10]));
  });
});

describe("buildMapGraph", () => {
  it("makes groups of sites, areas and plants with devices inside their plant", () => {
    const graph = graphOf(sampleStructure());

    expect(graph.nodes.map((node) => node.id)).toEqual([
      "site:1",
      "area:10",
      "plant:100",
      "device:1001",
      "device:1002",
      "device:1000",
      "plant:101",
      "area:11",
      "plant:102",
      "device:1003",
      "site:2",
      "network:192.0.2.0/24",
    ]);
    expect(nodeById(graph, "area:10").parentId).toBe("site:1");
    expect(nodeById(graph, "plant:102").parentId).toBe("area:11");
    expect(nodeById(graph, "device:1000").parentId).toBe("plant:100");
    expect(nodeById(graph, "device:1000").extent).toBe("parent");
    expect(nodeById(graph, "site:1").parentId).toBeUndefined();
    expect(nodeById(graph, "network:192.0.2.0/24").parentId).toBeUndefined();

    expect(nodeById(graph, "plant:100").data).toMatchObject({ kind: "plant", name: "Test plant one", key: "test-plant-1" });
    expect(nodeById(graph, "site:2").data).toMatchObject({ kind: "site", name: "Test site B", key: null, deviceCount: 0 });
    expect(nodeById(graph, "device:1000").data).toEqual({
      kind: "device",
      deviceId: 1000,
      name: "Test controller",
      key: "test-plc-1",
      ip: "192.0.2.10",
      model: "Test model",
      network: "192.0.2.0/24",
    });
    expect(nodeById(graph, "network:192.0.2.0/24").data).toEqual({
      kind: "network",
      cidr: "192.0.2.0/24",
      family: 4,
      deviceCount: 3,
    });
  });

  it("draws only 'device is in network' edges, none for devices without an address", () => {
    const graph = graphOf(sampleStructure());

    expect(graph.edges.map((edge) => [edge.source, edge.target])).toEqual([
      ["device:1001", "network:192.0.2.0/24"],
      ["device:1000", "network:192.0.2.0/24"],
      ["device:1003", "network:192.0.2.0/24"],
    ]);
    // test-io-1 has no address.
    expect(graph.edges.some((edge) => edge.source === "device:1002" || edge.target === "device:1002")).toBe(false);
    for (const edge of graph.edges) {
      expect(edge.source.startsWith("device:")).toBe(true);
      expect(edge.target.startsWith("network:")).toBe(true);
    }
  });

  it("makes one network node per IPv4 /24 and IPv6 /64, IPv4 first, sorted by address", () => {
    const base = sampleStructure();
    const extra = (id: number, key: string, ip: string): Device => device(base, id, 101, key, `Test ${key}`, { ip_address: ip });
    const structure: Structure = {
      ...base,
      devices: [
        ...base.devices,
        extra(2000, "test-v6-a", "2001:db8:0:2::10"),
        extra(2001, "test-v6-b", "2001:db8:0:2::11"),
        extra(2002, "test-v6-c", "2001:db8:0:1::1"),
        extra(2003, "test-v4-far", "198.51.100.7"),
        extra(2004, "test-v4-near", "192.0.20.1"),
      ],
    };
    const graph = graphOf(structure);

    const networks = graph.nodes.filter((node) => node.type === "network");
    expect(networks.map((node) => node.data)).toEqual([
      { kind: "network", cidr: "192.0.2.0/24", family: 4, deviceCount: 3 },
      { kind: "network", cidr: "192.0.20.0/24", family: 4, deviceCount: 1 },
      { kind: "network", cidr: "198.51.100.0/24", family: 4, deviceCount: 1 },
      { kind: "network", cidr: "2001:db8:0:1::/64", family: 6, deviceCount: 1 },
      { kind: "network", cidr: "2001:db8:0:2::/64", family: 6, deviceCount: 2 },
    ]);
    expect(graph.edges).toHaveLength(8);
    expect(graph.edges.find((edge) => edge.source === "device:2000")?.target).toBe("network:2001:db8:0:2::/64");
    expectReadableLayout(graph);
  });

  it("is empty without a structure", () => {
    expect(buildMapGraph([], [], [], [])).toEqual({ nodes: [], edges: [] });
  });

  it("shows sites, areas and plants without devices, and no network without addresses", () => {
    const structure: Structure = {
      sites: [site(1, "Test site")],
      areas: [area(10, 1, "Test area")],
      plants: [plant(100, 10, "test-plant", "Test plant")],
      devices: [],
    };
    structure.devices = [device(structure, 1000, 100, "test-device", "Test device")];
    const graph = graphOf(structure);

    expect(graph.nodes.map((node) => node.id)).toEqual(["site:1", "area:10", "plant:100", "device:1000"]);
    expect(graph.edges).toEqual([]);
    expectReadableLayout(graph);
  });

  it("gives the same layout for the same data in any order", () => {
    const structure = sampleStructure();
    const reference = graphOf(structure);

    for (const seed of [1, 7, 42, 1234]) {
      const graph = buildMapGraph(
        shuffled(structure.sites, seed),
        shuffled(structure.areas, seed + 1),
        shuffled(structure.plants, seed + 2),
        shuffled(structure.devices, seed + 3),
      );
      expect(graph).toEqual(reference);
      expect(graphSignature(graph)).toBe(graphSignature(reference));
    }
    expect(graphOf(sampleStructure())).toEqual(reference);
  });

  it("changes the signature when the data changes", () => {
    const structure = sampleStructure();
    const before = graphSignature(graphOf(structure));
    const changed = {
      ...structure,
      devices: structure.devices.map((item) => (item.id === 1002 ? { ...item, ip_address: "192.0.2.12" } : item)),
    };
    expect(graphSignature(graphOf(changed))).not.toBe(before);
  });

  it("lays out a larger structure without overlap: siblings apart, children inside their parent", () => {
    const sites = [site(1, "Test site A"), site(2, "Test site B"), site(3, "Test site C")];
    const areas = sites.flatMap((item) => [1, 2, 3].map((n) => area(item.id * 10 + n, item.id, `Test area ${String(n)}`)));
    const plants = areas.flatMap((item) =>
      Array.from({ length: (item.id % 5) + 1 }, (_, n) => plant(item.id * 10 + n, item.id, `test-plant-${String(item.id)}-${String(n)}`, "Test plant")),
    );
    const base = { sites, areas, plants };
    const devices = plants.flatMap((item, index) =>
      Array.from({ length: index % 7 }, (_, n) =>
        device(base, item.id * 10 + n, item.id, `test-device-${String(item.id)}-${String(n)}`, "Test device", {
          ip_address: n % 3 === 0 ? null : `192.0.2.${String(1 + ((index * 7 + n) % 250))}`,
        }),
      ),
    );
    const graph = buildMapGraph(sites, areas, plants, devices);

    expect(graph.nodes.filter((node) => node.type === "device")).toHaveLength(devices.length);
    expectReadableLayout(graph);
    // The network column lies right of all sites.
    const boxes = absoluteBoxes(graph);
    const rightmostSite = Math.max(...sites.map((item) => {
      const box = boxes.get(`site:${String(item.id)}`);
      return box === undefined ? 0 : box.x + box.width;
    }));
    expect(boxes.get("network:192.0.2.0/24")?.x).toBeGreaterThan(rightmostSite);
  });
});

describe("search and highlighting", () => {
  const graph = graphOf(sampleStructure());

  it("finds nodes by name, key and IP address, ignoring case", () => {
    expect(matchingNodeIds(graph.nodes, "test controller")).toEqual(["device:1000"]);
    expect(matchingNodeIds(graph.nodes, "TEST-HMI-1")).toEqual(["device:1001"]);
    expect(matchingNodeIds(graph.nodes, "192.0.2.20")).toEqual(["device:1003"]);
    expect(matchingNodeIds(graph.nodes, "test-plant-3")).toEqual(["plant:102"]);
    expect(matchingNodeIds(graph.nodes, "site b")).toEqual(["site:2"]);
    expect(matchingNodeIds(graph.nodes, "0/24")).toEqual(["network:192.0.2.0/24"]);
    expect(matchingNodeIds(graph.nodes, "192.0.2.")).toEqual([
      "device:1001",
      "device:1000",
      "device:1003",
      "network:192.0.2.0/24",
    ]);
  });

  it("finds nothing for an empty query or an unknown text", () => {
    expect(matchingNodeIds(graph.nodes, "   ")).toEqual([]);
    expect(matchingNodeIds(graph.nodes, "no such thing")).toEqual([]);
  });

  it("highlights the network edge of highlighted devices only", () => {
    const highlighted = new Set([1000]);
    expect(graph.edges.filter((edge) => isEdgeHighlighted(edge, highlighted)).map((edge) => edge.source)).toEqual([
      "device:1000",
    ]);
    expect(graph.edges.some((edge) => isEdgeHighlighted(edge, new Set()))).toBe(false);
  });
});
