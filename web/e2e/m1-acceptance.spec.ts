import type { Locator, Page } from "@playwright/test";

import { expect, test, uniqueSuffix } from "./fixtures";

// Acceptance of M1 (docs/ROADMAP.md) in the browser: the device list of the
// test factory loaded per CSV (testfactory/layout/devices.csv); one file with
// two versions; the change log shows the changes. The same flow runs without
// a browser in backend/tests/acceptance/test_m1.py.
//
// The device list is the real, unchanged file of the test factory, mounted
// read-only into the e2e container (deploy/compose/compose.web.yaml). The
// uploaded file is made in the test, with a content unique per run; nothing
// comes from vendor documents. The test runs on a fresh database and again
// on one that already holds the device list (then the import is unchanged).
test.use({ locale: "en-US", storageState: { cookies: [], origins: [] } });

// The web UI has no Node types (@types/node is not a dependency): the spec
// reads environment variables, and setInputFiles wants a Buffer.
declare const process: { readonly env: Readonly<Record<string, string | undefined>> };
declare const Buffer: { from(text: string, encoding: "utf8"): unknown };

/** The device list of the test factory inside the e2e container. */
const DEVICE_LIST = "/testfactory/layout/devices.csv";

/** Numbers of the device list (work order 106): 14 data rows. */
const ROWS = 14;
const EXPECTED = { sites: 1, areas: 3, plants: 10, devices: 13 } as const;
const LEVELS = ["sites", "areas", "plants", "devices"] as const;

const SITE = "Testfabrik";
const AREAS = ["Fertigungslinie", "Roboterzelle", "Netzübergang"] as const;
const DEVICE_KEYS = [
  "dps-plc",
  "dps-txt",
  "hbw-plc",
  "drill-plc",
  "mill-plc",
  "aiqs-plc",
  "aiqs-txt",
  "agv-txt",
  "cgw-txt",
  "ccu-rpi",
  "aps-router",
  "ur5e",
  "opnsense-fw",
] as const;

function testAccount(): { username: string; password: string } {
  const username = process.env.TWOX_E2E_USERNAME;
  const password = process.env.TWOX_E2E_PASSWORD;
  if (username === undefined || username === "" || password === undefined || password === "") {
    throw new Error('TWOX_E2E_USERNAME and TWOX_E2E_PASSWORD must be set; see README, "Browser test"');
  }
  return { username, password };
}

/** GET from inside the page, with the session of the page. */
async function apiGet(page: Page, path: string): Promise<unknown> {
  const answer = await page.evaluate(async (url) => {
    const result = await fetch(url);
    return { status: result.status, body: (await result.json()) as unknown };
  }, path);
  expect(answer.status, `GET ${path}`).toBe(200);
  return answer.body;
}

/** Whether the device list is already in the database (the PLC of goods in and out exists). */
async function deviceListLoaded(page: Page): Promise<boolean> {
  const devices = (await apiGet(page, "/api/v1/devices/")) as readonly { key: string }[];
  return devices.some((device) => device.key === "dps-plc");
}

