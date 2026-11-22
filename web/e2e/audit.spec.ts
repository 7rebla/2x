import type { Page } from "@playwright/test";

import { expect, test, testIp, testName } from "./fixtures";

declare const process: { readonly env: Readonly<Record<string, string | undefined>> };

// The change log page as served by Django: a device created and changed
// through the API appears twice, with the signed-in test account as user.
test.use({ locale: "en-US" });

interface ApiAnswer {
  readonly status: number;
  readonly body: unknown;
}

/**
 * Sends a writing request from inside the page, with the session cookie and
 * the CSRF token, like the web UI does (fixtures.ts explains why not through
 * Playwright's request client).
 */
async function apiWrite(page: Page, method: "POST" | "PATCH", path: string, body: object): Promise<ApiAnswer> {
  const token = (await page.context().cookies()).find((cookie) => cookie.name === "csrftoken")?.value;
  if (token === undefined) {
    throw new Error("no csrftoken cookie");
  }
  return page.evaluate(
    async ({ url, verb, csrfToken, payload }): Promise<ApiAnswer> => {
      const result = await fetch(url, {
        method: verb,
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
        body: JSON.stringify(payload),
      });
      return { status: result.status, body: (await result.json()) as unknown };
    },
    { url: path, verb: method, csrfToken: token, payload: body },
  );
}

async function create(page: Page, path: string, body: object): Promise<number> {
  const answer = await apiWrite(page, "POST", path, body);
  expect(answer.status, `POST ${path}: ${JSON.stringify(answer.body)}`).toBe(201);
  const id = (answer.body as { id?: unknown }).id;
  if (typeof id !== "number") {
    throw new Error(`POST ${path} answered without an id`);
  }
  return id;
}

test("a device created and changed through the API shows up twice with the user", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });
  page.on("pageerror", (error) => {
    consoleErrors.push(error.message);
  });
  const username = process.env.TWOX_E2E_USERNAME ?? "";

  // The page sets the CSRF cookie; the session comes from fixtures.ts.
  await page.goto("/");
  const siteId = await create(page, "/api/v1/sites/", { name: testName("site") });
  const areaId = await create(page, "/api/v1/areas/", { site: siteId, name: testName("area") });
  const plantId = await create(page, "/api/v1/plants/", { area: areaId, key: testName("plant"), name: testName("plant") });
  const deviceKey = testName("device");
  const firstName = testName("device");
  const secondName = testName("device");
  const deviceId = await create(page, "/api/v1/devices/", {
    plant: plantId,
    key: deviceKey,
    name: firstName,
    ip_address: testIp(10),
  });
  const changed = await apiWrite(page, "PATCH", `/api/v1/devices/${String(deviceId)}/`, {
    name: secondName,
    ip_address: testIp(11),
  });
  expect(changed.status, JSON.stringify(changed.body)).toBe(200);

  await page.goto("/audit");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Change log");
  await page.getByLabel("Object type").selectOption("assets.device");
  await page.getByLabel("User").fill(username);
  await page.getByRole("button", { name: "Apply filter" }).click();

  // Newest first: the change, then the creation. Other tests may write
  // entries at the same time, so only the rows of this device count.
  const rows = page.getByTestId("audit-entry").filter({ hasText: deviceKey });
  await expect(rows).toHaveCount(2);
  const [update, creation] = [rows.nth(0), rows.nth(1)];

  await expect(update.getByTestId("audit-action")).toHaveText("Changed");
  await expect(update.getByTestId("audit-actor")).toHaveText(username);
  await expect(update.getByTestId("audit-object-type")).toHaveText("Device");
  await expect(update.getByTestId("audit-object")).toContainText(`${secondName} (${deviceKey})`);
  await expect(update.getByTestId("audit-object")).toContainText(`ID ${String(deviceId)}`);
  // updated_at changes as well; only the two fields set here are checked.
  const updateChanges = update.getByTestId("audit-change");
  await expect(updateChanges.filter({ hasText: /^name: / })).toHaveText(`name: ${firstName} → ${secondName}`);
  await expect(updateChanges.filter({ hasText: /^ip_address: / })).toHaveText(
    `ip_address: ${testIp(10)} → ${testIp(11)}`,
  );
  await expect(update.getByTestId("audit-timestamp").locator("time")).toHaveAttribute("datetime", /^\d{4}-\d{2}-\d{2}T/);

  await expect(creation.getByTestId("audit-action")).toHaveText("Created");
  await expect(creation.getByTestId("audit-actor")).toHaveText(username);
  await expect(creation.getByTestId("audit-object")).toContainText(`${firstName} (${deviceKey})`);
  await expect(creation.getByTestId("audit-changes")).toContainText(`name: (empty) → ${firstName}`);
  await expect(creation.getByTestId("audit-changes")).toContainText(`key: (empty) → ${deviceKey}`);

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});
