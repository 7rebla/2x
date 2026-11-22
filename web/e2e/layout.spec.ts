import type { Locator, Page } from "@playwright/test";

import { expect, test } from "./fixtures";

// One page grid for header and content (work order 080, E-65 point 1),
// measured in the browser at the widths of the UI analysis. Read-only: the
// test changes nothing in the database.
test.use({ locale: "en-US" });

interface Box {
  readonly x: number;
  readonly y: number;
  readonly width: number;
  readonly height: number;
}

async function boxOf(locator: Locator): Promise<Box> {
  const box = await locator.boundingBox();
  if (box === null) {
    throw new Error("element has no box");
  }
  return box;
}

/** Left edge of the content box of an element (its box without the left padding). */
async function contentLeft(locator: Locator): Promise<number> {
  return locator.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    return rect.left + Number.parseFloat(getComputedStyle(element).paddingLeft);
  });
}

/** Whether the page is wider than the window (a horizontal scroll bar). */
async function overflowsSideways(page: Page): Promise<boolean> {
  return page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
}

/** Zoom of the map, read from the transform of React Flow's viewport. */
async function mapZoom(page: Page): Promise<number> {
  const transform = await page.locator(".react-flow__viewport").evaluate((element) => getComputedStyle(element).transform);
  // matrix(a, b, c, d, e, f): a is the scale.
  const scale = /^matrix\(([^,]+),/.exec(transform)?.[1];
  return scale === undefined ? 1 : Number(scale);
}

for (const width of [375, 1024, 1600]) {
  test(`brand mark and page heading start on the same line at ${String(width)} px`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    const heading = page.getByRole("heading", { level: 1, name: "Structure" });
    await expect(heading).toBeVisible();

    const header = page.getByTestId("header-grid");
    const main = page.getByRole("main");
    const [headerBox, mainBox] = await Promise.all([boxOf(header), boxOf(main)]);
    // Same grid: same left edge and width (at most 1280 px).
    expect(headerBox.x).toBe(mainBox.x);
    expect(headerBox.width).toBe(mainBox.width);
    expect(mainBox.width).toBeLessThanOrEqual(1280);

    const brand = await boxOf(page.getByRole("banner").getByRole("link", { name: "2x" }));
    const title = await boxOf(heading);
    expect(Math.abs(brand.x - title.x)).toBeLessThanOrEqual(0.5);
    expect(title.x).toBe(await contentLeft(main));
    testInfo.annotations.push({
      type: "left edges",
      description: `${String(width)} px: brand mark ${String(brand.x)} px, heading ${String(title.x)} px, grid ${String(mainBox.width)} px`,
    });

    if (width === 1600) {
      // Centred grid of 1280 px plus 16 px padding: (1600 - 1280) / 2 + 16 = 176 px without a scroll bar.
      const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);
      expect(title.x).toBe((clientWidth - 1280) / 2 + 16);
      // The introduction keeps a readable line length inside the wider grid.
      const intro = await boxOf(page.getByRole("main").locator("section > p").first());
      expect(intro.width).toBeLessThan(mainBox.width - 32);
      expect(intro.width).toBeLessThanOrEqual(720);
    }
  });
}

test("the self-test sets its cards in three, two or one columns", async ({ page }) => {
  const cards = ["database-check", "worker-check", "ai-check"].map((id) => page.getByTestId(id));
  const tops = async (): Promise<number[]> => Promise.all(cards.map(async (card) => (await boxOf(card)).y));

  await page.setViewportSize({ width: 1600, height: 900 });
  await page.goto("/selftest");
  await expect(page.getByTestId("worker-status")).toHaveText("OK");
  const [first, second, third] = await tops();
  expect([second, third]).toEqual([first, first]);
  // Heading and button stay in their narrow column (36rem).
  expect((await boxOf(page.getByTestId("selftest-head"))).width).toBeLessThanOrEqual(576);
  expect(await overflowsSideways(page)).toBe(false);

  await page.setViewportSize({ width: 1024, height: 900 });
  await expect.poll(tops).toEqual([first, first, expect.any(Number)]);
  const [top1024, , third1024] = await tops();
  expect(third1024).toBeGreaterThan(top1024 ?? 0);

  await page.setViewportSize({ width: 375, height: 812 });
  await expect.poll(async () => {
    const [a, b, c] = await tops();
    return (a ?? 0) < (b ?? 0) && (b ?? 0) < (c ?? 0);
  }).toBe(true);
  expect(await overflowsSideways(page)).toBe(false);
});

test("the settings stay a narrow column at the left edge of the grid", async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 900 });
  await page.goto("/settings");
  const settings = page.getByTestId("settings-page");
  await expect(settings).toBeVisible();
  const box = await boxOf(settings);
  expect(box.width).toBe(672);
  expect(box.x).toBe(await contentLeft(page.getByRole("main")));

  await page.setViewportSize({ width: 375, height: 812 });
  expect(await overflowsSideways(page)).toBe(false);
});

test("the map takes the width of the grid and the rest of the window, with its legend in the corner", async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 900 });
  await page.goto("/map");
  const canvas = page.getByRole("region", { name: "Map of sites, areas, plants, devices and networks" });
  await expect(canvas).toBeVisible();
  const main = page.getByRole("main");
  const mainBox = await boxOf(main);

  // The whole content width of the grid (1280 px minus 2 × 16 px padding).
  await expect.poll(async () => (await boxOf(canvas)).width).toBe(mainBox.width - 32);
  // Down to the bottom of the window, minus the padding of the page content.
  await expect.poll(async () => {
    const box = await boxOf(canvas);
    return Math.round(box.y + box.height);
  }).toBe(900 - 32);
  expect(await page.evaluate(() => document.documentElement.scrollHeight)).toBeLessThanOrEqual(900);

  // The legend stands in the top right corner of the map, not above it.
  const legend = canvas.getByRole("note", { name: "Legend" });
  await expect(legend).toBeVisible();
  const [legendBox, canvasBox] = await Promise.all([boxOf(legend), boxOf(canvas)]);
  expect(legendBox.y - canvasBox.y).toBeLessThan(32);
  expect(canvasBox.x + canvasBox.width - (legendBox.x + legendBox.width)).toBeLessThan(32);
  await expect(page.getByRole("main").locator("section > p", { hasText: "Dashed line" })).toHaveCount(0);

  // Fitting the view never zooms out below 0.6 (nor in beyond 1.25).
  await expect.poll(() => mapZoom(page)).toBeGreaterThanOrEqual(0.6);
  expect(await mapZoom(page)).toBeLessThanOrEqual(1.25);
  await canvas.getByRole("button", { name: "Zoom out" }).click();
  await canvas.getByRole("button", { name: "Zoom out" }).click();
  await canvas.getByRole("button", { name: "Zoom out" }).click();
  await page.getByRole("button", { name: "Fit view" }).click();
  await expect.poll(() => mapZoom(page)).toBeGreaterThanOrEqual(0.6);
  expect(await mapZoom(page)).toBeLessThanOrEqual(1.25);

  // A small window: the map keeps a least height and the page does not scroll sideways.
  await page.setViewportSize({ width: 375, height: 812 });
  await expect.poll(async () => (await boxOf(canvas)).height).toBeGreaterThanOrEqual(448);
  expect(await overflowsSideways(page)).toBe(false);
  // There the legend shows only the line and its meaning (two short lines), the details stay for screen readers.
  await expect.poll(async () => (await boxOf(legend)).height).toBeLessThan(64);
  await expect(legend).toContainText("IPv4 by /24");
});
