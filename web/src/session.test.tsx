import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { notifyManager, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createQueryClient } from "./api/queryClient.ts";
import { NoPermission } from "./components/SessionGuards.tsx";
import { changeLanguage } from "./i18n.ts";
import enNav from "./locales/en/nav.json";
import { navigation, requiredRole, visibleNavigation } from "./navigation.ts";
import { hasRole, loginPathFor, safeNextPath, useRole } from "./session.ts";
import { fakeApi, jsonResponse, manager, reader, roleless } from "./test/fakeApi.ts";
import { openUserMenu, renderApp } from "./test/renderApp.tsx";

const SESSION = "/_allauth/browser/v1/auth/session";
const ME = "/api/v1/me/";
const SELFTEST = "/api/v1/selftest/";

/** The scheduler TanStack Query uses by default for telling components about changes. */
function defaultScheduler(callback: () => void): void {
  setTimeout(callback, 0);
}

afterEach(async () => {
  cleanup();
  vi.unstubAllGlobals();
  await changeLanguage("en");
  window.localStorage.clear();
  document.cookie = "csrftoken=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
});

function navigationTexts(): string[] {
  const nav = screen.queryByRole("navigation", { name: enNav.label });
  return nav === null ? [] : within(nav).getAllByRole("link").map((link) => link.textContent);
}

describe("without a session", () => {
  it.each(["/", "/selftest", "/import", "/devices/plc-1", "/no-such-page"])(
    "%s leads to the sign-in page, which returns there afterwards",
    async (path) => {
      fakeApi(null);
      const { router } = renderApp(`${path}?tab=2`);

      expect(await screen.findByRole("heading", { level: 1, name: "Sign in" })).toBeDefined();
      expect(router.state.location.pathname).toBe("/login");
      expect(new URLSearchParams(router.state.location.search).get("next")).toBe(`${path}?tab=2`);
    },
  );

  it("/ leads to /login without ?next=", async () => {
    fakeApi(null);
    const { router } = renderApp("/");

    await screen.findByTestId("login-form");
    expect(`${router.state.location.pathname}${router.state.location.search}`).toBe("/login");
  });

  it("asks /api/v1/me/ once at the start and shows nothing of the pages", async () => {
    const api = fakeApi(null);
    renderApp("/selftest");

    await screen.findByTestId("login-form");
    expect(api.requestsTo(ME)).toHaveLength(1);
    expect(api.requestsTo(SELFTEST)).toHaveLength(0);
    expect(screen.queryByRole("navigation")).toBeNull();
  });

  it("shows an error, not the sign-in page, when /api/v1/me/ does not answer", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new TypeError("Failed to fetch"))));
    vi.stubGlobal(
      "Request",
      class extends Request {
        constructor(input: RequestInfo | URL, init?: RequestInit) {
          super(typeof input === "string" ? new URL(input, window.location.href) : input, init);
        }
      },
    );
    const { router } = renderApp("/selftest");

    expect((await screen.findByTestId("error-summary", {}, { timeout: 5000 })).textContent).toBe(
      "The API did not respond. Is the server running?",
    );
    expect(router.state.location.pathname).toBe("/selftest");
  });
});

describe("a 403 of another call", () => {
  it("with a valid session: no redirect, no sign-out, a notice instead", async () => {
    const api = fakeApi(reader, () => jsonResponse({ detail: "You do not have permission." }, 403));
    const { router } = renderApp("/selftest");

    expect((await screen.findByTestId("selftest-error")).textContent).toBe(
      "You do not have permission for this page or action.",
    );
    // /api/v1/me/ is asked again and still knows the user.
    await vi.waitFor(() => {
      expect(api.requestsTo(ME)).toHaveLength(2);
    });
    expect(router.state.location.pathname).toBe("/selftest");
    expect(screen.getByTestId("user-name").textContent).toBe(reader.username);
    expect(api.requestsTo(SESSION)).toHaveLength(0);
  });

  it("with an expired session: to the sign-in page, which returns afterwards", async () => {
    const api = fakeApi(manager, () => {
      api.setMe(null); // the session ended on the server
      return jsonResponse({ detail: "Authentication credentials were not provided." }, 403);
    });
    const { router } = renderApp("/selftest");

    expect(await screen.findByTestId("login-form")).toBeDefined();
    expect(router.state.location.pathname).toBe("/login");
    expect(new URLSearchParams(router.state.location.search).get("next")).toBe("/selftest");
    expect(api.requestsTo(ME)).toHaveLength(2);
    expect(screen.queryByTestId("user-name")).toBeNull();
  });
});

