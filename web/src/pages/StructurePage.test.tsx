import { cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { changeLanguage } from "../i18n.ts";
import { fakeApi, jsonResponse, manager, reader } from "../test/fakeApi.ts";
import { renderApp } from "../test/renderApp.tsx";
import { COLLAPSED_STORAGE_KEY } from "./structure/collapse.ts";
import { fakeStructureApi } from "./structure/testData.ts";

afterEach(async () => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  await changeLanguage("en");
  window.localStorage.clear();
});

function itemNamed(testId: string, name: string): HTMLElement {
  const item = screen
    .getAllByTestId(testId)
    .find((element) => element.querySelector(`[data-testid$="-name"]`)?.textContent === name);
  if (item === undefined) {
    throw new Error(`no ${testId} named ${name}`);
  }
  return item;
}

/** Text of the first device count inside an item (its own row comes first). */
function countOf(item: HTMLElement): string | null {
  return within(item).getAllByTestId("device-count")[0]?.textContent ?? null;
}

function form(name: string): HTMLElement {
  return screen.getByRole("form", { name });
}

function type(container: HTMLElement, label: string, value: string): void {
  fireEvent.change(within(container).getByLabelText(label), { target: { value } });
}

async function openTree(): Promise<HTMLElement> {
  return screen.findByTestId("structure-tree");
}

describe("structure tree", () => {
  it("shows sites, areas, plants and devices with the number of devices", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    expect(screen.getAllByTestId("site-name").map((element) => element.textContent)).toEqual([
      "Test site A",
      "Test site B",
    ]);
    expect(countOf(itemNamed("site-item", "Test site A"))).toBe("4 devices");
    expect(countOf(itemNamed("site-item", "Test site B"))).toBe("0 devices");
    expect(countOf(itemNamed("area-item", "Test area A2"))).toBe("1 device");
    expect(countOf(itemNamed("plant-item", "Test plant one"))).toBe("3 devices");

    const plantOne = itemNamed("plant-item", "Test plant one");
    expect(within(plantOne).getByTestId("plant-key").textContent).toBe("test-plant-1");
    const link = within(plantOne).getByRole("link", { name: "Test controller" });
    expect(link.getAttribute("href")).toBe("/devices/1000");
    expect(within(plantOne).getAllByTestId("device-ip").map((element) => element.textContent)).toEqual([
      "192.0.2.11",
      "192.0.2.10",
    ]);
  });

  it("shows each device with the icon and the name of its class, each plant with the plant icon", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    const iconOf = (element: Element | undefined): string | null | undefined =>
      element?.querySelector("svg[aria-hidden='true']")?.getAttribute("data-icon");
    const deviceRow = (name: string): HTMLElement => {
      const row = screen
        .getAllByTestId("device-item")
        .find((element) => within(element).queryByRole("link", { name }) !== null);
      if (row === undefined) {
        throw new Error(`no device row ${name}`);
      }
      return row;
    };
    const plc = within(deviceRow("Test controller")).getByTestId("device-class");
    expect(plc.textContent).toBe("PLC");
    expect(iconOf(plc)).toBe("devicePlc");
    const other = within(deviceRow("Test panel")).getByTestId("device-class");
    expect(other.textContent).toBe("Other");
    expect(iconOf(other)).toBe("device");
    // The label of the kind, after the fold button of the row.
    expect(iconOf(within(itemNamed("plant-item", "Test plant one")).getByText("Plant"))).toBe("plant");
  });

  it("shows the texts in German", async () => {
    await changeLanguage("de");
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Struktur");
    expect(countOf(itemNamed("site-item", "Test site A"))).toBe("4 Geräte");
    expect(countOf(itemNamed("area-item", "Test area A2"))).toBe("1 Gerät");
    expect(screen.getByLabelText("Suche")).toBeDefined();
    expect(screen.getAllByText("Standort")).toHaveLength(2);
    expect(screen.getAllByTestId("device-class").map((element) => element.textContent)).toContain("SPS");
  });

  it("says so when there is no site yet", async () => {
    fakeApi(reader, fakeStructureApi({ sites: [], areas: [], plants: [], devices: [] }).handler);
    renderApp("/");

    expect((await screen.findByTestId("structure-empty")).textContent).toBe("There are no sites yet.");
  });

  it("shows the error of the API instead of the tree", async () => {
    fakeApi(reader, () => jsonResponse({ detail: "Server trouble." }, 500));
    renderApp("/");

    expect((await screen.findByTestId("error-summary")).textContent).toBe("The API answered with HTTP status 500.");
    expect(screen.queryByTestId("structure-tree")).toBeNull();
  });
});

