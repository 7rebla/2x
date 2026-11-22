import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it } from "vitest";

import smallFormSvg from "../assets/brand/bildmarke-16.svg?raw";
import masterSvg from "../assets/brand/bildmarke.svg?raw";
import { changeLanguage } from "../i18n.ts";
import { BrandMark, brandForm, HEADER_BRAND_SIZE, MASTER_MIN_SIZE, nameGap, withUniqueIds } from "./BrandMark.tsx";

afterEach(async () => {
  cleanup();
  await changeLanguage("en");
});

function renderMark(size?: number): void {
  render(
    <MemoryRouter initialEntries={["/devices"]}>
      <BrandMark {...(size === undefined ? {} : { size })} />
    </MemoryRouter>,
  );
}

describe("brandForm", () => {
  it.each([
    [8, "small"],
    [16, "small"],
    [23, "small"],
    [23.9, "small"],
    [24, "master"],
    [36, "master"],
    [64, "master"],
  ] as const)("chooses the %s px form: %s", (size, form) => {
    expect(brandForm(size)).toBe(form);
  });

  it("switches at 24 px, the minimum size of the master", () => {
    expect(MASTER_MIN_SIZE).toBe(24);
    expect(HEADER_BRAND_SIZE).toBeGreaterThanOrEqual(MASTER_MIN_SIZE);
  });
});

describe("withUniqueIds", () => {
  it("prefixes every id and every reference to it", () => {
    const svg = withUniqueIds(masterSvg, "p1");
    expect(svg).toContain('id="p1-m"');
    expect(svg).toContain("url(#p1-m)");
    expect(svg).not.toMatch(/id="m"|url\(#m\)/);
  });

  it("leaves the drawing otherwise unchanged", () => {
    expect(withUniqueIds(smallFormSvg, "p2").replace(/p2-/g, "")).toBe(smallFormSvg);
  });
});

describe("nameGap", () => {
  it("keeps 16 grid units between the visible mark and the name", () => {
    // The box of the mark already holds 6 of the 64 units on each side.
    expect(nameGap(64)).toBe(10);
    expect(nameGap(HEADER_BRAND_SIZE)).toBeCloseTo(5.625, 10);
  });
});

describe("BrandMark", () => {
  it("is a link to the start page named after the visible text 2x", () => {
    renderMark();
    const link = screen.getByRole("link", { name: "2x" });
    expect(link.getAttribute("href")).toBe("/");
    // The only text of the link (the SVG holds whitespace between its elements only).
    expect(link.textContent.trim()).toBe("2x");
  });

  it("keeps the name 2x in every language", async () => {
    await changeLanguage("de");
    renderMark();
    expect(screen.getByRole("link", { name: "2x" })).toBeDefined();
  });

  it("shows the mark as a decorative SVG in the brand colour", () => {
    renderMark();
    const mark = within(screen.getByRole("link")).getByTestId("brand-mark");
    expect(mark.getAttribute("aria-hidden")).toBe("true");
    expect(mark.classList).toContain("text-brand");
    expect(mark.querySelector("svg")).not.toBeNull();
    expect(mark.querySelectorAll("[fill='currentColor'], [stroke='currentColor']").length).toBeGreaterThan(0);
    // No title or text inside the mark: the name next to it says it all.
    expect(mark.textContent.trim()).toBe("");
    expect(mark.querySelector("title, desc, text")).toBeNull();
  });

  it("uses the master at the header size", () => {
    renderMark();
    const mark = screen.getByTestId("brand-mark");
    expect(mark.dataset.form).toBe("master");
    expect(mark.querySelector("svg")?.getAttribute("viewBox")).toBe("0 0 64 64");
    expect(mark.style.width).toBe(`${String(HEADER_BRAND_SIZE)}px`);
    expect(mark.style.height).toBe(`${String(HEADER_BRAND_SIZE)}px`);
  });

  it("uses the small form below 24 px", () => {
    renderMark(16);
    const mark = screen.getByTestId("brand-mark");
    expect(mark.dataset.form).toBe("small");
    expect(mark.querySelector("svg")?.getAttribute("viewBox")).toBe("0 0 16 16");
  });

  it("gives two marks on one page different mask ids", () => {
    render(
      <MemoryRouter>
        <BrandMark />
        <BrandMark />
      </MemoryRouter>,
    );
    const ids = [...document.querySelectorAll("mask")].map((mask) => mask.id);
    expect(ids).toHaveLength(2);
    expect(new Set(ids).size).toBe(2);
    for (const id of ids) {
      expect(document.querySelectorAll(`[mask="url(#${id})"]`)).toHaveLength(1);
    }
  });
});
