import { QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { installClientConfig } from "../api/client.ts";
import { installApiErrorHandling } from "../api/errors.ts";
import type { AuditLogEntry, PaginatedAuditLogEntryList } from "../api/generated";
import { createQueryClient } from "../api/queryClient.ts";
import { changeLanguage } from "../i18n.ts";
import { type FakeApi, fakeApi, jsonResponse, manager } from "../test/fakeApi.ts";
import { fakeMatchMedia } from "../test/fakeMatchMedia.ts";
import { WIDE_TABLE_QUERY } from "./ui/ResponsiveTable.tsx";
import { AUDIT_PAGE_SIZE, AuditTrail, type AuditTrailProps } from "./AuditTrail.tsx";

const AUDIT_LOG = "/api/v1/audit-log/";
const TIMESTAMP = "2026-11-21T12:00:00.123456Z";

afterEach(async () => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  await changeLanguage("en");
  window.localStorage.clear();
});

function entry(id: number, fields: Partial<AuditLogEntry> = {}): AuditLogEntry {
  return {
    id,
    timestamp: TIMESTAMP,
    actor: "test-manager",
    action: "update",
    object_type: "assets.device",
    object_id: 7,
    object_repr: `test-device-${String(id)}`,
    changes: { name: ["old name", "new name"] },
    ...fields,
  };
}

function pageOf(results: AuditLogEntry[], count = results.length, next: string | null = null): PaginatedAuditLogEntryList {
  return { count, next, previous: null, results };
}

/** Fakes the API: the audit log answers with `answer(query)`. */
function auditApi(answer: (query: URLSearchParams) => Response | Promise<Response>): FakeApi {
  return fakeApi(manager, (request) => {
    const url = new URL(request.url);
    if (url.pathname === AUDIT_LOG) {
      return answer(url.searchParams);
    }
    return jsonResponse({ detail: "Not found." }, 404);
  });
}

function renderTrail(props: AuditTrailProps = {}): { rerender: (props: AuditTrailProps) => void } {
  installClientConfig();
  installApiErrorHandling();
  const queryClient = createQueryClient();
  const result = render(
    <QueryClientProvider client={queryClient}>
      <AuditTrail {...props} />
    </QueryClientProvider>,
  );
  return {
    rerender: (next) => {
      result.rerender(
        <QueryClientProvider client={queryClient}>
          <AuditTrail {...next} />
        </QueryClientProvider>,
      );
    },
  };
}

function queryOf(api: FakeApi, index: number): Record<string, string> {
  const request = api.requestsTo(AUDIT_LOG)[index];
  if (request === undefined) {
    throw new Error(`no request ${String(index)} to the audit log`);
  }
  return Object.fromEntries(new URL(request.url).searchParams);
}

async function rows(): Promise<HTMLElement[]> {
  await screen.findByTestId("audit-trail");
  return screen.queryAllByTestId("audit-entry");
}

function cell(row: HTMLElement, testId: string): HTMLElement {
  return within(row).getByTestId(testId);
}

