import type { Locator, Page } from "@playwright/test";

import { expect, test, testIp, testName } from "./fixtures";

// Layout and folding of the structure tree (work order 083): actions as icon
// buttons on the right of a row, devices in fixed columns, areas and plants
// foldable with the choice kept in the browser. Every test creates its own
// data through the API (names e2e-<kind>-<suffix>, addresses from 192.0.2.0/24).
test.use({ locale: "en-US" });

interface Created {
  readonly siteName: string;
  readonly areaName: string;
  readonly plantName: string;
  readonly devices: readonly { readonly key: string; readonly name: string; readonly ip: string }[];
}

/** Creates an item through the API from inside the page (same session, CSRF token from the cookie). */
async function create(page: Page, path: string, body: Record<string, unknown>): Promise<{ id: number }> {
  const token = (await page.context().cookies()).find((cookie) => cookie.name === "csrftoken")?.value;
  if (token === undefined) {
    throw new Error("no csrftoken cookie");
  }
  return page.evaluate(
    async ({ url, payload, csrfToken }): Promise<{ id: number }> => {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
        body: JSON.stringify(payload),
      });
      if (response.status !== 201) {
        throw new Error(`POST ${url} answered ${String(response.status)}: ${await response.text()}`);
      }
      return (await response.json()) as { id: number };
    },
    { url: path, payload: body, csrfToken: token },
  );
}

/** A site with one area, one plant and two devices of different classes and key lengths. */
async function createPlant(page: Page): Promise<Created> {
  await page.goto("/");
  const siteName = testName("site");
  const areaName = testName("area");
  const plantName = testName("plant");
  const site = await create(page, "/api/v1/sites/", { name: siteName });
  const area = await create(page, "/api/v1/areas/", { site: site.id, name: areaName });
  const plant = await create(page, "/api/v1/plants/", { area: area.id, key: testName("plant"), name: plantName });
  const base = 1 + Math.floor(Math.random() * 250);
  const devices = [
    // Short kind "d": the name column of the device grid is what is left after the key column, which
    // grows with the longest key. With "device" the name stood within a few pixels of wrapping to a
    // second line for some random suffixes (16 of 20000 at 1024 px, 0 of 20000 with "d").
    { key: testName("d"), name: testName("d"), ip: testIp(base), deviceClass: "plc" },
    { key: `${testName("d")}-x`, name: testName("d"), ip: testIp(base + 1), deviceClass: "controller" },
  ];
  for (const device of devices) {
    await create(page, "/api/v1/devices/", {
      plant: plant.id,
      key: device.key,
      name: device.name,
      device_class: device.deviceClass,
      manufacturer: "",
      model: "",
      software_version: "",
      ip_address: device.ip,
      address_source: "",
      protocols: "",
      notes: "",
    });
  }
  await page.reload();
  return { siteName, areaName, plantName, devices };
}

function item(page: Page, kind: "site" | "area" | "plant", name: string): Locator {
  return page
    .getByTestId(`${kind}-item`)
    .filter({ has: page.getByTestId(`${kind}-name`).getByText(name, { exact: true }) });
}

function deviceRow(page: Page, key: string): Locator {
  return page.getByTestId("device-item").filter({ has: page.getByTestId("device-key").getByText(key, { exact: true }) });
}

async function box(locator: Locator): Promise<{ x: number; y: number; width: number; height: number }> {
  const found = await locator.boundingBox();
  if (found === null) {
    throw new Error("element has no box");
  }
  return found;
}

/**
 * Reads the boxes of several elements in one step (one task of the page), so
 * that a render between two reads cannot move one element against the other.
 * Separate `boundingBox` calls each cost a round trip to the browser.
 */
async function boxesTogether(page: Page, locators: readonly Locator[]): Promise<{ x: number; y: number; width: number; height: number }[]> {
  const handles = await Promise.all(locators.map((locator) => locator.elementHandle()));
  return page.evaluate(
    (elements) =>
      elements.map((element) => {
        const { x, y, width, height } = (element as Element).getBoundingClientRect();
        return { x, y, width, height };
      }),
    handles,
  );
}

