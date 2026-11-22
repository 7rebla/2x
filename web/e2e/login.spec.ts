import type { Page } from "@playwright/test";

import { expect, test, testName } from "./fixtures";

declare const process: { readonly env: Readonly<Record<string, string | undefined>> };

// Sign-in page, sign-out and the redirect to the sign-in page, in a browser
// without a session. These tests sign in through the page themselves and
// never touch the shared session of the other specs (fixtures.ts).
test.use({ locale: "en-US", storageState: { cookies: [], origins: [] } });

function testAccount(): { username: string; password: string } {
  const username = process.env.TWOX_E2E_USERNAME;
  const password = process.env.TWOX_E2E_PASSWORD;
  if (username === undefined || username === "" || password === undefined || password === "") {
    throw new Error('TWOX_E2E_USERNAME and TWOX_E2E_PASSWORD must be set; see README, "Browser test"');
  }
  return { username, password };
}

async function signInThroughThePage(page: Page, username: string, password: string): Promise<void> {
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

test("a wrong password shows an error and no session", async ({ page }) => {
  // An account that does not exist: the failed attempt counts against this
  // name only, so the shared test account can never be locked (5 failures
  // per 5 minutes and account).
  await page.goto("/login");
  await signInThroughThePage(page, testName("nobody"), "dev-only-wrong-password");

  await expect(page.getByTestId("login-error")).toHaveText("Username or password is wrong.");
  await expect(page.getByTestId("login-card").getByTestId("login-error")).toBeVisible();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByTestId("user-name")).toHaveCount(0);
  expect((await page.context().cookies()).some((cookie) => cookie.name === "sessionid")).toBe(false);
});

// The sign-in page is a centred card with the brand above it (work order 086,
// E-65 point 7); fields and button are equally high and equally wide.
for (const width of [375, 1024, 1600]) {
  test(`the sign-in card is centred at ${String(width)} px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/login");
    const card = page.getByTestId("login-card");
    await expect(card).toBeVisible();

    const [cardBox, mainBox, lockupBox] = await Promise.all([
      card.boundingBox(),
      page.getByRole("main").boundingBox(),
      page.getByTestId("brand-lockup").boundingBox(),
    ]);
    if (cardBox === null || mainBox === null || lockupBox === null) {
      throw new Error("card, main or brand without a box");
    }
    // At most max-w-sm (384 px), centred in the page grid.
    expect(cardBox.width).toBeLessThanOrEqual(384);
    expect(Math.abs(cardBox.x + cardBox.width / 2 - (mainBox.x + mainBox.width / 2))).toBeLessThanOrEqual(1);
    // The brand stands centred above the card.
    expect(lockupBox.y + lockupBox.height).toBeLessThanOrEqual(cardBox.y);
    expect(Math.abs(lockupBox.x + lockupBox.width / 2 - (cardBox.x + cardBox.width / 2))).toBeLessThanOrEqual(1);

    const boxes = await Promise.all(
      [page.getByLabel("Username"), page.getByLabel("Password"), page.getByRole("button", { name: "Sign in" })].map(
        (control) => control.boundingBox(),
      ),
    );
    for (const box of boxes) {
      expect(box?.height).toBe(36);
      expect(box?.width).toBe(boxes[0]?.width);
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(
      false,
    );
  });
}

test("signing in through the page shows the user name and role", async ({ page }) => {
  const { username, password } = testAccount();

  await page.goto("/login");
  await signInThroughThePage(page, username, password);

  await expect(page.getByTestId("user-name")).toHaveText(username);
  await expect(page.getByTestId("user-role")).toHaveText("Manage");
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("navigation", { name: "Main navigation" })).toBeVisible();
});

test("signing out leads to /login and ends the session", async ({ page }) => {
  const { username, password } = testAccount();
  await page.goto("/login");
  await signInThroughThePage(page, username, password);
  await expect(page.getByTestId("user-name")).toHaveText(username);

  // Sign-out sits in the user menu of the header.
  await page.getByTestId("user-menu-button").click();
  await page.getByRole("button", { name: "Sign out" }).click();

  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByTestId("login-form")).toBeVisible();
  await expect(page.getByTestId("user-name")).toHaveCount(0);
  // The session is gone on the server too: a page leads to the sign-in page again.
  await page.goto("/selftest");
  await expect(page).toHaveURL(/\/login\?next=%2Fselftest$/);
});

test("/selftest without a session leads to /login and back after signing in", async ({ page }) => {
  const { username, password } = testAccount();

  await page.goto("/selftest");

  await expect(page).toHaveURL(/\/login\?next=%2Fselftest$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Sign in");
  await expect(page.getByRole("navigation")).toHaveCount(0);

  await signInThroughThePage(page, username, password);

  await expect(page).toHaveURL(/\/selftest$/);
  await expect(page.getByTestId("worker-result")).toHaveText("pong");
  await expect(page.getByTestId("user-name")).toHaveText(username);
});