describe("showing entries", () => {
  it("shows time, user, action, object type, object and the changed fields with old and new value", async () => {
    auditApi(() => jsonResponse(pageOf([entry(1)])));
    renderTrail();

    const [row] = await rows();
    if (row === undefined) {
      throw new Error("no row");
    }
    const expectedTime = new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "medium" }).format(
      new Date(TIMESTAMP),
    );
    expect(cell(row, "audit-timestamp").textContent).toBe(expectedTime);
    expect(cell(row, "audit-timestamp").textContent).toContain("2026");
    expect(within(row).getByTestId("audit-timestamp").querySelector("time")?.getAttribute("datetime")).toBe(
      "2026-11-21T12:00:00.123Z",
    );
    expect(cell(row, "audit-actor").textContent).toBe("test-manager");
    expect(cell(row, "audit-action").textContent).toBe("Changed");
    expect(cell(row, "audit-object-type").textContent).toBe("Device");
    expect(cell(row, "audit-object").textContent).toBe("test-device-1ID 7");
    expect(cell(row, "audit-change-list").textContent).toBe("Name: old name → new name");
    expect(cell(row, "audit-change-field").getAttribute("title")).toBe("name");
    expect(screen.getByRole("table", { name: "Changes" })).toBeDefined();
    expect(screen.getAllByRole("columnheader").map((header) => header.textContent)).toEqual([
      "Time",
      "User",
      "Action",
      "Object type",
      "Object",
      "Changes",
    ]);
  });

  it("translates every action and every object type of the change log", async () => {
    const types = [
      ["assets.site", "Site"],
      ["assets.area", "Area"],
      ["assets.plant", "Plant"],
      ["assets.device", "Device"],
      ["files.document", "File"],
      ["files.documentversion", "File version"],
      ["accounts.user", "User"],
    ] as const;
    const actions = [
      ["create", "Created"],
      ["update", "Changed"],
      ["delete", "Deleted"],
    ] as const;
    const entries = types.map(([type], index) =>
      entry(index + 1, { object_type: type, action: actions[index % actions.length]?.[0] ?? "update" }),
    );
    auditApi(() => jsonResponse(pageOf(entries)));
    renderTrail();

    const shown = await rows();
    expect(shown.map((row) => cell(row, "audit-object-type").textContent)).toEqual(types.map(([, text]) => text));
    expect(shown.map((row) => cell(row, "audit-action").textContent)).toEqual(
      types.map((_, index) => actions[index % actions.length]?.[1]),
    );
  });

  it("shows created and deleted values, role changes, a missing user and times inside the changes", async () => {
    auditApi(() =>
      jsonResponse(
        pageOf([
          entry(1, {
            action: "create",
            actor: null,
            changes: {
              id: [null, 7],
              name: [null, "test-device"],
              notes: [null, ""],
              ip_address: [null, null],
              created_at: [null, "2026-11-21 12:00:00.5"],
            },
          }),
          entry(2, {
            action: "delete",
            changes: { name: ["test-device", null], enabled: [true, false] },
          }),
          entry(3, {
            object_type: "accounts.user",
            object_repr: "test-user",
            changes: { groups: { type: "m2m", operation: "add", objects: ["manage"] } },
          }),
          entry(4, {
            object_type: "accounts.user",
            changes: { groups: { type: "m2m", operation: "delete", objects: ["read", "manage"] } },
          }),
          entry(5, { changes: { notes: [null, ""] } }),
        ]),
      ),
    );
    renderTrail();

    const [created, deleted, added, removed, nothing] = await rows();
    if (
      created === undefined ||
      deleted === undefined ||
      added === undefined ||
      removed === undefined ||
      nothing === undefined
    ) {
      throw new Error("missing rows");
    }
    expect(cell(created, "audit-actor").textContent).toBe("System (no signed-in user)");
    const createdChanges = within(cell(created, "audit-change-list")).getAllByTestId("audit-change");
    // Fields that are empty before and after (notes, ip_address) are left out;
    // the id is a technical field and stands under "Technical details".
    expect(
      within(cell(created, "audit-change-list"))
        .getAllByTestId("audit-change-field")
        .map((field) => field.getAttribute("data-field")),
    ).toEqual(["name", "created_at"]);
    expect(createdChanges[0]?.textContent).toBe("Name: (empty) → test-device");
    expect(
      within(cell(created, "audit-technical-list"))
        .getAllByTestId("audit-change")
        .map((change) => change.textContent),
    ).toEqual(["ID: (empty) → 7"]);
    const time = createdChanges[1]?.querySelector("time");
    expect(time?.getAttribute("datetime")).toBe("2026-11-21T12:00:00.500Z");
    expect(time?.getAttribute("title")).toBe("2026-11-21 12:00:00.5");
    expect(time?.textContent).toBe(
      new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "medium" }).format(
        new Date("2026-11-21T12:00:00.5Z"),
      ),
    );

    expect(cell(deleted, "audit-action").textContent).toBe("Deleted");
    expect(within(deleted).getAllByTestId("audit-change").map((change) => change.textContent)).toEqual([
      "Name: test-device → (empty)",
      "enabled: true → false",
    ]);
    expect(cell(added, "audit-change-list").textContent).toBe("Groups: added manage");
    expect(cell(removed, "audit-change-list").textContent).toBe("Groups: removed read, manage");
    expect(cell(nothing, "audit-no-changes").textContent).toBe("No field values");
    expect(within(nothing).queryByTestId("audit-change")).toBeNull();
    // Nothing is lost: the raw data keeps the pairs left out above.
    expect(JSON.parse(cell(nothing, "audit-raw").textContent)).toEqual({ notes: [null, ""] });
    expect(JSON.parse(cell(created, "audit-raw").textContent)).toEqual({
      id: [null, 7],
      name: [null, "test-device"],
      notes: [null, ""],
      ip_address: [null, null],
      created_at: [null, "2026-11-21 12:00:00.5"],
    });
  });

  it("shows an object type or a value it does not know as it came", async () => {
    auditApi(() =>
      jsonResponse(
        pageOf([
          entry(1, {
            object_type: "other.thing",
            object_id: null,
            changes: { data: [{ a: 1 }, [1, 2]] } as unknown as AuditLogEntry["changes"],
          }),
        ]),
      ),
    );
    renderTrail();

    const [row] = await rows();
    if (row === undefined) {
      throw new Error("no row");
    }
    expect(cell(row, "audit-object-type").textContent).toBe("other.thing");
    expect(cell(row, "audit-object").textContent).toBe("test-device-1");
    expect(cell(row, "audit-change-list").textContent).toBe('data: {"a":1} → [1,2]');
    expect(cell(row, "audit-change-field").tagName).toBe("CODE");
  });

  it("renders names and values as text, never as HTML", async () => {
    const markup = '<img src="x" onerror="window.hacked=1">';
    auditApi(() =>
      jsonResponse(
        pageOf([
          entry(1, {
            actor: "<b>user</b>",
            object_repr: markup,
            changes: { "<i>field</i>": ["<script>1</script>", markup] },
          }),
        ]),
      ),
    );
    renderTrail();

    const [row] = await rows();
    if (row === undefined) {
      throw new Error("no row");
    }
    expect(cell(row, "audit-actor").textContent).toBe("<b>user</b>");
    expect(cell(row, "audit-object").textContent).toContain(markup);
    expect(cell(row, "audit-change-list").textContent).toBe(`<i>field</i>: <script>1</script> → ${markup}`);
    expect(cell(row, "audit-raw").textContent).toContain("<script>1</script>");
    expect(row.querySelector("img, b, i, script")).toBeNull();
  });

  it("shows time, action and object type in German", async () => {
    await changeLanguage("de");
    auditApi(() => jsonResponse(pageOf([entry(1, { changes: { name: [null, "x"] } })])));
    renderTrail();

    const [row] = await rows();
    if (row === undefined) {
      throw new Error("no row");
    }
    expect(cell(row, "audit-timestamp").textContent).toContain("21.11.2026");
    expect(cell(row, "audit-action").textContent).toBe("Geändert");
    expect(cell(row, "audit-object-type").textContent).toBe("Gerät");
    expect(cell(row, "audit-change-list").textContent).toBe("Name: (leer) → x");
    expect(cell(row, "audit-technical").querySelector("summary")?.textContent).toBe("Technische Angaben");
    expect(screen.getByRole("table", { name: "Änderungen" })).toBeDefined();
    expect(screen.getByTestId("audit-page-status").textContent).toBe("Seite 1 von 1");
  });

  it("folds technical fields and the raw data away under Technical details", async () => {
    const sha = "0123456789abcdef".repeat(4);
    const blobKey = `versions/${sha}`;
    const changes = {
      id: [null, 70],
      document: [null, 7],
      number: [null, 1],
      blob_key: [null, blobKey],
      sha256: [null, sha],
      size: [null, 512],
      original_filename: [null, "test-file.txt"],
      uploaded_by: [null, 2],
    };
    auditApi(() =>
      jsonResponse(
        pageOf([
          entry(1, {
            action: "create",
            object_type: "files.documentversion",
            changes: changes as unknown as AuditLogEntry["changes"],
          }),
        ]),
      ),
    );
    renderTrail();

    const [row] = await rows();
    if (row === undefined) {
      throw new Error("no row");
    }
    // Translated names for what a person reads first.
    expect(
      within(cell(row, "audit-change-list"))
        .getAllByTestId("audit-change")
        .map((change) => change.textContent),
    ).toEqual([
      "Version number: (empty) → 1",
      "Size in bytes: (empty) → 512",
      "File name: (empty) → test-file.txt",
    ]);
    // id, storage key, checksum and the ids of other objects: folded away.
    const technical = cell(row, "audit-technical");
    expect(technical.tagName).toBe("DETAILS");
    expect(technical.hasAttribute("open")).toBe(false);
    expect(technical.querySelector("summary")?.textContent).toBe("Technical details");
    expect(
      within(technical)
        .getAllByTestId("audit-change-field")
        .map((field) => field.getAttribute("data-field")),
    ).toEqual(["id", "document", "blob_key", "sha256", "uploaded_by"]);
    // Hashes are cut like the checksums of the file table; the full value is the tooltip.
    const technicalChanges = within(technical).getAllByTestId("audit-change");
    const checksum = technicalChanges.find((change) => change.textContent.startsWith("Checksum (SHA-256): "));
    expect(checksum?.textContent).toBe(`Checksum (SHA-256): (empty) → ${sha.slice(0, 12)}…`);
    expect(checksum?.querySelector(`[title="${sha}"]`)).not.toBeNull();
    const key = technicalChanges.find((change) => change.textContent.startsWith("Storage key: "));
    expect(key?.textContent).toBe(`Storage key: (empty) → versions/${sha.slice(0, 12)}…`);
    expect(key?.querySelector(`[title="${blobKey}"]`)).not.toBeNull();
    expect(technicalChanges.find((change) => change.textContent.startsWith("Uploaded by (ID): "))?.textContent).toBe(
      "Uploaded by (ID): (empty) → 2",
    );
    // The raw data keeps every value complete.
    expect(JSON.parse(cell(row, "audit-raw").textContent)).toEqual(changes);
    // One field per line.
    expect(cell(row, "audit-raw").textContent.split("\n")).toContain(`  "sha256": [null,"${sha}"],`);
    const summary = technical.querySelector("summary");
    if (summary === null) {
      throw new Error("no summary");
    }
    fireEvent.click(summary);
    expect(technical.hasAttribute("open")).toBe(true);
  });

  it("shows only Technical details when an entry changed nothing but technical fields", async () => {
    auditApi(() => jsonResponse(pageOf([entry(1, { changes: { plant: [3, 4] } })])));
    renderTrail();

    const [row] = await rows();
    if (row === undefined) {
      throw new Error("no row");
    }
    expect(within(row).queryByTestId("audit-change-list")).toBeNull();
    expect(within(row).queryByTestId("audit-no-changes")).toBeNull();
    expect(cell(row, "audit-technical-list").textContent).toBe("Plant (ID): 3 → 4");
  });

  it("keeps time, user, action and object type on one line", async () => {
    auditApi(() => jsonResponse(pageOf([entry(1)])));
    renderTrail();

    const [row] = await rows();
    if (row === undefined) {
      throw new Error("no row");
    }
    for (const name of ["audit-timestamp", "audit-actor", "audit-action", "audit-object-type"]) {
      expect(cell(row, name).className).toContain("whitespace-nowrap");
    }
  });

  it("says so when there are no entries", async () => {
    auditApi(() => jsonResponse(pageOf([])));
    renderTrail();

    expect((await screen.findByTestId("audit-empty")).textContent).toBe("No entries found.");
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.getByTestId("audit-page-status").textContent).toBe("Page 1 of 1");
    expect(screen.getByRole("button", { name: "Next page" }).hasAttribute("disabled")).toBe(true);
  });
});

