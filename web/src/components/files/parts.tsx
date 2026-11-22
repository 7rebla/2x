// Small building blocks of the file views. File names, titles and user names
// are data: React renders them as text, they never go through i18next.
import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";

import type { KindEnum } from "../../api/generated";
import { Icon } from "../../icons/Icon.tsx";
import { downloadPath, formatDateTime, formatSize, shortChecksum } from "./format.ts";

/**
 * The checksum, shortened, as a quiet detail ("SHA-256 1a2b…"); a click on it
 * shows the whole value. No disclosure triangle: in a table it looked like an
 * error (work order 079). The full value is also the tooltip.
 */
export function Checksum({ sha256 }: { sha256: string }): ReactElement {
  const { t } = useTranslation("files");
  return (
    <details data-testid="checksum" className="text-xs text-fg-muted">
      <summary
        title={`${t("checksum.show")}: ${sha256}`}
        className="inline cursor-pointer list-none underline decoration-dotted underline-offset-2 hover:text-fg [&::-webkit-details-marker]:hidden"
      >
        <span>{t("checksum.label")} </span>
        <span data-testid="checksum-short" className="font-mono">
          {shortChecksum(sha256)}
        </span>
      </summary>
      <code data-testid="checksum-full" className="block font-mono break-all whitespace-normal text-fg">
        {sha256}
      </code>
    </details>
  );
}

/**
 * A file name that wraps at word boundaries (not inside words) and is cut
 * after two lines; the full name is the tooltip and stays the text content.
 */
export function FileName({ name, testId }: { name: string; testId?: string }): ReactElement {
  return (
    <span data-testid={testId} title={name} className="line-clamp-2 max-w-xs break-words">
      {name}
    </span>
  );
}

export function Size({ bytes }: { bytes: number }): ReactElement {
  const { i18n } = useTranslation();
  return <span title={String(bytes)}>{formatSize(bytes, i18n.resolvedLanguage)}</span>;
}

export function DateTime({ iso }: { iso: string }): ReactElement {
  const { i18n } = useTranslation();
  return <time dateTime={iso}>{formatDateTime(iso, i18n.resolvedLanguage)}</time>;
}

/** User name of an upload; null means the system. */
export function UserName({ name }: { name: string | null }): ReactElement {
  const { t } = useTranslation("files");
  return <>{name ?? t("system")}</>;
}

export function KindLabel({ kind }: { kind: KindEnum }): ReactElement {
  const { t } = useTranslation("files");
  return <>{t(`kind.${kind}`)}</>;
}

/** Plain link to the download of a version (the API sends it as an attachment). */
export function DownloadLink({ versionId, number }: { versionId: number; number: number }): ReactElement {
  const { t } = useTranslation("files");
  return (
    <a
      href={downloadPath(versionId)}
      aria-label={t("download.version", { number })}
      data-testid="download-link"
      className="whitespace-nowrap text-accent underline hover:text-accent-strong"
    >
      <Icon name="download" className="mr-1" decorative />
      {t("download.link")}
    </a>
  );
}

/**
 * The download of a version as a small icon button for tables: the icon
 * alone, the name ("Download version 2") in aria-label and tooltip. As high
 * as a small button (28 px, components/ui).
 */
export function DownloadIconLink({ versionId, number }: { versionId: number; number: number }): ReactElement {
  const { t } = useTranslation("files");
  const label = t("download.version", { number });
  return (
    <a
      href={downloadPath(versionId)}
      aria-label={label}
      title={label}
      data-testid="download-link"
      className="inline-flex size-7 items-center justify-center rounded border border-line-strong bg-surface text-accent hover:bg-surface-muted hover:text-accent-strong"
    >
      <Icon name="download" decorative />
    </a>
  );
}

/** A user name as a quiet detail line below the upload time, with "User:" for screen readers. */
export function UploadedBy({ name, testId }: { name: string | null; testId: string }): ReactElement {
  const { t } = useTranslation("files");
  return (
    <span className="block text-xs text-fg-muted">
      <Icon name="user" className="mr-1" decorative />
      <span className="sr-only">{t("columns.user")}: </span>
      <span data-testid={testId}>
        <UserName name={name} />
      </span>
    </span>
  );
}
