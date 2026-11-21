// Test helper: a fake of the file API behind fetch, on top of the structure fake.
// Titles and file names are plain test names; checksums are made up from the content.
import type { Document, DocumentDetail, DocumentVersion, Duplicate, KindEnum } from "../../api/generated";
import { vi } from "vitest";

import type { Me } from "../../api/generated";
import { type FakeApi, fakeApi, type Handler, jsonResponse } from "../../test/fakeApi.ts";

const STAMP = "2026-11-21T10:00:00Z";

/** A checksum of 64 hex digits that depends only on the text. */
export function fakeChecksum(content: string): string {
  let hash = 0;
  for (const char of content) {
    hash = (hash * 31 + (char.codePointAt(0) ?? 0)) >>> 0;
  }
  return hash.toString(16).padStart(8, "0").repeat(8);
}

export function version(
  id: number,
  number: number,
  more: Partial<Omit<DocumentVersion, "id" | "number">> = {},
): DocumentVersion {
  return {
    id,
    number,
    sha256: fakeChecksum(`content ${String(id)}`),
    size: 1536,
    content_type: "text/plain",
    original_filename: `test-file-${String(number)}.txt`,
    uploaded_by: "test-manager",
    created_at: STAMP,
    ...more,
  };
}

export interface StoredDocument {
  id: number;
  device: number;
  title: string;
  kind: KindEnum;
  created_by: string | null;
  versions: DocumentVersion[];
}

function summary(stored: StoredDocument): Document {
  return {
    id: stored.id,
    device: stored.device,
    title: stored.title,
    kind: stored.kind,
    created_at: STAMP,
    created_by: stored.created_by,
    latest_version: stored.versions.at(-1) ?? null,
  };
}

function detail(stored: StoredDocument): DocumentDetail {
  return { ...summary(stored), versions: [...stored.versions] };
}

/** Two files of device 1000: one with two versions, one with one. */
export function sampleDocuments(): StoredDocument[] {
  return [
    {
      id: 7,
      device: 1000,
      title: "Test manual",
      kind: "document",
      created_by: "test-manager",
      versions: [
        version(70, 1, { size: 1_500_000, created_at: "2026-11-20T08:00:00Z" }),
        version(71, 2, { size: 2_500_000, uploaded_by: null, created_at: "2026-11-21T09:30:00Z" }),
      ],
    },
    {
      id: 8,
      device: 1000,
      title: "Test notes",
      kind: "document",
      created_by: "test-manager",
      versions: [version(80, 1, { size: 512 })],
    },
  ];
}

export interface Answer {
  readonly status: number;
  readonly body: unknown;
}

// Under jsdom, FormData and File come from jsdom, Request from Node. Node's
// Request cannot read jsdom files: a form with a file goes out as an empty
// part named "blob". The tests therefore use text files made by textFile()
// and send forms through sendFormsAsText(), which writes the multipart body
// itself. The app code is the same as in the browser.

const fileContents = new WeakMap<Blob, string>();

/** A text file whose content the test Request can read (see sendFormsAsText). */
export function textFile(content: string, name: string): File {
  const file = new File([content], name, { type: "text/plain" });
  fileContents.set(file, content);
  return file;
}

const BOUNDARY = "test-boundary-7f3a";

function quoted(text: string): string {
  return text.replace(/"/g, "%22").replace(/\r?\n/g, " ");
}

function multipart(form: FormData): string {
  let body = "";
  for (const [name, value] of form.entries()) {
    body += `--${BOUNDARY}\r\n`;
    if (typeof value === "string") {
      body += `Content-Disposition: form-data; name="${quoted(name)}"\r\n\r\n${value}\r\n`;
    } else {
      const content = fileContents.get(value);
      if (content === undefined) {
        throw new Error("test: upload only files made by textFile()");
      }
      body += `Content-Disposition: form-data; name="${quoted(name)}"; filename="${quoted(value.name)}"\r\n`;
      body += `Content-Type: ${value.type === "" ? "application/octet-stream" : value.type}\r\n\r\n${content}\r\n`;
    }
  }
  return `${body}--${BOUNDARY}--\r\n`;
}

/** Makes every Request with a FormData body carry it as multipart text; call after fakeApi(). */
export function sendFormsAsText(): void {
  const Base = globalThis.Request;
  class TextFormRequest extends Base {
    constructor(input: RequestInfo | URL, init?: RequestInit) {
      if (init?.body instanceof FormData) {
        const headers = new Headers(init.headers);
        headers.set("Content-Type", `multipart/form-data; boundary=${BOUNDARY}`);
        super(input, { ...init, body: multipart(init.body), headers });
      } else {
        super(input, init);
      }
    }
  }
  vi.stubGlobal("Request", TextFormRequest);
}

/** fakeApi() (test/fakeApi.ts) whose requests carry forms as multipart text. */
export function fakeUploadApi(me: Me | null, other?: Handler): FakeApi {
  const api = fakeApi(me, other);
  sendFormsAsText();
  return api;
}

/** One part of a multipart form: its text and, for a file, the file name. */
export interface FormPart {
  readonly value: string;
  readonly filename: string | null;
}

/**
 * Reads a multipart/form-data request body. Under jsdom, Request.formData()
 * cannot hand out files (jsdom's File is not the one of Node's fetch), so the
 * tests read the body as text. Enough for small text files.
 */
export async function readForm(request: Request): Promise<Map<string, FormPart>> {
  const boundary = /boundary=(.+)$/.exec(request.headers.get("Content-Type") ?? "")?.[1];
  if (boundary === undefined) {
    throw new Error("test API: not a multipart form");
  }
  const body = await request.clone().text();
  const parts = new Map<string, FormPart>();
  for (const chunk of body.split(`--${boundary}`)) {
    const separator = chunk.indexOf("\r\n\r\n");
    if (separator === -1) {
      continue;
    }
    const head = chunk.slice(0, separator);
    const name = /name="([^"]*)"/.exec(head)?.[1];
    if (name === undefined) {
      continue;
    }
    const filename = /filename="([^"]*)"/.exec(head)?.[1] ?? null;
    parts.set(name, { value: chunk.slice(separator + 4).replace(/\r\n$/, ""), filename });
  }
  return parts;
}

