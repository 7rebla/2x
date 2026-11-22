import { act, cleanup, fireEvent, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { changeLanguage } from "../i18n.ts";
import { fakeApi, manager, reader, roleless } from "../test/fakeApi.ts";
import { fakeMatchMedia } from "../test/fakeMatchMedia.ts";
import { openUserMenu, renderApp } from "../test/renderApp.tsx";
import { darkQuery, reducedMotionQuery } from "../theme/settings.ts";
import { refreshDisplay } from "../theme/store.ts";

const root = document.documentElement;

afterEach(async () => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  await changeLanguage("en");
  window.localStorage.clear();
  refreshDisplay();
});

async function openSettings(): Promise<HTMLElement> {
  return screen.findByTestId("settings-page");
}

describe("settings page", () => {
  it("is open to the role read and reached from the user menu", async () => {
    fakeApi(reader);
    const { router } = renderApp("/");
    await openUserMenu();
    const menu = screen.getByTestId("user-menu");
    expect(menu.hidden).toBe(false);
    const link = within(menu).getByRole("link", { name: "Settings" });
    fireEvent.click(link);
    await openSettings();
    expect(router.state.location.pathname).toBe("/settings");
    expect(screen.getByRole("heading", { level: 2, name: "Settings" })).toBeDefined();
    expect(link.getAttribute("aria-current")).toBe("page");
    // Following a link closes the menu.
    expect(menu.hidden).toBe(true);
    expect(screen.getByTestId("user-menu-button").getAttribute("aria-expanded")).toBe("false");
  });

  it("offers no settings link to an account without a role", async () => {
    fakeApi(roleless);
    renderApp("/");
    await screen.findByTestId("no-role");
    expect(screen.queryByTestId("settings-link")).toBeNull();
  });

  it("starts with the system appearance, aubergine and full motion", async () => {
    fakeApi(manager);
    renderApp("/settings");
    await openSettings();
    expect(screen.getByRole<HTMLInputElement>("radio", { name: "Same as the system" }).checked).toBe(true);
    expect(screen.getByRole<HTMLInputElement>("radio", { name: "Aubergine (default)" }).checked).toBe(true);
    expect(screen.getByRole<HTMLInputElement>("checkbox", { name: "Reduce motion" }).checked).toBe(false);
    expect(screen.getByTestId("settings-system-mode").textContent).toBe(
      "Your system currently uses the light appearance.",
    );
  });

  it("switches the appearance at once and remembers it", async () => {
    fakeApi(reader);
    renderApp("/settings");
    await openSettings();

    fireEvent.click(screen.getByRole("radio", { name: "Dark" }));
    expect(root.dataset.theme).toBe("dark");
    expect(window.localStorage.getItem("twox.theme")).toBe("dark");
    expect(screen.queryByTestId("settings-system-mode")).toBeNull();

    fireEvent.click(screen.getByRole("radio", { name: "Light" }));
    expect(root.dataset.theme).toBe("light");
    expect(window.localStorage.getItem("twox.theme")).toBe("light");
  });

  it("shows what the system uses in mode 'system'", async () => {
    fakeMatchMedia({ [darkQuery]: true });
    act(() => {
      refreshDisplay();
    });
    fakeApi(reader);
    renderApp("/settings");
    await openSettings();
    expect(root.dataset.theme).toBe("dark");
    expect(screen.getByTestId("settings-system-mode").textContent).toBe(
      "Your system currently uses the dark appearance.",
    );
  });

  it("offers every accent as a named tile with a preview", async () => {
    fakeApi(reader);
    renderApp("/settings");
    await openSettings();
    const group = screen.getByRole("group", { name: "Accent colour" });
    const names = within(group)
      .getAllByRole("radio")
      .map((radio) => radio.closest("label")?.textContent);
    expect(names).toEqual(["AaAubergine (default)", "AaIndigo", "AaBerry", "AaUmber", "AaGraphite"]);
    expect(group.querySelectorAll("[data-accent-preview]")).toHaveLength(5);
    for (const preview of group.querySelectorAll("[data-accent-preview]")) {
      expect(preview.getAttribute("aria-hidden")).toBe("true");
    }

    fireEvent.click(within(group).getByRole("radio", { name: "Berry" }));
    expect(root.dataset.accent).toBe("berry");
    expect(window.localStorage.getItem("twox.accent")).toBe("berry");
    expect(within(group).getByRole<HTMLInputElement>("radio", { name: "Berry" }).checked).toBe(true);
  });

  it("changes the language together with the switch in the user menu", async () => {
    fakeApi(reader);
    renderApp("/settings");
    await openSettings();
    fireEvent.change(screen.getByRole("combobox", { name: "Language of the interface" }), {
      target: { value: "de" },
    });
    expect(await screen.findByRole("heading", { level: 2, name: "Einstellungen" })).toBeDefined();
    expect(screen.getByTestId<HTMLSelectElement>("language-switch").value).toBe("de");
    expect(window.localStorage.getItem("twox.language")).toBe("de");
    expect(screen.getByRole("radio", { name: "Wie im System" })).toBeDefined();
    expect(screen.getByRole("radio", { name: "Aubergine (Standard)" })).toBeDefined();

    fireEvent.change(screen.getByTestId("language-switch"), { target: { value: "en" } });
    expect(await screen.findByRole("heading", { level: 2, name: "Settings" })).toBeDefined();
    expect(screen.getByTestId<HTMLSelectElement>("settings-language-select").value).toBe("en");
  });

  it("reduces motion: no animation class on the page any more", async () => {
    // A new browser session, so the heading fades in once (E-65).
    window.sessionStorage.clear();
    fakeApi(reader);
    renderApp("/settings");
    await openSettings();
    expect(document.querySelectorAll("[class*='tx-']").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("checkbox", { name: "Reduce motion" }));
    expect(root.dataset.motion).toBe("reduce");
    expect(window.localStorage.getItem("twox.reduceMotion")).toBe("true");
    expect(document.querySelectorAll("[class*='tx-']")).toHaveLength(0);
    expect(screen.getByRole("heading", { level: 2, name: "Settings" }).textContent).toBe("Settings");
  });

  it("says when the system already reduces motion", async () => {
    fakeMatchMedia({ [reducedMotionQuery]: true });
    act(() => {
      refreshDisplay();
    });
    fakeApi(reader);
    renderApp("/settings");
    await openSettings();
    expect(screen.getByTestId("settings-system-motion").textContent).toBe(
      "Your system already asks for reduced motion, so animations stay off.",
    );
    expect(document.querySelectorAll("[class*='tx-']")).toHaveLength(0);
  });

  it("reads settings stored earlier", async () => {
    window.localStorage.setItem("twox.theme", "dark");
    window.localStorage.setItem("twox.accent", "graphite");
    window.localStorage.setItem("twox.reduceMotion", "true");
    act(() => {
      refreshDisplay();
    });
    fakeApi(reader);
    renderApp("/settings");
    await openSettings();
    expect(screen.getByRole<HTMLInputElement>("radio", { name: "Dark" }).checked).toBe(true);
    expect(screen.getByRole<HTMLInputElement>("radio", { name: "Graphite" }).checked).toBe(true);
    expect(screen.getByRole<HTMLInputElement>("checkbox", { name: "Reduce motion" }).checked).toBe(true);
    expect(root.dataset.theme).toBe("dark");
    expect(root.dataset.accent).toBe("graphite");
  });
});
