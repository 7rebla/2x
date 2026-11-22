// The device classes of E-53: a fixed choice the API checks; the web UI shows
// the label deviceClass.<value> of assets.json and the icon deviceClassIcon()
// names (work order 074). This is the only place that maps a class to an icon.
import type { DeviceClassEnum } from "../../api/generated";
import type { IconName } from "../../icons/names.ts";

// `satisfies` makes the type checker report a class that the API knows and
// this table misses, or one that the API does not know. The order is the
// order the form offers the classes; each class names its icon.
const ICONS = {
  plc: "devicePlc",
  controller: "deviceController",
  computer: "deviceComputer",
  router: "deviceRouter",
  firewall: "deviceFirewall",
  robot: "deviceRobot",
  other: "device",
} as const satisfies Record<DeviceClassEnum, IconName>;

/** Every device class, in the order the form offers them. */
export const deviceClasses = Object.keys(ICONS) as readonly DeviceClassEnum[];

/** The class of a new device and of a device the API names no class for. */
export const DEFAULT_DEVICE_CLASS: DeviceClassEnum = "other";

/** True if `value` is one of the device classes. */
export function isDeviceClass(value: string): value is DeviceClassEnum {
  return Object.hasOwn(ICONS, value);
}

/**
 * Icon of a device class. `other`, a missing value and a value this version
 * does not know all show the generic device icon.
 */
export function deviceClassIcon(value: string | null | undefined): IconName {
  return value !== null && value !== undefined && isDeviceClass(value) ? ICONS[value] : "device";
}

/** Icon of a plant (Anlage); plants have no class of their own yet. */
export const PLANT_ICON: IconName = "plant";
