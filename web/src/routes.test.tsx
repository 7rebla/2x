import { QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import type { ReactElement } from "react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createQueryClient } from "./api/queryClient.ts";
import { fakeFilesApi } from "./components/files/testData.ts";
import { Layout } from "./components/Layout.tsx";
import { lazyPage, PageLoadBoundary } from "./components/PageLoading.tsx";
import { RouteError } from "./components/RouteError.tsx";
import { changeLanguage } from "./i18n.ts";
import enNav from "./locales/en/nav.json";
import { navigation } from "./navigation.ts";
import { LoginPage } from "./pages/LoginPage.tsx";
import { StructurePage } from "./pages/StructurePage.tsx";
import { fakeStructureApi } from "./pages/structure/testData.ts";
import { routes } from "./routes.tsx";
import { fakeApi, manager } from "./test/fakeApi.ts";
import { renderApp } from "./test/renderApp.tsx";

// Routing inside the frame for a signed-in manager (who may see every page).
// Sign-in, redirects and roles: session.test.tsx.

// Every page except sign-in and structure is loaded lazily; test/renderApp.tsx
// loads their code once before the first test (preloadPages).

afterEach(async () => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  await changeLanguage("en");
  window.localStorage.clear();
});

function mainNavigation(): HTMLElement {
  return screen.getByRole("navigation", { name: enNav.label });
}

async function pageHeading(): Promise<HTMLElement> {
  return screen.findByRole("heading", { level: 2 });
}

describe("frame", () => {
  it("shows the name, the navigation, the language switch and the signed-in user", async () => {
    fakeApi(manager);
    renderApp("/");

    expect(screen.getByRole("heading", { level: 1, name: "2x" })).toBeDefined();
    expect((await screen.findByTestId("user-name")).textContent).toBe(manager.username);
    const links = within(mainNavigation()).getAllByRole("link");
    expect(links.map((link) => link.textContent)).toEqual(navigation.map((entry) => enNav[entry.textKey]));
    expect(links.map((link) => link.getAttribute("href"))).toEqual(navigation.map((entry) => entry.path));
    expect(screen.getByTestId("language-switch")).toBeDefined();
  });

  it("translates the navigation when the language changes", async () => {
    fakeApi(manager);
    renderApp("/");
    await screen.findByTestId("user-name");

    fireEvent.change(screen.getByTestId("language-switch"), { target: { value: "de" } });

    const nav = await screen.findByRole("navigation", { name: "Hauptnavigation" });
    expect(within(nav).getAllByRole("link").map((link) => link.textContent)).toEqual([
      "Struktur",
      "Landkarte",
      "Suche",
      "Einlesen",
      "Import",
      "Änderungsprotokoll",
      "Selbsttest",
    ]);
    expect((await pageHeading()).textContent).toBe("Struktur");
  });
});

describe("navigation", () => {
  it("starts on the structure page at /", async () => {
    fakeApi(manager);
    const { router } = renderApp("/");

    expect((await pageHeading()).textContent).toBe("Structure");
    expect(router.state.location.pathname).toBe("/");
    expect(within(mainNavigation()).getByRole("link", { name: "Structure" }).getAttribute("aria-current")).toBe(
      "page",
    );
  });

  it.each(navigation.map((entry) => [entry.path, enNav[entry.textKey]] as const))(
    "a click on the entry for %s shows the page %s",
    async (path, text) => {
      fakeApi(manager);
      const { router } = renderApp(path === "/" ? "/import" : "/");
      await screen.findByTestId("user-name");

      fireEvent.click(within(mainNavigation()).getByRole("link", { name: text }));

      expect((await screen.findByRole("heading", { level: 2, name: text })).textContent).toBe(text);
      expect(router.state.location.pathname).toBe(path);
      expect(within(mainNavigation()).getByRole("link", { name: text }).getAttribute("aria-current")).toBe(
        "page",
      );
      expect(screen.queryByTestId("not-found")).toBeNull();
    },
  );

  it("the name in the header leads back to the structure page", async () => {
    fakeApi(manager);
    const { router } = renderApp("/audit");
    await screen.findByRole("heading", { level: 2, name: "Change log" });

    fireEvent.click(screen.getByRole("link", { name: "2x" }));

    expect(await screen.findByRole("heading", { level: 2, name: "Structure" })).toBeDefined();
    expect(router.state.location.pathname).toBe("/");
  });
});

