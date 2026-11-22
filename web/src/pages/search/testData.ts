// Test helper: search hits written for the tests and a fake of GET /api/v1/search/.
// The texts are plain test sentences, not taken from any manual. Devices and
// plants are those of structure/testData.ts (sampleStructure).
import type { SearchHit, SearchLocation, SearchResult } from "../../api/generated";
import { type Handler, jsonResponse } from "../../test/fakeApi.ts";
import { fakeStructureApi } from "../structure/testData.ts";

export const SEARCH_PATH = "/api/v1/search/";

/** A place a hit is stored at; defaults: file 7 version 2 (newest) on device 1000 in plant 100. */
export function location(more: {
  documentId?: number;
  title?: string;
  versionId?: number;
  number?: number;
  filename?: string;
  isLatest?: boolean;
  deviceId?: number;
  deviceKey?: string;
  deviceName?: string;
  plantId?: number;
  plantKey?: string;
  plantName?: string;
} = {}): SearchLocation {
  return {
    document: { id: more.documentId ?? 7, title: more.title ?? "Test manual" },
    version: {
      id: more.versionId ?? 71,
      number: more.number ?? 2,
      original_filename: more.filename ?? "test-manual-v2.pdf",
      is_latest: more.isLatest ?? true,
    },
    device: { id: more.deviceId ?? 1000, key: more.deviceKey ?? "test-plc-1", name: more.deviceName ?? "Test controller" },
    plant: { id: more.plantId ?? 100, key: more.plantKey ?? "test-plant-1", name: more.plantName ?? "Test plant one" },
  };
}

/** A hit with one place; the snippet marks "inspection". */
export function hit(sectionId: number, more: Partial<SearchHit> = {}): SearchHit {
  return {
    section_id: sectionId,
    score: 1,
    match_kinds: ["keyword"],
    snippet: "The inspection of the test station is due every year.",
    highlights: [{ start: 4, end: 14 }],
    page_start: 31,
    page_end: 31,
    heading_path: ["Test chapter 3", "Test section 3.2"],
    locations: [location()],
    ...more,
  };
}

/** Three hits: one page, a page range with two places (one an older version), and one without a page. */
export function sampleResult(semantic: SearchResult["semantic"] = "used"): SearchResult {
  return {
    semantic,
    hits: [
      hit(501, { match_kinds: ["exact", "keyword"] }),
      hit(502, {
        snippet: "Address 192.0.2.10 of the test controller and its inspection plan.",
        highlights: [{ start: 8, end: 18 }],
        page_start: 31,
        page_end: 32,
        heading_path: ["Test network"],
        match_kinds: ["keyword", "semantic"],
        locations: [
          location(),
          location({
            documentId: 8,
            title: "Test drive notes",
            versionId: 81,
            number: 1,
            filename: "test-drive-notes.pdf",
            isLatest: false,
            deviceId: 1003,
            deviceKey: "test-drive-1",
            deviceName: "Test drive",
            plantId: 102,
            plantKey: "test-plant-3",
            plantName: "Test plant three",
          }),
        ],
      }),
      hit(503, {
        snippet: "A short test note without pages.",
        highlights: [{ start: 8, end: 12 }],
        page_start: null,
        page_end: null,
        heading_path: ["Test notes", "Test topic"],
        match_kinds: ["semantic"],
      }),
    ],
  };
}

export interface FakeSearchApi {
  readonly handler: Handler;
  /** Query parameters of every search request, in order. */
  readonly searches: URLSearchParams[];
}

/**
 * Answers GET /api/v1/search/ with `answer` (a result, or a function of the
 * request for errors); every other request goes to the structure API
 * (device list for the form).
 */
export function fakeSearchApi(
  answer: SearchResult | ((params: URLSearchParams) => Response) = sampleResult(),
  other: Handler = fakeStructureApi().handler,
): FakeSearchApi {
  const searches: URLSearchParams[] = [];
  const handler: Handler = (request) => {
    const url = new URL(request.url);
    if (url.pathname === SEARCH_PATH && request.method === "GET") {
      searches.push(url.searchParams);
      return typeof answer === "function" ? answer(url.searchParams) : jsonResponse(answer);
    }
    return other(request);
  };
  return { handler, searches };
}
