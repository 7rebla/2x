import type { Page } from "@playwright/test";

import { expect, test } from "./fixtures";

// Brand mark in the header, favicon and touch icon (work order 072).
test.use({ locale: "en-US" });

const BRAND_LIGHT = "rgb(118, 84, 119)";
const BRAND_DARK = "rgb(180, 150, 184)";

/** Colour the brand mark draws with (its currentColor). */
async function markColour(page: Page): Promise<string> {
  return page.getByTestId("brand-mark").evaluate((mark) => getComputedStyle(mark).color);
}

test.describe("brand", () => {
  test("shows the brand mark next to the name 2x in light mode", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "light" });
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");

    const heading = page.getByRole("heading", { level: 1, name: "2x" });
    const link = heading.getByRole("link", { name: "2x" });
    await expect(link).toHaveAttribute("href", "/");
    const mark = link.getByTestId("brand-mark");
    await expect(mark).toHaveAttribute("aria-hidden", "true");
    await expect(mark).toHaveAttribute("data-form", "master");
    await expect(mark.locator("svg")).toBeVisible();
    const box = await mark.boundingBox();
    expect(box?.width).toBe(36);
    expect(box?.height).toBe(36);
    expect(await markColour(page)).toBe(BRAND_LIGHT);
    // The mark stands left of the name.
    const nameBox = await link.getByText("2x", { exact: true }).boundingBox();
    expect((box?.x ?? 0) + (box?.width ?? 0)).toBeLessThan(nameBox?.x ?? 0);
  });

  test("shows the brand mark in the dark brand colour in dark mode", async ({ page }) => {
    await page.emulateMedia({ colorScheme: "dark" });
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

    const link = page.getByRole("heading", { level: 1 }).getByRole("link", { name: "2x" });
    await expect(link.getByTestId("brand-mark").locator("svg")).toBeVisible();
    expect(await markColour(page)).toBe(BRAND_DARK);
  });

  test("keeps the brand colour when the accent changes", async ({ page }) => {
    await page.goto("/settings");
    await page.getByRole("radio", { name: "Indigo" }).check();
    await expect(page.locator("html")).toHaveAttribute("data-accent", "indigo");
    expect(await markColour(page)).toBe(BRAND_LIGHT);
  });

  test("links favicon and touch icon in the page head", async ({ page }) => {
    await page.goto("/");
    const head = page.locator("head");
    await expect(page).toHaveTitle("2x");
    for (const [selector, contentType] of [
      ['link[rel="icon"][type="image/svg+xml"]', "image/svg+xml"],
      ['link[rel="icon"][sizes="16x16 32x32 48x48"]', "image/x-icon"],
      ['link[rel="apple-touch-icon"]', "image/png"],
    ] as const) {
      const href = await head.locator(selector).getAttribute("href");
      expect(href, selector).not.toBeNull();
      const response = await fetchInPage(page, href ?? "");
      expect(response.status, String(href)).toBe(200);
      expect(response.contentType.split(";")[0], String(href)).toBe(contentType);
    }
  });

  for (const [path, contentType] of [
    ["/favicon.ico", "image/x-icon"],
    ["/favicon.svg", "image/svg+xml"],
    ["/apple-touch-icon.png", "image/png"],
  ] as const) {
    test(`serves ${path} at the root of the site`, async ({ page }) => {
      await page.goto("/");
      const response = await fetchInPage(page, path);
      expect(response.status).toBe(200);
      expect(response.contentType).toBe(contentType);
      expect(response.isPage).toBe(false);
    });
  }
});

interface FetchedFile {
  readonly status: number;
  readonly contentType: string;
  /** True if the answer is the index.html of the UI. */
  readonly isPage: boolean;
}

/**
 * Fetches a path from inside the page: the browser maps "localhost" to the API
 * host (playwright.config.ts), Playwright's own request client does not.
 */
async function fetchInPage(page: Page, path: string): Promise<FetchedFile> {
  return page.evaluate(async (url) => {
    const response = await fetch(url, { cache: "no-store" });
    const text = await response.text();
    return {
      status: response.status,
      contentType: response.headers.get("content-type") ?? "",
      isPage: text.includes('<div id="root">'),
    };
  }, path);
}
