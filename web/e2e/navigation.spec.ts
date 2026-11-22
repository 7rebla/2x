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

test("a click in the navigation leads from / to the self-test page", async ({ page }) => {
  const consoleErrors = collectConsoleErrors(page);

  const response = await page.goto("/");
  expect(response?.status()).toBe(200);
  const navigation = page.getByRole("navigation", { name: "Main navigation" });
  await expect(page.getByRole("heading", { level: 2 })).toHaveText("Structure");
  await expect(navigation.getByRole("link", { name: "Structure" })).toHaveAttribute("aria-current", "page");

  await navigation.getByRole("link", { name: "Self-test" }).click();

  await expect(page).toHaveURL(/\/selftest$/);
  await expect(navigation.getByRole("link", { name: "Self-test" })).toHaveAttribute("aria-current", "page");
  await expect(page.getByTestId("worker-result")).toHaveText("pong");
  await expect(page.getByTestId("database-version")).toHaveText(/\d+\.\d+/);

  // Back in the browser history returns to the start page.
  await page.goBack();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { level: 2 })).toHaveText("Structure");

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
  await expect(page.getByRole("heading", { level: 2 })).toHaveText("Page not found");
  await expect(page.getByRole("navigation", { name: "Main navigation" })).toBeVisible();

  expect(
    consoleErrors.filter((message) => !message.includes("status of 404")),
    "errors in the browser console",
  ).toEqual([]);
});

// Header with icons (work order 071): every entry shows an icon hidden from
// assistive technology and a readable text; the header stays on one line in
// English and German and does not change its height when the language changes.
// From 1280 px (xl) the texts are shown and the header is wider than the page;
// below that only the icons, with the text as accessible name and tooltip
// (work order 055, seven entries).

const ENGLISH_ENTRIES = ["Structure", "Map", "Search", "Ingestion", "Import", "Change log", "Self-test"];
const GERMAN_ENTRIES = ["Struktur", "Landkarte", "Suche", "Einlesen", "Import", "Änderungsprotokoll", "Selbsttest"];

interface HeaderLayout {
  readonly header: number;
  readonly tops: number[];
  readonly overflow: number;
  /** Width left free in the navigation after the last entry. */
  readonly free: number;
  readonly labels: string[];
  readonly titles: (string | null)[];
  readonly labelWidths: number[];
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
    };
  });
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
]) {
  test(`the header stays on one line in English and German at ${String(viewport.width)} px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto("/");
    const navigation = page.getByRole("navigation", { name: "Main navigation" });
    await expect(navigation.getByRole("link", { name: "Self-test" })).toBeVisible();
    const english = await headerLayout(page);
    expect(english.labels).toEqual(ENGLISH_ENTRIES);
    expect(english.titles).toEqual(ENGLISH_ENTRIES);

    await page.getByTestId("user-menu-button").click();
    await page.getByTestId("language-switch").selectOption("de");
    await expect(page.getByRole("navigation", { name: "Hauptnavigation" }).getByRole("link", { name: "Selbsttest" })).toBeVisible();
    const german = await headerLayout(page);
    expect(german.labels).toEqual(GERMAN_ENTRIES);
    expect(german.titles).toEqual(GERMAN_ENTRIES);

    for (const layout of [english, german]) {
      // All entries on the same line, nothing to scroll.
      expect(new Set(layout.tops).size, `tops ${layout.tops.join(", ")}`).toBe(1);
      expect(layout.overflow).toBeLessThanOrEqual(0);
      expect(layout.free).toBeGreaterThanOrEqual(0);
      if (texts) {
        // Every text is shown.
        for (const width of layout.labelWidths) {
          expect(width).toBeGreaterThan(10);
        }
      } else {
        // Only the icons: the texts take no room (they stay for screen readers and as tooltip).
        for (const width of layout.labelWidths) {
          expect(width).toBeLessThanOrEqual(1);
        }
      }
    }
    test.info().annotations.push({
      type: "free width",
      description: `en ${String(english.free)} px, de ${String(german.free)} px at ${String(viewport.width)} px`,
    });
    expect(german.header).toBe(english.header);
    expect(german.tops).toEqual(english.tops);
  });
}

test("at 1024 px the icon of an entry opens its page and keeps its name", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.goto("/");
  const entry = page.getByRole("navigation", { name: "Main navigation" }).getByRole("link", { name: "Ingestion" });
  await expect(entry).toHaveAttribute("title", "Ingestion");
  await expect(entry.locator("svg")).toBeVisible();
  await entry.click();
  await expect(page).toHaveURL(/\/ingest$/);
  await expect(entry).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("heading", { level: 2 })).toHaveText("Ingestion");
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test("the navigation stays usable without scrolling the whole page", async ({ page }) => {
    await page.goto("/");
    const navigation = page.getByRole("navigation", { name: "Main navigation" });
    await expect(navigation.getByRole("link", { name: "Structure" })).toHaveAttribute("aria-current", "page");
    const layout = await headerLayout(page);
    expect(new Set(layout.tops).size).toBe(1);
    // The page itself never scrolls sideways.
    const pageOverflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(pageOverflow).toBeLessThanOrEqual(0);
    // Icons only; the texts stay as accessible names and tooltips.
    const selftest = navigation.getByRole("link", { name: "Self-test" });
    await expect(selftest).toHaveAttribute("title", "Self-test");
    await expect(selftest.locator("svg")).toBeVisible();
    await selftest.click();
    await expect(page).toHaveURL(/\/selftest$/);
    await expect(selftest).toHaveAttribute("aria-current", "page");
    // The user menu still opens and fits on the screen.
    await page.getByTestId("user-menu-button").click();
    const menu = page.getByTestId("user-menu");
    await expect(menu).toBeVisible();
    const box = await menu.boundingBox();
    expect(box?.x ?? -1).toBeGreaterThanOrEqual(0);
    expect((box?.x ?? 0) + (box?.width ?? 0)).toBeLessThanOrEqual(375);
  });
});

test("an unknown address shows NotFound inside the frame", async ({ page }) => {
  const consoleErrors = collectConsoleErrors(page);

  const response = await page.goto("/no-such-page");
  // Django serves the UI for this path; the UI itself decides that it is unknown.
  expect(response?.status()).toBe(200);

  await expect(page.getByTestId("not-found")).toBeVisible();
  await expect(page.getByRole("heading", { level: 2 })).toHaveText("Page not found");
  await expect(page.getByRole("navigation", { name: "Main navigation" })).toBeVisible();

  await page.getByRole("link", { name: "Go to the structure" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { level: 2 })).toHaveText("Structure");

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});
