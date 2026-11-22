import { cleanup, render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { SvgGlyph } from "./glyph.tsx";
import { ICON_STROKE_WIDTH, Icon, type IconSize } from "./Icon.tsx";
import { iconNames } from "./names.ts";

afterEach(() => {
  cleanup();
});

/** Every colour value an SVG attribute may carry: none, or the text colour. */
const ALLOWED_PAINT = new Set(["none", "currentColor"]);

function renderIcon(element: ReactElement): SVGSVGElement {
  const { container } = render(element);
  const svg = container.querySelector("svg");
  if (svg === null) {
    throw new Error("no svg rendered");
  }
  return svg;
}

describe("icon names", () => {
  it("has a name for every icon of the first set and no duplicate", () => {
    expect(iconNames.length).toBeGreaterThanOrEqual(30);
    expect(new Set(iconNames).size).toBe(iconNames.length);
  });

  it.each(iconNames)("renders %s as an outline SVG in currentColor on the 24 grid", (name) => {
    const svg = renderIcon(<Icon name={name} decorative />);
    expect(svg.getAttribute("viewBox")).toBe("0 0 24 24");
    expect(svg.getAttribute("stroke")).toBe("currentColor");
    expect(svg.getAttribute("fill")).toBe("none");
    expect(svg.getAttribute("stroke-width")).toBe(String(ICON_STROKE_WIDTH));
    expect(svg.getAttribute("data-icon")).toBe(name);
    // Some shapes at all, and no colour of their own anywhere inside.
    expect(svg.children.length).toBeGreaterThan(0);
    for (const element of [svg, ...svg.querySelectorAll("*")]) {
      for (const attribute of ["fill", "stroke", "color", "stop-color"]) {
        const value = element.getAttribute(attribute);
        if (value !== null) {
          expect(ALLOWED_PAINT.has(value), `${name}: ${attribute}="${value}"`).toBe(true);
        }
      }
      expect(element.getAttribute("style")).toBeNull();
    }
  });

  it("draws every icon differently", () => {
    const drawings = iconNames.map((name) => renderIcon(<Icon name={name} decorative />).innerHTML);
    expect(new Set(drawings).size).toBe(iconNames.length);
  });
});

describe("Icon", () => {
  it("hides a decorative icon from assistive technology", () => {
    const svg = renderIcon(<Icon name="structure" decorative />);
    expect(svg.getAttribute("aria-hidden")).toBe("true");
    expect(svg.getAttribute("role")).toBeNull();
    expect(svg.getAttribute("aria-label")).toBeNull();
    expect(svg.getAttribute("focusable")).toBe("false");
  });

  it("names an icon that carries meaning", () => {
    renderIcon(<Icon name="warning" label="Warning" />);
    const svg = screen.getByRole("img", { name: "Warning" });
    expect(svg.getAttribute("aria-hidden")).toBeNull();
  });

  it.each<IconSize>([16, 20, 24])("is %i px wide and high", (size) => {
    const svg = renderIcon(<Icon name="search" size={size} decorative />);
    expect(svg.getAttribute("width")).toBe(String(size));
    expect(svg.getAttribute("height")).toBe(String(size));
  });

  it("is 16 px by default and keeps extra classes", () => {
    const svg = renderIcon(<Icon name="success" className="text-success" decorative />);
    expect(svg.getAttribute("width")).toBe("16");
    expect(svg.getAttribute("class")).toContain("text-success");
    expect(svg.getAttribute("class")).toContain("shrink-0");
  });

  it("does not compile without a decision about the meaning", () => {
    // @ts-expect-error -- neither decorative nor label
    const missing = <Icon name="search" />;
    // @ts-expect-error -- both at once
    const both = <Icon name="search" decorative label="Search" />;
    // @ts-expect-error -- an unknown name
    const unknown = <Icon name="no-such-icon" decorative />;
    expect([missing, both, unknown]).toHaveLength(3);
  });
});

describe("SvgGlyph (frame of own icons)", () => {
  it("follows the same rules as the library icons", () => {
    const svg = renderIcon(
      <SvgGlyph size={20} strokeWidth={ICON_STROKE_WIDTH} aria-hidden>
        <rect x="4" y="4" width="16" height="16" rx="2" />
      </SvgGlyph>,
    );
    expect(svg.getAttribute("viewBox")).toBe("0 0 24 24");
    expect(svg.getAttribute("fill")).toBe("none");
    expect(svg.getAttribute("stroke")).toBe("currentColor");
    expect(svg.getAttribute("stroke-linecap")).toBe("round");
    expect(svg.getAttribute("stroke-linejoin")).toBe("round");
    expect(svg.getAttribute("width")).toBe("20");
    expect(svg.getAttribute("aria-hidden")).toBe("true");
  });
});
