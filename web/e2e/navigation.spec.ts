import type { Page } from "@playwright/test";

import { expect, test } from "./fixtures";

// Routing of the web UI as served by Django: the start page, a click through
// the navigation, deep links and the page for unknown addresses.
test.use({ locale: "en-US" });

/** Id of a file that no test creates (largest id of the database column). */
const MISSING_ID = "2147483647";

function collectConsoleErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      errors.push(message.text());
    }
  });
  page.on("pageerror", (error) => {
    errors.push(error.message);
  });
  return errors;
}

test("a click in the user menu leads from / to the self-test page", async ({ page }) => {
  const consoleErrors = collectConsoleErrors(page);

  const response = await page.goto("/");
  expect(response?.status()).toBe(200);
  const navigation = page.getByRole("navigation", { name: "Main navigation" });
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Structure");
  await expect(navigation.getByRole("link", { name: "Structure" })).toHaveAttribute("aria-current", "page");

  // The self-test is an operations page in the user menu, not an entry of the bar (work order 134).
  await page.getByTestId("user-menu-button").click();
  await page.getByTestId("user-menu").getByRole("link", { name: "Self-test" }).click();

  await expect(page).toHaveURL(/\/selftest$/);
  await expect(page.getByTestId("user-menu")).toBeHidden();
  await expect(page.getByTestId("selftest-link")).toHaveAttribute("aria-current", "page");
  await expect(navigation.locator('[aria-current="page"]')).toHaveCount(0);
  await expect(page.getByTestId("worker-result")).toHaveText("pong");
  await expect(page.getByTestId("database-version")).toHaveText(/\d+\.\d+/);

  // Back in the browser history returns to the start page.
  await page.goBack();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Structure");

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});

