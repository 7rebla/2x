import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import type { ReactElement } from "react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Layout } from "./components/Layout.tsx";
import { RouteError } from "./components/RouteError.tsx";
import { changeLanguage } from "./i18n.ts";
import enNav from "./locales/en/nav.json";
import { navigation } from "./navigation.ts";
import { renderApp } from "./test/renderApp.tsx";

/** Keeps the self-test page (one of the navigation targets) away from the network. */
function stubFetch(): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.reject(new TypeError("Failed to fetch"))),
  );
}

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

function pageHeading(): HTMLElement {
  return screen.getByRole("heading", { level: 2 });
}

describe("frame", () => {
  it("shows the name, the navigation, the language switch and an empty user area", () => {
    renderApp("/");

    expect(screen.getByRole("heading", { level: 1, name: "2x" })).toBeDefined();
    const links = within(mainNavigation()).getAllByRole("link");
    expect(links.map((link) => link.textContent)).toEqual(
      navigation.map((entry) => enNav[entry.textKey]),
    );
    expect(links.map((link) => link.getAttribute("href"))).toEqual(
      navigation.map((entry) => entry.path),
    );
    expect(screen.getByTestId("language-switch")).toBeDefined();
    expect(screen.getByTestId("user-area").childNodes.length).toBe(0);
  });

  it("translates the navigation when the language changes", async () => {
    renderApp("/");

    fireEvent.change(screen.getByTestId("language-switch"), { target: { value: "de" } });

    const nav = await screen.findByRole("navigation", { name: "Hauptnavigation" });
    expect(within(nav).getAllByRole("link").map((link) => link.textContent)).toEqual([
      "Struktur",
      "Import",
      "Änderungsprotokoll",
      "Selbsttest",
    ]);
    expect(pageHeading().textContent).toBe("Struktur");
  });
});

describe("navigation", () => {
  it("starts on the structure page at /", () => {
    const { router } = renderApp("/");

    expect(router.state.location.pathname).toBe("/");
    expect(pageHeading().textContent).toBe("Structure");
    expect(within(mainNavigation()).getByRole("link", { name: "Structure" }).getAttribute("aria-current")).toBe(
      "page",
    );
  });

  it.each(navigation.map((entry) => [entry.path, enNav[entry.textKey]] as const))(
    "a click on the entry for %s shows the page %s",
    async (path, text) => {
      stubFetch();
      const { router } = renderApp(path === "/" ? "/import" : "/");

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
    const { router } = renderApp("/audit");

    fireEvent.click(screen.getByRole("link", { name: "2x" }));

    expect(await screen.findByRole("heading", { level: 2, name: "Structure" })).toBeDefined();
    expect(router.state.location.pathname).toBe("/");
  });
});

describe("addresses", () => {
  it.each([
    ["/", "Structure"],
    ["/import", "Import"],
    ["/audit", "Change log"],
    ["/login", "Sign in"],
    ["/devices/plc-1", "Device"],
    ["/documents/42", "File"],
  ])("%s shows the page %s", (path, heading) => {
    renderApp(path);

    expect(pageHeading().textContent).toBe(heading);
    expect(screen.getByTestId("page-placeholder")).toBeDefined();
    expect(screen.queryByTestId("not-found")).toBeNull();
  });

  it("/selftest shows the self-test page", async () => {
    stubFetch();
    renderApp("/selftest");

    expect(pageHeading().textContent).toBe("Self-test");
    expect(await screen.findByTestId("selftest-error")).toBeDefined();
  });

  it("passes the address parameters to the device and file pages", () => {
    renderApp("/devices/conveyor%20belt");
    expect(screen.getByTestId("device-id").textContent).toBe("conveyor belt");
    cleanup();

    renderApp("/documents/7");
    expect(screen.getByTestId("document-id").textContent).toBe("7");
  });

  it.each(["/no-such-page", "/devices", "/documents/1/extra", "/selftest/x"])(
    "the unknown address %s shows NotFound inside the frame",
    (path) => {
      renderApp(path);

      expect(screen.getByTestId("not-found")).toBeDefined();
      expect(pageHeading().textContent).toBe("Page not found");
      expect(mainNavigation()).toBeDefined();
    },
  );

  it("NotFound links back to the structure page", async () => {
    const { router } = renderApp("/no-such-page");

    fireEvent.click(screen.getByRole("link", { name: "Go to the structure" }));

    expect(await screen.findByRole("heading", { level: 2, name: "Structure" })).toBeDefined();
    expect(router.state.location.pathname).toBe("/");
  });

  it("shows NotFound in German", async () => {
    await changeLanguage("de");
    renderApp("/no-such-page");

    expect(pageHeading().textContent).toBe("Seite nicht gefunden");
  });
});

describe("render errors", () => {
  it("a page that fails to render shows ErrorMessage and keeps the frame", () => {
    // React and the router log the thrown error; that is expected here.
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.spyOn(console, "warn").mockImplementation(() => undefined);
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
    render(<RouterProvider router={router} />);

    expect(screen.getByTestId("error-summary").textContent).toBe(
      "Something went wrong on this page. Please try again.",
    );
    expect(screen.getByTestId("error-message").textContent).not.toContain("broken page");
    expect(mainNavigation()).toBeDefined();
  });
});
