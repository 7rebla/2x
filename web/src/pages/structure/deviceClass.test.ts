import { describe, expect, it } from "vitest";

import assetsDe from "../../locales/de/assets.json";
import assetsEn from "../../locales/en/assets.json";
import { DEFAULT_DEVICE_CLASS, deviceClasses, isDeviceClass } from "./deviceClass.ts";

describe("device classes", () => {
  it("are the seven classes of E-53 in a fixed order", () => {
    expect(deviceClasses).toEqual(["plc", "controller", "computer", "router", "firewall", "robot", "other"]);
    expect(DEFAULT_DEVICE_CLASS).toBe("other");
  });

  it("tells known classes from other text", () => {
    for (const value of deviceClasses) {
      expect(isDeviceClass(value)).toBe(true);
    }
    for (const value of ["", "PLC", "sps", "switch", "toString", "constructor", "__proto__"]) {
      expect(isDeviceClass(value)).toBe(false);
    }
  });

  it("have a label in both languages", () => {
    expect(Object.keys(assetsEn.deviceClass)).toEqual([...deviceClasses]);
    expect(Object.keys(assetsDe.deviceClass)).toEqual([...deviceClasses]);
  });
});
