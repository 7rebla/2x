import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { installClientConfig } from "../../api/client.ts";
import { ApiError, installApiErrorHandling } from "../../api/errors.ts";
import { jsonResponse, manager } from "../../test/fakeApi.ts";
import { fakeUploadApi as fakeApi, readForm, textFile, version } from "./testData.ts";
import { uploadDocument, uploadVersion } from "./upload.ts";

beforeAll(() => {
  installClientConfig();
  installApiErrorHandling();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
});

function testFile(content = "test content", name = "test-file.txt"): File {
  return textFile(content, name);
}

const uploaded = {
  document: {
    id: 7,
    device: 1000,
    title: "Test manual",
    kind: "document",
    created_at: "2026-11-21T10:00:00Z",
    created_by: "test-manager",
    latest_version: version(70, 1),
  },
  version: version(70, 1),
  duplicates: [],
};

describe("uploadDocument", () => {
  it("sends file, title and kind as multipart form with the CSRF token", async () => {
    document.cookie = "csrftoken=test-token";
    const api = fakeApi(manager, () => jsonResponse(uploaded, 201));

    const outcome = await uploadDocument(1000, { file: testFile(), title: "  Test manual ", kind: "document" });

    expect(outcome).toEqual({ kind: "uploaded", result: uploaded });
    const [request] = api.requestsTo("/api/v1/devices/1000/documents/");
    expect(request?.method).toBe("POST");
    expect(request?.headers.get("X-CSRFToken")).toBe("test-token");
    expect(request?.headers.get("Content-Type")).toMatch(/^multipart\/form-data; boundary=/);
    const form = request === undefined ? null : await readForm(request);
    expect(form?.get("title")).toEqual({ value: "Test manual", filename: null });
    expect(form?.get("kind")).toEqual({ value: "document", filename: null });
    expect(form?.get("file")).toEqual({ value: "test content", filename: "test-file.txt" });
  });

  it("leaves out an empty title, so the API uses the file name", async () => {
    const api = fakeApi(manager, () => jsonResponse(uploaded, 201));

    await uploadDocument(1000, { file: testFile(), title: "   ", kind: "document" });

    const [request] = api.requestsTo("/api/v1/devices/1000/documents/");
    const form = request === undefined ? null : await readForm(request);
    expect([...(form?.keys() ?? [])]).toEqual(["file", "kind"]);
  });

  it("reads the field errors of a 400", async () => {
    fakeApi(manager, () =>
      jsonResponse({ kind: ["Configuration files are not accepted yet."], non_field_errors: ["Test message."] }, 400),
    );

    const outcome = await uploadDocument(1000, { file: testFile(), title: "", kind: "configuration" });

    expect(outcome).toEqual({
      kind: "invalid",
      fieldErrors: { kind: ["Configuration files are not accepted yet."], non_field_errors: ["Test message."] },
    });
  });

  it("reads the limit from a 413", async () => {
    fakeApi(manager, () => jsonResponse({ detail: "The file is larger than the limit of 200000000 bytes." }, 413));

    expect(await uploadDocument(1000, { file: testFile(), title: "", kind: "document" })).toEqual({
      kind: "tooLarge",
      limitBytes: 200_000_000,
    });
  });

  it("a 413 without a readable body has no limit", async () => {
    fakeApi(manager, () => new Response("Request Entity Too Large", { status: 413 }));

    expect(await uploadDocument(1000, { file: testFile(), title: "", kind: "document" })).toEqual({
      kind: "tooLarge",
      limitBytes: null,
    });
  });

  it("passes other errors on as ApiError", async () => {
    fakeApi(manager, () => jsonResponse({ detail: "You do not have permission." }, 403));

    const outcome = await uploadDocument(1000, { file: testFile(), title: "", kind: "document" });

    expect(outcome.kind).toBe("failed");
    const error = outcome.kind === "failed" ? outcome.error : null;
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(403);
  });

  it("reports a missing answer as network error", async () => {
    fakeApi(manager);

    const outcome = await uploadDocument(1000, { file: testFile(), title: "", kind: "document" });

    expect(outcome.kind === "failed" && outcome.error instanceof ApiError && outcome.error.kind).toBe("network");
  });
});

describe("uploadVersion", () => {
  it("sends only the file", async () => {
    const api = fakeApi(manager, () => jsonResponse({ ...uploaded, version: version(71, 2) }, 201));

    const outcome = await uploadVersion(7, testFile("second"));

    expect(outcome.kind === "uploaded" && outcome.result.version.number).toBe(2);
    const [request] = api.requestsTo("/api/v1/documents/7/versions/");
    const form = request === undefined ? null : await readForm(request);
    expect([...(form?.keys() ?? [])]).toEqual(["file"]);
  });

  it("names the existing version of a 409", async () => {
    const existing = version(71, 2);
    fakeApi(manager, () =>
      jsonResponse({ detail: "The content equals the newest version.", code: "duplicate_version", existing_version: existing }, 409),
    );

    expect(await uploadVersion(7, testFile())).toEqual({ kind: "sameAsLatest", existing });
  });

  it("a 409 without the existing version is a plain failure", async () => {
    fakeApi(manager, () => jsonResponse({ detail: "Conflict." }, 409));

    const outcome = await uploadVersion(7, testFile());

    expect(outcome.kind).toBe("failed");
  });
});
