import { act, cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Me } from "../api/generated";
import { changeLanguage } from "../i18n.ts";
import { fakeStructureApi } from "../pages/structure/testData.ts";
import { jsonResponse, manager, reader } from "../test/fakeApi.ts";
import { renderApp } from "../test/renderApp.tsx";
import {
  fakeChecksum,
  type FakeFilesApi,
  fakeFilesApi,
  fakeUploadApi as fakeApi,
  ingestJob,
  textFile,
} from "./files/testData.ts";

afterEach(async () => {
  vi.useRealTimers();
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  await changeLanguage("en");
  window.localStorage.clear();
});

/** Opens the page of device 1000 (two files) or another device, with the fake structure and file API. */
async function openDevice(
  user: Me,
  deviceId = 1000,
  prepare: (files: FakeFilesApi) => void = () => undefined,
): Promise<{ files: FakeFilesApi; api: ReturnType<typeof fakeApi> }> {
  const files = fakeFilesApi(fakeStructureApi().handler);
  prepare(files);
  const api = fakeApi(user, files.handler);
  renderApp(`/devices/${String(deviceId)}`);
  await screen.findByTestId("device-files");
  return { files, api };
}

function filesArea(): HTMLElement {
  return screen.getByTestId("device-files");
}

function rows(): HTMLElement[] {
  return within(filesArea()).getAllByTestId("device-file");
}

function cell(row: HTMLElement, name: string): string | null {
  return within(row).getByTestId(name).textContent;
}

function uploadForm(): HTMLElement {
  return within(filesArea()).getByRole("form", { name: "Upload a new file" });
}

function chooseFile(form: HTMLElement, file: File): void {
  fireEvent.change(within(form).getByLabelText("File"), { target: { files: [file] } });
}

function testFile(content: string, name = "test-upload.txt"): File {
  return textFile(content, name);
}

