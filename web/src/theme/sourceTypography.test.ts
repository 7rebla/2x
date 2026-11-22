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

/** Smallest font size (px) allowed in an inline style; below it only labels in capitals. */
const MIN_INLINE_PX = 13;

/**
 * An inline font size in a style object (`fontSize: 11`, `fontSize: "12px"`) or
 * in a style string (`font-size: 0.75rem`). A size given as a variable, such as
 * `var(--text-meta)`, does not match: the token is checked on its own above.
 */
const INLINE_FONT_SIZE =
  /\bfontSize\s*:\s*(?:(\d+(?:\.\d+)?)(?![\w.%])|["'`](\d+(?:\.\d+)?)(px|rem|em)["'`])|\bfont-size\s*:\s*(\d+(?:\.\d+)?)(px|rem|em)\b/g;

/** Inline font sizes below 13 px in the text, except in a style object that also sets `textTransform: "uppercase"`. */
function smallInlineFontSizes(text: string): string[] {
  const found: string[] = [];
  for (const match of text.matchAll(INLINE_FONT_SIZE)) {
    const value = Number(match[1] ?? match[2] ?? match[4]);
    const unit = match[3] ?? match[5] ?? "px";
    const px = unit === "px" ? value : value * 16;
    if (px >= MIN_INLINE_PX) {
      continue;
    }
    const start = text.lastIndexOf("{", match.index);
    const end = text.indexOf("}", match.index);
    const object = text.slice(start < 0 ? 0 : start, end < 0 ? text.length : end);
    if (/\btextTransform\s*:\s*["']uppercase["']/.test(object)) {
      continue;
    }
    found.push(match[0]);
  }
  return found;
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

  it("sets no inline font size below 13 px (React Flow styles such as labelStyle)", () => {
    const found = Object.entries(sources).flatMap(([path, text]) =>
      smallInlineFontSizes(text).map((size) => `${path}: ${size}`),
    );
    expect(found).toEqual([]);
  });

  it("finds an inline font size below 13 px in an example text, and nothing else", () => {
    expect(smallInlineFontSizes("const a = { fontSize: 11, fill: 'red' };")).toEqual(["fontSize: 11"]);
    expect(smallInlineFontSizes('const a = { fontSize: "12px" };')).toEqual(['fontSize: "12px"']);
    expect(smallInlineFontSizes("const a = { fontSize: 12.5 };")).toEqual(["fontSize: 12.5"]);
    expect(smallInlineFontSizes("const a = { fontSize: '0.75rem' };")).toEqual(["fontSize: '0.75rem'"]);
    expect(smallInlineFontSizes('const s = "font-size: 11px; color: red";')).toEqual(["font-size: 11px"]);
    // From 13 px on, as a variable, and numbers in another context: no finding.
    expect(smallInlineFontSizes("const a = { fontSize: 13 };")).toEqual([]);
    expect(smallInlineFontSizes('const a = { fontSize: "0.8125rem" };')).toEqual([]);
    expect(smallInlineFontSizes('const a = { fontSize: "var(--text-meta)" };')).toEqual([]);
    expect(smallInlineFontSizes("const a = { strokeWidth: 11, zIndex: 12, width: 11, fontSize: 14 };")).toEqual([]);
    expect(smallInlineFontSizes("const fontSizes = [11, 12]; const size = 11;")).toEqual([]);
    // A label in capitals may stay small.
    expect(smallInlineFontSizes('const a = { fontSize: 12, textTransform: "uppercase" };')).toEqual([]);
    expect(smallInlineFontSizes('const a = { textTransform: "uppercase", fontSize: 12 };')).toEqual([]);
    expect(smallInlineFontSizes('const a = { textTransform: "uppercase" }; const b = { fontSize: 12 };')).toEqual([
      "fontSize: 12",
    ]);
  });
});
