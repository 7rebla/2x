// Components take their colours only from the theme tokens (index.css): no
// classes from Tailwind's palette and no hard-coded colour values. Without this
// check a new page would look right in light mode and break in dark mode.
import { describe, expect, it } from "vitest";

const sources = import.meta.glob<string>(["../**/*.{ts,tsx}", "!../**/*.test.{ts,tsx}", "!../api/generated/**"], {
  query: "?raw",
  import: "default",
  eager: true,
});

const PALETTE_CLASS =
  /\b(?:bg|text|border|ring|from|to|via|outline|divide|fill|stroke|decoration|placeholder|shadow|accent|caret)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|white|black)(?:-\d+)?\b/g;
const COLOUR_VALUE = /#[0-9a-f]{6}\b|#[0-9a-f]{3}\b(?![0-9a-z-])|\brgba?\(|\bhsla?\(/gi;

function findings(pattern: RegExp): string[] {
  const found: string[] = [];
  for (const [path, text] of Object.entries(sources)) {
    text.split("\n").forEach((line, index) => {
      for (const match of line.matchAll(pattern)) {
        found.push(`${path}:${String(index + 1)}: ${match[0]}`);
      }
    });
  }
  return found;
}

describe("colours in the source code", () => {
  it("reads the sources of the app", () => {
    expect(Object.keys(sources)).toContain("../components/Layout.tsx");
    expect(Object.keys(sources)).toContain("../pages/SettingsPage.tsx");
    expect(Object.keys(sources).some((path) => path.includes(".test."))).toBe(false);
  });

  it("uses no class of Tailwind's colour palette", () => {
    expect(findings(PALETTE_CLASS)).toEqual([]);
  });

  it("uses no hard-coded colour value", () => {
    expect(findings(COLOUR_VALUE)).toEqual([]);
  });
});
