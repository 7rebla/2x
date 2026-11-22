import { act, cleanup, render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { fakeMatchMedia } from "../test/fakeMatchMedia.ts";
import { darkQuery, reducedMotionQuery, storageKeys } from "./settings.ts";
import { getDisplayState, installDisplaySettings, refreshDisplay, updateDisplaySettings, useDisplay } from "./store.ts";

const root = document.documentElement;
let uninstall: (() => void) | null = null;

afterEach(() => {
  cleanup();
  uninstall?.();
  uninstall = null;
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  window.localStorage.clear();
  refreshDisplay();
});

function Probe(): ReactElement {
  const display = useDisplay();
  return (
    <p data-testid="probe">
      {display.settings.mode}/{display.theme}/{display.settings.accent}/{String(display.reduceMotion)}
    </p>
  );
}

describe("display store", () => {
  it("applies a change at once, stores it and re-renders", () => {
    render(<Probe />);
    expect(screen.getByTestId("probe").textContent).toBe("system/light/aubergine/false");

    act(() => {
      updateDisplaySettings({ mode: "dark", accent: "umber" });
    });
    expect(screen.getByTestId("probe").textContent).toBe("dark/dark/umber/false");
    expect(root.dataset.theme).toBe("dark");
    expect(root.dataset.accent).toBe("umber");
    expect(window.localStorage.getItem(storageKeys.mode)).toBe("dark");
    expect(window.localStorage.getItem(storageKeys.accent)).toBe("umber");

    act(() => {
      updateDisplaySettings({ reduceMotion: true });
    });
    expect(root.dataset.motion).toBe("reduce");
    expect(getDisplayState().settings).toEqual({ mode: "dark", accent: "umber", reduceMotion: true });
  });

  it("keeps working when the storage is blocked", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    render(<Probe />);
    act(() => {
      updateDisplaySettings({ mode: "dark" });
    });
    expect(root.dataset.theme).toBe("dark");
    expect(screen.getByTestId("probe").textContent).toBe("dark/dark/aubergine/false");
  });

  it("follows the operating system in mode 'system'", () => {
    const media = fakeMatchMedia({ [darkQuery]: false });
    uninstall = installDisplaySettings();
    render(<Probe />);
    expect(root.dataset.theme).toBe("light");

    act(() => {
      media.set(darkQuery, true);
    });
    expect(root.dataset.theme).toBe("dark");
    expect(screen.getByTestId("probe").textContent).toBe("system/dark/aubergine/false");

    act(() => {
      media.set(reducedMotionQuery, true);
    });
    expect(root.dataset.motion).toBe("reduce");
    expect(screen.getByTestId("probe").textContent).toBe("system/dark/aubergine/true");
  });

  it("keeps an explicit mode when the operating system changes", () => {
    const media = fakeMatchMedia({ [darkQuery]: true });
    uninstall = installDisplaySettings();
    act(() => {
      updateDisplaySettings({ mode: "light" });
    });
    act(() => {
      media.set(darkQuery, false);
      media.set(darkQuery, true);
    });
    expect(root.dataset.theme).toBe("light");
  });

  it("takes over a change made in another tab", () => {
    uninstall = installDisplaySettings();
    render(<Probe />);
    window.localStorage.setItem(storageKeys.accent, "berry");
    act(() => {
      window.dispatchEvent(new StorageEvent("storage", { key: storageKeys.accent }));
    });
    expect(root.dataset.accent).toBe("berry");
    expect(screen.getByTestId("probe").textContent).toBe("system/light/berry/false");
  });
});
