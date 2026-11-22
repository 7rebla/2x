import type { Locator, Page } from "@playwright/test";

import { expect, test, testIp, testName, uniqueSuffix } from "./fixtures";

// Ingestion state of uploaded files as served by Django (work order 053).
// The CI starts no converter (Docling): no test waits for a finished
// conversion or for the end of the retries. A plain-text file is skipped at
// once by the format check (work order 049); a Markdown file is queued and
// then runs or fails, depending on the worker. The state "failed" with its
// button comes from an answer written by the test (page.route).
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

/** A new test device (site, area, plant, device); returns its id. */
async function newDevice(page: Page, ip: number): Promise<number> {
  await page.goto("/");
  const siteId = await create(page, "/api/v1/sites/", { name: testName("site") });
  const areaId = await create(page, "/api/v1/areas/", { site: siteId, name: testName("area") });
  const plantId = await create(page, "/api/v1/plants/", { area: areaId, key: testName("plant"), name: testName("plant") });
  return create(page, "/api/v1/devices/", {
    plant: plantId,
    key: testName("device"),
    name: testName("device"),
    ip_address: testIp(ip),
  });
}

/** Uploads a text file through the form on the device page and opens the page of the new file. */
async function uploadAndOpen(page: Page, deviceId: number, name: string, mimeType: string, content: string): Promise<void> {
  await page.goto(`/devices/${String(deviceId)}`);
  const files = page.getByTestId("device-files");
  const form = files.getByRole("form", { name: "Upload a new file" });
  await form.getByLabel("File").setInputFiles({ name, mimeType, buffer: Buffer.from(content, "utf8") });
  const title = testName("file");
  await form.getByLabel("Title").fill(title);
  await form.getByRole("button", { name: "Upload" }).click();
  await expect(form.getByTestId("upload-success")).toHaveText("Uploaded as version 1.");
  await files.getByTestId("device-file").getByRole("link", { name: title }).click();
  await expect(page).toHaveURL(/\/documents\/\d+$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(title);
}

function versionIngest(page: Page): Locator {
  return page.locator('[data-testid="document-version"][data-version="1"]').getByTestId("version-ingest");
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

test("a plain-text file is shown as skipped with its reason, on the file page and the device page", async ({ page }) => {
  const consoleErrors = collectConsoleErrors(page);
  const deviceId = await newDevice(page, 40);
  await uploadAndOpen(page, deviceId, `${testName("file")}.txt`, "text/plain", `e2e plain text ${uniqueSuffix()}\n`);

  const cell = versionIngest(page);
  await expect(cell.getByTestId("ingest-status")).toHaveAttribute("data-status", "skipped");
  await expect(cell.getByTestId("ingest-status")).toHaveText("Skipped");
  await expect(cell.getByTestId("ingest-error-message")).toHaveText(/^This format is not ingested/);
  // The technical text of the API is folded away until asked for.
  const detail = cell.getByTestId("ingest-error-detail");
  await expect(detail).toBeHidden();
  await cell.getByText("Technical details").click();
  await expect(detail).toBeVisible();
  await expect(detail).not.toBeEmpty();
  // A manager may start it again; nothing is running.
  await expect(cell.getByRole("button", { name: "Ingest version 1 again" })).toBeVisible();

  // The device page shows the small badge of the newest version.
  await page.goto(`/devices/${String(deviceId)}`);
  await expect(page.getByTestId("device-file").getByTestId("file-ingest")).toHaveText("Skipped");

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});

test("a Markdown file is queued, being ingested or failed (no converter in the CI)", async ({ page }) => {
  const consoleErrors = collectConsoleErrors(page);
  const deviceId = await newDevice(page, 41);
  const content = `# e2e note ${uniqueSuffix()}\n\nA short test text.\n`;
  await uploadAndOpen(page, deviceId, `${testName("file")}.md`, "text/markdown", content);

  const status = versionIngest(page).getByTestId("ingest-status");
  await expect(status).toHaveAttribute("data-status", /^(queued|running|failed)$/);
  await expect(status).toHaveText(/^(Queued|Ingesting.*|Error)$/);

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});

test("a failed job shows its message and the button, which starts a new job", async ({ page }) => {
  const consoleErrors = collectConsoleErrors(page);
  const deviceId = await newDevice(page, 42);
  await uploadAndOpen(page, deviceId, `${testName("file")}.txt`, "text/plain", `e2e failed state ${uniqueSuffix()}\n`);
  await expect(versionIngest(page).getByTestId("ingest-status")).toHaveAttribute("data-status", "skipped");

  // The file as the API sends it, with the newest job turned into a failed one.
  // It is read inside the page: only Chromium maps the host name of the API
  // (playwright.config.ts), so route.fetch() from the test runner cannot reach it.
  const documentPath = `/api/v1/documents/${new URL(page.url()).pathname.split("/").at(-1) ?? ""}/`;
  const body = await page.evaluate(
    async (url) => (await fetch(url)).json() as Promise<{ versions: { ingest: unknown }[] }>,
    documentPath,
  );
  for (const entry of body.versions) {
    entry.ingest = {
      id: 999_999,
      status: "failed",
      step: "convert",
      error_code: "docling_unavailable",
      error_detail: "Docling could not be reached: written by the browser test",
      partly_converted: false,
      section_count: null,
      page_count: null,
      created_at: "2026-11-22T10:00:00Z",
      finished_at: "2026-11-22T10:05:00Z",
    };
  }
  let override = true;
  await page.route(
    (url) => url.pathname === documentPath,
    async (route) => {
      if (override && route.request().method() === "GET") {
        await route.fulfill({ json: body });
      } else {
        await route.fallback();
      }
    },
  );
  await page.reload();

  const cell = versionIngest(page);
  await expect(cell.getByTestId("ingest-status")).toHaveAttribute("data-status", "failed");
  await expect(cell.getByTestId("ingest-status")).toHaveText("Error");
  await expect(cell.getByTestId("ingest-error-message")).toHaveText(
    "The converter (Docling) could not be reached. Please try again later.",
  );
  await cell.getByText("Technical details").click();
  await expect(cell.getByTestId("ingest-error-detail")).toHaveText(
    "Docling could not be reached: written by the browser test",
  );

  // The button sends the real request: the plain-text file gets a new, skipped job.
  override = false;
  const request = page.waitForRequest(
    (sent) => sent.method() === "POST" && /\/api\/v1\/document-versions\/\d+\/ingest\/$/.test(sent.url()),
  );
  const answer = page.waitForResponse((received) => /\/api\/v1\/document-versions\/\d+\/ingest\/$/.test(received.url()));
  await cell.getByRole("button", { name: "Ingest version 1 again" }).click();
  await request;
  expect((await answer).status()).toBe(202);
  await expect(cell.getByTestId("ingest-status")).toHaveAttribute("data-status", "skipped");
  await expect(cell.getByTestId("ingest-error")).toHaveAttribute("data-code", "unsupported_format");

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});
