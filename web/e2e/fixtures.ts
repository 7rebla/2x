import { test as base, type Page } from "@playwright/test";

// Shared steps and test data helpers of the browser tests. Every spec imports
// `test` and `expect` from here, so each test starts signed in with the test
// account (TWOX_E2E_USERNAME, TWOX_E2E_PASSWORD; README, "Browser test").

// The web UI has no Node types (@types/node is not a dependency); this file
// only reads environment variables.
declare const process: { readonly env: Readonly<Record<string, string | undefined>> };

const SIGN_IN_PATH = "/_allauth/browser/v1/auth/login";
const CSRF_COOKIE = "csrftoken";

interface SignInAnswer {
  readonly status: number;
  readonly body: string;
}

function requiredVariable(name: string): string {
  const value = process.env[name];
  if (value === undefined || value === "") {
    throw new Error(`${name} is not set; see README, "Browser test"`);
  }
  return value;
}

/**
 * Signs in with the test account through the sign-in API of django-allauth.
 *
 * The request runs inside the page (fetch at the same origin), not through
 * Playwright's own request client: only Chromium maps the host name of the
 * API (playwright.config.ts), and the session cookie lands directly in the
 * browser context of the page.
 */
export async function signIn(page: Page): Promise<void> {
  const username = requiredVariable("TWOX_E2E_USERNAME");
  const password = requiredVariable("TWOX_E2E_PASSWORD");

  // Django sets the CSRF cookie with the page of the web UI.
  const response = await page.goto("/");
  if (response === null || !response.ok()) {
    throw new Error(`sign-in: / answered ${String(response?.status())}`);
  }
  const cookies = await page.context().cookies();
  const token = cookies.find((cookie) => cookie.name === CSRF_COOKIE)?.value;
  if (token === undefined) {
    throw new Error(`sign-in: no ${CSRF_COOKIE} cookie after opening /`);
  }

  const answer = await page.evaluate(
    async ({ path, csrfToken, credentials }): Promise<SignInAnswer> => {
      const result = await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
        body: JSON.stringify(credentials),
      });
      return { status: result.status, body: await result.text() };
    },
    { path: SIGN_IN_PATH, csrfToken: token, credentials: { username, password } },
  );
  if (answer.status !== 200) {
    // allauth answers a lockout after failed attempts with 400 and the code
    // too_many_login_attempts. The answer never holds the password.
    throw new Error(`sign-in as ${username} failed with ${String(answer.status)}: ${answer.body}`);
  }
  const sessionCookie = (await page.context().cookies()).find((cookie) => cookie.name === "sessionid");
  if (sessionCookie === undefined) {
    throw new Error("sign-in: no session cookie in the browser context");
  }
}

// Every test gets a page that is already signed in.
export const test = base.extend<{ page: Page }>({
  page: async ({ page }, provide) => {
    await signIn(page);
    await provide(page);
  },
});

export { expect } from "@playwright/test";

// Test data (CLAUDE.md, guideline 9): nothing that looks like a real plant.

const runId = `${Date.now().toString(36)}${crypto.randomUUID().slice(0, 8)}`;
let counter = 0;

/** A suffix unique per call and per run: run id plus a counter. */
export function uniqueSuffix(): string {
  counter += 1;
  return `${runId}-${String(counter)}`;
}

/** A name following the pattern e2e-<kind>-<suffix>, for example e2e-site-…. */
export function testName(kind: string): string {
  if (!/^[a-z][a-z0-9]*$/.test(kind)) {
    throw new Error(`testName: kind must be lower-case letters and digits, got ${JSON.stringify(kind)}`);
  }
  return `e2e-${kind}-${uniqueSuffix()}`;
}

/** Address n (1 to 254) from the documentation range 192.0.2.0/24 (RFC 5737). */
export function testIp(n: number): string {
  if (!Number.isInteger(n) || n < 1 || n > 254) {
    throw new Error(`testIp: n must be an integer from 1 to 254, got ${String(n)}`);
  }
  return `192.0.2.${String(n)}`;
}
