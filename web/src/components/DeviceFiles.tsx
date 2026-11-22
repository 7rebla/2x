import { useQuery } from "@tanstack/react-query";
import { type ReactElement, useId } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import type { Document } from "../api/generated";
import { deviceDocumentsListOptions } from "../api/generated/@tanstack/react-query.gen.ts";
import { Icon } from "../icons/Icon.tsx";
import { useRole } from "../session.ts";
import { ErrorMessage } from "./ErrorMessage.tsx";
import { documentPath } from "./files/format.ts";
import { IngestStatusBadge, ingestPollInterval } from "./files/IngestStatus.tsx";
import { Checksum, DateTime, DownloadIconLink, KindLabel, Size, UploadedBy } from "./files/parts.tsx";
import { NewDocumentForm } from "./files/UploadForm.tsx";
import { Loading } from "./Loading.tsx";

/**
 * Files of a device on the device page: each file with its newest version
 * (number, date and user, size, checksum) and a download button. Managers upload
 * new files here; new versions are uploaded on the page of the file.
 */
export function DeviceFiles({ deviceId }: { deviceId: number }): ReactElement {
  const { t } = useTranslation("files");
  const { canManage } = useRole();
  const headingId = useId();
  // While a newest version is queued or being ingested, the list asks again every few seconds.
  const query = useQuery({
    ...deviceDocumentsListOptions({ path: { device_id: deviceId } }),
    refetchInterval: (current) => ingestPollInterval(current.state.data?.map((item) => item.latest_version)),
  });

  return (
    <section
      aria-labelledby={headingId}
      data-testid="device-files"
      data-device-id={deviceId}
      className="space-y-3 rounded border border-line bg-surface p-4"
    >
      <h2 id={headingId} className="font-semibold">
        {t("heading")}
      </h2>
      {query.error === null ? null : <ErrorMessage error={query.error} />}
      {query.data === undefined ? (
        query.isError ? null : (
          <Loading />
        )
      ) : (
        <FileTable documents={query.data} />
      )}
      {canManage ? <NewDocumentForm deviceId={deviceId} /> : null}
    </section>
  );
}

/*
 * Seven columns (work order 079): the user stands below the upload time, the
 * checksum below the title; date, size, version and user never wrap. The
 * download is an icon button whose column has a heading for screen readers only.
 */
function FileTable({ documents }: { documents: readonly Document[] }): ReactElement {
  const { t } = useTranslation("files");
  if (documents.length === 0) {
    return (
      <p data-testid="device-files-empty" className="text-fg-muted">
        {t("empty")}
      </p>
    );
  }
  return (
    // relative: the screen-reader texts (absolute) stay inside the scroll box.
    <div className="relative overflow-x-auto">
      <table aria-label={t("listLabel")} data-testid="device-files-table" className="w-full text-left text-sm tabular-nums">
        <thead>
          <tr className="border-b border-line text-fg-muted">
            <th className="py-2 pr-4 font-normal">{t("columns.title")}</th>
            <th className="py-2 pr-4 font-normal">{t("columns.kind")}</th>
            <th className="py-2 pr-4 font-normal whitespace-nowrap">{t("columns.version")}</th>
            <th className="py-2 pr-4 font-normal whitespace-nowrap">{t("columns.date")}</th>
            <th className="py-2 pr-4 font-normal whitespace-nowrap">{t("columns.size")}</th>
            <th className="py-2 pr-4 font-normal">{t("columns.ingest")}</th>
            <th className="py-2 font-normal">
              <span className="sr-only">{t("columns.download")}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {documents.map((item) => (
            <FileRow key={item.id} item={item} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FileRow({ item }: { item: Document }): ReactElement {
  const { t } = useTranslation("files");
  const version = item.latest_version;
  return (
    <tr data-testid="device-file" data-document-id={item.id} className="border-b border-line align-top">
      <td className="min-w-48 py-2 pr-4">
        <span data-testid="file-title" title={item.title} className="line-clamp-2 break-words">
          <Link to={documentPath(item.id)} className="text-accent underline hover:text-accent-strong">
            <Icon name="document" className="mr-1" decorative />
            {item.title}
          </Link>
        </span>
        {version === null ? null : <Checksum sha256={version.sha256} />}
      </td>
      <td data-testid="file-kind" className="py-2 pr-4">
        <KindLabel kind={item.kind} />
      </td>
      {version === null ? (
        <td colSpan={5} className="py-2 text-fg-muted">
          {t("noVersion")}
        </td>
      ) : (
        <>
          <td data-testid="file-version" className="py-2 pr-4 whitespace-nowrap">
            <Icon name="version" className="mr-1 text-fg-muted" decorative />
            {version.number}
          </td>
          <td className="py-2 pr-4 whitespace-nowrap">
            <span data-testid="file-date" className="block">
              <DateTime iso={version.created_at} />
            </span>
            <UploadedBy name={version.uploaded_by} testId="file-user" />
          </td>
          <td data-testid="file-size" className="py-2 pr-4 whitespace-nowrap">
            <Size bytes={version.size} />
          </td>
          <td data-testid="file-ingest" className="py-2 pr-4">
            <IngestStatusBadge job={version.ingest} compact />
          </td>
          <td className="py-2">
            <DownloadIconLink versionId={version.id} number={version.number} />
          </td>
        </>
      )}
    </tr>
  );
}

