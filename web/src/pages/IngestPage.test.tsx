// Ingest overview (work order 055): filter and address, pages, the states of
// the list and of a job, polling, the button and the column "started by" per role.
import { act, cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import type { IngestJob, IngestStatusEnum, Me } from "../api/generated";
import { changeLanguage } from "../i18n.ts";
import { fakeApi, type FakeApi, type Handler, jsonResponse, manager, reader } from "../test/fakeApi.ts";
import { renderApp } from "../test/renderApp.tsx";
import { ingestAddressParams, readIngestAddress, statusesFor } from "./IngestPage.tsx";
import { fakeStructureApi } from "./structure/testData.ts";

// routes.tsx loads the page lazily; importing it once keeps the first render within the usual waiting time.
beforeAll(async () => {
  await import("./IngestPage.tsx");
});

afterEach(async () => {
  vi.useRealTimers();
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  await changeLanguage("en");
  window.localStorage.clear();
});

const JOBS_PATH = "/api/v1/ingest-jobs/";
const INGEST = /^\/api\/v1\/document-versions\/(\d+)\/ingest\/$/;

/** Devices of structure/testData.ts (sampleStructure). */
const DEVICES = {
  1000: { id: 1000, key: "test-plc-1", name: "Test controller" },
  1001: { id: 1001, key: "test-hmi-1", name: "Test panel" },
} as const;

/** A job as GET /api/v1/ingest-jobs/ lists it; created later for a higher id. */
function job(id: number, status: IngestStatusEnum, more: Partial<IngestJob> = {}): IngestJob {
  return {
    id,
    status,
    step: "",
    error_code: "",
    error_detail: "",
    partly_converted: false,
    conversion_error_count: 0,
    section_count: null,
    page_count: null,
    created_at: new Date(Date.UTC(2026, 10, 1, 8, 0, id)).toISOString(),
    finished_at: null,
    document: { id: 7, title: "Test manual" },
    version: { id: 71, number: 2, original_filename: "test-manual-v2.pdf" },
    device: DEVICES[1000],
    requested_by: "test-manager",
    // The fake API sets it from the other jobs of the version (isNewest).
    is_latest: true,
    ...more,
  };
}

/** Whether `item` is the newest job of its version among `jobs`: by creation, then id, like the API. */
function isNewest(item: IngestJob, jobs: readonly IngestJob[]): boolean {
  return !jobs.some(
    (other) =>
      other.version.id === item.version.id &&
      (other.created_at > item.created_at || (other.created_at === item.created_at && other.id > item.id)),
  );
}

/** Five jobs, one per state, on different files; newest first like the API. */
function sampleJobs(): IngestJob[] {
  return [
    job(15, "failed", {
      error_code: "docling_unavailable",
      error_detail: "converter not reachable after 5 attempts",
      finished_at: "2026-11-01T08:10:00Z",
    }),
    job(14, "running", {
      step: "convert",
      document: { id: 8, title: "Test wiring plan" },
      version: { id: 81, number: 1, original_filename: "wiring.pdf" },
      device: DEVICES[1001],
      requested_by: null,
    }),
    job(13, "queued", {
      document: { id: 9, title: "Test checklist" },
      version: { id: 91, number: 1, original_filename: "checklist.md" },
    }),
    job(12, "done", {
      step: "sections",
      page_count: 60,
      section_count: 140,
      finished_at: "2026-11-01T08:05:00Z",
      document: { id: 10, title: "Test handbook" },
      version: { id: 101, number: 3, original_filename: "handbook.pdf" },
    }),
    job(11, "skipped", {
      error_code: "unsupported_format",
      error_detail: "format text/plain is not ingested",
      finished_at: "2026-11-01T08:00:11Z",
      document: { id: 11, title: "Test notes" },
      version: { id: 111, number: 1, original_filename: "notes.txt" },
      device: DEVICES[1001],
    }),
  ];
}

interface FakeIngestApi {
  readonly handler: Handler;
  /** The jobs the fake API holds, newest first; tests change them between two queries. */
  readonly jobs: IngestJob[];
  /** Query parameters of every list request, in order. */
  readonly lists: URLSearchParams[];
  /** Version ids sent to POST …/ingest/, in order. */
  readonly ingests: number[];
}

/**
 * GET /api/v1/ingest-jobs/ with the filters latest, status (repeatable) and
 * device, is_latest on every job and 50 jobs per page; POST …/ingest/ adds a
 * queued job (202). Everything else goes to the structure API (device list of
 * the filter).
 */
function fakeIngestApi(jobs: IngestJob[] = sampleJobs(), listAnswer?: () => Response): FakeIngestApi {
  const lists: URLSearchParams[] = [];
  const ingests: number[] = [];
  const structure = fakeStructureApi().handler;
  const handler: Handler = (request) => {
    const url = new URL(request.url);
    if (url.pathname === JOBS_PATH && request.method === "GET") {
      lists.push(url.searchParams);
      if (listAnswer !== undefined) {
        return listAnswer();
      }
      const statuses = url.searchParams.getAll("status");
      const device = url.searchParams.get("device");
      const latest = url.searchParams.get("latest") === "true";
      // The newest job is chosen among all jobs of a version, before the other filters.
      const matching = jobs
        .map((item) => ({ ...item, is_latest: isNewest(item, jobs) }))
        .filter(
          (item) =>
            (!latest || item.is_latest) &&
            (statuses.length === 0 || statuses.includes(item.status)) &&
            (device === null || String(item.device.id) === device),
        );
      const page = Number(url.searchParams.get("page") ?? "1");
      const results = matching.slice((page - 1) * 50, page * 50);
      return jsonResponse({
        count: matching.length,
        next: page * 50 < matching.length ? `http://testserver${JOBS_PATH}?page=${String(page + 1)}` : null,
        previous: page > 1 ? `http://testserver${JOBS_PATH}?page=${String(page - 1)}` : null,
        results,
      });
    }
    const ingest = INGEST.exec(url.pathname);
    if (ingest !== null && request.method === "POST") {
      const versionId = Number(ingest[1]);
      ingests.push(versionId);
      const old = jobs.find((item) => item.version.id === versionId);
      if (old === undefined) {
        return jsonResponse({ detail: "Not found." }, 404);
      }
      const id = Math.max(...jobs.map((item) => item.id)) + 1;
      const created = job(id, "queued", { document: old.document, version: old.version, device: old.device });
      jobs.unshift(created);
      return jsonResponse(created, 202);
    }
    return structure(request);
  };
  return { handler, jobs, lists, ingests };
}

async function openOverview(user: Me, path = "/ingest", api = fakeIngestApi()): Promise<{ api: FakeIngestApi; fake: FakeApi; router: ReturnType<typeof renderApp>["router"] }> {
  const fake = fakeApi(user, api.handler);
  const { router } = renderApp(path);
  await screen.findByTestId("ingest-filter");
  return { api, fake, router };
}

async function rows(): Promise<HTMLElement[]> {
  return screen.findAllByTestId("ingest-job");
}

function row(id: number): HTMLElement {
  const found = screen.getAllByTestId("ingest-job").find((item) => item.dataset.job === String(id));
  if (found === undefined) {
    throw new Error(`no row for job ${String(id)}`);
  }
  return found;
}

function lastList(api: FakeIngestApi): URLSearchParams {
  const last = api.lists.at(-1);
  if (last === undefined) {
    throw new Error("no list request");
  }
  return last;
}

describe("address", () => {
  it("reads the status, the device and the switch, and falls back to the open, newest jobs of all devices", () => {
    expect(readIngestAddress(new URLSearchParams(""))).toEqual({ status: "open", device: null, older: false });
    expect(readIngestAddress(new URLSearchParams("status=all&device=1000"))).toEqual({
      status: "all",
      device: 1000,
      older: false,
    });
    expect(readIngestAddress(new URLSearchParams("status=skipped"))).toEqual({ status: "skipped", device: null, older: false });
    expect(readIngestAddress(new URLSearchParams("status=broken&device=abc"))).toEqual({
      status: "open",
      device: null,
      older: false,
    });
    expect(readIngestAddress(new URLSearchParams("device=0"))).toEqual({ status: "open", device: null, older: false });
    expect(readIngestAddress(new URLSearchParams("older=1"))).toEqual({ status: "open", device: null, older: true });
    expect(readIngestAddress(new URLSearchParams("older=yes")).older).toBe(false);
    expect(readIngestAddress(new URLSearchParams("older=0")).older).toBe(false);
  });

  it("writes only what differs from the defaults", () => {
    expect(ingestAddressParams({ status: "open", device: null, older: false }).toString()).toBe("");
    expect(ingestAddressParams({ status: "failed", device: 1001, older: false }).toString()).toBe("status=failed&device=1001");
    expect(ingestAddressParams({ status: "all", device: null, older: false }).toString()).toBe("status=all");
    expect(ingestAddressParams({ status: "all", device: 1000, older: true }).toString()).toBe("status=all&device=1000&older=1");
  });

  it("asks the API for failed, running and queued jobs by default, for one state, or for all", () => {
    expect(statusesFor("open")).toEqual(["failed", "running", "queued"]);
    expect(statusesFor("done")).toEqual(["done"]);
    expect(statusesFor("all")).toBeUndefined();
  });
});

describe("filter", () => {
  it("lists failed, running and queued jobs of all devices without a filter", async () => {
    const { api } = await openOverview(reader);

    expect((await screen.findByRole("heading", { level: 1 })).textContent).toBe("Ingestion");
    expect(await rows()).toHaveLength(3);
    expect(lastList(api).getAll("status")).toEqual(["failed", "running", "queued"]);
    expect(lastList(api).get("device")).toBeNull();
    expect(lastList(api).get("page")).toBeNull();
    // Only the newest job of each version by default (work order 064).
    expect(lastList(api).get("latest")).toBe("true");
    expect(screen.getByTestId<HTMLInputElement>("ingest-filter-older").checked).toBe(false);
    expect(screen.getByTestId("ingest-filter").textContent).toContain("Also show older attempts");
    expect(screen.getByTestId<HTMLSelectElement>("ingest-filter-status").value).toBe("open");
    expect(screen.getByTestId<HTMLSelectElement>("ingest-filter-device").value).toBe("");
    expect(screen.getAllByTestId("ingest-job").map((item) => item.dataset.status)).toEqual(["failed", "running", "queued"]);
  });

  it("offers every state and 'All' in English and German", async () => {
    await openOverview(reader);
    const select = screen.getByTestId("ingest-filter-status");
    expect(within(select).getAllByRole("option").map((option) => option.textContent)).toEqual([
      "Open (error, running, queued)",
      "Error",
      "Ingesting",
      "Queued",
      "Ingested",
      "Skipped",
      "All",
    ]);

    await act(() => changeLanguage("de"));
    expect(within(select).getAllByRole("option").map((option) => option.textContent)).toEqual([
      "Offen (Fehler, läuft, wartet)",
      "Fehler",
      "Wird eingelesen",
      "In Warteschlange",
      "Eingelesen",
      "Übersprungen",
      "Alle",
    ]);
  });

  it("'All' also lists ingested and skipped jobs and sends no status", async () => {
    const { api } = await openOverview(reader, "/ingest?status=all");

    expect(await rows()).toHaveLength(5);
    expect(lastList(api).getAll("status")).toEqual([]);
    expect(lastList(api).get("latest")).toBe("true");
    expect(within(row(12)).getByTestId("ingest-status").textContent).toBe("Ingested");
    expect(within(row(12)).getByTestId("ingest-counts").textContent).toBe("60 pages, 140 sections");
    expect(within(row(11)).getByTestId("ingest-status").textContent).toBe("Skipped");
  });

  it("a status choice goes into the address and the request; Back restores the previous view", async () => {
    const { api, router } = await openOverview(reader);
    await rows();

    fireEvent.change(screen.getByTestId("ingest-filter-status"), { target: { value: "skipped" } });

    await waitFor(() => {
      expect(router.state.location.search).toBe("?status=skipped");
    });
    await waitFor(() => {
      expect(screen.getAllByTestId("ingest-job").map((item) => item.dataset.job)).toEqual(["11"]);
    });
    expect(lastList(api).getAll("status")).toEqual(["skipped"]);

    await act(() => router.navigate(-1));
    await waitFor(() => {
      expect(screen.getAllByTestId("ingest-job")).toHaveLength(3);
    });
    expect(screen.getByTestId<HTMLSelectElement>("ingest-filter-status").value).toBe("open");
  });

  it("lists the devices by plant and filters by the chosen one", async () => {
    const { api, router } = await openOverview(reader, "/ingest?status=all");
    await rows();
    const select = screen.getByTestId("ingest-filter-device");
    await waitFor(() => {
      expect(within(select).getAllByRole("option")).toHaveLength(5);
    });
    expect(within(select).getAllByRole("option")[0]?.textContent).toBe("All devices");

    fireEvent.change(select, { target: { value: "1001" } });

    await waitFor(() => {
      expect(router.state.location.search).toBe("?status=all&device=1001");
    });
    await waitFor(() => {
      expect(screen.getAllByTestId("ingest-job").map((item) => item.dataset.job)).toEqual(["14", "11"]);
    });
    expect(lastList(api).get("device")).toBe("1001");
    expect(lastList(api).getAll("status")).toEqual([]);
  });

  it("ignores an unknown status and a device value that is no id, and names a device that is not listed", async () => {
    const { api } = await openOverview(reader, "/ingest?status=broken&device=x");
    await rows();
    expect(lastList(api).getAll("status")).toEqual(["failed", "running", "queued"]);
    expect(lastList(api).get("device")).toBeNull();
    cleanup();

    await openOverview(reader, "/ingest?device=4242");
    await waitFor(() => {
      expect(screen.getByTestId<HTMLSelectElement>("ingest-filter-device").selectedOptions[0]?.textContent).toBe(
        "Device no. 4242",
      );
    });
  });
});

describe("older attempts", () => {
  /** The sample jobs plus a later, ingested attempt (17) of version 71, whose failed attempt is job 15. */
  function withRetry(): IngestJob[] {
    return [
      job(17, "done", { step: "sections", page_count: 3, section_count: 5, finished_at: "2026-11-01T08:20:00Z" }),
      ...sampleJobs(),
    ];
  }

  it("by default leaves out a failed attempt that a later one has ingested", async () => {
    const { api } = await openOverview(reader, "/ingest", fakeIngestApi(withRetry()));

    await waitFor(() => {
      expect(screen.getAllByTestId("ingest-job").map((item) => item.dataset.job)).toEqual(["14", "13"]);
    });
    expect(lastList(api).get("latest")).toBe("true");
    expect(screen.queryAllByTestId("ingest-superseded")).toHaveLength(0);
  });

  it("the switch goes into the address, lists every attempt and marks the older one; Back restores", async () => {
    const { api, router } = await openOverview(manager, "/ingest", fakeIngestApi(withRetry()));
    await rows();

    fireEvent.click(screen.getByTestId("ingest-filter-older"));

    await waitFor(() => {
      expect(router.state.location.search).toBe("?older=1");
    });
    await waitFor(() => {
      expect(screen.getAllByTestId("ingest-job").map((item) => item.dataset.job)).toEqual(["15", "14", "13"]);
    });
    expect(lastList(api).get("latest")).toBeNull();
    expect(lastList(api).getAll("status")).toEqual(["failed", "running", "queued"]);
    expect(screen.getByTestId<HTMLInputElement>("ingest-filter-older").checked).toBe(true);
    expect(within(row(15)).getByTestId("ingest-superseded").textContent).toBe("Older attempt: this version has a newer job.");
    expect(within(row(15)).queryByTestId("ingest-retry")).toBeNull();
    expect(within(row(14)).queryByTestId("ingest-superseded")).toBeNull();

    await act(() => router.navigate(-1));
    await waitFor(() => {
      expect(screen.getAllByTestId("ingest-job").map((item) => item.dataset.job)).toEqual(["14", "13"]);
    });
    expect(screen.getByTestId<HTMLInputElement>("ingest-filter-older").checked).toBe(false);
    expect(lastList(api).get("latest")).toBe("true");
  });

  it("marks an older attempt by is_latest even when the newer job is not listed", async () => {
    await openOverview(manager, "/ingest?status=failed&older=1", fakeIngestApi(withRetry()));

    await waitFor(() => {
      expect(screen.getAllByTestId("ingest-job").map((item) => item.dataset.job)).toEqual(["15"]);
    });
    expect(within(row(15)).getByTestId("ingest-superseded")).toBeDefined();
    expect(within(row(15)).queryByTestId("ingest-retry")).toBeNull();
  });

  it("trusts is_latest from the API, not the order of the page", async () => {
    // Two jobs of different versions; the API says the first is not the newest of its version.
    const api = fakeIngestApi([job(31, "failed"), job(30, "failed", { version: { id: 72, number: 3, original_filename: "x.pdf" } })]);
    const original = api.handler;
    const handler: Handler = async (request) => {
      const answer = await original(request);
      if (new URL(request.url).pathname !== JOBS_PATH) {
        return answer;
      }
      const body = (await answer.json()) as { results: IngestJob[] };
      return jsonResponse({ ...body, results: body.results.map((item) => ({ ...item, is_latest: item.id !== 31 })) });
    };
    await openOverview(manager, "/ingest?older=1", { ...api, handler });
    await rows();

    expect(within(row(31)).getByTestId("ingest-superseded")).toBeDefined();
    expect(within(row(30)).queryByTestId("ingest-superseded")).toBeNull();
    expect(within(row(30)).getByTestId("ingest-retry")).toBeDefined();
  });

  it("is translated into German", async () => {
    await changeLanguage("de");
    await openOverview(manager, "/ingest?older=1", fakeIngestApi(withRetry()));
    await rows();

    expect(screen.getByTestId("ingest-filter").textContent).toContain("Auch ältere Versuche zeigen");
    expect(within(row(15)).getByTestId("ingest-superseded").textContent).toBe(
      "Älterer Versuch: Zu dieser Version gibt es einen neueren Auftrag.",
    );
  });
});

describe("table", () => {
  it("shows device, file with link, version, file name, status with step, message and times", async () => {
    await openOverview(reader);
    await rows();

    const failed = row(15);
    expect(within(failed).getByTestId("ingest-job-device").textContent).toBe("Test controllertest-plc-1");
    expect(within(failed).getByRole("link", { name: "Test controller" }).getAttribute("href")).toBe("/devices/1000");
    expect(within(failed).getByTestId("ingest-job-document-link").getAttribute("href")).toBe("/documents/7");
    expect(within(failed).getByTestId("ingest-job-document-link").textContent).toBe("Test manual");
    expect(within(failed).getByTestId("ingest-job-version").textContent).toBe("Version 2 · test-manual-v2.pdf");
    expect(within(failed).getByTestId("ingest-status").textContent).toBe("Error");
    expect(within(failed).getByTestId("ingest-error-message").textContent).toBe(
      "The converter (Docling) could not be reached. Please try again later.",
    );
    expect(within(failed).getByTestId("ingest-error-detail").textContent).toBe("converter not reachable after 5 attempts");
    expect(within(failed).getByTestId("ingest-job-times").textContent).toContain("Created: ");
    expect(within(failed).getByTestId("ingest-job-times").querySelectorAll("time")).toHaveLength(2);

    const running = row(14);
    expect(within(running).getByTestId("ingest-status").textContent).toBe("Ingesting: converting");
    expect(within(running).getByTestId("ingest-job-times").textContent).toContain("Finished: not yet");
    expect(within(row(13)).getByTestId("ingest-status").textContent).toBe("Queued");
  });

  it("wraps file names only at words, cuts them after two lines with the full name as tooltip, and keeps times on one line", async () => {
    const longName = "test-acceptance-protocol-of-the-controller-with-a-very-long-file-name-v2.pdf";
    const api = fakeIngestApi([job(21, "failed", { version: { id: 72, number: 3, original_filename: longName } })]);
    await openOverview(manager, "/ingest", api);
    await rows();

    const line = within(row(21)).getByTestId("ingest-job-version");
    expect(line.textContent).toBe(`Version 3 · ${longName}`);
    expect(line.getAttribute("title")).toBe(longName);
    expect(line.className).toContain("break-words");
    expect(line.className).toContain("line-clamp-2");
    expect(line.querySelector(".break-all")).toBeNull();
    expect(within(line).getByText("Version 3").className).toContain("whitespace-nowrap");
    expect(within(row(21)).getByTestId("ingest-job-times").className).toContain("whitespace-nowrap");
    expect(within(row(21)).getByTestId("ingest-job-requested-by").className).toContain("whitespace-nowrap");
  });

  it("a click on the file opens the file page", async () => {
    const { router } = await openOverview(reader);
    await rows();
    fireEvent.click(within(row(15)).getByTestId("ingest-job-document-link"));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/documents/7");
    });
  });

  it("renders error_detail, titles and file names only as text", async () => {
    const api = fakeIngestApi([
      job(20, "failed", {
        error_code: "internal",
        error_detail: '<img src=x onerror="alert(1)"><script>alert(2)</script>',
        document: { id: 7, title: "<b>bold</b>" },
        version: { id: 71, number: 2, original_filename: "<i>name</i>.pdf" },
      }),
    ]);
    await openOverview(reader, "/ingest", api);
    await rows();

    const item = row(20);
    expect(within(item).getByTestId("ingest-error-detail").textContent).toBe(
      '<img src=x onerror="alert(1)"><script>alert(2)</script>',
    );
    expect(within(item).getByTestId("ingest-job-document-link").textContent).toBe("<b>bold</b>");
    expect(within(item).getByTestId("ingest-job-version").textContent).toBe("Version 2 · <i>name</i>.pdf");
    expect(item.querySelector("img, script, b, i")).toBeNull();
  });

  it("is translated into German", async () => {
    await changeLanguage("de");
    await openOverview(manager);
    await rows();

    expect((await screen.findByRole("heading", { level: 1 })).textContent).toBe("Einlesen");
    expect(screen.getAllByRole("columnheader").map((cell) => cell.textContent)).toEqual([
      "Gerät",
      "Datei",
      "Status",
      "Zeitpunkte",
      "Angestoßen von",
    ]);
    expect(within(row(15)).getByTestId("ingest-status").textContent).toBe("Fehler");
    expect(within(row(15)).getByTestId("ingest-error-message").textContent).toBe(
      "Der Umwandlungsdienst (Docling) war nicht erreichbar. Bitte später erneut versuchen.",
    );
    expect(within(row(14)).getByTestId("ingest-status").textContent).toBe("Wird eingelesen: Umwandeln");
    expect(within(row(14)).getByTestId("ingest-job-times").textContent).toContain("Beendet: noch nicht");
    expect(within(row(14)).getByTestId("ingest-job-requested-by").textContent).toBe("System");
    expect(screen.getByTestId("ingest-page-status").textContent).toBe("Seite 1 von 1");
    expect(screen.getByTestId("ingest-total").textContent).toBe("Aufträge: 3");
  });
});

