import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { type ReactElement, type ReactNode, useState } from "react";
import { useTranslation } from "react-i18next";

import { auditLogListOptions } from "../api/generated/@tanstack/react-query.gen.ts";
import type { AuditLogEntry, AuditLogListData } from "../api/generated";
import { ErrorMessage } from "./ErrorMessage.tsx";
import { shortChecksum } from "./files/format.ts";
import { Loading } from "./Loading.tsx";
import { type CountReport, ResultCount, useReportCount, useResultCount } from "./ResultCount.tsx";
import { Button } from "./ui/Button.tsx";
import { ResponsiveTable, type TableColumn } from "./ui/ResponsiveTable.tsx";

// Change log entries as a table (GET /api/v1/audit-log/, only for "manage"),
// below 768 px as stacked cards (work order 081).
//
// Everything in an entry (user names, object names, field values) is data:
// it is rendered as text by React, never as HTML, and never goes through the
// interpolation of i18next.

/** Entries per page; fixed by the API (work order 028). */
export const AUDIT_PAGE_SIZE = 50;

/** The object types the change log knows (E-43), as the API names them, with their text key. */
export const auditObjectTypes = [
  { value: "assets.site", textKey: "site" },
  { value: "assets.area", textKey: "area" },
  { value: "assets.plant", textKey: "plant" },
  { value: "assets.device", textKey: "device" },
  { value: "files.document", textKey: "document" },
  { value: "files.documentversion", textKey: "documentVersion" },
  { value: "accounts.user", textKey: "user" },
] as const;

export type AuditObjectType = (typeof auditObjectTypes)[number]["value"];

export interface AuditTrailProps {
  /** Only entries of this object type, for example "assets.device". */
  objectType?: string;
  /** Only entries of the object with this id (use together with objectType). */
  objectId?: number;
  /** Only entries of the user with this exact user name. */
  actor?: string;
  /** Accessible name of the table; default: the "Changes" text. */
  label?: string;
  /**
   * Level of the card headings below 768 px: one below the heading of the
   * section around the change log; default 2 (the page /audit has only its h1 above).
   */
  cardHeadingLevel?: 2 | 3 | 4;
}

/**
 * Change log entries, newest first, one page of 50 at a time, with "previous"
 * and "next" like the API. A device or file page shows the history of its
 * object with `<AuditTrail objectType="assets.device" objectId={id} />`.
 * Changing a filter starts again on page 1.
 */
export function AuditTrail(props: AuditTrailProps): ReactElement {
  const { t } = useTranslation("audit");
  const filterKey = JSON.stringify([props.objectType ?? null, props.objectId ?? null, props.actor ?? null]);
  // The number of entries stays outside the pages, which a new filter mounts
  // afresh: the live region remains and announces the new number (work order 089).
  const [count, reportCount] = useResultCount(filterKey);
  return (
    <div className="space-y-3">
      <ResultCount
        count={count}
        text={(entries) => t("resultCount", { count: entries })}
        empty={t("empty")}
        testId="audit-result-count"
        countTestId="audit-total"
        emptyTestId="audit-empty"
      />
      <AuditTrailPages key={filterKey} {...props} filterKey={filterKey} reportCount={reportCount} />
    </div>
  );
}

function queryFor(props: AuditTrailProps, page: number): NonNullable<AuditLogListData["query"]> {
  const query: NonNullable<AuditLogListData["query"]> = {};
  if (props.objectType !== undefined) {
    query.object_type = props.objectType;
  }
  if (props.objectId !== undefined) {
    query.object_id = props.objectId;
  }
  if (props.actor !== undefined) {
    query.actor = props.actor;
  }
  if (page > 1) {
    query.page = page;
  }
  return query;
}