test("an address with a parameter opens directly", async ({ page }) => {
  const consoleErrors = collectConsoleErrors(page);
  // The file page asks the API for the file; the browser logs its 404.
  const fileRequest = page.waitForResponse((answer) => answer.url().endsWith(`/api/v1/documents/${MISSING_ID}/`));

  // Device and file pages with real data open directly in assets.spec.ts and
  // files.spec.ts. Here the file does not exist: the page itself (not
  // Django) answers with NotFound after asking the API.
  const response = await page.goto(`/documents/${MISSING_ID}`);
  expect(response?.status()).toBe(200);

  expect((await fileRequest).status()).toBe(404);
  await expect(page.getByTestId("not-found")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Page not found");
  await expect(page.getByRole("navigation", { name: "Main navigation" })).toBeVisible();

  expect(
    consoleErrors.filter((message) => !message.includes("status of 404")),
    "errors in the browser console",
  ).toEqual([]);
});

// Header with icons (work order 071): every entry shows an icon hidden from
// assistive technology and a readable text; the header stays on one line in
// English and German and does not change its height when the language changes.
// From 1280 px (xl) the texts are shown next to the icons; from 768 to 1279 px
// a short text below each icon, with the full text as accessible name and
// tooltip; below 768 px a button "Menu" opens a list with every entry and the
// user menu (work order 082, E-65 point 3; seven entries since work order 055).
// Since work order 134 (E-69) "Ask" follows "Search", and the self-test sits in
// the user menu instead of the bar; the bar keeps seven entries.

const ENGLISH_ENTRIES = ["Structure", "Map", "Search", "Ask", "Ingestion", "Import", "Change log"];
const GERMAN_ENTRIES = ["Struktur", "Landkarte", "Suche", "Auskunft", "Einlesen", "Import", "Änderungsprotokoll"];
const ENGLISH_SHORT = ["Structure", "Map", "Search", "Ask", "Ingestion", "Import", "Log"];
const GERMAN_SHORT = ["Struktur", "Karte", "Suche", "Auskunft", "Einlesen", "Import", "Protokoll"];
/** The last entry of the bar (for a manager): once it shows, the whole bar is there. */
const ENGLISH_LAST = ENGLISH_ENTRIES[ENGLISH_ENTRIES.length - 1] ?? "";
const GERMAN_LAST = GERMAN_ENTRIES[GERMAN_ENTRIES.length - 1] ?? "";

interface HeaderLayout {
  readonly header: number;
  readonly tops: number[];
  readonly overflow: number;
  /** Width left free in the navigation after the last entry. */
  readonly free: number;
  readonly labels: string[];
  readonly titles: (string | null)[];
  readonly labelWidths: number[];
  /** Short texts as drawn (the content of ::before) and the width of their element. */
  readonly shorts: string[];
  readonly shortWidths: number[];
  /** Whether the short text stands below the icon (its top below the icon's bottom). */
  readonly shortBelowIcon: boolean[];
}

/** Positions of the header and of every entry of the main navigation. */
async function headerLayout(page: Page): Promise<HeaderLayout> {
  return page.evaluate(() => {
    const header = document.querySelector("header");
    const nav = document.querySelector('[data-testid="main-navigation"]');
    const list = nav?.querySelector("ul");
    if (header === null || nav === null || list === null || list === undefined) {
      throw new Error("no header or navigation");
    }
    const links = [...nav.querySelectorAll("a")];
    return {
      header: Math.round(header.getBoundingClientRect().height),
      tops: links.map((link) => Math.round(link.getBoundingClientRect().top)),
      overflow: nav.scrollWidth - nav.clientWidth,
      free: Math.floor(nav.clientWidth - list.getBoundingClientRect().width),
      labels: links.map((link) => link.textContent),
      titles: links.map((link) => link.getAttribute("title")),
      labelWidths: links.map((link) => Math.round(link.querySelector(".nav-label")?.getBoundingClientRect().width ?? 0)),
      shorts: links.map((link) => {
        const short = link.querySelector(".nav-short");
        return short === null ? "" : getComputedStyle(short, "::before").content.replace(/^"|"$/g, "");
      }),
      shortWidths: links.map((link) => Math.round(link.querySelector(".nav-short")?.getBoundingClientRect().width ?? 0)),
      shortBelowIcon: links.map((link) => {
        const icon = link.querySelector("svg")?.getBoundingClientRect();
        const short = link.querySelector(".nav-short")?.getBoundingClientRect();
        return icon !== undefined && short !== undefined && short.width > 0 && short.top >= icon.bottom - 0.5;
      }),
    };
  });
}

/** Whether the page itself is wider than the window (a horizontal scroll bar). */
async function pageOverflows(page: Page): Promise<boolean> {
  return page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
}

test("every navigation entry shows a hidden icon and a readable text", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/");
  const links = page.getByRole("navigation", { name: "Main navigation" }).getByRole("link");
  await expect(links).toHaveText(ENGLISH_ENTRIES);
  for (const link of await links.all()) {
    const icon = link.locator("svg");
    await expect(icon).toBeVisible();
    await expect(icon).toHaveAttribute("aria-hidden", "true");
    await expect(link.locator(".nav-label")).toBeVisible();
  }
});

