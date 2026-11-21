import { cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { changeLanguage } from "../i18n.ts";
import { fakeApi, jsonResponse, manager, reader } from "../test/fakeApi.ts";
import { renderApp } from "../test/renderApp.tsx";
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

  it("shows the texts in German", async () => {
    await changeLanguage("de");
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    expect(screen.getByRole("heading", { level: 2 }).textContent).toBe("Struktur");
    expect(countOf(itemNamed("site-item", "Test site A"))).toBe("4 Geräte");
    expect(countOf(itemNamed("area-item", "Test area A2"))).toBe("1 Gerät");
    expect(screen.getByLabelText("Suche")).toBeDefined();
    expect(screen.getAllByText("Standort")).toHaveLength(2);
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

describe("buttons per role", () => {
  it("a reader sees no button to create or edit", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/");
    await openTree();

    expect(screen.queryByRole("button", { name: "New site" })).toBeNull();
    expect(screen.queryByRole("button", { name: /^Edit/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /^New/ })).toBeNull();
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
      manufacturer: "",
      model: "",
      software_version: "",
      ip_address: "192.0.2.30",
      address_source: "",
      protocols: "",
      notes: "",
    });
  });

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
