import { expect, test } from "./fixtures";

// Skip link, browser title per page and the focus after a change of page
// (work order 078; WCAG 2.4.1, 2.4.2, 2.4.3), in the real browser.
test.use({ locale: "en-US" });

test("the skip link is the first stop of the keyboard and leads to the content", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Structure");
  const skip = page.getByRole("link", { name: "Skip to content" });
  // Out of sight until it has the focus.
  await expect(skip).not.toBeInViewport();

  await page.keyboard.press("Tab");
  await expect(skip).toBeFocused();
  await expect(skip).toBeInViewport();

  await page.keyboard.press("Enter");
  await expect(page.getByRole("main")).toBeFocused();
  await expect(page).toHaveURL(/\/$/);
  // The next Tab leaves the header behind.
  await page.keyboard.press("Tab");
  await expect(page.getByRole("main").locator(":focus")).toHaveCount(1);
});

test("every page names itself in the browser title", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("Structure – 2x");
  const navigation = page.getByRole("navigation", { name: "Main navigation" });
  for (const [entry, title] of [
    ["Search", "Search – 2x"],
    ["Ingestion", "Ingestion – 2x"],
    ["Change log", "Change log – 2x"],
    ["Ask", "Ask – 2x"],
  ] as const) {
    await navigation.getByRole("link", { name: entry }).click();
    await expect(page).toHaveTitle(title);
  }
  await page.goto("/no-such-page");
  await expect(page).toHaveTitle("Page not found – 2x");
});

test("after a change of page the focus is on its heading, not on the first load", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Structure");
  await expect(page.locator("body")).toBeFocused();

  const navigation = page.getByRole("navigation", { name: "Main navigation" });
  await navigation.getByRole("link", { name: "Ask" }).focus();
  await page.keyboard.press("Enter");
  const heading = page.getByRole("heading", { level: 1, name: "Ask" });
  await expect(heading).toBeFocused();

  // Back in the history moves the focus as well.
  await page.goBack();
  await expect(page.getByRole("heading", { level: 1, name: "Structure" })).toBeFocused();
});
