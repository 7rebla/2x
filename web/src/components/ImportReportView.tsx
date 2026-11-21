import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";

import type { ImportCounts, ImportReport, ImportRowError } from "../api/generated";

/** The levels of the structure in the order the report shows them. */
export const importLevels = ["sites", "areas", "plants", "devices"] as const;
export type ImportLevel = (typeof importLevels)[number];

const countKinds = ["created", "updated", "unchanged"] as const satisfies readonly (keyof ImportCounts)[];

/**
 * Report of a device list import (dry run or saved): what was or would be
 * created, changed or left unchanged per level, and every error of the file
 * with line, column and message. Values from the file and messages of the API
 * are data; React renders them as text.
 */
export function ImportReportView({ report }: { report: ImportReport }): ReactElement {
  const { t } = useTranslation("import");
  const errorCount = report.errors.length;

  let summary: string;
  if (errorCount > 0) {
    summary = t("report.hasErrors", { count: errorCount });
  } else if (report.saved) {
    summary = t("report.saved", { count: report.rows });
  } else {
    summary = t("report.dryRun", { count: report.rows });
  }

  return (
    <div data-testid="import-report" className="space-y-4">
      <p
        data-testid="import-summary"
        className={errorCount > 0 ? "font-medium text-red-800" : report.saved ? "font-medium text-green-800" : ""}
      >
        {summary}
      </p>

      {errorCount > 0 ? (
        <ImportErrors errors={report.errors} />
      ) : (
        <table data-testid="import-counts" className="border-collapse text-sm">
          <caption className="mb-1 text-left font-medium">{t("report.countsCaption")}</caption>
          <thead>
            <tr>
              <th scope="col" className="border border-slate-300 px-2 py-1 text-left">
                {t("report.level")}
              </th>
              {countKinds.map((kind) => (
                <th key={kind} scope="col" className="border border-slate-300 px-2 py-1 text-right">
                  {t(`report.${kind}`)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {importLevels.map((level) => (
              <tr key={level} data-testid={`import-counts-${level}`}>
                <th scope="row" className="border border-slate-300 px-2 py-1 text-left font-normal">
                  {t(`report.${level}`)}
                </th>
                {countKinds.map((kind) => (
                  <td
                    key={kind}
                    data-testid={`import-count-${level}-${kind}`}
                    className="border border-slate-300 px-2 py-1 text-right tabular-nums"
                  >
                    {report[level][kind]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function ImportErrors({ errors }: { errors: readonly ImportRowError[] }): ReactElement {
  const { t } = useTranslation("import");
  return (
    <table data-testid="import-errors" className="w-full border-collapse text-sm">
      <caption className="mb-1 text-left font-medium">{t("errors.caption")}</caption>
      <thead>
        <tr>
          <th scope="col" className="border border-slate-300 px-2 py-1 text-right">
            {t("errors.line")}
          </th>
          <th scope="col" className="border border-slate-300 px-2 py-1 text-left">
            {t("errors.column")}
          </th>
          <th scope="col" className="border border-slate-300 px-2 py-1 text-left">
            {t("errors.message")}
          </th>
        </tr>
      </thead>
      <tbody>
        {errors.map((error, index) => (
          // The list is replaced as a whole, never reordered: the index is a stable key.
          <tr key={index} data-testid="import-error">
            <td data-testid="import-error-line" className="border border-slate-300 px-2 py-1 text-right tabular-nums">
              {error.line ?? t("errors.wholeFile")}
            </td>
            <td data-testid="import-error-column" className="border border-slate-300 px-2 py-1 font-mono">
              {error.column ?? t("errors.wholeRow")}
            </td>
            <td
              data-testid="import-error-message"
              className="border border-slate-300 px-2 py-1 break-words whitespace-pre-wrap"
            >
              {error.message}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