describe("list of files", () => {
  it("shows each file with its newest version", async () => {
    await openDevice(reader);

    await waitFor(() => {
      expect(rows()).toHaveLength(2);
    });
    const [manual, notes] = rows();
    if (manual === undefined || notes === undefined) {
      throw new Error("rows missing");
    }
    expect(within(filesArea()).getByRole("heading", { level: 2 }).textContent).toBe("Files");
    expect(within(manual).getByRole("link", { name: "Test manual" }).getAttribute("href")).toBe("/documents/7");
    expect(cell(manual, "file-kind")).toBe("Document");
    expect(cell(manual, "file-version")).toBe("2");
    expect(within(manual).getByTestId("file-date").querySelector("time")?.getAttribute("dateTime")).toBe(
      "2026-11-21T09:30:00Z",
    );
    expect(cell(manual, "file-size")?.replace(/\s/gu, " ")).toBe("2.5 MB");
    expect(cell(manual, "file-user")).toBe("System");
    expect(cell(notes, "file-user")).toBe("test-manager");
    expect(cell(notes, "file-size")?.replace(/\s/gu, " ")).toBe("512 byte");

    const link = within(manual).getByRole("link", { name: "Download version 2" });
    expect(link.getAttribute("href")).toBe("/api/v1/document-versions/71/download/");
    expect(link.textContent).toBe("Download");
  });

  it("shows the checksum shortened and in full when expanded", async () => {
    await openDevice(reader);
    await waitFor(() => {
      expect(rows()).toHaveLength(2);
    });
    const sha = fakeChecksum("content 71");
    const [manual] = rows();
    if (manual === undefined) {
      throw new Error("row missing");
    }

    const checksum = within(manual).getByTestId("checksum");
    expect(within(checksum).getByTestId("checksum-short").textContent).toBe(`${sha.slice(0, 12)}…`);
    expect(checksum.hasAttribute("open")).toBe(false);
    fireEvent.click(within(checksum).getByTestId("checksum-short"));
    expect(checksum.hasAttribute("open")).toBe(true);
    expect(within(checksum).getByTestId("checksum-full").textContent).toBe(sha);
  });

  it("says so when the device has no files", async () => {
    await openDevice(reader, 1001);

    expect((await within(filesArea()).findByTestId("device-files-empty")).textContent).toBe(
      "This device has no files yet.",
    );
  });

  it("renders titles and user names as text", async () => {
    const files = fakeFilesApi(fakeStructureApi().handler);
    const first = files.documents[0];
    if (first === undefined) {
      throw new Error("no sample document");
    }
    first.title = '<img src="x" data-testid="injected">Test';
    fakeApi(reader, files.handler);
    renderApp("/devices/1000");

    expect(await within(await screen.findByTestId("device-files")).findByText('<img src="x" data-testid="injected">Test')).toBeDefined();
    expect(screen.queryByTestId("injected")).toBeNull();
  });

  it("shows an error of the API inside the files area", async () => {
    const structure = fakeStructureApi();
    fakeApi(reader, (request) =>
      new URL(request.url).pathname.endsWith("/documents/")
        ? jsonResponse({ detail: "Server trouble." }, 500)
        : structure.handler(request),
    );
    renderApp("/devices/1000");

    expect((await within(await screen.findByTestId("device-files")).findByTestId("error-summary")).textContent).toBe(
      "The API answered with HTTP status 500.",
    );
  });

  it("shows the texts in German", async () => {
    await changeLanguage("de");
    await openDevice(manager);
    await waitFor(() => {
      expect(rows()).toHaveLength(2);
    });

    expect(within(filesArea()).getByRole("heading", { level: 2 }).textContent).toBe("Dateien");
    expect(within(filesArea()).getAllByRole("columnheader").map((header) => header.textContent)).toEqual([
      "Titel",
      "Art",
      "Version",
      "Hochgeladen",
      "Größe",
      "Benutzer",
      "Prüfsumme (SHA-256)",
      "Herunterladen",
      "Einlesen",
    ]);
    const [manual] = rows();
    expect(manual === undefined ? null : cell(manual, "file-size")?.replace(/\s/gu, " ")).toBe("2,5 MB");
    expect(within(filesArea()).getByRole("form", { name: "Neue Datei hochladen" })).toBeDefined();
    expect(within(filesArea()).getByRole("link", { name: "Version 2 herunterladen" })).toBeDefined();
  });
});

describe("ingestion state of the newest version", () => {
  it("shows a small badge per file: the newest version's state without counts or messages", async () => {
    await openDevice(reader, 1000, (files) => {
      const [oldManual, newManual] = files.documents[0]?.versions ?? [];
      const notes = files.documents[1]?.versions[0];
      if (oldManual === undefined || newManual === undefined || notes === undefined) {
        throw new Error("sample versions missing");
      }
      // Only the newest version counts (version 2 of the manual).
      oldManual.ingest = ingestJob("failed", { error_code: "internal" });
      newManual.ingest = ingestJob("done");
      notes.ingest = ingestJob("skipped", { error_code: "unsupported_format", error_detail: "x" });
    });

    await waitFor(() => {
      expect(rows()).toHaveLength(2);
    });
    const [manual, notes] = rows();
    if (manual === undefined || notes === undefined) {
      throw new Error("rows missing");
    }
    expect(within(filesArea()).getByRole("columnheader", { name: "Ingestion" })).toBeDefined();
    expect(cell(manual, "file-ingest")).toBe("Ingested");
    expect(cell(notes, "file-ingest")).toBe("Skipped");
    expect(within(filesArea()).queryByTestId("ingest-counts")).toBeNull();
    expect(within(filesArea()).queryByTestId("ingest-error")).toBeNull();
    expect(within(filesArea()).queryByTestId("ingest-retry")).toBeNull();
  });

  it("shows a file without any job as not ingested, in German as well", async () => {
    await changeLanguage("de");
    await openDevice(manager);

    await waitFor(() => {
      expect(rows()).toHaveLength(2);
    });
    expect(rows().map((row) => cell(row, "file-ingest"))).toEqual(["Nicht eingelesen", "Nicht eingelesen"]);
    expect(within(filesArea()).getByRole("columnheader", { name: "Einlesen" })).toBeDefined();
  });

  it("asks again every 5 seconds only while a newest version is queued or running", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { files, api } = await openDevice(reader, 1000, (served) => {
      const notes = served.documents[1]?.versions[0];
      if (notes !== undefined) {
        notes.ingest = ingestJob("running");
      }
    });
    const path = "/api/v1/devices/1000/documents/";
    await waitFor(() => {
      expect(rows()).toHaveLength(2);
    });
    const first = api.requestsTo(path).length;

    const notes = files.documents[1]?.versions[0];
    if (notes === undefined) {
      throw new Error("sample version missing");
    }
    notes.ingest = ingestJob("done");
    await act(() => vi.advanceTimersByTimeAsync(5000));
    await waitFor(() => {
      expect(rows().map((row) => cell(row, "file-ingest"))).toEqual(["Not ingested", "Ingested"]);
    });
    const afterDone = api.requestsTo(path).length;
    expect(afterDone).toBe(first + 1);

    await act(() => vi.advanceTimersByTimeAsync(30_000));
    expect(api.requestsTo(path)).toHaveLength(afterDone);
  });
});

