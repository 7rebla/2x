import { cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ImportCounts, ImportReport, ImportRowError } from "../api/generated";
import { changeLanguage } from "../i18n.ts";
import { fakeApi, type Handler, jsonResponse, manager, reader } from "../test/fakeApi.ts";
import { renderApp } from "../test/renderApp.tsx";
import { deviceListColumns } from "./ImportPage.tsx";

const IMPORT_PATH = "/api/v1/imports/devices/";

/**
 * Under jsdom, File and Blob come from jsdom, but Request and FormData from
 * Node's fetch, which sends a jsdom File without its content (a browser has
 * one set of classes). The tests therefore read the file the page hands to
 * FormData.append, and the other fields from the multipart body itself.
 */
function watchFormFields(): () => ReadonlyMap<string, unknown> {
  const append = vi.spyOn(FormData.prototype, "append");
  let seen = 0;
  return () => {
    const calls = append.mock.calls.slice(seen);
    seen = append.mock.calls.length;
    return new Map(calls.map(([name, value]) => [name, value] as const));
  };
}
/** Reads one form field of a multipart body (enough for the small forms of these tests). */
function formField(body: string, name: string): string | null {
  for (const part of body.split(/\r\n--[^\r\n]*/)) {
    const separator = part.indexOf("\r\n\r\n");
    if (separator !== -1 && part.slice(0, separator).includes(`name="${name}"`)) {
      return part.slice(separator + 4);
    }
  }
  return null;
}

beforeEach(() => {
  document.cookie = "csrftoken=test-csrf-token; path=/";
});

afterEach(async () => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  document.cookie = "csrftoken=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  await changeLanguage("en");
  window.localStorage.clear();
});

function counts(created: number, updated = 0, unchanged = 0): ImportCounts {
  return { created, updated, unchanged };
}

const zero = counts(0);

/** A report as the API sends it; by default a dry run that would create one of each and two devices. */
function report(overrides: Partial<ImportReport> = {}): ImportReport {
  return {
    dry_run: true,
    saved: false,
    rows: 2,
    sites: counts(1),
    areas: counts(1),
    plants: counts(1),
    devices: counts(2),
    errors: [],
    ...overrides,
  };
}

function failedReport(errors: ImportRowError[], dryRun = true): ImportReport {
  return report({ dry_run: dryRun, sites: zero, areas: zero, plants: zero, devices: zero, errors });
}

const CSV = `${deviceListColumns.join(",")}\nTest site,Test area,test-plant-1,Test plant,test-plc-1,Test controller,,,,192.0.2.10,,,\n`;

function csvFile(content = CSV, name = "devices.csv"): File {
  return new File([content], name, { type: "text/csv" });
}

interface SentForm {
  readonly dryRun: string | null;
  /** What the page handed to FormData.append as the field "file". */
  readonly file: unknown;
  readonly contentType: string | null;
  readonly csrf: string | null;
}

/** Fake of the import endpoint: answers the calls in order with `answers`, records what was sent. */
function fakeImport(...answers: (() => Response)[]): { handler: Handler; sent: SentForm[] } {
  const sent: SentForm[] = [];
  const appendedFields = watchFormFields();
  const handler: Handler = async (request) => {
    const path = new URL(request.url).pathname;
    if (path !== IMPORT_PATH || request.method !== "POST") {
      return jsonResponse([]);
    }
    const body = await request.text();
    sent.push({
      dryRun: formField(body, "dry_run"),
      file: appendedFields().get("file"),
      contentType: request.headers.get("Content-Type"),
      csrf: request.headers.get("X-CSRFToken"),
    });
    const answer = answers[sent.length - 1];
    if (answer === undefined) {
      throw new Error(`unexpected call ${String(sent.length)} to the import endpoint`);
    }
    return answer();
  };
  return { handler, sent };
}

async function openPage(): Promise<void> {
  await screen.findByTestId("import-form");
}

function chooseFile(file: File = csvFile()): void {
  fireEvent.change(screen.getByLabelText("CSV file"), { target: { files: [file] } });
}

function count(level: string, kind: string): string | null {
  return screen.getByTestId(`import-count-${level}-${kind}`).textContent;
}

