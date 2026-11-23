import type { Page, Request, Route } from "@playwright/test";

import { expect, test, testIp, testName } from "./fixtures";

// Acceptance of M3 in the browser, CI part (work order 137): question and
// answer, the sources shown, the limit to a device or plant, "AI off",
// "no evidence" and a failure on the page "Ask", in German and English. The
// local part with the real chat model is m3-acceptance.spec.ts; the judgement
// of the test questions is backend/tests/acceptance/test_m3.py.
//
// The CI has no chat model, so the test answers both endpoints itself
// (page.route): GET /api/v1/answers/status/ and POST /api/v1/answers/ with a
// stream of server-sent events in the format of the event contract
// (docs/ARCHITECTURE.md, "Server-sent events"). Every text is a test sentence
// written here. route.fulfill sends the stream in one piece: that the text
// grows piece by piece is checked by the Vitest tests of work orders 131 and
// 132; here a sentence that only a `delta` holds must be gone once
// `done.final_text` replaces the pieces (D8, D9).
//
// No axe package (question 2 of work order 137, option (a)): accessibility is
// checked with roles, accessible names, role="status", role="alert",
// aria-busy and the keyboard.

const STATUS_API = "/api/v1/answers/status/";
const ANSWERS_API = "/api/v1/answers/";
const DOCUMENT_ID = 2_147_483_137;
const DOCUMENT_TITLE = "e2e test manual";
const FILE_NAME = "e2e-test-manual.pdf";

interface AnswerStatus {
  readonly enabled: boolean;
  readonly chat_model_configured: boolean;
  readonly available: boolean;
}

const AVAILABLE: AnswerStatus = {
  enabled: true,
  chat_model_configured: true,
  available: true,
};
const AI_OFF: AnswerStatus = {
  enabled: false,
  chat_model_configured: false,
  available: false,
};

type StreamEvent = Readonly<Record<string, unknown>> & {
  readonly type: "sources" | "delta" | "done" | "error";
};

/** One source of the `sources` event, at one place (all values made up here). */
function source(n: number, page: number): Record<string, unknown> {
  return {
    n,
    section_id: 9_000 + n,
    version_id: 9_100,
    sha256: "0".repeat(64),
    page_start: page,
    page_end: page,
    heading_path: ["e2e chapter"],
    snippet: `Test snippet ${String(n)} of the e2e manual.`,
    locations: [
      {
        section_id: 9_000 + n,
        document_id: DOCUMENT_ID,
        document_title: DOCUMENT_TITLE,
        version_id: 9_100,
        version_number: 1,
        version_filename: FILE_NAME,
        is_latest_version: true,
        device_id: 9_200,
        device_key: "e2e-device",
        device_name: "e2e test device",
        plant_id: 9_300,
        plant_key: "e2e-plant",
        plant_name: "e2e test plant",
      },
    ],
  };
}

const KEPT_SENTENCE = "The e2e test station runs at 24 V [1].";
const MARKUP_SENTENCE = 'A tag <img src="/e2e-missing-image.png"> stays text [2].';
const REMOVED_SENTENCE = "A removed e2e sentence without evidence.";

/** An answer with two cited sources; one sentence of the pieces is not in the checked text. */
const ANSWERED: readonly StreamEvent[] = [
  { type: "sources", sources: [source(1, 14), source(2, 3)] },
  { type: "delta", text: `${KEPT_SENTENCE} ` },
  { type: "delta", text: `${REMOVED_SENTENCE} ` },
  { type: "delta", text: MARKUP_SENTENCE },
  {
    type: "done",
    status: "answered",
    cited: [1, 2],
    removed_sentences: 1,
    final_text: `${KEPT_SENTENCE} ${MARKUP_SENTENCE}`,
  },
];

const NO_EVIDENCE: readonly StreamEvent[] = [
  { type: "sources", sources: [] },
  {
    type: "done",
    status: "no_evidence",
    cited: [],
    removed_sentences: 0,
    final_text: "Server text of the e2e test.",
  },
];

