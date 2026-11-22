// Contrast ratio of two colours after WCAG 2.2 (relative luminance of sRGB),
// used by the contrast test of the theme tokens (contrast.test.ts). Only opaque
// colours written as #rrggbb are supported; that is all index.css uses.

const HEX_COLOUR = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i;

/** Red, green and blue of a colour written as #rrggbb, each 0–255. */
export function parseHexColour(colour: string): readonly [number, number, number] {
  const match = HEX_COLOUR.exec(colour.trim());
  if (match === null) {
    throw new Error(`Not a colour of the form #rrggbb: ${colour}`);
  }
  const [, red = "", green = "", blue = ""] = match;
  return [Number.parseInt(red, 16), Number.parseInt(green, 16), Number.parseInt(blue, 16)];
}

function linearChannel(channel: number): number {
  const value = channel / 255;
  return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
}

/** Relative luminance (0 = black, 1 = white). */
export function relativeLuminance(colour: string): number {
  const [red, green, blue] = parseHexColour(colour);
  return 0.2126 * linearChannel(red) + 0.7152 * linearChannel(green) + 0.0722 * linearChannel(blue);
}

/** Contrast ratio between 1 and 21; the order of the two colours does not matter. */
export function contrastRatio(first: string, second: string): number {
  const a = relativeLuminance(first);
  const b = relativeLuminance(second);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}
