import { expect, test } from "./fixtures";

// The page starts in the browser language; this test fixes it to English.
test.use({ locale: "en-US" });

test("switching to German translates the page and sets <html lang>", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });
  page.on("pageerror", (error) => {
    consoleErrors.push(error.message);
  });

  const response = await page.goto("/selftest");
  expect(response?.status()).toBe(200);

  await expect(page.getByTestId("database-heading")).toHaveText("Database");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");

  await page.getByLabel("Language").selectOption("de");

  await expect(page.getByTestId("database-heading")).toHaveText("Datenbank");
  await expect(page.getByTestId("worker-heading")).toHaveText("Hintergrunddienst");
  await expect(page.getByRole("heading", { level: 2 })).toHaveText("Selbsttest");
  await expect(page.locator("html")).toHaveAttribute("lang", "de");

  // The choice is remembered across a reload.
  await page.reload();
  await expect(page.getByTestId("database-heading")).toHaveText("Datenbank");
  await expect(page.locator("html")).toHaveAttribute("lang", "de");

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});
