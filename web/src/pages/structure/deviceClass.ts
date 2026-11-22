// The device classes of E-53: a fixed choice the API checks; the web UI shows
// the label deviceClass.<value> of assets.json (and, later, an icon per class).
import type { DeviceClassEnum } from "../../api/generated";

// `satisfies` makes the type checker report a class that the API knows and
// this list misses, or one that the API does not know.
const ORDER = {
  plc: true,
  controller: true,
  computer: true,
  router: true,
  firewall: true,
  robot: true,
  other: true,
} as const satisfies Record<DeviceClassEnum, true>;

/** Every device class, in the order the form offers them. */
export const deviceClasses = Object.keys(ORDER) as readonly DeviceClassEnum[];

/** The class of a new device and of a device the API names no class for. */
export const DEFAULT_DEVICE_CLASS: DeviceClassEnum = "other";

/** True if `value` is one of the device classes. */
export function isDeviceClass(value: string): value is DeviceClassEnum {
  return Object.hasOwn(ORDER, value);
}