export interface FakeFilesApi {
  readonly handler: Handler;
  readonly documents: StoredDocument[];
  /** Answer of the next upload instead of storing it (for example a 413). */
  rejectNextUpload: (status: number, body: unknown) => void;
  /** Places reported as duplicates by the next successful upload. */
  duplicatesOfNextUpload: (duplicates: Duplicate[]) => void;
  /** The forms sent to the upload endpoints, in order. */
  readonly uploads: { path: string; form: Map<string, FormPart> }[];
}

const DEVICE_DOCUMENTS = /^\/api\/v1\/devices\/(\d+)\/documents\/$/;
const DOCUMENT = /^\/api\/v1\/documents\/(\d+)\/$/;
const VERSIONS = /^\/api\/v1\/documents\/(\d+)\/versions\/$/;

interface SentFile {
  readonly name: string;
  readonly content: string;
  readonly size: number;
}

function fileOf(form: Map<string, FormPart>): SentFile | null {
  const part = form.get("file");
  if (part === undefined || part.filename === null || part.filename === "") {
    return null;
  }
  return { name: part.filename, content: part.value, size: new TextEncoder().encode(part.value).length };
}

/**
 * Serves the file endpoints; everything else goes to `fallback` (for example
 * the structure fake). Uploads are stored, so a reload shows them; an upload
 * equal to the newest version answers 409 like the API.
 */
export function fakeFilesApi(fallback: Handler, documents: StoredDocument[] = sampleDocuments()): FakeFilesApi {
  let rejection: Answer | null = null;
  let nextDuplicates: Duplicate[] = [];
  let nextId = 9000;
  const uploads: { path: string; form: Map<string, FormPart> }[] = [];

  const takeRejection = (): Answer | null => {
    const answer = rejection;
    rejection = null;
    return answer;
  };

  const newVersion = (number: number, file: SentFile): DocumentVersion => {
    nextId += 1;
    return version(nextId, number, {
      sha256: fakeChecksum(file.content),
      size: file.size,
      original_filename: file.name,
      created_at: "2026-11-22T12:00:00Z",
    });
  };

  const handler: Handler = async (request) => {
    const path = new URL(request.url).pathname;
    const list = DEVICE_DOCUMENTS.exec(path);
    const single = DOCUMENT.exec(path);
    const versions = VERSIONS.exec(path);

    if (list !== null && request.method === "GET") {
      const deviceId = Number(list[1]);
      return jsonResponse(documents.filter((item) => item.device === deviceId).map(summary));
    }
    if (single !== null && request.method === "GET") {
      const found = documents.find((item) => item.id === Number(single[1]));
      return found === undefined ? jsonResponse({ detail: "Not found." }, 404) : jsonResponse(detail(found));
    }
    if ((list !== null || versions !== null) && request.method === "POST") {
      const form = await readForm(request);
      uploads.push({ path, form });
      const rejected = takeRejection();
      if (rejected !== null) {
        return jsonResponse(rejected.body, rejected.status);
      }
      const file = fileOf(form);
      if (file === null) {
        return jsonResponse({ file: ["No file was submitted."] }, 400);
      }
      const duplicates = nextDuplicates;
      nextDuplicates = [];
      if (list !== null) {
        nextId += 1;
        const title = form.get("title")?.value ?? "";
        const kind = form.get("kind")?.value === "configuration" ? "configuration" : "document";
        const item: StoredDocument = {
          id: nextId,
          device: Number(list[1]),
          title: title === "" ? file.name : title,
          kind,
          created_by: "test-manager",
          versions: [newVersion(1, file)],
        };
        documents.push(item);
        return jsonResponse({ document: summary(item), version: item.versions[0], duplicates }, 201);
      }
      const item = documents.find((entry) => entry.id === Number(versions?.[1]));
      if (item === undefined) {
        return jsonResponse({ detail: "Not found." }, 404);
      }
      const latest = item.versions.at(-1);
      if (latest !== undefined && latest.sha256 === fakeChecksum(file.content)) {
        return jsonResponse(
          { detail: "The content equals the newest version.", code: "duplicate_version", existing_version: latest },
          409,
        );
      }
      const added = newVersion((latest?.number ?? 0) + 1, file);
      item.versions.push(added);
      return jsonResponse({ document: summary(item), version: added, duplicates }, 201);
    }
    return fallback(request);
  };

  return {
    handler,
    documents,
    uploads,
    rejectNextUpload: (status, body) => {
      rejection = { status, body };
    },
    duplicatesOfNextUpload: (duplicates) => {
      nextDuplicates = duplicates;
    },
  };
}
