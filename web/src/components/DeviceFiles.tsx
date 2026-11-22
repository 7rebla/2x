import { useQuery } from "@tanstack/react-query";
import { type ReactElement, useId } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import type { Document } from "../api/generated";
import { deviceDocumentsListOptions } from "../api/generated/@tanstack/react-query.gen.ts";
import { useRole } from "../session.ts";
import { ErrorMessage } from "./ErrorMessage.tsx";
import { documentPath } from "./files/format.ts";
import { Checksum, DateTime, DownloadLink, KindLabel, Size, UserName } from "./files/parts.tsx";
import { NewDocumentForm } from "./files/UploadForm.tsx";
import { Loading } from "./Loading.tsx";

/**
 * Files of a device on the device page: each file with its newest version
 * (number, date, size, user, checksum) and a download link. Managers upload
 * new files here; new versions are uploaded on the page of the file.
 */
export function DeviceFiles({ deviceId }: { deviceId: number }): ReactElement {
  const { t } = useTranslation("files");
  const { canManage } = useRole();
  const headingId = useId();
  const query = useQuery(deviceDocumentsListOptions({ path: { device_id: deviceId } }));

  return (
    <section
      aria-labelledby={headingId}
      data-testid="device-files"
      data-device-id={deviceId}
      className="space-y-3 rounded border border-line bg-surface p-4"
    >
      <h3 id={headingId} className="font-semibold">
        {t("heading")}
      </h3>
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
    <div className="overflow-x-auto">
      <table aria-label={t("listLabel")} data-testid="device-files-table" className="w-full text-left text-sm tabular-nums">
        <thead>
          <tr className="border-b border-line text-fg-muted">
            <th className="py-2 pr-4 font-normal">{t("columns.title")}</th>
            <th className="py-2 pr-4 font-normal">{t("columns.kind")}</th>
            <th className="py-2 pr-4 font-normal">{t("columns.version")}</th>
            <th className="py-2 pr-4 font-normal">{t("columns.date")}</th>
            <th className="py-2 pr-4 font-normal">{t("columns.size")}</th>
            <th className="py-2 pr-4 font-normal">{t("columns.user")}</th>
            <th className="py-2 pr-4 font-normal">{t("columns.checksum")}</th>
            <th className="py-2 font-normal">{t("columns.download")}</th>
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
      <td data-testid="file-title" className="py-2 pr-4 break-words">
        <Link to={documentPath(item.id)} className="text-accent underline hover:text-accent-strong">
          {item.title}
        </Link>
      </td>
      <td data-testid="file-kind" className="py-2 pr-4">
        <KindLabel kind={item.kind} />
      </td>
      {version === null ? (
        <td colSpan={6} className="py-2 text-fg-muted">
          {t("noVersion")}
        </td>
      ) : (
        <>
          <td data-testid="file-version" className="py-2 pr-4">
            {version.number}
          </td>
          <td data-testid="file-date" className="py-2 pr-4">
            <DateTime iso={version.created_at} />
          </td>
          <td data-testid="file-size" className="py-2 pr-4">
            <Size bytes={version.size} />
          </td>
          <td data-testid="file-user" className="py-2 pr-4">
            <UserName name={version.uploaded_by} />
          </td>
          <td className="py-2 pr-4">
            <Checksum sha256={version.sha256} />
          </td>
          <td className="py-2">
            <DownloadLink versionId={version.id} number={version.number} />
          </td>
        </>
      )}
    </tr>
  );
}
