import type { Locator, Page } from "@playwright/test";

import { expect, test, testIp, testName, uniqueSuffix } from "./fixtures";

// Acceptance of M2 (docs/ROADMAP.md) in the browser: manuals ingested; the
// search finds an IP address and a question asked in other words; errors are
// visible. The whole way without a browser is backend/tests/acceptance/test_m2.py.
//
// Two parts:
// - The CI part runs everywhere. The CI starts no converter (Docling) and no
//   model service: a plain-text file is skipped at once by the format check
//   (work order 049), a Markdown file is queued and then runs or fails; no test
//   waits for a conversion or the end of the retries. The files are made here.
// - The local part runs only with TWOX_M2_LOCAL=1, in the test environment
//   with the manuals of the test factory (acceptance run, work order 060).
//   TWOX_M2_REQUIRED lists the file names of the manuals that must be
//   ingested (comma-separated), TWOX_M2_FAILED_FILE the file name of a job
//   that failed on purpose. Pages and identifiers come from
//   testfactory/questions.yaml, checksums from testfactory/manifest.yaml; the
//   questions are asked in the project's own words.
test.use({ locale: "en-US", storageState: { cookies: [], origins: [] } });

// The web UI has no Node types (@types/node is not a dependency): the spec
// reads environment variables, and setInputFiles wants a Buffer.
declare const process: { readonly env: Readonly<Record<string, string | undefined>> };
declare const Buffer: { from(text: string, encoding: "utf8"): unknown };

const SEARCH_API = "/api/v1/search/";
const INGEST_JOBS_API = "/api/v1/ingest-jobs/";

interface ApiAnswer {
  readonly status: number;
  readonly body: unknown;
}

interface IngestJob {
  readonly id: number;
  readonly status: string;
  readonly error_code: string;
  readonly document: { readonly id: number; readonly title: string };
  readonly version: { readonly id: number; readonly number: number; readonly original_filename: string };
  readonly device: { readonly id: number; readonly key: string; readonly name: string };
}

interface SearchHit {
  readonly match_kinds: readonly string[];
  readonly page_start: number | null;
  readonly page_end: number | null;
  readonly locations: readonly { readonly document: { readonly id: number } }[];
}

interface SearchAnswer {
  readonly semantic: "used" | "disabled" | "unavailable";
  readonly hits: readonly SearchHit[];
}

function testAccount(): { username: string; password: string } {
  const username = process.env.TWOX_E2E_USERNAME;
  const password = process.env.TWOX_E2E_PASSWORD;
  if (username === undefined || username === "" || password === undefined || password === "") {
    throw new Error('TWOX_E2E_USERNAME and TWOX_E2E_PASSWORD must be set; see README, "Browser test"');
  }
  return { username, password };
}

/** Opens `path` without a session and signs in through the sign-in page with the test account. */
async function signInAt(page: Page, path: string): Promise<string> {
  const { username, password } = testAccount();
  await page.goto(path);
  await expect(page).toHaveURL(/\/login\?next=/);
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByTestId("user-name")).toHaveText(username);
  await expect(page.getByTestId("user-role")).toHaveText("Manage");
  return username;
}

/** Errors in the browser console from now on. */
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

/** GET from inside the page, with the session of the page. */
async function apiGet<T>(page: Page, path: string): Promise<T> {
  const answer = await page.evaluate(async (url): Promise<ApiAnswer> => {
    const result = await fetch(url);
    return { status: result.status, body: (await result.json()) as unknown };
  }, path);
  expect(answer.status, `GET ${path}`).toBe(200);
  return answer.body as T;
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
  readonly key: string;
  readonly name: string;
  readonly plantId: number;
  readonly plantKey: string;
  readonly plantName: string;
}

/** A new test device with its site, area and plant. */
async function newDevice(page: Page, ip: number): Promise<TestDevice> {
  const siteId = await create(page, "/api/v1/sites/", { name: testName("site") });
  const areaId = await create(page, "/api/v1/areas/", { site: siteId, name: testName("area") });
  const plantKey = testName("plant");
  const plantName = testName("plant");
  const plantId = await create(page, "/api/v1/plants/", { area: areaId, key: plantKey, name: plantName });
  const key = testName("device");
  const name = testName("device");
  const id = await create(page, "/api/v1/devices/", { plant: plantId, key, name, ip_address: testIp(ip) });
  return { id, key, name, plantId, plantKey, plantName };
}

