// Display settings of the user interface: colour mode, accent colour and
// reduced motion (work order 070). They live only in this browser
// (localStorage, keys below "twox."); without a usable storage every setting
// has its default value.
//
// The small inline script in index.html applies the same rules before the
// first paint, so that the page never shows the wrong colours while loading.
// theme/settings.test.ts runs that script against applySettings() below; keep
// both in step (see theme/README.md).

/** Colour mode the user picked; "system" follows the operating system. */
export const themeModes = ["system", "light", "dark"] as const;
export type ThemeMode = (typeof themeModes)[number];

/** Colour mode actually shown. */
export type ResolvedTheme = "light" | "dark";

/** Accent colours to choose from; the values are defined in index.css. */
export const accents = ["aubergine", "indigo", "berry", "umber", "graphite"] as const;
export type Accent = (typeof accents)[number];

export interface DisplaySettings {
  readonly mode: ThemeMode;
  readonly accent: Accent;
  /** Reduce motion in addition to the operating system's setting. */
  readonly reduceMotion: boolean;
}

export const defaultSettings: DisplaySettings = {
  mode: "system",
  accent: "aubergine",
  reduceMotion: false,
};

/** localStorage keys; the language has its own key "twox.language" (i18n.ts). */
export const storageKeys = {
  mode: "twox.theme",
  accent: "twox.accent",
  reduceMotion: "twox.reduceMotion",
} as const;

/** What the operating system asks for (media queries). */
export interface SystemPreferences {
  readonly dark: boolean;
  readonly reduceMotion: boolean;
}

export const darkQuery = "(prefers-color-scheme: dark)";
export const reducedMotionQuery = "(prefers-reduced-motion: reduce)";

export function isThemeMode(value: unknown): value is ThemeMode {
  return typeof value === "string" && (themeModes as readonly string[]).includes(value);
}

export function isAccent(value: unknown): value is Accent {
  return typeof value === "string" && (accents as readonly string[]).includes(value);
}

function storage(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function readItem(key: string): string | null {
  try {
    return storage()?.getItem(key) ?? null;
  } catch {
    return null;
  }
}

/** The stored settings; unknown or unreadable values fall back to the defaults. */
export function readSettings(): DisplaySettings {
  const mode = readItem(storageKeys.mode);
  const accent = readItem(storageKeys.accent);
  return {
    mode: isThemeMode(mode) ? mode : defaultSettings.mode,
    accent: isAccent(accent) ? accent : defaultSettings.accent,
    reduceMotion: readItem(storageKeys.reduceMotion) === "true",
  };
}

/** Stores the settings; a blocked or full storage keeps them until the page is reloaded. */
export function storeSettings(settings: DisplaySettings): void {
  try {
    const target = storage();
    target?.setItem(storageKeys.mode, settings.mode);
    target?.setItem(storageKeys.accent, settings.accent);
    target?.setItem(storageKeys.reduceMotion, String(settings.reduceMotion));
  } catch {
    // Nothing to do: the settings stay in effect for this page.
  }
}

/** Whether a media query matches; false where matchMedia is missing (tests) or fails. */
export function mediaMatches(query: string): boolean {
  try {
    return typeof window.matchMedia === "function" && window.matchMedia(query).matches;
  } catch {
    return false;
  }
}

export function systemPreferences(): SystemPreferences {
  return { dark: mediaMatches(darkQuery), reduceMotion: mediaMatches(reducedMotionQuery) };
}

export function resolveTheme(mode: ThemeMode, system: SystemPreferences): ResolvedTheme {
  if (mode === "system") {
    return system.dark ? "dark" : "light";
  }
  return mode;
}

/** Reduced motion is on if the user or the operating system asks for it. */
export function resolveReducedMotion(settings: DisplaySettings, system: SystemPreferences): boolean {
  return settings.reduceMotion || system.reduceMotion;
}

/**
 * Writes the settings onto <html>: data-theme ("light"/"dark"), data-accent
 * and data-motion ("reduce"/"full"). index.css reads these attributes.
 */
export function applySettings(root: HTMLElement, settings: DisplaySettings, system: SystemPreferences): void {
  root.dataset.theme = resolveTheme(settings.mode, system);
  root.dataset.accent = settings.accent;
  root.dataset.motion = resolveReducedMotion(settings, system) ? "reduce" : "full";
}
