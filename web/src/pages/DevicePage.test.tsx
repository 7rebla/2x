import { cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { changeLanguage } from "../i18n.ts";
import { fakeApi, jsonResponse, manager, reader } from "../test/fakeApi.ts";
import { renderApp } from "../test/renderApp.tsx";
import { parseDeviceId } from "./DevicePage.tsx";
import { fakeStructureApi } from "./structure/testData.ts";

afterEach(async () => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  await changeLanguage("en");
  window.localStorage.clear();
});

async function deviceHeading(name: string): Promise<HTMLElement> {
  return screen.findByRole("heading", { level: 1, name });
}

function field(name: string): string | null {
  return screen.getByTestId(`device-${name}`).textContent;
}

describe("parseDeviceId", () => {
  it.each([
    ["1", 1],
    ["1000", 1000],
    ["9007199254740991", 9007199254740991],
  ])("accepts %s", (raw, id) => {
    expect(parseDeviceId(raw)).toBe(id);
  });

  it.each([undefined, "", "0", "01", "-1", "1.5", "plc-1", "1e3", "9007199254740993", "12345678901234567"])(
    "rejects %s",
    (raw) => {
      expect(parseDeviceId(raw)).toBeNull();
    },
  );
});

describe("device page", () => {
  it("shows every field, the chain as breadcrumb and the files area", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/devices/1000");
    await deviceHeading("Test controller");

    const breadcrumb = screen.getByRole("navigation", { name: "Location of the device" });
    expect(within(breadcrumb).getAllByRole("listitem").map((item) => item.textContent)).toEqual([
      "Structure",
      "Test site A",
      "Test area A1",
      "Test plant one (test-plant-1)",
      "Test controller",
    ]);
    expect(within(breadcrumb).getByRole("link", { name: "Structure" }).getAttribute("href")).toBe("/");
    expect(screen.getByTestId("breadcrumb-device").getAttribute("aria-current")).toBe("page");

    expect(field("site")).toBe("Test site A");
    expect(field("area")).toBe("Test area A1");
    expect(field("plant")).toBe("Test plant one (test-plant-1)");
    expect(field("key")).toBe("test-plc-1");
    expect(field("name")).toBe("Test controller");
    expect(field("device_class")).toBe("PLC");
    expect(field("manufacturer")).toBe("Test maker");
    expect(field("model")).toBe("Test model");
    expect(field("software_version")).toBe("1.0.0");
    expect(field("ip_address")).toBe("192.0.2.10");
    expect(field("protocols")).toBe("Test protocol");
    expect(screen.getByTestId("device-created_at").querySelector("time")?.getAttribute("dateTime")).toBe(
      "2026-11-21T10:00:00Z",
    );
    expect(field("updated_at")).toMatch(/2026/);

    expect(screen.getAllByRole("term").map((term) => term.textContent)).toEqual([
      "Site",
      "Area",
      "Plant",
      "Key",
      "Name",
      "Device class",
      "Manufacturer",
      "Model",
      "Software version",
      "IP address",
      "Source of the address",
      "Protocols",
      "Notes",
      "Created",
      "Last changed",
    ]);

    const files = screen.getByTestId("device-files");
    expect(within(files).getByRole("heading", { level: 2 }).textContent).toBe("Files");
    expect(files.getAttribute("data-device-id")).toBe("1000");
  });

  it("shows the icon of the device class in the heading and the breadcrumb, the class as text", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/devices/1000");
    await deviceHeading("Test controller");

    const iconOf = (element: HTMLElement): string | null | undefined =>
      element.querySelector("svg[aria-hidden='true']")?.getAttribute("data-icon");
    expect(iconOf(screen.getByTestId("device-heading"))).toBe("devicePlc");
    expect(iconOf(screen.getByTestId("breadcrumb-device"))).toBe("devicePlc");
    expect(iconOf(screen.getByTestId("breadcrumb-plant"))).toBe("plant");
    expect(field("device_class")).toBe("PLC");
    cleanup();

    // Class "other": the generic device icon, the class still written out.
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/devices/1002");
    await deviceHeading("Test remote I/O");
    expect(iconOf(screen.getByTestId("device-heading"))).toBe("device");
    expect(iconOf(screen.getByTestId("breadcrumb-device"))).toBe("device");
    expect(field("device_class")).toBe("Other");
  });

  it("shows long free texts in full and with their line breaks", async () => {
    const structureApi = fakeStructureApi();
    const longNote = `${"A long note without any break ".repeat(40)}\nand a second line`;
    structureApi.structure.devices = structureApi.structure.devices.map((item) =>
      item.id === 1000 ? { ...item, notes: longNote } : item,
    );
    fakeApi(reader, structureApi.handler);
    renderApp("/devices/1000");
    await deviceHeading("Test controller");

    const notes = screen.getByTestId("device-notes");
    expect(notes.textContent).toBe(longNote);
    expect(notes.className).toContain("whitespace-pre-wrap");
    expect(notes.className).toContain("break-words");
    const source = screen.getByTestId("device-address_source");
    expect(source.textContent).toBe("Line one of the source\nLine two of the source");
    expect(source.className).toContain("whitespace-pre-wrap");
  });

  it("marks empty fields", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/devices/1002");
    await deviceHeading("Test remote I/O");

    expect(field("ip_address")).toBe("–");
    expect(field("notes")).toBe("–");
  });

  it("shows the labels in German", async () => {
    await changeLanguage("de");
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/devices/1000");
    await deviceHeading("Test controller");

    for (const label of ["Standort", "Bereich", "Anlage", "Kennung", "Gerätetyp", "Softwarestand", "IP-Adresse", "Notizen"]) {
      expect(screen.getAllByRole("term").map((term) => term.textContent)).toContain(label);
    }
    expect(field("device_class")).toBe("SPS");
    expect(screen.getByRole("navigation", { name: "Ort des Geräts" })).toBeDefined();
    expect(within(screen.getByTestId("device-files")).getByRole("heading").textContent).toBe("Dateien");
  });

  it("a reader sees no edit button, a manager does", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/devices/1000");
    await deviceHeading("Test controller");
    expect(screen.queryByRole("button", { name: /Edit/ })).toBeNull();
    cleanup();

    fakeApi(manager, fakeStructureApi().handler);
    renderApp("/devices/1000");
    await deviceHeading("Test controller");
    expect(screen.getByRole("button", { name: "Edit device Test controller" })).toBeDefined();
  });

  it("links readers and managers to a question limited to the device", async () => {
    for (const user of [reader, manager]) {
      fakeApi(user, fakeStructureApi().handler);
      renderApp("/devices/1000");
      await deviceHeading("Test controller");
      const link = screen.getByRole("link", { name: "Ask a question about device Test controller" });
      expect(link.getAttribute("href")).toBe("/ask?device=1000");
      expect(link.getAttribute("data-testid")).toBe("device-ask");
      expect(link.textContent).toBe("Ask about this device");
      cleanup();
      vi.unstubAllGlobals();
    }
  });

  it("names the link to the question in German", async () => {
    await changeLanguage("de");
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/devices/1000");
    await deviceHeading("Test controller");
    const link = screen.getByTestId("device-ask");
    expect(link.getAttribute("aria-label")).toBe("Frage zu Gerät Test controller stellen");
    expect(link.textContent).toBe("Frage zu diesem Gerät");
  });

  it("opens the answer page limited to the device without sending a question", async () => {
    const api = fakeApi(reader, fakeStructureApi().handler);
    const { router } = renderApp("/devices/1000");
    await deviceHeading("Test controller");
    fireEvent.click(screen.getByTestId("device-ask"));
    await screen.findByTestId("answer-scope");
    expect(router.state.location.pathname).toBe("/ask");
    expect(router.state.location.search).toBe("?device=1000");
    expect(api.requestsTo("/api/v1/answers/")).toHaveLength(0);
  });

  it("edits the device and shows the new value after reloading", async () => {
    const api = fakeApi(manager, fakeStructureApi().handler);
    renderApp("/devices/1000");
    await deviceHeading("Test controller");

    fireEvent.click(screen.getByRole("button", { name: "Edit device Test controller" }));
    const deviceForm = await screen.findByRole("form", { name: "Edit device" });
    expect(within(deviceForm).getByLabelText<HTMLInputElement>("Software version").value).toBe("1.0.0");
    expect(within(deviceForm).getByLabelText<HTMLTextAreaElement>("Notes").value).toBe(
      "First line of the notes\nSecond line of the notes",
    );
    expect(within(deviceForm).getByLabelText<HTMLSelectElement>("Plant").value).toBe("100");
    fireEvent.change(within(deviceForm).getByLabelText("Software version"), { target: { value: "2.0.0" } });
    fireEvent.click(within(deviceForm).getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(field("software_version")).toBe("2.0.0");
    });
    expect(screen.queryByRole("form", { name: "Edit device" })).toBeNull();
    const put = api.requestsTo("/api/v1/devices/1000/").find((request) => request.method === "PUT");
    expect(await put?.clone().json()).toEqual({
      plant: 100,
      key: "test-plc-1",
      name: "Test controller",
      device_class: "plc",
      manufacturer: "Test maker",
      model: "Test model",
      software_version: "2.0.0",
      ip_address: "192.0.2.10",
      address_source: "Line one of the source\nLine two of the source",
      protocols: "Test protocol",
      notes: "First line of the notes\nSecond line of the notes",
    });
    expect(api.requestsTo("/api/v1/devices/1000/").filter((request) => request.method === "GET")).toHaveLength(2);
  });

  it("shows the stored device class in the form and sends a changed one", async () => {
    const api = fakeApi(manager, fakeStructureApi().handler);
    renderApp("/devices/1000");
    await deviceHeading("Test controller");

    fireEvent.click(screen.getByRole("button", { name: "Edit device Test controller" }));
    const deviceForm = await screen.findByRole("form", { name: "Edit device" });
    const select = within(deviceForm).getByLabelText<HTMLSelectElement>("Device class");
    expect(select.value).toBe("plc");
    fireEvent.change(select, { target: { value: "router" } });
    fireEvent.click(within(deviceForm).getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(screen.queryByRole("form", { name: "Edit device" })).toBeNull();
    });
    const put = api.requestsTo("/api/v1/devices/1000/").find((request) => request.method === "PUT");
    expect(((await put?.clone().json()) as { device_class: unknown }).device_class).toBe("router");
  });

  it("an empty IP address is sent as null", async () => {
    const api = fakeApi(manager, fakeStructureApi().handler);
    renderApp("/devices/1001");
    await deviceHeading("Test panel");

    fireEvent.click(screen.getByRole("button", { name: "Edit device Test panel" }));
    const deviceForm = await screen.findByRole("form", { name: "Edit device" });
    fireEvent.change(within(deviceForm).getByLabelText("IP address"), { target: { value: "  " } });
    fireEvent.click(within(deviceForm).getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(field("ip_address")).toBe("–");
    });
    const put = api.requestsTo("/api/v1/devices/1001/").find((request) => request.method === "PUT");
    expect(((await put?.clone().json()) as { ip_address: unknown }).ip_address).toBeNull();
  });

  it("shows an invalid IP address as error at the field", async () => {
    const structureApi = fakeStructureApi();
    fakeApi(manager, structureApi.handler);
    renderApp("/devices/1000");
    await deviceHeading("Test controller");

    fireEvent.click(screen.getByRole("button", { name: "Edit device Test controller" }));
    const deviceForm = await screen.findByRole("form", { name: "Edit device" });
    fireEvent.change(within(deviceForm).getByLabelText("IP address"), { target: { value: "not-an-address" } });
    structureApi.rejectNextWrite(400, { ip_address: ["Enter a valid IPv4 or IPv6 address."] });
    fireEvent.click(within(deviceForm).getByRole("button", { name: "Save" }));

    expect((await within(deviceForm).findByTestId("field-error-ip_address")).textContent).toBe(
      "Enter a valid IPv4 or IPv6 address.",
    );
    expect(within(deviceForm).getByLabelText<HTMLInputElement>("IP address").value).toBe("not-an-address");
    // The page still shows the saved value.
    expect(field("ip_address")).toBe("192.0.2.10");
  });

  it("an unknown device shows NotFound", async () => {
    fakeApi(reader, fakeStructureApi().handler);
    renderApp("/devices/999");

    expect(await screen.findByTestId("not-found")).toBeDefined();
  });

  it("an address that cannot be a device id shows NotFound without asking the API", async () => {
    const api = fakeApi(reader, fakeStructureApi().handler);
    renderApp("/devices/plc-1");

    expect(await screen.findByTestId("not-found")).toBeDefined();
    expect(api.fetch.mock.calls.some(([request]) => request.url.includes("/api/v1/devices/"))).toBe(false);
  });

  it("shows other errors of the API under the page heading", async () => {
    fakeApi(reader, () => jsonResponse({ detail: "Server trouble." }, 500));
    renderApp("/devices/1000");

    expect((await screen.findByTestId("error-summary")).textContent).toBe("The API answered with HTTP status 500.");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Device");
  });
});