describe("search", () => {
  it("filters by name, key and IP address in the browser", async () => {
    const api = fakeApi(reader, fakeStructureApi().handler);
    renderApp("/");
    await openTree();
    const requestsBefore = api.fetch.mock.calls.length;
    const search = screen.getByLabelText("Search");

    fireEvent.change(search, { target: { value: "192.0.2.20" } });
    await waitFor(() => {
      expect(screen.getAllByTestId("device-item")).toHaveLength(1);
    });
    expect(screen.getByRole("link", { name: "Test drive" })).toBeDefined();
    expect(screen.getAllByTestId("site-name").map((element) => element.textContent)).toEqual(["Test site A"]);

    fireEvent.change(search, { target: { value: "TEST-HMI" } });
    await waitFor(() => {
      expect(screen.getAllByTestId("device-item").map((element) => element.textContent)).toEqual([
        expect.stringContaining("Test panel"),
      ]);
    });

    fireEvent.change(search, { target: { value: "Test panel" } });
    await waitFor(() => {
      expect(screen.getAllByTestId("device-item")).toHaveLength(1);
    });

    fireEvent.change(search, { target: { value: "nothing like this" } });
    expect((await screen.findByTestId("structure-no-match")).textContent).toBe("Nothing matches the search.");

    fireEvent.change(search, { target: { value: "" } });
    await waitFor(() => {
      expect(screen.getAllByTestId("device-item")).toHaveLength(4);
    });
    // The search needs no further request.
    expect(api.fetch.mock.calls.length).toBe(requestsBefore);
  });
});

describe("search status", () => {
  it("announces the number of shown devices in a live region, and nothing without a search", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/");
    await openTree();
    const status = screen.getByTestId("structure-search-status");
    expect(status.getAttribute("role")).toBe("status");
    expect(status.textContent).toBe("");

    fireEvent.change(screen.getByLabelText("Search"), { target: { value: "192.0.2.1" } });
    await waitFor(() => {
      expect(status.textContent).toBe("2 devices shown");
    });

    fireEvent.change(screen.getByLabelText("Search"), { target: { value: "Test drive" } });
    await waitFor(() => {
      expect(status.textContent).toBe("1 device shown");
    });

    // A plant that matches by name shows all its devices, here none.
    fireEvent.change(screen.getByLabelText("Search"), { target: { value: "test-plant-2" } });
    await waitFor(() => {
      expect(status.textContent).toBe("0 devices shown");
    });

    // "Nothing matches" is announced by the same region.
    fireEvent.change(screen.getByLabelText("Search"), { target: { value: "nothing like this" } });
    await waitFor(() => {
      expect(within(status).getByTestId("structure-no-match").textContent).toBe("Nothing matches the search.");
    });
    expect(screen.queryByTestId("structure-tree")).toBeNull();

    fireEvent.change(screen.getByLabelText("Search"), { target: { value: "" } });
    await waitFor(() => {
      expect(status.textContent).toBe("");
    });
  });

  it("counts in German", async () => {
    await changeLanguage("de");
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    fireEvent.change(screen.getByLabelText("Suche"), { target: { value: "Test plant one" } });
    await waitFor(() => {
      expect(screen.getByTestId("structure-search-status").textContent).toBe("3 Geräte angezeigt");
    });
  });
});

