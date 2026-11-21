// Uploading a new file or a new version through the generated client.
//
// The shared error handling (api/errors.ts) keeps only the status and a
// "detail" text of a failed call. An upload needs more of the answer: the
// field errors of a 400, the existing version of a 409 and the limit named in
// a 413. The call therefore gets a fetch of its own that keeps a copy of these
// answers (the same way as pages/structure/save.ts does for 400).
import { ApiError } from "../../api/errors.ts";
import type { DocumentVersion, KindEnum, UploadResult } from "../../api/generated";
import { deviceDocumentsCreate, documentVersionCreate } from "../../api/generated/sdk.gen.ts";
import { type FieldErrors, parseFieldErrors } from "../../pages/structure/save.ts";
import { limitFromMessage } from "./format.ts";

export type UploadOutcome =
  | { readonly kind: "uploaded"; readonly result: UploadResult }
  /** 409: the content equals the newest version of the file; nothing was stored. */
  | { readonly kind: "sameAsLatest"; readonly existing: DocumentVersion }
  /** 413: larger than TWOX_UPLOAD_MAX_BYTES; the limit if the API's message names it. */
  | { readonly kind: "tooLarge"; readonly limitBytes: number | null }
  /** 400: the API named what is wrong (possibly nothing readable: then the map is empty). */
  | { readonly kind: "invalid"; readonly fieldErrors: FieldErrors }
  /** Anything else: no permission, unknown device, no answer, server error … */
  | { readonly kind: "failed"; readonly error: unknown };

/** Statuses whose body the upload reads itself. */
const READ_STATUSES = new Set([400, 409, 413]);

function isDocumentVersion(value: unknown): value is DocumentVersion {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    typeof record.id === "number" &&
    typeof record.number === "number" &&
    typeof record.sha256 === "string" &&
    typeof record.size === "number" &&
    typeof record.created_at === "string"
  );
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return (await response.json()) as unknown;
  } catch {
    return null;
  }
}

/** The outcome of a failed call, from the error and the copy of the answer. */
async function failedOutcome(error: unknown, answer: Response | null): Promise<UploadOutcome> {
  if (!(error instanceof ApiError) || error.kind !== "http" || answer === null || answer.status !== error.status) {
    return { kind: "failed", error };
  }
  const body = await readJson(answer);
  switch (answer.status) {
    case 400:
      return { kind: "invalid", fieldErrors: parseFieldErrors(body) };
    case 409: {
      const existing =
        typeof body === "object" && body !== null ? (body as Record<string, unknown>).existing_version : undefined;
      return isDocumentVersion(existing) ? { kind: "sameAsLatest", existing } : { kind: "failed", error };
    }
    case 413:
      return { kind: "tooLarge", limitBytes: limitFromMessage(error.detail) };
    default:
      return { kind: "failed", error };
  }
}

/**
 * Sends one upload. `send` must pass the given fetch to the generated client
 * (option `fetch`) and throw on error (option `throwOnError`).
 */
export async function upload(send: (fetchFn: typeof fetch) => Promise<UploadResult>): Promise<UploadOutcome> {
  const captured: { answer: Response | null } = { answer: null };
  const capturingFetch: typeof fetch = async (input, init) => {
    // Looked up at call time, like the generated client does (tests replace it).
    const response = await globalThis.fetch(input, init);
    captured.answer = READ_STATUSES.has(response.status) ? response.clone() : null;
    return response;
  };
  try {
    return { kind: "uploaded", result: await send(capturingFetch) };
  } catch (error) {
    return failedOutcome(error, captured.answer);
  }
}

export interface NewDocument {
  readonly file: File;
  /** Empty: the API uses the file name. */
  readonly title: string;
  readonly kind: KindEnum;
}

/** Uploads a new file of the device (version 1). */
export function uploadDocument(deviceId: number, form: NewDocument): Promise<UploadOutcome> {
  return upload(async (fetchFn) => {
    const title = form.title.trim();
    const { data } = await deviceDocumentsCreate({
      path: { device_id: deviceId },
      body: title === "" ? { file: form.file, kind: form.kind } : { file: form.file, title, kind: form.kind },
      fetch: fetchFn,
      throwOnError: true,
    });
    return data;
  });
}

/** Uploads a new version of the file. */
export function uploadVersion(documentId: number, file: File): Promise<UploadOutcome> {
  return upload(async (fetchFn) => {
    const { data } = await documentVersionCreate({
      path: { document_id: documentId },
      body: { file },
      fetch: fetchFn,
      throwOnError: true,
    });
    return data;
  });
}
