import type { Locator, Page } from "@playwright/test";

import { expect, test, testIp, testName } from "./fixtures";

// The map (/map, work order 039), signed in as the test account. The test
// creates its own structure through the API with unique names and an address
// from 192.0.2.0/24, so repeated runs against the same database (with the
// devices of earlier runs on the map) do not disturb each other.
test.use({ locale: "en-US" });

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

/** Whether the element lies completely inside the box of another one (for example a node inside the map). */
async function insideBox(inner: Locator, outer: Locator): Promise<boolean> {
  const [innerBox, outerBox] = await Promise.all([inner.boundingBox(), outer.boundingBox()]);
  if (innerBox === null || outerBox === null) {
    return false;
  }
  return (
    innerBox.x >= outerBox.x &&
    innerBox.y >= outerBox.y &&
    innerBox.x + innerBox.width <= outerBox.x + outerBox.width &&
    innerBox.y + innerBox.height <= outerBox.y + outerBox.height
  );
}

test("the map shows a device and its network, finds it and opens its page", async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      consoleErrors.push(message.text());
    }
  });
  page.on("pageerror", (error) => {
    consoleErrors.push(error.message);
  });

  await page.goto("/");
  const site = await create(page, "/api/v1/sites/", { name: testName("site") });
  const area = await create(page, "/api/v1/areas/", { site: site.id, name: testName("area") });
  const plantKey = testName("plant");
  const plant = await create(page, "/api/v1/plants/", { area: area.id, key: plantKey, name: testName("plant") });
  const deviceKey = testName("device");
  const deviceName = testName("device");
  const ip = testIp(1 + Math.floor(Math.random() * 254));
  const device = await create(page, "/api/v1/devices/", {
    plant: plant.id,
    key: deviceKey,
    name: deviceName,
    ip_address: ip,
    model: "Test model",
  });
  // A second device without an address: on the map, but without a network line.
  const plainKey = testName("device");
  await create(page, "/api/v1/devices/", { plant: plant.id, key: plainKey, name: testName("device") });

  // Through the navigation to the map.
  await page.getByRole("navigation", { name: "Main navigation" }).getByRole("link", { name: "Map" }).click();
  await expect(page).toHaveURL(/\/map$/);
  await expect(page.getByRole("heading", { level: 2 })).toHaveText("Map");
  const canvas = page.getByRole("region", { name: "Map of sites, areas, plants, devices and networks" });
  await expect(canvas).toBeVisible();
  await expect(page.getByTestId("map-list-link")).toHaveAttribute("href", "/");

  // The network of the test addresses is a node of its own.
  const network = canvas.getByRole("group", { name: /^Network 192\.0\.2\.0\/24 with \d+ devices?$/ });
  await expect(network).toBeVisible();
  await expect(network.getByTestId("map-network")).toHaveText("Network192.0.2.0/24");

  // The search finds the device by its address and its key and brings it into view.
  const search = page.getByLabel("Search on the map");
  await search.fill(deviceKey);
  await expect(page.getByTestId("map-search-status")).toHaveText("1 match");
  const deviceNode = canvas.getByRole("link", {
    name: `Device ${deviceName} (${deviceKey}), ${ip} in network 192.0.2.0/24, opens the device page`,
  });
  await expect(deviceNode).toBeVisible();
  await expect(deviceNode).toBeInViewport();
  await expect(deviceNode.getByTestId("map-device")).toHaveAttribute("data-match", "true");
  await expect(deviceNode.getByTestId("map-device")).toHaveText(`${deviceName}${deviceKey}${ip}Test model`);
  // Its network line is drawn and highlighted; a device without an address has none.
  await expect(canvas.locator(".react-flow__edge.map-membership-active")).toHaveCount(1);
  await expect(canvas.locator(`[data-id="member:device:${String(device.id)}"]`)).toHaveCount(1);
  await search.fill(plainKey);
  await expect(page.getByTestId("map-search-status")).toHaveText("1 match");
  await expect(canvas.locator(".react-flow__edge.map-membership-active")).toHaveCount(0);

  await search.fill(ip);
  // The address may also match longer addresses of other devices (192.0.2.24 and
  // 192.0.2.242); the view then fits all matches, so the node is inside the map,
  // though not necessarily inside the browser window.
  await expect.poll(() => insideBox(deviceNode, canvas)).toBe(true);
  await expect(deviceNode.getByTestId("map-device")).toHaveAttribute("data-match", "true");

  // Hiding the networks removes the network node and the lines.
  await page.getByLabel("Show networks").uncheck();
  await expect(network).toBeHidden();
  await expect(canvas.locator(".react-flow__edge")).toHaveCount(0);
  await page.getByLabel("Show networks").check();
  await expect(network).toBeVisible();

  // A click on the device opens its page.
  await search.fill(deviceKey);
  await expect(deviceNode).toBeInViewport();
  await deviceNode.click();
  await expect(page).toHaveURL(new RegExp(`/devices/${String(device.id)}$`));
  await expect(page.getByRole("heading", { level: 2 })).toHaveText(deviceName);

  // Back on the map, Enter on the focused device opens the page as well.
  await page.goBack();
  await expect(canvas).toBeVisible();
  await page.getByLabel("Search on the map").fill(deviceKey);
  await expect(page.getByTestId("map-search-status")).toHaveText("1 match");
  await deviceNode.focus();
  await expect(deviceNode.getByTestId("map-device")).toHaveAttribute("data-highlighted", "true");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(new RegExp(`/devices/${String(device.id)}$`));

  expect(consoleErrors, "errors in the browser console").toEqual([]);
});
