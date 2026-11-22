// Header of the frame with icons (work order 071): navigation with an icon per
// entry, the user menu with role, settings, language and sign-out.
import { cleanup, fireEvent, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { changeLanguage } from "../i18n.ts";
import { iconNames } from "../icons/names.ts";
import enNav from "../locales/en/nav.json";
import { navigation } from "../navigation.ts";
import { fakeApi, manager, reader } from "../test/fakeApi.ts";
import { openUserMenu, renderApp } from "../test/renderApp.tsx";

afterEach(async () => {
  cleanup();
  vi.unstubAllGlobals();
  await changeLanguage("en");
  window.localStorage.clear();
});

function mainNavigation(): HTMLElement {
  return screen.getByRole("navigation", { name: enNav.label });
}

describe("navigation with icons", () => {
  it("names a known icon for every entry, each a different one", () => {
    for (const entry of navigation) {
      expect(iconNames).toContain(entry.icon);
    }
    expect(new Set(navigation.map((entry) => entry.icon)).size).toBe(navigation.length);
  });

  it("shows the icon of each entry hidden from assistive technology, next to its readable text", async () => {
    fakeApi(manager);
    renderApp("/");
    await screen.findByTestId("user-name");
    const links = within(mainNavigation()).getAllByRole("link");
    expect(links).toHaveLength(navigation.length);
    links.forEach((link, index) => {
      const entry = navigation[index];
      const label = enNav[entry?.textKey ?? "structure"];
      const svg = link.querySelector("svg");
      expect(svg?.getAttribute("data-icon")).toBe(entry?.icon);
      expect(svg?.getAttribute("aria-hidden")).toBe("true");
      // The accessible name is the text, also when the text is shown to screen readers only.
      expect(within(mainNavigation()).getByRole("link", { name: label })).toBe(link);
      expect(link.getAttribute("title")).toBe(label);
      const text = link.querySelector(".nav-label");
      expect(text?.textContent).toBe(label);
      expect(text?.getAttribute("data-label")).toBe(label);
      // Below 1280 px only the icon is visible (the text stays for screen readers, work order 055).
      expect(text?.classList.contains("max-xl:sr-only")).toBe(true);
    });
  });

  it("marks the current entry without changing its icon", async () => {
    fakeApi(manager);
    renderApp("/selftest");
    await screen.findByTestId("user-name");
    const current = within(mainNavigation()).getByRole("link", { name: "Self-test" });
    expect(current.getAttribute("aria-current")).toBe("page");
    expect(current.querySelector("svg")?.getAttribute("data-icon")).toBe("selftest");
    expect(current.querySelector("svg")?.getAttribute("fill")).toBe("none");
  });
});

describe("user menu", () => {
  it("shows only the user name in the header; role, settings, language and sign-out sit in the closed menu", async () => {
    fakeApi(reader);
    renderApp("/");
    const button = await screen.findByTestId("user-menu-button");
    expect(button.getAttribute("aria-expanded")).toBe("false");
    expect(screen.getByRole("button", { name: `Account menu: ${reader.username}` })).toBe(button);
    expect(button.querySelector("svg")?.getAttribute("aria-hidden")).toBe("true");
    const menu = screen.getByTestId("user-menu");
    expect(menu.hidden).toBe(true);
    expect(button.getAttribute("aria-controls")).toBe(menu.id);
    expect(screen.queryByRole("button", { name: "Sign out" })).toBeNull();
    // The language switch is no longer part of the header line.
    expect(within(menu).getByTestId("language-switch")).toBeDefined();
    expect(screen.getAllByTestId("language-switch")).toHaveLength(1);
  });

  it("opens on a click and shows role, settings, language and sign-out", async () => {
    fakeApi(manager);
    renderApp("/");
    await openUserMenu();
    const menu = screen.getByTestId("user-menu");
    expect(menu.hidden).toBe(false);
    expect(screen.getByTestId("user-menu-button").getAttribute("aria-expanded")).toBe("true");
    expect(within(menu).getByTestId("user-role").textContent).toBe("Manage");
    expect(within(menu).getByRole("link", { name: "Settings" })).toBeDefined();
    expect(within(menu).getByRole("combobox", { name: "Language" })).toBeDefined();
    const signOut = within(menu).getByRole("button", { name: "Sign out" });
    expect(signOut.querySelector("svg")?.getAttribute("data-icon")).toBe("signOut");
  });

  it("closes on Escape and gives the focus back to its button", async () => {
    fakeApi(manager);
    renderApp("/");
    await openUserMenu();
    const menu = screen.getByTestId("user-menu");
    fireEvent.keyDown(within(menu).getByRole("button", { name: "Sign out" }), { key: "Escape" });
    expect(menu.hidden).toBe(true);
    expect(document.activeElement).toBe(screen.getByTestId("user-menu-button"));
  });

  it("closes on a click outside, but not on a click inside", async () => {
    fakeApi(manager);
    renderApp("/");
    await openUserMenu();
    const menu = screen.getByTestId("user-menu");
    fireEvent.pointerDown(within(menu).getByTestId("user-role"));
    expect(menu.hidden).toBe(false);
    fireEvent.pointerDown(document.body);
    expect(menu.hidden).toBe(true);
  });

  it("changes the language from the menu", async () => {
    fakeApi(manager);
    renderApp("/");
    await openUserMenu();
    fireEvent.change(within(screen.getByTestId("user-menu")).getByTestId("language-switch"), {
      target: { value: "de" },
    });
    expect(await screen.findByRole("navigation", { name: "Hauptnavigation" })).toBeDefined();
    expect(screen.getByRole("button", { name: `Benutzermenü: ${manager.username}` })).toBeDefined();
  });
});

describe("before sign-in", () => {
  it("keeps the language switch in the header and shows no user menu", async () => {
    fakeApi(null);
    renderApp("/login");
    await screen.findByTestId("login-form");
    expect(screen.getByTestId("language-switch")).toBeDefined();
    expect(screen.queryByTestId("user-menu-button")).toBeNull();
    expect(screen.getByTestId("user-area").childNodes.length).toBe(0);
  });
});
