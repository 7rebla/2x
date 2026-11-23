import type { Locator, Page } from "@playwright/test";

import { expect, test } from "./fixtures";

// Acceptance of M3 (docs/ROADMAP.md) in the browser, local part: question and
// answer, the sources shown, the limit to a device, and the control question
// without an invented answer, with the real chat model and the manuals of the
// test factory. The judgement of all test questions is
// backend/tests/acceptance/test_m3.py (evaluate_answers); the CI part of the
// page is answer.spec.ts.
//
// Runs only with TWOX_M3_LOCAL=1, in the test environment with the ingested
// manuals, the AI features on and the chat model configured (acceptance run,
// work order 138). It creates no data (no device, no upload): it only asks.
// Manuals are recognised by the checksum of testfactory/manifest.yaml, devices
// by their key in testfactory/layout/devices.csv. The questions are asked in
// the project's own words. Annotations hold the state, the number of sources
// and the time of each step, never a question or an answer (D7).
test.use({ locale: "de-DE" });

// The web UI has no Node types (@types/node is not a dependency): the spec
// reads environment variables.
declare const process: {
  readonly env: Readonly<Record<string, string | undefined>>;
};

const LOCAL = process.env.TWOX_M3_LOCAL === "1";

/** Longest wait for one answer: TWOX_ANSWER_TOTAL_TIMEOUT (180 s) and a margin. */
const ANSWER_TIMEOUT = 240_000;

/** A manual of the test factory: checksum from testfactory/manifest.yaml. */
interface Manual {
  readonly manifestId: string;
  readonly sha256: string;
}

const UR5E_USER_MANUAL_DE: Manual = {
  manifestId: "ur5e-user-manual-de",
  sha256: "70940ab1cd824a2af60e75d1f2437f45fe479f2394057e267fecfe8448266102",
};
/** Every manual of the UR5e in the manifest (ur5e-*). */
const UR5E_MANUALS: readonly Manual[] = [
  UR5E_USER_MANUAL_DE,
  {
    manifestId: "ur5e-software-handbook-en",
    sha256: "06488da8a8bc2be51e796d2e62e2f90ad4b00412acbac016c232780b1d0ee3ba",
  },
  {
    manifestId: "ur5e-script-directory-en",
    sha256: "8e730b42b82a4ce3100cd06a9c35fb87bafaded4058942e43526ea4a53d6f9fa",
  },
  {
    manifestId: "ur5e-service-manual-en",
    sha256: "c969dbbfb621e8f7cae705645ab628328e2168fc23082ccdb9fbb8f30570c26d",
  },
];

/** Devices of testfactory/layout/devices.csv (lines 5 and 14). */
const UR5E_DEVICE_KEY = "ur5e";
const OTHER_DEVICE_KEY = "drill-plc";

/** Test question 9 (payload of the UR5e), asked in the project's own words. */
const PAYLOAD_QUESTION = "Wie schwer darf eine Last höchstens sein, die der UR5e bewegen soll?";
/** Expected places of question 9: PDF pages of the German user manual (questions.yaml). */
const PAYLOAD_PAGES: readonly number[] = [16, 101, 102];
/** Test question 11, the control question, in the project's own words and without its note. */
const CONTROL_QUESTION = "An welchem Tag fand die letzte Wartung an der Frässtation statt?";

const NO_EVIDENCE_TEXT = "Dazu finde ich nichts in den Unterlagen.";
const DONE = "Fertig";