/** Uploads a file written here through the form on the device page; returns its title. */
async function upload(page: Page, deviceId: number, name: string, mimeType: string, content: string): Promise<string> {
  await page.goto(`/devices/${String(deviceId)}`);
  const form = page.getByTestId("device-files").getByRole("form", { name: "Upload a new file" });
  await form.getByLabel("File").setInputFiles({ name, mimeType, buffer: Buffer.from(content, "utf8") });
  const title = testName("file");
  await form.getByLabel("Title").fill(title);
  await form.getByRole("button", { name: "Upload" }).click();
  await expect(form.getByTestId("upload-success")).toHaveText("Uploaded as version 1.");
  return title;
}

/** The row of a file on the device page. */
function deviceFile(page: Page, title: string): Locator {
  return page.getByTestId("device-file").filter({ has: page.getByTestId("file-title").getByText(title, { exact: true }) });
}

/** The ingest state of version `number` on the page of a file. */
function versionIngest(page: Page, number = 1): Locator {
  return page.locator(`[data-testid="document-version"][data-version="${String(number)}"]`).getByTestId("version-ingest");
}

/** States of a Markdown file in the CI: no converter, so no test waits for the end. */
const MARKDOWN_STATES = /^(queued|running|failed)$/;
const MARKDOWN_TEXTS = /^(Queued|Ingesting.*|Error)$/;
const SKIPPED_REASON = /^This format is not ingested/;

/** Searches on the search page and returns the answer of the API. */
async function searchFor(page: Page, query: string): Promise<SearchAnswer> {
  const field = page.getByLabel("Search for");
  const answer = page.waitForResponse((received) => new URL(received.url()).pathname === SEARCH_API);
  await field.fill(query);
  await field.press("Enter");
  const received = await answer;
  expect(received.status(), `search for ${query}`).toBe(200);
  return (await received.json()) as SearchAnswer;
}

