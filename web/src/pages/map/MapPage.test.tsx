import { act, cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { changeLanguage } from "../../i18n.ts";
import { fakeApi, jsonResponse, manager, reader } from "../../test/fakeApi.ts";
import { renderApp } from "../../test/renderApp.tsx";
import { fakeStructureApi, type Structure } from "../structure/testData.ts";

// jsdom has no layout. React Flow measures nodes through ResizeObserver and
// offsetWidth/offsetHeight and reads the zoom from DOMMatrixReadOnly; these
// stand-ins follow the testing notes of React Flow. Sizes come from the
// inline styles (every map node has a fixed width and height).

class ResizeObserverStub {
  private readonly callback: ResizeObserverCallback;

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
  }

  observe(target: Element): void {
    this.callback([{ target } as ResizeObserverEntry], this);
  }

  unobserve(): void {
    // Nothing to stop.
  }

  disconnect(): void {
    // Nothing to stop.
  }
}

class DOMMatrixReadOnlyStub {
  readonly m22: number;

  constructor(transform?: string) {
    const scale = /scale\(([\d.]+)\)/.exec(transform ?? "")?.[1];
    this.m22 = scale === undefined ? 1 : Number(scale);
  }
}

const originalOffsets = {
  height: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetHeight"),
  width: Object.getOwnPropertyDescriptor(HTMLElement.prototype, "offsetWidth"),
};

beforeAll(() => {
  // Edge labels measure their text.
  Object.defineProperty(SVGElement.prototype, "getBBox", {
    configurable: true,
    value: () => ({ x: 0, y: 0, width: 40, height: 12 }),
  });
  Object.defineProperties(HTMLElement.prototype, {
    offsetHeight: {
      configurable: true,
      get(this: HTMLElement): number {
        return Number.parseFloat(this.style.height) || 1;
      },
    },
    offsetWidth: {
      configurable: true,
      get(this: HTMLElement): number {
        return Number.parseFloat(this.style.width) || 1;
      },
    },
  });
});

afterAll(() => {
  Reflect.deleteProperty(SVGElement.prototype, "getBBox");
  for (const [name, descriptor] of Object.entries({
    offsetHeight: originalOffsets.height,
    offsetWidth: originalOffsets.width,
  })) {
    if (descriptor !== undefined) {
      Object.defineProperty(HTMLElement.prototype, name, descriptor);
    }
  }
});

beforeEach(() => {
  vi.stubGlobal("ResizeObserver", ResizeObserverStub);
  vi.stubGlobal("DOMMatrixReadOnly", DOMMatrixReadOnlyStub);
});

afterEach(async () => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  await changeLanguage("en");
  window.localStorage.clear();
});

async function openMap(): Promise<HTMLElement> {
  // The page is loaded lazily; the first import of React Flow may take a moment.
  return screen.findByTestId("map-canvas", {}, { timeout: 5000 });
}

function deviceNode(name: RegExp): HTMLElement {
  return screen.getByRole("link", { name });
}