describe("navigation and role", () => {
  it("a manager sees every entry and the role Manage", async () => {
    fakeApi(manager);
    renderApp("/");

    expect((await screen.findByTestId("user-role")).textContent).toBe("Manage");
    expect(navigationTexts()).toEqual(["Structure", "Map", "Search", "Ingestion", "Import", "Change log", "Self-test"]);
    expect(screen.queryByTestId("no-role")).toBeNull();
  });

  it("a reader does not see import and change log, and the role is translated", async () => {
    fakeApi(reader);
    renderApp("/");

    expect((await screen.findByTestId("user-role")).textContent).toBe("Read");
    expect(navigationTexts()).toEqual(["Structure", "Map", "Search", "Ingestion", "Self-test"]);

    fireEvent.change(screen.getByTestId("language-switch"), { target: { value: "de" } });

    expect(await screen.findByText("Lesen")).toBeDefined();
    expect(
      within(screen.getByRole("navigation", { name: "Hauptnavigation" }))
        .getAllByRole("link")
        .map((link) => link.textContent),
    ).toEqual(["Struktur", "Landkarte", "Suche", "Einlesen", "Selbsttest"]);
  });

  it.each(["/import", "/audit"])("a reader who opens %s directly gets a notice, no redirect", async (path) => {
    const api = fakeApi(reader);
    const { router } = renderApp(path);

    expect((await screen.findByTestId("no-permission")).textContent).toBe(
      "You do not have permission for this page or action.",
    );
    expect(screen.queryByTestId("page-placeholder")).toBeNull();
    expect(router.state.location.pathname).toBe(path);
    expect(api.requestsTo(SESSION)).toHaveLength(0);
    expect(screen.getAllByRole("heading", { level: 1 }).map((h) => h.textContent)).toEqual(["No permission"]);
    expect(document.title).toBe("No permission – 2x");
  });

  it("the page without permission has a heading and a title in German", async () => {
    await changeLanguage("de");
    fakeApi(reader);
    renderApp("/audit");

    expect((await screen.findByTestId("no-permission")).textContent).toBe(
      "Sie haben keine Berechtigung für diese Seite oder Aktion.",
    );
    expect(screen.getAllByRole("heading", { level: 1 }).map((h) => h.textContent)).toEqual(["Keine Berechtigung"]);
    expect(document.title).toBe("Keine Berechtigung – 2x");
  });

  it("the notice inside a page has neither heading nor title of its own", () => {
    render(<NoPermission />);

    expect(screen.getByTestId("no-permission").textContent).toBe(
      "You do not have permission for this page or action.",
    );
    expect(screen.queryByRole("heading")).toBeNull();
    expect(document.title).not.toContain("No permission");
  });

  it("an account without a role sees a hint, no navigation and no page", async () => {
    fakeApi(roleless);
    const { router } = renderApp("/");

    expect((await screen.findByTestId("no-role")).textContent).toContain("No role is assigned to your account");
    expect(screen.getByTestId("user-name").textContent).toBe(roleless.username);
    expect(screen.getByTestId("user-role").textContent).toBe("No role");
    expect(screen.queryByRole("navigation")).toBeNull();
    expect(screen.getByTestId("no-permission")).toBeDefined();
    expect(screen.queryByTestId("page-placeholder")).toBeNull();
    expect(router.state.location.pathname).toBe("/");
  });

  it("the hint for an account without a role in German", async () => {
    await changeLanguage("de");
    fakeApi(roleless);
    renderApp("/");

    expect((await screen.findByTestId("no-role")).textContent).toContain("Ihrem Konto ist keine Rolle zugewiesen");
    expect(screen.getByTestId("user-role").textContent).toBe("Keine Rolle");
  });

  it("navigation.ts names a role for every entry; import and change log need manage", () => {
    expect(navigation.map((entry) => [entry.path, entry.requires])).toEqual([
      ["/", "read"],
      ["/map", "read"],
      ["/search", "read"],
      ["/ingest", "read"],
      ["/import", "manage"],
      ["/audit", "manage"],
      ["/selftest", "read"],
    ]);
    expect(visibleNavigation("manage")).toHaveLength(7);
    expect(visibleNavigation("read").map((entry) => entry.path)).toEqual(["/", "/map", "/search", "/ingest", "/selftest"]);
    expect(requiredRole("/search")).toBe("read");
    expect(requiredRole("/ingest")).toBe("read");
    expect(requiredRole("/map")).toBe("read");
    expect(visibleNavigation(null)).toEqual([]);
    expect(requiredRole("/import")).toBe("manage");
    expect(requiredRole("/devices")).toBe("read");
  });
});

