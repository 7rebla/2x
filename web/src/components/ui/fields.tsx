import type { ComponentPropsWithRef, ReactElement } from "react";

import { fieldClasses, textareaClasses, type ControlSize } from "./classes.ts";

/**
 * Text fields and choices of the interface (work order 077, README.md next to
 * this file). They have the height of a button of the same size, one border
 * and one error state: `invalid` sets aria-invalid, which colours the border.
 * The label, hint and error list stay with the caller (id, aria-describedby).
 * `className` is for layout only (width, alignment, number style).
 */
interface FieldOptions {
  /** "md" (36 px, default) or "sm" (28 px). Replaces the native size attribute. */
  readonly size?: ControlSize;
  /** The value was rejected: aria-invalid and a border in the error colour. */
  readonly invalid?: boolean;
}

/** Input types that are one-line text fields; check boxes, radio buttons and files keep their native look. */
export type TextInputType = "text" | "search" | "password" | "email" | "url" | "tel" | "number";

export type InputProps = Omit<ComponentPropsWithRef<"input">, "size" | "type" | "aria-invalid"> &
  FieldOptions & {
    /** "text" by default. */
    readonly type?: TextInputType;
  };

export function Input({ size = "md", invalid, type = "text", className, ...rest }: InputProps): ReactElement {
  return <input {...rest} type={type} aria-invalid={invalid} className={fieldClasses(size, className)} />;
}

export type SelectProps = Omit<ComponentPropsWithRef<"select">, "size" | "multiple" | "aria-invalid"> & FieldOptions;

/** A drop-down choice (one value). */
export function Select({ size = "md", invalid, className, children, ...rest }: SelectProps): ReactElement {
  return (
    <select {...rest} aria-invalid={invalid} className={fieldClasses(size, className)}>
      {children}
    </select>
  );
}

export type TextareaProps = Omit<ComponentPropsWithRef<"textarea">, "aria-invalid"> & {
  readonly invalid?: boolean;
};

/** A text area: border, padding and text of an md field; its height follows `rows`. */
export function Textarea({ invalid, className, ...rest }: TextareaProps): ReactElement {
  return <textarea {...rest} aria-invalid={invalid} className={textareaClasses(className)} />;
}
