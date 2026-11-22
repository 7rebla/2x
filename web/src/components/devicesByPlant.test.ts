// devicesByPlant (work order 133): sorted by plant, name and key; one group per plant.
import { describe, expect, it } from "vitest";

import { area, device, plant, site } from "../pages/structure/testData.ts";
import { devicesByPlant } from "./devicesByPlant.ts";

const base = {
  sites: [site(1, "Test site")],
  areas: [area(10, 1, "Test area")],
  plants: [plant(100, 10, "test-plant-b", "Plant B"), plant(101, 10, "test-plant-a", "Plant A")],
};

describe("devicesByPlant", () => {
  it("returns no groups for no devices", () => {
    expect(devicesByPlant([])).toEqual([]);
  });

  it("groups by plant, sorted by plant name, device name and key", () => {
    const devices = [
      device(base, 1, 100, "key-2", "Pump"),
      device(base, 2, 101, "key-9", "Valve"),
      device(base, 3, 100, "key-1", "Pump"),
      device(base, 4, 101, "key-3", "Drive"),
      device(base, 5, 100, "key-5", "Inverter"),
    ];

    const groups = devicesByPlant(devices);

    expect(groups.map((group) => [group.plantId, group.plantName])).toEqual([
      [101, "Plant A"],
      [100, "Plant B"],
    ]);
    expect(groups.map((group) => group.devices.map((item) => item.id))).toEqual([
      [4, 2],
      [5, 3, 1],
    ]);
  });

  it("does not change the given list", () => {
    const devices = [device(base, 1, 100, "key-2", "Pump"), device(base, 2, 101, "key-1", "Drive")];
    devicesByPlant(devices);
    expect(devices.map((item) => item.id)).toEqual([1, 2]);
  });
});
