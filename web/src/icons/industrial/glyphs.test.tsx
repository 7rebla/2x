import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ICON_STROKE_WIDTH, Icon } from "../Icon.tsx";
import type { IconName } from "../names.ts";
import controllerSvg from "./dev-02-controller.svg?raw";
import computerSvg from "./dev-03-rechner.svg?raw";
import firewallSvg from "./dev-06-firewall.svg?raw";
import plcSvg from "./dev-01-sps.svg?raw";
import robotSvg from "./dev-05-roboter.svg?raw";
import routerSvg from "./dev-04-router.svg?raw";
import plantSvg from "./obj-03-anlage.svg?raw";
import deviceSvg from "./obj-04-geraet.svg?raw";

afterEach(() => {
  cleanup();
});

/** Each own icon with the approved drawing it repeats. */
const DRAWINGS: readonly (readonly [IconName, string])[] = [
  ["plant", plantSvg],
  ["device", deviceSvg],
  ["devicePlc", plcSvg],
  ["deviceController", controllerSvg],
  ["deviceComputer", computerSvg],
  ["deviceRouter", routerSvg],
  ["deviceRobot", robotSvg],
  ["deviceFirewall", firewallSvg],
];

/** An element as tag name and its attributes in a fixed order, for comparing drawings. */
type Shape = readonly [string, readonly (readonly [string, string])[]];

function shapeOf(element: Element): Shape {
  const attributes = [...element.attributes]
    .map((attribute) => [attribute.name, attribute.value] as const)
    .sort(([a], [b]) => a.localeCompare(b));
  return [element.localName, attributes];
}

function parse(source: string): SVGSVGElement {
  const document = new DOMParser().parseFromString(source, "image/svg+xml");
  const root = document.documentElement;
  if (!(root instanceof SVGSVGElement)) {
    throw new Error("not an SVG document");
  }
  return root;
}

describe("own icons (work order 074)", () => {
  it.each(DRAWINGS)("%s draws exactly the shapes of its approved file", (name, source) => {
    const file = parse(source);
    const { container } = render(<Icon name={name} size={24} decorative />);
    const svg = container.querySelector("svg");
    expect(svg).not.toBeNull();
    expect([...(svg?.children ?? [])].map(shapeOf)).toEqual([...file.children].map(shapeOf));
  });

  it.each(DRAWINGS)("the file of %s follows the rules of the icon set and holds nothing but shapes", (_name, source) => {
    const file = parse(source);
    expect(file.getAttribute("viewBox")).toBe("0 0 24 24");
    expect(file.getAttribute("fill")).toBe("none");
    expect(file.getAttribute("stroke")).toBe("currentColor");
    expect(file.getAttribute("stroke-width")).toBe(String(ICON_STROKE_WIDTH));
    expect(file.getAttribute("stroke-linecap")).toBe("round");
    expect(file.getAttribute("stroke-linejoin")).toBe("round");
    // Only basic shapes: no text, title, style, script, link or embedded image.
    for (const element of file.querySelectorAll("*")) {
      expect(["path", "rect", "circle"]).toContain(element.localName);
      expect(element.textContent).toBe("");
    }
  });
});
