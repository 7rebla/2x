// Links of the user menu (work order 134): the settings and, since the self-test
// left the header bar (E-69), the self-test. Both need a role like every page.
import { act, cleanup, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { changeLanguage } from "../i18n.ts";
import { fakeApi, manager, reader, roleless } from "../test/fakeApi.ts";
import { openUserMenu, renderApp } from "../test/renderApp.tsx";

afterEach(async () => {
  cleanup();
  vi.unstubAllGlobals();
  await changeLanguage("en");
});

describe("self-test link in the user menu", () => {
  it.each([
    ["read", reader],
    ["manage", manager],
  ])("is there for the role %s, after the settings, with the classes of the settings link", async (_role, user) => {
    fakeApi(user);
    renderApp("/");
    await openUserMenu();
    const menu = screen.getByTestId("user-menu");
    const link = within(menu).getByRole("link", { name: "Self-test" });
    expect(link).toBe(within(menu).getByTestId("selftest-link"));
    expect(link.getAttribute("href")).toBe("/selftest");
    expect(link.classList.contains("nav-link")).toBe(true);
    const label = link.querySelector(".nav-label");
    expect(label?.getAttribute("data-label")).toBe("Self-test");
    const icon = link.querySelector("svg");
    expect(icon?.getAttribute("data-icon")).toBe("selftest");
    expect(icon?.getAttribute("aria-hidden")).toBe("true");
    expect(within(menu).getAllByRole("link").map((element) => element.getAttribute("href"))).toEqual([
      "/settings",
      "/selftest",
    ]);
  });

  it("is missing without a role, like the settings", async () => {
    fakeApi(roleless);
    renderApp("/");
    await openUserMenu();
    const menu = screen.getByTestId("user-menu");
    expect(within(menu).queryByTestId("selftest-link")).toBeNull();
    expect(within(menu).queryByTestId("settings-link")).toBeNull();
    expect(within(menu).queryAllByRole("link")).toEqual([]);
  });

  it("speaks German", async () => {
    fakeApi(reader);
    renderApp("/");
    await openUserMenu();
    await act(async () => {
      await changeLanguage("de");
    });
    const link = within(screen.getByTestId("user-menu")).getByRole("link", { name: "Selbsttest" });
    expect(link.getAttribute("href")).toBe("/selftest");
    expect(link.querySelector(".nav-label")?.getAttribute("data-label")).toBe("Selbsttest");
  });

  it("marks itself as the current page on /selftest", async () => {
    fakeApi(manager);
    renderApp("/selftest");
    await openUserMenu();
    const link = within(screen.getByTestId("user-menu")).getByTestId("selftest-link");
    expect(link.getAttribute("aria-current")).toBe("page");
    expect(within(screen.getByTestId("user-menu")).getByTestId("settings-link").getAttribute("aria-current")).toBeNull();
  });
});
