import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import indexHtml from "../../index.html?raw";
import { fakeMatchMedia } from "../test/fakeMatchMedia.ts";
import themeReadme from "./README.md?raw";
import {
  accents,
  applySettings,
  darkQuery,
  defaultSettings,
  type DisplaySettings,
  readSettings,
  reducedMotionQuery,
  resolveReducedMotion,
  resolveTheme,
  storageKeys,
  storeSettings,
  type SystemPreferences,
  systemPreferences,
  themeModes,
} from "./settings.ts";

const root = document.documentElement;

function clearRoot(): void {
  for (const name of ["data-theme", "data-accent", "data-motion"]) {
    root.removeAttribute(name);
  }
}

beforeEach(() => {
  window.localStorage.clear();
  clearRoot();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  window.localStorage.clear();
  clearRoot();
});

const lightSystem: SystemPreferences = { dark: false, reduceMotion: false };
const darkSystem: SystemPreferences = { dark: true, reduceMotion: false };

describe("resolving the colour mode", () => {
  it("follows the system for 'system'", () => {
    expect(resolveTheme("system", lightSystem)).toBe("light");
    expect(resolveTheme("system", darkSystem)).toBe("dark");
  });

  it("keeps an explicit choice whatever the system says", () => {
    expect(resolveTheme("light", darkSystem)).toBe("light");
    expect(resolveTheme("dark", lightSystem)).toBe("dark");
  });

  it("reduces motion if the user or the system asks for it", () => {
    expect(resolveReducedMotion(defaultSettings, lightSystem)).toBe(false);
    expect(resolveReducedMotion({ ...defaultSettings, reduceMotion: true }, lightSystem)).toBe(true);
    expect(resolveReducedMotion(defaultSettings, { dark: false, reduceMotion: true })).toBe(true);
  });

  it("reads the system through matchMedia, and nothing without it", () => {
    expect(systemPreferences()).toEqual(lightSystem);
    fakeMatchMedia({ [darkQuery]: true, [reducedMotionQuery]: true });
    expect(systemPreferences()).toEqual({ dark: true, reduceMotion: true });
  });

  it("treats a failing matchMedia as 'no preference'", () => {
    vi.stubGlobal("matchMedia", () => {
      throw new Error("not available");
    });
    expect(systemPreferences()).toEqual(lightSystem);
  });
});

describe("stored settings", () => {
  it("starts with system mode, aubergine and full motion", () => {
    expect(readSettings()).toEqual({ mode: "system", accent: "aubergine", reduceMotion: false });
  });

  it("reads a stored choice", () => {
    window.localStorage.setItem(storageKeys.mode, "dark");
    window.localStorage.setItem(storageKeys.accent, "berry");
    window.localStorage.setItem(storageKeys.reduceMotion, "true");
    expect(readSettings()).toEqual({ mode: "dark", accent: "berry", reduceMotion: true });
  });

  it("ignores unknown values", () => {
    window.localStorage.setItem(storageKeys.mode, "sepia");
    window.localStorage.setItem(storageKeys.accent, "teal");
    window.localStorage.setItem(storageKeys.reduceMotion, "yes");
    expect(readSettings()).toEqual(defaultSettings);
  });

  it("uses the defaults if the storage cannot be read", () => {
    window.localStorage.setItem(storageKeys.mode, "dark");
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    expect(readSettings()).toEqual(defaultSettings);
  });

  it("uses the defaults if there is no storage at all", () => {
    vi.spyOn(window, "localStorage", "get").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    expect(readSettings()).toEqual(defaultSettings);
    expect(() => {
      storeSettings({ mode: "dark", accent: "umber", reduceMotion: true });
    }).not.toThrow();
  });

  it("stores and reads back every setting under twox.*", () => {
    storeSettings({ mode: "light", accent: "graphite", reduceMotion: true });
    expect(window.localStorage.getItem("twox.theme")).toBe("light");
    expect(window.localStorage.getItem("twox.accent")).toBe("graphite");
    expect(window.localStorage.getItem("twox.reduceMotion")).toBe("true");
    expect(readSettings()).toEqual({ mode: "light", accent: "graphite", reduceMotion: true });
  });

  it("survives a full storage", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("full", "QuotaExceededError");
    });
    expect(() => {
      storeSettings({ mode: "dark", accent: "indigo", reduceMotion: false });
    }).not.toThrow();
  });
});