describe("import page", () => {
  it("describes the 13 columns and starts the dry run only with a file", async () => {
    fakeApi(manager, fakeImport().handler);
    renderApp("/import");
    await openPage();

    expect(screen.getByRole("heading", { level: 2 }).textContent).toBe("Import");
    expect(deviceListColumns).toHaveLength(13);
    expect(screen.getByTestId("import-columns").textContent).toBe(
      "site,area,plant_id,plant_name,device_id,device_name,manufacturer,model,software_version,ip_address,address_source,protocols,notes",
    );
    const checkButton = screen.getByRole("button", { name: "Start dry run" });
    expect(checkButton).toHaveProperty("disabled", true);
    expect(screen.queryByRole("button", { name: "Apply" })).toBeNull();

    chooseFile();
    expect(checkButton).toHaveProperty("disabled", false);
  });

  it("runs the dry run, shows the counts, then applies the same file", async () => {
    const saved = report({ dry_run: false, saved: true });
    const api = fakeImport(
      () => jsonResponse(report({ sites: counts(0, 0, 1), plants: counts(1, 1, 0) })),
      () => jsonResponse(saved),
    );
    const fake = fakeApi(manager, api.handler);
    renderApp("/import");
    await openPage();
    const file = csvFile();
    chooseFile(file);

    fireEvent.click(screen.getByRole("button", { name: "Start dry run" }));

    expect((await screen.findByTestId("import-summary")).textContent).toBe(
      "Dry run: nothing has been saved yet. 2 rows read.",
    );
    expect(api.sent).toHaveLength(1);
    expect(api.sent[0]?.dryRun).toBe("true");
    expect(api.sent[0]?.csrf).toBe("test-csrf-token");
    expect(api.sent[0]?.contentType).toMatch(/^multipart\/form-data; boundary=/);
    expect(api.sent[0]?.file).toBe(file);

    expect(count("sites", "created")).toBe("0");
    expect(count("sites", "unchanged")).toBe("1");
    expect(count("areas", "created")).toBe("1");
    expect(count("plants", "created")).toBe("1");
    expect(count("plants", "updated")).toBe("1");
    expect(count("devices", "created")).toBe("2");
    expect(count("devices", "updated")).toBe("0");
    expect(screen.getByTestId("import-next").textContent).toContain("Apply");
    expect(screen.queryByTestId("import-errors")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Apply" }));

    expect(
      await screen.findByText("Saved. 2 rows imported.", { selector: "[data-testid=import-summary]" }),
    ).toBeDefined();
    expect(api.sent).toHaveLength(2);
    expect(api.sent[1]?.dryRun).toBe("false");
    expect(api.sent[1]?.csrf).toBe("test-csrf-token");
    expect(api.sent[1]?.file).toBe(file);
    expect(fake.requestsTo(IMPORT_PATH).map((request) => request.method)).toEqual(["POST", "POST"]);
    expect(count("devices", "created")).toBe("2");
    expect(screen.queryByRole("button", { name: "Apply" })).toBeNull();
    expect(screen.getByRole("link", { name: "Show the structure" }).getAttribute("href")).toBe("/");
  });

  it("shows every error with line, column and message, as text, and offers no apply", async () => {
    const api = fakeImport(() =>
      jsonResponse(
        failedReport([
          { line: 3, column: "ip_address", message: "Enter a valid IPv4 or IPv6 address." },
          { line: 4, column: null, message: "<b>Expected 13 fields</b>, found 12." },
          { line: null, column: null, message: "The file ends inside a quoted value." },
        ]),
      ),
    );
    fakeApi(manager, api.handler);
    renderApp("/import");
    await openPage();
    chooseFile();

    fireEvent.click(screen.getByRole("button", { name: "Start dry run" }));

    const table = await screen.findByTestId("import-errors");
    expect(screen.getByTestId("import-summary").textContent).toBe("The file has 3 errors. Nothing has been saved.");
    const rows = within(table).getAllByTestId("import-error");
    expect(
      rows.map((row) => [
        within(row).getByTestId("import-error-line").textContent,
        within(row).getByTestId("import-error-column").textContent,
        within(row).getByTestId("import-error-message").textContent,
      ]),
    ).toEqual([
      ["3", "ip_address", "Enter a valid IPv4 or IPv6 address."],
      ["4", "–", "<b>Expected 13 fields</b>, found 12."],
      ["whole file", "–", "The file ends inside a quoted value."],
    ]);
    // The message is data: no markup from it reaches the page.
    expect(table.querySelector("b")).toBeNull();
    expect(screen.queryByTestId("import-counts")).toBeNull();
    expect(screen.queryByRole("button", { name: "Apply" })).toBeNull();
    expect(screen.getByTestId("import-next").textContent).toBe("Correct the file and start the dry run again.");
  });

  it("a single error reads in the singular", async () => {
    const api = fakeImport(() =>
      jsonResponse(failedReport([{ line: 2, column: "device_id", message: "Duplicate device_id." }])),
    );
    fakeApi(manager, api.handler);
    renderApp("/import");
    await openPage();
    chooseFile();
    fireEvent.click(screen.getByRole("button", { name: "Start dry run" }));

    expect((await screen.findByTestId("import-summary")).textContent).toBe(
      "The file has 1 error. Nothing has been saved.",
    );
  });

  it("errors found while applying are shown and nothing is offered to apply", async () => {
    const api = fakeImport(
      () => jsonResponse(report()),
      () => jsonResponse(failedReport([{ line: 2, column: "device_id", message: "Already taken." }], false)),
    );
    fakeApi(manager, api.handler);
    renderApp("/import");
    await openPage();
    chooseFile();
    fireEvent.click(screen.getByRole("button", { name: "Start dry run" }));
    fireEvent.click(await screen.findByRole("button", { name: "Apply" }));

    expect((await screen.findByTestId("import-errors")).textContent).toContain("Already taken.");
    expect(screen.getByTestId("import-summary").textContent).toBe("The file has 1 error. Nothing has been saved.");
    expect(screen.queryByRole("button", { name: "Apply" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Show the structure" })).toBeNull();
  });

  it("choosing another file drops the report of the previous one", async () => {
    const api = fakeImport(() => jsonResponse(report()));
    fakeApi(manager, api.handler);
    renderApp("/import");
    await openPage();
    chooseFile();
    fireEvent.click(screen.getByRole("button", { name: "Start dry run" }));
    await screen.findByRole("button", { name: "Apply" });

    chooseFile(csvFile(CSV, "other.csv"));

    expect(screen.queryByTestId("import-report")).toBeNull();
    expect(screen.queryByRole("button", { name: "Apply" })).toBeNull();
  });

  it("413 names the upload limit from the API", async () => {
    const api = fakeImport(() =>
      jsonResponse({ detail: "The file is larger than the limit of 1000 bytes." }, 413),
    );
    fakeApi(manager, api.handler);
    renderApp("/import");
    await openPage();
    chooseFile();
    fireEvent.click(screen.getByRole("button", { name: "Start dry run" }));

    const problem = await screen.findByTestId("import-too-large");
    expect(problem.getAttribute("role")).toBe("alert");
    expect(problem.textContent).toContain("The file is larger than the server accepts.");
    expect(screen.getByTestId("import-too-large-detail").textContent).toBe(
      "The file is larger than the limit of 1000 bytes.",
    );
    expect(screen.queryByRole("button", { name: "Apply" })).toBeNull();
  });

  it("400 shows the messages of the API", async () => {
    const api = fakeImport(() => jsonResponse({ file: ["The submitted file is empty."] }, 400));
    fakeApi(manager, api.handler);
    renderApp("/import");
    await openPage();
    chooseFile(csvFile(""));
    fireEvent.click(screen.getByRole("button", { name: "Start dry run" }));

    const problem = await screen.findByTestId("import-invalid");
    expect(problem.textContent).toContain("The server did not accept the upload.");
    expect(screen.getAllByTestId("import-invalid-message").map((item) => item.textContent)).toEqual([
      "The submitted file is empty.",
    ]);
  });

  it("other failures show the general error message", async () => {
    const api = fakeImport(() => new Response("oops", { status: 500, headers: { "Content-Type": "text/html" } }));
    fakeApi(manager, api.handler);
    renderApp("/import");
    await openPage();
    chooseFile();
    fireEvent.click(screen.getByRole("button", { name: "Start dry run" }));

    expect((await screen.findByTestId("error-summary")).textContent).toBe("The API answered with HTTP status 500.");
    // The button can be used again.
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Start dry run" })).toHaveProperty("disabled", false);
    });
  });

  it("shows the texts in German", async () => {
    await changeLanguage("de");
    const api = fakeImport(
      () => jsonResponse(report()),
      () => jsonResponse(report({ dry_run: false, saved: true })),
    );
    fakeApi(manager, api.handler);
    renderApp("/import");
    await openPage();

    expect(screen.getByRole("heading", { level: 3, name: "Erwartetes Format" })).toBeDefined();
    fireEvent.change(screen.getByLabelText("CSV-Datei"), { target: { files: [csvFile()] } });
    fireEvent.click(screen.getByRole("button", { name: "Probelauf starten" }));

    expect((await screen.findByTestId("import-summary")).textContent).toBe(
      "Probelauf: Noch nichts gespeichert. 2 Zeilen gelesen.",
    );
    expect(screen.getByRole("columnheader", { name: "Angelegt" })).toBeDefined();
    expect(screen.getByRole("rowheader", { name: "Geräte" })).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Übernehmen" }));
    expect(
      await screen.findByText("Gespeichert. 2 Zeilen übernommen.", { selector: "[data-testid=import-summary]" }),
    ).toBeDefined();
    expect(screen.getByRole("link", { name: "Zur Struktur" })).toBeDefined();
  });
});

describe("import page and roles", () => {
  it("a reader sees a notice instead of the form and sends nothing", async () => {
    const api = fakeImport();
    const fake = fakeApi(reader, api.handler);
    renderApp("/import");

    expect(await screen.findByTestId("no-permission")).toBeDefined();
    expect(screen.queryByTestId("import-form")).toBeNull();
    expect(screen.queryByLabelText("CSV file")).toBeNull();
    expect(fake.requestsTo(IMPORT_PATH)).toHaveLength(0);
  });

  it("a manager sees the form", async () => {
    fakeApi(manager, fakeImport().handler);
    renderApp("/import");

    expect(await screen.findByTestId("import-form")).toBeDefined();
    expect(screen.queryByTestId("no-permission")).toBeNull();
  });
});
