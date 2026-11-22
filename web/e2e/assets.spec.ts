import type { Locator, Page } from "@playwright/test";

import { expect, test, testIp, testName } from "./fixtures";

// Structure and devices in the web UI, signed in as the test account (role
// "manage"). Every test creates its own data with unique names
// (e2e-<kind>-<suffix>) and addresses from 192.0.2.0/24, so repeated runs
// against the same database do not disturb each other.
test.use({ locale: "en-US" });

/** Errors in the browser console; `expected` lets through messages a test causes on purpose. */
function collectConsoleErrors(page: Page, expected?: RegExp): string[] {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error" && !(expected?.test(message.text()) ?? false)) {
      errors.push(message.text());
    }
  });
  page.on("pageerror", (error) => {
    errors.push(error.message);
  });
  return errors;
}

/** An address from 192.0.2.0/24 that differs between runs (the API does not require unique addresses). */
function someTestIp(): string {
  return testIp(1 + Math.floor(Math.random() * 254));
}

/** The item of the given kind (site, area, plant) whose name is exactly `name`. */
function item(page: Page, kind: "site" | "area" | "plant", name: string): Locator {
  return page
    .getByTestId(`${kind}-item`)
    .filter({ has: page.getByTestId(`${kind}-name`).getByText(name, { exact: true }) });
}

async function save(form: Locator): Promise<void> {
  await form.getByRole("button", { name: "Save" }).click();
  await expect(form).toBeHidden();
}

