import { useQuery } from "@tanstack/react-query";
import type { ReactElement, ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import { ApiError } from "../api/errors.ts";
import type { DocumentDetail, DocumentVersion } from "../api/generated";
import { devicesRetrieveOptions, documentRetrieveOptions } from "../api/generated/@tanstack/react-query.gen.ts";
import { AuditTrail } from "../components/AuditTrail.tsx";
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
import { Icon } from "../icons/Icon.tsx";
import { useRole } from "../session.ts";
import { AnimatedHeading, MaskedTitle } from "../components/TextMotion.tsx";

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

function DocumentView({ document, error }: { document: DocumentDetail; error: unknown }): ReactElement {
  const { t } = useTranslation("files");
  const { canManage } = useRole();
  // The API lists the versions oldest first; the page shows the newest first.
  const versions = [...document.versions].sort((a, b) => b.number - a.number);

  return (
    <section className="space-y-4">
      <p className="text-sm text-fg-muted">
        <Icon name="document" className="mr-1" decorative />
        {t("document.heading")}
      </p>
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
        <h3 className="font-semibold">{t("document.versions")}</h3>
        {/* Configurations are not ingested (the API answers 400), so they get no button. */}
        <VersionTable versions={versions} canIngest={canManage && document.kind === "document"} />
        {canManage ? <NewVersionForm documentId={document.id} kind={document.kind} /> : null}
      </section>

      {/* The change log is readable for managers only (E-43). */}
      {canManage ? (
        <section className="space-y-3" data-testid="document-history">
          <h3 className="font-semibold">{t("document.history")}</h3>
          <AuditTrail objectType="files.document" objectId={document.id} label={t("document.history")} />
        </section>
      ) : null}
    </section>
  );
}

/*
 * Version table (work order 079): the user stands below the upload time, the
 * checksum below the file name; version, date, size and user never wrap. The
 * download is an icon button whose column has a heading for screen readers only.
 */
function VersionTable({
  versions,
  canIngest,
}: {
  versions: readonly DocumentVersion[];
  canIngest: boolean;
}): ReactElement {
  const { t } = useTranslation("files");
  return (
    // relative: the screen-reader texts (absolute) stay inside the scroll box.
    <div className="relative overflow-x-auto">
      <table aria-label={t("document.versionsLabel")} data-testid="document-versions" className="w-full text-left text-sm tabular-nums">
        <thead>
          <tr className="border-b border-line text-fg-muted">
            <th className="py-2 pr-4 font-normal whitespace-nowrap">{t("columns.version")}</th>
            <th className="py-2 pr-4 font-normal whitespace-nowrap">{t("columns.date")}</th>
            <th className="py-2 pr-4 font-normal whitespace-nowrap">{t("columns.size")}</th>
            <th className="py-2 pr-4 font-normal">{t("columns.filename")}</th>
            <th className="py-2 pr-4 font-normal">{t("columns.ingest")}</th>
            <th className="py-2 font-normal">
              <span className="sr-only">{t("columns.download")}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {versions.map((version) => (
            <tr key={version.id} data-testid="document-version" data-version={version.number} className="border-b border-line align-top">
              <td data-testid="version-number" className="py-2 pr-4 whitespace-nowrap">
                <Icon name="version" className="mr-1 text-fg-muted" decorative />
                {version.number}
              </td>
              <td className="py-2 pr-4 whitespace-nowrap">
                <span data-testid="version-date" className="block">
                  <DateTime iso={version.created_at} />
                </span>
                <UploadedBy name={version.uploaded_by} testId="version-user" />
              </td>
              <td data-testid="version-size" className="py-2 pr-4 whitespace-nowrap">
                <Size bytes={version.size} />
              </td>
              <td className="min-w-40 py-2 pr-4">
                <FileName name={version.original_filename} testId="version-filename" />
                <Checksum sha256={version.sha256} />
              </td>
              <td data-testid="version-ingest" className="min-w-48 space-y-1 py-2 pr-4">
                <IngestStatusBadge job={version.ingest} />
                <IngestError job={version.ingest} />
                {canIngest ? <IngestRetryButton version={version} /> : null}
              </td>
              <td className="py-2">
                <DownloadIconLink versionId={version.id} number={version.number} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
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
