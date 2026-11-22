import { afterEach, describe, expect, it, vi } from "vitest";

import {
  areaKey,
  type BranchKey,
  COLLAPSED_STORAGE_KEY,
  plantKey,
  readCollapsed,
  withKey,
  writeCollapsed,
} from "./collapse.ts";

afterEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
});

describe("folded branches in localStorage", () => {
  it("names areas and plants by id", () => {
    expect(areaKey(10)).toBe("area:10");
    expect(plantKey(100)).toBe("plant:100");
  });

  it("writes a sorted list and reads it back", () => {
    writeCollapsed(new Set<BranchKey>(["plant:100", "area:10"]));
    expect(window.localStorage.getItem(COLLAPSED_STORAGE_KEY)).toBe('["area:10","plant:100"]');
    expect([...readCollapsed()]).toEqual(["area:10", "plant:100"]);
  });

  it("removes the key when nothing is folded", () => {
    writeCollapsed(new Set<BranchKey>(["area:1"]));
    writeCollapsed(new Set());
    expect(window.localStorage.getItem(COLLAPSED_STORAGE_KEY)).toBeNull();
  });

  it.each([
    ["nothing stored", null, []],
    ["no JSON", "{", []],
    ["no list", '{"area:1": true}', []],
    ["foreign entries", '["area:1", "site:2", 3, "plant:x", "plant:4"]', ["area:1", "plant:4"]],
  ])("reads only branch keys (%s)", (_case, stored, expected) => {
    if (stored !== null) {
      window.localStorage.setItem(COLLAPSED_STORAGE_KEY, stored);
    }
    expect([...readCollapsed()]).toEqual(expected);
  });

  it("works without a usable storage", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(readCollapsed().size).toBe(0);
    expect(() => {
      writeCollapsed(new Set<BranchKey>(["area:1"]));
    }).not.toThrow();
  });
});

describe("withKey", () => {
  it("adds and removes a key without changing the given set", () => {
    const start: ReadonlySet<BranchKey> = new Set<BranchKey>(["area:1"]);
    const added = withKey(start, "plant:2", true);
    expect([...added]).toEqual(["area:1", "plant:2"]);
    expect([...withKey(added, "area:1", false)]).toEqual(["plant:2"]);
    expect([...start]).toEqual(["area:1"]);
  });

  it("returns the same set when nothing changes", () => {
    const start: ReadonlySet<BranchKey> = new Set<BranchKey>(["area:1"]);
    expect(withKey(start, "area:1", true)).toBe(start);
    expect(withKey(start, "plant:9", false)).toBe(start);
  });
});