for (const width of [1024, 1600]) {
  test(`devices of a plant stand in fixed columns at ${String(width)} px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const created = await createPlant(page);
    await page.getByLabel("Search", { exact: true }).fill(created.plantName);
    const [first, second] = created.devices.map((device) => deviceRow(page, device.key));
    if (first === undefined || second === undefined) {
      throw new Error("two devices expected");
    }

    // Measure only in the settled state: the search has filtered the tree down
    // to this plant (the status line says so) and the interface font is in use.
    // Before that the tree is longer and rows move when the filter is applied.
    await expect(page.getByTestId("structure-search-status")).toHaveText("2 devices shown");
    await page.evaluate(async () => {
      await document.fonts.load('16px "Inter"');
      await document.fonts.ready;
    });
    // The class is written out next to its icon.
    await expect(first.getByTestId("device-class")).toHaveText("PLC");
    await expect(second.getByTestId("device-class")).toHaveText("Controller / embedded");
    // Name, key and address start at the same place in both rows, although the class labels differ in length.
    const firstRow = [first.getByRole("link"), first.getByTestId("device-key"), first.getByTestId("device-ip")];
    const secondRow = [second.getByRole("link"), second.getByTestId("device-key"), second.getByTestId("device-ip")];
    for (const part of [...firstRow, ...secondRow]) {
      await expect(part).toBeVisible();
    }
    // All boxes are read in one step, so the limits below stay as strict as they are.
    const boxes = await boxesTogether(page, [...firstRow, ...secondRow]);
    for (const [index, part] of boxes.slice(0, 3).entries()) {
      const other = boxes[index + 3];
      if (other === undefined) {
        throw new Error("missing cell");
      }
      expect(Math.abs(part.x - other.x)).toBeLessThan(1);
    }
    // One line per device.
    const [link, key] = boxes;
    if (link === undefined || key === undefined) {
      throw new Error("missing cell");
    }
    expect(Math.abs(key.y - link.y)).toBeLessThan(8);
  });
}

test("at 375 px the actions stay on the right and the tree fits the width", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  const created = await createPlant(page);
  await page.getByLabel("Search", { exact: true }).fill(created.plantName);
  await expect(page.getByTestId("structure-search-status")).toHaveText("2 devices shown");

  const plant = item(page, "plant", created.plantName);
  const name = plant.getByTestId("plant-name");
  const edit = page.getByRole("button", { name: `Edit plant ${created.plantName}` });
  const add = page.getByRole("button", { name: `New device in ${created.plantName}` });
  const nameBox = await box(name);
  const editBox = await box(edit);
  const addBox = await box(add);
  // Both buttons right of the name, side by side at the end of the row, the add button last.
  expect(editBox.x).toBeGreaterThan(nameBox.x);
  expect(addBox.x).toBeGreaterThan(editBox.x);
  expect(Math.abs(addBox.y - editBox.y)).toBeLessThan(1);
  const plantBox = await box(plant);
  expect(plantBox.x + plantBox.width - (addBox.x + addBox.width)).toBeLessThan(2);
  // Icon buttons, 28 px high.
  expect(Math.round(editBox.height)).toBe(28);
  await expect(edit).toHaveText("");

  // Key and address go to a second line below the name; the class shows as icon only.
  const device = deviceRow(page, created.devices[0]?.key ?? "");
  const link = await box(device.getByRole("link"));
  expect((await box(device.getByTestId("device-key"))).y).toBeGreaterThanOrEqual(link.y + link.height - 1);
  expect((await box(device.getByTestId("device-class"))).width).toBeLessThan(20);
  await expect(device.getByTestId("device-class")).toHaveAttribute("title", "PLC");

  // No sideways scrolling.
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("with a mouse the actions show clearly on hover and focus of their row", async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 900 });
  const created = await createPlant(page);
  await page.getByLabel("Search", { exact: true }).fill(created.plantName);
  const edit = page.getByRole("button", { name: `Edit plant ${created.plantName}` });
  const actions = edit.locator("..");

  await page.mouse.move(0, 0);
  await expect(actions).toHaveCSS("opacity", "0");
  await item(page, "plant", created.plantName).getByTestId("plant-name").hover();
  await expect(actions).toHaveCSS("opacity", "1");
  await page.mouse.move(0, 0);
  await expect(actions).toHaveCSS("opacity", "0");
  await edit.focus();
  await expect(actions).toHaveCSS("opacity", "1");
  // Clicking an action works as before.
  await edit.click();
  await expect(page.getByRole("form", { name: "Edit plant" })).toBeVisible();
});

test.describe("on a touch screen", () => {
  test.use({ hasTouch: true, isMobile: true, viewport: { width: 375, height: 812 } });

  test("the actions always show", async ({ page }) => {
    const created = await createPlant(page);
    await page.getByLabel("Search", { exact: true }).fill(created.plantName);
    const edit = page.getByRole("button", { name: `Edit plant ${created.plantName}` });
    await expect(edit.locator("..")).toHaveCSS("opacity", "1");
  });
});

test("areas and plants fold, the choice survives a reload, and the search unfolds hits", async ({ page }) => {
  const created = await createPlant(page);
  const area = item(page, "area", created.areaName);
  const toggle = page.getByRole("button", { name: `Contents of area ${created.areaName}` });
  const device = created.devices[0];
  if (device === undefined) {
    throw new Error("a device expected");
  }

  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  await expect(area.getByTestId("plant-item")).toHaveCount(1);
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await expect(area.getByTestId("plant-item")).toHaveCount(0);
  // The count of the folded area stays.
  await expect(area.getByTestId("device-count")).toHaveText("2 devices");

  await page.reload();
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await expect(area.getByTestId("plant-item")).toHaveCount(0);

  // The search opens the way to its hit; clearing it folds the area again.
  const search = page.getByLabel("Search", { exact: true });
  await search.fill(device.key);
  await expect(page.getByTestId("structure-search-status")).toHaveText("1 device shown");
  await expect(page.getByRole("link", { name: device.name })).toBeVisible();
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  await search.fill("");
  await expect(page.getByTestId("structure-search-status")).toHaveText("");
  await expect(toggle).toHaveAttribute("aria-expanded", "false");

  // Plants fold the same way.
  await toggle.click();
  const plantToggle = page.getByRole("button", { name: `Devices of plant ${created.plantName}` });
  await plantToggle.click();
  await expect(plantToggle).toHaveAttribute("aria-expanded", "false");
  await expect(item(page, "plant", created.plantName).getByTestId("device-item")).toHaveCount(0);
});
