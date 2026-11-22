import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";

import { changeLanguage } from "../i18n.ts";
import { refreshDisplay, updateDisplaySettings } from "../theme/store.ts";
import {
  lazyPage,
  PAGE_LOADING_DELAY_MS,
  PageLoadBoundary,
  PageLoadError,
  PageLoadFailed,
  PageLoading,
} from "./PageLoading.tsx";
import { RouteError } from "./RouteError.tsx";

afterEach(async () => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
  window.localStorage.clear();
  refreshDisplay();
  await changeLanguage("en");
});

/** Class names of the element and everything inside it that belong to a text animation. */
function animationClasses(element: Element): string[] {
  return [element, ...element.querySelectorAll("*")]
    .flatMap((node) => [...node.classList])
    .filter((name) => name.startsWith("tx-") || name.startsWith("animate-"));
}

/** A promise with its resolve and reject functions, to decide in the test when a page "arrives". */
function deferred<T>(): { promise: Promise<T>; resolve: (value: T) => void; reject: (reason: unknown) => void } {
  let resolve: (value: T) => void = () => undefined;
  let reject: (reason: unknown) => void = () => undefined;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function TestPage(): ReactElement {
  return <h2>Test page</h2>;
}

/** Renders `element` as the only page of a router, with the usual error element of a route. */
function renderPage(element: ReactElement): void {
  const router = createMemoryRouter([{ path: "/", element, errorElement: <RouteError /> }], {
    initialEntries: ["/"],
  });
  render(<RouterProvider router={router} />);
}

describe("PageLoading", () => {
  it("keeps quiet at first and shows the loading state after a short delay", () => {
    vi.useFakeTimers();
    render(<PageLoading />);

    const frame = screen.getByTestId("page-loading");
    expect(frame.getAttribute("aria-busy")).toBe("true");
    expect(screen.queryByRole("status")).toBeNull();

    act(() => {
      vi.advanceTimersByTime(PAGE_LOADING_DELAY_MS - 1);
    });
    expect(screen.queryByRole("status")).toBeNull();

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(screen.getByRole("status").textContent).toBe("Loading page…");
    // Pattern D of the text animations and the turning icon (E-52).
    expect(animationClasses(frame)).toEqual(["animate-spin", "tx-sheen", "tx-dots"]);
  });

  it("says it in German", async () => {
    await changeLanguage("de");
    vi.useFakeTimers();
    render(<PageLoading />);

    act(() => {
      vi.advanceTimersByTime(PAGE_LOADING_DELAY_MS);
    });
    expect(screen.getByRole("status").textContent).toBe("Seite wird geladen…");
  });

  it("does not shimmer when the user reduces motion", () => {
    act(() => {
      updateDisplaySettings({ reduceMotion: true });
    });
    vi.useFakeTimers();
    render(<PageLoading />);

    act(() => {
      vi.advanceTimersByTime(PAGE_LOADING_DELAY_MS);
    });
    expect(screen.getByRole("status").textContent).toBe("Loading page…");
    // The icon keeps its class; index.css stops every animation while motion is reduced.
    expect(animationClasses(screen.getByTestId("page-loading"))).toEqual(["animate-spin"]);
  });
});

describe("PageLoadFailed", () => {
  it("explains the problem and reloads on request", () => {
    const onReload = vi.fn();
    render(<PageLoadFailed onReload={onReload} />);

    expect(screen.getByRole("alert")).toBeDefined();
    expect(screen.getByTestId("page-load-failed-summary").textContent).toBe("This page could not be loaded.");
    expect(screen.getByTestId("page-load-failed").textContent).toContain("Reloading usually helps.");

    fireEvent.click(screen.getByRole("button", { name: "Reload" }));
    expect(onReload).toHaveBeenCalledTimes(1);
  });

  it("says it in German", async () => {
    await changeLanguage("de");
    render(<PageLoadFailed onReload={vi.fn()} />);

    expect(screen.getByTestId("page-load-failed-summary").textContent).toBe("Diese Seite konnte nicht geladen werden.");
    expect(screen.getByRole("button", { name: "Neu laden" })).toBeDefined();
  });
});

describe("lazyPage", () => {
  it("shows the loading state until the page has arrived, then the page", async () => {
    const arrival = deferred<typeof TestPage>();
    const page = lazyPage(() => arrival.promise);
    renderPage(page.element);

    expect(await screen.findByTestId("page-loading")).toBeDefined();
    expect(screen.queryByRole("heading", { name: "Test page" })).toBeNull();

    arrival.resolve(TestPage);

    expect(await screen.findByRole("heading", { name: "Test page" })).toBeDefined();
    expect(screen.queryByTestId("page-loading")).toBeNull();
  });

  it("shows a notice with Reload instead of an empty page when the code cannot be loaded", async () => {
    // React logs the caught error; that is expected here.
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const page = lazyPage(() =>
      Promise.reject(new TypeError("Failed to fetch dynamically imported module: /static/assets/MapPage-old.js")),
    );
    renderPage(page.element);

    expect(await screen.findByTestId("page-load-failed")).toBeDefined();
    expect(screen.getByRole("button", { name: "Reload" })).toBeDefined();
    expect(screen.queryByTestId("error-message")).toBeNull();
    expect(screen.queryByTestId("page-load-failed")?.textContent).not.toContain("MapPage-old");
  });

  it("passes other errors of the page on to the error element of the route", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.spyOn(console, "warn").mockImplementation(() => undefined);
    function Broken(): ReactElement {
      throw new Error("broken page");
    }
    const page = lazyPage(() => Promise.resolve(Broken));
    renderPage(page.element);

    expect((await screen.findByTestId("error-summary")).textContent).toBe(
      "Something went wrong on this page. Please try again.",
    );
    expect(screen.queryByTestId("page-load-failed")).toBeNull();
  });

  it("preload loads the code without rendering anything", async () => {
    const load = vi.fn(() => Promise.resolve(TestPage));
    const page = lazyPage(load);

    await page.preload();

    expect(load).toHaveBeenCalledTimes(1);
  });
});

describe("PageLoadBoundary", () => {
  it("catches only PageLoadError and hands the reload to its caller", () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const onReload = vi.fn();
    function Failing(): ReactElement {
      throw new PageLoadError(new TypeError("Failed to fetch"));
    }
    render(
      <PageLoadBoundary onReload={onReload}>
        <Failing />
      </PageLoadBoundary>,
    );

    fireEvent.click(screen.getByTestId("page-reload"));
    expect(onReload).toHaveBeenCalledTimes(1);
  });
});