function AuditTrailPages(
  props: AuditTrailProps & { filterKey: string; reportCount: (report: CountReport) => void },
): ReactElement {
  const { t } = useTranslation("audit");
  const [page, setPage] = useState(1);
  const query = useQuery({
    ...auditLogListOptions({ query: queryFor(props, page) }),
    // Keep the shown page while the next one loads, so the table does not jump.
    placeholderData: keepPreviousData,
  });
  // The number of entries goes to the live region of AuditTrail.
  useReportCount(props.filterKey, query.data?.count, props.reportCount);
  // The page whose entries are shown: while the next page loads, the table
  // (and the page number) still show the previous one.
  const [shownPage, setShownPage] = useState(page);
  if (query.isSuccess && !query.isPlaceholderData && shownPage !== page) {
    setShownPage(page);
  }

  if (query.isPending) {
    return <Loading />;
  }
  if (query.isError) {
    return <ErrorMessage error={query.error} />;
  }

  const { count, results, next } = query.data;
  const pages = Math.max(1, Math.ceil(count / AUDIT_PAGE_SIZE));
  const busy = query.isPlaceholderData;

  return (
    <div data-testid="audit-trail" className="space-y-3" aria-busy={busy}>
      {/* No entries: the result count above says so. */}
      {results.length === 0 ? null : (
        <AuditTable
          entries={results}
          label={props.label ?? t("tableLabel")}
          cardHeadingLevel={props.cardHeadingLevel ?? 2}
        />
      )}
      <nav aria-label={t("pagination.label")} className="flex flex-wrap items-center gap-3">
        <Button
          type="button"
          icon="previous"
          disabled={busy || shownPage <= 1}
          onClick={() => {
            setPage(shownPage - 1);
          }}
        >
          {t("pagination.previous")}
        </Button>
        <span data-testid="audit-page-status">{t("pagination.status", { page: shownPage, pages })}</span>
        <Button
          type="button"
          icon="next"
          iconPosition="end"
          disabled={busy || next === null || next === undefined}
          onClick={() => {
            setPage(shownPage + 1);
          }}
        >
          {t("pagination.next")}
        </Button>
      </nav>
    </div>
  );
}

/**
 * The entries as a table from 768 px; below that every entry is a card (work
 * order 081): the object as heading, the action below it, then time, user,
 * object type and the changes over the full width.
 */
function AuditTable({
  entries,
  label,
  cardHeadingLevel,
}: {
  entries: readonly AuditLogEntry[];
  label: string;
  cardHeadingLevel: 2 | 3 | 4;
}): ReactElement {
  const { t } = useTranslation("audit");
  const columns: TableColumn<AuditLogEntry>[] = [
    {
      key: "timestamp",
      header: t("column.timestamp"),
      headerClassName: "p-2 font-semibold",
      className: "p-2 whitespace-nowrap",
      testId: "audit-timestamp",
      cell: (entry) => <DateTime value={entry.timestamp} />,
    },
    {
      key: "actor",
      header: t("column.actor"),
      headerClassName: "p-2 font-semibold",
      className: "p-2 whitespace-nowrap",
      testId: "audit-actor",
      cell: (entry) => entry.actor ?? <span className="text-fg-muted italic">{t("noActor")}</span>,
    },
    {
      key: "action",
      header: t("column.action"),
      headerClassName: "p-2 font-semibold",
      className: "p-2 whitespace-nowrap",
      testId: "audit-action",
      card: "status",
      cell: (entry) => (isKnownAction(entry.action) ? t(`action.${entry.action}`) : entry.action),
    },
    {
      key: "objectType",
      header: t("column.objectType"),
      headerClassName: "p-2 font-semibold",
      className: "p-2 whitespace-nowrap",
      testId: "audit-object-type",
      cell: (entry) => {
        const objectType = auditObjectTypes.find((type) => type.value === entry.object_type);
        return objectType === undefined ? entry.object_type : t(`objectType.${objectType.textKey}`);
      },
    },
    {
      key: "object",
      header: t("column.object"),
      headerClassName: "p-2 font-semibold",
      className: "min-w-40 p-2 break-words",
      testId: "audit-object",
      card: "title",
      cell: (entry) => (
        <>
          <span>{entry.object_repr}</span>
          {entry.object_id === null ? null : (
            <span className="block text-xs font-normal whitespace-nowrap text-fg-muted">
              {t("objectId", { id: entry.object_id })}
            </span>
          )}
        </>
      ),
    },
    {
      key: "changes",
      header: t("column.changes"),
      headerClassName: "p-2 font-semibold",
      className: "min-w-64 p-2",
      testId: "audit-changes",
      card: "wide",
      cell: (entry) => <Changes changes={entry.changes} />,
    },
  ];
  return (
    <ResponsiveTable
      label={label}
      rows={entries}
      rowKey={(entry) => entry.id}
      columns={columns}
      rowAttributes={() => ({ "data-testid": "audit-entry" })}
      cardHeadingLevel={cardHeadingLevel}
      tableClassName="border-collapse tabular-nums"
      headerRowClassName="border-b border-line"
      rowClassName="border-b border-line align-top"
    />
  );
}

