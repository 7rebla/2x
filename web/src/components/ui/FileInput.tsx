import { type ComponentPropsWithoutRef, type DragEvent, type ReactElement, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Icon } from "../../icons/Icon.tsx";
import { fileButtonClasses, fileDropClasses } from "./classes.ts";

/** Secondary text; full text colour while a file is dragged over the soft accent (theme/contrast.test.ts measures fg there). */
const MUTED = "text-fg-muted group-data-[dragging=true]:text-fg";

export type FileInputProps =Omit<
  ComponentPropsWithoutRef<"input">,
  "type" | "value" | "defaultValue" | "multiple" | "onChange" | "aria-invalid" | "className" | "size"
> & {
  /** The id the caller's <label htmlFor> points to; the native input carries it. */
  readonly id: string;
  /** The chosen file as the caller keeps it; its name is shown next to the button. */
  readonly file: File | null;
  /** Called with the chosen or dropped file (null if the choice was cleared). */
  readonly onFileChange: (file: File | null) => void;
  /** The value was rejected: aria-invalid and a border in the error colour. */
  readonly invalid?: boolean;
  /** Layout only (width, margin). */
  readonly className?: string;
};

/**
 * File chooser of the interface (work order 088, README.md next to this file).
 *
 * The native <input type="file"> stays in the page, visually hidden but
 * focusable: the caller's label names it, keyboard and screen readers use it
 * as usual, and form data and tests (setInputFiles) reach it. What shows is a
 * secondary button ("Choose file…") with the focus ring of the hidden input,
 * the chosen file name, and a frame a file can be dropped on.
 */
export function FileInput({
  id,
  file,
  onFileChange,
  invalid,
  disabled = false,
  className,
  ...rest
}: FileInputProps): ReactElement {
  const { t } = useTranslation("common");
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function onDragOver(event: DragEvent<HTMLDivElement>): void {
    if (disabled) {
      return;
    }
    // Allows the drop (the browser would otherwise open the file).
    event.preventDefault();
    setDragging(true);
  }

  function onDrop(event: DragEvent<HTMLDivElement>): void {
    if (disabled) {
      return;
    }
    event.preventDefault();
    setDragging(false);
    const dropped = event.dataTransfer.files;
    const first = dropped[0];
    if (first === undefined) {
      return;
    }
    // Put the file into the native input as well, so the form data holds it.
    // Environments without a settable file list (jsdom) keep only the callback.
    if (input.current !== null) {
      try {
        input.current.files = dropped;
      } catch {
        // Not settable here; the caller still gets the file.
      }
    }
    onFileChange(first);
  }

  return (
    <div
      data-dragging={dragging ? "true" : undefined}
      onDragOver={onDragOver}
      onDragLeave={() => {
        setDragging(false);
      }}
      onDrop={onDrop}
      className={fileDropClasses(dragging, className)}
    >
      <input
        {...rest}
        ref={input}
        id={id}
        type="file"
        disabled={disabled}
        aria-invalid={invalid}
        onChange={(event) => {
          onFileChange(event.target.files?.[0] ?? null);
        }}
        className="peer sr-only"
      />
      {/* The hidden input is the control; this only shows it and opens it for the mouse. */}
      <span
        aria-hidden="true"
        onClick={() => {
          if (!disabled) {
            input.current?.click();
          }
        }}
        className={fileButtonClasses()}
      >
        <Icon name="document" size={20} decorative />
        {t("fileInput.choose")}
      </span>
      <span data-testid="file-input-name" className="min-w-0 flex-1 truncate" title={file?.name}>
        {file === null ? <span className={MUTED}>{t("fileInput.none")}</span> : file.name}
      </span>
      {disabled ? null : (
        <span aria-hidden="true" className={`hidden text-sm sm:inline ${MUTED}`}>
          {t("fileInput.drop")}
        </span>
      )}
    </div>
  );
}
