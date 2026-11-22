// Devices grouped by plant for a choice of one device (<optgroup> per plant).
// Shared by the search page and the answer page (work order 133).
import type { Device } from "../api/generated";

/** Devices sorted by plant, then by name, then by key. */
function sortedDevices(devices: readonly Device[]): Device[] {
  return [...devices].sort(
    (a, b) =>
      a.plant.name.localeCompare(b.plant.name) || a.name.localeCompare(b.name) || a.key.localeCompare(b.key),
  );
}

/** Devices grouped by plant, in the order of sortedDevices. */
export function devicesByPlant(devices: readonly Device[]): { plantId: number; plantName: string; devices: Device[] }[] {
  const groups: { plantId: number; plantName: string; devices: Device[] }[] = [];
  for (const device of sortedDevices(devices)) {
    const last = groups.at(-1);
    if (last?.plantId === device.plant.id) {
      last.devices.push(device);
    } else {
      groups.push({ plantId: device.plant.id, plantName: device.plant.name, devices: [device] });
    }
  }
  return groups;
}
