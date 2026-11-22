import { describe, expect, it } from "vitest";

import assetsDe from "../../locales/de/assets.json";
import assetsEn from "../../locales/en/assets.json";
import { iconNames } from "../../icons/names.ts";
import { DEFAULT_DEVICE_CLASS, deviceClasses, deviceClassIcon, isDeviceClass, PLANT_ICON } from "./deviceClass.ts";

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

describe("deviceClassIcon", () => {
  it.each([
    ["plc", "devicePlc"],
    ["controller", "deviceController"],
    ["computer", "deviceComputer"],
    ["router", "deviceRouter"],
    ["firewall", "deviceFirewall"],
    ["robot", "deviceRobot"],
    ["other", "device"],
  ] as const)("shows %s with the icon %s", (value, icon) => {
    expect(deviceClassIcon(value)).toBe(icon);
  });

  it("covers every class, each with an icon of the table and only other without its own", () => {
    const icons = deviceClasses.map(deviceClassIcon);
    for (const icon of icons) {
      expect(iconNames).toContain(icon);
    }
    expect(new Set(icons).size).toBe(deviceClasses.length);
    expect(deviceClasses.filter((value) => deviceClassIcon(value) === "device")).toEqual(["other"]);
  });

  it.each([undefined, null, "", "switch", "PLC", "__proto__", "toString"])(
    "falls back to the generic device icon for %s",
    (value) => {
      expect(deviceClassIcon(value)).toBe("device");
    },
  );

  it("shows plants with the plant icon", () => {
    expect(PLANT_ICON).toBe("plant");
  });
});