function isKnownAction(action: string): action is "create" | "update" | "delete" {
  return action === "create" || action === "update" || action === "delete";
}

type FieldChange = AuditLogEntry["changes"][string];

/**
 * The fields of the logged models (backend/twox/accounts/audit.py) that have a
 * label of their own in audit.json ("field"). Another field shows its name as
 * the API sends it.
 */
export const auditFieldNames = [
  "id",
  "name",
  "key",
  "title",
  "kind",
  "notes",
  "site",
  "area",
  "plant",
  "device",
  "device_class",
  "manufacturer",
  "model",
  "software_version",
  "ip_address",
  "address_source",
  "protocols",
  "document",
  "number",
  "original_filename",
  "size",
  "content_type",
  "blob_key",
  "sha256",
  "uploaded_by",
  "created_by",
  "created_at",
  "updated_at",
  "username",
  "first_name",
  "last_name",
  "email",
  "is_active",
  "is_staff",
  "is_superuser",
  "date_joined",
  "groups",
] as const;

type AuditFieldName = (typeof auditFieldNames)[number];

/**
 * Technical fields (work order 079): the id, storage key and checksum of an
 * object and the ids of the objects it points to. They are folded away under
 * "Technical details" by default, next to the raw data of the entry.
 */
export const TECHNICAL_AUDIT_FIELDS: ReadonlySet<string> = new Set<AuditFieldName>([
  "id",
  "blob_key",
  "sha256",
  "site",
  "area",
  "plant",
  "device",
  "document",
  "uploaded_by",
  "created_by",
]);

function isAuditFieldName(field: string): field is AuditFieldName {
  return (auditFieldNames as readonly string[]).includes(field);
}

/**
 * The changed fields: the ones a person reads first in a list, the technical
 * ones and the raw data of the entry (`changes` exactly as the API sent it,
 * also the pairs left out above) folded away under "Technical details".
 */
function Changes({ changes }: { changes: AuditLogEntry["changes"] }): ReactElement {
  const { t } = useTranslation("audit");
  const all = Object.entries(changes);
  // A pair that is empty on both sides is no change worth showing: on create,
  // every field that was left empty appears as [null, ""].
  const shown = all.filter(([, change]) => !isEmptyPair(change));
  const plain = shown.filter(([field]) => !TECHNICAL_AUDIT_FIELDS.has(field));
  const technical = shown.filter(([field]) => TECHNICAL_AUDIT_FIELDS.has(field));

  return (
    <div className="space-y-1">
      {plain.length > 0 ? (
        <ChangeList entries={plain} testId="audit-change-list" />
      ) : technical.length === 0 ? (
        <span data-testid="audit-no-changes" className="text-fg-muted">
          {t("noFieldChanges")}
        </span>
      ) : null}
      {all.length === 0 ? null : (
        <details data-testid="audit-technical" className="text-xs">
          <summary className="cursor-pointer text-fg-muted">{t("technical")}</summary>
          <div className="mt-1 space-y-2">
            {technical.length === 0 ? null : <ChangeList entries={technical} testId="audit-technical-list" />}
            <div>
              <p className="text-fg-muted">{t("raw")}</p>
              <pre
                data-testid="audit-raw"
                className="font-mono text-xs whitespace-pre-wrap text-fg-muted [overflow-wrap:anywhere]"
              >
                {rawJson(changes)}
              </pre>
            </div>
          </div>
        </details>
      )}
    </div>
  );
}

/** The changes as JSON with one field per line, values complete and compact. */
export function rawJson(changes: AuditLogEntry["changes"]): string {
  const lines = Object.entries(changes).map(([field, change]) => `  ${JSON.stringify(field)}: ${JSON.stringify(change)}`);
  return lines.length === 0 ? "{}" : `{\n${lines.join(",\n")}\n}`;
}

