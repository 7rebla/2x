import { QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import type { ReactElement } from "react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createQueryClient } from "./api/queryClient.ts";
import { Layout } from "./components/Layout.tsx";
import { RouteError } from "./components/RouteError.tsx";
import { changeLanguage } from "./i18n.ts";
import enNav from "./locales/en/nav.json";
import { navigation } from "./navigation.ts";
import { fakeApi, manager } from "./test/fakeApi.ts";
import { renderApp } from "./test/renderApp.tsx";

// Routing inside the frame for a signed-in manager (who may see every page).
// Sign-in, redirects and roles: session.test.tsx.

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
  it.each([
    ["/", "Structure"],
    ["/import", "Import"],
    ["/audit", "Change log"],
    ["/devices/plc-1", "Device"],
    ["/documents/42", "File"],
  ])("%s shows the page %s", async (path, heading) => {
    fakeApi(manager);
    renderApp(path);

    expect((await pageHeading()).textContent).toBe(heading);
    expect(screen.getByTestId("page-placeholder")).toBeDefined();
    expect(screen.queryByTestId("not-found")).toBeNull();
  });

  it("/login shows the sign-in page to a visitor who is not signed in", async () => {
    fakeApi(null);
    renderApp("/login");

    expect((await pageHeading()).textContent).toBe("Sign in");
    expect(screen.getByTestId("login-form")).toBeDefined();
  });

  it("/selftest shows the self-test page", async () => {
    fakeApi(manager);
    renderApp("/selftest");

    expect((await pageHeading()).textContent).toBe("Self-test");
    expect(await screen.findByTestId("selftest-error")).toBeDefined();
  });

  it("passes the address parameters to the device and file pages", async () => {
    fakeApi(manager);
    renderApp("/devices/conveyor%20belt");
    expect((await screen.findByTestId("device-id")).textContent).toBe("conveyor belt");
    cleanup();

    renderApp("/documents/7");
    expect((await screen.findByTestId("document-id")).textContent).toBe("7");
  });

  it.each(["/no-such-page", "/devices", "/documents/1/extra", "/selftest/x"])(
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
