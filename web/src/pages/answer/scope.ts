// The limit of the answer page to one device or one plant (work order 133).
//
// The limit stands in the browser address (/ask?device=… or /ask?plant=…, the
// E-54 pattern of the search), so it can be linked, reloaded and reached with
// Back. The question never does: it goes only into the body of the request.
// At most one of the two is set; the search API joins filters with AND, so a
// device together with another plant would never find anything.
import { parseId } from "../../components/files/format.ts";

/** The device or the plant an answer is limited to (ids); both null: all devices. */
export interface ScopeAddress {
  readonly device: number | null;
  readonly plant: number | null;
}

export const ALL_DEVICES: ScopeAddress = { device: null, plant: null };

/** The id in `raw`, or null if it cannot be an id (then it counts as "all"). */
function parseScopeId(raw: string | null): number | null {
  return parseId(raw ?? undefined);
}

/**
 * Reads ?device= and ?plant= from the address. A value that cannot be an id
 * counts as "all". If both are valid, the device wins (it is the narrower one).
 */
export function readScopeAddress(params: URLSearchParams): ScopeAddress {
  const device = parseScopeId(params.get("device"));
  if (device !== null) {
    return { device, plant: null };
  }
  return { device: null, plant: parseScopeId(params.get("plant")) };
}

/**
 * The address parameters with `scope` in place of the old limit; every other
 * parameter (?q= of work order 132) stays as it is.
 */
export function withScopeAddress(params: URLSearchParams, scope: ScopeAddress): URLSearchParams {
  const next = new URLSearchParams(params);
  next.delete("device");
  next.delete("plant");
  if (scope.device !== null) {
    next.set("device", String(scope.device));
  } else if (scope.plant !== null) {
    next.set("plant", String(scope.plant));
  }
  return next;
}

/** The value of a choice ("" for all) as a scope; choosing a device resets the plant and the other way round. */
export function chooseDevice(value: string): ScopeAddress {
  return { device: parseScopeId(value), plant: null };
}

export function choosePlant(value: string): ScopeAddress {
  return { device: null, plant: parseScopeId(value) };
}
