import type { Page } from "@playwright/test";

import { expect, test, testIp, testName, uniqueSuffix } from "./fixtures";

// Ingest overview as served by Django (work order 055), signed in as the
// manager of the browser test. The CI starts no converter (Docling): a
// plain-text file is skipped at once by the format check (work order 049), so
// no test waits for a conversion.
test.use({ locale: "en-US" });

// The web UI has no Node types (fixtures.ts): setInputFiles wants a Buffer.
declare const Buffer: { from(text: string, encoding: "utf8"): unknown };
declare const process: { readonly env: Readonly<Record<string, string | undefined>> };

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

interface TestDevice {
  readonly id: number;
  readonly name: string;
  readonly key: string;
}

/** A new test device (site, area, plant, device). */
async function newDevice(page: Page, ip: number): Promise<TestDevice> {
  await page.goto("/");
  const siteId = await create(page, "/api/v1/sites/", { name: testName("site") });
  const areaId = await create(page, "/api/v1/areas/", { site: siteId, name: testName("area") });
  const plantId = await create(page, "/api/v1/plants/", { area: areaId, key: testName("plant"), name: testName("plant") });
  const name = testName("device");
  const key = testName("device");
  const id = await create(page, "/api/v1/devices/", { plant: plantId, key, name, ip_address: testIp(ip) });
  return { id, name, key };
}

/** Uploads a plain-text file, written here, through the form on the device page; returns its title. */
async function uploadText(page: Page, deviceId: number): Promise<string> {
  await page.goto(`/devices/${String(deviceId)}`);
  const form = page.getByTestId("device-files").getByRole("form", { name: "Upload a new file" });
  await form.getByLabel("File").setInputFiles({
    name: `${testName("file")}.txt`,
    mimeType: "text/plain",
    buffer: Buffer.from(`e2e ingest overview ${uniqueSuffix()}\n`, "utf8"),
  });
  const title = testName("file");
  await form.getByLabel("Title").fill(title);
  await form.getByRole("button", { name: "Upload" }).click();
  await expect(form.getByTestId("upload-success")).toHaveText("Uploaded as version 1.");
  return title;
}

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

test("the navigation leads to the ingest overview, which lists the open jobs by default", async ({ page }) => {
  const consoleErrors = collectConsoleErrors(page);
  await page.goto("/");
  const navigation = page.getByRole("navigation", { name: "Main navigation" });
  const entry = navigation.getByRole("link", { name: "Ingestion" });
  await expect(entry).toBeVisible();
  await expect(entry.locator("svg")).toHaveAttribute("data-icon", "ingest");

  const list = page.waitForResponse((answer) => new URL(answer.url()).pathname === "/api/v1/ingest-jobs/");
  await entry.click();

  await expect(page).toHaveURL(/\/ingest$/);
  await expect(entry).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("heading", { level: 2 })).toHaveText("Ingestion");
  const answer = await list;
  expect(answer.status()).toBe(200);
  expect(new URL(answer.url()).searchParams.getAll("status")).toEqual(["failed", "running", "queued"]);
  await expect(page.getByTestId("ingest-filter-status")).toHaveValue("open");
  await expect(page.getByTestId("ingest-page-status")).toHaveText(/^Page 1 of \d+$/);

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});

test.describe("on a phone", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test("the filters fit and only the table scrolls sideways", async ({ page }) => {
    await page.goto("/ingest?status=all");
    await expect(page.getByTestId("ingest-jobs")).toBeVisible();
    const pageOverflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(pageOverflow).toBeLessThanOrEqual(0);
    for (const id of ["ingest-filter-status", "ingest-filter-device"]) {
      const box = await page.getByTestId(id).boundingBox();
      expect((box?.x ?? 0) + (box?.width ?? 0)).toBeLessThanOrEqual(375);
    }
  });
});

test("an uploaded plain-text file appears under All as skipped, with its device and a link to the file", async ({ page }) => {
  const consoleErrors = collectConsoleErrors(page);
  const device = await newDevice(page, 55);
  const title = await uploadText(page, device.id);

  // Only this device: other tests (and earlier runs) add jobs of their own.
  await page.goto(`/ingest?device=${String(device.id)}`);
  await expect(page.getByTestId("ingest-filter-device")).toHaveValue(String(device.id));
  // A skipped job is not open: the default view of this device stays empty.
  await expect(page.getByTestId("ingest-empty")).toHaveText("No ingest job matches this filter.");

  await page.getByTestId("ingest-filter-status").selectOption({ label: "All" });
  await expect(page).toHaveURL(new RegExp(`/ingest\\?status=all&device=${String(device.id)}$`));

  const row = page.getByTestId("ingest-job");
  await expect(row).toHaveCount(1);
  await expect(row.getByTestId("ingest-status")).toHaveAttribute("data-status", "skipped");
  await expect(row.getByTestId("ingest-status")).toHaveText("Skipped");
  await expect(row.getByTestId("ingest-error-message")).toHaveText(/^This format is not ingested/);
  await expect(row.getByTestId("ingest-job-device")).toContainText(device.name);
  await expect(row.getByTestId("ingest-job-device")).toContainText(device.key);
  await expect(row.getByTestId("ingest-job-version")).toHaveText(/^Version 1 · e2e-file-.+\.txt$/);
  // Started by the signed-in manager through the upload.
  await expect(row.getByTestId("ingest-job-requested-by")).toHaveText(process.env.TWOX_E2E_USERNAME ?? "");

  // The link leads to the page of the file.
  await row.getByTestId("ingest-job-document-link").click();
  await expect(page).toHaveURL(/\/documents\/\d+$/);
  await expect(page.getByRole("heading", { level: 2 })).toHaveText(title);

  // Back returns to the same view.
  await page.goBack();
  await expect(page).toHaveURL(new RegExp(`/ingest\\?status=all&device=${String(device.id)}$`));
  await expect(page.getByTestId("ingest-job")).toHaveCount(1);

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});

test("a manager starts the ingestion again from the overview; the older attempt is marked", async ({ page }) => {
  const consoleErrors = collectConsoleErrors(page);
  const device = await newDevice(page, 56);
  await uploadText(page, device.id);
  await page.goto(`/ingest?status=all&device=${String(device.id)}`);
  const rows = page.getByTestId("ingest-job");
  await expect(rows).toHaveCount(1);
  await expect(rows.getByTestId("ingest-status")).toHaveAttribute("data-status", "skipped");

  const answer = page.waitForResponse(
    (received) => received.request().method() === "POST" && /\/api\/v1\/document-versions\/\d+\/ingest\/$/.test(received.url()),
  );
  await rows.getByRole("button", { name: "Ingest version 1 again" }).click();
  expect((await answer).status()).toBe(202);

  // The real new job is listed on top; the format check skips it again (the
  // page polls while it is queued).
  await expect(rows).toHaveCount(2);
  await expect(rows.first().getByTestId("ingest-status")).toHaveAttribute("data-status", "skipped");
  await expect(rows.nth(1).getByTestId("ingest-superseded")).toHaveText(
    "Older attempt: a newer job of this version is listed above.",
  );
  await expect(rows.nth(1).getByTestId("ingest-retry")).toHaveCount(0);
  await expect(rows.first().getByRole("button", { name: "Ingest version 1 again" })).toBeVisible();

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});
