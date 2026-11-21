import { describe, expect, it } from "vitest";

import { sampleStructure } from "./testData.ts";
import { buildTree, filterTree, type SiteNode } from "./tree.ts";

function sampleTree(): SiteNode[] {
  const { sites, areas, plants, devices } = sampleStructure();
  return buildTree(sites, areas, plants, devices);
}

/** The tree as nested names, for readable comparisons. */
function outline(tree: readonly SiteNode[]): unknown {
  return tree.map((siteNode) => [
    siteNode.site.name,
    siteNode.areas.map((areaNode) => [
      areaNode.area.name,
      areaNode.plants.map((plantNode) => [plantNode.plant.key, plantNode.devices.map((device) => device.key)]),
    ]),
  ]);
}

describe("buildTree", () => {
  it("nests sites, areas, plants and devices, sorted by name and key", () => {
    expect(outline(sampleTree())).toEqual([
      [
        "Test site A",
        [
          [
            "Test area A1",
            [
              ["test-plant-1", ["test-hmi-1", "test-io-1", "test-plc-1"]],
              ["test-plant-2", []],
            ],
          ],
          ["Test area A2", [["test-plant-3", ["test-drive-1"]]]],
        ],
      ],
      ["Test site B", []],
    ]);
  });

  it("counts the devices on every level", () => {
    const [siteA, siteB] = sampleTree();
    expect(siteA?.deviceCount).toBe(4);
    expect(siteA?.areas.map((areaNode) => areaNode.deviceCount)).toEqual([3, 1]);
    expect(siteA?.areas[0]?.plants.map((plantNode) => plantNode.deviceCount)).toEqual([3, 0]);
    expect(siteB?.deviceCount).toBe(0);
  });

  it("sorts numbers in names naturally", () => {
    const { areas, plants, devices } = sampleStructure();
    const sites = [
      { id: 3, name: "Site 10", created_at: "", updated_at: "" },
      { id: 4, name: "site 9", created_at: "", updated_at: "" },
    ];
    expect(buildTree(sites, areas, plants, devices).map((node) => node.site.name)).toEqual(["site 9", "Site 10"]);
  });

  it("leaves out items whose parent is missing", () => {
    const { sites, areas, plants, devices } = sampleStructure();
    const tree = buildTree(sites, areas.slice(1), plants, devices);
    expect(outline(tree)).toEqual([
      ["Test site A", [["Test area A2", [["test-plant-3", ["test-drive-1"]]]]]],
      ["Test site B", []],
    ]);
  });
});

describe("filterTree", () => {
  it("keeps everything for an empty or blank query", () => {
    const tree = sampleTree();
    expect(filterTree(tree, "")).toEqual(tree);
    expect(filterTree(tree, "   ")).toEqual(tree);
  });

  it("finds a device by name, key or IP address, ignoring case and spaces around", () => {
    const tree = sampleTree();
    const onlyDrive = [["Test site A", [["Test area A2", [["test-plant-3", ["test-drive-1"]]]]]]];
    expect(outline(filterTree(tree, "TEST DRIVE"))).toEqual(onlyDrive);
    expect(outline(filterTree(tree, " test-drive-1 "))).toEqual(onlyDrive);
    expect(outline(filterTree(tree, "192.0.2.20"))).toEqual(onlyDrive);
  });

  it("an IP address part matches every device that contains it", () => {
    expect(outline(filterTree(sampleTree(), "192.0.2.1"))).toEqual([
      ["Test site A", [["Test area A1", [["test-plant-1", ["test-hmi-1", "test-plc-1"]]]]]],
    ]);
  });

  it("shows a matching site, area or plant with everything below it", () => {
    const tree = sampleTree();
    expect(outline(filterTree(tree, "site b"))).toEqual([["Test site B", []]]);
    expect(outline(filterTree(tree, "area a2"))).toEqual([
      ["Test site A", [["Test area A2", [["test-plant-3", ["test-drive-1"]]]]]],
    ]);
    expect(outline(filterTree(tree, "test-plant-1"))).toEqual([
      ["Test site A", [["Test area A1", [["test-plant-1", ["test-hmi-1", "test-io-1", "test-plc-1"]]]]]],
    ]);
    expect(outline(filterTree(tree, "plant two"))).toEqual([
      ["Test site A", [["Test area A1", [["test-plant-2", []]]]]],
    ]);
  });

  it("keeps the device counts of the whole structure", () => {
    const [siteA] = filterTree(sampleTree(), "test panel");
    expect(siteA?.deviceCount).toBe(4);
    expect(siteA?.areas[0]?.plants[0]?.devices).toHaveLength(1);
    expect(siteA?.areas[0]?.plants[0]?.deviceCount).toBe(3);
  });

  it("returns nothing when nothing matches", () => {
    expect(filterTree(sampleTree(), "no such thing")).toEqual([]);
  });
});
