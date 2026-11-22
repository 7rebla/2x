// Events of an answer (work order 131), as POST /api/v1/answers/ streams them.
//
// The contract (work order 122, docs/ARCHITECTURE.md "The package answers";
// work order 130 for the stream): one `sources`, then any number of `delta`,
// then one `done`; or, at any point, one `error`, after which nothing follows.
//
// The shapes come from the generated types. The schema describes `status` of
// `done` and `code` of `error` only as text, so the known values are listed
// here as literal unions (the list of codes is ErrorCode in
// backend/twox/answers/types.py). Careful with the names: the generated type
// `AnswerStatus` is the answer of GET /api/v1/answers/status/, not the status
// of `done`; that one is `AnswerResultStatus` here.
//
// Everything in an event is data: texts stay plain strings and are never read
// as HTML, Markdown or links (guard rail 4).
import type {
  AnswerDeltaEvent as GeneratedDeltaEvent,
  AnswerDoneEvent as GeneratedDoneEvent,
  AnswerErrorEvent as GeneratedErrorEvent,
  AnswerLocation,
  AnswerSource,
  AnswerSourcesEvent as GeneratedSourcesEvent,
  SearchLocation,
} from "../../api/generated";

/** How an answer ended (`status` of `done`). */
export const ANSWER_RESULT_STATUSES = ["answered", "no_evidence", "contradiction"] as const;
export type AnswerResultStatus = (typeof ANSWER_RESULT_STATUSES)[number];

/** Why an answer failed after its start (`code` of `error`); fixed list of the server. */
export const ANSWER_ERROR_CODES = [
  "ai_disabled",
  "model_unavailable",
  "model_rejected",
  "timeout",
  "search_failed",
  "internal",
] as const;
export type AnswerErrorCode = (typeof ANSWER_ERROR_CODES)[number];

/** Why no answer was started (`code` of a 409 or 503 before the stream). */
export const ANSWER_REFUSAL_CODES = ["ai_disabled", "answer_in_progress", "chat_not_configured"] as const;
export type AnswerRefusalCode = (typeof ANSWER_REFUSAL_CODES)[number];

export type AnswerSourcesEvent = Omit<GeneratedSourcesEvent, "type"> & { type: "sources" };
export type AnswerDeltaEvent = Omit<GeneratedDeltaEvent, "type"> & { type: "delta" };
export type AnswerDoneEvent = Omit<GeneratedDoneEvent, "type" | "status"> & {
  type: "done";
  status: AnswerResultStatus;
};
export type AnswerErrorEvent = Omit<GeneratedErrorEvent, "type" | "code"> & {
  type: "error";
  code: AnswerErrorCode;
};

/** One checked event of an answer. */
export type AnswerEvent = AnswerSourcesEvent | AnswerDeltaEvent | AnswerDoneEvent | AnswerErrorEvent;

type JsonObject = Readonly<Record<string, unknown>>;

function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value);
}

function isPositiveInteger(value: unknown): value is number {
  return isInteger(value) && value >= 1;
}