/** The SHA-256 checksum of a text as hex, as the API reports it. */
async function sha256(text: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function dryRun(page: Page): Promise<void> {
  await page.goto("/import");
  await expect(page.getByRole("heading", { level: 2 })).toHaveText("Import");
  await page.getByLabel("CSV file", { exact: true }).setInputFiles(DEVICE_LIST);
  await page.getByRole("button", { name: "Start dry run" }).click();
  await expect(page.getByTestId("import-summary")).toHaveText(
    `Dry run: nothing has been saved yet. ${String(ROWS)} rows read.`,
  );
  await expect(page.getByTestId("import-errors")).toHaveCount(0);
}

/** The counts of the shown report: created and changed per level. */
async function expectCounts(page: Page, created: Record<string, number>, updated: number): Promise<void> {
  for (const level of LEVELS) {
    await expect(page.getByTestId(`import-count-${level}-created`), `${level} created`).toHaveText(
      String(created[level] ?? 0),
    );
    await expect(page.getByTestId(`import-count-${level}-updated`), `${level} changed`).toHaveText(String(updated));
  }
}

/** Nothing new and nothing changed: every entry of the file is unchanged. */
async function expectUnchanged(page: Page): Promise<void> {
  await expectCounts(page, {}, 0);
  for (const level of LEVELS) {
    await expect(page.getByTestId(`import-count-${level}-unchanged`), `${level} unchanged`).toHaveText(
      String(EXPECTED[level]),
    );
  }
}

function item(page: Page, kind: "site" | "area" | "plant", name: string): Locator {
  return page
    .getByTestId(`${kind}-item`)
    .filter({ has: page.getByTestId(`${kind}-name`).getByText(name, { exact: true }) });
}

/** Opens /audit with a filter by object type and user. */
async function auditFor(page: Page, objectType: string, username: string): Promise<void> {
  await page.goto("/audit");
  await expect(page.getByRole("heading", { level: 2 })).toHaveText("Change log");
  await page.getByLabel("Object type").selectOption(objectType);
  await page.getByLabel("User").fill(username);
  await page.getByRole("button", { name: "Apply filter" }).click();
}

/** The change log rows whose object is exactly `objectRepr`. */
function auditRows(page: Page, objectRepr: string): Locator {
  return page
    .getByTestId("audit-entry")
    .filter({ has: page.getByTestId("audit-object").getByText(objectRepr, { exact: true }) });
}

async function expectCreatedBy(row: Locator, username: string): Promise<void> {
  await expect(row).toHaveCount(1);
  await expect(row.getByTestId("audit-action")).toHaveText("Created");
  await expect(row.getByTestId("audit-actor")).toHaveText(username);
  await expect(row.getByTestId("audit-timestamp").locator("time")).toHaveAttribute(
    "datetime",
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/,
  );
}

test("M1 acceptance: device list of the test factory, a file with two versions, the change log", async ({
  page,
}) => {
  test.setTimeout(180_000);
  const { username, password } = testAccount();

  // 1. Sign in through the sign-in page with the test account (role "manage").
  await test.step("sign in", async () => {
    await page.goto("/import");
    await expect(page).toHaveURL(/\/login\?next=%2Fimport$/);
    await page.getByLabel("Username").fill(username);
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).toHaveURL(/\/import$/);
    await expect(page.getByTestId("user-name")).toHaveText(username);
    await expect(page.getByTestId("user-role")).toHaveText("Manage");
  });

  // From here on the browser console stays free of errors. (Without a
  // session, the 403 of the account endpoint above is expected.)
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });
  page.on("pageerror", (error) => {
    consoleErrors.push(error.message);
  });

  // 2. Import the device list: dry run, then apply. On a fresh database
  // everything is new; with the list already loaded, nothing changes.
  const fresh = !(await deviceListLoaded(page));
  await test.step(fresh ? "import the device list (fresh database)" : "import the device list (already loaded)", async () => {
    await dryRun(page);
    if (fresh) {
      await expectCounts(page, EXPECTED, 0);
    } else {
      await expectUnchanged(page);
    }
    await page.getByRole("button", { name: "Apply" }).click();
    await expect(page.getByTestId("import-summary")).toHaveText(`Saved. ${String(ROWS)} rows imported.`);
    if (fresh) {
      await expectCounts(page, EXPECTED, 0);
    } else {
      await expectUnchanged(page);
    }
    await expect(page.getByRole("button", { name: "Apply" })).toHaveCount(0);
  });

  // 3. The structure: three areas, the PLC with its address, the charging
  // station without a device but with notes.
  await test.step("structure", async () => {
    await page.getByRole("link", { name: "Show the structure" }).click();
    await expect(page).toHaveURL(/\/$/);
    await page.getByLabel("Search", { exact: true }).fill(SITE);
    const site = item(page, "site", SITE);
    await expect(site).toHaveCount(1);
    // The tree sorts areas by name.
    await expect(site.getByTestId("area-name")).toHaveText(["Fertigungslinie", "Netzübergang", "Roboterzelle"]);
    await expect(site.getByTestId("device-count").first()).toHaveText(`${String(EXPECTED.devices)} devices`);

    const plc = site.getByTestId("device-item").filter({ has: page.getByTestId("device-key").getByText("dps-plc", { exact: true }) });
    await expect(plc.getByTestId("device-ip")).toHaveText("192.168.0.90");

    const charging = site
      .getByTestId("plant-item")
      .filter({ has: page.getByTestId("plant-key").getByText("aps-charging", { exact: true }) });
    await expect(charging.getByTestId("device-count").first()).toHaveText("0 devices");
    await expect(charging.getByTestId("device-item")).toHaveCount(0);
    await page.getByRole("button", { name: "Edit plant Ladestation" }).click();
    const plantForm = page.getByRole("form", { name: "Edit plant" });
    await expect(plantForm.getByLabel("Notes", { exact: true })).toHaveValue(/^Kein Gerät angelegt/);
    await plantForm.getByRole("button", { name: "Cancel" }).click();
    await expect(plantForm).toBeHidden();
  });

  // 4. A file of the PLC with two versions; the content is unique per run.
  const run = uniqueSuffix();
  const title = `M1 acceptance ${run}`;
  const fileName = `m1-acceptance-${run}.txt`;
  const contents = [`M1 acceptance test file ${run}\nversion 1\n`, `M1 acceptance test file ${run}\nversion 2\n`] as const;
  await test.step("file with two versions", async () => {
    await page
      .getByTestId("device-item")
      .filter({ has: page.getByTestId("device-key").getByText("dps-plc", { exact: true }) })
      .getByRole("link")
      .click();
    await expect(page).toHaveURL(/\/devices\/\d+$/);
    await expect(page.getByRole("heading", { level: 2 })).toHaveText("SPS Wareneingang und -ausgang");
    await expect(page.getByTestId("device-key")).toHaveText("dps-plc");

    const newFile = page.getByTestId("device-files").getByRole("form", { name: "Upload a new file" });
    await newFile.getByLabel("File").setInputFiles({
      name: fileName,
      mimeType: "text/plain",
      buffer: Buffer.from(contents[0], "utf8"),
    });
    await newFile.getByLabel("Title").fill(title);
    await newFile.getByRole("button", { name: "Upload" }).click();
    await expect(newFile.getByTestId("upload-success")).toHaveText("Uploaded as version 1.");

    const row = page.getByTestId("device-file").filter({ has: page.getByTestId("file-title").getByText(title) });
    await expect(row.getByTestId("file-version")).toHaveText("1");
    await row.getByRole("link", { name: title }).click();
    await expect(page).toHaveURL(/\/documents\/\d+$/);
    await expect(page.getByTestId("document-title")).toHaveText(title);

    const newVersion = page.getByRole("form", { name: "Upload a new version" });
    await newVersion.getByLabel("File").setInputFiles({
      name: fileName,
      mimeType: "text/plain",
      buffer: Buffer.from(contents[1], "utf8"),
    });
    await newVersion.getByRole("button", { name: "Upload" }).click();
    await expect(newVersion.getByTestId("upload-success")).toHaveText("Uploaded as version 2.");

    // Newest first, each with its own checksum and the user.
    const versions = page.getByTestId("document-version");
    await expect(versions.getByTestId("version-number")).toHaveText(["2", "1"]);
    await expect(versions.getByTestId("version-user")).toHaveText([username, username]);
    const [second, first] = [await sha256(contents[1]), await sha256(contents[0])];
    expect(second).not.toBe(first);
    await expect(versions.getByTestId("checksum-full")).toHaveText([second, first]);
    await expect(versions.getByTestId("checksum-short")).toHaveText([`${second.slice(0, 12)}…`, `${first.slice(0, 12)}…`]);
  });

  // 5. The change log: the import with the user (fresh database only: on a
  // database used before, the entries may lie beyond the first page), and
  // both versions of the file with user and time.
  if (fresh) {
    await test.step("change log of the import", async () => {
      await auditFor(page, "assets.site", username);
      await expectCreatedBy(auditRows(page, SITE), username);
      await auditFor(page, "assets.area", username);
      for (const area of AREAS) {
        await expectCreatedBy(auditRows(page, area), username);
      }
      await auditFor(page, "assets.plant", username);
      await expectCreatedBy(auditRows(page, "Ladestation (aps-charging)"), username);
      await auditFor(page, "assets.device", username);
      for (const key of DEVICE_KEYS) {
        const row = page
          .getByTestId("audit-entry")
          .filter({ has: page.getByTestId("audit-object").getByText(`(${key})`) });
        await expectCreatedBy(row, username);
      }
      const plc = page.getByTestId("audit-entry").filter({ has: page.getByTestId("audit-object").getByText("(dps-plc)") });
      await expect(plc.getByTestId("audit-change").filter({ hasText: /^ip_address: / })).toHaveText(
        "ip_address: (empty) → 192.168.0.90",
      );
    });
  }

  await test.step("change log of the two versions", async () => {
    await auditFor(page, "files.documentversion", username);
    const rows = page.getByTestId("audit-entry").filter({ hasText: title });
    await expect(rows).toHaveCount(2);
    await expect(rows.getByTestId("audit-object-type")).toHaveText(["File version", "File version"]);
    await expectCreatedBy(auditRows(page, `${title} v2`), username);
    await expectCreatedBy(auditRows(page, `${title} v1`), username);
    // Newest first: version 2 above version 1.
    await expect(rows.nth(0).getByTestId("audit-object")).toContainText(`${title} v2`);
    await expect(rows.nth(1).getByTestId("audit-object")).toContainText(`${title} v1`);
  });

  // 6. The same file again: nothing created, nothing changed.
  await test.step("repeat the import", async () => {
    await dryRun(page);
    await expectUnchanged(page);
  });

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});