const RAW_DETAIL = "e2e raw detail from the model server";
const FAILED: readonly StreamEvent[] = [
  { type: "sources", sources: [source(1, 14)] },
  { type: "delta", text: "Half an e2e sentence" },
  { type: "error", code: "model_unavailable", detail: RAW_DETAIL },
];

/** The body of a stream: `event: <type>` and `data: <JSON>` with an empty line after each event. */
function eventStream(events: readonly StreamEvent[]): string {
  return events.map((event) => `event: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`).join("");
}

/** What the answer endpoint does for the next questions. */
type AnswerReply = { readonly events: readonly StreamEvent[] } | { readonly status: number; readonly json: object };

interface AnswerRoutes {
  /** Every POST to the answer endpoint, in order. */
  readonly posts: Request[];
}

/** Answers the status and the answer endpoint for this page. */
async function routeAnswers(page: Page, status: AnswerStatus, reply: AnswerReply): Promise<AnswerRoutes> {
  const posts: Request[] = [];
  await page.route(
    (url) => url.pathname === STATUS_API,
    async (route: Route) => {
      await route.fulfill({ json: status });
    },
  );
  await page.route(
    (url) => url.pathname === ANSWERS_API,
    async (route: Route) => {
      if (route.request().method() !== "POST") {
        await route.fallback();
        return;
      }
      posts.push(route.request());
      if ("events" in reply) {
        await route.fulfill({
          status: 200,
          headers: {
            "Content-Type": "text/event-stream; charset=utf-8",
            "Cache-Control": "no-cache",
          },
          body: eventStream(reply.events),
        });
      } else {
        await route.fulfill({ status: reply.status, json: reply.json });
      }
    },
  );
  return { posts };
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
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
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
  readonly plantName: string;
}

/** A new test device with its site, area and plant (as in m2-acceptance.spec.ts). */
async function newDevice(page: Page, ip: number): Promise<TestDevice> {
  const siteId = await create(page, "/api/v1/sites/", {
    name: testName("site"),
  });
  const areaId = await create(page, "/api/v1/areas/", {
    site: siteId,
    name: testName("area"),
  });
  const plantName = testName("plant");
  const plantId = await create(page, "/api/v1/plants/", {
    area: areaId,
    key: testName("plant"),
    name: plantName,
  });
  const key = testName("device");
  const name = testName("device");
  const id = await create(page, "/api/v1/devices/", {
    plant: plantId,
    key,
    name,
    ip_address: testIp(ip),
  });
  return { id, key, name, plantId, plantName };
}

/** The JSON body of a POST to the answer endpoint. */
function requestBody(request: Request | undefined): Record<string, unknown> {
  if (request === undefined) {
    throw new Error("no POST to the answer endpoint");
  }
  return request.postDataJSON() as Record<string, unknown>;
}

const LANGUAGES = [
  {
    locale: "en-US",
    ip: 137,
    navigation: "Main navigation",
    entry: "Ask",
    heading: "Ask",
    answer: "Answer",
    form: "Ask a question",
    question: "Question",
    button: "Ask",
    done: "Done",
    checked: "Answer with checked sources",
    removed: "Statements without evidence were removed.",
    sources: "Sources",
    page14: "p. 14",
    citation: `Source 1: ${DOCUMENT_TITLE}, page 14`,
    noEvidence: "I can't find anything on this in the documents.",
    off: "The AI features are switched off, so there are no answers.",
    toSearch: "Go to the search",
    modelUnavailable: "The language model cannot be reached.",
    limitedDevice: "Limited to: device",
    limitedPlant: "Limited to: plant",
    reset: "Remove limit",
    askDevice: "Ask about this device",
  },
  {
    locale: "de-DE",
    ip: 138,
    navigation: "Hauptnavigation",
    entry: "Auskunft",
    heading: "Auskunft",
    answer: "Antwort",
    form: "Frage stellen",
    question: "Frage",
    button: "Fragen",
    done: "Fertig",
    checked: "Antwort mit geprüften Quellen",
    removed: "Nicht belegte Aussagen wurden entfernt.",
    sources: "Quellen",
    page14: "S. 14",
    citation: `Quelle 1: ${DOCUMENT_TITLE}, Seite 14`,
    noEvidence: "Dazu finde ich nichts in den Unterlagen.",
    off: "Die KI-Funktionen sind ausgeschaltet, deshalb gibt es keine Antworten.",
    toSearch: "Zur Suche",
    modelUnavailable: "Das Sprachmodell ist nicht erreichbar.",
    limitedDevice: "Eingegrenzt auf: Gerät",
    limitedPlant: "Eingegrenzt auf: Anlage",
    reset: "Eingrenzung aufheben",
    askDevice: "Frage zu diesem Gerät",
  },
] as const;

