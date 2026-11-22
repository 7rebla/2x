// The shared building blocks of search hits and answer sources (moved from
// pages/search/SearchHitView.tsx by work order 132). The search page tests
// cover them in place; these tests cover the parts the answer page relies on.
// Titles and names are invented test names.
import { cleanup, render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, describe, expect, it } from "vitest";

import type { SearchLocation } from "../../api/generated";
import { changeLanguage } from "../../i18n.ts";
import { hiddenPlacesKind, Locations, PageLabel, Snippet } from "./index.ts";

afterEach(async () => {
  cleanup();
  await changeLanguage("en");
});

function show(element: ReactElement): void {
  render(<RouterProvider router={createMemoryRouter([{ path: "/", element }])} />);
}

function place(deviceId: number, isLatest = true): SearchLocation {
  return {
    document: { id: 7, title: "Test manual" },
    version: { id: 71, number: 2, original_filename: "test-manual-v2.pdf", is_latest: isLatest },
    device: { id: deviceId, key: `test-device-${String(deviceId)}`, name: "Test controller" },
    plant: { id: 100, key: "test-plant-1", name: "Test plant one" },
  };
}

describe("PageLabel", () => {
  it("takes only the page numbers", () => {
    show(<PageLabel pages={{ page_start: 31, page_end: 32 }} />);
    expect(screen.getByTestId("search-hit-page").textContent).toBe("pp. 31–32");
  });

  it("shows nothing without a page", () => {
    show(<PageLabel pages={{ page_start: null, page_end: null }} />);
    expect(screen.queryByTestId("search-hit-page")).toBeNull();
  });
});

describe("Snippet", () => {
  it("shows the text without marks when there are no highlights", () => {
    show(<Snippet hit={{ snippet: "Plain <b>test</b> text.", highlights: [] }} />);
    const snippet = screen.getByTestId("search-snippet");
    expect(snippet.textContent).toBe("Plain <b>test</b> text.");
    expect(snippet.querySelector("mark, b")).toBeNull();
  });
});

describe("Locations", () => {
  it("shows one place with its links and the older version mark", () => {
    show(<Locations locations={[place(1000, false)]} />);
    expect(screen.getByTestId("search-location-document").getAttribute("href")).toBe("/documents/7");
    expect(screen.getByTestId("search-location-device").getAttribute("href")).toBe("/devices/1000");
    expect(screen.getByTestId("search-location-filename").textContent).toBe("test-manual-v2.pdf");
    expect(screen.getByTestId("search-older-version").textContent).toBe("Older version");
    expect(screen.queryByTestId("search-more-locations")).toBeNull();
  });

  it("names hidden places by devices or places", () => {
    expect(hiddenPlacesKind([place(1000), place(1001)])).toBe("devices");
    expect(hiddenPlacesKind([place(1000), place(1000)])).toBe("places");
  });
});
