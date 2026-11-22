import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { openServerPage } from "../browserLocation.ts";
import { changeLanguage } from "../i18n.ts";
import { fakeApi, type FakeApi, jsonResponse, manager } from "../test/fakeApi.ts";
import { renderApp } from "../test/renderApp.tsx";

vi.mock("../browserLocation.ts", () => ({ openServerPage: vi.fn() }));

const LOGIN = "/_allauth/browser/v1/auth/login";
// Test values only.
const USERNAME = "test-manager";
const PASSWORD = "test-only-password";

afterEach(async () => {
  cleanup();
  vi.unstubAllGlobals();
  vi.mocked(openServerPage).mockReset();
  await changeLanguage("en");
  window.localStorage.clear();
});

/** Nobody is signed in; the sign-in call answers with `status` and `body`, a 200 signs the manager in. */
function serverWithSignIn(status: number, body: unknown = {}): FakeApi {
  const api: FakeApi = fakeApi(null, (request) => {
    if (new URL(request.url).pathname !== LOGIN) {
      return Promise.reject(new TypeError("Failed to fetch"));
    }
    if (status === 200) {
      api.setMe(manager);
    }
    return jsonResponse({ status, ...(body as object) }, status);
  });
  return api;
}

async function fillAndSubmit(username = USERNAME, password = PASSWORD): Promise<void> {
  fireEvent.change(await screen.findByLabelText("Username"), { target: { value: username } });
  fireEvent.change(screen.getByLabelText("Password"), { target: { value: password } });
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("sign-in form", () => {
  it("shows username, password and the button, but no navigation and no user", async () => {
    fakeApi(null);
    renderApp("/login");

    expect(await screen.findByRole("heading", { level: 1, name: "Sign in" })).toBeDefined();
    expect(screen.getByLabelText("Username").getAttribute("autocomplete")).toBe("username");
    expect(screen.getByLabelText("Password").getAttribute("type")).toBe("password");
    expect(screen.queryByRole("navigation")).toBeNull();
    expect(screen.getByTestId("user-area").childNodes.length).toBe(0);
    expect(screen.queryByTestId("login-error")).toBeNull();
  });

  it("shows an error for a wrong password and empties the password field", async () => {
    const api = serverWithSignIn(400, { errors: [{ code: "username_password_mismatch", param: "password" }] });
    const { router } = renderApp("/login");

    await fillAndSubmit();

    const error = await screen.findByTestId("login-error");
    expect(error.textContent).toBe("Username or password is wrong.");
    expect(error.getAttribute("role")).toBe("alert");
    expect(screen.getByLabelText<HTMLInputElement>("Password").value).toBe("");
    expect(screen.getByLabelText<HTMLInputElement>("Username").value).toBe(USERNAME);
    expect(router.state.location.pathname).toBe("/login");
    expect(api.requestsTo(LOGIN)).toHaveLength(1);
  });

  it.each([
    [400, { errors: [{ code: "too_many_login_attempts" }] }, "locked", "Too many failed sign-in attempts for this account."],
    [429, {}, "rate-limited", "Too many sign-in attempts from this computer."],
    [403, {}, "expired-page", "This page has expired."],
    [500, {}, "http-error", "The sign-in failed with HTTP status 500."],
  ])("explains HTTP %s (%j) as %s", async (status, body, reason, text) => {
    serverWithSignIn(status, body);
    renderApp("/login");

    await fillAndSubmit();

    const error = await screen.findByTestId("login-error");
    expect(error.getAttribute("data-reason")).toBe(reason);
    expect(error.textContent).toContain(text);
  });

  it("asks for both fields before sending anything", async () => {
    const api = serverWithSignIn(200);
    renderApp("/login");

    await fillAndSubmit(" ", "");

    expect((await screen.findByTestId("login-error")).textContent).toBe("Please enter your username and password.");
    expect(api.requestsTo(LOGIN)).toHaveLength(0);
  });

  it("shows the errors in German", async () => {
    await changeLanguage("de");
    serverWithSignIn(400, { errors: [{ code: "too_many_login_attempts" }] });
    renderApp("/login");

    fireEvent.change(await screen.findByLabelText("Benutzername"), { target: { value: USERNAME } });
    fireEvent.change(screen.getByLabelText("Kennwort"), { target: { value: PASSWORD } });
    fireEvent.click(screen.getByRole("button", { name: "Anmelden" }));

    expect((await screen.findByTestId("login-error")).textContent).toContain(
      "Zu viele fehlgeschlagene Anmeldeversuche",
    );
  });
});

describe("after signing in", () => {
  it("continues to the page from ?next= and shows the user", async () => {
    const api = serverWithSignIn(200);
    const { router } = renderApp("/login?next=%2Fselftest%3Fx%3D1");

    await fillAndSubmit();

    expect((await screen.findByTestId("user-name")).textContent).toBe(manager.username);
    expect(await screen.findByRole("heading", { level: 1, name: "Self-test" })).toBeDefined();
    expect(router.state.location.pathname).toBe("/selftest");
    expect(router.state.location.search).toBe("?x=1");
    const [login] = api.requestsTo(LOGIN);
    expect(await login?.json()).toEqual({ username: USERNAME, password: PASSWORD });
  });

  it.each(["https://example.test/", "//example.test/", "/api/v1/me/", "/login", "javascript:alert(1)"])(
    "never continues to %s, only to /",
    async (next) => {
      serverWithSignIn(200);
      const { router } = renderApp(`/login?next=${encodeURIComponent(next)}`);

      await fillAndSubmit();

      expect(await screen.findByRole("heading", { level: 1, name: "Structure" })).toBeDefined();
      expect(router.state.location.pathname).toBe("/");
      expect(openServerPage).not.toHaveBeenCalled();
    },
  );

  it("opens the admin as a page of its own", async () => {
    serverWithSignIn(200);
    renderApp("/login?next=%2Fadmin%2Faccounts%2Fuser%2F");

    await fillAndSubmit();

    await vi.waitFor(() => {
      expect(openServerPage).toHaveBeenCalledWith("/admin/accounts/user/");
    });
  });

  it("a signed-in visitor of /login continues at once", async () => {
    fakeApi(manager);
    const { router } = renderApp("/login?next=%2Faudit");

    expect(await screen.findByRole("heading", { level: 1, name: "Change log" })).toBeDefined();
    expect(router.state.location.pathname).toBe("/audit");
  });
});
