import type { Page } from "@playwright/test";

import { expect, test } from "./fixtures";

// Settings page, colour modes, accent, font and motion (work order 070).
// Every test starts with an empty localStorage (new browser context).
test.use({ locale: "en-US" });

/** Collects console errors and uncaught errors of the page. */
function watchErrors(page: Page): string[] {
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

/** Background colour of <html> as the browser computes it. */
async function pageBackground(page: Page): Promise<string> {
  return page.evaluate(() => getComputedStyle(document.documentElement).backgroundColor);
}

const LIGHT_CANVAS = "rgb(248, 246, 249)";
const DARK_CANVAS = "rgb(25, 23, 29)";

test.describe("settings", () => {
  test("changes appearance and accent at once, and keeps them after a reload", async ({ page }) => {
    const errors = watchErrors(page);
    await page.goto("/");
    await page.getByTestId("user-menu-button").click();
    await page.getByTestId("settings-link").click();
    await expect(page).toHaveURL(/\/settings$/);
    await expect(page.getByRole("heading", { level: 1, name: "Settings" })).toBeVisible();

    const html = page.locator("html");
    await expect(html).toHaveAttribute("data-theme", "light");
    await expect(html).toHaveAttribute("data-accent", "aubergine");

    await page.getByRole("radio", { name: "Dark" }).check();
    await expect(html).toHaveAttribute("data-theme", "dark");
    expect(await pageBackground(page)).toBe(DARK_CANVAS);

    await page.getByRole("radio", { name: "Indigo" }).check();
    await expect(html).toHaveAttribute("data-accent", "indigo");
    // The accent reaches the components: the current entry (the settings link) is underlined in it.
    await expect(page.getByTestId("settings-link")).toHaveAttribute("aria-current", "page");
    expect(
      await page.getByTestId("settings-link").evaluate((link) => getComputedStyle(link).backgroundImage),
    ).toContain("rgb(166, 171, 223)");

    await page.reload();
    await expect(html).toHaveAttribute("data-theme", "dark");
    await expect(html).toHaveAttribute("data-accent", "indigo");
    await expect(page.getByRole("radio", { name: "Dark" })).toBeChecked();
    await expect(page.getByRole("radio", { name: "Indigo" })).toBeChecked();

    await page.getByRole("radio", { name: "Same as the system" }).check();
    await expect(html).toHaveAttribute("data-theme", "light");
    expect(errors, "errors in the browser console").toEqual([]);
  });

  test("sets the colours before the first paint, without any script of the bundle", async ({ page }) => {
    await page.goto("/settings");
    await page.getByRole("radio", { name: "Dark" }).check();
    await page.getByRole("radio", { name: "Umber" }).check();

    // Without the JavaScript bundle only the inline script of index.html runs.
    await page.route("**/static/assets/*.js", (route) => route.abort());
    await page.reload();
    const html = page.locator("html");
    await expect(html).toHaveAttribute("data-theme", "dark");
    await expect(html).toHaveAttribute("data-accent", "umber");
    expect(await pageBackground(page)).toBe(DARK_CANVAS);
  });

  test("shares the language with the switch in the user menu", async ({ page }) => {
    await page.goto("/settings");
    await page.getByRole("combobox", { name: "Language of the interface" }).selectOption("de");
    await expect(page.getByRole("heading", { level: 1, name: "Einstellungen" })).toBeVisible();
    await expect(page.getByTestId("language-switch")).toHaveValue("de");
    await expect(page.locator("html")).toHaveAttribute("lang", "de");
    await page.getByTestId("user-menu-button").click();
    await page.getByTestId("language-switch").selectOption("en");
    await expect(page.getByRole("combobox", { name: "Language of the interface" })).toHaveValue("en");
  });

  test("reduces motion on request: no animation classes, nothing running", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.locator("h1 .tx-word").first()).toBeAttached();
    await page.getByRole("checkbox", { name: "Reduce motion" }).check();
    await expect(page.locator("html")).toHaveAttribute("data-motion", "reduce");
    await expect(page.locator("[class*='tx-']")).toHaveCount(0);
    expect(await page.evaluate(() => document.getAnimations().length)).toBe(0);

    await page.reload();
    await expect(page.getByRole("heading", { level: 1, name: "Settings" })).toBeVisible();
    await expect(page.locator("[class*='tx-']")).toHaveCount(0);
  });

  test("uses the bundled Inter with ss02 and loads nothing from elsewhere", async ({ page }) => {
    const requested: string[] = [];
    page.on("request", (request) => {
      requested.push(request.url());
    });
    await page.goto("/settings");
    const origin = new URL(page.url()).origin;
    await expect(page.getByRole("heading", { level: 1, name: "Settings" })).toBeVisible();
    const font = await page.evaluate(async () => {
      await document.fonts.ready;
      const style = getComputedStyle(document.body);
      return {
        loaded: document.fonts.check('16px "Inter"'),
        family: style.fontFamily,
        features: getComputedStyle(document.documentElement).fontFeatureSettings,
      };
    });
    expect(font.loaded).toBe(true);
    expect(font.family.startsWith('Inter') || font.family.startsWith('"Inter"')).toBe(true);
    expect(font.features).toContain("ss02");
    expect(requested.some((url) => /\/static\/assets\/InterVariable-[\w-]+\.woff2$/.test(url))).toBe(true);
    expect(requested.filter((url) => url.startsWith("http") && new URL(url).origin !== origin)).toEqual([]);
  });

  test("keeps the width of every navigation entry when the current page changes", async ({ page }) => {
    await page.goto("/");
    const nav = page.getByRole("navigation", { name: "Main navigation" });
    const widths = async (): Promise<number[]> =>
      nav.getByRole("link").evaluateAll((links) => links.map((link) => link.getBoundingClientRect().width));
    await expect(nav.getByRole("link", { name: "Structure" })).toHaveAttribute("aria-current", "page");
    const onStructure = await widths();
    await nav.getByRole("link", { name: "Ask" }).click();
    await expect(nav.getByRole("link", { name: "Ask" })).toHaveAttribute("aria-current", "page");
    expect(await widths()).toEqual(onStructure);
  });
});

test.describe("operating system preferences", () => {
  test.use({ colorScheme: "dark" });

  test("starts dark when the system is dark and nothing is stored", async ({ page }) => {
    await page.goto("/settings");
    const html = page.locator("html");
    await expect(html).toHaveAttribute("data-theme", "dark");
    expect(await pageBackground(page)).toBe(DARK_CANVAS);
    await expect(page.getByRole("radio", { name: "Same as the system" })).toBeChecked();
    await expect(page.getByTestId("settings-system-mode")).toHaveText("Your system currently uses the dark appearance.");

    // An explicit choice wins over the system.
    await page.getByRole("radio", { name: "Light" }).check();
    await expect(html).toHaveAttribute("data-theme", "light");
    expect(await pageBackground(page)).toBe(LIGHT_CANVAS);
  });
});

test.describe("reduced motion of the system", () => {
  test.use({ reducedMotion: "reduce" });

  test("shows no animation when the system asks for reduced motion", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.getByRole("heading", { level: 1, name: "Settings" })).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("data-motion", "reduce");
    await expect(page.locator("[class*='tx-']")).toHaveCount(0);
    await expect(page.getByTestId("settings-system-motion")).toBeVisible();
    await expect(page.getByRole("checkbox", { name: "Reduce motion" })).not.toBeChecked();
  });
});