for (const { viewport, texts } of [
  { viewport: { width: 1280, height: 800 }, texts: true },
  { viewport: { width: 1024, height: 768 }, texts: false },
  { viewport: { width: 768, height: 1024 }, texts: false },
]) {
  test(`the header stays on one line in English and German at ${String(viewport.width)} px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto("/");
    const navigation = page.getByRole("navigation", { name: "Main navigation" });
    await expect(navigation.getByRole("link", { name: ENGLISH_LAST })).toBeVisible();
    await expect(page.getByTestId("navigation-menu-button")).toHaveCount(0);
    const english = await headerLayout(page);
    expect(english.labels).toEqual(ENGLISH_ENTRIES);
    expect(english.titles).toEqual(ENGLISH_ENTRIES);

    await page.getByTestId("user-menu-button").click();
    await page.getByTestId("language-switch").selectOption("de");
    await expect(page.getByRole("navigation", { name: "Hauptnavigation" }).getByRole("link", { name: GERMAN_LAST })).toBeVisible();
    const german = await headerLayout(page);
    expect(german.labels).toEqual(GERMAN_ENTRIES);
    expect(german.titles).toEqual(GERMAN_ENTRIES);

    for (const [layout, shorts] of [
      [english, ENGLISH_SHORT],
      [german, GERMAN_SHORT],
    ] as const) {
      // All entries on the same line, nothing to scroll, neither the navigation nor the page.
      expect(new Set(layout.tops).size, `tops ${layout.tops.join(", ")}`).toBe(1);
      expect(layout.overflow).toBeLessThanOrEqual(0);
      expect(layout.free).toBeGreaterThanOrEqual(0);
      if (texts) {
        // Every text is shown next to its icon; no short texts.
        for (const width of layout.labelWidths) {
          expect(width).toBeGreaterThan(10);
        }
        for (const width of layout.shortWidths) {
          expect(width).toBe(0);
        }
      } else {
        // The full texts take no room (they stay for screen readers and as tooltip) ...
        for (const width of layout.labelWidths) {
          expect(width).toBeLessThanOrEqual(1);
        }
        // ... and every entry shows its short text below the icon.
        expect(layout.shorts).toEqual(shorts);
        for (const width of layout.shortWidths) {
          expect(width).toBeGreaterThan(10);
        }
        expect(layout.shortBelowIcon).toEqual(shorts.map(() => true));
      }
    }
    expect(await pageOverflows(page)).toBe(false);
    test.info().annotations.push({
      type: "free width",
      description: `en ${String(english.free)} px, de ${String(german.free)} px at ${String(viewport.width)} px`,
    });
    expect(german.header).toBe(english.header);
    expect(german.tops).toEqual(english.tops);
  });
}

for (const { language, navigationName, menuName, last, shorts } of [
  { language: "de", navigationName: "Hauptnavigation", menuName: "Benutzermenü", last: GERMAN_LAST, shorts: GERMAN_SHORT },
  { language: "en", navigationName: "Main navigation", menuName: "Account menu", last: ENGLISH_LAST, shorts: ENGLISH_SHORT },
]) {
  test(`at 768 px in ${language} a user name as wide as its button covers nothing and widens nothing`, async ({ page }) => {
    // The answer of /api/v1/me/ gets a user name longer than the button can show (max-w-48, cut off with an
    // ellipsis). The real answer is read in the browser (only the browser reaches the API under "localhost").
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto("/");
    const me = await page.evaluate(async () => (await fetch("/api/v1/me/")).json() as Promise<Record<string, unknown>>);
    await page.route(
      (url) => url.pathname === "/api/v1/me/",
      async (route) => {
        await route.fulfill({ json: { ...me, username: "e2e-manager-with-a-very-long-user-name" } });
      },
    );
    await page.reload();
    await page.getByTestId("user-menu-button").click();
    await page.getByTestId("language-switch").selectOption(language);
    await page.getByTestId("user-menu-button").click();
    await expect(page.getByTestId("user-menu")).toBeHidden();
    const navigation = page.getByRole("navigation", { name: navigationName });
    await expect(navigation.getByRole("link", { name: last })).toBeVisible();
    const button = page.getByTestId("user-menu-button");
    await expect(button).toHaveAccessibleName(`${menuName}: e2e-manager-with-a-very-long-user-name`);

    const layout = await headerLayout(page);
    const [navBox, buttonBox, headerBox] = await Promise.all([
      navigation.boundingBox(),
      button.boundingBox(),
      page.getByRole("banner").boundingBox(),
    ]);
    // Seven entries with "Ask" instead of the self-test (work order 134).
    expect(layout.shorts).toEqual(shorts);
    // The button is as wide as it may be (192 px); the navigation ends before it and does not scroll.
    expect(Math.round(buttonBox?.width ?? 0)).toBe(192);
    expect((navBox?.x ?? 0) + (navBox?.width ?? 0)).toBeLessThanOrEqual(buttonBox?.x ?? 0);
    expect(layout.overflow).toBeLessThanOrEqual(0);
    expect(layout.free).toBeGreaterThanOrEqual(0);
    expect(new Set(layout.tops).size).toBe(1);
    // Same header height as everywhere (76 px), and the page does not scroll sideways.
    expect(Math.round(headerBox?.height ?? 0)).toBe(76);
    expect(await pageOverflows(page)).toBe(false);
    test.info().annotations.push({
      type: "free width",
      description: `${language}, long user name: ${String(layout.free)} px at 768 px`,
    });
    // Back to English, for the other tests of this browser context.
    await page.getByTestId("user-menu-button").click();
    await page.getByTestId("language-switch").selectOption("en");
  });
}

test("from 768 px the user menu holds the self-test; it opens /selftest and closes", async ({ page }) => {
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Structure");
  const navigation = page.getByRole("navigation", { name: "Main navigation" });
  await expect(navigation.getByRole("link", { name: "Self-test" })).toHaveCount(0);
  const button = page.getByTestId("user-menu-button");
  const menu = page.getByTestId("user-menu");
  await button.click();
  await expect(menu).toBeVisible();
  // Settings first, then the self-test, both with icon and full text.
  await expect(menu.getByRole("link")).toHaveText(["Settings", "Self-test"]);
  const link = menu.getByRole("link", { name: "Self-test" });
  await expect(link.locator("svg")).toHaveAttribute("aria-hidden", "true");
  await link.click();
  await expect(page).toHaveURL(/\/selftest$/);
  await expect(menu).toBeHidden();
  await expect(button).toHaveAttribute("aria-expanded", "false");
  await expect(page.getByRole("heading", { level: 1, name: "Self-test" })).toBeFocused();
  await button.click();
  await expect(link).toHaveAttribute("aria-current", "page");
});

test("the entry 'Ask' opens /ask, is marked current and the focus moves to the heading", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Structure");
  const entry = page.getByRole("navigation", { name: "Main navigation" }).getByRole("link", { name: "Ask" });
  await expect(entry.locator("svg")).toHaveAttribute("aria-hidden", "true");
  await entry.click();
  await expect(page).toHaveURL(/\/ask$/);
  await expect(entry).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("heading", { level: 1, name: "Ask" })).toBeFocused();
  await expect(page).toHaveTitle("Ask – 2x");
});

test("at 1024 px the icon of an entry opens its page and keeps its name", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.goto("/");
  const entry = page.getByRole("navigation", { name: "Main navigation" }).getByRole("link", { name: "Ingestion" });
  await expect(entry).toHaveAttribute("title", "Ingestion");
  await expect(entry.locator("svg")).toBeVisible();
  await entry.click();
  await expect(page).toHaveURL(/\/ingest$/);
  await expect(entry).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Ingestion");
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test("a button 'Menu' opens every entry and the user menu, within the screen", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Structure");
    const button = page.getByRole("button", { name: "Menu" });
    const panel = page.getByTestId("navigation-menu");
    // Closed: no navigation bar, no scroll bar, the page itself never scrolls sideways.
    await expect(button).toHaveAttribute("aria-expanded", "false");
    await expect(button).toHaveAttribute("aria-controls", (await panel.getAttribute("id")) ?? "");
    await expect(panel).toBeHidden();
    await expect(page.getByRole("navigation", { name: "Main navigation" })).toHaveCount(0);
    await expect(page.getByTestId("user-menu-button")).toHaveCount(0);
    expect(await pageOverflows(page)).toBe(false);
    // Brand mark and button on one line.
    const brand = await page.getByRole("banner").getByRole("link", { name: "2x" }).boundingBox();
    const buttonBox = await button.boundingBox();
    expect(Math.abs((brand?.y ?? 0) + (brand?.height ?? 0) / 2 - ((buttonBox?.y ?? 0) + (buttonBox?.height ?? 0) / 2))).toBeLessThan(4);

    await button.click();
    await expect(button).toHaveAttribute("aria-expanded", "true");
    await expect(panel).toBeVisible();
    const navigation = panel.getByRole("navigation", { name: "Main navigation" });
    const links = navigation.getByRole("link");
    await expect(links).toHaveText(ENGLISH_ENTRIES);
    await expect(navigation.getByRole("link", { name: "Structure" })).toHaveAttribute("aria-current", "page");
    // One entry per line, every text visible, everything inside the screen.
    const boxes = await Promise.all((await links.all()).map((link) => link.boundingBox()));
    const tops = boxes.map((box) => box?.y ?? 0);
    expect([...tops].sort((a, b) => a - b)).toEqual(tops);
    expect(new Set(tops).size).toBe(ENGLISH_ENTRIES.length);
    for (const box of boxes) {
      expect(box?.x ?? -1).toBeGreaterThanOrEqual(0);
      expect((box?.x ?? 0) + (box?.width ?? 0)).toBeLessThanOrEqual(375);
      // Touch targets at least 40 px high.
      expect(box?.height ?? 0).toBeGreaterThanOrEqual(40);
    }
    for (const label of await navigation.locator(".nav-label").all()) {
      await expect(label).toBeVisible();
    }
    await expect(panel.getByTestId("user-role")).toHaveText("Manage");
    await expect(panel.getByRole("link", { name: "Settings" })).toBeVisible();
    await expect(panel.getByRole("combobox", { name: "Language" })).toBeVisible();
    await expect(panel.getByRole("button", { name: "Sign out" })).toBeVisible();
    const panelBox = await panel.boundingBox();
    expect(panelBox?.x ?? -1).toBeGreaterThanOrEqual(0);
    expect((panelBox?.x ?? 0) + (panelBox?.width ?? 0)).toBeLessThanOrEqual(375);
    expect((panelBox?.y ?? 0) + (panelBox?.height ?? 0)).toBeLessThanOrEqual(812);
    expect(await pageOverflows(page)).toBe(false);

    // A choice closes the menu and opens the page; the focus moves on to its heading.
    await navigation.getByRole("link", { name: "Ask" }).click();
    await expect(page).toHaveURL(/\/ask$/);
    await expect(panel).toBeHidden();
    await expect(button).toHaveAttribute("aria-expanded", "false");
    await expect(page.getByRole("heading", { level: 1, name: "Ask" })).toBeFocused();
    await button.click();
    await expect(navigation.getByRole("link", { name: "Ask" })).toHaveAttribute("aria-current", "page");

    // The self-test sits in the user part of the panel, after the settings (work order 134).
    const selftest = panel.getByTestId("selftest-link");
    await expect(navigation.getByRole("link", { name: "Self-test" })).toHaveCount(0);
    await expect(selftest).toHaveAccessibleName("Self-test");
    await expect(selftest).toBeVisible();
    await selftest.click();
    await expect(page).toHaveURL(/\/selftest$/);
    await expect(panel).toBeHidden();
    await expect(page.getByRole("heading", { level: 1, name: "Self-test" })).toBeFocused();
    await button.click();
    await expect(selftest).toHaveAttribute("aria-current", "page");
    expect(await pageOverflows(page)).toBe(false);
  });

  test("the menu works with the keyboard alone", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Structure");
    const button = page.getByRole("button", { name: "Menu" });
    const panel = page.getByTestId("navigation-menu");
    await button.focus();
    await page.keyboard.press("Enter");
    await expect(panel).toBeVisible();
    await expect(button).toHaveAttribute("aria-expanded", "true");
    // The next stop after the button is the first entry of the list.
    await page.keyboard.press("Tab");
    await expect(panel.getByRole("link", { name: "Structure" })).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(panel.getByRole("link", { name: "Map" })).toBeFocused();
    // Escape closes it and gives the focus back to the button.
    await page.keyboard.press("Escape");
    await expect(panel).toBeHidden();
    await expect(button).toBeFocused();
    await expect(button).toHaveAttribute("aria-expanded", "false");
    // Space opens it again; choosing with Enter opens the page.
    await page.keyboard.press("Space");
    await expect(panel).toBeVisible();
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    await expect(panel.getByRole("link", { name: "Search" })).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/search$/);
    await expect(panel).toBeHidden();
    await expect(page.getByRole("heading", { level: 1, name: "Search" })).toBeFocused();

    // Tab after the last control of the panel ("Sign out") closes it; the focus goes on into the page,
    // never onto content hidden under the panel (WCAG 2.4.11), and is not taken back to the button.
    await button.focus();
    await page.keyboard.press("Enter");
    await expect(panel).toBeVisible();
    await panel.getByRole("button", { name: "Sign out" }).focus();
    await page.keyboard.press("Tab");
    await expect(panel).toBeHidden();
    await expect(button).toHaveAttribute("aria-expanded", "false");
    await expect(button).not.toBeFocused();
    const focused = page.locator(":focus");
    await expect(focused).toHaveCount(1);
    expect(await focused.evaluate((element) => document.querySelector("main")?.contains(element) ?? false)).toBe(true);
    await expect(focused).toBeInViewport();
    // Shift+Tab from the button leaves it closed as well.
    await button.focus();
    await page.keyboard.press("Enter");
    await expect(panel).toBeVisible();
    await page.keyboard.press("Shift+Tab");
    await expect(panel).toBeHidden();
  });

  test("the menu speaks German and changes the language", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Menu" }).click();
    await page.getByTestId("navigation-menu").getByRole("combobox", { name: "Language" }).selectOption("de");
    const button = page.getByRole("button", { name: "Menü" });
    await expect(button).toBeVisible();
    const panel = page.getByTestId("navigation-menu");
    // Still open after the change of language.
    await expect(panel).toBeVisible();
    await expect(panel.getByRole("navigation", { name: "Hauptnavigation" }).getByRole("link")).toHaveText(GERMAN_ENTRIES);
    expect(await pageOverflows(page)).toBe(false);
    // Back to English, for the other tests of this browser context.
    await panel.getByRole("combobox", { name: "Sprache" }).selectOption("en");
    await expect(page.getByRole("button", { name: "Menu" })).toBeVisible();
  });

  test("the header bar returns at 768 px", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Menu" }).click();
    await page.setViewportSize({ width: 768, height: 1024 });
    await expect(page.getByRole("navigation", { name: "Main navigation" }).getByRole("link")).toHaveText(ENGLISH_ENTRIES);
    await expect(page.getByTestId("navigation-menu-button")).toHaveCount(0);
    await expect(page.getByTestId("user-menu-button")).toBeVisible();
    await page.setViewportSize({ width: 767, height: 1024 });
    await expect(page.getByTestId("navigation-menu")).toBeHidden();
    await expect(page.getByRole("button", { name: "Menu" })).toHaveAttribute("aria-expanded", "false");
  });
});

test("an unknown address shows NotFound inside the frame", async ({ page }) => {
  const consoleErrors = collectConsoleErrors(page);

  const response = await page.goto("/no-such-page");
  // Django serves the UI for this path; the UI itself decides that it is unknown.
  expect(response?.status()).toBe(200);

  await expect(page.getByTestId("not-found")).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Page not found");
  await expect(page.getByRole("navigation", { name: "Main navigation" })).toBeVisible();

  await page.getByRole("link", { name: "Go to the structure" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Structure");

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});
