// The contract every icon drawing fulfils, whether it comes from Lucide or is
// one of the project's own drawings (device classes, work order 074). Icon.tsx
// renders any of them the same way.
import type { ComponentType, ReactElement, ReactNode, SVGProps } from "react";

/** Properties Icon.tsx passes to a drawing; the rest are plain SVG attributes (aria-*, role, className). */
export interface GlyphProps extends Omit<SVGProps<SVGSVGElement>, "ref" | "children"> {
  /** Width and height in pixels. */
  readonly size: number;
  /** Stroke width in units of the 24 × 24 grid; it scales with the size. */
  readonly strokeWidth: number;
}

/** A drawing that Icon.tsx can render: a Lucide icon or an own one built on SvgGlyph. */
export type Glyph = ComponentType<GlyphProps>;

/**
 * Frame for the project's own icons, with the same rules as Lucide
 * (docs/design/icon-bedarfsanalyse.md, part F): view box 0 0 24 24, no fill,
 * stroke in currentColor with round caps and joins. An own icon passes only
 * its shapes as children, without colours:
 *
 *   export function PlcGlyph(props: GlyphProps): ReactElement {
 *     return <SvgGlyph {...props}><rect x="4" y="3" width="16" height="18" rx="2" /></SvgGlyph>;
 *   }
 */
export function SvgGlyph({ size, strokeWidth, children, ...rest }: GlyphProps & { readonly children: ReactNode }): ReactElement {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...rest}
    >
      {children}
    </svg>
  );
}