describe("pages", () => {
  /** 120 entries: pages 1 and 2 hold 50, page 3 holds 20. */
  function threePages(query: URLSearchParams): Response {
    const page = Number(query.get("page") ?? "1");
    const first = (page - 1) * AUDIT_PAGE_SIZE + 1;
    const size = page < 3 ? AUDIT_PAGE_SIZE : 20;
    const results = Array.from({ length: size }, (_, index) => entry(first + index));
    const next = page < 3 ? `http://localhost${AUDIT_LOG}?page=${String(page + 1)}` : null;
    return jsonResponse(pageOf(results, 120, next));
  }

  it("goes forward and back one page at a time, like the API", async () => {
    const api = auditApi(threePages);
    renderTrail();

    expect(await rows()).toHaveLength(50);
    expect(screen.getByTestId("audit-page-status").textContent).toBe("Page 1 of 3");
    expect(screen.getByTestId("audit-total").textContent).toBe("120 entries found");
    const previous = screen.getByRole("button", { name: "Previous page" });
    const next = screen.getByRole("button", { name: "Next page" });
    expect(previous.hasAttribute("disabled")).toBe(true);
    expect(queryOf(api, 0)).toEqual({});

    fireEvent.click(next);
    expect(await screen.findByText("Page 2 of 3")).toBeDefined();
    expect(await screen.findByText("test-device-51")).toBeDefined();
    expect(queryOf(api, 1)).toEqual({ page: "2" });

    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(await screen.findByText("Page 3 of 3")).toBeDefined();
    expect(await screen.findByText("test-device-120")).toBeDefined();
    expect(screen.getAllByTestId("audit-entry")).toHaveLength(20);
    expect(screen.getByRole("button", { name: "Next page" }).hasAttribute("disabled")).toBe(true);
    expect(queryOf(api, 2)).toEqual({ page: "3" });

    fireEvent.click(screen.getByRole("button", { name: "Previous page" }));
    expect(await screen.findByText("Page 2 of 3")).toBeDefined();
    expect(await screen.findByText("test-device-51")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "Previous page" }));
    expect(await screen.findByText("Page 1 of 3")).toBeDefined();
    expect(await screen.findByText("test-device-1")).toBeDefined();
    expect(screen.getByRole("button", { name: "Previous page" }).hasAttribute("disabled")).toBe(true);
    expect(queryOf(api, api.requestsTo(AUDIT_LOG).length - 1)).toEqual({});
  });

  it("keeps the shown page while the next one loads", async () => {
    let release: () => void = () => undefined;
    const api = auditApi((query) => {
      if (query.get("page") === "2") {
        return new Promise<Response>((resolve) => {
          release = () => {
            resolve(threePages(query));
          };
        });
      }
      return threePages(query);
    });
    renderTrail();
    await rows();

    fireEvent.click(screen.getByRole("button", { name: "Next page" }));

    await vi.waitFor(() => {
      expect(api.requestsTo(AUDIT_LOG)).toHaveLength(2);
    });
    expect(screen.getByText("test-device-1")).toBeDefined();
    expect(screen.getByTestId("audit-page-status").textContent).toBe("Page 1 of 3");
    expect(screen.getByTestId("audit-trail").getAttribute("aria-busy")).toBe("true");
    expect(screen.getByRole("button", { name: "Next page" }).hasAttribute("disabled")).toBe(true);
    act(() => {
      release();
    });
    expect(await screen.findByText("Page 2 of 3")).toBeDefined();
    expect(screen.getByText("test-device-51")).toBeDefined();
    expect(screen.getByTestId("audit-trail").getAttribute("aria-busy")).toBe("false");
  });
});

