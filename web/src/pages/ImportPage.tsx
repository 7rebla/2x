import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type ReactElement, type SubmitEvent, useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { ApiError } from "../api/errors.ts";
import { devicesImportMutation } from "../api/generated/@tanstack/react-query.gen.ts";
import type { ImportReport } from "../api/generated";
import { ErrorMessage } from "../components/ErrorMessage.tsx";
import { ImportReportView } from "../components/ImportReportView.tsx";
import { reloadAfterSave, save } from "./structure/save.ts";

/** The 13 columns of the device list, in the order the first line must name them (E-44). */
export const deviceListColumns = [
  "site",
  "area",
  "plant_id",
  "plant_name",
  "device_id",
  "device_name",
  "manufacturer",
  "model",
  "software_version",
  "ip_address",
  "address_source",
  "protocols",
  "notes",
] as const;

/** What the last call to the import endpoint gave. */
type Outcome =
  /** 200: the report of a dry run or of saving (possibly with errors in the file). */
  | { readonly kind: "report"; readonly report: ImportReport }
  /** 400: the form was not accepted (for example no file); the messages of the API. */
  | { readonly kind: "invalid"; readonly messages: readonly string[] }
  /** 413: larger than the upload limit; the API names the limit in its message. */
  | { readonly kind: "too-large"; readonly detail: string | null }
  /** Anything else: no permission, no answer, server error … */
  | { readonly kind: "failed"; readonly error: unknown };

type Step = "check" | "save";

/**
 * Import of the device list (address /import, role "manage" only; the route
 * shows everybody else a notice instead of this page).
 *
 * Step 1: choose a CSV file and start a dry run (dry_run=true). Step 2: the
 * report shows what would be created or changed and every error with line
 * and column. Step 3: only a dry run without errors offers "Apply", which
 * sends the same file again with dry_run=false.
 */
export function ImportPage(): ReactElement {
  const { t } = useTranslation(["nav", "import"]);
  const queryClient = useQueryClient();
  const importDevices = useMutation(devicesImportMutation());
  const [file, setFile] = useState<File | null>(null);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [running, setRunning] = useState<Step | null>(null);
  const fileInputId = useId();

  async function run(step: Step, chosen: File): Promise<void> {
    setRunning(step);
    setOutcome(null);
    try {
      const result = await save((fetchFn) =>
        importDevices.mutateAsync({ body: { file: chosen, dry_run: step === "check" }, fetch: fetchFn }),
      );
      switch (result.kind) {
        case "saved":
          if (result.data.saved) {
            await reloadAfterSave(queryClient);
          }
          setOutcome({ kind: "report", report: result.data });
          break;
        case "invalid":
          setOutcome({ kind: "invalid", messages: Object.values(result.fieldErrors).flat() });
          break;
        case "failed":
          setOutcome(
            result.error instanceof ApiError && result.error.kind === "http" && result.error.status === 413
              ? { kind: "too-large", detail: result.error.detail }
              : { kind: "failed", error: result.error },
          );
          break;
      }
    } finally {
      setRunning(null);
    }
  }

  function check(event: SubmitEvent<HTMLFormElement>): void {
    event.preventDefault();
    if (file !== null && running === null) {
      void run("check", file);
    }
  }

  const report = outcome?.kind === "report" ? outcome.report : null;
  const canApply = report !== null && report.dry_run && !report.saved && report.errors.length === 0;

  return (
    <section className="space-y-6">
      <h2 className="text-2xl font-semibold">{t("nav:import")}</h2>
      <p className="text-slate-600">{t("import:intro")}</p>

      <section data-testid="import-format" className="space-y-2 rounded border border-slate-200 p-4 text-sm">
        <h3 className="font-semibold">{t("import:format.heading")}</h3>
        <p>{t("import:format.header")}</p>
        <code data-testid="import-columns" className="block font-mono break-words">
          {deviceListColumns.join(",")}
        </code>
        <ul className="list-disc space-y-1 pl-5">
          <li>{t("import:format.encoding")}</li>
          <li>{t("import:format.matching")}</li>
          <li>{t("import:format.plantRow")}</li>
          <li>{t("import:format.allOrNothing")}</li>
        </ul>
      </section>

      <form data-testid="import-form" onSubmit={check} className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1 text-sm">
          <label htmlFor={fileInputId}>{t("import:file.label")}</label>
          <input
            id={fileInputId}
            data-testid="import-file"
            type="file"
            accept=".csv,text/csv"
            disabled={running !== null}
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null);
              setOutcome(null);
            }}
          />
        </div>
        <button
          type="submit"
          data-testid="import-check"
          disabled={file === null || running !== null}
          className="rounded bg-slate-800 px-3 py-1 text-white disabled:opacity-50"
        >
          {running === "check" ? t("import:file.checking") : t("import:file.check")}
        </button>
      </form>

      {outcome === null ? null : (
        <section aria-labelledby={`${fileInputId}-result`} className="space-y-4">
          <h3 id={`${fileInputId}-result`} className="text-lg font-semibold">
            {t("import:report.heading")}
          </h3>
          <OutcomeView outcome={outcome} />
          {report === null ? null : <NextStep report={report} />}
          {canApply ? (
            <button
              type="button"
              data-testid="import-apply"
              disabled={file === null || running !== null}
              className="rounded bg-green-700 px-3 py-1 text-white disabled:opacity-50"
              onClick={() => {
                if (file !== null && running === null) {
                  void run("save", file);
                }
              }}
            >
              {running === "save" ? t("import:file.saving") : t("import:file.save")}
            </button>
          ) : null}
        </section>
      )}
    </section>
  );
}

function OutcomeView({ outcome }: { outcome: Outcome }): ReactElement {
  const { t } = useTranslation("import");
  switch (outcome.kind) {
    case "report":
      return <ImportReportView report={outcome.report} />;
    case "invalid":
      return (
        <div
          role="alert"
          data-testid="import-invalid"
          className="space-y-1 rounded border border-red-300 bg-red-50 p-4 text-red-800"
        >
          <p>{t("problem.invalid")}</p>
          {outcome.messages.length === 0 ? null : (
            <ul className="list-disc pl-5 text-sm">
              {outcome.messages.map((message, index) => (
                // Messages of one answer, shown once and never reordered.
                <li key={index} data-testid="import-invalid-message">
                  {message}
                </li>
              ))}
            </ul>
          )}
        </div>
      );
    case "too-large":
      return (
        <div
          role="alert"
          data-testid="import-too-large"
          className="space-y-1 rounded border border-red-300 bg-red-50 p-4 text-red-800"
        >
          <p>{t("problem.tooLarge")}</p>
          {outcome.detail === null ? null : (
            <p data-testid="import-too-large-detail" className="text-sm">
              {outcome.detail}
            </p>
          )}
        </div>
      );
    case "failed":
      return <ErrorMessage error={outcome.error} />;
  }
}

/** What to do after the report: correct the file, apply the dry run, or look at the result. */
function NextStep({ report }: { report: ImportReport }): ReactElement | null {
  const { t } = useTranslation("import");
  if (report.errors.length > 0) {
    return <p data-testid="import-next">{t("report.fixAndRetry")}</p>;
  }
  if (report.saved) {
    return (
      <p data-testid="import-next">
        <Link to="/" className="text-blue-700 underline">
          {t("report.toStructure")}
        </Link>
      </p>
    );
  }
  return <p data-testid="import-next">{t("report.readyToSave")}</p>;
}