test("M2 acceptance, CI part: uploaded files with their ingest state, the ingest overview and the search page", async ({
  page,
}) => {
  test.setTimeout(180_000);
  // 1. Sign in through the sign-in page with the test account (role "manage");
  // from here on the browser console stays free of errors.
  const username = await signInAt(page, "/ingest");
  await expectIngestAddress(page, {});
  const consoleErrors = collectConsoleErrors(page);

  // 2. A plain-text file and a Markdown file at one new test device.
  const device = await newDevice(page, 58);
  const run = uniqueSuffix();
  const textName = `m2-acceptance-${run}.txt`;
  const markdownName = `m2-acceptance-${run}.md`;
  let textTitle = "";
  let markdownTitle = "";
  await test.step("upload a plain-text and a Markdown file", async () => {
    textTitle = await upload(page, device.id, textName, "text/plain", `M2 acceptance plain text ${run}\n`);
    markdownTitle = await upload(page, device.id, markdownName, "text/markdown", `# M2 acceptance ${run}\n\nA short test text.\n`);
    // The device page shows the state of the newest version of each file.
    await expect(deviceFile(page, textTitle).getByTestId("file-ingest")).toHaveText("Skipped");
    await expect(deviceFile(page, markdownTitle).getByTestId("file-ingest")).toHaveText(MARKDOWN_TEXTS);
  });

  // 3. The page of each file shows the state of its version.
  await test.step("state on the file pages", async () => {
    await deviceFile(page, textTitle).getByRole("link", { name: textTitle }).click();
    await expect(page).toHaveURL(/\/documents\/\d+$/);
    const text = versionIngest(page);
    await expect(text.getByTestId("ingest-status")).toHaveAttribute("data-status", "skipped");
    await expect(text.getByTestId("ingest-status")).toHaveText("Skipped");
    await expect(text.getByTestId("ingest-error")).toHaveAttribute("data-code", "unsupported_format");
    await expect(text.getByTestId("ingest-error-message")).toHaveText(SKIPPED_REASON);
    await text.getByText("Technical details").click();
    await expect(text.getByTestId("ingest-error-detail")).toHaveText(/^files with the extension \.txt are not ingested/);

    await page.goto(`/devices/${String(device.id)}`);
    await deviceFile(page, markdownTitle).getByRole("link", { name: markdownTitle }).click();
    await expect(page).toHaveURL(/\/documents\/\d+$/);
    const markdown = versionIngest(page).getByTestId("ingest-status");
    await expect(markdown).toHaveAttribute("data-status", MARKDOWN_STATES);
    await expect(markdown).toHaveText(MARKDOWN_TEXTS);
  });

  // 4. The ingest overview lists both jobs of the device under "All".
  await test.step("ingest overview", async () => {
    await page.goto(`/ingest?device=${String(device.id)}`);
    await page.getByTestId("ingest-filter-status").selectOption({ label: "All" });
    await expectIngestAddress(page, { status: "all", device: String(device.id) });
    const rows = page.getByTestId("ingest-job");
    await expect(rows).toHaveCount(2);

    const text = rows.filter({ has: page.getByTestId("ingest-job-version").getByText(textName) });
    await expect(text.getByTestId("ingest-status")).toHaveAttribute("data-status", "skipped");
    await expect(text.getByTestId("ingest-status")).toHaveText("Skipped");
    await expect(text.getByTestId("ingest-error-message")).toHaveText(SKIPPED_REASON);
    await expect(text.getByTestId("ingest-job-device")).toContainText(device.name);
    await expect(text.getByTestId("ingest-job-requested-by")).toHaveText(username);

    const markdown = rows.filter({ has: page.getByTestId("ingest-job-version").getByText(markdownName) });
    await expect(markdown.getByTestId("ingest-status")).toHaveAttribute("data-status", MARKDOWN_STATES);
    await expect(markdown.getByTestId("ingest-status")).toHaveText(MARKDOWN_TEXTS);
  });

  // 5. The search page is reachable through the navigation; a search without
  // hits says so. With the AI features off the search says so calmly; with
  // them on but no model service (the CI) it shows the hint (E-59).
  await test.step("search without hits", async () => {
    await page.getByRole("navigation", { name: "Main navigation" }).getByRole("link", { name: "Search" }).click();
    await expect(page).toHaveURL(/\/search$/);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("Search");
    const word = `zzq${run.replace(/[^a-z0-9]/g, "")}`;
    const answer = await searchFor(page, word);
    expect(answer.hits).toEqual([]);
    await expect(page.getByTestId("search-no-hits")).toHaveText("No hits. Try other words, or search all devices.");
    await expect(page.getByTestId("search-results")).toHaveAttribute("data-semantic", answer.semantic);
    await expect(page.getByTestId("search-semantic-disabled")).toHaveCount(answer.semantic === "disabled" ? 1 : 0);
    await expect(page.getByTestId("search-semantic-unavailable")).toHaveCount(answer.semantic === "unavailable" ? 1 : 0);
  });

  // 6. AI features on (a stand-in answer with a hit by meaning) and off (the
  // same hit by keyword): written by the test (page.route), plain test sentences.
  await test.step("search with the AI features on and off (answers written by the test)", async () => {
    const hit = (kind: string): object => ({
      section_id: 1,
      score: 1,
      match_kinds: [kind],
      snippet: `The e2e test station is checked once a year (${run}).`,
      highlights: [],
      page_start: 3,
      page_end: 3,
      heading_path: ["e2e chapter"],
      locations: [
        {
          document: { id: 2_147_483_001, title: "e2e test manual" },
          version: { id: 1, number: 1, original_filename: "e2e-test-manual.pdf", is_latest: true },
          device: { id: device.id, key: device.key, name: device.name },
          plant: { id: device.plantId, key: device.plantKey, name: device.plantName },
        },
      ],
    });
    let answer: object = { semantic: "used", hits: [hit("semantic")] };
    await page.route(
      (url) => url.pathname === SEARCH_API,
      async (route) => {
        await route.fulfill({ json: answer });
      },
    );

    await searchFor(page, "how often is the station checked");
    const found = page.getByTestId("search-hit");
    await expect(found).toHaveCount(1);
    await expect(found.getByTestId("search-match-kind")).toHaveText("Meaning");
    await expect(found.getByTestId("search-hit-page")).toHaveText("p. 3");
    await expect(page.getByTestId("search-semantic-disabled")).toHaveCount(0);
    await expect(page.getByTestId("search-semantic-unavailable")).toHaveCount(0);

    answer = { semantic: "disabled", hits: [hit("keyword")] };
    await searchFor(page, "station checked");
    await expect(found).toHaveCount(1);
    await expect(found.getByTestId("search-match-kind")).toHaveText("Keyword");
    // A normal state, not an error: a calm line without a warning.
    await expect(page.getByTestId("search-semantic-disabled")).toHaveText("Keyword search (AI features not enabled)");
    await expect(page.getByTestId("search-semantic-disabled").locator("svg")).toHaveCount(0);
    await expect(page.getByTestId("search-semantic-unavailable")).toHaveCount(0);
    await page.unroute((url) => url.pathname === SEARCH_API);
  });

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});

