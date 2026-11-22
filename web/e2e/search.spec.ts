import type { Page } from "@playwright/test";

import { expect, test, testIp, testName, uniqueSuffix } from "./fixtures";

// Search page as served by Django (work order 054). The CI starts no converter
// (Docling) and no model service, so nothing is ingested there: a real search
// finds nothing, and the hits come from an answer written by the test
// (page.route) with plain test sentences, not from any manual.
test.use({ locale: "en-US" });

const SEARCH_API = "/api/v1/search/";

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
  readonly key: string;
  readonly name: string;
  readonly plantId: number;
  readonly plantKey: string;
  readonly plantName: string;
}

/** A new test device with its site, area and plant. */
async function newDevice(page: Page, ip: number): Promise<TestDevice> {
  await page.goto("/");
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

test("the navigation leads to the search page, which waits for a search text", async ({ page }) => {
  const consoleErrors = collectConsoleErrors(page);
  await page.goto("/");
  const navigation = page.getByRole("navigation", { name: "Main navigation" });

  await navigation.getByRole("link", { name: "Search" }).click();

  await expect(page).toHaveURL(/\/search$/);
  await expect(page.getByRole("heading", { level: 2 })).toHaveText("Search");
  await expect(navigation.getByRole("link", { name: "Search" })).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("search", { name: "Search the files" })).toBeVisible();
  await expect(page.getByTestId("search-empty")).toBeVisible();
  await expect(page.getByLabel("Search for")).toBeVisible();
  await expect(page.getByLabel("Device")).toBeVisible();

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});

test.describe("without a session", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("the search page leads to the sign-in page and back", async ({ page }) => {
    await page.goto("/search");

    await expect(page).toHaveURL(/\/login\?next=%2Fsearch$/);
    await expect(page.getByTestId("login-form")).toBeVisible();
    await expect(page.getByTestId("search-form")).toHaveCount(0);
  });
});

test("a search without hits says so, and the search text stands in the address", async ({ page }) => {
  const consoleErrors = collectConsoleErrors(page);
  await page.goto("/search");
  // A word no test data contains; this real search reaches the API.
  const word = `zzq${uniqueSuffix().replace(/[^a-z0-9]/g, "")}`;
  const answer = page.waitForResponse((received) => new URL(received.url()).pathname === SEARCH_API);

  const field = page.getByLabel("Search for");
  await field.fill(word);
  await field.press("Enter");

  expect((await answer).status()).toBe(200);
  await expect(page).toHaveURL(new RegExp(`/search\\?q=${word}$`));
  await expect(page.getByTestId("search-no-hits")).toHaveText("No hits. Try other words, or search all devices.");
  await expect(page.getByTestId("search-hit")).toHaveCount(0);

  // Reloading the address runs the same search again.
  await page.reload();
  await expect(page.getByLabel("Search for")).toHaveValue(word);
  await expect(page.getByTestId("search-no-hits")).toBeVisible();

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});

test("hits show page, heading path, marked snippet, device and links", async ({ page }) => {
  const consoleErrors = collectConsoleErrors(page);
  const device = await newDevice(page, 54);
  const documentId = 2_147_483_000;

  // The answer of the API, written by the test. Places name the real test
  // device (its link opens its page); the file id does not exist.
  const snippet = "\u{1F600} The e2e inspection of the test station is due every year.";
  const start = Array.from(snippet).indexOf("i");
  const result = {
    semantic: "unavailable",
    hits: [
      {
        section_id: 1,
        score: 1,
        match_kinds: ["keyword"],
        snippet,
        highlights: [{ start, end: start + "inspection".length }],
        page_start: 31,
        page_end: 32,
        heading_path: ["e2e chapter", "e2e section"],
        locations: [
          {
            document: { id: documentId, title: "e2e test manual" },
            version: { id: 1, number: 2, original_filename: "e2e-test-manual.pdf", is_latest: false },
            device: { id: device.id, key: device.key, name: device.name },
            plant: { id: device.plantId, key: device.plantKey, name: device.plantName },
          },
        ],
      },
      {
        section_id: 2,
        score: 0.5,
        match_kinds: ["exact"],
        snippet: "Address 192.0.2.54 of the e2e test station.",
        highlights: [{ start: 8, end: 18 }],
        page_start: 7,
        page_end: 7,
        heading_path: [],
        locations: [
          {
            document: { id: documentId, title: "e2e test manual" },
            version: { id: 2, number: 3, original_filename: "e2e-test-manual-3.pdf", is_latest: true },
            device: { id: device.id, key: device.key, name: device.name },
            plant: { id: device.plantId, key: device.plantKey, name: device.plantName },
          },
        ],
      },
    ],
  };
  const searches: URL[] = [];
  await page.route(
    (url) => url.pathname === SEARCH_API,
    async (route) => {
      searches.push(new URL(route.request().url()));
      await route.fulfill({ json: result });
    },
  );

  await page.goto("/search");
  await page.getByLabel("Device").selectOption(String(device.id));
  await page.getByLabel("Search for").fill("e2e inspection");
  await page.getByLabel("Search for").press("Enter");

  const hits = page.getByTestId("search-hit");
  await expect(hits).toHaveCount(2);
  expect(searches.at(-1)?.searchParams.get("q")).toBe("e2e inspection");
  expect(searches.at(-1)?.searchParams.getAll("device")).toEqual([String(device.id)]);
  await expect(page).toHaveURL(new RegExp(`/search\\?q=e2e\\+inspection&device=${String(device.id)}$`));

  await expect(page.getByTestId("search-semantic-unavailable")).toHaveText(
    "Keyword search only – language model not reachable",
  );
  const first = hits.nth(0);
  await expect(first.getByTestId("search-hit-page")).toHaveText("pp. 31–32");
  await expect(first.getByTestId("search-hit-heading-path")).toHaveText("Section: e2e chapter › e2e section");
  await expect(first.locator("mark")).toHaveText("inspection");
  await expect(first.getByTestId("search-snippet")).toHaveText(snippet);
  await expect(first.getByTestId("search-match-kind")).toHaveText("Keyword");
  await expect(first.getByTestId("search-older-version")).toHaveText("Older version");
  await expect(first.getByTestId("search-location-filename")).toHaveText("e2e-test-manual.pdf");
  await expect(first.getByTestId("search-location-plant")).toHaveText(`Plant: ${device.plantName}`);
  await expect(first.getByRole("link", { name: "e2e test manual" })).toHaveAttribute(
    "href",
    `/documents/${String(documentId)}`,
  );
  const second = hits.nth(1);
  await expect(second.getByTestId("search-hit-page")).toHaveText("p. 7");
  await expect(second.locator("mark")).toHaveText("192.0.2.54");
  await expect(second.getByTestId("search-older-version")).toHaveCount(0);

  // The device link opens the page of the real test device.
  await first.getByRole("link", { name: device.name }).click();
  await expect(page).toHaveURL(new RegExp(`/devices/${String(device.id)}$`));
  await expect(page.getByRole("heading", { level: 2 })).toHaveText(device.name);

  // Back returns to the same search with its device.
  await page.goBack();
  await expect(page.getByTestId("search-hit")).toHaveCount(2);
  await expect(page.getByLabel("Device")).toHaveValue(String(device.id));

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});
