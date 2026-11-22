import type { Locator, Page } from "@playwright/test";

import { expect, test, testIp, testName } from "./fixtures";

// Import of the device list in the web UI, signed in as the test account
// (role "manage"). Each test writes its own small CSV file with unique names
// (e2e-<kind>-<suffix>) and addresses from 192.0.2.0/24, so repeated runs
// against the same database always create new entries.
test.use({ locale: "en-US" });

// The web UI has no Node types (@types/node is not a dependency); this file
// only turns the CSV text into the bytes Playwright uploads.
declare const Buffer: { from(text: string, encoding: "utf8"): Uint8Array };

/** The header of the device list (E-44). */
const COLUMNS = [
  "site",
  "area",
  "plant_id",
  "plant_name",
  "device_id",
  "device_name",
  "manufacturer",
  "model",
  "software_version",
  "ip_address",
  "address_source",
  "protocols",
  "notes",
] as const;

/** The header with the optional 14th column (E-53). */
const COLUMNS_WITH_DEVICE_CLASS = [...COLUMNS, "device_class"] as const;

type Row = Partial<Record<(typeof COLUMNS_WITH_DEVICE_CLASS)[number], string>>;

/** A CSV file with the header and one line per row; the test values need no quoting. */
function csv(rows: readonly Row[], columns: readonly (keyof Row)[] = COLUMNS): string {
  const lines = rows.map((row) => columns.map((column) => row[column] ?? "").join(","));
  return `${[columns.join(","), ...lines].join("\n")}\n`;
}

/** Errors in the browser console. */
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

/** The structure page says that the search found nothing (or that there is no site at all). */
function nothingFound(page: Page): Locator {
  return page.getByTestId("structure-no-match").or(page.getByTestId("structure-empty"));
}

async function chooseCsv(page: Page, content: string): Promise<void> {
  await page.getByLabel("CSV file", { exact: true }).setInputFiles({
    name: "devices.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(content, "utf8"),
  });
}

/** Rows of a plant with two devices; every name is new for this run. */
function twoDevices(): { rows: Row[]; site: string; plant: string; devices: [string, string] } {
  const site = testName("site");
  const area = testName("area");
  const plant = testName("plant");
  const device = testName("device");
  const devices: [string, string] = [`${device}-1`, `${device}-2`];
  const common: Row = { site, area, plant_id: plant, plant_name: plant };
  return {
    site,
    plant,
    devices,
    rows: [
      { ...common, device_id: devices[0], device_name: devices[0], ip_address: testIp(41), protocols: "MQTT" },
      { ...common, device_id: devices[1], device_name: devices[1], ip_address: testIp(42) },
    ],
  };
}

