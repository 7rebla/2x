/**
 * Classes of the shared controls (work order 077): buttons, text fields,
 * choices. Components use the building blocks in this folder (Button, Input,
 * Select, Textarea); these functions are exported for them and for tests.
 * Colours come only from the theme tokens (../../theme/README.md).
 */

/** The two control heights: md 36 px (default), sm 28 px. */
export type ControlSize = "md" | "sm";

/** Height of a control in CSS pixels, per size. */
export const CONTROL_HEIGHT_PX: Readonly<Record<ControlSize, number>> = { md: 36, sm: 28 };

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

export const buttonVariants: readonly ButtonVariant[] = ["primary", "secondary", "ghost", "danger"];

export const controlSizes: readonly ControlSize[] = ["md", "sm"];

/** Joins class names, leaving out empty parts. */
export function joinClasses(...parts: readonly (string | false | null | undefined)[]): string {
  return parts.filter((part): part is string => typeof part === "string" && part !== "").join(" ");
}

/** Disabled looks the same everywhere: half opacity and the "not allowed" cursor. */
export const DISABLED_CLASSES = "disabled:cursor-not-allowed disabled:opacity-50";

const BUTTON_BASE = `inline-flex items-center justify-center rounded border text-center ${DISABLED_CLASSES}`;

/*
 * Every variant has a border (transparent where none shows), so all variants
 * of one size have the same box. Hover only while enabled.
 */
const BUTTON_VARIANT: Readonly<Record<ButtonVariant, string>> = {
  primary: "border-transparent bg-accent text-on-accent enabled:hover:bg-accent-strong",
  secondary: "border-line-strong bg-surface text-fg enabled:hover:bg-surface-muted",
  ghost: "border-transparent bg-transparent text-fg enabled:hover:bg-surface-muted",
  danger: "border-danger bg-danger-soft text-danger enabled:hover:bg-danger-line",
};

/*
 * min-h keeps one line at exactly 36 or 28 px (line height plus padding plus
 * border stays below it) and lets a long label wrap instead of overflowing.
 */
const BUTTON_SIZE: Readonly<Record<ControlSize, string>> = {
  md: "min-h-9 gap-2 px-4 py-1 text-base",
  sm: "min-h-7 gap-1.5 px-2 py-0.5 text-sm",
};

/** Classes of a button; `extra` is for layout only (width, margin, alignment). */
export function buttonClasses(variant: ButtonVariant, size: ControlSize, extra?: string): string {
  return joinClasses(BUTTON_BASE, BUTTON_VARIANT[variant], BUTTON_SIZE[size], extra);
}

/** Border, surface and error state shared by text fields and choices. */
const FIELD_BASE = `rounded border border-line-strong bg-surface text-fg aria-[invalid=true]:border-danger ${DISABLED_CLASSES}`;

/** Fields always use 16 px text (md) so that phones do not zoom in on focus. */
const FIELD_SIZE: Readonly<Record<ControlSize, string>> = {
  md: "h-9 px-3 text-base",
  sm: "h-7 px-2 text-sm",
};

/** Classes of a one-line text field or a choice; `extra` is for layout only. */
export function fieldClasses(size: ControlSize, extra?: string): string {
  return joinClasses(FIELD_BASE, FIELD_SIZE[size], extra);
}

/** Classes of a text area: the border and text of an md field, the height from its rows. */
export function textareaClasses(extra?: string): string {
  return joinClasses(FIELD_BASE, "min-h-9 px-3 py-1.5 text-base", extra);
}