describe("filters", () => {
  it("asks only for the entries of one object", async () => {
    const api = auditApi(() => jsonResponse(pageOf([entry(1)])));
    renderTrail({ objectType: "assets.device", objectId: 7 });
    await rows();

    expect(queryOf(api, 0)).toEqual({ object_type: "assets.device", object_id: "7" });
  });

  it("asks for the entries of one user", async () => {
    const api = auditApi(() => jsonResponse(pageOf([entry(1)])));
    renderTrail({ actor: "test-manager" });
    await rows();

    expect(queryOf(api, 0)).toEqual({ actor: "test-manager" });
  });

  it("starts again on page 1 when a filter changes", async () => {
    const api = auditApi((query) =>
      jsonResponse(pageOf([entry(Number(query.get("page") ?? "1"))], 60, query.has("page") ? null : "next")),
    );
    const { rerender } = renderTrail({ objectType: "assets.device" });
    await rows();
    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(await screen.findByText("Page 2 of 2")).toBeDefined();

    rerender({ objectType: "assets.site" });

    expect(await screen.findByText("Page 1 of 2")).toBeDefined();
    expect(queryOf(api, 2)).toEqual({ object_type: "assets.site" });
  });
});

describe("result count (work order 089)", () => {
  it("announces the number of entries in one live region that stays while a new filter loads", async () => {
    let release: () => void = () => undefined;
    auditApi((query) => {
      if (query.get("object_type") === "assets.site") {
        return new Promise<Response>((resolve) => {
          release = () => {
            resolve(jsonResponse(pageOf([], 0)));
          };
        });
      }
      return jsonResponse(pageOf([entry(1), entry(2)], 120, "next"));
    });
    const { rerender } = renderTrail({ objectType: "assets.device" });

    const region = screen.getByTestId("audit-result-count");
    expect(region.getAttribute("role")).toBe("status");
    // Empty until the list has loaded, then the number of all pages.
    expect(region.textContent).toBe("");
    await rows();
    expect(region.textContent).toBe("120 entries found");
    expect(within(region).getByTestId("audit-total").className).toContain("text-fg-muted");

    // A new filter: the same region empties while loading and then says "none".
    rerender({ objectType: "assets.site" });
    expect(await screen.findByTestId("loading")).toBeDefined();
    expect(screen.getByTestId("audit-result-count")).toBe(region);
    expect(region.textContent).toBe("");
    await act(async () => {
      release();
      await Promise.resolve();
    });
    expect((await within(region).findByTestId("audit-empty")).textContent).toBe("No entries found.");
    expect(screen.getByTestId("audit-result-count")).toBe(region);
  });

  it("keeps the number while turning pages", async () => {
    auditApi((query) =>
      jsonResponse(pageOf([entry(Number(query.get("page") ?? "1"))], 60, query.has("page") ? null : "next")),
    );
    renderTrail();
    await rows();
    const region = screen.getByTestId("audit-result-count");
    expect(region.textContent).toBe("60 entries found");

    fireEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(await screen.findByText("Page 2 of 2")).toBeDefined();
    expect(screen.getByTestId("audit-result-count")).toBe(region);
    expect(region.textContent).toBe("60 entries found");
  });

  it("counts in the singular and in German", async () => {
    auditApi(() => jsonResponse(pageOf([entry(1)], 1)));
    renderTrail();
    await rows();
    expect(screen.getByTestId("audit-result-count").textContent).toBe("1 entry found");

    cleanup();
    await changeLanguage("de");
    auditApi(() => jsonResponse(pageOf([entry(1), entry(2)], 1234)));
    renderTrail();
    await rows();
    expect(screen.getByTestId("audit-result-count").textContent).toBe("1.234 Einträge gefunden");
  });
});