for (const language of LANGUAGES) {
  test.describe(`answers on the page "Ask" (${language.locale})`, () => {
    test.use({ locale: language.locale });

    test("reached through the main navigation", async ({ page }) => {
      const consoleErrors = collectConsoleErrors(page);
      await routeAnswers(page, AVAILABLE, { events: NO_EVIDENCE });
      await page.goto("/");
      await page
        .getByRole("navigation", { name: language.navigation })
        .getByRole("link", { name: language.entry })
        .click();
      await expect(page).toHaveURL(/\/ask$/);
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(language.heading);
      await expect(page.getByRole("form", { name: language.form })).toBeVisible();
      expect(consoleErrors, "errors in the browser console").toEqual([]);
    });

    test("question and answer with sources, sent with the keyboard", async ({ page }) => {
      const consoleErrors = collectConsoleErrors(page);
      const routes = await routeAnswers(page, AVAILABLE, { events: ANSWERED });
      // ?q= only fills the field; nothing is sent (D14 (i)).
      await page.goto("/ask?q=e2e%20prefilled%20question");
      const form = page.getByRole("form", { name: language.form });
      const question = form.getByRole("textbox", { name: language.question });
      await expect(question).toHaveValue("e2e prefilled question");
      await expect(form.getByRole("button", { name: language.button })).toBeEnabled();
      expect(routes.posts, "no POST from ?q=").toHaveLength(0);

      // Typed and sent with Ctrl+Enter; the focus stays in the form.
      await page.goto("/ask");
      const asked = "How is the e2e test station supplied?";
      await question.focus();
      await page.keyboard.type(asked);
      await page.keyboard.press("Control+Enter");
      const status = page.getByTestId("answer-status");
      await expect(status).toHaveAttribute("role", "status");
      await expect(status).toHaveText(language.done);
      await expect(question).toBeFocused();

      // The question travels in the body only, never in the address (D14, E-54).
      expect(routes.posts).toHaveLength(1);
      expect(requestBody(routes.posts[0])).toEqual({ question: asked });
      expect(new URL(routes.posts[0]?.url() ?? "http://x/").search).toBe("");
      await expect(page).toHaveURL((url) => url.pathname === "/ask" && url.search === "");

      // The checked answer replaces the pieces; the removed sentence is gone.
      const answer = page.getByRole("article", { name: language.answer });
      await expect(answer).toHaveAttribute("aria-busy", "false");
      await expect(answer.getByTestId("answer-label")).toHaveText(language.checked);
      const text = answer.getByTestId("answer-text");
      await expect(text).toContainText(KEPT_SENTENCE);
      await expect(text).not.toContainText(REMOVED_SENTENCE);
      await expect(answer.getByTestId("answer-note")).toHaveText(language.removed);
      // Markup in the answer is text, never HTML.
      await expect(text).toContainText('<img src="/e2e-missing-image.png">');
      await expect(text.locator("img")).toHaveCount(0);

      // [1] links to its source with an accessible name.
      const citation = answer.getByRole("link", { name: language.citation });
      await expect(citation).toHaveText("[1]");
      await expect(citation).toHaveAttribute("href", "#source-1");
      await expect(answer.getByTestId("answer-citation")).toHaveCount(2);

      // The list of sources: file, page and a link to the file page.
      await expect(page.getByRole("heading", { level: 2, name: language.sources })).toBeVisible();
      const cards = page.getByRole("list", { name: language.sources }).getByTestId("answer-source");
      await expect(cards).toHaveCount(2);
      const first = page.locator('[data-testid="answer-source"][data-n="1"]');
      await expect(first.getByTestId("search-hit-page")).toHaveText(language.page14);
      await expect(first.getByTestId("search-location-filename")).toHaveText(FILE_NAME);
      await expect(first.getByTestId("search-location-document")).toHaveAttribute(
        "href",
        `/documents/${String(DOCUMENT_ID)}`,
      );
      await expect(first.getByTestId("search-location-document")).toHaveText(DOCUMENT_TITLE);

      // A click on [1] moves the focus to its card without changing the address.
      await citation.click();
      await expect(first).toBeFocused();
      await expect(page).toHaveURL((url) => url.hash === "");

      await expect(page.getByRole("alert")).toHaveCount(0);
      expect(consoleErrors, "errors in the browser console").toEqual([]);
    });

    test("without evidence: the fixed sentence and no sources", async ({ page }) => {
      const consoleErrors = collectConsoleErrors(page);
      const routes = await routeAnswers(page, AVAILABLE, {
        events: NO_EVIDENCE,
      });
      await page.goto("/ask");
      const form = page.getByRole("form", { name: language.form });
      await form.getByRole("textbox", { name: language.question }).fill("When was the e2e test station painted?");
      await form.getByRole("button", { name: language.button }).click();

      await expect(page.getByTestId("answer-status")).toHaveText(language.done);
      await expect(page.getByTestId("answer-no-evidence")).toContainText(language.noEvidence);
      await expect(page.getByTestId("answer-no-evidence")).not.toContainText("Server text");
      await expect(page.getByTestId("answer-sources")).toHaveCount(0);
      await expect(page.getByTestId("answer-card")).toHaveCount(0);
      await expect(page.getByTestId("answer-citation")).toHaveCount(0);
      // No check of the focus here: the button is disabled while the answer
      // streams, so a click leaves the focus on the page (finding of work
      // order 137); the keyboard path keeps it in the field (see above).
      expect(routes.posts).toHaveLength(1);
      expect(consoleErrors, "errors in the browser console").toEqual([]);
    });

    test("AI off: a calm hint with a link to the search, the form disabled, nothing sent", async ({ page }) => {
      const consoleErrors = collectConsoleErrors(page);
      const routes = await routeAnswers(page, AI_OFF, { events: ANSWERED });
      await page.goto("/ask?q=e2e%20question");
      const form = page.getByRole("form", { name: language.form });
      const notice = page.getByTestId("answer-unavailable");
      await expect(notice).toHaveAttribute("data-availability", "off");
      await expect(notice).toContainText(language.off);
      await expect(notice.getByRole("link", { name: language.toSearch })).toHaveAttribute("href", "/search");
      await expect(form.getByRole("textbox", { name: language.question })).toBeDisabled();
      await expect(form.getByRole("button", { name: language.button })).toBeDisabled();
      // A normal state, not an error.
      await expect(page.getByRole("alert")).toHaveCount(0);
      expect(routes.posts, "no POST with the AI features off").toHaveLength(0);
      expect(consoleErrors, "errors in the browser console").toEqual([]);
    });

    test("AI switched off after the status: 409 ai_disabled shows the same hint", async ({ page }) => {
      const consoleErrors = collectConsoleErrors(page);
      const routes = await routeAnswers(page, AVAILABLE, {
        status: 409,
        json: { detail: "e2e: the AI features are off.", code: "ai_disabled" },
      });
      await page.goto("/ask");
      const form = page.getByRole("form", { name: language.form });
      const question = form.getByRole("textbox", { name: language.question });
      await question.fill("Is the e2e test station on?");
      await form.getByRole("button", { name: language.button }).click();

      const notice = page.getByTestId("answer-unavailable");
      await expect(notice).toHaveAttribute("data-availability", "off");
      await expect(notice).toContainText(language.off);
      await expect(question).toBeDisabled();
      await expect(form.getByRole("button", { name: language.button })).toBeDisabled();
      await expect(page.getByRole("alert")).toHaveCount(0);
      expect(routes.posts).toHaveLength(1);
      // The browser logs the refused request itself; nothing else may be there.
      expect(
        consoleErrors.filter((message) => !message.includes("status of 409")),
        "errors in the browser console",
      ).toEqual([]);
    });

    test("a failure of the model in role=alert, without the raw text", async ({ page }) => {
      const consoleErrors = collectConsoleErrors(page);
      await routeAnswers(page, AVAILABLE, { events: FAILED });
      await page.goto("/ask");
      const form = page.getByRole("form", { name: language.form });
      await form.getByRole("textbox", { name: language.question }).fill("How warm is the e2e test station?");
      await form.getByRole("button", { name: language.button }).click();

      const alert = page.getByRole("alert");
      await expect(alert).toHaveCount(1);
      await expect(alert).toContainText(language.modelUnavailable);
      await expect(alert.getByTestId("answer-error-code")).toHaveText("Code: model_unavailable");
      await expect(alert).not.toContainText(RAW_DETAIL);
      await expect(page.locator("body")).not.toContainText(RAW_DETAIL);
      await expect(page.getByTestId("answer-card")).toHaveCount(0);
      // The form stays usable for the next question.
      await expect(form.getByRole("button", { name: language.button })).toBeEnabled();
      expect(consoleErrors, "errors in the browser console").toEqual([]);
    });

    test("limited to a device or a plant: chip, request and lifting the limit", async ({ page }) => {
      test.setTimeout(120_000);
      const consoleErrors = collectConsoleErrors(page);
      const routes = await routeAnswers(page, AVAILABLE, {
        events: NO_EVIDENCE,
      });
      await page.goto("/ask");
      const device = await newDevice(page, language.ip);
      const form = page.getByRole("form", { name: language.form });
      const question = form.getByRole("textbox", { name: language.question });
      const chip = page.getByTestId("answer-scope");

      // The device page leads to the answer page limited to the device.
      await page.goto(`/devices/${String(device.id)}`);
      const askDevice = page.getByTestId("device-ask");
      await expect(askDevice).toHaveAccessibleName(`${language.askDevice}: ${device.name}`);
      await askDevice.click();
      await expect(page).toHaveURL(
        (url) => url.pathname === "/ask" && url.searchParams.get("device") === String(device.id),
      );

      await expect(chip).toContainText(language.limitedDevice);
      await expect(page.getByTestId("answer-scope-name")).toHaveText(`${device.name} (${device.key})`);
      await expect(page.getByTestId("answer-device")).toHaveValue(String(device.id));
      await question.fill("Which e2e voltage applies here?");
      await form.getByRole("button", { name: language.button }).click();
      await expect(page.getByTestId("answer-status")).toHaveText(language.done);
      expect(requestBody(routes.posts.at(-1))).toEqual({
        question: "Which e2e voltage applies here?",
        device: [device.id],
      });

      await page.getByTestId("answer-scope-reset").click();
      await expect(chip).toHaveCount(0);
      await expect(page).toHaveURL((url) => url.pathname === "/ask" && !url.searchParams.has("device"));
      await expect(page.getByTestId("answer-device")).toHaveValue("");

      // The same with a plant.
      await page.goto(`/ask?plant=${String(device.plantId)}`);
      await expect(chip).toContainText(language.limitedPlant);
      await expect(page.getByTestId("answer-scope-name")).toHaveText(device.plantName);
      await expect(page.getByTestId("answer-plant")).toHaveValue(String(device.plantId));
      await question.fill("Which e2e plant voltage applies?");
      await form.getByRole("button", { name: language.button }).click();
      await expect(page.getByTestId("answer-status")).toHaveText(language.done);
      expect(requestBody(routes.posts.at(-1))).toEqual({
        question: "Which e2e plant voltage applies?",
        plant: [device.plantId],
      });

      await chip.getByRole("button", { name: language.reset }).click();
      await expect(chip).toHaveCount(0);
      await expect(page).toHaveURL((url) => url.pathname === "/ask" && !url.searchParams.has("plant"));
      expect(routes.posts).toHaveLength(2);
      expect(consoleErrors, "errors in the browser console").toEqual([]);
    });
  });
}
