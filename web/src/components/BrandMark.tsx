import { type CSSProperties, type ReactElement, useId } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

// The brand mark (E-52, work order 072), unchanged from the design files: a
// master on a 64 grid and a small form on a 16 grid, both in currentColor.
import smallFormSvg from "../assets/brand/bildmarke-16.svg?raw";
import masterSvg from "../assets/brand/bildmarke.svg?raw";

/** Below this size (px) the master loses detail; the small form takes over. */
export const MASTER_MIN_SIZE = 24;

/** Size of the brand mark in the header (px): as tall as the line of the name. */
export const HEADER_BRAND_SIZE = 36;

/** Edge of the master grid; the visible mark spans 6…58 of it. */
const GRID = 64;
/** Units between the edge of the grid and the visible mark. */
const GRID_PADDING = 6;
/** Units between the visible mark and the name (lockup rule: 16 units). */
const NAME_DISTANCE = 16;

export type BrandForm = "master" | "small";

/** The form of the mark for a size in px: the small form below 24 px, else the master. */
export function brandForm(size: number): BrandForm {
  return size < MASTER_MIN_SIZE ? "small" : "master";
}

/**
 * Makes the ids inside the SVG (its mask) unique on the page, so that two
 * marks never point at each other's mask.
 */
export function withUniqueIds(svg: string, prefix: string): string {
  return svg.replace(/id="([\w-]+)"/g, `id="${prefix}-$1"`).replace(/url\(#([\w-]+)\)/g, `url(#${prefix}-$1)`);
}

/** Space (px) between the edge of the mark's box and the name for a mark of this size. */
export function nameGap(size: number): number {
  return ((NAME_DISTANCE - GRID_PADDING) * size) / GRID;
}

interface BrandMarkProps {
  /** Edge length of the mark in px. */
  readonly size?: number;
}

/**
 * Link to the start page with the brand mark and the name "2x" next to it.
 * The mark is decorative (aria-hidden); the visible name is the link's
 * accessible name. Its colour comes from the token "brand" (index.css).
 */
export function BrandMark({ size = HEADER_BRAND_SIZE }: BrandMarkProps): ReactElement {
  const { t } = useTranslation("common");
  const prefix = `brand${useId().replace(/[^\w-]/g, "")}`;
  const form = brandForm(size);
  const svg = withUniqueIds(form === "small" ? smallFormSvg : masterSvg, prefix);
  const markStyle: CSSProperties = { width: size, height: size };
  return (
    <Link to="/" className="inline-flex items-center" style={{ gap: nameGap(size) }}>
      <span
        aria-hidden="true"
        data-testid="brand-mark"
        data-form={form}
        className="inline-block shrink-0 text-brand [&>svg]:block [&>svg]:h-full [&>svg]:w-full"
        style={markStyle}
        // The SVG is a file of this repository (src/assets/brand), not user content.
        dangerouslySetInnerHTML={{ __html: svg }}
      />
      <span>{t("appTitle")}</span>
    </Link>
  );
}