interface ApiAnswer {
  readonly status: number;
  readonly body: unknown;
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

interface Device {
  readonly id: number;
  readonly key: string;
}

/** The id of the device with `key`; fails if it is not there. */
async function deviceId(page: Page, key: string): Promise<number> {
  const devices = await apiGet<readonly Device[]>(page, "/api/v1/devices/");
  const device = devices.find((item) => item.key === key);
  if (device === undefined) {
    throw new Error(`device ${key} (testfactory/layout/devices.csv) is not in the database`);
  }
  return device.id;
}

/** The ids of the files whose newest version has the checksum of one of `manuals`. */
async function documentsOf(page: Page, manuals: readonly Manual[]): Promise<Set<number>> {
  const checksums = new Set(manuals.map((manual) => manual.sha256));
  const devices = await apiGet<readonly Device[]>(page, "/api/v1/devices/");
  const ids = new Set<number>();
  for (const device of devices) {
    const documents = await apiGet<readonly { id: number; latest_version: { sha256: string } | null }[]>(
      page,
      `/api/v1/devices/${String(device.id)}/documents/`,
    );
    for (const document of documents) {
      if (document.latest_version !== null && checksums.has(document.latest_version.sha256)) {
        ids.add(document.id);
      }
    }
  }
  return ids;
}

/** What the page showed for one question. */
interface Shown {
  /** "answered", "contradiction", "no_evidence" or "error". */
  readonly state: string;
  /** The cards of the sources the answer cites. */
  readonly cards: Locator;
  readonly sources: number;
}

/** Asks `question` on the answer page at `path` and waits until the answer is complete. */
async function ask(page: Page, path: string, name: string, question: string): Promise<Shown> {
  await page.goto(path);
  const form = page.getByRole("form", { name: "Frage stellen" });
  const field = form.getByRole("textbox", { name: "Frage" });
  await field.fill(question);
  const started = Date.now();
  await form.getByRole("button", { name: "Fragen" }).click();
  const status = page.getByTestId("answer-status");
  await expect(status.filter({ hasText: DONE }).or(page.getByRole("alert"))).toBeVisible({ timeout: ANSWER_TIMEOUT });
  const seconds = (Date.now() - started) / 1000;

  let state: string;
  if ((await page.getByRole("alert").count()) > 0) {
    state = "error";
  } else if ((await page.getByTestId("answer-no-evidence").count()) > 0) {
    state = "no_evidence";
  } else if ((await page.getByTestId("answer-contradiction").count()) > 0) {
    state = "contradiction";
  } else {
    state = "answered";
  }
  const cards = page.getByTestId("answer-sources").getByTestId("answer-source");
  const sources = await cards.count();
  test.info().annotations.push({
    type: "step",
    description: `${name}: state ${state}, ${String(sources)} sources, ${seconds.toFixed(1)} s`,
  });
  return { state, cards, sources };
}

/** The file id each source card links to (its first place). */
async function cardDocuments(cards: Locator): Promise<number[]> {
  const hrefs = await cards.evaluateAll((items) =>
    items.map((item) => item.querySelector('[data-testid="search-location-document"]')?.getAttribute("href") ?? ""),
  );
  return hrefs.map((href) => Number(/^\/documents\/(\d+)$/.exec(href)?.[1] ?? "0"));
}

/** The PDF pages a card names ("S. 16", "S. 101–102"); empty without a page. */
async function cardPages(card: Locator): Promise<number[]> {
  const label = card.getByTestId("search-hit-page");
  if ((await label.count()) === 0) {
    return [];
  }
  const numbers = ((await label.textContent()) ?? "").match(/\d+/g) ?? [];
  const [start, end] = numbers.map(Number);
  if (start === undefined) {
    return [];
  }
  const last = end ?? start;
  return Array.from({ length: Math.max(0, last - start) + 1 }, (_, index) => start + index);
}

/** Whether the answer text holds the key fact "5 kg" ("5kg" counts the same, as in work order 123). */
async function holdsPayload(page: Page): Promise<boolean> {
  const text = (await page.getByTestId("answer-text").textContent()) ?? "";
  // Unified: every kind of space as one plain space, lower case.
  const unified = text.replace(/[\s  ]+/g, " ").toLowerCase();
  return /(?<![\d.,])5 ?kg(?![a-z])/.test(unified);
}

test("M3 acceptance, local part: answers with sources, the limit to a device and the control question", async ({
  page,
}) => {
  test.skip(
    !LOCAL,
    "Local part: runs only with TWOX_M3_LOCAL=1 in the test environment with the manuals and the chat model (acceptance run, work order 138).",
  );
  test.setTimeout(600_000);
  const consoleErrors = collectConsoleErrors(page);

  // 0. Answers must be available; otherwise fail at once instead of waiting.
  await page.goto("/ask");
  const availability = await apiGet<{
    enabled: boolean;
    chat_model_configured: boolean;
    available: boolean;
  }>(page, "/api/v1/answers/status/");
  if (!availability.available) {
    throw new Error(
      `answers not available (AI off or no chat model): enabled=${String(availability.enabled)}, chat_model_configured=${String(availability.chat_model_configured)}`,
    );
  }
  const userManual = await documentsOf(page, [UR5E_USER_MANUAL_DE]);
  const ur5eManuals = await documentsOf(page, UR5E_MANUALS);
  expect(userManual.size, `${UR5E_USER_MANUAL_DE.manifestId} is uploaded`).toBeGreaterThan(0);
  const ur5e = await deviceId(page, UR5E_DEVICE_KEY);
  const otherDevice = await deviceId(page, OTHER_DEVICE_KEY);

  // 1. Question 9 without a limit: answered, the key fact, and a cited source
  // in the German user manual on an expected page, shown with page and link.
  await test.step("question 9 with its sources", async () => {
    const shown = await ask(page, "/ask", "question 9", PAYLOAD_QUESTION);
    expect(shown.state, "state of the answer").toBe("answered");
    await expect(page.getByRole("article", { name: "Antwort" })).toHaveAttribute("aria-busy", "false");
    expect(await holdsPayload(page), "the answer holds the key fact 5 kg").toBe(true);
    const documents = await cardDocuments(shown.cards);
    const expected: number[] = [];
    for (const [index, document] of documents.entries()) {
      const pages = await cardPages(shown.cards.nth(index));
      if (userManual.has(document) && pages.some((number) => PAYLOAD_PAGES.includes(number))) {
        expected.push(index);
      }
    }
    expect(
      expected.length,
      `a source in ${UR5E_USER_MANUAL_DE.manifestId} on page ${PAYLOAD_PAGES.join(", ")}`,
    ).toBeGreaterThan(0);
    const card = shown.cards.nth(expected[0] ?? 0);
    await expect(card.getByTestId("search-hit-page")).toHaveText(/^S\. \d+/);
    await expect(card.getByTestId("search-location-document")).toHaveAttribute("href", /^\/documents\/\d+$/);
  });

  // 2. The same question limited to the UR5e: a source in a manual of the UR5e.
  // Limited to another device (drill-plc): no source of a UR5e manual at all;
  // "no evidence" or sources of that device are both right.
  await test.step("question 9 limited to the UR5e and to another device", async () => {
    const limited = await ask(page, `/ask?device=${String(ur5e)}`, "question 9, device ur5e", PAYLOAD_QUESTION);
    await expect(page.getByTestId("answer-scope")).toBeVisible();
    expect(limited.state, "state of the answer").not.toBe("error");
    const documents = await cardDocuments(limited.cards);
    expect(
      documents.some((document) => ur5eManuals.has(document)),
      "a source in a manual of the UR5e",
    ).toBe(true);

    const other = await ask(
      page,
      `/ask?device=${String(otherDevice)}`,
      "question 9, device drill-plc",
      PAYLOAD_QUESTION,
    );
    await expect(page.getByTestId("answer-scope")).toBeVisible();
    expect(["answered", "contradiction", "no_evidence"], "state of the answer").toContain(other.state);
    const foreign = (await cardDocuments(other.cards)).filter((document) => ur5eManuals.has(document));
    expect(foreign, "no source from a manual of the UR5e when limited to drill-plc").toEqual([]);
  });

  // 3. The control question: the fixed sentence, no sources, no [n].
  await test.step("control question 11", async () => {
    const shown = await ask(page, "/ask", "question 11", CONTROL_QUESTION);
    expect(shown.state, "state of the answer").toBe("no_evidence");
    await expect(page.getByTestId("answer-no-evidence")).toContainText(NO_EVIDENCE_TEXT);
    expect(shown.sources).toBe(0);
    await expect(page.getByTestId("answer-sources")).toHaveCount(0);
    await expect(page.getByTestId("answer-citation")).toHaveCount(0);
    await expect(page.getByTestId("answer-card")).toHaveCount(0);
  });

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});
