import { expect, type Page, test } from "@playwright/test";

// Routing of the web UI as served by Django: the start page, a click through
// the navigation, deep links and the page for unknown addresses.
test.use({ locale: "en-US" });

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

  const response = await page.goto("/devices/plc-1");
  expect(response?.status()).toBe(200);

  await expect(page.getByRole("heading", { level: 2 })).toHaveText("Device");
  await expect(page.getByTestId("device-id")).toHaveText("plc-1");

  expect(consoleErrors, "errors in the browser console").toEqual([]);
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
