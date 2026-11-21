import { expect, test } from "@playwright/test";

// Acceptance of milestone M0: the page served by Django shows a value from the
// database and a result from the worker, read live through the API.
test("self-test page shows the database version and the worker result", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });
  page.on("pageerror", (error) => {
    consoleErrors.push(error.message);
  });

  const response = await page.goto("/");
  expect(response?.status()).toBe(200);

  // Wait for content (with the expect timeout), never for a fixed time.
  await expect(page.getByTestId("database-version")).toHaveText(/\d+\.\d+/);
  await expect(page.getByTestId("worker-result")).toHaveText("pong");
  await expect(page.getByTestId("database-status")).toHaveText("OK");
  await expect(page.getByTestId("worker-status")).toHaveText("OK");

  await expect(page.getByTestId("selftest-loading")).toHaveCount(0);
  await expect(page.getByTestId("selftest-error")).toHaveCount(0);
  await expect(page.getByTestId("database-error")).toHaveCount(0);
  await expect(page.getByTestId("worker-error")).toHaveCount(0);

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});