describe("rows", () => {
  it("puts class, name, key and address of every device in the columns of one grid per plant", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    const list = within(itemNamed("plant-item", "Test plant one")).getByTestId("device-list");
    expect(list.className).toContain("grid-cols-[auto_minmax(0,1fr)]");
    expect(list.className).toContain("sm:grid-cols-[auto_minmax(0,1fr)_auto_auto]");
    // From 1024 px least widths line up the columns of different plants.
    expect(list.className).toContain("lg:grid-cols-[minmax(11rem,auto)_minmax(0,1fr)_minmax(8rem,auto)_minmax(8rem,auto)]");
    const rows = within(list).getAllByTestId("device-item");
    expect(rows).toHaveLength(3);
    for (const row of rows) {
      // Each row is a subgrid with four cells, also without an address.
      expect(row.className).toContain("grid-cols-subgrid");
      const cells = [...row.children];
      expect(cells[0]?.getAttribute("data-testid")).toBe("device-class");
      expect(cells[1]?.tagName).toBe("A");
      expect(cells[2]?.className).toContain("sm:contents");
      expect(cells[2]?.children).toHaveLength(2);
      expect(cells[2]?.children[0]?.getAttribute("data-testid")).toBe("device-key");
    }
    expect(within(list).getAllByTestId("device-ip")).toHaveLength(2);
  });

  it("names the device class as tooltip and for screen readers, shown as text from 640 px", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    const [first] = screen.getAllByTestId("device-class");
    expect(first?.getAttribute("title")).toBe(first?.textContent);
    expect(first?.querySelector("span")?.className).toBe("sr-only sm:not-sr-only");
  });

  it("shows the actions of a manager as icon buttons named by action and item, on the right of the row", async () => {
    fakeApi(manager, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    const edit = screen.getByRole("button", { name: "Edit plant Test plant one" });
    const create = screen.getByRole("button", { name: "New device in Test plant one" });
    for (const button of [edit, create]) {
      // No visible text, an icon, the label as tooltip.
      expect(button.textContent).toBe("");
      expect(button.querySelector("svg")?.getAttribute("aria-hidden")).toBe("true");
      expect(button.getAttribute("title")).toBe(button.getAttribute("aria-label"));
    }
    expect(edit.querySelector("svg")?.getAttribute("data-icon")).toBe("edit");
    expect(create.querySelector("svg")?.getAttribute("data-icon")).toBe("create");
    // Both stand in the last part of the row, which fades in on hover or focus with a mouse.
    const actions = edit.parentElement;
    expect(actions?.lastElementChild).toBe(create);
    expect(actions?.parentElement?.lastElementChild).toBe(actions);
    expect(actions?.className).toContain("pointer-fine:opacity-0");
    expect(actions?.className).toContain("pointer-fine:group-hover:opacity-100");
    expect(actions?.className).toContain("pointer-fine:group-focus-within:opacity-100");
    expect(actions?.parentElement?.className).toContain("group");
  });
});

