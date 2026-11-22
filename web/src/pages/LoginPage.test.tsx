import { act, cleanup, fireEvent, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { openServerPage } from "../browserLocation.ts";
import { HEADER_BRAND_SIZE } from "../components/BrandMark.tsx";
import { changeLanguage } from "../i18n.ts";
import { fakeApi, type FakeApi, jsonResponse, manager } from "../test/fakeApi.ts";
import { renderApp } from "../test/renderApp.tsx";
import { refreshDisplay, updateDisplaySettings } from "../theme/store.ts";
import { CARD_BRAND_SIZE } from "./LoginPage.tsx";

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
  window.sessionStorage.clear();
  refreshDisplay();
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

describe("sign-in card (work order 086)", () => {
  it("centres a narrow card on the surface with a border", async () => {
    fakeApi(null);
    renderApp("/login");

    const card = await screen.findByTestId("login-card");
    const page = screen.getByTestId("login-page");
    expect(page.classList).toContain("mx-auto");
    expect(page.classList).toContain("max-w-sm");
    expect(page.classList).toContain("w-full");
    for (const name of ["bg-surface", "border", "border-line", "rounded-lg"]) {
      expect(card.classList).toContain(name);
    }
    // Heading, introduction and form are inside the card.
    expect(within(card).getByRole("heading", { level: 1, name: "Sign in" })).toBeDefined();
    expect(within(card).getByText("Sign in with your 2x account.")).toBeDefined();
    expect(within(card).getByTestId("login-form")).toBeDefined();
  });

  it("shows the brand mark and the name above the card, not as a second link", async () => {
    fakeApi(null);
    renderApp("/login");

    const card = await screen.findByTestId("login-card");
    const lockup = within(screen.getByTestId("login-page")).getByTestId("brand-lockup");
    // Above the card in the order of the page.
    expect(lockup.compareDocumentPosition(card) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(card.contains(lockup)).toBe(false);
    expect(lockup.closest("a")).toBeNull();
    expect(lockup.textContent.trim()).toBe("2x");
    const mark = within(lockup).getByTestId("brand-mark");
    expect(mark.getAttribute("aria-hidden")).toBe("true");
    expect(mark.dataset.form).toBe("master");
    expect(mark.style.width).toBe(`${String(CARD_BRAND_SIZE)}px`);
    expect(CARD_BRAND_SIZE).toBeGreaterThan(HEADER_BRAND_SIZE);
    // The only link named 2x is the one in the header.
    expect(screen.getAllByRole("link", { name: "2x" })).toHaveLength(1);
    expect(within(screen.getByRole("banner")).getByRole("link", { name: "2x" })).toBeDefined();
  });

  it("types the name in the card and in the header (run sign-in)", async () => {
    fakeApi(null);
    renderApp("/login");

    const lockup = await screen.findByTestId("brand-lockup");
    expect(within(lockup).getByTestId("typed-text").dataset.typing).toBe("type");
    const header = within(screen.getByRole("banner")).getByRole("link", { name: "2x" });
    expect(within(header).getByTestId("typed-text").dataset.typing).toBe("type");
    expect(window.sessionStorage.getItem("twox.typed")).toBe("sign-in");
  });

  it("shows the name at once with reduced motion", async () => {
    act(() => {
      updateDisplaySettings({ reduceMotion: true });
    });
    fakeApi(null);
    renderApp("/login");

    const lockup = await screen.findByTestId("brand-lockup");
    expect(lockup.querySelector(".tx-type")).toBeNull();
    expect(lockup.textContent.trim()).toBe("2x");
  });

  it("gives fields and button the same height and the button the full width", async () => {
    fakeApi(null);
    renderApp("/login");

    const button = await screen.findByRole("button", { name: "Sign in" });
    expect(button.classList).toContain("w-full");
    expect(button.classList).toContain("min-h-9");
    for (const label of ["Username", "Password"]) {
      const field = screen.getByLabelText(label);
      expect(field.classList).toContain("w-full");
      expect(field.classList).toContain("h-9");
    }
  });

  it("keeps the card in German, with the language switch in the header", async () => {
    await changeLanguage("de");
    fakeApi(null);
    renderApp("/login");

    const card = await screen.findByTestId("login-card");
    expect(within(card).getByRole("heading", { level: 1, name: "Anmelden" })).toBeDefined();
    expect(within(card).getByRole("button", { name: "Anmelden" }).classList).toContain("w-full");
    expect(within(screen.getByRole("banner")).getByRole("combobox")).toBeDefined();
  });

  it("shows a wrong password inside the card", async () => {
    serverWithSignIn(400, { errors: [{ code: "username_password_mismatch", param: "password" }] });
    renderApp("/login");

    await fillAndSubmit();

    const error = await screen.findByTestId("login-error");
    expect(screen.getByTestId("login-card").contains(error)).toBe(true);
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
