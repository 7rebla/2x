import type { ComponentPropsWithRef, ReactElement } from "react";

import { Icon } from "../../icons/Icon.tsx";
import type { IconName } from "../../icons/names.ts";
import { buttonClasses, type ButtonVariant, type ControlSize } from "./classes.ts";

export type ButtonProps = Omit<ComponentPropsWithRef<"button">, "type"> & {
  /** Required, so that no button submits a form by accident. */
  readonly type: "button" | "submit" | "reset";
  /** "secondary" by default. */
  readonly variant?: ButtonVariant;
  /** "md" (36 px, default) or "sm" (28 px). */
  readonly size?: ControlSize;
  /** A decorative icon next to the label (20 px in md, 16 px in sm). */
  readonly icon?: IconName;
  /** Where the icon stands; "start" by default ("end" for "next"). */
  readonly iconPosition?: "start" | "end";
  /**
   * The action is running: the button is disabled, says so with aria-busy and
   * shows the turning loading icon in place of its icon. The label is the
   * caller's (for example "Saving…").
   */
  readonly loading?: boolean;
};

/**
 * The button of the interface (work order 077, README.md next to this file).
 * `className` is for layout only (width, margin, alignment); colours, height
 * and padding come from the variant and the size.
 */
export function Button({
  type,
  variant = "secondary",
  size = "md",
  icon,
  iconPosition = "start",
  loading = false,
  disabled = false,
  className,
  children,
  ...rest
}: ButtonProps): ReactElement {
  const iconSize = size === "md" ? 20 : 16;
  const shownIcon: IconName | undefined = loading ? "loading" : icon;
  const iconElement =
    shownIcon === undefined ? null : (
      <Icon name={shownIcon} size={iconSize} className={loading ? "animate-spin" : undefined} decorative />
    );
  // The loading icon always stands at the start, where the eye looks first.
  const atStart = loading || iconPosition === "start";
  return (
    <button
      {...rest}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading ? true : undefined}
      className={buttonClasses(variant, size, className)}
    >
      {atStart ? iconElement : null}
      {children}
      {atStart ? null : iconElement}
    </button>
  );
}
