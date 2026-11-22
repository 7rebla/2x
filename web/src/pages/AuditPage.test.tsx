import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AuditLogEntry, PaginatedAuditLogEntryList } from "../api/generated";
import { changeLanguage } from "../i18n.ts";
import { type FakeApi, fakeApi, jsonResponse, manager, reader } from "../test/fakeApi.ts";
import { renderApp } from "../test/renderApp.tsx";

const AUDIT_LOG = "/api/v1/audit-log/";
const SESSION = "/api/v1/me/";

afterEach(async () => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  await changeLanguage("en");
  window.localStorage.clear();
});

const deviceChange: AuditLogEntry = {
  id: 1,
  timestamp: "2026-11-21T12:00:00Z",
  actor: manager.username,
  action: "update",
  object_type: "assets.device",
  object_id: 3,
  object_repr: "test-device",
  changes: { name: ["test-device-old", "test-device"] },
};

function auditApi(answer: (query: URLSearchParams) => Response): FakeApi {
  return fakeApi(manager, (request) => {
    const url = new URL(request.url);
    if (url.pathname === AUDIT_LOG) {
      return answer(url.searchParams);
    }
    return jsonResponse({ detail: "Not found." }, 404);
  });
}

function listOf(results: AuditLogEntry[]): Response {
  const body: PaginatedAuditLogEntryList = { count: results.length, next: null, previous: null, results };
  return jsonResponse(body);
}

function lastQuery(api: FakeApi): Record<string, string> {
  const request = api.requestsTo(AUDIT_LOG).at(-1);
  if (request === undefined) {
    throw new Error("no request to the audit log");
  }
  return Object.fromEntries(new URL(request.url).searchParams);
}

describe("change log page", () => {
  it("shows the heading and the newest entries", async () => {
    const api = auditApi(() => listOf([deviceChange]));
    renderApp("/audit");

    expect(await screen.findByRole("heading", { level: 1, name: "Change log" })).toBeDefined();
    expect((await screen.findByTestId("audit-change-list")).textContent).toBe("Name: test-device-old → test-device");
    expect(screen.getByTestId("audit-actor").textContent).toBe(manager.username);
    expect(lastQuery(api)).toEqual({});
  });

  it("filters by object type and user, and the reset shows everything again", async () => {
    const api = auditApi(() => listOf([deviceChange]));
    renderApp("/audit");
    await screen.findByTestId("audit-entry");

    fireEvent.change(screen.getByLabelText("Object type"), { target: { value: "assets.device" } });
    fireEvent.change(screen.getByLabelText("User"), { target: { value: `  ${manager.username} ` } });
    // Nothing is asked before the filter is applied.
    expect(api.requestsTo(AUDIT_LOG)).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "Apply filter" }));

    await vi.waitFor(() => {
      expect(lastQuery(api)).toEqual({ object_type: "assets.device", actor: manager.username });
    });

    fireEvent.change(screen.getByLabelText("Object type"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply filter" }));
    await vi.waitFor(() => {
      expect(lastQuery(api)).toEqual({ actor: manager.username });
    });

    fireEvent.click(screen.getByRole("button", { name: "Reset filter" }));
    expect(screen.getByLabelText<HTMLInputElement>("User").value).toBe("");
    expect(screen.getByLabelText<HTMLSelectElement>("Object type").value).toBe("");
    // Without a filter the first answer comes from the cache again.
    expect(await screen.findByTestId("audit-entry")).toBeDefined();
  });

  it("offers every object type of the change log as a filter", async () => {
    auditApi(() => listOf([]));
    renderApp("/audit");

    const select = await screen.findByLabelText("Object type");
    expect(Array.from((select as HTMLSelectElement).options).map((option) => [option.value, option.text])).toEqual([
      ["", "All object types"],
      ["assets.site", "Site"],
      ["assets.area", "Area"],
      ["assets.plant", "Plant"],
      ["assets.device", "Device"],
      ["files.document", "File"],
      ["files.documentversion", "File version"],
      ["accounts.user", "User"],
    ]);
  });

  it("shows a 403 of the API as missing permission, without a redirect", async () => {
    const api = auditApi(() => jsonResponse({ detail: "You do not have permission to perform this action." }, 403));
    const { router } = renderApp("/audit");

    expect((await screen.findByTestId("error-summary")).textContent).toBe(
      "You do not have permission for this page or action.",
    );
    // The app asked /api/v1/me/ again: the session is valid, so it stays here.
    await vi.waitFor(() => {
      expect(api.requestsTo(SESSION).length).toBeGreaterThanOrEqual(2);
    });
    expect(router.state.location.pathname).toBe("/audit");
    expect(screen.getByRole("heading", { level: 1, name: "Change log" })).toBeDefined();
    expect(screen.getByTestId("user-name").textContent).toBe(manager.username);
  });

  it("a reader does not ask the API at all", async () => {
    const api = fakeApi(reader, () => listOf([deviceChange]));
    renderApp("/audit");

    expect(await screen.findByTestId("no-permission")).toBeDefined();
    expect(api.requestsTo(AUDIT_LOG)).toHaveLength(0);
  });

  it("is translated into German", async () => {
    await changeLanguage("de");
    auditApi(() => listOf([deviceChange]));
    renderApp("/audit");

    expect(await screen.findByRole("heading", { level: 1, name: "Änderungsprotokoll" })).toBeDefined();
    expect(screen.getByLabelText("Objektart")).toBeDefined();
    expect(screen.getByLabelText("Benutzer")).toBeDefined();
    expect(screen.getByRole("button", { name: "Filter anwenden" })).toBeDefined();
    expect((await screen.findByTestId("audit-action")).textContent).toBe("Geändert");
  });
});
