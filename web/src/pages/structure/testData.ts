// Test helper: a small structure and a fake of the structure API behind fetch.
// Names are plain test names, IP addresses come from 192.0.2.0/24 (RFC 5737).
import type { Area, Device, Plant, Site } from "../../api/generated";
import { type Handler, jsonResponse } from "../../test/fakeApi.ts";

const STAMP = "2026-11-21T10:00:00Z";

export function site(id: number, name: string): Site {
  return { id, name, created_at: STAMP, updated_at: STAMP };
}

export function area(id: number, siteId: number, name: string): Area {
  return { id, site: siteId, name, created_at: STAMP, updated_at: STAMP };
}

export function plant(id: number, areaId: number, key: string, name: string): Plant {
  return { id, area: areaId, key, name, notes: "", created_at: STAMP, updated_at: STAMP };
}

export interface Structure {
  sites: Site[];
  areas: Area[];
  plants: Plant[];
  devices: Device[];
}

export function device(
  structure: Pick<Structure, "sites" | "areas" | "plants">,
  id: number,
  plantId: number,
  key: string,
  name: string,
  more: Partial<Omit<Device, "id" | "plant" | "area" | "site" | "key" | "name">> = {},
): Device {
  const owner = structure.plants.find((item) => item.id === plantId);
  const ownerArea = structure.areas.find((item) => item.id === owner?.area);
  const ownerSite = structure.sites.find((item) => item.id === ownerArea?.site);
  if (owner === undefined || ownerArea === undefined || ownerSite === undefined) {
    throw new Error(`test data: no plant ${String(plantId)} with area and site`);
  }
  return {
    id,
    plant: { id: owner.id, key: owner.key, name: owner.name },
    area: { id: ownerArea.id, name: ownerArea.name },
    site: { id: ownerSite.id, name: ownerSite.name },
    key,
    name,
    manufacturer: "",
    model: "",
    software_version: "",
    ip_address: null,
    address_source: "",
    protocols: "",
    notes: "",
    created_at: STAMP,
    updated_at: STAMP,
    ...more,
  };
}

/**
 * Two sites; the first with two areas. Devices: three in plant 1, one in plant 3,
 * none in plant 2 and none in site 2.
 */
export function sampleStructure(): Structure {
  const base = {
    sites: [site(1, "Test site A"), site(2, "Test site B")],
    areas: [area(10, 1, "Test area A1"), area(11, 1, "Test area A2")],
    plants: [
      plant(100, 10, "test-plant-1", "Test plant one"),
      plant(101, 10, "test-plant-2", "Test plant two"),
      plant(102, 11, "test-plant-3", "Test plant three"),
    ],
  };
  return {
    ...base,
    devices: [
      device(base, 1000, 100, "test-plc-1", "Test controller", {
        ip_address: "192.0.2.10",
        manufacturer: "Test maker",
        model: "Test model",
        software_version: "1.0.0",
        address_source: "Line one of the source\nLine two of the source",
        protocols: "Test protocol",
        notes: "First line of the notes\nSecond line of the notes",
      }),
      device(base, 1001, 100, "test-hmi-1", "Test panel", { ip_address: "192.0.2.11" }),
      device(base, 1002, 100, "test-io-1", "Test remote I/O"),
      device(base, 1003, 102, "test-drive-1", "Test drive", { ip_address: "192.0.2.20" }),
    ],
  };
}

export interface FakeStructureApi {
  readonly handler: Handler;
  readonly structure: Structure;
  /** Answer of the next write call instead of storing it (for example a 400 with field errors). */
  rejectNextWrite: (status: number, body: unknown) => void;
}

async function readJson(request: Request): Promise<Record<string, unknown>> {
  // A copy, so that tests can read the body of the recorded request as well.
  const body: unknown = await request.clone().json();
  if (typeof body !== "object" || body === null) {
    throw new Error("test API: body is not an object");
  }
  return body as Record<string, unknown>;
}

const LIST = /^\/api\/v1\/(sites|areas|plants|devices)\/$/;
const ITEM = /^\/api\/v1\/(sites|areas|plants|devices)\/(\d+)\/$/;

/**
 * Serves the structure lists, single devices and the write calls. Written
 * items are stored, so a reload after saving shows them.
 */
export function fakeStructureApi(structure: Structure = sampleStructure()): FakeStructureApi {
  let rejection: { status: number; body: unknown } | null = null;
  let nextId = 5000;

  const store = (kind: string, id: number, fields: Record<string, unknown>): unknown => {
    switch (kind) {
      case "sites": {
        const item = site(id, String(fields.name));
        structure.sites = [...structure.sites.filter((other) => other.id !== id), item];
        return item;
      }
      case "areas": {
        const item = area(id, Number(fields.site), String(fields.name));
        structure.areas = [...structure.areas.filter((other) => other.id !== id), item];
        return item;
      }
      case "plants": {
        const item = { ...plant(id, Number(fields.area), String(fields.key), String(fields.name)), notes: typeof fields.notes === "string" ? fields.notes : "" };
        structure.plants = [...structure.plants.filter((other) => other.id !== id), item];
        return item;
      }
      default: {
        const { plant: plantId, key, name, ...rest } = fields;
        const item = device(structure, id, Number(plantId), String(key), String(name), rest);
        structure.devices = [...structure.devices.filter((other) => other.id !== id), item];
        return item;
      }
    }
  };

  const handler: Handler = async (request) => {
    const path = new URL(request.url).pathname;
    const list = LIST.exec(path);
    const item = ITEM.exec(path);
    if (request.method !== "GET" && rejection !== null) {
      const answer = rejection;
      rejection = null;
      return jsonResponse(answer.body, answer.status);
    }
    if (list !== null && request.method === "GET") {
      const kind = list[1] as keyof Structure;
      return jsonResponse(structure[kind]);
    }
    if (list !== null && request.method === "POST") {
      nextId += 1;
      return jsonResponse(store(list[1] ?? "", nextId, await readJson(request)), 201);
    }
    if (item !== null) {
      const kind = item[1] as keyof Structure;
      const id = Number(item[2]);
      const found = structure[kind].find((entry) => entry.id === id);
      if (found === undefined) {
        return jsonResponse({ detail: "No Device matches the given query." }, 404);
      }
      if (request.method === "GET") {
        return jsonResponse(found);
      }
      if (request.method === "PUT") {
        return jsonResponse(store(item[1] ?? "", id, await readJson(request)));
      }
    }
    return jsonResponse({ detail: "Not found." }, 404);
  };

  return {
    handler,
    structure,
    rejectNextWrite: (status, body) => {
      rejection = { status, body };
    },
  };
}
