// Small building blocks of the file views. File names, titles and user names
// are data: React renders them as text, they never go through i18next.
import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";

import type { KindEnum } from "../../api/generated";
import { Icon } from "../../icons/Icon.tsx";
import { downloadPath, formatDateTime, formatSize, shortChecksum } from "./format.ts";

/** The checksum, shortened; a click on it shows the whole value. */
export function Checksum({ sha256 }: { sha256: string }): ReactElement {
  const { t } = useTranslation("files");
  return (
    <details data-testid="checksum" className="font-mono text-sm">
      <summary title={t("checksum.show")} data-testid="checksum-short" className="cursor-pointer">
        {shortChecksum(sha256)}
      </summary>
      <code data-testid="checksum-full" className="block break-all">
        {sha256}
      </code>
    </details>
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