describe("states of the list", () => {
  it("shows the loading state until the list arrives", async () => {
    let answer: (response: Response) => void = () => undefined;
    const pending = new Promise<Response>((resolve) => {
      answer = resolve;
    });
    const structure = fakeStructureApi().handler;
    fakeApi(reader, (request) => (new URL(request.url).pathname === JOBS_PATH ? pending : structure(request)));
    renderApp("/ingest");

    expect(await screen.findByTestId("loading")).toBeDefined();
    answer(jsonResponse({ count: 0, next: null, previous: null, results: [] }));
    expect(await screen.findByTestId("ingest-empty")).toBeDefined();
  });

  it("says that nothing is open when there is no failed, running or queued job", async () => {
    await openOverview(reader, "/ingest", fakeIngestApi(sampleJobs().filter((item) => item.status === "done")));
    expect((await screen.findByTestId("ingest-empty")).textContent).toBe(
      "Nothing open: no job has failed, none is running or queued.",
    );
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("says that no job matches a filter", async () => {
    await openOverview(reader, "/ingest?status=failed&device=1001");
    expect((await screen.findByTestId("ingest-empty")).textContent).toBe("No ingest job matches this filter.");
  });

  it("shows an error of the API", async () => {
    await openOverview(reader, "/ingest", fakeIngestApi([], () => jsonResponse({ detail: "Server error" }, 500)));
    expect((await screen.findByTestId("error-summary")).textContent).toContain("500");
    expect(screen.queryByTestId("ingest-jobs")).toBeNull();
  });
});

describe("pages", () => {
  function manyJobs(count: number): IngestJob[] {
    return Array.from({ length: count }, (_, index) =>
      job(1000 - index, "failed", {
        error_code: "timeout",
        version: { id: 5000 - index, number: 1, original_filename: `file-${String(index)}.pdf` },
      }),
    );
  }

  it("shows 50 jobs per page with previous and next", async () => {
    const { api } = await openOverview(reader, "/ingest", fakeIngestApi(manyJobs(120)));
    expect(await rows()).toHaveLength(50);
    expect(screen.getByTestId("ingest-page-status").textContent).toBe("Page 1 of 3");
    expect(screen.getByTestId("ingest-total").textContent).toBe("Jobs: 120");
    expect(screen.getByTestId<HTMLButtonElement>("ingest-previous").disabled).toBe(true);

    fireEvent.click(screen.getByTestId("ingest-next"));
    await waitFor(() => {
      expect(screen.getByTestId("ingest-page-status").textContent).toBe("Page 2 of 3");
    });
    expect(lastList(api).get("page")).toBe("2");
    expect(row(950)).toBeDefined();

    fireEvent.click(screen.getByTestId("ingest-next"));
    await waitFor(() => {
      expect(screen.getByTestId("ingest-page-status").textContent).toBe("Page 3 of 3");
    });
    expect(screen.getAllByTestId("ingest-job")).toHaveLength(20);
    expect(screen.getByTestId<HTMLButtonElement>("ingest-next").disabled).toBe(true);

    fireEvent.click(screen.getByTestId("ingest-previous"));
    await waitFor(() => {
      expect(screen.getByTestId("ingest-page-status").textContent).toBe("Page 2 of 3");
    });
  });

  it("a new filter starts again on page 1", async () => {
    const { api } = await openOverview(reader, "/ingest", fakeIngestApi(manyJobs(120)));
    await rows();
    fireEvent.click(screen.getByTestId("ingest-next"));
    await waitFor(() => {
      expect(screen.getByTestId("ingest-page-status").textContent).toBe("Page 2 of 3");
    });

    fireEvent.change(screen.getByTestId("ingest-filter-status"), { target: { value: "failed" } });
    await waitFor(() => {
      expect(screen.getByTestId("ingest-page-status").textContent).toBe("Page 1 of 3");
    });
    expect(lastList(api).get("page")).toBeNull();
    expect(lastList(api).getAll("status")).toEqual(["failed"]);
  });
});

describe("roles", () => {
  it("a reader sees no button and no column 'started by'", async () => {
    await openOverview(reader, "/ingest?status=all");
    await rows();

    expect(screen.queryAllByTestId("ingest-retry")).toHaveLength(0);
    expect(screen.queryByTestId("ingest-column-requested-by")).toBeNull();
    expect(screen.queryAllByTestId("ingest-job-requested-by")).toHaveLength(0);
    expect(screen.getAllByRole("columnheader").map((cell) => cell.textContent)).toEqual([
      "Device",
      "File",
      "Status",
      "Times",
    ]);
  });

  it("a manager sees who started a job (System for none) and the button on every job that is not active", async () => {
    await openOverview(manager, "/ingest?status=all");
    await rows();

    expect(screen.getByTestId("ingest-column-requested-by").textContent).toBe("Started by");
    expect(within(row(15)).getByTestId("ingest-job-requested-by").textContent).toBe("test-manager");
    expect(within(row(14)).getByTestId("ingest-job-requested-by").textContent).toBe("System");
    for (const id of [15, 12, 11]) {
      expect(within(row(id)).getByRole("button", { name: /^Ingest version \d+ again$/ }).textContent).toBe("Ingest again");
    }
    for (const id of [14, 13]) {
      expect(within(row(id)).queryByTestId("ingest-retry")).toBeNull();
    }
  });

  it("ingests again and lists the new job in place of the older attempt", async () => {
    const { api } = await openOverview(manager);
    await rows();
    const before = api.lists.length;

    fireEvent.click(within(row(15)).getByTestId("ingest-retry"));

    await waitFor(() => {
      expect(api.ingests).toEqual([71]);
    });
    await waitFor(() => {
      expect(screen.getAllByTestId("ingest-job").map((item) => item.dataset.job)).toEqual(["16", "14", "13"]);
    });
    expect(api.lists.length).toBeGreaterThan(before);
    expect(within(row(16)).getByTestId("ingest-status").textContent).toBe("Queued");
    expect(within(row(16)).queryByTestId("ingest-retry")).toBeNull();
  });

  it("with older attempts shown, ingests again, lists the new job and marks the older attempt", async () => {
    const { api } = await openOverview(manager, "/ingest?older=1");
    await rows();

    fireEvent.click(within(row(15)).getByTestId("ingest-retry"));

    await waitFor(() => {
      expect(api.ingests).toEqual([71]);
    });
    await waitFor(() => {
      expect(screen.getAllByTestId("ingest-job").map((item) => item.dataset.job)).toEqual(["16", "15", "14", "13"]);
    });
    expect(within(row(16)).getByTestId("ingest-status").textContent).toBe("Queued");
    expect(within(row(16)).queryByTestId("ingest-retry")).toBeNull();
    expect(within(row(15)).queryByTestId("ingest-retry")).toBeNull();
    expect(within(row(15)).getByTestId("ingest-superseded").textContent).toBe(
      "Older attempt: this version has a newer job.",
    );
  });
});

describe("polling", () => {
  it("asks again every 5 seconds while a listed job is queued or running and stops when none is", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { api } = await openOverview(reader);
    await rows();
    expect(screen.getByTestId("ingest-polling").textContent).toBe("Jobs are running: the list updates every 5 seconds.");
    const first = api.lists.length;

    // The running job ends, the queued one starts.
    const running = api.jobs.find((item) => item.id === 14);
    const queued = api.jobs.find((item) => item.id === 13);
    if (running === undefined || queued === undefined) {
      throw new Error("sample jobs missing");
    }
    running.status = "done";
    queued.status = "running";
    queued.step = "sections";
    await act(() => vi.advanceTimersByTimeAsync(5000));
    await waitFor(() => {
      expect(screen.getAllByTestId("ingest-job").map((item) => item.dataset.job)).toEqual(["15", "13"]);
    });
    expect(within(row(13)).getByTestId("ingest-status").textContent).toBe("Ingesting: building sections");
    expect(api.lists.length).toBe(first + 1);

    queued.status = "done";
    await act(() => vi.advanceTimersByTimeAsync(5000));
    await waitFor(() => {
      expect(screen.getAllByTestId("ingest-job").map((item) => item.dataset.job)).toEqual(["15"]);
    });
    const afterDone = api.lists.length;
    expect(afterDone).toBe(first + 2);
    expect(screen.queryByTestId("ingest-polling")).toBeNull();

    await act(() => vi.advanceTimersByTimeAsync(30_000));
    expect(api.lists.length).toBe(afterDone);
  });

  it("does not poll when no listed job is active", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { api } = await openOverview(reader, "/ingest?status=failed");
    await rows();
    const first = api.lists.length;
    expect(screen.queryByTestId("ingest-polling")).toBeNull();

    await act(() => vi.advanceTimersByTimeAsync(30_000));
    expect(api.lists.length).toBe(first);
  });
});

describe("navigation entry", () => {
  it.each([
    ["reader", reader],
    ["manager", manager],
  ] as const)("is shown to a %s with its own icon and marked on the page", async (_name, user) => {
    await openOverview(user);
    const navigation = screen.getByRole("navigation", { name: "Main navigation" });
    const link = within(navigation).getByRole("link", { name: "Ingestion" });
    expect(link.getAttribute("href")).toBe("/ingest");
    expect(link.getAttribute("aria-current")).toBe("page");
    expect(link.querySelector("svg")?.getAttribute("data-icon")).toBe("ingest");
    expect(screen.queryByTestId("no-permission")).toBeNull();
  });
});
