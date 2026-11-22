import type { Page } from "@playwright/test";

import { expect, test } from "./fixtures";

// Answer page as served by Django (work order 132). The CI has no chat model
// (TWOX_CHAT_MODEL is empty), so the real status endpoint reports answers as
// not available: the page shows the calm hint with a link to the search and a
// disabled form. Roles, accessible names, the status region and the keyboard
// are checked here, in German and English (no axe package, see work order 132).
// The full flow with a recorded stream is work order 137 (answer.spec.ts).

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

const LANGUAGES = [
  {
    locale: "en-US",
    heading: "Ask",
    title: "Ask – 2x",
    form: "Ask a question",
    question: "Question",
    button: "Ask",
    unavailable: "Answers are not available at the moment.",
    toSearch: "Go to the search",
    searchHeading: "Search",
  },
  {
    locale: "de-DE",
    heading: "Auskunft",
    title: "Auskunft – 2x",
    form: "Frage stellen",
    question: "Frage",
    button: "Fragen",
    unavailable: "Auskunft derzeit nicht verfügbar.",
    toSearch: "Zur Suche",
    searchHeading: "Suche",
  },
] as const;

for (const language of LANGUAGES) {
  test.describe(`answer page (${language.locale})`, () => {
    test.use({ locale: language.locale });

    test("without a chat model: hint, link to the search, disabled form, keyboard", async ({ page }) => {
      const consoleErrors = collectConsoleErrors(page);
      const response = await page.goto("/ask?q=Test%20question");
      expect(response?.status()).toBe(200);

      await expect(page.getByRole("heading", { level: 1 })).toHaveText(language.heading);
      await expect(page).toHaveTitle(language.title);

      const form = page.getByRole("form", { name: language.form });
      await expect(form).toBeVisible();
      const question = form.getByRole("textbox", { name: language.question });
      // ?q= only fills the field; nothing is sent.
      await expect(question).toHaveValue("Test question");

      const notice = page.getByTestId("answer-unavailable");
      await expect(notice).toContainText(language.unavailable);
      await expect(question).toBeDisabled();
      await expect(form.getByRole("button", { name: language.button })).toBeDisabled();
      // A calm hint, no error.
      await expect(page.getByRole("alert")).toHaveCount(0);
      await expect(page.getByTestId("answer-status")).toHaveAttribute("role", "status");

      // The keyboard reaches the link to the search; the disabled field and button are skipped.
      const toSearch = notice.getByRole("link", { name: language.toSearch });
      await toSearch.focus();
      await expect(toSearch).toBeFocused();
      await page.keyboard.press("Tab");
      await expect(question).not.toBeFocused();
      await page.keyboard.press("Shift+Tab");
      await expect(toSearch).toBeFocused();
      await page.keyboard.press("Enter");
      await expect(page).toHaveURL(/\/search$/);
      await expect(page.getByRole("heading", { level: 1 })).toHaveText(language.searchHeading);

      expect(consoleErrors, "errors in the browser console").toEqual([]);
    });
  });
}

test.describe("answer page at 375 px", () => {
  test.use({ locale: "en-US", viewport: { width: 375, height: 812 } });

  test("fits the window without a horizontal scroll bar", async ({ page }) => {
    await page.goto("/ask");
    await expect(page.getByTestId("answer-unavailable")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  });
});
