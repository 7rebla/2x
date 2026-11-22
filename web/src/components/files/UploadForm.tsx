// Upload forms (only for the role "manage"; the API checks it as well):
// a new file of a device and a new version of a file. React 19 form actions,
// no form library. The answer of the API is shown under the form: the new
// version with other places of the same content, a 409 (same content as the
// newest version), a 413 (larger than the limit), field errors of a 400.
import { useQueryClient } from "@tanstack/react-query";
import { type ReactElement, type ReactNode, useActionState, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import type { Duplicate, KindEnum } from "../../api/generated";
import { Icon } from "../../icons/Icon.tsx";
import { reloadAfterSave } from "../../pages/structure/save.ts";
import { ErrorMessage } from "../ErrorMessage.tsx";
import { Button } from "../ui/Button.tsx";
import { Input, Select } from "../ui/fields.tsx";
import { FileInput } from "../ui/FileInput.tsx";
import { devicePath, documentPath, formatDateTime, formatSize } from "./format.ts";
import { DownloadLink } from "./parts.tsx";
import { type UploadOutcome, uploadDocument, uploadVersion } from "./upload.ts";

/** Form fields that show their errors at the field; other keys appear above the fields. */
type UploadField = "file" | "title" | "kind";

interface UploadState {
  /** Answer of the last upload; null before the first one. */
  readonly outcome: UploadOutcome | null;
  /** The form was sent without a file (checked before calling the API). */
  readonly noFile: boolean;
  /** Title as last sent; kept after an error, empty after an upload. */
  readonly title: string;
  /** Counts submissions; the fields are rebuilt for each one (React resets form fields after an action). */
  readonly attempt: number;
}

const initialState: UploadState = { outcome: null, noFile: false, title: "", attempt: 0 };

/** The chosen file, or null if the form holds none. */
function chosenFile(formData: FormData): File | null {
  const value = formData.get("file");
  return value instanceof File && value.name !== "" ? value : null;
}

interface UploadAction {
  readonly state: UploadState;
  readonly action: (formData: FormData) => void;
  readonly pending: boolean;
  /** The file chosen or dropped in the file field; null until one is chosen and after each submission. */
  readonly file: File | null;
  /** Change handler of the file field: remembers the chosen file. */
  readonly onFileChange: (file: File | null) => void;
}

function useUploadAction(send: (formData: FormData, file: File) => Promise<UploadOutcome>): UploadAction {
  const queryClient = useQueryClient();
  // The file as chosen in the field. The form data holds it as well; this is
  // the fallback for environments whose FormData does not see a file set by
  // script or dropped (jsdom in the tests). The state drives the display and
  // the submit button, the ref is what the action reads.
  const [file, setFile] = useState<File | null>(null);
  const chosen = useRef<File | null>(null);
  const onFileChange = (next: File | null): void => {
    chosen.current = next;
    setFile(next);
  };
  const [state, action, pending] = useActionState<UploadState, FormData>(async (previous, formData) => {
    const attempt = previous.attempt + 1;
    const titleValue = formData.get("title");
    const title = typeof titleValue === "string" ? titleValue : "";
    const sent = chosenFile(formData) ?? chosen.current;
    // The fields are rebuilt empty after every submission (see UploadState.attempt).
    chosen.current = null;
    setFile(null);
    // The submit button waits for a file; this guards a submission by other means.
    if (sent === null) {
      return { outcome: null, noFile: true, title, attempt };
    }
    const outcome = await send(formData, sent);
    if (outcome.kind === "uploaded") {
      await reloadAfterSave(queryClient);
      return { outcome, noFile: false, title: "", attempt };
    }
    return { outcome, noFile: false, title, attempt };
  }, initialState);
  return { state, action, pending, file, onFileChange };
}

function fieldErrors(state: UploadState, field: UploadField): readonly string[] {
  return state.outcome?.kind === "invalid" ? (state.outcome.fieldErrors[field] ?? []) : [];
}

function FieldFrame({
  label,
  name,
  errors,
  hint,
  children,
}: {
  label: string;
  name: UploadField;
  errors: readonly string[];
  hint?: ReactNode;
  children: (props: { id: string; invalid: boolean; describedBy: string | undefined }) => ReactNode;
}): ReactElement {
  const id = useId();
  const errorId = `${id}-error`;
  const hintId = `${id}-hint`;
  const invalid = errors.length > 0;
  const describedBy = [invalid ? errorId : null, hint === undefined ? null : hintId].filter((item) => item !== null);
  return (
    <div className="space-y-1">
      <label htmlFor={id} className="block text-sm text-fg-muted">
        {label}
      </label>
      {children({ id, invalid, describedBy: describedBy.length > 0 ? describedBy.join(" ") : undefined })}
      {hint === undefined ? null : (
        <p id={hintId} className="text-sm text-fg-muted">
          {hint}
        </p>
      )}
      {invalid ? (
        <ul id={errorId} data-testid={`upload-error-${name}`} className="text-sm text-danger">
          {errors.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function FileField({ upload }: { upload: UploadAction }): ReactElement {
  const { t } = useTranslation("files");
  const { state } = upload;
  const errors = state.noFile ? [t("upload.noFile")] : fieldErrors(state, "file");
  return (
    <FieldFrame label={t("upload.file")} name="file" errors={errors}>
      {({ id, invalid, describedBy }) => (
        <FileInput
          id={id}
          name="file"
          file={upload.file}
          onFileChange={upload.onFileChange}
          invalid={invalid}
          aria-describedby={describedBy}
          className="w-full"
        />
      )}
    </FieldFrame>
  );
}

/** Where else the same content is stored, with links to the device and the file. */
export function DuplicateList({ duplicates }: { duplicates: readonly Duplicate[] }): ReactElement {
  const { t } = useTranslation("files");
  return (
    <div data-testid="upload-duplicates" className="space-y-1">
      <p>{t("upload.duplicates")}</p>
      <ul className="list-disc pl-5">
        {duplicates.map((item) => (
          <li key={item.version} data-testid="upload-duplicate">
            <Link to={devicePath(item.device)} className="text-accent underline hover:text-accent-strong">
              {item.device_name}
            </Link>{" "}
            <span className="tabular-nums slashed-zero">({item.device_key})</span>
            {": "}
            <Link to={documentPath(item.document)} className="text-accent underline hover:text-accent-strong">
              {item.document_title}
            </Link>
            {", "}
            {t("upload.duplicateEntry", { number: item.version_number })}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** The answer of the last upload, above the fields. */
function OutcomeMessage({
  state,
  knownFields,
  configurationDocument,
}: {
  state: UploadState;
  knownFields: readonly UploadField[];
  configurationDocument: boolean;
}): ReactElement | null {
  const { t, i18n } = useTranslation("files");
  const outcome = state.outcome;
  if (outcome === null) {
    return null;
  }
  switch (outcome.kind) {
    case "uploaded":
      return (
        <div role="status" data-testid="upload-success" className="space-y-1 rounded border border-success-line bg-success-soft p-3 text-success">
          <p>
            <Icon name="success" className="mr-2" decorative />
            {t("upload.uploaded", { number: outcome.result.version.number })}
          </p>
          {outcome.result.duplicates.length > 0 ? <DuplicateList duplicates={outcome.result.duplicates} /> : null}
        </div>
      );
    case "sameAsLatest":
      return (
        <div role="alert" data-testid="upload-same-content" className="space-y-1 rounded border border-warning-line bg-warning-soft p-3 text-warning">
          <p>
            <Icon name="warning" className="mr-2" decorative />
            {t("upload.sameAsLatest", { number: outcome.existing.number })}
          </p>
          <p className="text-sm">
            {t("upload.sameAsLatestFrom", {
              number: outcome.existing.number,
              date: formatDateTime(outcome.existing.created_at, i18n.resolvedLanguage),
            })}{" "}
            <DownloadLink versionId={outcome.existing.id} number={outcome.existing.number} />
          </p>
        </div>
      );
    case "tooLarge":
      return (
        <div role="alert" data-testid="upload-too-large" className="rounded border border-danger-line bg-danger-soft p-3 text-danger">
          <Icon name="error" className="mr-2" decorative />
          {outcome.limitBytes === null
            ? t("upload.tooLargeUnknown")
            : t("upload.tooLarge", { limit: formatSize(outcome.limitBytes, i18n.resolvedLanguage) })}
        </div>
      );
    case "invalid": {
      const known = new Set<string>(knownFields);
      const otherErrors = Object.entries(outcome.fieldErrors)
        .filter(([field]) => !known.has(field))
        .flatMap(([, list]) => list);
      // A configuration is rejected at the field "kind" (new file) or as a whole
      // (new version of a configuration stored on another way, work order 029).
      const configuration =
        "kind" in outcome.fieldErrors || (configurationDocument && "non_field_errors" in outcome.fieldErrors);
      return (
        <div role="alert" data-testid="upload-invalid" className="space-y-1 rounded border border-danger-line bg-danger-soft p-3 text-danger">
          <p>
            <Icon name="error" className="mr-2" decorative />
            {t("upload.invalid")}
          </p>
          {configuration ? <p data-testid="upload-configuration-rejected">{t("upload.configurationRejected")}</p> : null}
          {otherErrors.length > 0 ? (
            <ul className="list-disc pl-5 text-sm" aria-label={t("upload.otherErrors")}>
              {otherErrors.map((message) => (
                <li key={message}>{message}</li>
              ))}
            </ul>
          ) : null}
        </div>
      );
    }
    case "failed":
      return <ErrorMessage error={outcome.error} />;
  }
}

function UploadShell({
  title,
  testId,
  upload,
  knownFields,
  configurationDocument = false,
  children,
}: {
  title: string;
  testId: string;
  upload: UploadAction;
  knownFields: readonly UploadField[];
  configurationDocument?: boolean;
  children: ReactNode;
}): ReactElement {
  const { t } = useTranslation(["files", "common"]);
  const titleId = useId();
  const hintId = useId();
  const { state, action, pending, file } = upload;
  const waitsForFile = file === null && !pending;
  return (
    <form
      action={action}
      noValidate
      aria-labelledby={titleId}
      aria-busy={pending}
      data-testid={testId}
      className="space-y-3 rounded border border-line bg-surface p-4"
    >
      <h4 id={titleId} className="font-semibold">
        {title}
      </h4>
      <OutcomeMessage state={state} knownFields={knownFields} configurationDocument={configurationDocument} />
      {/* Fresh fields per submission, see UploadState.attempt. */}
      <div key={state.attempt} className="space-y-3">
        {children}
      </div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <Button
          type="submit"
          variant="primary"
          icon="upload"
          loading={pending}
          disabled={waitsForFile}
          aria-describedby={waitsForFile ? hintId : undefined}
        >
          {pending ? t("upload.submitting") : t("upload.submit")}
        </Button>
        {waitsForFile ? (
          <p id={hintId} data-testid="upload-choose-first" className="text-sm text-fg-muted">
            {t("common:fileInput.chooseFirst")}
          </p>
        ) : null}
      </div>
    </form>
  );
}

const NEW_DOCUMENT_FIELDS: readonly UploadField[] = ["file", "title", "kind"];

/** Upload of a new file (version 1) of the device. */
export function NewDocumentForm({ deviceId }: { deviceId: number }): ReactElement {
  const { t } = useTranslation("files");
  const upload = useUploadAction((formData, file) => {
    const title = formData.get("title");
    const kind: KindEnum = formData.get("kind") === "configuration" ? "configuration" : "document";
    return uploadDocument(deviceId, { file, title: typeof title === "string" ? title : "", kind });
  });
  return (
    <UploadShell
      title={t("upload.newDocument")}
      testId="upload-document-form"
      upload={upload}
      knownFields={NEW_DOCUMENT_FIELDS}
    >
      <FileField upload={upload} />
      <FieldFrame label={t("upload.title")} name="title" errors={fieldErrors(upload.state, "title")} hint={t("upload.titleHint")}>
        {({ id, invalid, describedBy }) => (
          <Input
            id={id}
            name="title"
            type="text"
            autoComplete="off"
            maxLength={255}
            defaultValue={upload.state.title}
            invalid={invalid}
            aria-describedby={describedBy}
            className="w-full"
          />
        )}
      </FieldFrame>
      <FieldFrame
        label={t("upload.kind")}
        name="kind"
        errors={fieldErrors(upload.state, "kind")}
        hint={<span data-testid="upload-configuration-hint">{t("upload.configurationHint")}</span>}
      >
        {({ id, invalid, describedBy }) => (
          <Select
            id={id}
            name="kind"
            defaultValue="document"
            invalid={invalid}
            aria-describedby={describedBy}
            className="w-full"
          >
            <option value="document">{t("kind.document")}</option>
            {/* Shown but not selectable: configurations follow with redaction in M5 (E-42). */}
            <option value="configuration" disabled>
              {t("upload.configurationLocked")}
            </option>
          </Select>
        )}
      </FieldFrame>
    </UploadShell>
  );
}

const NEW_VERSION_FIELDS: readonly UploadField[] = ["file"];

/** Upload of a new version of the file. */
export function NewVersionForm({ documentId, kind }: { documentId: number; kind: KindEnum }): ReactElement {
  const { t } = useTranslation("files");
  const upload = useUploadAction((_formData, file) => uploadVersion(documentId, file));
  return (
    <UploadShell
      title={t("upload.newVersion")}
      testId="upload-version-form"
      upload={upload}
      knownFields={NEW_VERSION_FIELDS}
      configurationDocument={kind === "configuration"}
    >
      <FileField upload={upload} />
    </UploadShell>
  );
}