// --- Local part (acceptance run 060) -----------------------------------------------

const LOCAL = process.env.TWOX_M2_LOCAL === "1";

/** A manual of the test factory: checksum from testfactory/manifest.yaml. */
interface Manual {
  readonly manifestId: string;
  readonly sha256: string;
}

const APS_DOCUMENTATION_DE: Manual = {
  manifestId: "aps-documentation-de",
  sha256: "662ae19b00945aab2b014c72d6a6bd966403bf0f2cc2b939f6b97a4658350d55",
};
// The English edition of the same documentation. A place in the other language
// edition counts as correct (E-61); it has the same pages as the German one
// (compared at the files in work order 067, like backend/twox/search/probes/m2.json).
const APS_DOCUMENTATION_EN: Manual = {
  manifestId: "aps-documentation-en",
  sha256: "f4555cab6cdc25d39769d7388b848622d23c1c4180ccb519c2965a4db19304d2",
};
const UR5E_USER_MANUAL_DE: Manual = {
  manifestId: "ur5e-user-manual-de",
  sha256: "70940ab1cd824a2af60e75d1f2437f45fe479f2394057e267fecfe8448266102",
};
const UR5E_SOFTWARE_HANDBOOK_EN: Manual = {
  manifestId: "ur5e-software-handbook-en",
  sha256: "06488da8a8bc2be51e796d2e62e2f90ad4b00412acbac016c232780b1d0ee3ba",
};

/**
 * A search of the acceptance: the query and where the answer must be found (PDF pages of
 * questions.yaml, or the same pages in the other language edition of the manual, E-61).
 */
interface Probe {
  readonly name: string;
  readonly query: string;
  readonly within: number;
  /** false: the rank is only reported (annotation `rank`), not required (E-67). */
  readonly required: boolean;
  readonly expected: readonly { readonly manual: Manual; readonly pages: readonly number[] }[];
}

const PROBES: readonly Probe[] = [
  {
    // Test question 1: the address of the central control, in either language edition (E-61).
    name: "IP address of the central control (question 1)",
    query: "192.168.0.100",
    within: 3,
    required: true,
    expected: [
      { manual: APS_DOCUMENTATION_DE, pages: [18, 31, 38] },
      { manual: APS_DOCUMENTATION_EN, pages: [18, 31, 38] },
    ],
  },
  {
    // Test question 9: the payload of the robot arm, in the project's own words.
    name: "payload of the UR5e (question 9)",
    query: "Wie schwer darf eine Last höchstens sein, die der UR5e bewegen soll?",
    within: 5,
    required: true,
    expected: [{ manual: UR5E_USER_MANUAL_DE, pages: [16, 101, 102] }],
  },
  {
    // Test question 10 as meant by E-33: release after a stop by a safeguard (SF2).
    // Not required (E-67): the ROADMAP asks for one question in other words
    // (question 9); the rank of question 10 depends on the wording and is only
    // reported, a topic for M3 (docs/ARCHITECTURE.md, limits of the search).
    name: "release after a safeguard stop (question 10)",
    query: "Wie gibt man den UR5e wieder frei, wenn eine Schutzeinrichtung ihn angehalten hat?",
    within: 5,
    required: false,
    expected: [
      { manual: UR5E_USER_MANUAL_DE, pages: [81, 84, 86, 252] },
      { manual: UR5E_SOFTWARE_HANDBOOK_EN, pages: [46] },
    ],
  },
];

/** Every ingest job, newest first (all pages of the list). */
async function allJobs(page: Page): Promise<IngestJob[]> {
  const jobs: IngestJob[] = [];
  for (let number = 1; ; number += 1) {
    const answer = await apiGet<{ next: string | null; results: IngestJob[] }>(page, `${INGEST_JOBS_API}?page=${String(number)}`);
    jobs.push(...answer.results);
    if (answer.next === null) {
      return jobs;
    }
  }
}

/** The newest job of each version whose file is called `filename`. */
function newestJobsOf(jobs: readonly IngestJob[], filename: string): IngestJob[] {
  const newest = new Map<number, IngestJob>();
  for (const job of jobs) {
    if (job.version.original_filename === filename && !newest.has(job.version.id)) {
      newest.set(job.version.id, job);
    }
  }
  return [...newest.values()];
}

