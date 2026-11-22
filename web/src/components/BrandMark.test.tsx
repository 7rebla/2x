import { act, cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it } from "vitest";

import smallFormSvg from "../assets/brand/bildmarke-16.svg?raw";
import masterSvg from "../assets/brand/bildmarke.svg?raw";
import { changeLanguage } from "../i18n.ts";
import { refreshDisplay, updateDisplaySettings } from "../theme/store.ts";
import {
  BrandMark,
  brandForm,
  HEADER_BRAND_SIZE,
  MASTER_MIN_SIZE,
  nameGap,
  typingRunFor,
  withUniqueIds,
} from "./BrandMark.tsx";

afterEach(async () => {
  cleanup();
  window.sessionStorage.clear();
  window.localStorage.clear();
  refreshDisplay();
  await changeLanguage("en");
});

describe("typingRunFor", () => {
  it.each([
    ["loading", "pending"],
    ["signed-out", "sign-in"],
    ["error", "sign-in"],
    ["signed-in", "app"],
  ] as const)("maps the session state %s to the run %s", (status, run) => {
    expect(typingRunFor(status)).toBe(run);
  });
});

describe("BrandMark with the typing name", () => {
  function renderTyping(): HTMLElement {
    render(
      <MemoryRouter>
        <BrandMark typing="sign-in" />
      </MemoryRouter>,
    );
    return screen.getByRole("link", { name: "2x" });
  }

  it("keeps 2x as the accessible name and the only text of the link", () => {
    const link = renderTyping();
    expect(link.textContent.trim()).toBe("2x");
    expect(within(link).getByTestId("typed-text").dataset.typing).toBe("type");
    expect(link.querySelector(".tx-type-layer")?.getAttribute("aria-hidden")).toBe("true");
  });

  it("types only the name; the mark is there from the start", () => {
    const link = renderTyping();
    const mark = within(link).getByTestId("brand-mark");
    expect(mark.closest(".tx-type")).toBeNull();
    expect(mark.className).not.toMatch(/tx-/);
    expect([...link.querySelectorAll(".tx-type-char")].map((char) => char.getAttribute("data-char"))).toEqual([
      "2",
      "x",
    ]);
  });

  it("shows the name at once with reduced motion", () => {
    act(() => {
      updateDisplaySettings({ reduceMotion: true });
    });
    const link = renderTyping();
    expect(link.querySelector(".tx-type")).toBeNull();
    expect(link.textContent.trim()).toBe("2x");
  });

  it("does not type without the typing property", () => {
    render(
      <MemoryRouter>
        <BrandMark />
      </MemoryRouter>,
    );
    expect(screen.getByRole("link", { name: "2x" }).querySelector(".tx-type")).toBeNull();
    expect(window.sessionStorage.getItem("twox.typed")).toBeNull();
  });
});

function renderMark(size?: number): void {
  render(
    <MemoryRouter initialEntries={["/devices"]}>
      <BrandMark {...(size === undefined ? {} : { size })} />
    </MemoryRouter>,
  );
}

describe("BrandMark without a link", () => {
  it("draws the same lockup as plain text, without a link", () => {
    render(
      <MemoryRouter>
        <BrandMark size={48} link={false} />
      </MemoryRouter>,
    );
    expect(screen.queryByRole("link")).toBeNull();
    const lockup = screen.getByTestId("brand-lockup");
    expect(lockup.textContent.trim()).toBe("2x");
    const mark = within(lockup).getByTestId("brand-mark");
    expect(mark.getAttribute("aria-hidden")).toBe("true");
    expect(mark.style.width).toBe("48px");
    expect(lockup.style.gap).toBe(`${String(nameGap(48))}px`);
  });

  it("types the name like the header when asked to", () => {
    render(
      <MemoryRouter>
        <BrandMark link={false} typing="sign-in" />
      </MemoryRouter>,
    );
    expect(within(screen.getByTestId("brand-lockup")).getByTestId("typed-text").dataset.typing).toBe("type");
  });
});

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
