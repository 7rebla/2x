import { expect, test, testIp, testName, uniqueSuffix } from "./fixtures";

declare const process: { readonly env: Readonly<Record<string, string | undefined>> };

// The shared sign-in step and the test data helpers of fixtures.ts.

test("the page starts signed in with the test account and its role", async ({ page }) => {
  const answer = await page.evaluate(async () => {
    const result = await fetch("/api/v1/me/");
    return { status: result.status, body: (await result.json()) as unknown };
  });

  expect(answer.status).toBe(200);
  expect(answer.body).toEqual({
    username: process.env.TWOX_E2E_USERNAME,
    role: "manage",
    is_superuser: false,
  });
});

test("test names follow e2e-<kind>-<suffix> and never repeat", () => {
  const first = testName("site");
  const second = testName("site");

  expect(first).toMatch(/^e2e-site-[a-z0-9]+-\d+$/);
  expect(second).not.toBe(first);
  expect(uniqueSuffix()).not.toBe(uniqueSuffix());
  expect(() => testName("Plant 1")).toThrow();
});

test("test addresses come from 192.0.2.0/24 only", () => {
  expect(testIp(1)).toBe("192.0.2.1");
  expect(testIp(254)).toBe("192.0.2.254");
  for (const invalid of [0, 255, 1.5, -1]) {
    expect(() => testIp(invalid)).toThrow();
  }
});