/** The ids of the files whose newest version has the checksum of `manual`. */
async function documentsOf(page: Page, manual: Manual): Promise<Set<number>> {
  const devices = await apiGet<readonly { id: number }[]>(page, "/api/v1/devices/");
  const ids = new Set<number>();
  for (const device of devices) {
    const documents = await apiGet<readonly { id: number; latest_version: { sha256: string } | null }[]>(
      page,
      `/api/v1/devices/${String(device.id)}/documents/`,
    );
    for (const document of documents) {
      if (document.latest_version?.sha256 === manual.sha256) {
        ids.add(document.id);
      }
    }
  }
  return ids;
}

/** The row of `job` in the ingest overview of its device under `status`, turning pages if needed. */
async function overviewRow(page: Page, job: IngestJob, status: string): Promise<Locator> {
  await page.goto(`/ingest?status=${status}&device=${String(job.device.id)}`);
  const list = page.getByTestId("ingest-jobs");
  const row = page.locator(`[data-testid="ingest-job"][data-job="${String(job.id)}"]`);
  const notListed = new Error(`job ${String(job.id)} (${job.version.original_filename}) is not listed under ${status}`);
  for (let shown = 1; ; shown += 1) {
    // The page keeps the rows of the previous page while the next one loads
    // (keepPreviousData, aria-busy): look only once the list shows page `shown`.
    await expect(list).toHaveAttribute("aria-busy", "false");
    if ((await page.getByTestId("ingest-empty").count()) > 0) {
      throw notListed;
    }
    const pageStatus = page.getByTestId("ingest-page-status");
    await expect(pageStatus).toHaveText(new RegExp(`^Page ${String(shown)} of \\d+$`));
    if ((await row.count()) > 0) {
      return row;
    }
    const pages = Number(/of (\d+)$/.exec((await pageStatus.textContent()) ?? "")?.[1] ?? "0");
    if (shown >= pages) {
      throw notListed;
    }
    await page.getByTestId("ingest-next").click();
    await expect(pageStatus).toHaveText(new RegExp(`^Page ${String(shown + 1)} of \\d+$`));
  }
}

/** The address is /ingest with these parameters; other parameters (such as a later `latest`) may stand there as well. */
async function expectIngestAddress(page: Page, params: Readonly<Record<string, string>>): Promise<void> {
  await expect(page).toHaveURL((url) => {
    if (url.pathname !== "/ingest") {
      return false;
    }
    return Object.entries(params).every(([name, value]) => url.searchParams.get(name) === value);
  });
}

function pageText(hit: SearchHit): string {
  if (hit.page_start === null) {
    return "";
  }
  // As the search page writes it (pageRange in web/src/components/sources/snippet.ts).
  return hit.page_end === null || hit.page_end <= hit.page_start
    ? `p. ${String(hit.page_start)}`
    : `pp. ${String(hit.page_start)}–${String(hit.page_end)}`;
}

