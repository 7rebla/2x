// Which branches of the structure tree are folded in (work order 083).
//
// Areas and plants can be folded; the choice is kept per browser in
// localStorage. Every access is wrapped in try/catch: without a usable storage
// (private window, blocked site data) the tree starts unfolded and the choice
// lasts until the page is reloaded.

/** A foldable branch: an area or a plant, by id ("area:10", "plant:100"). */
export type BranchKey = `area:${string}` | `plant:${string}`;

/** localStorage key of the folded branches (a JSON list of branch keys). */
export const COLLAPSED_STORAGE_KEY = "twox.structure.collapsed";

const BRANCH_KEY = /^(?:area|plant):\d+$/;

export function areaKey(id: number): BranchKey {
  return `area:${String(id)}`;
}

export function plantKey(id: number): BranchKey {
  return `plant:${String(id)}`;
}

function isBranchKey(value: unknown): value is BranchKey {
  return typeof value === "string" && BRANCH_KEY.test(value);
}

/** The folded branches stored in this browser; anything unreadable counts as none. */
export function readCollapsed(): ReadonlySet<BranchKey> {
  try {
    const stored = window.localStorage.getItem(COLLAPSED_STORAGE_KEY);
    if (stored === null) {
      return new Set();
    }
    const parsed: unknown = JSON.parse(stored);
    return new Set(Array.isArray(parsed) ? parsed.filter(isBranchKey) : []);
  } catch {
    return new Set();
  }
}

/** Stores the folded branches; an empty set removes the key. */
export function writeCollapsed(keys: ReadonlySet<BranchKey>): void {
  try {
    if (keys.size === 0) {
      window.localStorage.removeItem(COLLAPSED_STORAGE_KEY);
    } else {
      window.localStorage.setItem(COLLAPSED_STORAGE_KEY, JSON.stringify([...keys].sort()));
    }
  } catch {
    // No usable storage: the choice lasts until the page is reloaded.
  }
}

/** A copy of `keys` with `key` added (`present`) or removed. */
export function withKey(keys: ReadonlySet<BranchKey>, key: BranchKey, present: boolean): ReadonlySet<BranchKey> {
  if (keys.has(key) === present) {
    return keys;
  }
  const next = new Set(keys);
  if (present) {
    next.add(key);
  } else {
    next.delete(key);
  }
  return next;
}
