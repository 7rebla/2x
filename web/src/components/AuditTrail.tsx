import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { type ReactElement, type ReactNode, useState } from "react";
import { useTranslation } from "react-i18next";

import { auditLogListOptions } from "../api/generated/@tanstack/react-query.gen.ts";
import type { AuditLogEntry, AuditLogListData } from "../api/generated";
import { ErrorMessage } from "./ErrorMessage.tsx";
import { Loading } from "./Loading.tsx";

// Change log entries as a table (GET /api/v1/audit-log/, only for "manage").
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
}

/**
 * Change log entries, newest first, one page of 50 at a time, with "previous"
 * and "next" like the API. A device or file page shows the history of its
 * object with `<AuditTrail objectType="assets.device" objectId={id} />`.
 * Changing a filter starts again on page 1.
 */
export function AuditTrail(props: AuditTrailProps): ReactElement {
  const filterKey = JSON.stringify([props.objectType ?? null, props.objectId ?? null, props.actor ?? null]);
  return <AuditTrailPages key={filterKey} {...props} />;
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

function AuditTrailPages(props: AuditTrailProps): ReactElement {
  const { t } = useTranslation("audit");
  const [page, setPage] = useState(1);
  const query = useQuery({
    ...auditLogListOptions({ query: queryFor(props, page) }),
    // Keep the shown page while the next one loads, so the table does not jump.
    placeholderData: keepPreviousData,
  });
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
      {results.length === 0 ? (
        <p data-testid="audit-empty" className="text-slate-600">
          {t("empty")}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table aria-label={props.label ?? t("tableLabel")} className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-slate-300">
                <th scope="col" className="p-2 font-semibold">
                  {t("column.timestamp")}
                </th>
                <th scope="col" className="p-2 font-semibold">
                  {t("column.actor")}
                </th>
                <th scope="col" className="p-2 font-semibold">
                  {t("column.action")}
                </th>
                <th scope="col" className="p-2 font-semibold">
                  {t("column.objectType")}
                </th>
                <th scope="col" className="p-2 font-semibold">
                  {t("column.object")}
                </th>
                <th scope="col" className="p-2 font-semibold">
                  {t("column.changes")}
                </th>
              </tr>
            </thead>
            <tbody>
              {results.map((entry) => (
                <AuditRow key={entry.id} entry={entry} />
              ))}
            </tbody>
          </table>
        </div>
      )}
      <nav aria-label={t("pagination.label")} className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          className="rounded border border-slate-300 px-3 py-1 disabled:opacity-50"
          disabled={busy || shownPage <= 1}
          onClick={() => {
            setPage(shownPage - 1);
          }}
        >
          {t("pagination.previous")}
        </button>
        <span data-testid="audit-page-status">{t("pagination.status", { page: shownPage, pages })}</span>
        <button
          type="button"
          className="rounded border border-slate-300 px-3 py-1 disabled:opacity-50"
          disabled={busy || next === null || next === undefined}
          onClick={() => {
            setPage(shownPage + 1);
          }}
        >
          {t("pagination.next")}
        </button>
        <span data-testid="audit-total" className="text-slate-600">
          {t("pagination.total", { count })}
        </span>
      </nav>
    </div>
  );
}

function AuditRow({ entry }: { entry: AuditLogEntry }): ReactElement {
  const { t } = useTranslation("audit");
  const objectType = auditObjectTypes.find((type) => type.value === entry.object_type);
  const action = isKnownAction(entry.action) ? t(`action.${entry.action}`) : entry.action;

  return (
    <tr data-testid="audit-entry" className="border-b border-slate-200 align-top">
      <td className="p-2 whitespace-nowrap" data-testid="audit-timestamp">
        <DateTime value={entry.timestamp} />
      </td>
      <td className="p-2" data-testid="audit-actor">
        {entry.actor ?? <span className="text-slate-600 italic">{t("noActor")}</span>}
      </td>
      <td className="p-2" data-testid="audit-action">
        {action}
      </td>
      <td className="p-2" data-testid="audit-object-type">
        {objectType === undefined ? entry.object_type : t(`objectType.${objectType.textKey}`)}
      </td>
      <td className="p-2" data-testid="audit-object">
        <span>{entry.object_repr}</span>
        {entry.object_id === null ? null : (
          <span className="block text-xs text-slate-600">{t("objectId", { id: entry.object_id })}</span>
        )}
      </td>
      <td className="p-2" data-testid="audit-changes">
        <Changes changes={entry.changes} />
      </td>
    </tr>
  );
}

function isKnownAction(action: string): action is "create" | "update" | "delete" {
  return action === "create" || action === "update" || action === "delete";
}

type FieldChange = AuditLogEntry["changes"][string];

function Changes({ changes }: { changes: AuditLogEntry["changes"] }): ReactElement {
  const { t } = useTranslation("audit");
  // A pair that is empty on both sides is no change worth showing: on create,
  // every field that was left empty appears as [null, ""].
  const shown = Object.entries(changes).filter(([, change]) => !isEmptyPair(change));
  if (shown.length === 0) {
    return <span className="text-slate-600">{t("noFieldChanges")}</span>;
  }
  return (
    <ul className="space-y-1">
      {shown.map(([field, change]) => (
        <li key={field} data-testid="audit-change">
          <code className="font-mono text-xs" data-testid="audit-change-field">
            {field}
          </code>
          {": "}
          <ChangeValue change={change} />
        </li>
      ))}
    </ul>
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

/** Times inside `changes` are UTC without a zone, for example "2026-11-21 22:09:19.347373". */
const UTC_WITHOUT_ZONE = /^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?)$/;

function Value({ value }: { value: unknown }): ReactNode {
  const { t } = useTranslation("audit");
  if (isEmptyValue(value)) {
    return <span className="text-slate-600 italic">{t("emptyValue")}</span>;
  }
  if (typeof value === "string") {
    const time = UTC_WITHOUT_ZONE.exec(value);
    if (time !== null) {
      return <DateTime value={`${time[1] ?? ""}T${time[2] ?? ""}Z`} title={value} />;
    }
    return value;
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