describe("visibility per role", () => {
  it("a reader sees the list but no upload form", async () => {
    await openDevice(reader);
    await waitFor(() => {
      expect(rows()).toHaveLength(2);
    });

    expect(within(filesArea()).queryByRole("form")).toBeNull();
    expect(within(filesArea()).queryByRole("button", { name: "Upload" })).toBeNull();
  });

  it("a manager sees the upload form with the hint on configurations", async () => {
    await openDevice(manager);
    const form = uploadForm();

    const kind = within(form).getByLabelText<HTMLSelectElement>("Kind");
    expect(kind.value).toBe("document");
    const configuration = within(kind).getByRole<HTMLOptionElement>("option", { name: "Configuration (not yet possible)" });
    expect(configuration.disabled).toBe(true);
    expect(within(form).getByTestId("upload-configuration-hint").textContent).toMatch(
      /^Configuration files are not accepted yet/,
    );
    expect(kind.getAttribute("aria-describedby")).toBeTruthy();
  });
});

describe("upload of a new file", () => {
  it("sends file, title and kind, then shows the new file in the list", async () => {
    const { files } = await openDevice(manager);
    await waitFor(() => {
      expect(rows()).toHaveLength(2);
    });
    const form = uploadForm();

    chooseFile(form, testFile("first content"));
    fireEvent.change(within(form).getByLabelText("Title"), { target: { value: "Test upload" } });
    fireEvent.click(within(form).getByRole("button", { name: "Upload" }));

    expect((await within(form).findByTestId("upload-success")).textContent).toBe("Uploaded as version 1.");
    await waitFor(() => {
      expect(rows()).toHaveLength(3);
    });
    expect(within(filesArea()).getByRole("link", { name: "Test upload" })).toBeDefined();
    const [sent] = files.uploads;
    expect(sent?.path).toBe("/api/v1/devices/1000/documents/");
    expect(sent?.form.get("file")).toEqual({ value: "first content", filename: "test-upload.txt" });
    expect(sent?.form.get("title")?.value).toBe("Test upload");
    expect(sent?.form.get("kind")?.value).toBe("document");
    // The fields are empty again.
    expect(within(form).getByLabelText<HTMLInputElement>("Title").value).toBe("");
  });

  it("names other places of the same content with links", async () => {
    const { files } = await openDevice(manager);
    files.duplicatesOfNextUpload([
      {
        device: 1003,
        device_key: "test-drive-1",
        device_name: "Test drive",
        document: 8,
        document_title: "Test notes",
        version: 80,
        version_number: 1,
      },
    ]);
    const form = uploadForm();

    chooseFile(form, testFile("shared content"));
    fireEvent.click(within(form).getByRole("button", { name: "Upload" }));

    const duplicates = await within(form).findByTestId("upload-duplicates");
    expect(within(duplicates).getByText("The same content is already stored elsewhere:")).toBeDefined();
    const [entry] = within(duplicates).getAllByTestId("upload-duplicate");
    expect(entry?.textContent).toBe("Test drive (test-drive-1): Test notes, version 1");
    expect(within(duplicates).getByRole("link", { name: "Test drive" }).getAttribute("href")).toBe("/devices/1003");
    expect(within(duplicates).getByRole("link", { name: "Test notes" }).getAttribute("href")).toBe("/documents/8");
  });

  it("shows the limit of a 413", async () => {
    const { files } = await openDevice(manager);
    files.rejectNextUpload(413, { detail: "The file is larger than the limit of 200000000 bytes." });
    const form = uploadForm();

    chooseFile(form, testFile("too large"));
    fireEvent.change(within(form).getByLabelText("Title"), { target: { value: "Test large" } });
    fireEvent.click(within(form).getByRole("button", { name: "Upload" }));

    expect((await within(form).findByTestId("upload-too-large")).textContent.replace(/\s/gu, " ")).toBe(
      "The file is larger than the limit of 200 MB.",
    );
    // The title stays for the next try.
    expect(within(form).getByLabelText<HTMLInputElement>("Title").value).toBe("Test large");
  });

  it("explains the rejection of a configuration file", async () => {
    const { files } = await openDevice(manager);
    files.rejectNextUpload(400, {
      kind: ["Configuration files are not accepted yet: credentials are only redacted from M5 on."],
    });
    const form = uploadForm();

    chooseFile(form, testFile("test configuration"));
    fireEvent.click(within(form).getByRole("button", { name: "Upload" }));

    const invalid = await within(form).findByTestId("upload-invalid");
    expect(within(invalid).getByTestId("upload-configuration-rejected").textContent).toBe(
      "Configuration files are not accepted yet (redaction of credentials follows in milestone M5).",
    );
    expect(within(form).getByTestId("upload-error-kind").textContent).toBe(
      "Configuration files are not accepted yet: credentials are only redacted from M5 on.",
    );
    expect(within(form).getByLabelText("Kind").getAttribute("aria-invalid")).toBe("true");
  });

  it("shows errors without a field above the fields", async () => {
    const { files } = await openDevice(manager);
    files.rejectNextUpload(400, { non_field_errors: ["Test message without field."] });
    const form = uploadForm();

    chooseFile(form, testFile("content"));
    fireEvent.click(within(form).getByRole("button", { name: "Upload" }));

    const invalid = await within(form).findByTestId("upload-invalid");
    expect(within(invalid).getByRole("list", { name: "Messages from the API" }).textContent).toBe(
      "Test message without field.",
    );
    expect(within(invalid).queryByTestId("upload-configuration-rejected")).toBeNull();
  });

  it("asks for a file before calling the API", async () => {
    const { files } = await openDevice(manager);
    const form = uploadForm();

    fireEvent.click(within(form).getByRole("button", { name: "Upload" }));

    expect((await within(form).findByTestId("upload-error-file")).textContent).toBe("Please choose a file.");
    expect(files.uploads).toHaveLength(0);
  });

  it("shows a 403 as missing permission", async () => {
    const { files } = await openDevice(manager);
    files.rejectNextUpload(403, { detail: "You do not have permission to perform this action." });
    const form = uploadForm();

    chooseFile(form, testFile("content"));
    fireEvent.click(within(form).getByRole("button", { name: "Upload" }));

    expect(await within(form).findByTestId("error-message")).toBeDefined();
    expect(within(form).getByTestId("error-detail").textContent).toBe(
      "You do not have permission to perform this action.",
    );
  });
});
