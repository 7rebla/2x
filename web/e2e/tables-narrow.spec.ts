import type { Page } from "@playwright/test";

import { expect, test, testIp, testName, uniqueSuffix } from "./fixtures";

// Tables on narrow screens (work order 081, decision E-65 (2)): below 768 px
// the files of a device, the versions of a file, the ingest jobs and the
// change log are stacked cards (a list with one heading per card) and the page
// does not scroll sideways; from 768 px they are tables again. The CI starts
// no converter: a plain-text file is skipped at once (work order 049), so the
// ingest overview has a job without waiting.
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

/** The page is not wider than the window: nothing scrolls sideways. */
async function expectNoSidewaysScrolling(page: Page): Promise<void> {
  const widths = await page.evaluate(() => ({
    page: document.documentElement.scrollWidth,
    window: document.documentElement.clientWidth,
  }));
  expect(widths.page, `page ${String(widths.page)} px in a window of ${String(widths.window)} px`).toBeLessThanOrEqual(
    widths.window,
  );
}

test("tables are stacked cards at 375 px and tables again from 768 px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  const siteId = await create(page, "/api/v1/sites/", { name: testName("site") });
  const areaId = await create(page, "/api/v1/areas/", { site: siteId, name: testName("area") });
  const plantId = await create(page, "/api/v1/plants/", { area: areaId, key: testName("plant"), name: testName("plant") });
  const deviceId = await create(page, "/api/v1/devices/", {
    plant: plantId,
    key: testName("device"),
    name: testName("device"),
    ip_address: testIp(81),
  });
  // A long title without spaces: on a card it must wrap instead of widening the page.
  const title = `${testName("file")}-with-a-rather-long-title-for-a-narrow-screen`;
  const fileName = `${testName("file")}.txt`;

  // Device page: upload a file at 375 px, then its card.
  await page.goto(`/devices/${String(deviceId)}`);
  const files = page.getByTestId("device-files");
  const newFile = files.getByRole("form", { name: "Upload a new file" });
  await newFile.getByLabel("File").setInputFiles({
    name: fileName,
    mimeType: "text/plain",
    buffer: Buffer.from(`e2e narrow tables ${uniqueSuffix()}\n`, "utf8"),
  });
  await newFile.getByLabel("Title").fill(title);
  await newFile.getByRole("button", { name: "Upload" }).click();
  await expect(newFile.getByTestId("upload-success")).toHaveText("Uploaded as version 1.");

  const fileList = files.getByRole("list", { name: "Files of the device" });
  await expect(fileList).toBeVisible();
  await expect(files.getByRole("table")).toHaveCount(0);
  const card = fileList.getByTestId("device-file");
  await expect(card).toHaveCount(1);
  await expect(card.getByRole("heading", { level: 3 })).toHaveText(title);
  await expect(card.getByTestId("file-kind")).toHaveText("Document");
  await expect(card.getByTestId("file-version")).toHaveText("1");
  await expect(card.getByRole("link", { name: "Download version 1" })).toBeVisible();
  await expect(card.getByTestId("checksum-short")).toHaveText(/^[0-9a-f]{12}…$/);
  const cardBox = await card.boundingBox();
  expect(cardBox?.width ?? 0).toBeLessThanOrEqual(375);
  await expectNoSidewaysScrolling(page);

  // File page: the versions and the change log of the file as cards.
  await card.getByRole("link", { name: title }).click();
  await expect(page).toHaveURL(/\/documents\/\d+$/);
  const versionList = page.getByRole("list", { name: "All versions, newest first" });
  await expect(versionList.getByRole("heading", { level: 3 })).toHaveText(["Version 1"]);
  await expect(versionList.getByTestId("version-filename")).toHaveText(fileName);
  const history = page.getByTestId("document-history");
  await expect(history.getByRole("list", { name: "Change log of the file" }).getByTestId("audit-entry")).not.toHaveCount(0);
  await expect(history.getByRole("table")).toHaveCount(0);
  await expectNoSidewaysScrolling(page);

  // Ingest overview: the skipped job of the text file as a card with its state.
  await page.goto(`/ingest?status=all&device=${String(deviceId)}`);
  const jobList = page.getByRole("list", { name: "Ingest jobs" });
  const job = jobList.getByTestId("ingest-job");
  await expect(job).toHaveCount(1);
  await expect(job.getByRole("heading", { level: 2 })).toHaveText(title);
  await expect(job.getByTestId("ingest-status")).toBeVisible();
  await expect(job.getByTestId("ingest-job-version")).toHaveText(`Version 1 · ${fileName}`);
  await expectNoSidewaysScrolling(page);

  // Change log: every entry a card below the page heading.
  await page.goto("/audit");
  const entries = page.getByRole("list", { name: "Changes" });
  await expect(entries.getByTestId("audit-entry").first()).toBeVisible();
  await expect(entries.getByTestId("audit-entry").first().getByRole("heading", { level: 2 })).toBeVisible();
  await expectNoSidewaysScrolling(page);

  // From 768 px on the same views are tables again.
  await page.setViewportSize({ width: 1024, height: 800 });
  await expect(page.getByRole("table", { name: "Changes" })).toBeVisible();
  await page.goto(`/devices/${String(deviceId)}`);
  await expect(page.getByRole("table", { name: "Files of the device" })).toBeVisible();
  await expect(page.getByTestId("device-files").getByRole("list", { name: "Files of the device" })).toHaveCount(0);
});