describe("sign-out", () => {
  it("signs out at allauth with the CSRF token and leads to /login", async () => {
    document.cookie = "csrftoken=csrf-sign-out; path=/";
    const api = fakeApi(manager, (request) => {
      expect(new URL(request.url).pathname).toBe(SESSION);
      api.setMe(null);
      return jsonResponse({ status: 401, meta: { is_authenticated: false } }, 401);
    });
    const { router } = renderApp("/selftest");

    await openUserMenu();
    fireEvent.click(await screen.findByRole("button", { name: "Sign out" }));

    expect(await screen.findByTestId("login-form")).toBeDefined();
    expect(`${router.state.location.pathname}${router.state.location.search}`).toBe("/login");
    expect(screen.getByTestId("user-area").childNodes.length).toBe(0);
    const [request] = api.requestsTo(SESSION);
    expect(request?.method).toBe("DELETE");
    expect(request?.headers.get("X-CSRFToken")).toBe("csrf-sign-out");
  });

  // Regression test for a flaky run (work order 062): TanStack Query tells the
  // components about the forgotten session in a timer, React Router renders a
  // new address in a transition. If the timer came first, the session guard of
  // the old page sent the browser to /login?next=%2Fselftest. Here the timer
  // fires exactly when the router has moved to /login, before React could
  // render a transition, which made the old order fail every time.
  it("leads to /login even if the session guard hears of the sign-out at the same moment", async () => {
    const api = fakeApi(manager, () => {
      api.setMe(null);
      return jsonResponse({ status: 401, meta: { is_authenticated: false } }, 401);
    });
    const { router } = renderApp("/selftest");
    await openUserMenu();
    const signOutButton = await screen.findByRole("button", { name: "Sign out" });

    const held: (() => void)[] = [];
    notifyManager.setScheduler((callback) => {
      held.push(callback);
    });
    const unsubscribe = router.subscribe((state) => {
      if (state.location.pathname === "/login") {
        unsubscribe();
        notifyManager.setScheduler(defaultScheduler);
        held.splice(0).forEach((callback) => {
          callback();
        });
      }
    });
    try {
      fireEvent.click(signOutButton);

      expect(await screen.findByTestId("login-form")).toBeDefined();
      expect(`${router.state.location.pathname}${router.state.location.search}`).toBe("/login");
    } finally {
      unsubscribe();
      notifyManager.setScheduler(defaultScheduler);
      held.splice(0).forEach((callback) => {
        callback();
      });
    }
  });

  it("stays signed in and says so when signing out fails", async () => {
    fakeApi(manager, () => jsonResponse({ status: 500 }, 500));
    const { router } = renderApp("/");

    await openUserMenu();
    fireEvent.click(await screen.findByRole("button", { name: "Sign out" }));

    expect((await screen.findByTestId("sign-out-error")).textContent).toBe("Signing out failed. Please try again.");
    expect(router.state.location.pathname).toBe("/");
    expect(screen.getByTestId("user-name").textContent).toBe(manager.username);
  });
});

function RoleProbe(): ReactElement {
  const access = useRole();
  return <p data-testid="role-probe">{JSON.stringify(access)}</p>;
}

