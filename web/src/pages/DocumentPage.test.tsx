import { cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Me } from "../api/generated";
import { fakeChecksum, type FakeFilesApi, fakeFilesApi, fakeUploadApi as fakeApi, textFile } from "../components/files/testData.ts";
import { changeLanguage } from "../i18n.ts";
import { type FakeApi, jsonResponse, manager, reader } from "../test/fakeApi.ts";
import { renderApp } from "../test/renderApp.tsx";
import { fakeStructureApi } from "./structure/testData.ts";

afterEach(async () => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  await changeLanguage("en");
  window.localStorage.clear();
});

const AUDIT_PATH = "/api/v1/audit-log/";

/** Fake structure, file and change log API; the change log is empty. */
function serve(user: Me): { files: FakeFilesApi; api: FakeApi } {
  const files = fakeFilesApi(fakeStructureApi().handler);
  const api = fakeApi(user, (request) =>
    new URL(request.url).pathname === AUDIT_PATH
      ? jsonResponse({ count: 0, next: null, previous: null, results: [] })
      : files.handler(request),
  );
  return { files, api };
}

async function openDocument(user: Me, documentId = 7): Promise<{ files: FakeFilesApi; api: FakeApi }> {
  const served = serve(user);
  renderApp(`/documents/${String(documentId)}`);
  await screen.findByTestId("document-title");
  return served;
}

function versionRows(): HTMLElement[] {
  return within(screen.getByTestId("document-versions")).getAllByTestId("document-version");
}

function versionForm(): HTMLElement {
  return screen.getByRole("form", { name: "Upload a new version" });
}

function upload(form: HTMLElement, content: string, name = "test-version.txt"): void {
  fireEvent.change(within(form).getByLabelText("File"), { target: { files: [textFile(content, name)] } });
  fireEvent.click(within(form).getByRole("button", { name: "Upload" }));
}

describe("file page", () => {
  it("shows the file and all versions, newest first, with download links", async () => {
    await openDocument(reader);

    expect(screen.getByRole("heading", { level: 2 }).textContent).toBe("Test manual");
    expect(screen.getByTestId("document-kind").textContent).toBe("Document");
    expect(screen.getByTestId("document-created-by").textContent).toBe("test-manager");
    const device = within(screen.getByTestId("document-device")).getByRole("link");
    expect(device.getAttribute("href")).toBe("/devices/1000");
    await waitFor(() => {
      expect(device.textContent).toBe("Test controller (test-plc-1)");
    });

    const rows = versionRows();
    expect(rows.map((row) => within(row).getByTestId("version-number").textContent)).toEqual(["2", "1"]);
    const [second, first] = rows;
    if (second === undefined || first === undefined) {
      throw new Error("rows missing");
    }
    expect(within(second).getByTestId("version-user").textContent).toBe("System");
    expect(within(first).getByTestId("version-user").textContent).toBe("test-manager");
    expect(within(first).getByTestId("version-filename").textContent).toBe("test-file-1.txt");
    expect(within(first).getByTestId("version-size").textContent.replace(/\s/gu, " ")).toBe("1.5 MB");
    expect(within(first).getByTestId("checksum-full").textContent).toBe(fakeChecksum("content 70"));
    expect(within(first).getByRole("link", { name: "Download version 1" }).getAttribute("href")).toBe(
      "/api/v1/document-versions/70/download/",
    );
    expect(within(second).getByRole("link", { name: "Download version 2" }).getAttribute("href")).toBe(
      "/api/v1/document-versions/71/download/",
    );
  });

  it("an unknown file shows NotFound", async () => {
    serve(reader);
    renderApp("/documents/999");

    expect(await screen.findByTestId("not-found")).toBeDefined();
  });

  it("an address that cannot be a file id shows NotFound without asking the API", async () => {
    const { api } = serve(reader);
    renderApp("/documents/abc");

    expect(await screen.findByTestId("not-found")).toBeDefined();
    expect(api.fetch.mock.calls.some(([request]) => request.url.includes("/api/v1/documents/"))).toBe(false);
  });

  it("shows other errors of the API under the page heading", async () => {
    fakeApi(reader, () => jsonResponse({ detail: "Server trouble." }, 500));
    renderApp("/documents/7");

    expect((await screen.findByTestId("error-summary")).textContent).toBe("The API answered with HTTP status 500.");
    expect(screen.getByRole("heading", { level: 2 }).textContent).toBe("File");
  });

  it("shows the texts in German", async () => {
    await changeLanguage("de");
    await openDocument(manager);

    expect(screen.getByTestId("document-kind").textContent).toBe("Dokument");
    expect(screen.getByRole("heading", { level: 3, name: "Versionen" })).toBeDefined();
    expect(screen.getByRole("link", { name: "Version 1 herunterladen" })).toBeDefined();
    expect(screen.getByRole("form", { name: "Neue Version hochladen" })).toBeDefined();
    expect(screen.getByRole("heading", { level: 3, name: "Protokoll der Datei" })).toBeDefined();
  });
});