describe("attributes on <html>", () => {
  it("writes mode, accent and motion", () => {
    applySettings(root, { mode: "system", accent: "indigo", reduceMotion: false }, darkSystem);
    expect(root.dataset.theme).toBe("dark");
    expect(root.dataset.accent).toBe("indigo");
    expect(root.dataset.motion).toBe("full");
    applySettings(root, { mode: "light", accent: "aubergine", reduceMotion: true }, darkSystem);
    expect(root.dataset.theme).toBe("light");
    expect(root.dataset.motion).toBe("reduce");
  });
});

// ---------------------------------------------------------------------------
// The inline script in index.html must give the same result as applySettings().

const inlineScript = /<script>([\s\S]*?)<\/script>/.exec(indexHtml)?.[1] ?? "";

function runInlineScript(): void {
  // The script comes from index.html of this repository, not from outside.
  // eslint-disable-next-line @typescript-eslint/no-implied-eval
  const run = new Function(inlineScript) as () => void;
  run();
}

function attributes(): Record<string, string | undefined> {
  return { theme: root.dataset.theme, accent: root.dataset.accent, motion: root.dataset.motion };
}

describe("inline script in index.html", () => {
  it("sits in <head>, before anything else is loaded", () => {
    expect(inlineScript).not.toBe("");
    const head = /<head>([\s\S]*?)<\/head>/.exec(indexHtml)?.[1] ?? "";
    expect(head).toContain(inlineScript);
    expect(indexHtml).not.toMatch(/<script[^>]+src="https?:/);
  });

  const stored: readonly (string | null)[][] = [
    // mode, accent, reduceMotion
    [null, null, null],
    ["light", "indigo", "false"],
    ["dark", "berry", "true"],
    ["system", "umber", null],
    ["sepia", "teal", "yes"],
    ["dark", "graphite", "false"],
  ];
  const systems: readonly SystemPreferences[] = [
    lightSystem,
    darkSystem,
    { dark: false, reduceMotion: true },
    { dark: true, reduceMotion: true },
  ];

  it.each(stored)("matches applySettings() for stored %s / %s / %s", (mode, accent, motion) => {
    for (const system of systems) {
      window.localStorage.clear();
      const entries: [string, string | null][] = [
        [storageKeys.mode, mode ?? null],
        [storageKeys.accent, accent ?? null],
        [storageKeys.reduceMotion, motion ?? null],
      ];
      for (const [key, value] of entries) {
        if (value !== null) {
          window.localStorage.setItem(key, value);
        }
      }
      fakeMatchMedia({ [darkQuery]: system.dark, [reducedMotionQuery]: system.reduceMotion });

      clearRoot();
      runInlineScript();
      const fromScript = attributes();

      clearRoot();
      applySettings(root, readSettings(), systemPreferences());
      expect(fromScript, JSON.stringify({ mode, accent, motion, system })).toEqual(attributes());
    }
  });

  it("knows every accent of settings.ts", () => {
    for (const accent of accents) {
      window.localStorage.setItem(storageKeys.accent, accent);
      runInlineScript();
      expect(root.dataset.accent).toBe(accent);
    }
    expect(themeModes).toEqual(["system", "light", "dark"]);
  });

  it("works without storage and without matchMedia", () => {
    vi.spyOn(window, "localStorage", "get").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    runInlineScript();
    expect(attributes()).toEqual({ theme: "light", accent: "aubergine", motion: "full" });
  });

  it("has the hash that theme/README.md names for a content security policy", async () => {
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(inlineScript));
    const hash = btoa(String.fromCharCode(...new Uint8Array(digest)));
    expect(themeReadme).toContain(`'sha256-${hash}'`);
  });
});

describe("settings type", () => {
  it("lists five accents with aubergine as default", () => {
    const settings: DisplaySettings = defaultSettings;
    expect(accents).toHaveLength(5);
    expect(settings.accent).toBe(accents[0]);
  });
});
