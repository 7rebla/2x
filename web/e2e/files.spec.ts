import type { Page } from "@playwright/test";

import { expect, test, testIp, testName, uniqueSuffix } from "./fixtures";

// Files of a device as served by Django: upload a file and a second version
// through the web UI, download version 1, and the 409 for the same content
// again. The device comes from the API; the file content is made per run.
test.use({ locale: "en-US" });

// The web UI has no Node types (fixtures.ts): the spec reads an environment
// variable, and setInputFiles wants a Buffer.
declare const process: { readonly env: Readonly<Record<string, string | undefined>> };
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

function textUpload(name: string, content: string): { name: string; mimeType: string; buffer: unknown } {
  return { name, mimeType: "text/plain", buffer: Buffer.from(content, "utf8") };
}

test("upload a file and a second version, download version 1, same content again gives 409", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    // The browser logs the 409 answer of the repeated upload.
    if (message.type() === "error" && !message.text().includes("status of 409")) {
      consoleErrors.push(message.text());
    }
  });
  page.on("pageerror", (error) => {
    consoleErrors.push(error.message);
  });

  // The page sets the CSRF cookie; the session comes from fixtures.ts.
  await page.goto("/");
  const siteId = await create(page, "/api/v1/sites/", { name: testName("site") });
  const areaId = await create(page, "/api/v1/areas/", { site: siteId, name: testName("area") });
  const plantId = await create(page, "/api/v1/plants/", { area: areaId, key: testName("plant"), name: testName("plant") });
  const deviceName = testName("device");
  const deviceId = await create(page, "/api/v1/devices/", {
    plant: plantId,
    key: testName("device"),
    name: deviceName,
    ip_address: testIp(30),
  });

  const title = testName("file");
  const fileName = `${testName("file")}.txt`;
  const run = uniqueSuffix();
  const firstContent = `e2e test file ${run}\nversion 1\n`;
  const secondContent = `e2e test file ${run}\nversion 2\n`;

  // Device page: no files yet, then version 1 through the form.
  await page.goto(`/devices/${String(deviceId)}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(deviceName);
  const files = page.getByTestId("device-files");
  await expect(files.getByTestId("device-files-empty")).toBeVisible();

  const newFile = files.getByRole("form", { name: "Upload a new file" });
  await expect(newFile.getByTestId("upload-configuration-hint")).toBeVisible();
  // The file chooser (work order 088): the button waits for a file and says so.
  await expect(newFile.getByText("Choose file…")).toBeVisible();
  await expect(newFile.getByTestId("file-input-name")).toHaveText("No file chosen");
  await expect(newFile.getByRole("button", { name: "Upload" })).toBeDisabled();
  await expect(newFile.getByTestId("upload-choose-first")).toHaveText("Choose a file first.");
  await newFile.getByLabel("File").setInputFiles(textUpload(fileName, firstContent));
  await expect(newFile.getByTestId("file-input-name")).toHaveText(fileName);
  await expect(newFile.getByTestId("upload-choose-first")).toHaveCount(0);
  await newFile.getByLabel("Title").fill(title);
  await newFile.getByRole("button", { name: "Upload" }).click();
  await expect(newFile.getByTestId("upload-success")).toHaveText("Uploaded as version 1.");

  const row = files.getByTestId("device-file");
  await expect(row).toHaveCount(1);
  await expect(row.getByTestId("file-title")).toHaveText(title);
  await expect(row.getByTestId("file-kind")).toHaveText("Document");
  await expect(row.getByTestId("file-version")).toHaveText("1");
  await expect(row.getByTestId("file-user")).toHaveText(process.env.TWOX_E2E_USERNAME ?? "");
  await expect(row.getByTestId("checksum-short")).toHaveText(/^[0-9a-f]{12}…$/);

  // File page: version 2 with changed content.
  await row.getByRole("link", { name: title }).click();
  await expect(page).toHaveURL(/\/documents\/\d+$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(title);
  await expect(page.getByTestId("document-device").getByRole("link")).toContainText(deviceName);

  const newVersion = page.getByRole("form", { name: "Upload a new version" });
  await expect(newVersion.getByRole("button", { name: "Upload" })).toBeDisabled();
  await newVersion.getByLabel("File").setInputFiles(textUpload(fileName, secondContent));
  await newVersion.getByRole("button", { name: "Upload" }).click();
  await expect(newVersion.getByTestId("upload-success")).toHaveText("Uploaded as version 2.");
  // After the upload the chooser is empty again.
  await expect(newVersion.getByTestId("file-input-name")).toHaveText("No file chosen");

  const versions = page.getByTestId("document-version");
  await expect(versions.getByTestId("version-number")).toHaveText(["2", "1"]);
  await expect(versions.getByTestId("version-filename")).toHaveText([fileName, fileName]);

  // Download version 1: a plain link, the API sends it as an attachment.
  const link = page.getByRole("link", { name: "Download version 1" });
  const downloadPromise = page.waitForEvent("download");
  await link.click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe(fileName);
  expect(await download.failure()).toBeNull();
  // The content, read the same way with the session of the page.
  const href = await link.getAttribute("href");
  expect(href).toMatch(/^\/api\/v1\/document-versions\/\d+\/download\/$/);
  const fetched = await page.evaluate(async (url) => {
    const answer = await fetch(url);
    return { status: answer.status, disposition: answer.headers.get("Content-Disposition"), text: await answer.text() };
  }, href ?? "");
  expect(fetched.status).toBe(200);
  expect(fetched.disposition).toContain("attachment");
  expect(fetched.text).toBe(firstContent);

  // The same file again: 409, no third version.
  await newVersion.getByLabel("File").setInputFiles(textUpload(fileName, secondContent));
  await newVersion.getByRole("button", { name: "Upload" }).click();
  await expect(newVersion.getByTestId("upload-same-content")).toContainText(
    "The content equals version 2. No new version was created.",
  );
  await expect(versions).toHaveCount(2);

  // The address of the file opens directly; the change log names the upload.
  await page.reload();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(title);
  await expect(page.getByTestId("document-version")).toHaveCount(2);
  await expect(
    page.getByTestId("document-history").getByTestId("audit-entry").filter({ hasText: "Created" }),
  ).toHaveCount(1);

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});