describe("folding", () => {
  function toggle(name: string): HTMLElement {
    return screen.getByRole("button", { name });
  }

  it("folds areas and plants with a button that says whether it is open", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    const area = toggle("Contents of area Test area A1");
    expect(area.getAttribute("aria-expanded")).toBe("true");
    const plantList = itemNamed("area-item", "Test area A1").querySelector("ul");
    expect(area.getAttribute("aria-controls")).toBe(plantList?.id);

    fireEvent.click(area);
    expect(area.getAttribute("aria-expanded")).toBe("false");
    expect(area.getAttribute("aria-controls")).toBeNull();
    expect(screen.getAllByTestId("plant-name").map((element) => element.textContent)).toEqual(["Test plant three"]);
    // The count of the folded area stays.
    expect(countOf(itemNamed("area-item", "Test area A1"))).toBe("3 devices");

    fireEvent.click(toggle("Devices of plant Test plant three"));
    expect(screen.queryAllByTestId("device-item")).toHaveLength(0);
    expect(toggle("Devices of plant Test plant three").getAttribute("aria-expanded")).toBe("false");

    fireEvent.click(area);
    expect(screen.getAllByTestId("device-item")).toHaveLength(3);
  });

  it("has no fold button for an area or plant without children", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    expect(screen.queryByRole("button", { name: "Devices of plant Test plant two" })).toBeNull();
    expect(screen.getByRole("button", { name: "Devices of plant Test plant one" })).toBeDefined();
  });

  it("keeps the folded branches in this browser", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/");
    await openTree();
    fireEvent.click(toggle("Contents of area Test area A2"));
    fireEvent.click(toggle("Devices of plant Test plant one"));
    expect(JSON.parse(window.localStorage.getItem(COLLAPSED_STORAGE_KEY) ?? "null")).toEqual([
      "area:11",
      "plant:100",
    ]);
    cleanup();

    renderApp("/");
    await openTree();
    expect(toggle("Contents of area Test area A2").getAttribute("aria-expanded")).toBe("false");
    expect(toggle("Devices of plant Test plant one").getAttribute("aria-expanded")).toBe("false");
    expect(toggle("Contents of area Test area A1").getAttribute("aria-expanded")).toBe("true");
    expect(screen.queryAllByTestId("device-item")).toHaveLength(0);

    fireEvent.click(toggle("Contents of area Test area A2"));
    fireEvent.click(toggle("Devices of plant Test plant one"));
    expect(window.localStorage.getItem(COLLAPSED_STORAGE_KEY)).toBeNull();
  });

  it("unfolds the hits of a search and folds them again when the search is cleared", async () => {
    window.localStorage.setItem(COLLAPSED_STORAGE_KEY, JSON.stringify(["area:10", "plant:102"]));
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/");
    await openTree();
    expect(screen.queryAllByTestId("device-item")).toHaveLength(0);
    const search = screen.getByLabelText("Search");

    // Every plant key matches, so every plant shows with all its devices.
    fireEvent.change(search, { target: { value: "test-plant" } });
    await waitFor(() => {
      expect(screen.getAllByTestId("device-item")).toHaveLength(4);
    });
    expect(toggle("Contents of area Test area A1").getAttribute("aria-expanded")).toBe("true");

    // Folding during a search lasts for this search text only and is not stored.
    fireEvent.click(toggle("Devices of plant Test plant three"));
    expect(screen.getAllByTestId("device-item")).toHaveLength(3);
    expect(JSON.parse(window.localStorage.getItem(COLLAPSED_STORAGE_KEY) ?? "null")).toEqual(["area:10", "plant:102"]);
    fireEvent.change(search, { target: { value: "test-plant-" } });
    await waitFor(() => {
      expect(screen.getAllByTestId("device-item")).toHaveLength(4);
    });

    // Unfolding during a search is stored.
    fireEvent.change(search, { target: { value: "Test area A1" } });
    await waitFor(() => {
      expect(screen.getAllByTestId("area-item")).toHaveLength(1);
    });
    fireEvent.click(toggle("Contents of area Test area A1"));
    fireEvent.click(toggle("Contents of area Test area A1"));
    expect(JSON.parse(window.localStorage.getItem(COLLAPSED_STORAGE_KEY) ?? "null")).toEqual(["plant:102"]);

    fireEvent.change(search, { target: { value: "" } });
    await waitFor(() => {
      expect(screen.getAllByTestId("area-item")).toHaveLength(2);
    });
    expect(toggle("Contents of area Test area A1").getAttribute("aria-expanded")).toBe("true");
    expect(toggle("Devices of plant Test plant three").getAttribute("aria-expanded")).toBe("false");
    expect(screen.getAllByTestId("device-item")).toHaveLength(3);
  });

  it("unfolds a plant when a device is added to it", async () => {
    window.localStorage.setItem(COLLAPSED_STORAGE_KEY, JSON.stringify(["plant:100"]));
    fakeApi(manager, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    fireEvent.click(screen.getByRole("button", { name: "New device in Test plant one" }));
    expect(toggle("Devices of plant Test plant one").getAttribute("aria-expanded")).toBe("true");
    expect(form("New device")).toBeDefined();
    expect(window.localStorage.getItem(COLLAPSED_STORAGE_KEY)).toBeNull();
  });

  it("works without a usable storage, unfolded at the start", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/");
    await openTree();
    expect(screen.getAllByTestId("device-item")).toHaveLength(4);

    fireEvent.click(toggle("Devices of plant Test plant one"));
    expect(screen.getAllByTestId("device-item")).toHaveLength(1);
  });

  it("names the fold buttons in German", async () => {
    await changeLanguage("de");
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    expect(screen.getByRole("button", { name: "Inhalt von Bereich Test area A1" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Geräte von Anlage Test plant one" })).toBeDefined();
  });
});

describe("buttons per role", () => {
  it("a reader sees no button to create or edit, but can fold", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    expect(screen.queryByRole("button", { name: "New site" })).toBeNull();
    expect(screen.queryByRole("button", { name: /^Edit/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /^New/ })).toBeNull();
    expect(screen.getByRole("button", { name: "Contents of area Test area A1" })).toBeDefined();
  });

  it("a manager sees create and edit buttons on every level", async () => {
    fakeApi(manager, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    expect(screen.getByRole("button", { name: "New site" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Edit site Test site A" })).toBeDefined();
    expect(screen.getByRole("button", { name: "New area in Test site A" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Edit area Test area A1" })).toBeDefined();
    expect(screen.getByRole("button", { name: "New plant in Test area A1" })).toBeDefined();
    expect(screen.getByRole("button", { name: "Edit plant Test plant one" })).toBeDefined();
    expect(screen.getByRole("button", { name: "New device in Test plant one" })).toBeDefined();
  });
});

describe("forms", () => {
  it("creates a site, reloads the data and closes the form", async () => {
    const structureApi = fakeStructureApi();
    const api = fakeApi(manager, structureApi.handler);
    renderApp("/");
    await openTree();
    expect(api.requestsTo("/api/v1/sites/")).toHaveLength(1);

    fireEvent.click(screen.getByRole("button", { name: "New site" }));
    type(form("New site"), "Name", "Test site C");
    fireEvent.click(within(form("New site")).getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(screen.getAllByTestId("site-name").map((element) => element.textContent)).toContain("Test site C");
    });
    expect(screen.queryByRole("form", { name: "New site" })).toBeNull();
    const posts = api.requestsTo("/api/v1/sites/").filter((request) => request.method === "POST");
    expect(posts).toHaveLength(1);
    expect(await posts[0]?.clone().json()).toEqual({ name: "Test site C" });
    // Lists are fetched again after saving.
    expect(api.requestsTo("/api/v1/sites/").filter((request) => request.method === "GET")).toHaveLength(2);
    expect(api.requestsTo("/api/v1/devices/").filter((request) => request.method === "GET")).toHaveLength(2);
  });

  it("creates an area in the site whose button was used", async () => {
    const api = fakeApi(manager, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    fireEvent.click(screen.getByRole("button", { name: "New area in Test site B" }));
    const areaForm = form("New area");
    expect(within(areaForm).getByLabelText<HTMLSelectElement>("Site").value).toBe("2");
    type(areaForm, "Name", "Test area B1");
    fireEvent.click(within(areaForm).getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(countOf(itemNamed("area-item", "Test area B1"))).toBe("0 devices");
    });
    const post = api.requestsTo("/api/v1/areas/").find((request) => request.method === "POST");
    expect(await post?.clone().json()).toEqual({ site: 2, name: "Test area B1" });
  });

  it("edits an area with its values filled in", async () => {
    const api = fakeApi(manager, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    fireEvent.click(screen.getByRole("button", { name: "Edit area Test area A1" }));
    const areaForm = form("Edit area");
    expect(within(areaForm).getByLabelText<HTMLInputElement>("Name").value).toBe("Test area A1");
    expect(within(areaForm).getByLabelText<HTMLSelectElement>("Site").value).toBe("1");
    type(areaForm, "Name", "Test area A1 renamed");
    fireEvent.click(within(areaForm).getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(screen.getAllByTestId("area-name").map((element) => element.textContent)).toContain(
        "Test area A1 renamed",
      );
    });
    const put = api.requestsTo("/api/v1/areas/10/").find((request) => request.method === "PUT");
    expect(await put?.clone().json()).toEqual({ site: 1, name: "Test area A1 renamed" });
  });

  it("creates a plant with key and notes", async () => {
    const api = fakeApi(manager, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    fireEvent.click(screen.getByRole("button", { name: "New plant in Test area A2" }));
    const plantForm = form("New plant");
    type(plantForm, "Key", "test-plant-9");
    type(plantForm, "Name", "Test plant nine");
    type(plantForm, "Notes", "Line one\nLine two");
    fireEvent.click(within(plantForm).getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(screen.getAllByTestId("plant-key").map((element) => element.textContent)).toContain("test-plant-9");
    });
    const post = api.requestsTo("/api/v1/plants/").find((request) => request.method === "POST");
    expect(await post?.clone().json()).toEqual({
      area: 11,
      key: "test-plant-9",
      name: "Test plant nine",
      notes: "Line one\nLine two",
    });
  });

  it("shows the field errors of a 400 answer at the fields and keeps the entry", async () => {
    const structureApi = fakeStructureApi();
    const api = fakeApi(manager, structureApi.handler);
    renderApp("/");
    await openTree();

    fireEvent.click(screen.getByRole("button", { name: "New device in Test plant two" }));
    const deviceForm = form("New device");
    expect(within(deviceForm).getByLabelText<HTMLSelectElement>("Plant").value).toBe("101");
    type(deviceForm, "Key", "test-new-1");
    type(deviceForm, "Name", "Test new device");
    type(deviceForm, "IP address", "192.0.2.300");
    structureApi.rejectNextWrite(400, {
      ip_address: ["Enter a valid IPv4 or IPv6 address."],
      key: ["A device with this key exists already."],
    });
    fireEvent.click(within(deviceForm).getByRole("button", { name: "Save" }));

    const ipError = await within(deviceForm).findByTestId("field-error-ip_address");
    expect(ipError.textContent).toBe("Enter a valid IPv4 or IPv6 address.");
    expect(within(deviceForm).getByTestId("field-error-key").textContent).toBe(
      "A device with this key exists already.",
    );
    expect(within(deviceForm).queryByTestId("field-error-name")).toBeNull();
    const ipInput = within(deviceForm).getByLabelText<HTMLInputElement>("IP address");
    expect(ipInput.getAttribute("aria-invalid")).toBe("true");
    expect(ipInput.getAttribute("aria-describedby")).toBe(ipError.id);
    expect(within(deviceForm).getByTestId("form-invalid").textContent).toContain("Please check the marked fields.");
    // The entry stays in the fields.
    expect(ipInput.value).toBe("192.0.2.300");
    expect(within(deviceForm).getByLabelText<HTMLInputElement>("Name").value).toBe("Test new device");
    expect(within(deviceForm).getByLabelText<HTMLSelectElement>("Plant").value).toBe("101");

    // Corrected, the entry is saved; an empty field is sent as text, the address as given.
    type(deviceForm, "Key", "test-new-2");
    type(deviceForm, "IP address", "192.0.2.30");
    fireEvent.click(within(deviceForm).getByRole("button", { name: "Save" }));
    await waitFor(() => {
      expect(screen.getByRole("link", { name: "Test new device" })).toBeDefined();
    });
    expect(screen.queryByRole("form", { name: "New device" })).toBeNull();
    const posts = api.requestsTo("/api/v1/devices/").filter((request) => request.method === "POST");
    expect(posts).toHaveLength(2);
    expect(await posts[1]?.clone().json()).toEqual({
      plant: 101,
      key: "test-new-2",
      name: "Test new device",
      device_class: "other",
      manufacturer: "",
      model: "",
      software_version: "",
      ip_address: "192.0.2.30",
      address_source: "",
      protocols: "",
      notes: "",
    });
  });

  it("offers the seven device classes, starts with Other and sends the chosen one", async () => {
    const api = fakeApi(manager, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    fireEvent.click(screen.getByRole("button", { name: "New device in Test plant two" }));
    const deviceForm = form("New device");
    const select = within(deviceForm).getByLabelText<HTMLSelectElement>("Device class");
    expect([...select.options].map((option) => [option.value, option.textContent])).toEqual([
      ["plc", "PLC"],
      ["controller", "Controller / embedded"],
      ["computer", "Computer / edge"],
      ["router", "Router"],
      ["firewall", "Firewall"],
      ["robot", "Robot"],
      ["other", "Other"],
    ]);
    expect(select.value).toBe("other");
    type(deviceForm, "Key", "test-robot-1");
    type(deviceForm, "Name", "Test robot");
    fireEvent.change(select, { target: { value: "robot" } });
    fireEvent.click(within(deviceForm).getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(screen.getByRole("link", { name: "Test robot" })).toBeDefined();
    });
    const post = api.requestsTo("/api/v1/devices/").find((request) => request.method === "POST");
    expect(((await post?.clone().json()) as { device_class: unknown }).device_class).toBe("robot");
  });

  it("shows an error of the API at the device class and keeps the choice", async () => {
    const structureApi = fakeStructureApi();
    fakeApi(manager, structureApi.handler);
    renderApp("/");
    await openTree();

    fireEvent.click(screen.getByRole("button", { name: "New device in Test plant two" }));
    const deviceForm = form("New device");
    type(deviceForm, "Key", "test-new-3");
    type(deviceForm, "Name", "Test new device");
    fireEvent.change(within(deviceForm).getByLabelText("Device class"), { target: { value: "firewall" } });
    structureApi.rejectNextWrite(400, { device_class: ['"x" is not a valid choice.'] });
    fireEvent.click(within(deviceForm).getByRole("button", { name: "Save" }));

    const error = await within(deviceForm).findByTestId("field-error-device_class");
    expect(error.textContent).toBe('"x" is not a valid choice.');
    const select = within(deviceForm).getByLabelText<HTMLSelectElement>("Device class");
    expect(select.getAttribute("aria-invalid")).toBe("true");
    expect(select.value).toBe("firewall");
  });

  it("names the device classes in German", async () => {
    await changeLanguage("de");
    fakeApi(manager, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    fireEvent.click(screen.getByRole("button", { name: "Neues Gerät in Test plant two" }));
    const deviceForm = form("Neues Gerät");
    const select = within(deviceForm).getByLabelText<HTMLSelectElement>("Gerätetyp");
    expect([...select.options].map((option) => option.textContent)).toEqual([
      "SPS",
      "Controller/Embedded",
      "Rechner/Edge",
      "Router",
      "Firewall",
      "Roboter",
      "Sonstiges",
    ]);
  });

  it.each([
    ["Edit area Test area A1", "Edit area", "Site", "2", { name: ["Name taken."] }, "/api/v1/areas/10/"],
    ["Edit plant Test plant one", "Edit plant", "Area", "11", { key: ["Key taken."] }, "/api/v1/plants/100/"],
    ["New device in Test plant two", "New device", "Plant", "100", { key: ["Key taken."] }, "/api/v1/devices/"],
  ] as const)(
    "after a 400 on another field, the changed parent choice stays (%s)",
    async (button, formName, parentLabel, newParent, errors, path) => {
      const structureApi = fakeStructureApi();
      const api = fakeApi(manager, structureApi.handler);
      renderApp("/");
      await openTree();

      fireEvent.click(screen.getByRole("button", { name: button }));
      const current = form(formName);
      if (formName === "New device") {
        type(current, "Key", "test-new-3");
        type(current, "Name", "Test device three");
      }
      fireEvent.change(within(current).getByLabelText(parentLabel), { target: { value: newParent } });
      structureApi.rejectNextWrite(400, errors);
      fireEvent.click(within(current).getByRole("button", { name: "Save" }));

      expect(await within(form(formName)).findByTestId("form-invalid")).toBeDefined();
      expect(within(form(formName)).getByLabelText<HTMLSelectElement>(parentLabel).value).toBe(newParent);

      // Saving again sends the changed parent, not the old one.
      fireEvent.click(within(form(formName)).getByRole("button", { name: "Save" }));
      await waitFor(() => {
        expect(screen.queryByRole("form", { name: formName })).toBeNull();
      });
      const writes = api.requestsTo(path).filter((request) => request.method !== "GET");
      expect(writes).toHaveLength(2);
      const parentField = parentLabel.toLowerCase();
      for (const write of writes) {
        expect(((await write.clone().json()) as Record<string, unknown>)[parentField]).toBe(Number(newParent));
      }
    },
  );

  it("shows errors that belong to no field above the fields", async () => {
    const structureApi = fakeStructureApi();
    fakeApi(manager, structureApi.handler);
    renderApp("/");
    await openTree();

    fireEvent.click(screen.getByRole("button", { name: "Edit site Test site A" }));
    structureApi.rejectNextWrite(400, { non_field_errors: ["The entry contradicts itself."] });
    fireEvent.click(within(form("Edit site")).getByRole("button", { name: "Save" }));

    const alert = await screen.findByTestId("form-invalid");
    expect(alert.textContent).toContain("The entry contradicts itself.");
  });

  it("shows 'no permission' if the API refuses the write", async () => {
    const structureApi = fakeStructureApi();
    fakeApi(manager, structureApi.handler);
    renderApp("/");
    await openTree();

    fireEvent.click(screen.getByRole("button", { name: "New site" }));
    type(form("New site"), "Name", "Test site D");
    structureApi.rejectNextWrite(403, { detail: "You do not have permission to perform this action." });
    fireEvent.click(within(form("New site")).getByRole("button", { name: "Save" }));

    expect((await within(form("New site")).findByTestId("error-summary")).textContent).toBe(
      "You do not have permission for this page or action.",
    );
  });

  it("Cancel closes the form without sending anything", async () => {
    const api = fakeApi(manager, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    fireEvent.click(screen.getByRole("button", { name: "Edit plant Test plant one" }));
    fireEvent.click(within(form("Edit plant")).getByRole("button", { name: "Cancel" }));

    expect(screen.queryByRole("form", { name: "Edit plant" })).toBeNull();
    expect(api.fetch.mock.calls.some(([request]) => request.method !== "GET")).toBe(false);
  });

  it("shows the forms in German with translated field names", async () => {
    await changeLanguage("de");
    fakeApi(manager, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    fireEvent.click(screen.getByRole("button", { name: "Neues Gerät in Test plant one" }));
    const deviceForm = form("Neues Gerät");
    for (const label of [
      "Anlage",
      "Kennung",
      "Name",
      "Hersteller",
      "Modell",
      "Softwarestand",
      "IP-Adresse",
      "Herkunft der Adresse",
      "Protokolle",
      "Notizen",
    ]) {
      expect(within(deviceForm).getByLabelText(label)).toBeDefined();
    }
    expect(within(deviceForm).getByRole("button", { name: "Speichern" })).toBeDefined();
  });
});