describe("addresses", () => {
  it("/ shows the structure page", async () => {
    fakeApi(manager, fakeStructureApi().handler);
    renderApp("/");

    expect((await pageHeading()).textContent).toBe("Structure");
    expect(await screen.findByTestId("structure-tree")).toBeDefined();
  });

  it("/import shows the import page", async () => {
    fakeApi(manager);
    renderApp("/import");

    expect((await pageHeading()).textContent).toBe("Import");
    expect(await screen.findByTestId("import-form")).toBeDefined();
  });

  it("/login shows the sign-in page to a visitor who is not signed in", async () => {
    fakeApi(null);
    renderApp("/login");

    expect((await pageHeading()).textContent).toBe("Sign in");
    expect(screen.getByTestId("login-form")).toBeDefined();
  });

  it("/search shows the search page, loaded lazily", async () => {
    fakeApi(manager);
    renderApp("/search?q=test");

    expect((await pageHeading()).textContent).toBe("Search");
    expect(await screen.findByTestId("search-form")).toBeDefined();
  });

  it("/ingest shows the ingest overview, loaded lazily", async () => {
    fakeApi(manager);
    renderApp("/ingest");

    expect((await pageHeading()).textContent).toBe("Ingestion");
    expect(await screen.findByTestId("ingest-filter")).toBeDefined();
    expect(within(mainNavigation()).getByRole("link", { name: "Ingestion" }).getAttribute("aria-current")).toBe("page");
  });

  it("/selftest shows the self-test page", async () => {
    fakeApi(manager);
    renderApp("/selftest");

    expect((await pageHeading()).textContent).toBe("Self-test");
    expect(await screen.findByTestId("selftest-error")).toBeDefined();
  });

  it("passes the address parameters to the device and file pages", async () => {
    fakeApi(manager, fakeStructureApi().handler);
    renderApp("/devices/1001");
    expect(await screen.findByRole("heading", { level: 2, name: "Test panel" })).toBeDefined();
    cleanup();

    fakeApi(manager, fakeFilesApi(fakeStructureApi().handler).handler);
    renderApp("/documents/7");
    expect(await screen.findByRole("heading", { level: 2, name: "Test manual" })).toBeDefined();
  });

  it.each(["/no-such-page", "/devices", "/devices/plc-1", "/documents/1/extra", "/selftest/x"])(
    "the unknown address %s shows NotFound inside the frame",
    async (path) => {
      fakeApi(manager);
      renderApp(path);

      expect(await screen.findByTestId("not-found")).toBeDefined();
      expect((await pageHeading()).textContent).toBe("Page not found");
      expect(mainNavigation()).toBeDefined();
    },
  );

  it("NotFound links back to the structure page", async () => {
    fakeApi(manager);
    const { router } = renderApp("/no-such-page");

    fireEvent.click(await screen.findByRole("link", { name: "Go to the structure" }));

    expect(await screen.findByRole("heading", { level: 2, name: "Structure" })).toBeDefined();
    expect(router.state.location.pathname).toBe("/");
  });

  it("shows NotFound in German", async () => {
    await changeLanguage("de");
    fakeApi(manager);
    renderApp("/no-such-page");

    expect(await screen.findByRole("heading", { level: 2, name: "Seite nicht gefunden" })).toBeDefined();
  });
});

describe("render errors", () => {
  it("a page that fails to render shows ErrorMessage and keeps the frame", async () => {
    // React and the router log the thrown error; that is expected here.
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.spyOn(console, "warn").mockImplementation(() => undefined);
    fakeApi(manager);
    function Broken(): ReactElement {
      throw new Error("broken page");
    }
    const router = createMemoryRouter(
      [
        {
          path: "/",
          element: <Layout />,
          children: [{ errorElement: <RouteError />, children: [{ index: true, element: <Broken /> }] }],
        },
      ],
      { initialEntries: ["/"] },
    );
    render(
      <QueryClientProvider client={createQueryClient()}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    expect(screen.getByTestId("error-summary").textContent).toBe(
      "Something went wrong on this page. Please try again.",
    );
    expect(screen.getByTestId("error-message").textContent).not.toContain("broken page");
    expect(await screen.findByRole("navigation", { name: enNav.label })).toBeDefined();
  });
});

/** The routes below the session guard, by path ("" for the start page). */
function sessionRoutes(): Map<string, unknown> {
  const frame = routes[0]?.children?.[0]?.children ?? [];
  const guarded = frame.find((route) => route.path === undefined)?.children ?? [];
  return new Map(guarded.map((route) => [route.path ?? "", route.element]));
}

/** Type of the page inside <RequireRole>, or of the element itself. */
function pageType(element: unknown): unknown {
  const outer = element as ReactElement<{ children?: unknown }>;
  const inner = outer.props.children as ReactElement | undefined;
  return inner?.type ?? outer.type;
}

describe("loading on demand (work order 062)", () => {
  it("loads every page except sign-in and structure when it is opened", () => {
    const pages = sessionRoutes();
    const lazy = [...pages].filter(([, element]) => pageType(element) === PageLoadBoundary).map(([path]) => path);

    expect(lazy).toEqual([
      "map",
      "search",
      "ingest",
      "devices/:deviceId",
      "documents/:documentId",
      "import",
      "audit",
      "selftest",
      "settings",
    ]);
    expect(pageType(pages.get(""))).toBe(StructurePage);
    const login = routes[0]?.children?.[0]?.children?.find((route) => route.path === "login");
    expect(pageType(login?.element)).toBe(LoginPage);
  });

  it("a page whose code cannot be loaded shows a notice with Reload and keeps the frame", async () => {
    // React logs the caught error; that is expected here.
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    fakeApi(manager);
    const page = lazyPage(() => Promise.reject(new TypeError("Failed to fetch dynamically imported module")));
    const router = createMemoryRouter(
      [
        {
          path: "/",
          element: <Layout />,
          children: [{ errorElement: <RouteError />, children: [{ index: true, element: page.element }] }],
        },
      ],
      { initialEntries: ["/"] },
    );
    render(
      <QueryClientProvider client={createQueryClient()}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    expect((await screen.findByTestId("page-load-failed-summary")).textContent).toBe("This page could not be loaded.");
    expect(screen.getByRole("button", { name: "Reload" })).toBeDefined();
    expect(screen.queryByTestId("error-message")).toBeNull();
    expect(await screen.findByRole("navigation", { name: enNav.label })).toBeDefined();
  });
});
