import { expect, test } from "./fixtures";

// Acceptance of milestone M0: the page served by Django shows a value from the
// database and a result from the worker, read live through the API. Since
// work order 027 only signed-in users with a role may call the self-test; the
// test account comes from the shared sign-in step (fixtures.ts). The page
// is opened directly at /selftest, so Django's delivery of index.html for UI
// paths (work order 016) is checked as well.
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

  const response = await page.goto("/selftest");
  expect(response?.status()).toBe(200);

  // Wait for content (with the expect timeout), never for a fixed time.
  await expect(page.getByTestId("database-version")).toHaveText(/\d+\.\d+/);
  await expect(page.getByTestId("worker-result")).toHaveText("pong");
  await expect(page.getByTestId("database-status")).toHaveText("OK");
  await expect(page.getByTestId("worker-status")).toHaveText("OK");

  // The AI card is there; its state depends on TWOX_AI_ENABLED and on the
  // model service (E-59). The CI has no Ollama, so its content is not checked.
  await expect(page.getByTestId("ai-check")).toBeVisible();
  await expect(page.getByTestId("ai-status")).toHaveText(/^(OK|Failed|Not enabled)$/);

  await expect(page.getByTestId("selftest-loading")).toHaveCount(0);
  await expect(page.getByTestId("selftest-error")).toHaveCount(0);
  await expect(page.getByTestId("database-error")).toHaveCount(0);
  await expect(page.getByTestId("worker-error")).toHaveCount(0);

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});