function isNullableInteger(value: unknown): value is number | null {
  return value === null || isInteger(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isOneOf<T extends string>(values: readonly T[], value: unknown): value is T {
  return typeof value === "string" && (values as readonly string[]).includes(value);
}

/** The known error code, or "internal" for one this version of the UI does not know yet. */
export function toAnswerErrorCode(value: string): AnswerErrorCode {
  return isOneOf(ANSWER_ERROR_CODES, value) ? value : "internal";
}

/** The known refusal code, or null. */
export function toAnswerRefusalCode(value: unknown): AnswerRefusalCode | null {
  return isOneOf(ANSWER_REFUSAL_CODES, value) ? value : null;
}

function parseLocation(data: unknown): AnswerLocation | null {
  if (!isObject(data)) {
    return null;
  }
  const {
    section_id,
    document_id,
    document_title,
    version_id,
    version_number,
    version_filename,
    is_latest_version,
    device_id,
    device_key,
    device_name,
    plant_id,
    plant_key,
    plant_name,
  } = data;
  if (
    !isInteger(section_id) ||
    !isInteger(document_id) ||
    typeof document_title !== "string" ||
    !isInteger(version_id) ||
    !isInteger(version_number) ||
    typeof version_filename !== "string" ||
    typeof is_latest_version !== "boolean" ||
    !isInteger(device_id) ||
    typeof device_key !== "string" ||
    typeof device_name !== "string" ||
    !isInteger(plant_id) ||
    typeof plant_key !== "string" ||
    typeof plant_name !== "string"
  ) {
    return null;
  }
  return {
    section_id,
    document_id,
    document_title,
    version_id,
    version_number,
    version_filename,
    is_latest_version,
    device_id,
    device_key,
    device_name,
    plant_id,
    plant_key,
    plant_name,
  };
}

function parseSource(data: unknown): AnswerSource | null {
  if (!isObject(data)) {
    return null;
  }
  const { n, section_id, version_id, sha256, page_start, page_end, heading_path, locations, snippet } = data;
  if (
    !isPositiveInteger(n) ||
    !isInteger(section_id) ||
    !isInteger(version_id) ||
    typeof sha256 !== "string" ||
    !isNullableInteger(page_start) ||
    !isNullableInteger(page_end) ||
    !isStringArray(heading_path) ||
    !Array.isArray(locations) ||
    // Every source is stored somewhere (E-55): at least one place.
    locations.length === 0 ||
    typeof snippet !== "string"
  ) {
    return null;
  }
  const parsedLocations: AnswerLocation[] = [];
  for (const item of locations) {
    const location = parseLocation(item);
    if (location === null) {
      return null;
    }
    parsedLocations.push(location);
  }
  return {
    n,
    section_id,
    version_id,
    sha256,
    page_start,
    page_end,
    heading_path: [...heading_path],
    locations: parsedLocations,
    snippet,
  };
}

function parseSources(data: JsonObject): AnswerSourcesEvent | null {
  const { sources } = data;
  if (!Array.isArray(sources)) {
    return null;
  }
  const parsed: AnswerSource[] = [];
  for (const item of sources) {
    const source = parseSource(item);
    if (source === null) {
      return null;
    }
    parsed.push(source);
  }
  return { type: "sources", sources: parsed };
}

function parseDone(data: JsonObject): AnswerDoneEvent | null {
  const { status, cited, removed_sentences, final_text } = data;
  if (
    !isOneOf(ANSWER_RESULT_STATUSES, status) ||
    !Array.isArray(cited) ||
    !cited.every(isPositiveInteger) ||
    !isInteger(removed_sentences) ||
    removed_sentences < 0 ||
    typeof final_text !== "string"
  ) {
    return null;
  }
  return { type: "done", status, cited: [...cited], removed_sentences, final_text };
}

function parseError(data: JsonObject): AnswerErrorEvent | null {
  const { code, detail } = data;
  if (typeof code !== "string" || typeof detail !== "string") {
    return null;
  }
  // An unknown code is still an error of the answer: it counts as "internal",
  // so a newer server does not turn a clean failure into an unreadable answer.
  return { type: "error", code: toAnswerErrorCode(code), detail };
}

/**
 * The event in `data` (the parsed JSON of one `data:` line), or null if it
 * does not match the contract: unknown type, missing or wrongly typed field,
 * unknown `status`. Returns fresh objects; unknown extra fields are dropped.
 */
export function parseAnswerEvent(data: unknown): AnswerEvent | null {
  if (!isObject(data)) {
    return null;
  }
  switch (data.type) {
    case "sources":
      return parseSources(data);
    case "delta":
      return typeof data.text === "string" ? { type: "delta", text: data.text } : null;
    case "done":
      return parseDone(data);
    case "error":
      return parseError(data);
    default:
      return null;
  }
}

/**
 * A place of a source in the shape of a place of a search hit, so the answer
 * page (work order 132) can show sources like the search shows hits. The
 * stream sends places flat (`source_ref_to_json()` of work order 122).
 */
export function toSearchLocation(location: AnswerLocation): SearchLocation {
  return {
    document: { id: location.document_id, title: location.document_title },
    version: {
      id: location.version_id,
      number: location.version_number,
      original_filename: location.version_filename,
      is_latest: location.is_latest_version,
    },
    device: { id: location.device_id, key: location.device_key, name: location.device_name },
    plant: { id: location.plant_id, key: location.plant_key, name: location.plant_name },
  };
}