describe("visibility per role", () => {
  it("a reader sees the versions, but no upload form and no change log", async () => {
    const { api } = await openDocument(reader);

    expect(versionRows()).toHaveLength(2);
    expect(screen.queryByRole("form")).toBeNull();
    expect(screen.queryByTestId("document-history")).toBeNull();
    expect(api.requestsTo(AUDIT_PATH)).toHaveLength(0);
  });

  it("a manager sees the upload form and the change log of the file", async () => {
    const { api } = await openDocument(manager);

    expect(versionForm()).toBeDefined();
    const history = screen.getByTestId("document-history");
    expect(within(history).getByRole("heading", { level: 3 }).textContent).toBe("Change log of the file");
    await waitFor(() => {
      expect(api.requestsTo(AUDIT_PATH)).toHaveLength(1);
    });
    const query = new URL(api.requestsTo(AUDIT_PATH)[0]?.url ?? "").searchParams;
    expect(query.get("object_type")).toBe("files.document");
    expect(query.get("object_id")).toBe("7");
  });
});

describe("upload of a new version", () => {
  it("adds the version and shows it at the top", async () => {
    const { files } = await openDocument(manager);
    const form = versionForm();

    upload(form, "third content");

    expect((await within(form).findByTestId("upload-success")).textContent).toBe("Uploaded as version 3.");
    await waitFor(() => {
      expect(versionRows()).toHaveLength(3);
    });
    const [newest] = versionRows();
    expect(newest === undefined ? null : within(newest).getByTestId("version-filename").textContent).toBe(
      "test-version.txt",
    );
    expect(files.uploads.map((sent) => sent.path)).toEqual(["/api/v1/documents/7/versions/"]);
    expect([...(files.uploads[0]?.form.keys() ?? [])]).toEqual(["file"]);
  });

  it("shows a 409 as the version whose content it equals", async () => {
    await openDocument(manager);
    const form = versionForm();

    // The content of version 2 in the fake (its checksum is made from this text).
    upload(form, "content 71");

    const message = await within(form).findByTestId("upload-same-content");
    expect(message.textContent).toMatch(/^The content equals version 2\. No new version was created\./);
    expect(message.textContent).toContain("Version 2 was uploaded on");
    expect(within(message).getByRole("link", { name: "Download version 2" }).getAttribute("href")).toBe(
      "/api/v1/document-versions/71/download/",
    );
    expect(versionRows()).toHaveLength(2);
  });

  it("shows the 409 text in German", async () => {
    await changeLanguage("de");
    await openDocument(manager);
    const form = screen.getByRole("form", { name: "Neue Version hochladen" });

    fireEvent.change(within(form).getByLabelText("Datei"), {
      target: { files: [textFile("content 71", "test-version.txt")] },
    });
    fireEvent.click(within(form).getByRole("button", { name: "Hochladen" }));

    expect((await within(form).findByTestId("upload-same-content")).textContent).toMatch(
      /^Inhalt gleicht Version 2\. Es wurde keine neue Version angelegt\./,
    );
  });

  it("shows the limit of a 413", async () => {
    const { files } = await openDocument(manager);
    files.rejectNextUpload(413, { detail: "The file is larger than the limit of 1000 bytes." });
    const form = versionForm();

    upload(form, "too large");

    expect((await within(form).findByTestId("upload-too-large")).textContent.replace(/\s/gu, " ")).toBe(
      "The file is larger than the limit of 1 kB.",
    );
  });

  it("explains the rejection of a new version of a configuration", async () => {
    const files = fakeFilesApi(fakeStructureApi().handler);
    const first = files.documents[0];
    if (first === undefined) {
      throw new Error("no sample document");
    }
    first.kind = "configuration";
    files.rejectNextUpload(400, { non_field_errors: ["Configuration files are not accepted yet."] });
    fakeApi(manager, (request) =>
      new URL(request.url).pathname === AUDIT_PATH
        ? jsonResponse({ count: 0, next: null, previous: null, results: [] })
        : files.handler(request),
    );
    renderApp("/documents/7");
    await screen.findByTestId("document-title");
    expect(screen.getByTestId("document-kind").textContent).toBe("Configuration");

    upload(versionForm(), "new configuration");

    expect(await screen.findByTestId("upload-configuration-rejected")).toBeDefined();
  });
});
