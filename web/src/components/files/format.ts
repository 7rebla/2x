// Formatting helpers of the file views: sizes, dates, checksums, addresses.

/** Units for formatSize, decimal (1 kB = 1000 bytes) like the upload limit (200 000 000 bytes = 200 MB). */
const SIZE_UNITS = ["byte", "kilobyte", "megabyte", "gigabyte", "terabyte"] as const;

/** A size in bytes as text in the given language, for example "1.5 MB" or "1,5 MB". */
export function formatSize(bytes: number, locale: string | undefined): string {
  let value = bytes;
  let unit = 0;
  while (Math.abs(value) >= 1000 && unit < SIZE_UNITS.length - 1) {
    value /= 1000;
    unit += 1;
  }
  return new Intl.NumberFormat(locale, {
    style: "unit",
    unit: SIZE_UNITS[unit],
    unitDisplay: "short",
    maximumFractionDigits: unit === 0 ? 0 : 1,
  }).format(value);
}

/** A point in time (ISO text from the API) as date and time in the given language and the browser's time zone. */
export function formatDateTime(iso: string, locale: string | undefined): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(iso));
}

/** Characters of the checksum shown before it is expanded. */
export const SHORT_CHECKSUM_LENGTH = 12;

/** The start of a checksum, for the collapsed view. */
export function shortChecksum(sha256: string): string {
  return sha256.length <= SHORT_CHECKSUM_LENGTH ? sha256 : `${sha256.slice(0, SHORT_CHECKSUM_LENGTH)}…`;
}

/**
 * Address of the download of a version. A plain link: the API answers with
 * Content-Disposition: attachment and the session cookie goes along.
 */
export function downloadPath(versionId: number): string {
  return `/api/v1/document-versions/${String(versionId)}/download/`;
}

/** Address of the page of a file. */
export function documentPath(documentId: number): string {
  return `/documents/${String(documentId)}`;
}

/** Address of the page of a device. */
export function devicePath(deviceId: number): string {
  return `/devices/${String(deviceId)}`;
}

/** The id from the address, or null if it cannot be an id (then the page is NotFound). */
export function parseId(raw: string | undefined): number | null {
  if (raw === undefined || !/^[1-9][0-9]{0,15}$/.test(raw)) {
    return null;
  }
  const id = Number(raw);
  return Number.isSafeInteger(id) ? id : null;
}

/**
 * The limit in bytes from the API's 413 message ("… the limit of 200000000
 * bytes."), or null if the message names none. The number is the only one in
 * the message in every language.
 */
export function limitFromMessage(detail: string | null): number | null {
  if (detail === null) {
    return null;
  }
  const match = /(\d+)/.exec(detail);
  if (match?.[1] === undefined) {
    return null;
  }
  const limit = Number(match[1]);
  return Number.isSafeInteger(limit) && limit > 0 ? limit : null;
}
