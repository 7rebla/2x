import { useQuery } from "@tanstack/react-query";
import type { ReactElement, ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import { ApiError } from "../api/errors.ts";
import type { Device, DocumentDetail, DocumentVersion } from "../api/generated";
import { devicesRetrieveOptions, documentRetrieveOptions } from "../api/generated/@tanstack/react-query.gen.ts";
import { AuditTrail } from "../components/AuditTrail.tsx";
import { Breadcrumb, type Crumb, useDeviceCrumbs } from "../components/Breadcrumb.tsx";
import { ErrorMessage } from "../components/ErrorMessage.tsx";
import { devicePath, parseId } from "../components/files/format.ts";
import {
  IngestError,
  IngestRetryButton,
  IngestStatusBadge,
  ingestPollInterval,
} from "../components/files/IngestStatus.tsx";
import {
  Checksum,
  DateTime,
  DownloadIconLink,
  FileName,
  KindLabel,
  Size,
  UploadedBy,
  UserName,
} from "../components/files/parts.tsx";
import { NewVersionForm } from "../components/files/UploadForm.tsx";
import { Loading } from "../components/Loading.tsx";
import { NotFound } from "../components/NotFound.tsx";
import { ResponsiveTable, type TableColumn } from "../components/ui/ResponsiveTable.tsx";
import { Icon } from "../icons/Icon.tsx";
import { useRole } from "../session.ts";
import { AnimatedHeading, MaskedTitle } from "../components/TextMotion.tsx";
import { usePageTitle } from "../hooks/usePageTitle.ts";

/** One file with all its versions (address /documents/:documentId). */
export function DocumentPage(): ReactElement {
  const { documentId } = useParams();
  const id = parseId(documentId);
  if (id === null) {
    return <NotFound />;
  }
  // The key starts a fresh page (empty upload form) for another file.
  return <DocumentDetails key={id} id={id} />;
}

function DocumentDetails({ id }: { id: number }): ReactElement {
  const { t } = useTranslation("files");
  // While a version is queued or being ingested, the page asks again every few seconds.
  const query = useQuery({
    ...documentRetrieveOptions({ path: { document_id: id } }),
    refetchInterval: (current) => ingestPollInterval(current.state.data?.versions),
  });
  // The browser title names the file once it is loaded; an unknown file leaves it to NotFound.
  usePageTitle(
    query.data?.title ?? (query.error instanceof ApiError && query.error.status === 404 ? null : t("document.heading")),
  );

  if (query.data !== undefined) {
    return <DocumentView document={query.data} error={query.error} />;
  }
  if (query.error instanceof ApiError && query.error.kind === "http" && query.error.status === 404) {
    return <NotFound />;
  }
  return (
    <section className="space-y-4">
      <AnimatedHeading text={t("document.heading")} />
      {query.isError ? <ErrorMessage error={query.error} /> : <Loading />}
    </section>
  );
}

/** Name and key of the device of the file; its id until the device is loaded. */
function DeviceLink({ deviceId }: { deviceId: number }): ReactElement {
  const { t } = useTranslation("files");
  const query = useQuery(devicesRetrieveOptions({ path: { id: deviceId } }));
  return (
    <Link to={devicePath(deviceId)} className="text-accent underline hover:text-accent-strong">
      <Icon name="device" className="mr-1" decorative />
      {query.data === undefined ? (
        t("document.deviceFallback", { id: deviceId })
      ) : (
        <>
          {query.data.name} <span className="tabular-nums slashed-zero">({query.data.key})</span>
        </>
      )}
    </Link>
  );
}

/** The file as the last level of the breadcrumb. */
function fileCrumb(document: DocumentDetail): Crumb {
  return { key: "document", icon: "document", label: document.title, testId: "breadcrumb-document" };
}

/**
 * Where the file sits (work order 089): Structure › site › area › plant ›
 * device › file, like the breadcrumb of the device page, with the device as a
 * link. Until the device is loaded (or if it cannot be), the device stands
 * there by its id.
 */
function DocumentBreadcrumb({ document }: { document: DocumentDetail }): ReactElement {
  const { t } = useTranslation(["files", "nav"]);
  const query = useQuery(devicesRetrieveOptions({ path: { id: document.device } }));
  if (query.data !== undefined) {
    return <DeviceDocumentBreadcrumb device={query.data} document={document} />;
  }
  const crumbs: Crumb[] = [
    { key: "structure", icon: "structure", label: t("nav:structure"), to: "/" },
    {
      key: "device",
      icon: "device",
      label: t("files:document.deviceFallback", { id: document.device }),
      to: devicePath(document.device),
      testId: "breadcrumb-device",
    },
    fileCrumb(document),
  ];
  return <Breadcrumb label={t("files:document.breadcrumb")} testId="document-breadcrumb" crumbs={crumbs} />;
}

function DeviceDocumentBreadcrumb({ device, document }: { device: Device; document: DocumentDetail }): ReactElement {
  const { t } = useTranslation("files");
  const crumbs = [...useDeviceCrumbs(device), fileCrumb(document)];
  return <Breadcrumb label={t("document.breadcrumb")} testId="document-breadcrumb" crumbs={crumbs} />;
}

function DocumentView({ document, error }: { document: DocumentDetail; error: unknown }): ReactElement {
  const { t } = useTranslation("files");
  const { canManage } = useRole();
  // The API lists the versions oldest first; the page shows the newest first.
  const versions = [...document.versions].sort((a, b) => b.number - a.number);

  return (
    <section className="space-y-4">
      <DocumentBreadcrumb document={document} />
      <MaskedTitle text={document.title} className="text-2xl font-semibold break-words" testId="document-title" />

      {/* A failed reload keeps the last data on screen and says so. */}
      {error === null ? null : <ErrorMessage error={error} />}

      <dl
        aria-label={t("document.detailsLabel")}
        className="grid grid-cols-1 gap-x-6 gap-y-2 rounded border border-line bg-surface p-4 sm:grid-cols-[max-content_1fr]"
      >
        <Field label={t("document.device")} testId="document-device">
          <DeviceLink deviceId={document.device} />
        </Field>
        <Field label={t("columns.kind")} testId="document-kind">
          <KindLabel kind={document.kind} />
        </Field>
        <Field label={t("document.created")} testId="document-created">
          <DateTime iso={document.created_at} />
        </Field>
        <Field label={t("document.createdBy")} testId="document-created-by">
          <UserName name={document.created_by} />
        </Field>
      </dl>

      <section className="space-y-3 rounded border border-line bg-surface p-4">
        <h2 className="font-semibold">{t("document.versions")}</h2>
        {/* Configurations are not ingested (the API answers 400), so they get no button. */}
        <VersionTable versions={versions} canIngest={canManage && document.kind === "document"} />
        {canManage ? <NewVersionForm documentId={document.id} kind={document.kind} /> : null}
      </section>

      {/* The change log is readable for managers only (E-43). */}
      {canManage ? (
        <section className="space-y-3" data-testid="document-history">
          <h2 className="font-semibold">{t("document.history")}</h2>
          <AuditTrail
            objectType="files.document"
            objectId={document.id}
            label={t("document.history")}
            cardHeadingLevel={3}
          />
        </section>
      ) : null}
    </section>
  );
}

/*
 * Version table (work order 079): the user stands below the upload time, the
 * checksum below the file name; version, date, size and user never wrap. The
 * download is an icon button whose column has a heading for screen readers only.
 * Below 768 px every version is a card (work order 081): "Version N" as
 * heading, the download button next to it, the ingest state below, then the
 * pairs and the checksum.
 */
function VersionTable({
  versions,
  canIngest,
}: {
  versions: readonly DocumentVersion[];
  canIngest: boolean;
}): ReactElement {
  const { t } = useTranslation("files");
  const columns: TableColumn<DocumentVersion>[] = [
    {
      key: "version",
      header: t("columns.version"),
      headerClassName: "py-2 pr-4 font-normal whitespace-nowrap",
      className: "py-2 pr-4 whitespace-nowrap",
      testId: "version-number",
      card: "title",
      cell: (version) => (
        <>
          <Icon name="version" className="mr-1 text-fg-muted" decorative />
          {version.number}
        </>
      ),
      // On a card the number alone would be a poor heading: "Version 3".
      cardCell: (version) => (
        <>
          <Icon name="version" className="mr-1 text-fg-muted" decorative />
          {t("versionNumber", { number: version.number })}
        </>
      ),
    },
    {
      key: "date",
      header: t("columns.date"),
      headerClassName: "py-2 pr-4 font-normal whitespace-nowrap",
      className: "py-2 pr-4 whitespace-nowrap",
      cell: (version) => (
        <>
          <span data-testid="version-date" className="block">
            <DateTime iso={version.created_at} />
          </span>
          <UploadedBy name={version.uploaded_by} testId="version-user" />
        </>
      ),
    },
    {
      key: "size",
      header: t("columns.size"),
      headerClassName: "py-2 pr-4 font-normal whitespace-nowrap",
      className: "py-2 pr-4 whitespace-nowrap",
      testId: "version-size",
      cell: (version) => <Size bytes={version.size} />,
    },
    {
      key: "filename",
      header: t("columns.filename"),
      headerClassName: "py-2 pr-4 font-normal",
      className: "min-w-40 py-2 pr-4",
      cell: (version) => (
        <>
          <FileName name={version.original_filename} testId="version-filename" />
          <Checksum sha256={version.sha256} />
        </>
      ),
      cardCell: (version) => <FileName name={version.original_filename} testId="version-filename" />,
    },
    {
      key: "ingest",
      header: t("columns.ingest"),
      headerClassName: "py-2 pr-4 font-normal",
      className: "min-w-48 space-y-1 py-2 pr-4",
      testId: "version-ingest",
      card: "status",
      cell: (version) => (
        <>
          <IngestStatusBadge job={version.ingest} />
          <IngestError job={version.ingest} />
          {canIngest ? <IngestRetryButton version={version} /> : null}
        </>
      ),
    },
    {
      key: "download",
      header: t("columns.download"),
      headerHidden: true,
      headerClassName: "py-2 font-normal",
      className: "py-2",
      card: "action",
      cell: (version) => <DownloadIconLink versionId={version.id} number={version.number} />,
    },
    {
      // In the table the checksum stands below the file name; on a card at the end.
      key: "checksum",
      header: t("columns.checksum"),
      table: false,
      card: "detail",
      cell: (version) => <Checksum sha256={version.sha256} />,
    },
  ];
  return (
    <ResponsiveTable
      label={t("document.versionsLabel")}
      testId="document-versions"
      rows={versions}
      rowKey={(version) => version.id}
      columns={columns}
      rowAttributes={(version) => ({ "data-testid": "document-version", "data-version": version.number })}
      cardHeadingLevel={3}
      tableClassName="tabular-nums"
      headerRowClassName="border-b border-line text-fg-muted"
      rowClassName="border-b border-line align-top"
    />
  );
}

function Field({ label, testId, children }: { label: string; testId: string; children: ReactNode }): ReactElement {
  return (
    <>
      <dt className="text-fg-muted">{label}</dt>
      <dd data-testid={testId} className="break-words">
        {children}
      </dd>
    </>
  );
}
