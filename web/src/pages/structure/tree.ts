// The structure as a tree (site > area > plant > device) and the search in the browser.
//
// The four lists come from the API in one piece each (GET /api/v1/sites/ …);
// at the size of a plant directory the browser builds the tree and filters it
// itself (work order 032).
import type { Area, Device, Plant, Site } from "../../api/generated";

export interface PlantNode {
  readonly plant: Plant;
  readonly devices: readonly Device[];
  /** Devices of this plant (not reduced by a search). */
  readonly deviceCount: number;
}

export interface AreaNode {
  readonly area: Area;
  readonly plants: readonly PlantNode[];
  readonly deviceCount: number;
}

export interface SiteNode {
  readonly site: Site;
  readonly areas: readonly AreaNode[];
  readonly deviceCount: number;
}

const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });

function byName(left: { readonly name: string }, right: { readonly name: string }): number {
  return collator.compare(left.name, right.name);
}

function byKey(left: { readonly key: string }, right: { readonly key: string }): number {
  return collator.compare(left.key, right.key);
}

function groupBy<T>(items: readonly T[], parentId: (item: T) => number): Map<number, T[]> {
  const groups = new Map<number, T[]>();
  for (const item of items) {
    const id = parentId(item);
    const group = groups.get(id);
    if (group === undefined) {
      groups.set(id, [item]);
    } else {
      group.push(item);
    }
  }
  return groups;
}

function sum(values: readonly { readonly deviceCount: number }[]): number {
  return values.reduce((total, value) => total + value.deviceCount, 0);
}

/**
 * Builds the tree. Sites and areas are sorted by name, plants and devices by
 * key. Items whose parent is not in the lists (possible only while another
 * user moves something) are left out.
 */
export function buildTree(
  sites: readonly Site[],
  areas: readonly Area[],
  plants: readonly Plant[],
  devices: readonly Device[],
): SiteNode[] {
  const areasBySite = groupBy(areas, (area) => area.site);
  const plantsByArea = groupBy(plants, (plant) => plant.area);
  const devicesByPlant = groupBy(devices, (device) => device.plant.id);

  return [...sites].sort(byName).map((site): SiteNode => {
    const areaNodes = [...(areasBySite.get(site.id) ?? [])].sort(byName).map((area): AreaNode => {
      const plantNodes = [...(plantsByArea.get(area.id) ?? [])].sort(byKey).map((plant): PlantNode => {
        const plantDevices = [...(devicesByPlant.get(plant.id) ?? [])].sort(byKey);
        return { plant, devices: plantDevices, deviceCount: plantDevices.length };
      });
      return { area, plants: plantNodes, deviceCount: sum(plantNodes) };
    });
    return { site, areas: areaNodes, deviceCount: sum(areaNodes) };
  });
}

/** The search text as compared: trimmed and in lower case. */
export function normaliseQuery(query: string): string {
  return query.trim().toLocaleLowerCase();
}

function matches(query: string, ...texts: readonly (string | null)[]): boolean {
  return texts.some((text) => text !== null && text.toLocaleLowerCase().includes(query));
}

/** True if the device's name, key or IP address contains the (normalised) query. */
export function deviceMatches(device: Device, query: string): boolean {
  return matches(query, device.name, device.key, device.ip_address);
}

/**
 * The part of the tree that matches the search. A site, area or plant whose
 * name (plants: or key) contains the query is shown with everything below it;
 * otherwise it is shown only with the children that match. Devices match by
 * name, key or IP address. An empty query keeps the whole tree. The device
 * counts stay those of the whole structure.
 */
export function filterTree(tree: readonly SiteNode[], query: string): SiteNode[] {
  const needle = normaliseQuery(query);
  if (needle === "") {
    return [...tree];
  }
  const result: SiteNode[] = [];
  for (const siteNode of tree) {
    if (matches(needle, siteNode.site.name)) {
      result.push(siteNode);
      continue;
    }
    const areas: AreaNode[] = [];
    for (const areaNode of siteNode.areas) {
      if (matches(needle, areaNode.area.name)) {
        areas.push(areaNode);
        continue;
      }
      const plants: PlantNode[] = [];
      for (const plantNode of areaNode.plants) {
        if (matches(needle, plantNode.plant.name, plantNode.plant.key)) {
          plants.push(plantNode);
          continue;
        }
        const devices = plantNode.devices.filter((device) => deviceMatches(device, needle));
        if (devices.length > 0) {
          plants.push({ ...plantNode, devices });
        }
      }
      if (plants.length > 0) {
        areas.push({ ...areaNode, plants });
      }
    }
    if (areas.length > 0) {
      result.push({ ...siteNode, areas });
    }
  }
  return result;
}
