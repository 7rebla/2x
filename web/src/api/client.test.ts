import { afterEach, describe, expect, it, vi } from "vitest";

import { changeLanguage } from "../i18n.ts";
import { fakeApi, jsonResponse, manager } from "../test/fakeApi.ts";
import { signIn, signOut } from "./auth.ts";
import { csrfToken, installClientConfig, isWritingMethod, onForbidden } from "./client.ts";
import { client } from "./generated/client.gen.ts";

function setCsrfCookie(value: string): void {
  document.cookie = `csrftoken=${value}; path=/`;
}

function clearCsrfCookie(): void {
  document.cookie = "csrftoken=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
}

afterEach(async () => {
  clearCsrfCookie();
  vi.unstubAllGlobals();
  await changeLanguage("en");
  window.localStorage.clear();
});

describe("csrfToken", () => {
  it("reads the csrftoken cookie among others", () => {
    document.cookie = "other=1; path=/";
    setCsrfCookie("token-from-django");

    expect(csrfToken()).toBe("token-from-django");

    document.cookie = "other=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  });

  it("is null without the cookie", () => {
    expect(csrfToken()).toBeNull();
  });

  it("treats only GET, HEAD, OPTIONS and TRACE as reading", () => {
    expect(["GET", "head", "OPTIONS", "TRACE"].map(isWritingMethod)).toEqual([false, false, false, false]);
    expect(["POST", "PUT", "patch", "DELETE"].map(isWritingMethod)).toEqual([true, true, true, true]);
  });
});

describe("headers of the generated client", () => {
  it("sends X-CSRFToken from the cookie with writing requests only", async () => {
    installClientConfig();
    setCsrfCookie("csrf-test-value");
    const api = fakeApi(manager, () => jsonResponse({}));

    await client.post({ url: "/api/v1/sites/", body: { name: "x" } });
    await client.patch({ url: "/api/v1/sites/1/", body: { name: "y" } });
    await client.delete({ url: "/api/v1/sites/1/" });
    await client.get({ url: "/api/v1/sites/" });

    const [post, get] = api.requestsTo("/api/v1/sites/");
    const [patch, remove] = api.requestsTo("/api/v1/sites/1/");
    expect(post?.method).toBe("POST");
    expect(post?.headers.get("X-CSRFToken")).toBe("csrf-test-value");
    expect(get?.method).toBe("GET");
    expect(get?.headers.get("X-CSRFToken")).toBeNull();
    expect(patch?.headers.get("X-CSRFToken")).toBe("csrf-test-value");
    expect(remove?.headers.get("X-CSRFToken")).toBe("csrf-test-value");
  });

  it("sends Accept-Language with the language shown", async () => {
    installClientConfig();
    const api = fakeApi(manager, () => jsonResponse({}));

    await client.get({ url: "/api/v1/sites/" });
    await changeLanguage("de");
    await client.get({ url: "/api/v1/sites/" });

    expect(api.requestsTo("/api/v1/sites/").map((request) => request.headers.get("Accept-Language"))).toEqual([
      "en",
      "de",
    ]);
  });

  it("reports a 403 to the listeners, but not one of /api/v1/me/", async () => {
    installClientConfig();
    fakeApi(null, () => jsonResponse({ detail: "You do not have permission to perform this action." }, 403));
    const listener = vi.fn();
    const stop = onForbidden(listener);

    await client.get({ url: "/api/v1/me/" });
    expect(listener).not.toHaveBeenCalled();
    await client.get({ url: "/api/v1/sites/" });
    expect(listener).toHaveBeenCalledOnce();

    stop();
    await client.get({ url: "/api/v1/sites/" });
    expect(listener).toHaveBeenCalledOnce();
  });
});

describe("sign-in calls (allauth)", () => {
  it("send the CSRF token and the language as well", async () => {
    setCsrfCookie("csrf-for-allauth");
    await changeLanguage("de");
    const api = fakeApi(null, (request) =>
      request.method === "DELETE" ? jsonResponse({ status: 401 }, 401) : jsonResponse({ status: 200 }),
    );

    await signIn("someone", "test-only-password");
    await signOut();

    const [login] = api.requestsTo("/_allauth/browser/v1/auth/login");
    const [logout] = api.requestsTo("/_allauth/browser/v1/auth/session");
    expect(login?.method).toBe("POST");
    expect(login?.headers.get("X-CSRFToken")).toBe("csrf-for-allauth");
    expect(login?.headers.get("Accept-Language")).toBe("de");
    expect(login?.headers.get("Content-Type")).toBe("application/json");
    expect(await login?.json()).toEqual({ username: "someone", password: "test-only-password" });
    expect(logout?.method).toBe("DELETE");
    expect(logout?.headers.get("X-CSRFToken")).toBe("csrf-for-allauth");
  });

  it.each([
    [200, {}, "signed-in"],
    [409, {}, "signed-in"],
    [400, { errors: [{ code: "username_password_mismatch" }] }, "wrong-credentials"],
    [400, { errors: [{ code: "too_many_login_attempts" }] }, "locked"],
    [400, { errors: [{ code: "required", param: "password" }] }, "invalid"],
    [400, "not json", "invalid"],
    [429, {}, "rate-limited"],
    [403, {}, "expired-page"],
    [500, {}, "http-error"],
  ] as const)("signIn turns HTTP %s %j into %s", async (status, body, kind) => {
    fakeApi(null, () =>
      typeof body === "string" ? new Response(body, { status }) : jsonResponse({ status, ...body }, status),
    );

    expect((await signIn("someone", "test-only-password")).kind).toBe(kind);
  });

  it("signIn reports a missing answer", async () => {
    fakeApi(null);

    expect(await signIn("someone", "test-only-password")).toEqual({ kind: "network" });
  });

  it("signOut counts allauth's 401 as signed out, other answers not", async () => {
    let status = 401;
    fakeApi(null, () => jsonResponse({ status }, status));

    expect(await signOut()).toEqual({ kind: "signed-out" });
    status = 403;
    expect(await signOut()).toEqual({ kind: "http-error", status: 403 });
  });
});
