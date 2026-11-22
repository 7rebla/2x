// Reads the colour tokens out of the text of index.css, so that the contrast
// test measures exactly the values the browser gets. Used only by tests
// (theme/contrast.test.ts); nothing in the app imports it.
import { type Accent, accents, type ResolvedTheme } from "./settings.ts";

/** A rule of the stylesheet without nested blocks: its selectors and custom properties. */
interface CssBlock {
  readonly selectors: readonly string[];
  readonly properties: ReadonlyMap<string, string>;
}

const BLOCK = /([^{}]+)\{([^{}]*)\}/g;
const PROPERTY = /(--[\w-]+)\s*:\s*([^;]+);/g;

function normalizeSelector(selector: string): string {
  return selector.trim().replace(/\s+/g, " ").replace(/'/g, '"');
}

/** All innermost blocks of the stylesheet (comments removed). */
export function parseBlocks(css: string): CssBlock[] {
  const text = css.replace(/\/\*[\s\S]*?\*\//g, "");
  const blocks: CssBlock[] = [];
  for (const match of text.matchAll(BLOCK)) {
    const [, head = "", body = ""] = match;
    const properties = new Map<string, string>();
    for (const property of body.matchAll(PROPERTY)) {
      const [, name = "", value = ""] = property;
      properties.set(name, value.trim().replace(/\s+/g, " "));
    }
    blocks.push({ selectors: head.split(",").map(normalizeSelector), properties });
  }
  return blocks;
}

function propertiesFor(blocks: readonly CssBlock[], selector: string): Map<string, string> {
  const merged = new Map<string, string>();
  for (const block of blocks) {
    if (block.selectors.includes(selector)) {
      for (const [name, value] of block.properties) {
        merged.set(name, value);
      }
    }
  }
  return merged;
}

/** Selector of an accent on the page (<html data-accent>) in one mode. */
export function pageAccentSelector(mode: ResolvedTheme, accent: Accent): string {
  const theme = mode === "dark" ? '[data-theme="dark"]' : "";
  return accent === "aubergine" ? `:root${theme}` : `:root${theme}[data-accent="${accent}"]`;
}

/** Selector of an accent preview tile (settings page) in one mode. */
export function previewAccentSelector(mode: ResolvedTheme, accent: Accent): string {
  const preview = `[data-accent-preview="${accent}"]`;
  return mode === "dark" ? `[data-theme="dark"] ${preview}` : preview;
}

export interface ThemeTokens {
  /** Tailwind colour name (e.g. "accent") → custom property it reads (e.g. "--twox-accent"). */
  readonly colourNames: ReadonlyMap<string, string>;
  /** Custom properties for neutral and status colours per mode. */
  readonly base: Readonly<Record<ResolvedTheme, ReadonlyMap<string, string>>>;
  /** Accent properties per mode and accent, as set for the preview tile. */
  readonly accentPreview: Readonly<Record<ResolvedTheme, ReadonlyMap<Accent, ReadonlyMap<string, string>>>>;
  /** Accent properties per mode and accent, as set on the page. */
  readonly accentPage: Readonly<Record<ResolvedTheme, ReadonlyMap<Accent, ReadonlyMap<string, string>>>>;
}

/** The token blocks of index.css. */
export function readThemeTokens(css: string): ThemeTokens {
  const blocks = parseBlocks(css);
  const colourNames = new Map<string, string>();
  for (const block of blocks) {
    if (block.selectors.length === 1 && block.selectors[0] === "@theme inline") {
      for (const [name, value] of block.properties) {
        const reference = /^var\((--[\w-]+)\)$/.exec(value);
        if (name.startsWith("--color-") && reference?.[1] !== undefined) {
          colourNames.set(name.slice("--color-".length), reference[1]);
        }
      }
    }
  }
  const accentMaps = (selectorOf: (mode: ResolvedTheme, accent: Accent) => string, mode: ResolvedTheme) =>
    new Map(accents.map((accent) => [accent, propertiesFor(blocks, selectorOf(mode, accent))] as const));
  return {
    colourNames,
    base: {
      // Neutral and status colours sit in blocks for :root alone, never with an accent.
      light: neutralProperties(blocks, ":root"),
      dark: neutralProperties(blocks, ':root[data-theme="dark"]'),
    },
    accentPreview: { light: accentMaps(previewAccentSelector, "light"), dark: accentMaps(previewAccentSelector, "dark") },
    accentPage: { light: accentMaps(pageAccentSelector, "light"), dark: accentMaps(pageAccentSelector, "dark") },
  };
}

function neutralProperties(blocks: readonly CssBlock[], selector: string): Map<string, string> {
  return propertiesFor(
    blocks.filter((block) => block.selectors.length === 1),
    selector,
  );
}

/**
 * Colour value of every Tailwind colour name in one mode with one accent,
 * resolved through index.css like the browser does on the page.
 */
export function resolveColours(tokens: ThemeTokens, mode: ResolvedTheme, accent: Accent): Map<string, string> {
  const accentProperties = tokens.accentPage[mode].get(accent) ?? new Map<string, string>();
  const colours = new Map<string, string>();
  for (const [name, property] of tokens.colourNames) {
    const value = accentProperties.get(property) ?? tokens.base[mode].get(property);
    if (value === undefined) {
      throw new Error(`--color-${name} reads ${property}, which ${mode} mode with accent ${accent} does not define`);
    }
    colours.set(name, value);
  }
  return colours;
}