describe("map page", () => {
  it("shows the structure and the networks to the role read", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/map");
    const canvas = await openMap();

    expect(screen.getByRole("heading", { level: 2 }).textContent).toBe("Map");
    expect(screen.getByRole("region", { name: "Map of sites, areas, plants, devices and networks" })).toBe(canvas);
    // Groups with name (and key), devices with name, key, address and model.
    const plants = within(canvas).getAllByTestId("map-plant");
    expect(plants.map((element) => element.textContent)).toEqual([
      "PlantTest plant onetest-plant-1",
      "PlantTest plant twotest-plant-2",
      "PlantTest plant threetest-plant-3",
    ]);
    expect(within(canvas).getAllByTestId("map-site").map((element) => element.textContent)).toEqual([
      "SiteTest site A",
      "SiteTest site B",
    ]);
    const controller = deviceNode(/^Device Test controller \(test-plc-1\)/);
    expect(controller.getAttribute("aria-label")).toBe(
      "Device Test controller (test-plc-1), 192.0.2.10 in network 192.0.2.0/24, opens the device page",
    );
    expect(within(controller).getByTestId("map-device").textContent).toBe(
      "Test controllertest-plc-1192.0.2.10Test model",
    );
    expect(deviceNode(/^Device Test remote I\/O \(test-io-1\), opens/)).toBeDefined();
    expect(within(canvas).getAllByTestId("map-device")).toHaveLength(4);
    const network = within(canvas).getByTestId("map-network");
    expect(network.textContent).toBe("Network192.0.2.0/24");
    expect(network.closest(".react-flow__node")?.getAttribute("aria-label")).toBe("Network 192.0.2.0/24 with 3 devices");
    // Every node shows the decorative icon of its kind (work order 071).
    expect(plants[0]?.querySelector("svg[aria-hidden='true']")?.getAttribute("data-icon")).toBe("plant");
    expect(within(canvas).getAllByTestId("map-site")[0]?.querySelector("svg")?.getAttribute("data-icon")).toBe("site");
    expect(within(controller).getByTestId("map-device").querySelector("svg")?.getAttribute("data-icon")).toBe("device");
    expect(network.querySelector("svg")?.getAttribute("data-icon")).toBe("network");
    // Controls and overview with their own names; the list view stays reachable.
    // "Fit view" is the button above the map, with its icon (the one of React Flow is off).
    expect(screen.getByRole("button", { name: "Fit view" }).querySelector("svg")?.getAttribute("data-icon")).toBe("fitView");
    expect(screen.getByRole("button", { name: "Zoom in" })).toBeDefined();
    expect(screen.getByTestId("map-list-link").getAttribute("href")).toBe("/");
    expect(screen.getByText(/Dashed line: the device's address lies in this network/)).toBeDefined();
  });

  it("is in the navigation for the role read", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    const { router } = renderApp("/");
    const navigation = await screen.findByRole("navigation", { name: "Main navigation" });

    fireEvent.click(within(navigation).getByRole("link", { name: "Map" }));

    await openMap();
    expect(router.state.location.pathname).toBe("/map");
  });

  it("opens the device page on a click on a device", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    const { router } = renderApp("/map");
    await openMap();

    fireEvent.click(within(deviceNode(/^Device Test panel/)).getByTestId("map-device"));

    expect(await screen.findByRole("heading", { level: 2, name: "Test panel" })).toBeDefined();
    expect(router.state.location.pathname).toBe("/devices/1001");
  });

  it("opens the device page with Enter on a focused device", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    const { router } = renderApp("/map");
    await openMap();

    const node = deviceNode(/^Device Test drive/);
    expect(node.tabIndex).toBe(0);
    act(() => {
      node.focus();
    });
    fireEvent.keyDown(node, { key: "Enter" });

    expect(await screen.findByRole("heading", { level: 2, name: "Test drive" })).toBeDefined();
    expect(router.state.location.pathname).toBe("/devices/1003");
  });

  it("does not open a page for Enter on a group", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    const { router } = renderApp("/map");
    const canvas = await openMap();

    const group = within(canvas).getAllByTestId("map-plant")[0]?.closest<HTMLElement>(".react-flow__node");
    if (group === null || group === undefined) {
      throw new Error("no plant node");
    }
    expect(group.getAttribute("aria-label")).toBe("Plant Test plant one (test-plant-1)");
    fireEvent.keyDown(group, { key: "Enter" });

    expect(router.state.location.pathname).toBe("/map");
  });

  it("highlights a focused device and its network line", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/map");
    await openMap();

    const node = deviceNode(/^Device Test drive/);
    act(() => {
      node.focus();
    });

    await waitFor(() => {
      expect(within(node).getByTestId("map-device").getAttribute("data-highlighted")).toBe("true");
    });
    expect(screen.getByTestId("map-network").getAttribute("data-highlighted")).toBe("true");
    const others = screen
      .getAllByTestId("map-device")
      .filter((element) => element.getAttribute("data-highlighted") === "true");
    expect(others).toHaveLength(1);
  });

  it("marks search matches by name, key or IP address and reports their number", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/map");
    await openMap();
    const search = screen.getByLabelText("Search on the map");

    fireEvent.change(search, { target: { value: "test-hmi" } });
    await waitFor(() => {
      expect(screen.getByTestId("map-search-status").textContent).toBe("1 match");
    });
    expect(within(deviceNode(/^Device Test panel/)).getByTestId("map-device").getAttribute("data-match")).toBe("true");
    expect(document.querySelectorAll('[data-match="true"]')).toHaveLength(1);

    fireEvent.change(search, { target: { value: "192.0.2.1" } });
    await waitFor(() => {
      expect(screen.getByTestId("map-search-status").textContent).toBe("2 matches");
    });

    fireEvent.change(search, { target: { value: "nothing like this" } });
    await waitFor(() => {
      expect(screen.getByTestId("map-search-status").textContent).toBe("No match");
    });
    expect(document.querySelectorAll('[data-match="true"]')).toHaveLength(0);
  });

  it("hides and shows the network nodes", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/map");
    await openMap();
    const toggle = screen.getByLabelText("Show networks");
    expect((toggle as HTMLInputElement).checked).toBe(true);

    fireEvent.click(toggle);
    await waitFor(() => {
      expect(screen.queryByTestId("map-network")).toBeNull();
    });

    fireEvent.click(toggle);
    expect(await screen.findByTestId("map-network")).toBeDefined();
  });

  it("shows a hint with a link to the structure page when nothing is recorded", async () => {
    const empty: Structure = { sites: [], areas: [], plants: [], devices: [] };
    fakeApi(manager, fakeStructureApi(empty).handler);
    const { router } = renderApp("/map");

    const hint = await screen.findByTestId("map-empty", {}, { timeout: 5000 });
    expect(hint.textContent).toContain("No structure recorded yet.");
    expect(screen.queryByTestId("map-canvas")).toBeNull();

    fireEvent.click(within(hint).getByRole("link", { name: "Go to the structure" }));
    expect(await screen.findByRole("heading", { level: 2, name: "Structure" })).toBeDefined();
    expect(router.state.location.pathname).toBe("/");
  });

  it("shows an error of the API", async () => {
    fakeApi(reader, () => jsonResponse({ detail: "Test failure" }, 500));
    renderApp("/map");

    const message = await screen.findByTestId("error-message", {}, { timeout: 5000 });
    expect(message.textContent).toContain("Test failure");
    expect(screen.queryByTestId("map-canvas")).toBeNull();
  });

  it("shows the texts in German", async () => {
    await changeLanguage("de");
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/map");
    await openMap();

    expect(screen.getByRole("heading", { level: 2 }).textContent).toBe("Landkarte");
    expect(screen.getByLabelText("Auf der Karte suchen")).toBeDefined();
    expect(screen.getByLabelText("Netze anzeigen")).toBeDefined();
    expect(screen.getByRole("button", { name: "Ansicht einpassen" })).toBeDefined();
    expect(deviceNode(/^Gerät Test drive \(test-drive-1\), 192\.0\.2\.20 im Netz 192\.0\.2\.0\/24/)).toBeDefined();
    expect(screen.getByTestId("map-network").textContent).toBe("Netz192.0.2.0/24");
    expect(screen.getByTestId("map-list-link").textContent).toBe("Struktur als Liste ansehen");
  });
});