function ChangeList({ entries, testId }: { entries: [string, FieldChange][]; testId: string }): ReactElement {
  return (
    <ul className="space-y-1 [overflow-wrap:anywhere]" data-testid={testId}>
      {entries.map(([field, change]) => (
        <li key={field} data-testid="audit-change">
          <FieldLabel field={field} />
          {": "}
          <ChangeValue change={change} />
        </li>
      ))}
    </ul>
  );
}

/** The translated name of a known field (its API name as tooltip), else the name as it came. */
function FieldLabel({ field }: { field: string }): ReactElement {
  const { t } = useTranslation("audit");
  if (isAuditFieldName(field)) {
    return (
      <span className="font-semibold" title={field} data-testid="audit-change-field" data-field={field}>
        {t(`field.${field}`)}
      </span>
    );
  }
  return (
    <code className="font-sans text-xs tabular-nums slashed-zero" data-testid="audit-change-field" data-field={field}>
      {field}
    </code>
  );
}

function isEmptyValue(value: unknown): boolean {
  return value === null || value === undefined || value === "";
}

function isEmptyPair(change: FieldChange): boolean {
  return Array.isArray(change) && isEmptyValue(change[0]) && isEmptyValue(change[1]);
}

function ChangeValue({ change }: { change: FieldChange }): ReactElement {
  const { t } = useTranslation("audit");
  if (Array.isArray(change)) {
    return (
      <>
        <span data-testid="audit-change-old">
          <Value value={change[0]} />
        </span>
        {" → "}
        <span data-testid="audit-change-new">
          <Value value={change[1]} />
        </span>
      </>
    );
  }
  if (isMembershipChange(change)) {
    // Groups of a user (the role): which groups were added or removed.
    return (
      <>
        <span data-testid="audit-change-operation">{t(`membership.${change.operation}`)}</span>{" "}
        <span data-testid="audit-change-objects">{change.objects.join(", ")}</span>
      </>
    );
  }
  // A shape this page does not know: show it as it came, as text.
  return <span>{JSON.stringify(change)}</span>;
}

function isMembershipChange(value: unknown): value is { operation: "add" | "delete"; objects: string[] } {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    record.type === "m2m" &&
    (record.operation === "add" || record.operation === "delete") &&
    Array.isArray(record.objects) &&
    record.objects.every((item) => typeof item === "string")
  );
}

/** A run of 32 or more hex digits: a checksum or a key made from one. */
const HASH = /[0-9a-f]{32,}/gi;

/**
 * The text with every hash cut to its first characters like the checksums of
 * the file table ("1a2b3c4d5e6f…"); other text stays as it is.
 */
export function shortenHashes(text: string): string {
  return text.replace(HASH, (hash) => shortChecksum(hash));
}

/** Times inside `changes` are UTC without a zone, for example "2026-11-21 22:09:19.347373". */
const UTC_WITHOUT_ZONE = /^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?)$/;

function Value({ value }: { value: unknown }): ReactNode {
  const { t } = useTranslation("audit");
  if (isEmptyValue(value)) {
    return <span className="text-fg-muted italic">{t("emptyValue")}</span>;
  }
  if (typeof value === "string") {
    const time = UTC_WITHOUT_ZONE.exec(value);
    if (time !== null) {
      return <DateTime value={`${time[1] ?? ""}T${time[2] ?? ""}Z`} title={value} />;
    }
    const short = shortenHashes(value);
    return short === value ? value : <span title={value}>{short}</span>;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

/**
 * A point in time in the shown language and the browser's time zone. A value
 * that is not a valid time is shown as it came.
 */
function DateTime({ value, title }: { value: string; title?: string }): ReactNode {
  const { i18n } = useTranslation("audit");
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return title ?? value;
  }
  const text = new Intl.DateTimeFormat(i18n.resolvedLanguage, { dateStyle: "medium", timeStyle: "medium" }).format(
    date,
  );
  return (
    <time dateTime={date.toISOString()} title={title}>
      {text}
    </time>
  );
}
