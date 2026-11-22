// Header of the frame with icons (work order 071): navigation with an icon per
// entry, the user menu with role, settings, language and sign-out. Skip link,
// browser title per page and the focus after a change of page (work order 078).
import { act, cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { changeLanguage } from "../i18n.ts";
import { iconNames } from "../icons/names.ts";
import deNav from "../locales/de/nav.json";
import enNav from "../locales/en/nav.json";
import { navigation } from "../navigation.ts";
import { fakeStructureApi } from "../pages/structure/testData.ts";
import { fakeApi, manager, reader } from "../test/fakeApi.ts";
import { fakeMatchMedia } from "../test/fakeMatchMedia.ts";
import { openUserMenu, renderApp } from "../test/renderApp.tsx";
import { fakeFilesApi } from "./files/testData.ts";
import { MAIN_CONTENT_ID, NARROW_QUERY, PAGE_GRID, PAGE_PROSE } from "./Layout.tsx";

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
      // Below 1280 px the text is for screen readers only (work order 055) ...
      expect(text?.classList.contains("max-xl:sr-only")).toBe(true);
      // ... and from 768 to 1279 px the short text shows below the icon, hidden from assistive technology (work order 082).
      const short = link.querySelector(".nav-short");
      expect(short?.getAttribute("data-short")).toBe(enNav.short[entry?.textKey ?? "structure"]);
      expect(short?.getAttribute("aria-hidden")).toBe("true");
      expect(short?.textContent).toBe("");
      // The metadata size (13 px, E-65 point 5, work order 084) on a 16 px line, so the entry stays 42 px high.
      expect(short?.classList.contains("text-meta")).toBe(true);
      expect(short?.classList.contains("leading-4")).toBe(true);
      expect(short?.classList.contains("xl:hidden")).toBe(true);
      expect(link.classList.contains("max-xl:flex-col")).toBe(true);
      // The link's text stays the full text.
      expect(link.textContent).toBe(label);
    });
  });

  it("has a short text in German and English for every entry, contained in its full text", () => {
    for (const [full, short] of [
      [enNav, enNav.short],
      [deNav, deNav.short],
    ] as const) {
      expect(Object.keys(short).sort()).toEqual(navigation.map((entry) => entry.textKey).sort());
      for (const entry of navigation) {
        const text = short[entry.textKey];
        // Label in name (WCAG 2.5.3): what shows is part of the accessible name.
        expect(full[entry.textKey].toLowerCase()).toContain(text.toLowerCase());
        expect(text.length).toBeLessThanOrEqual(10);
      }
    }
  });

  it("shows the German short texts after a change of language", async () => {
    fakeApi(manager);
    renderApp("/");
    await screen.findByTestId("user-name");
    await act(async () => {
      await changeLanguage("de");
    });
    const nav = screen.getByRole("navigation", { name: deNav.label });
    expect([...nav.querySelectorAll(".nav-short")].map((element) => element.getAttribute("data-short"))).toEqual([
      "Struktur",
      "Karte",
      "Suche",
      "Einlesen",
      "Import",
      "Protokoll",
      "Selbsttest",
    ]);
    expect(within(nav).getByRole("link", { name: "Änderungsprotokoll" }).getAttribute("title")).toBe("Änderungsprotokoll");
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

describe("menu below 768 px (work order 082)", () => {
  function menuButton(): HTMLElement {
    return screen.getByTestId("navigation-menu-button");
  }

  async function renderNarrow(path = "/", user = manager): Promise<ReturnType<typeof renderApp>> {
    fakeMatchMedia({ [NARROW_QUERY]: true });
    fakeApi(user);
    const result = renderApp(path);
    await screen.findByTestId("navigation-menu-button");
    return result;
  }

  it("shows a closed button 'Menu' instead of navigation and user menu", async () => {
    await renderNarrow();
    const button = menuButton();
    expect(screen.getByRole("button", { name: "Menu" })).toBe(button);
    expect(button.getAttribute("aria-expanded")).toBe("false");
    expect(button.querySelector("svg")?.getAttribute("data-icon")).toBe("menu");
    expect(button.querySelector("svg")?.getAttribute("aria-hidden")).toBe("true");
    const panel = screen.getByTestId("navigation-menu");
    expect(button.getAttribute("aria-controls")).toBe(panel.id);
    expect(panel.hidden).toBe(true);
    expect(screen.queryByRole("navigation")).toBeNull();
    expect(screen.queryByTestId("user-menu-button")).toBeNull();
    expect(within(screen.getByTestId("user-area")).getByRole("button", { name: "Menu" })).toBe(button);
  });

  it("opens a list with every entry and the content of the user menu", async () => {
    await renderNarrow();
    fireEvent.click(menuButton());
    const panel = screen.getByTestId("navigation-menu");
    expect(panel.hidden).toBe(false);
    expect(menuButton().getAttribute("aria-expanded")).toBe("true");
    expect(menuButton().querySelector("svg")?.getAttribute("data-icon")).toBe("close");
    const nav = within(panel).getByRole("navigation", { name: enNav.label });
    const links = within(nav).getAllByRole("link");
    expect(links.map((link) => link.textContent)).toEqual(navigation.map((entry) => enNav[entry.textKey]));
    expect(links.map((link) => link.getAttribute("href"))).toEqual(navigation.map((entry) => entry.path));
    // Full texts, one entry per line, no short texts.
    expect(nav.querySelectorAll(".nav-short")).toHaveLength(0);
    expect(nav.querySelector("ul")?.classList.contains("flex-col")).toBe(true);
    expect(within(nav).getByRole("link", { name: "Structure" }).getAttribute("aria-current")).toBe("page");
    // The user menu's content: name, role, settings, language, sign-out.
    expect(within(panel).getByText(manager.username)).toBeDefined();
    expect(within(panel).getByTestId("user-role").textContent).toBe("Manage");
    expect(within(panel).getByRole("link", { name: "Settings" })).toBeDefined();
    expect(within(panel).getByRole("combobox", { name: "Language" })).toBeDefined();
    expect(within(panel).getByRole("button", { name: "Sign out" })).toBeDefined();
    expect(screen.getAllByTestId("language-switch")).toHaveLength(1);
  });

  it("closes on Escape and gives the focus back to its button", async () => {
    await renderNarrow();
    fireEvent.click(menuButton());
    const panel = screen.getByTestId("navigation-menu");
    const entry = within(panel).getByRole("link", { name: "Search" });
    entry.focus();
    fireEvent.keyDown(entry, { key: "Escape" });
    expect(panel.hidden).toBe(true);
    expect(menuButton().getAttribute("aria-expanded")).toBe("false");
    expect(document.activeElement).toBe(menuButton());
  });

  it("closes after a choice; the focus goes to the button and then to the new page's heading", async () => {
    const { router } = await renderNarrow();
    fireEvent.click(menuButton());
    const panel = screen.getByTestId("navigation-menu");
    const entry = within(panel).getByRole("link", { name: "Self-test" });
    entry.focus();
    fireEvent.click(entry);
    expect(panel.hidden).toBe(true);
    expect(router.state.location.pathname).toBe("/selftest");
    const heading = await screen.findByRole("heading", { level: 1, name: "Self-test" });
    await waitFor(() => {
      expect(document.activeElement).toBe(heading);
    });
  });

  it("closes when the focus leaves button and panel, without taking the focus back", async () => {
    await renderNarrow();
    fireEvent.click(menuButton());
    const panel = screen.getByTestId("navigation-menu");
    // Within button and panel it stays open.
    menuButton().focus();
    within(panel).getByRole("link", { name: "Structure" }).focus();
    const signOut = within(panel).getByRole("button", { name: "Sign out" });
    signOut.focus();
    expect(panel.hidden).toBe(false);
    // A focus that goes nowhere (a click on text in the panel) leaves it open.
    fireEvent.focusOut(signOut, { relatedTarget: null });
    expect(panel.hidden).toBe(false);
    // Tab after "Sign out": the focus moves on outside, the panel closes, the focus stays there.
    // (jsdom already names the new target in the focusout of focus(); the explicit event states the case on its own.)
    const outside = screen.getByRole("link", { name: "Skip to content" });
    outside.focus();
    fireEvent.focusOut(signOut, { relatedTarget: outside });
    expect(panel.hidden).toBe(true);
    expect(menuButton().getAttribute("aria-expanded")).toBe("false");
    expect(document.activeElement).toBe(outside);
  });

  it("keeps the focus on the button when the current page is chosen", async () => {
    await renderNarrow();
    fireEvent.click(menuButton());
    const panel = screen.getByTestId("navigation-menu");
    fireEvent.click(within(panel).getByRole("link", { name: "Structure" }));
    expect(panel.hidden).toBe(true);
    expect(document.activeElement).toBe(menuButton());
  });

  it("closes on a click outside, but not on a click inside, and on a second click on the button", async () => {
    await renderNarrow();
    fireEvent.click(menuButton());
    const panel = screen.getByTestId("navigation-menu");
    fireEvent.pointerDown(within(panel).getByTestId("user-role"));
    expect(panel.hidden).toBe(false);
    fireEvent.pointerDown(screen.getByRole("main"));
    expect(panel.hidden).toBe(true);
    fireEvent.click(menuButton());
    expect(panel.hidden).toBe(false);
    fireEvent.click(menuButton());
    expect(panel.hidden).toBe(true);
  });

  it("gives way to the header bar at 768 px and stays closed when the window narrows again", async () => {
    const media = fakeMatchMedia({ [NARROW_QUERY]: true });
    fakeApi(manager);
    renderApp("/");
    fireEvent.click(await screen.findByTestId("navigation-menu-button"));
    act(() => {
      media.set(NARROW_QUERY, false);
    });
    expect(screen.queryByTestId("navigation-menu-button")).toBeNull();
    expect(within(mainNavigation()).getAllByRole("link")).toHaveLength(navigation.length);
    expect(screen.getByTestId("user-menu-button")).toBeDefined();
    act(() => {
      media.set(NARROW_QUERY, true);
    });
    expect(screen.getByTestId("navigation-menu").hidden).toBe(true);
    expect(menuButton().getAttribute("aria-expanded")).toBe("false");
  });

  it("offers only the user menu's content to an account without a role", async () => {
    await renderNarrow("/", { ...reader, role: null });
    fireEvent.click(menuButton());
    const panel = screen.getByTestId("navigation-menu");
    expect(within(panel).queryByRole("navigation")).toBeNull();
    expect(within(panel).getByRole("button", { name: "Sign out" })).toBeDefined();
  });

  it("speaks German", async () => {
    await changeLanguage("de");
    await renderNarrow();
    fireEvent.click(screen.getByRole("button", { name: "Menü" }));
    const nav = within(screen.getByTestId("navigation-menu")).getByRole("navigation", { name: deNav.label });
    expect(within(nav).getAllByRole("link").map((link) => link.textContent)).toEqual([
      "Struktur",
      "Landkarte",
      "Suche",
      "Einlesen",
      "Import",
      "Änderungsprotokoll",
      "Selbsttest",
    ]);
  });

  it("is not there before sign-in: the language switch stays in the header", async () => {
    fakeMatchMedia({ [NARROW_QUERY]: true });
    fakeApi(null);
    renderApp("/login");
    await screen.findByTestId("login-form");
    expect(screen.queryByTestId("navigation-menu-button")).toBeNull();
    expect(screen.getByTestId("language-switch")).toBeDefined();
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

/** Elements the Tab key reaches, in document order. */
function tabStops(): HTMLElement[] {
  return [...document.body.querySelectorAll<HTMLElement>("a[href], button, input, select, textarea, [tabindex]")].filter(
    (element) => element.tabIndex >= 0 && !element.hasAttribute("disabled"),
  );
}

describe("skip link (work order 078)", () => {
  it("is the first stop of the keyboard and leads to the page content", async () => {
    fakeApi(manager);
    renderApp("/");
    await screen.findByTestId("user-name");
    const skip = screen.getByRole("link", { name: "Skip to content" });
    expect(tabStops()[0]).toBe(skip);
    expect(skip.getAttribute("href")).toBe(`#${MAIN_CONTENT_ID}`);
    const main = screen.getByRole("main");
    expect(main.id).toBe(MAIN_CONTENT_ID);
    expect(main.tabIndex).toBe(-1);
  });

  it("focuses the content without changing the address", async () => {
    fakeApi(manager);
    const { router } = renderApp("/");
    await screen.findByTestId("user-name");
    fireEvent.click(screen.getByRole("link", { name: "Skip to content" }));
    expect(document.activeElement).toBe(screen.getByRole("main"));
    expect(router.state.location.hash).toBe("");
  });

  it("is there before sign-in as well, in German", async () => {
    await changeLanguage("de");
    fakeApi(null);
    renderApp("/login");
    await screen.findByTestId("login-form");
    expect(tabStops()[0]).toBe(screen.getByRole("link", { name: "Zum Inhalt" }));
  });
});

describe("page grid (work order 080)", () => {
  /** The classes of an element as a set (order does not matter). */
  function classesOf(element: Element): Set<string> {
    return new Set(element.className.split(/\s+/).filter((name) => name !== ""));
  }

  it("gives header and page content the same width and side padding, signed in and before sign-in", async () => {
    for (const user of [manager, null]) {
      fakeApi(user);
      renderApp(user === null ? "/login" : "/");
      await screen.findByRole("heading", { level: 1 });
      const header = screen.getByTestId("header-grid");
      const main = screen.getByRole("main");
      for (const name of PAGE_GRID.split(" ")) {
        expect(classesOf(header).has(name), `header ${name}`).toBe(true);
        expect(classesOf(main).has(name), `main ${name}`).toBe(true);
      }
      expect(PAGE_GRID).toContain("max-w-7xl");
      // No second, narrower width on either of them, also not from a breakpoint (before: max-w-5xl, xl:max-w-7xl).
      // The prose rule of main applies to paragraphs inside, not to main itself.
      for (const element of [header, main]) {
        expect([...classesOf(element)].filter((name) => /^(?:[a-z0-9-]+:)*max-w-/.test(name))).toEqual(["max-w-7xl"]);
      }
      cleanup();
    }
  });

  it("holds the introduction of a page to a readable line length", async () => {
    fakeApi(manager);
    renderApp("/audit");
    await screen.findByRole("heading", { level: 1, name: "Change log" });
    const main = screen.getByRole("main");
    expect(classesOf(main).has(PAGE_PROSE)).toBe(true);
    expect(PAGE_PROSE).toBe("[&>section>p]:max-w-prose");
    // The rule reaches the introduction: a paragraph directly inside the page's section.
    const intro = screen.getByText("Who changed what and when, newest first.");
    expect(intro.tagName).toBe("P");
    expect(intro.parentElement?.tagName).toBe("SECTION");
    expect(intro.parentElement?.parentElement).toBe(main);
  });
});

describe("headings (work order 078)", () => {
  it("makes the page title the only h1; the name in the header is a link, not a heading", async () => {
    fakeApi(manager);
    renderApp("/audit");
    const heading = await screen.findByRole("heading", { level: 1, name: "Change log" });
    expect(screen.getAllByRole("heading", { level: 1 })).toEqual([heading]);
    const brand = within(screen.getByRole("banner")).getByRole("link", { name: "2x" });
    expect(brand.closest("h1, h2, h3, h4, h5, h6")).toBeNull();
  });
});

describe("browser title (work order 078)", () => {
  it.each([
    ["/", "Structure – 2x"],
    ["/search", "Search – 2x"],
    ["/ingest", "Ingestion – 2x"],
    ["/import", "Import – 2x"],
    ["/audit", "Change log – 2x"],
    ["/selftest", "Self-test – 2x"],
    ["/settings", "Settings – 2x"],
    ["/no-such-page", "Page not found – 2x"],
  ])("names the page at %s: %s", async (path, title) => {
    fakeApi(manager);
    renderApp(path);
    await waitFor(() => {
      expect(document.title).toBe(title);
    });
  });

  it("names the sign-in page", async () => {
    fakeApi(null);
    renderApp("/login");
    await screen.findByTestId("login-form");
    expect(document.title).toBe("Sign in – 2x");
  });

  it("names a device and a file by their names", async () => {
    fakeApi(manager, fakeStructureApi().handler);
    renderApp("/devices/1001");
    await screen.findByRole("heading", { level: 1, name: "Test panel" });
    expect(document.title).toBe("Test panel – 2x");
    cleanup();

    fakeApi(manager, fakeFilesApi(fakeStructureApi().handler).handler);
    renderApp("/documents/7");
    await screen.findByRole("heading", { level: 1, name: "Test manual" });
    expect(document.title).toBe("Test manual – 2x");
  });

  it("names an unknown device as a page that does not exist", async () => {
    fakeApi(manager, fakeStructureApi().handler);
    renderApp("/devices/999999");
    await screen.findByTestId("not-found");
    expect(document.title).toBe("Page not found – 2x");
  });

  it("follows the page and the language", async () => {
    fakeApi(manager);
    renderApp("/");
    await waitFor(() => {
      expect(document.title).toBe("Structure – 2x");
    });
    fireEvent.click(within(mainNavigation()).getByRole("link", { name: "Search" }));
    await waitFor(() => {
      expect(document.title).toBe("Search – 2x");
    });
    await act(async () => {
      await changeLanguage("de");
    });
    expect(document.title).toBe("Suche – 2x");
  });
});

describe("focus after a change of page (work order 078)", () => {
  it("stays where it is when the app opens", async () => {
    fakeApi(manager);
    renderApp("/");
    await screen.findByRole("heading", { level: 1, name: "Structure" });
    expect(document.activeElement).toBe(document.body);
  });

  it("stays where it is when the app opens on the sign-in page by a redirect", async () => {
    fakeApi(null);
    const { router } = renderApp("/");
    await screen.findByRole("heading", { level: 1, name: "Sign in" });
    expect(router.state.location.pathname).toBe("/login");
    expect(document.activeElement).toBe(document.body);
  });

  it("moves to the heading of the page a navigation entry opens", async () => {
    fakeApi(manager);
    renderApp("/");
    await screen.findByTestId("user-name");
    const entry = within(mainNavigation()).getByRole("link", { name: "Search" });
    entry.focus();
    fireEvent.click(entry);
    const heading = await screen.findByRole("heading", { level: 1, name: "Search" });
    await waitFor(() => {
      expect(document.activeElement).toBe(heading);
    });
    expect(heading.tabIndex).toBe(-1);
  });

  it("does not move when only the query of the address changes", async () => {
    fakeApi(manager);
    const { router } = renderApp("/search");
    await screen.findByRole("heading", { level: 1, name: "Search" });
    await act(async () => {
      await router.navigate("/search?q=test");
    });
    expect(document.activeElement).toBe(document.body);
  });

  it("moves after a redirect the user started, not after one without any action", async () => {
    fakeApi(manager);
    const { router } = renderApp("/");
    await screen.findByRole("heading", { level: 1, name: "Structure" });
    await act(async () => {
      await router.navigate("/import", { replace: true });
    });
    await screen.findByRole("heading", { level: 1, name: "Import" });
    expect(document.activeElement).toBe(document.body);

    fireEvent.keyDown(document.body, { key: "Enter" });
    await act(async () => {
      await router.navigate("/audit", { replace: true });
    });
    const heading = await screen.findByRole("heading", { level: 1, name: "Change log" });
    await waitFor(() => {
      expect(document.activeElement).toBe(heading);
    });
  });

  it("follows the heading of a page that is still loading, but never takes the focus back from the user", async () => {
    const structure = fakeStructureApi();
    const waiting: (() => void)[] = [];
    fakeApi(manager, (request) => {
      if (/^\/api\/v1\/devices\/\d+\/$/.test(new URL(request.url).pathname)) {
        return new Promise<Response>((resolve) => {
          waiting.push(() => {
            resolve(structure.handler(request));
          });
        });
      }
      return structure.handler(request);
    });
    const { router } = renderApp("/");
    await screen.findByTestId("user-name");
    const answer = async (): Promise<void> => {
      await act(async () => {
        waiting.splice(0).forEach((resolve) => {
          resolve();
        });
        await Promise.resolve();
      });
    };

    // The heading while loading first, then the name of the device: the focus follows.
    await act(async () => {
      await router.navigate("/devices/1001");
    });
    const loading = await screen.findByRole("heading", { level: 1, name: "Device" });
    await waitFor(() => {
      expect(document.activeElement).toBe(loading);
    });
    await answer();
    const title = await screen.findByRole("heading", { level: 1, name: "Test panel" });
    await waitFor(() => {
      expect(document.activeElement).toBe(title);
    });

    // The user moves on while the next device is loading: the focus stays there.
    await act(async () => {
      await router.navigate("/devices/1002");
    });
    await screen.findByRole("heading", { level: 1, name: "Device" });
    const entry = within(mainNavigation()).getByRole("link", { name: "Search" });
    fireEvent.keyDown(entry, { key: "Tab" });
    entry.focus();
    await answer();
    await screen.findByTestId("device-title");
    expect(document.activeElement).toBe(entry);
  });
});
