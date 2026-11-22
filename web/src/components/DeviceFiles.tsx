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
import { ResponsiveTable, type TableColumn } from "./ui/ResponsiveTable.tsx";

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
 * Below 768 px every file is a card (work order 081): the title as heading,
 * the download button next to it, the ingest state below, then the pairs and
 * the checksum.
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
  const columns: TableColumn<Document>[] = [
    {
      key: "title",
      header: t("columns.title"),
      headerClassName: "py-2 pr-4 font-normal",
      className: "min-w-48 py-2 pr-4",
      card: "title",
      cell: (item) => (
        <>
          <FileTitle item={item} />
          {item.latest_version === null ? null : <Checksum sha256={item.latest_version.sha256} />}
        </>
      ),
      cardCell: (item) => <FileTitle item={item} />,
    },
    {
      key: "kind",
      header: t("columns.kind"),
      headerClassName: "py-2 pr-4 font-normal",
      className: "py-2 pr-4",
      testId: "file-kind",
      cell: (item) => <KindLabel kind={item.kind} />,
    },
    {
      key: "version",
      header: t("columns.version"),
      headerClassName: "py-2 pr-4 font-normal whitespace-nowrap",
      className: "py-2 pr-4 whitespace-nowrap",
      testId: "file-version",
      cell: (item) => (
        <>
          <Icon name="version" className="mr-1 text-fg-muted" decorative />
          {item.latest_version?.number}
        </>
      ),
    },
    {
      key: "date",
      header: t("columns.date"),
      headerClassName: "py-2 pr-4 font-normal whitespace-nowrap",
      className: "py-2 pr-4 whitespace-nowrap",
      cell: (item) =>
        item.latest_version === null ? null : (
          <>
            <span data-testid="file-date" className="block">
              <DateTime iso={item.latest_version.created_at} />
            </span>
            <UploadedBy name={item.latest_version.uploaded_by} testId="file-user" />
          </>
        ),
    },
    {
      key: "size",
      header: t("columns.size"),
      headerClassName: "py-2 pr-4 font-normal whitespace-nowrap",
      className: "py-2 pr-4 whitespace-nowrap",
      testId: "file-size",
      cell: (item) => (item.latest_version === null ? null : <Size bytes={item.latest_version.size} />),
    },
    {
      key: "ingest",
      header: t("columns.ingest"),
      headerClassName: "py-2 pr-4 font-normal",
      className: "py-2 pr-4",
      testId: "file-ingest",
      card: "status",
      cell: (item) =>
        item.latest_version === null ? null : <IngestStatusBadge job={item.latest_version.ingest} compact />,
    },
    {
      key: "download",
      header: t("columns.download"),
      headerHidden: true,
      headerClassName: "py-2 font-normal",
      className: "py-2",
      card: "action",
      cell: (item) =>
        item.latest_version === null ? null : (
          <DownloadIconLink versionId={item.latest_version.id} number={item.latest_version.number} />
        ),
    },
    {
      // In the table the checksum stands below the title; on a card at the end.
      key: "checksum",
      header: t("columns.checksum"),
      table: false,
      card: "detail",
      cell: (item) => (item.latest_version === null ? null : <Checksum sha256={item.latest_version.sha256} />),
    },
  ];
  return (
    <ResponsiveTable
      label={t("listLabel")}
      testId="device-files-table"
      rows={documents}
      rowKey={(item) => item.id}
      columns={columns}
      rowAttributes={(item) => ({ "data-testid": "device-file", "data-document-id": item.id })}
      rowNote={(item) => (item.latest_version === null ? { from: "version", content: t("noVersion") } : null)}
      cardHeadingLevel={3}
      tableClassName="tabular-nums"
      headerRowClassName="border-b border-line text-fg-muted"
      rowClassName="border-b border-line align-top"
      noteClassName="py-2 text-fg-muted"
    />
  );
}

/** The title as a link to the file page; wraps at word boundaries, cut after two lines (079). */
function FileTitle({ item }: { item: Document }): ReactElement {
  return (
    <span data-testid="file-title" title={item.title} className="line-clamp-2 break-words">
      <Link to={documentPath(item.id)} className="text-accent underline hover:text-accent-strong">
        <Icon name="document" className="mr-1" decorative />
        {item.title}
      </Link>
    </span>
  );
}
