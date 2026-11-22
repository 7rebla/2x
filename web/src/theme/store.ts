// Live state of the display settings: the stored choice plus what the
// operating system asks for. Components read it with useDisplay(); the
// settings page changes it with updateDisplaySettings(). Every change is
// written onto <html> at once, so the page switches without a reload.
import { useSyncExternalStore } from "react";

import {
  applySettings,
  darkQuery,
  type DisplaySettings,
  readSettings,
  reducedMotionQuery,
  resolveReducedMotion,
  resolveTheme,
  type ResolvedTheme,
  storageKeys,
  storeSettings,
  type SystemPreferences,
  systemPreferences,
} from "./settings.ts";

export interface DisplayState {
  readonly settings: DisplaySettings;
  readonly system: SystemPreferences;
  /** Colour mode actually shown. */
  readonly theme: ResolvedTheme;
  /** True if no animation and no transition may run. */
  readonly reduceMotion: boolean;
}

function buildState(settings: DisplaySettings, system: SystemPreferences): DisplayState {
  return {
    settings,
    system,
    theme: resolveTheme(settings.mode, system),
    reduceMotion: resolveReducedMotion(settings, system),
  };
}

let state: DisplayState = buildState(readSettings(), systemPreferences());
const listeners = new Set<() => void>();

function publish(next: DisplayState): void {
  state = next;
  applySettings(document.documentElement, next.settings, next.system);
  for (const listener of listeners) {
    listener();
  }
}

export function getDisplayState(): DisplayState {
  return state;
}

export function subscribeDisplay(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Changes some settings, stores them and applies them to the page. */
export function updateDisplaySettings(change: Partial<DisplaySettings>): void {
  const settings: DisplaySettings = { ...state.settings, ...change };
  storeSettings(settings);
  publish(buildState(settings, state.system));
}

/** Reads storage and media queries again (after a change elsewhere) and applies the result. */
export function refreshDisplay(): void {
  publish(buildState(readSettings(), systemPreferences()));
}

function watchQuery(query: string, onChange: () => void): () => void {
  try {
    if (typeof window.matchMedia !== "function") {
      return () => undefined;
    }
    const list = window.matchMedia(query);
    list.addEventListener("change", onChange);
    return () => {
      list.removeEventListener("change", onChange);
    };
  } catch {
    return () => undefined;
  }
}

/**
 * Applies the settings to <html> and follows later changes of the operating
 * system (mode "system", reduced motion) and of other tabs (storage event).
 * Called once in main.tsx; returns a function that stops listening.
 */
export function installDisplaySettings(): () => void {
  refreshDisplay();
  const onStorage = (event: StorageEvent): void => {
    if (event.key === null || (Object.values(storageKeys) as string[]).includes(event.key)) {
      refreshDisplay();
    }
  };
  window.addEventListener("storage", onStorage);
  const stopDark = watchQuery(darkQuery, refreshDisplay);
  const stopMotion = watchQuery(reducedMotionQuery, refreshDisplay);
  return () => {
    window.removeEventListener("storage", onStorage);
    stopDark();
    stopMotion();
  };
}

/** Current display state; re-renders the component on every change. */
export function useDisplay(): DisplayState {
  return useSyncExternalStore(subscribeDisplay, getDisplayState);
}

/** True if animations must not run (user setting or operating system). */
export function useReducedMotion(): boolean {
  return useDisplay().reduceMotion;
}
