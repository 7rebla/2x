// Contrast of every colour pair the interface uses, in both modes and with
// every accent, measured on the values of index.css (WCAG 2.2: text 4.5:1,
// focus ring and borders of form controls 3:1).
import { describe, expect, it } from "vitest";

import indexCss from "../index.css?raw";
import { contrastRatio, parseHexColour, relativeLuminance } from "./contrast.ts";
import { pageAccentSelector, readThemeTokens, resolveColours } from "./cssTokens.ts";
import { accents, type ResolvedTheme } from "./settings.ts";

const TEXT = 4.5;
const NON_TEXT = 3;

/** Foreground, background, minimum ratio, what the pair is used for. */
type Pair = readonly [foreground: string, background: string, minimum: number, use: string];

const pairs: readonly Pair[] = [
  ["fg", "canvas", TEXT, "text on the page"],
  ["fg", "surface", TEXT, "text on cards, header, inputs"],
  ["fg", "surface-muted", TEXT, "text on hovered rows and network nodes"],
  ["fg", "accent-soft", TEXT, "text on the selected accent tile"],
  ["fg-muted", "canvas", TEXT, "secondary text on the page"],
  ["fg-muted", "surface", TEXT, "secondary text on cards"],
  ["fg-muted", "surface-muted", TEXT, "secondary text on muted areas"],
  ["accent", "canvas", TEXT, "links on the page"],
  ["accent", "surface", TEXT, "links on cards"],
  ["accent-strong", "canvas", TEXT, "hovered links on the page"],
  ["accent-strong", "surface", TEXT, "hovered links on cards"],
  ["accent-strong", "accent-soft", TEXT, "strong accent text on the soft accent"],
  ["on-accent", "accent", TEXT, "text of primary buttons"],
  ["on-accent", "accent-strong", TEXT, "text of hovered primary buttons"],
  ["focus", "canvas", NON_TEXT, "focus ring on the page"],
  ["focus", "surface", NON_TEXT, "focus ring on cards"],
  ["accent", "surface", NON_TEXT, "navigation line in the header"],
  ["accent", "accent-soft", NON_TEXT, "navigation line of the current entry on its soft background"],
  ["line-strong", "canvas", NON_TEXT, "border of form controls on the page"],
  ["line-strong", "surface", NON_TEXT, "border of form controls on cards"],
  ["line-strong", "surface-muted", NON_TEXT, "border of controls on muted areas"],
  ["success", "success-soft", TEXT, "success message"],
  ["success", "canvas", TEXT, "success text on the page"],
  ["success", "surface", TEXT, "success text on cards"],
  ["warning", "warning-soft", TEXT, "warning message"],
  ["warning", "canvas", TEXT, "warning text on the page"],
  ["danger", "danger-soft", TEXT, "error message"],
  ["danger", "canvas", TEXT, "error text on the page"],
  ["danger", "surface", TEXT, "field errors on cards"],
  ["info", "info-soft", TEXT, "information message"],
  ["info", "surface", TEXT, "information text on cards"],
];

const modes: readonly ResolvedTheme[] = ["light", "dark"];
const tokens = readThemeTokens(indexCss);

describe("contrast function", () => {
  it("reads #rrggbb colours", () => {
    expect(parseHexColour("#765477")).toEqual([0x76, 0x54, 0x77]);
    expect(parseHexColour(" #FFFFFF ")).toEqual([255, 255, 255]);
    expect(() => parseHexColour("#fff")).toThrow();
    expect(() => parseHexColour("var(--x)")).toThrow();
  });

  it("measures known ratios", () => {
    expect(relativeLuminance("#000000")).toBe(0);
    expect(relativeLuminance("#ffffff")).toBeCloseTo(1, 10);
    expect(contrastRatio("#000000", "#ffffff")).toBeCloseTo(21, 10);
    expect(contrastRatio("#ffffff", "#000000")).toBeCloseTo(21, 10);
    expect(contrastRatio("#765477", "#765477")).toBe(1);
    // Reference values of the WCAG examples: #777777 just misses 4.5:1 on white, #767676 just reaches it.
    expect(contrastRatio("#777777", "#ffffff")).toBeLessThan(4.5);
    expect(contrastRatio("#767676", "#ffffff")).toBeGreaterThanOrEqual(4.5);
  });
});

describe("theme tokens in index.css", () => {
  it("names every colour the components use", () => {
    expect([...tokens.colourNames.keys()].sort()).toEqual(
      [
        "accent",
        "accent-soft",
        "accent-strong",
        "canvas",
        "danger",
        "danger-line",
        "danger-soft",
        "fg",
        "fg-muted",
        "focus",
        "info",
        "info-line",
        "info-soft",
        "line",
        "line-strong",
        "on-accent",
        "success",
        "success-line",
        "success-soft",
        "surface",
        "surface-muted",
        "warning",
        "warning-line",
        "warning-soft",
      ].sort(),
    );
  });

  it.each(modes)("defines every colour as #rrggbb in %s mode with every accent", (mode) => {
    for (const accent of accents) {
      for (const [name, value] of resolveColours(tokens, mode, accent)) {
        expect(() => parseHexColour(value), `${mode}/${accent}: ${name} = ${value}`).not.toThrow();
      }
    }
  });

  it.each(modes)("gives page and preview tile the same accent values in %s mode", (mode) => {
    for (const accent of accents) {
      const preview = tokens.accentPreview[mode].get(accent);
      const page = tokens.accentPage[mode].get(accent);
      expect(preview?.size, `${mode}/${accent} preview`).toBe(4);
      for (const [property, value] of preview ?? []) {
        expect(page?.get(property), `${pageAccentSelector(mode, accent)} ${property}`).toBe(value);
      }
    }
  });

  it("keeps status colours independent of the accent", () => {
    for (const mode of modes) {
      const statusOf = (accent: (typeof accents)[number]): string[] =>
        [...resolveColours(tokens, mode, accent)]
          .filter(([name]) => /^(success|warning|danger|info)/.test(name))
          .map(([name, value]) => `${name}=${value}`);
      for (const accent of accents) {
        expect(statusOf(accent)).toEqual(statusOf("aubergine"));
      }
    }
  });

  it("uses no petrol or turquoise accent (hue 160–200°)", () => {
    for (const mode of modes) {
      for (const accent of accents) {
        const [red, green, blue] = parseHexColour(resolveColours(tokens, mode, accent).get("accent") ?? "");
        const max = Math.max(red, green, blue);
        const min = Math.min(red, green, blue);
        if (max === min) {
          continue;
        }
        let hue: number;
        if (max === red) {
          hue = (60 * ((green - blue) / (max - min)) + 360) % 360;
        } else if (max === green) {
          hue = 60 * ((blue - red) / (max - min)) + 120;
        } else {
          hue = 60 * ((red - green) / (max - min)) + 240;
        }
        expect(hue < 160 || hue > 200, `${mode}/${accent} hue ${hue.toFixed(0)}`).toBe(true);
      }
    }
  });
});

describe("contrast of all colour pairs", () => {
  for (const mode of modes) {
    for (const accent of accents) {
      it(`${mode} mode, accent ${accent}`, () => {
        const colours = resolveColours(tokens, mode, accent);
        for (const [foreground, background, minimum, use] of pairs) {
          const ratio = contrastRatio(colours.get(foreground) ?? "", colours.get(background) ?? "");
          expect(ratio, `${foreground} on ${background} (${use}): ${ratio.toFixed(2)}`).toBeGreaterThanOrEqual(minimum);
        }
      });
    }
  }
});