test("a manager creates a site, area, plant and device and edits the device", async ({ page }) => {
  const consoleErrors = collectConsoleErrors(page);
  const siteName = testName("site");
  const areaName = testName("area");
  const plantKey = testName("plant");
  const plantName = testName("plant");
  const deviceKey = testName("device");
  const deviceName = testName("device");
  const ip = someTestIp();

  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Structure");

  await page.getByRole("button", { name: "New site" }).click();
  const siteForm = page.getByRole("form", { name: "New site" });
  await siteForm.getByLabel("Name", { exact: true }).fill(siteName);
  await save(siteForm);
  await expect(item(page, "site", siteName).getByTestId("device-count").first()).toHaveText("0 devices");

  await page.getByRole("button", { name: `New area in ${siteName}` }).click();
  const areaForm = page.getByRole("form", { name: "New area" });
  await expect(areaForm.getByLabel("Site", { exact: true })).toHaveValue(/^\d+$/);
  await areaForm.getByLabel("Name", { exact: true }).fill(areaName);
  await save(areaForm);

  await page.getByRole("button", { name: `New plant in ${areaName}` }).click();
  const plantForm = page.getByRole("form", { name: "New plant" });
  await plantForm.getByLabel("Key", { exact: true }).fill(plantKey);
  await plantForm.getByLabel("Name", { exact: true }).fill(plantName);
  await save(plantForm);

  await page.getByRole("button", { name: `New device in ${plantName}` }).click();
  const deviceForm = page.getByRole("form", { name: "New device" });
  await deviceForm.getByLabel("Key", { exact: true }).fill(deviceKey);
  await deviceForm.getByLabel("Name", { exact: true }).fill(deviceName);
  await deviceForm.getByLabel("Software version", { exact: true }).fill("1.0.0");
  await deviceForm.getByLabel("IP address", { exact: true }).fill(ip);
  await deviceForm.getByLabel("Notes", { exact: true }).fill("First line\nSecond line");
  await save(deviceForm);

  // The tree shows the new device and the counts on every level.
  const site = item(page, "site", siteName);
  await expect(site.getByTestId("device-count").first()).toHaveText("1 device");
  await expect(item(page, "area", areaName).getByTestId("device-count").first()).toHaveText("1 device");
  await expect(item(page, "plant", plantName).getByTestId("device-count").first()).toHaveText("1 device");
  await expect(site.getByRole("link", { name: deviceName })).toBeVisible();

  // Search in the browser: by key and by IP address.
  const search = page.getByLabel("Search", { exact: true });
  await search.fill(deviceKey);
  await expect(page.getByTestId("device-item")).toHaveCount(1);
  await expect(page.getByTestId("site-name")).toHaveText([siteName]);
  await search.fill(ip);
  await expect(page.getByRole("link", { name: deviceName })).toBeVisible();
  await search.fill(`${deviceKey}-nothing`);
  await expect(page.getByTestId("structure-no-match")).toBeVisible();
  await search.fill(deviceKey);

  // The device page: all fields, the chain as breadcrumb, the files area.
  await page.getByRole("link", { name: deviceName }).click();
  await expect(page).toHaveURL(/\/devices\/\d+$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(deviceName);
  const breadcrumb = page.getByRole("navigation", { name: "Location of the device" });
  await expect(breadcrumb.getByRole("listitem")).toHaveText([
    "Structure",
    siteName,
    areaName,
    `${plantName} (${plantKey})`,
    deviceName,
  ]);
  await expect(page.getByTestId("device-key")).toHaveText(deviceKey);
  await expect(page.getByTestId("device-ip_address")).toHaveText(ip);
  await expect(page.getByTestId("device-software_version")).toHaveText("1.0.0");
  await expect(page.getByTestId("device-notes")).toHaveText("First line\nSecond line");
  await expect(page.getByTestId("device-files")).toBeVisible();

  // Edit the software version; the page shows the new value, also after a reload.
  await page.getByRole("button", { name: `Edit device ${deviceName}` }).click();
  const editForm = page.getByRole("form", { name: "Edit device" });
  await expect(editForm.getByLabel("Software version", { exact: true })).toHaveValue("1.0.0");
  await editForm.getByLabel("Software version", { exact: true }).fill("2.0.0");
  await save(editForm);
  await expect(page.getByTestId("device-software_version")).toHaveText("2.0.0");
  await page.reload();
  await expect(page.getByTestId("device-software_version")).toHaveText("2.0.0");

  // Back to the structure through the breadcrumb.
  await page.getByRole("navigation", { name: "Location of the device" }).getByRole("link", { name: "Structure" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(item(page, "site", siteName)).toBeVisible();

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});

/** Creates an item through the API from inside the page (same session, CSRF token from the cookie). */
async function create(page: Page, path: string, body: Record<string, unknown>): Promise<{ id: number }> {
  const token = (await page.context().cookies()).find((cookie) => cookie.name === "csrftoken")?.value;
  if (token === undefined) {
    throw new Error("no csrftoken cookie");
  }
  return page.evaluate(
    async ({ url, payload, csrfToken }): Promise<{ id: number }> => {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
        body: JSON.stringify(payload),
      });
      if (response.status !== 201) {
        throw new Error(`POST ${url} answered ${String(response.status)}: ${await response.text()}`);
      }
      return (await response.json()) as { id: number };
    },
    { url: path, payload: body, csrfToken: token },
  );
}

test("an invalid IP address shows the error of the API at the field", async ({ page }) => {
  // The browser logs the 400 answer of the rejected entry.
  const consoleErrors = collectConsoleErrors(page, /status of 400/);
  await page.goto("/");
  const site = await create(page, "/api/v1/sites/", { name: testName("site") });
  const area = await create(page, "/api/v1/areas/", { site: site.id, name: testName("area") });
  const plantName = testName("plant");
  await create(page, "/api/v1/plants/", { area: area.id, key: testName("plant"), name: plantName });
  const deviceKey = testName("device");

  await page.reload();
  await page.getByLabel("Search", { exact: true }).fill(plantName);
  await page.getByRole("button", { name: `New device in ${plantName}` }).click();
  const deviceForm = page.getByRole("form", { name: "New device" });
  await deviceForm.getByLabel("Key", { exact: true }).fill(deviceKey);
  await deviceForm.getByLabel("Name", { exact: true }).fill(testName("device"));
  const ipField = deviceForm.getByLabel("IP address", { exact: true });
  await ipField.fill("192.0.2.256");
  await deviceForm.getByRole("button", { name: "Save" }).click();

  const error = deviceForm.getByTestId("field-error-ip_address");
  await expect(error).toBeVisible();
  await expect(error).not.toBeEmpty();
  await expect(ipField).toHaveAttribute("aria-invalid", "true");
  await expect(ipField).toHaveAccessibleDescription(/\S/);
  await expect(ipField).toHaveValue("192.0.2.256");
  await expect(deviceForm.getByTestId("form-invalid")).toBeVisible();
  // Only the address is wrong.
  await expect(deviceForm.getByTestId("field-error-key")).toHaveCount(0);

  // Nothing was saved.
  await deviceForm.getByRole("button", { name: "Cancel" }).click();
  await page.getByLabel("Search", { exact: true }).fill(deviceKey);
  await expect(page.getByTestId("structure-no-match")).toBeVisible();

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});
