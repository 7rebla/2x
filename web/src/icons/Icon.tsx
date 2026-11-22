import type { ReactElement } from "react";

import { glyphOf, type IconName } from "./names.ts";

/** The three sizes of the interface (icon-bedarfsanalyse.md, F1): text and tables, navigation and buttons, headings and nodes. */
export type IconSize = 16 | 20 | 24;

/** One stroke width for every icon: 2 units of the 24 grid (F3), about 1.33 px at 16 px. */
export const ICON_STROKE_WIDTH = 2;

/**
 * Every icon says whether it carries meaning. An icon next to a text that
 * says the same is decorative and hidden from assistive technology; an icon
 * without such a text needs a label. The type allows exactly one of both.
 */
export type IconMeaning =
  | { readonly decorative: true; readonly label?: never }
  | { readonly label: string; readonly decorative?: never };

export type IconProps = {
  readonly name: IconName;
  /** Pixels; 16 by default. */
  readonly size?: IconSize;
  /** Extra classes, e.g. a colour (`text-success`) or a margin. The colour comes from currentColor. */
  readonly className?: string;
} & IconMeaning;

/**
 * An icon of the interface, by name (names.ts). Outline in currentColor, so it
 * takes the colour of the text around it in light and dark mode.
 */
export function Icon({ name, size = 16, className, label }: IconProps): ReactElement {
  const Glyph = glyphOf(name);
  const meaning =
    label === undefined ? ({ "aria-hidden": true } as const) : ({ role: "img", "aria-label": label } as const);
  return (
    <Glyph
      size={size}
      strokeWidth={ICON_STROKE_WIDTH}
      focusable="false"
      data-icon={name}
      className={`inline-block shrink-0 align-middle${className === undefined ? "" : ` ${className}`}`}
      {...meaning}
    />
  );
}