describe("useRole", () => {
  it.each([
    [manager, { role: "manage", canRead: true, canManage: true }],
    [reader, { role: "read", canRead: true, canManage: false }],
    [roleless, { role: null, canRead: false, canManage: false }],
    [null, { role: null, canRead: false, canManage: false }],
  ] as const)("for %j gives %j", async (me, expected) => {
    fakeApi(me);
    render(
      <QueryClientProvider client={createQueryClient()}>
        <RoleProbe />
      </QueryClientProvider>,
    );

    await vi.waitFor(() => {
      expect(JSON.parse(screen.getByTestId("role-probe").textContent)).toEqual(expected);
    });
  });

  it("hasRole: manage includes read, read not manage, no role nothing", () => {
    expect(hasRole("manage", "manage")).toBe(true);
    expect(hasRole("manage", "read")).toBe(true);
    expect(hasRole("read", "read")).toBe(true);
    expect(hasRole("read", "manage")).toBe(false);
    expect(hasRole(null, "read")).toBe(false);
  });
});

describe("addresses after signing in", () => {
  it.each([
    [null, "/"],
    ["", "/"],
    ["/selftest", "/selftest"],
    ["/devices/plc-1?tab=2#files", "/devices/plc-1?tab=2#files"],
    ["/admin/", "/admin/"],
    ["https://example.test/", "/"],
    ["//example.test/", "/"],
    ["/\\example.test/", "/"],
    ["/\t/example.test/", "/"],
    ["javascript:alert(1)", "/"],
    ["selftest", "/"],
    ["/api/v1/me/", "/"],
    ["/static/index.html", "/"],
    ["/_allauth/browser/v1/auth/session", "/"],
    ["/accounts/login/", "/"],
    ["/login", "/"],
    ["/login?next=/x", "/"],
  ])("safeNextPath(%j) is %j", (raw, expected) => {
    expect(safeNextPath(raw)).toBe(expected);
  });

  // Dot segments and backslashes that only become "//host" after the URL
  // parser has normalised the path (open redirect, review of work order 030).
  it.each([
    "/.//evil.test/",
    "/%2e//evil.test/",
    "/%2E//evil.test/",
    "/x/..//evil.test/",
    "/x/%2e%2e//evil.test/",
    "/admin/..//evil.test/",
    "/selftest/../..//evil.test/",
    "/.\\/evil.test/",
    "/.\\\\evil.test/",
    "/x/..\\/evil.test/",
    "/x/..\\\\evil.test/",
    "/admin/..\\\\evil.test/",
    "/\t\\/evil.test/",
    "/\n/evil.test/",
  ])("safeNextPath(%j) does not leave the application", (raw) => {
    expect(safeNextPath(raw)).toBe("/");
  });

  it.each([
    ["/%5c/evil.test/", "/%5c/evil.test/"],
    ["/%5C%5Cevil.test/", "/%5C%5Cevil.test/"],
    ["/.%5c/evil.test/", "/.%5c/evil.test/"],
    ["/x/..%5c/evil.test/", "/x/..%5c/evil.test/"],
    ["/x/..%5c%5cevil.test/", "/x/..%5c%5cevil.test/"],
    ["/selftest?next=//evil.test/", "/selftest?next=//evil.test/"],
    ["/selftest?x=%5c", "/selftest?x=%5c"],
  ])("safeNextPath(%j) keeps an encoded backslash as a path of this application: %j", (raw, expected) => {
    const result = safeNextPath(raw);

    expect(result).toBe(expected);
    expect(result.startsWith("//")).toBe(false);
    expect(result).not.toContain("\\");
    expect(new URL(result, "http://app.test").origin).toBe("http://app.test");
  });

  it("a malicious ?next= leads to / after signing in, never to another host", async () => {
    const api = fakeApi(null, () => {
      api.setMe(manager);
      return jsonResponse({ status: 200 });
    });
    const { router } = renderApp(`/login?next=${encodeURIComponent("/x/..//evil.test/")}`);

    fireEvent.change(await screen.findByLabelText("Username"), { target: { value: "test-manager" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "test-only-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Structure" })).toBeDefined();
    expect(router.state.location.pathname).toBe("/");
  });

  it("loginPathFor keeps the address for later", () => {
    expect(loginPathFor("/")).toBe("/login");
    expect(loginPathFor("/selftest?x=1")).toBe("/login?next=%2Fselftest%3Fx%3D1");
  });
});