test("a manager checks a CSV file in a dry run, applies it and finds the devices in the structure", async ({
  page,
}) => {
  const consoleErrors = collectConsoleErrors(page);
  const { rows, site, plant, devices } = twoDevices();

  await page.goto("/import");
  await expect(page.getByRole("heading", { level: 2 })).toHaveText("Import");
  await expect(page.getByTestId("import-columns")).toHaveText(COLUMNS.join(","));
  await chooseCsv(page, csv(rows));
  await page.getByRole("button", { name: "Start dry run" }).click();

  // The dry run: two new devices, one new site, area and plant, nothing saved.
  await expect(page.getByTestId("import-summary")).toHaveText("Dry run: nothing has been saved yet. 2 rows read.");
  await expect(page.getByTestId("import-count-devices-created")).toHaveText("2");
  await expect(page.getByTestId("import-count-devices-updated")).toHaveText("0");
  await expect(page.getByTestId("import-count-plants-created")).toHaveText("1");
  await expect(page.getByTestId("import-count-areas-created")).toHaveText("1");
  await expect(page.getByTestId("import-count-sites-created")).toHaveText("1");
  await expect(page.getByTestId("import-errors")).toHaveCount(0);

  // Nothing is in the structure yet.
  await page.goto("/");
  await page.getByLabel("Search", { exact: true }).fill(site);
  await expect(nothingFound(page)).toBeVisible();

  // Dry run again, then apply.
  await page.goto("/import");
  await chooseCsv(page, csv(rows));
  await page.getByRole("button", { name: "Start dry run" }).click();
  await expect(page.getByTestId("import-count-devices-created")).toHaveText("2");
  await page.getByRole("button", { name: "Apply" }).click();
  await expect(page.getByTestId("import-summary")).toHaveText("Saved. 2 rows imported.");
  await expect(page.getByTestId("import-count-devices-created")).toHaveText("2");
  await expect(page.getByRole("button", { name: "Apply" })).toHaveCount(0);

  // The structure shows both devices below the new plant.
  await page.getByRole("link", { name: "Show the structure" }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.getByLabel("Search", { exact: true }).fill(site);
  const plantItem = page
    .getByTestId("plant-item")
    .filter({ has: page.getByTestId("plant-name").getByText(plant, { exact: true }) });
  await expect(plantItem.getByTestId("device-count").first()).toHaveText("2 devices");
  await expect(plantItem.getByRole("link", { name: devices[0], exact: true })).toBeVisible();
  await expect(plantItem.getByRole("link", { name: devices[1], exact: true })).toBeVisible();

  // The same file again: everything is unchanged now.
  await page.goto("/import");
  await chooseCsv(page, csv(rows));
  await page.getByRole("button", { name: "Start dry run" }).click();
  await expect(page.getByTestId("import-count-devices-created")).toHaveText("0");
  await expect(page.getByTestId("import-count-devices-unchanged")).toHaveText("2");

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});

test("a CSV file with an invalid IP address shows the error with its line number", async ({ page }) => {
  const consoleErrors = collectConsoleErrors(page);
  const { rows, site } = twoDevices();
  const second = rows[1];
  if (second === undefined) {
    throw new Error("twoDevices() gives two rows");
  }
  rows[1] = { ...second, ip_address: "192.0.2.256" };

  await page.goto("/import");
  await chooseCsv(page, csv(rows));
  await page.getByRole("button", { name: "Start dry run" }).click();

  // The header is line 1, so the second device is on line 3.
  await expect(page.getByTestId("import-summary")).toHaveText("The file has 1 error. Nothing has been saved.");
  const error = page.getByTestId("import-error");
  await expect(error).toHaveCount(1);
  await expect(error.getByTestId("import-error-line")).toHaveText("3");
  await expect(error.getByTestId("import-error-column")).toHaveText("ip_address");
  await expect(error.getByTestId("import-error-message")).not.toBeEmpty();
  await expect(page.getByRole("button", { name: "Apply" })).toHaveCount(0);

  // Nothing was saved.
  await page.goto("/");
  await page.getByLabel("Search", { exact: true }).fill(site);
  await expect(nothingFound(page)).toBeVisible();

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});

test("a CSV file with the column device_class sets the class of each device", async ({ page }) => {
  const consoleErrors = collectConsoleErrors(page);
  const { rows, site, plant, devices } = twoDevices();
  const classes = ["plc", "robot"] as const;
  const classified = rows.map((row, index) => ({ ...row, device_class: classes[index] ?? "" }));

  await page.goto("/import");
  await expect(page.getByTestId("import-optional-column")).toHaveText("device_class");
  await chooseCsv(page, csv(classified, COLUMNS_WITH_DEVICE_CLASS));
  await page.getByRole("button", { name: "Start dry run" }).click();
  await expect(page.getByTestId("import-count-devices-created")).toHaveText("2");
  await page.getByRole("button", { name: "Apply" }).click();
  await expect(page.getByTestId("import-summary")).toHaveText("Saved. 2 rows imported.");

  // Each device shows its class in the edit form of its page.
  const plantItem = page
    .getByTestId("plant-item")
    .filter({ has: page.getByTestId("plant-name").getByText(plant, { exact: true }) });
  for (const [index, device] of devices.entries()) {
    await page.goto("/");
    await page.getByLabel("Search", { exact: true }).fill(site);
    await plantItem.getByRole("link", { name: device, exact: true }).click();
    await page.getByRole("button", { name: `Edit device ${device}` }).click();
    const deviceForm = page.getByRole("form", { name: "Edit device" });
    await expect(deviceForm.getByLabel("Device class")).toHaveValue(classes[index] ?? "");
  }

  // The same file with 13 columns changes nothing: the classes stay.
  await page.goto("/import");
  await chooseCsv(page, csv(rows));
  await page.getByRole("button", { name: "Start dry run" }).click();
  await expect(page.getByTestId("import-count-devices-unchanged")).toHaveText("2");
  await expect(page.getByTestId("import-count-devices-updated")).toHaveText("0");

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});

test("an unknown device class is an error at its line and column", async ({ page }) => {
  const consoleErrors = collectConsoleErrors(page);
  const { rows, site } = twoDevices();
  const classified = [
    { ...rows[0], device_class: "router" },
    { ...rows[1], device_class: "switch" },
  ];

  await page.goto("/import");
  await chooseCsv(page, csv(classified, COLUMNS_WITH_DEVICE_CLASS));
  await page.getByRole("button", { name: "Start dry run" }).click();

  await expect(page.getByTestId("import-summary")).toHaveText("The file has 1 error. Nothing has been saved.");
  const error = page.getByTestId("import-error");
  await expect(error).toHaveCount(1);
  await expect(error.getByTestId("import-error-line")).toHaveText("3");
  await expect(error.getByTestId("import-error-column")).toHaveText("device_class");
  await expect(error.getByTestId("import-error-message")).toContainText("is not a device class");
  await expect(page.getByRole("button", { name: "Apply" })).toHaveCount(0);

  await page.goto("/");
  await page.getByLabel("Search", { exact: true }).fill(site);
  await expect(nothingFound(page)).toBeVisible();

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});
