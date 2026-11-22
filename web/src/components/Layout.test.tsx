// Header of the frame with icons (work order 071): navigation with an icon per
// entry, the user menu with role, settings, language and sign-out. Skip link,
// browser title per page and the focus after a change of page (work order 078).
import { act, cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { changeLanguage } from "../i18n.ts";
import { iconNames } from "../icons/names.ts";
import enNav from "../locales/en/nav.json";
import { navigation } from "../navigation.ts";
import { fakeStructureApi } from "../pages/structure/testData.ts";
import { fakeApi, manager, reader } from "../test/fakeApi.ts";
import { openUserMenu, renderApp } from "../test/renderApp.tsx";
import { fakeFilesApi } from "./files/testData.ts";
import { MAIN_CONTENT_ID, PAGE_GRID, PAGE_PROSE } from "./Layout.tsx";

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