describe("errors", () => {
  it("shows a 403 of the API as missing permission", async () => {
    auditApi(() => jsonResponse({ detail: "You do not have permission to perform this action." }, 403));
    renderTrail();

    expect((await screen.findByTestId("error-summary")).textContent).toBe(
      "You do not have permission for this page or action.",
    );
    expect(screen.getByRole("alert")).toBeDefined();
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.queryByTestId("audit-trail")).toBeNull();
  });

  it("shows other HTTP errors with their status", async () => {
    auditApi(() => jsonResponse({ detail: "Invalid page." }, 404));
    renderTrail();

    expect((await screen.findByTestId("error-summary")).textContent).toBe("The API answered with HTTP status 404.");
    expect(screen.getByTestId("error-detail").textContent).toBe("Invalid page.");
  });
});

describe("narrow screens (work order 081)", () => {
  it("lists the entries as cards below 768 px: object as heading, action, then time, user, object type and changes", async () => {
    fakeMatchMedia({ [WIDE_TABLE_QUERY]: false });
    auditApi(() =>
      jsonResponse(pageOf([entry(2, { changes: { name: ["old name", "new name"], id: [null, 7] } }), entry(1)])),
    );
    renderTrail();
    const [first] = await rows();
    if (first === undefined) {
      throw new Error("card missing");
    }

    expect(screen.queryByRole("table")).toBeNull();
    const list = screen.getByRole("list", { name: "Changes" });
    // Two cards; the changed fields inside them are lists of their own.
    expect(Array.from(list.children).map((item) => item.tagName)).toEqual(["LI", "LI"]);
    // On /audit the page heading (h1) is the only heading above the list.
    expect(within(list).getAllByRole("heading", { level: 2 }).map((heading) => heading.textContent)).toEqual([
      "test-device-2ID 7",
      "test-device-1ID 7",
    ]);
    expect(first.tagName).toBe("LI");
    expect(cell(first, "audit-action").textContent).toBe("Action: Changed");
    expect(Array.from(first.querySelectorAll("dt")).map((term) => term.textContent)).toEqual([
      "Time",
      "User",
      "Object type",
      "Changes",
    ]);
    expect(cell(first, "audit-timestamp").querySelector("time")?.getAttribute("dateTime")).toBe("2026-11-21T12:00:00.123Z");
    expect(cell(first, "audit-actor").textContent).toBe("test-manager");
    expect(cell(first, "audit-object-type").textContent).toBe("Device");
    // The changes take the full width of the card; technical details and raw data stay folded away.
    const changes = cell(first, "audit-changes");
    expect(changes.parentElement?.className).toContain("col-span-2");
    expect(within(changes).getAllByTestId("audit-change-field").map((field) => field.textContent)).toEqual(["Name", "ID"]);
    expect(within(changes).getByTestId("audit-technical").hasAttribute("open")).toBe(false);
    expect(within(changes).getByTestId("audit-raw").textContent).toContain('"id": [null,7]');
  });

  it("uses the heading level the caller asks for", async () => {
    fakeMatchMedia({ [WIDE_TABLE_QUERY]: false });
    auditApi(() => jsonResponse(pageOf([entry(1)])));
    renderTrail({ cardHeadingLevel: 3, label: "Test history" });
    await rows();

    const list = screen.getByRole("list", { name: "Test history" });
    expect(within(list).getAllByRole("heading", { level: 3 })).toHaveLength(1);
    expect(within(list).queryByRole("heading", { level: 2 })).toBeNull();
  });

  it("names the pairs in German", async () => {
    fakeMatchMedia({ [WIDE_TABLE_QUERY]: false });
    await changeLanguage("de");
    auditApi(() => jsonResponse(pageOf([entry(1)])));
    renderTrail();
    const [first] = await rows();
    if (first === undefined) {
      throw new Error("card missing");
    }

    expect(screen.getByRole("list", { name: "Änderungen" })).toBeDefined();
    expect(Array.from(first.querySelectorAll("dt")).map((term) => term.textContent)).toEqual([
      "Zeitpunkt",
      "Benutzer",
      "Objektart",
      "Änderungen",
    ]);
  });
});