test("M2 acceptance, local part: the manuals of the test factory are ingested and found", async ({ page }) => {
  test.skip(
    !LOCAL,
    "Local part: runs only with TWOX_M2_LOCAL=1 in the test environment with the manuals (acceptance run, work order 060).",
  );
  test.setTimeout(600_000);
  const required = (process.env.TWOX_M2_REQUIRED ?? "")
    .split(",")
    .map((name) => name.trim())
    .filter((name) => name !== "");
  const failedFile = (process.env.TWOX_M2_FAILED_FILE ?? "").trim();
  expect(required, "TWOX_M2_REQUIRED lists the file names of the required manuals").not.toEqual([]);
  expect(failedFile, "TWOX_M2_FAILED_FILE names the file of the job that failed on purpose").not.toBe("");

  await signInAt(page, "/ingest?status=all");
  await expectIngestAddress(page, { status: "all" });
  const consoleErrors = collectConsoleErrors(page);
  const jobs = await allJobs(page);

  // 1. Nothing is running or queued any more: on the overview under "All",
  // and over all pages of the list.
  await test.step("no job running or queued", async () => {
    await expect(page.getByTestId("ingest-jobs")).toBeVisible();
    await expect(page.getByTestId("ingest-filter-status")).toHaveValue("all");
    await expect(page.locator('[data-testid="ingest-job"][data-status="running"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="ingest-job"][data-status="queued"]')).toHaveCount(0);
    await expect(page.getByTestId("ingest-polling")).toHaveCount(0);
    const open = jobs.filter((job) => job.status === "running" || job.status === "queued");
    expect(open.map((job) => `${job.version.original_filename}: ${job.status}`)).toEqual([]);
  });

  // 2. Every required manual is ingested (the newest job of each of its versions).
  for (const filename of required) {
    await test.step(`ingested: ${filename}`, async () => {
      const newest = newestJobsOf(jobs, filename);
      expect(newest.length, `${filename} has an ingest job`).toBeGreaterThan(0);
      for (const job of newest) {
        expect(job.status, `${filename}, version ${String(job.version.number)}`).toBe("done");
        const row = await overviewRow(page, job, "all");
        await expect(row.getByTestId("ingest-status")).toHaveAttribute("data-status", "done");
        await expect(row.getByTestId("ingest-status")).toHaveText("Ingested");
        await expect(row.getByTestId("ingest-job-version")).toContainText(filename);
      }
    });
  }

  // 3. The searches of the acceptance: the address of question 1 among the
  // first three hits, question 9 in other words among the first five (the
  // ROADMAP criterion, E-67). Question 10 is asked as well, but its rank is
  // only reported as the annotation "rank" (a known limit, M3).
  await page.goto("/search");
  for (const probe of PROBES) {
    await test.step(`search: ${probe.name}`, async () => {
      const expected = await Promise.all(
        probe.expected.map(async ({ manual, pages }) => ({ documents: await documentsOf(page, manual), pages })),
      );
      expect(
        expected.some(({ documents }) => documents.size > 0),
        `a file of ${probe.expected.map(({ manual }) => manual.manifestId).join(" or ")} is uploaded`,
      ).toBe(true);
      const answer = await searchFor(page, probe.query);
      const hits = probe.required ? answer.hits.slice(0, probe.within) : answer.hits;
      const index = hits.findIndex((hit) =>
        expected.some(
          ({ documents, pages }) =>
            hit.locations.some((location) => documents.has(location.document.id)) &&
            hit.page_start !== null &&
            pages.some((number) => (hit.page_start ?? 0) <= number && number <= (hit.page_end ?? hit.page_start ?? 0)),
        ),
      );
      test.info().annotations.push({
        type: "rank",
        description: `${probe.name}: ${index >= 0 ? String(index + 1) : "not found"} of ${String(answer.hits.length)} hits (semantic: ${answer.semantic})`,
      });
      if (!probe.required) {
        return;
      }
      expect(index, `expected place among the first ${String(probe.within)} hits (semantic: ${answer.semantic})`).toBeGreaterThanOrEqual(0);

      // The same hit on the page: its page and a link to the file.
      const hit = answer.hits[index];
      if (hit === undefined) {
        throw new Error("the hit found above is missing");
      }
      const card = page.getByTestId("search-hit").nth(index);
      await expect(card.getByTestId("search-hit-page")).toHaveText(pageText(hit));
      const links = await card.getByRole("link").evaluateAll((anchors) => anchors.map((anchor) => anchor.getAttribute("href")));
      expect(links.some((href) => hit.locations.some((location) => href === `/documents/${String(location.document.id)}`))).toBe(true);
    });
  }

  // 4. A job that failed on purpose is shown with its message.
  await test.step(`failed with a message: ${failedFile}`, async () => {
    const job = newestJobsOf(jobs, failedFile)[0];
    if (job === undefined) {
      throw new Error(`${failedFile} has no ingest job`);
    }
    expect(job.status, `${failedFile}, version ${String(job.version.number)}`).toBe("failed");
    const row = await overviewRow(page, job, "failed");
    await expect(row.getByTestId("ingest-status")).toHaveAttribute("data-status", "failed");
    await expect(row.getByTestId("ingest-status")).toHaveText("Error");
    await expect(row.getByTestId("ingest-error")).toHaveAttribute("data-code", job.error_code);
    await expect(row.getByTestId("ingest-error-message")).not.toBeEmpty();

    // The page of the file shows the same message.
    await row.getByTestId("ingest-job-document-link").click();
    await expect(page).toHaveURL(new RegExp(`/documents/${String(job.document.id)}$`));
    const state = versionIngest(page, job.version.number);
    await expect(state.getByTestId("ingest-status")).toHaveAttribute("data-status", "failed");
    await expect(state.getByTestId("ingest-error-message")).not.toBeEmpty();
  });

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});
