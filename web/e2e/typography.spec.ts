import type { Locator, Page } from "@playwright/test";

import { expect, test, testIp, testName, uniqueSuffix } from "./fixtures";

// Font size of metadata (work order 084, decision E-65 (5)): times, status
// details, checksums and identifiers are 13 px (token text-meta), 12 px stays
// only for labels in capitals. With the larger text the tables of files,
// ingest jobs and the change log still fit their box at 1024 and 1600 px
// (work order 079). The CI starts no converter: a plain-text file is skipped
// at once (work order 049), so the ingest overview has a job without waiting.
test.use({ locale: "en-US" });

// The web UI has no Node types (fixtures.ts): setInputFiles wants a Buffer.
declare const Buffer: { from(text: string, encoding: "utf8"): unknown };

interface ApiAnswer {
  readonly status: number;
  readonly body: unknown;
}

/** POST with session and CSRF token from inside the page, like the web UI (see fixtures.ts). */
async function create(page: Page, path: string, body: object): Promise<number> {
  const token = (await page.context().cookies()).find((cookie) => cookie.name === "csrftoken")?.value;
  if (token === undefined) {
    throw new Error("no csrftoken cookie");
  }
  const answer = await page.evaluate(
    async ({ url, csrfToken, payload }): Promise<ApiAnswer> => {
      const result = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
        body: JSON.stringify(payload),
      });
      return { status: result.status, body: (await result.json()) as unknown };
    },
    { url: path, csrfToken: token, payload: body },
  );
  expect(answer.status, `POST ${path}: ${JSON.stringify(answer.body)}`).toBe(201);
  const id = (answer.body as { id?: unknown }).id;
  if (typeof id !== "number") {
    throw new Error(`POST ${path} answered without an id`);
  }
  return id;
}

/** Computed font size and text transform of an element. */
async function fontOf(locator: Locator): Promise<{ size: string; transform: string }> {
  return locator.evaluate((element) => {
    const style = getComputedStyle(element);
    return { size: style.fontSize, transform: style.textTransform };
  });
}

/** The table is not wider than its box, and the page does not scroll sideways. */
async function expectTableFits(page: Page, table: Locator): Promise<void> {
  const widths = await table.evaluate((element) => ({
    table: element.scrollWidth,
    box: element.parentElement?.clientWidth ?? 0,
  }));
  expect(widths.table, `table ${String(widths.table)} px in a box of ${String(widths.box)} px`).toBeLessThanOrEqual(widths.box);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBe(0);
}

test("metadata are 13 px, labels in capitals 12 px, and the tables still fit at 1024 and 1600 px", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 900 });
  await page.goto("/");
  const siteId = await create(page, "/api/v1/sites/", { name: testName("site") });
  const areaId = await create(page, "/api/v1/areas/", { site: siteId, name: testName("area") });
  const plantName = testName("plant");
  const plantId = await create(page, "/api/v1/plants/", { area: areaId, key: plantName, name: plantName });
  const deviceKey = testName("device");
  const deviceId = await create(page, "/api/v1/devices/", {
    plant: plantId,
    key: deviceKey,
    name: testName("device"),
    device_class: "plc",
    ip_address: testIp(84),
  });

  await page.goto(`/devices/${String(deviceId)}`);
  const files = page.getByTestId("device-files");
  const newFile = files.getByRole("form", { name: "Upload a new file" });
  await newFile.getByLabel("File").setInputFiles({
    name: `${testName("file")}.txt`,
    mimeType: "text/plain",
    buffer: Buffer.from(`e2e typography ${uniqueSuffix()}\n`, "utf8"),
  });
  await newFile.getByLabel("Title").fill(testName("file"));
  await newFile.getByRole("button", { name: "Upload" }).click();
  await expect(newFile.getByTestId("upload-success")).toHaveText("Uploaded as version 1.");
  await page.evaluate(async () => {
    await document.fonts.load('16px "Inter"');
    await document.fonts.ready;
  });

  const fileTable = files.getByRole("table", { name: "Files of the device" });
  const row = fileTable.getByTestId("device-file");
  await expect(row).toHaveCount(1);
  expect((await fontOf(row.getByTestId("checksum"))).size).toBe("13px");
  expect((await fontOf(row.getByTestId("file-user"))).size).toBe("13px");
  expect((await fontOf(row.getByTestId("ingest-status"))).size).toBe("13px");

  // Labels in capitals keep 12 px: the device class in the structure tree.
  await page.goto("/");
  await page.getByLabel("Search", { exact: true }).fill(plantName);
  await expect(page.getByTestId("structure-search-status")).toHaveText("1 device shown");
  const deviceClass = page
    .getByTestId("device-item")
    .filter({ has: page.getByTestId("device-key").getByText(deviceKey, { exact: true }) })
    .getByTestId("device-class");
  expect(await fontOf(deviceClass)).toEqual({ size: "12px", transform: "uppercase" });

  for (const width of [1024, 1600]) {
    await page.setViewportSize({ width, height: 900 });

    await page.goto(`/devices/${String(deviceId)}`);
    await expect(row).toHaveCount(1);
    await expectTableFits(page, fileTable);

    await page.goto(`/ingest?status=all&device=${String(deviceId)}`);
    const jobTable = page.getByRole("table", { name: "Ingest jobs" });
    const job = jobTable.getByTestId("ingest-job");
    await expect(job).toHaveCount(1);
    expect((await fontOf(job.getByTestId("ingest-job-times"))).size).toBe("13px");
    expect((await fontOf(job.getByTestId("ingest-job-version"))).size).toBe("13px");
    await expectTableFits(page, jobTable);

    await page.goto("/audit");
    const changes = page.getByRole("table", { name: "Changes" });
    await expect(changes.getByTestId("audit-entry").first()).toBeVisible();
    await expectTableFits(page, changes);
  }
});
