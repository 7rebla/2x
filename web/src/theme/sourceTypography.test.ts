// Font sizes of small text (E-65 point 5, work order 084): metadata use the
// token text-meta (13 px) from index.css; 12 px (text-xs) stays only for labels
// in capitals. Without this check a new page would bring back 12 px metadata.
import { describe, expect, it } from "vitest";

import indexCss from "../index.css?raw";

const sources = import.meta.glob<string>(["../**/*.{ts,tsx}", "!../**/*.test.{ts,tsx}", "!../api/generated/**"], {
  query: "?raw",
  import: "default",
  eager: true,
});

/** A quoted or template string, the place where class lists live. */
const CLASS_STRING = /"[^"\n]*"|`[^`]*`/g;

function classStringsWith(pattern: RegExp): string[] {
  const found: string[] = [];
  for (const [path, text] of Object.entries(sources)) {
    for (const match of text.matchAll(CLASS_STRING)) {
      if (pattern.test(match[0])) {
        const line = text.slice(0, match.index).split("\n").length;
        found.push(`${path}:${String(line)}: ${match[0]}`);
      }
    }
  }
  return found;
}

/** Value of a custom property in the first @theme block of index.css. */
function themeValue(name: string): string | undefined {
  const block = /@theme\s*\{([\s\S]*?)\n\}/.exec(indexCss)?.[1] ?? "";
  return new RegExp(`^\\s*${name}:\\s*([^;]+);`, "m").exec(block)?.[1]?.trim();
}

describe("font sizes in the source code", () => {
  it("reads the sources of the app", () => {
    expect(Object.keys(sources)).toContain("../components/Layout.tsx");
    expect(Object.keys(sources)).toContain("../pages/StructurePage.tsx");
    expect(Object.keys(sources).some((path) => path.includes(".test."))).toBe(false);
  });

  it("defines the metadata size as 13 px on an 18 px line", () => {
    expect(themeValue("--text-meta")).toBe("0.8125rem");
    expect(themeValue("--text-meta--line-height")).toBe("1.125rem");
  });

  it("uses the metadata size for metadata", () => {
    // The places of work order 084, as a sample that the token is in use.
    expect(classStringsWith(/\btext-meta\b/).length).toBeGreaterThanOrEqual(20);
  });

  it("uses 12 px (text-xs) only for labels in capitals", () => {
    const found = classStringsWith(/\btext-xs\b/).filter((entry) => !/\buppercase\b/.test(entry));
    expect(found).toEqual([]);
  });

  it("uses no font size in pixels, only the named sizes", () => {
    expect(classStringsWith(/\btext-\[\d+(?:\.\d+)?(?:px|rem|em)\]/)).toEqual([]);
  });
});
