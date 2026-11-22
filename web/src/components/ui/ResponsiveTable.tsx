// A data table that becomes a list of stacked cards on narrow screens (work
// order 081, decision E-65 (2)). From 768 px (Tailwind `md`) it is a real
// <table>; below that every row is a list item with a heading, its status and
// the other columns as label/value pairs. Only one of the two is in the page,
// so screen readers meet either a table or a list, never both.
import { type HTMLAttributes, type ReactElement, type ReactNode, useSyncExternalStore } from "react";

import { joinClasses } from "./classes.ts";

/** The width from which a responsive table is a table: Tailwind's `md` (48rem, 768 px). */
export const WIDE_TABLE_QUERY = "(min-width: 48rem)";

function subscribe(onChange: () => void): () => void {
  try {
    if (typeof window.matchMedia !== "function") {
      return () => undefined;
    }
    const list = window.matchMedia(WIDE_TABLE_QUERY);
    list.addEventListener("change", onChange);
    return () => {
      list.removeEventListener("change", onChange);
    };
  } catch {
    return () => undefined;
  }
}

function isWide(): boolean {
  try {
    // Without media queries (jsdom, very old browsers) the table is the safe choice.
    return typeof window.matchMedia !== "function" || window.matchMedia(WIDE_TABLE_QUERY).matches;
  } catch {
    return true;
  }
}

/** True from 768 px on (or when the browser cannot say); follows changes of the window width. */
export function useWideTable(): boolean {
  return useSyncExternalStore(subscribe, isWide, () => true);
}

/**
 * Where a column goes on a card:
 * - `title`: the heading of the card (exactly one column should be the title),
 * - `status`: below the heading, without a visible label (a badge says what it is),
 * - `action`: next to the heading, right (a small icon button),
 * - `field`: a label/value pair (the default),
 * - `wide`: a label/value pair over the full width of the card (long content),
 * - `detail`: below the pairs without a label (a quiet line that names itself),
 * - `none`: not on the card.
 */
export type CardPlace = "title" | "status" | "action" | "field" | "wide" | "detail" | "none";

export interface TableColumn<Row> {
  /** Unique within the table; also the React key. */
  readonly key: string;
  /** Column heading and label on the card. */
  readonly header: string;
  /** The heading is for screen readers only (a column of icon buttons). */
  readonly headerHidden?: boolean;
  /** Classes of the heading cell (table only). */
  readonly headerClassName?: string;
  /** `data-testid` of the heading cell (table only). */
  readonly headerTestId?: string;
  /** Content of the cell. */
  readonly cell: (row: Row) => ReactNode;
  /** Content on the card when it differs from the cell (a title without its detail line). */
  readonly cardCell?: (row: Row) => ReactNode;
  /** Classes of the cell (table only). */
  readonly className?: string;
  /** `data-testid` of the cell and of its value on the card. */
  readonly testId?: string;
  /** Place on the card; default `field`. */
  readonly card?: CardPlace;
  /** False: only on the card (for example a detail the table shows inside another cell). */
  readonly table?: boolean;
}

/** A row whose columns from `from` on are replaced by one note (for example "No version"). */
export interface RowNote {
  /** Key of the first column the note replaces. */
  readonly from: string;
  readonly content: ReactNode;
}

/** Attributes of a row (and of its card): `data-*` attributes and the like. */
export type RowAttributes = HTMLAttributes<HTMLElement> & Record<`data-${string}`, string | number | undefined>;

export interface ResponsiveTableProps<Row> {
  /** Accessible name of the table and of the list of cards. */
  readonly label: string;
  /** `data-testid` of the table and of the list. */
  readonly testId?: string;
  readonly rows: readonly Row[];
  readonly rowKey: (row: Row) => string | number;
  readonly columns: readonly TableColumn<Row>[];
  /** Attributes of the row and of the card (`data-testid`, `data-*`). */
  readonly rowAttributes?: (row: Row) => RowAttributes;
  /** A note that replaces the last columns of a row. */
  readonly rowNote?: (row: Row) => RowNote | null;
  /** Level of the card headings: one below the heading of the section around the table. */
  readonly cardHeadingLevel: 2 | 3 | 4;
  /** Classes of the table (wide). */
  readonly tableClassName?: string;
  /** Classes of the header row (wide). */
  readonly headerRowClassName?: string;
  /** Classes of every body row (wide). */
  readonly rowClassName?: string;
  /** Classes of the cell holding the note (wide). */
  readonly noteClassName?: string;
}

/**
 * A table from 768 px, stacked cards below. The caller describes the columns
 * once; `card` says where each one goes on a card.
 */
export function ResponsiveTable<Row>(props: ResponsiveTableProps<Row>): ReactElement {
  const wide = useWideTable();
  return wide ? <WideTable {...props} /> : <CardList {...props} />;
}

function columnsBefore<Row>(columns: readonly TableColumn<Row>[], note: RowNote | null): TableColumn<Row>[] {
  if (note === null) {
    return [...columns];
  }
  const index = columns.findIndex((column) => column.key === note.from);
  return index < 0 ? [...columns] : columns.slice(0, index);
}

function WideTable<Row>({
  label,
  testId,
  rows,
  rowKey,
  columns,
  rowAttributes,
  rowNote,
  tableClassName,
  headerRowClassName,
  rowClassName,
  noteClassName,
}: ResponsiveTableProps<Row>): ReactElement {
  const shown = columns.filter((column) => column.table !== false);
  return (
    // relative: screen-reader texts (absolute) stay inside the scroll box (work order 079).
    <div className="relative overflow-x-auto">
      <table aria-label={label} data-testid={testId} className={joinClasses("w-full text-left text-sm", tableClassName)}>
        <thead>
          <tr className={headerRowClassName}>
            {shown.map((column) => (
              <th key={column.key} scope="col" data-testid={column.headerTestId} className={column.headerClassName}>
                {column.headerHidden === true ? <span className="sr-only">{column.header}</span> : column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const note = rowNote?.(row) ?? null;
            const before = columnsBefore(shown, note);
            return (
              <tr key={rowKey(row)} {...rowAttributes?.(row)} className={rowClassName}>
                {before.map((column) => (
                  <td key={column.key} data-testid={column.testId} className={column.className}>
                    {column.cell(row)}
                  </td>
                ))}
                {note === null ? null : (
                  <td colSpan={shown.length - before.length} className={noteClassName}>
                    {note.content}
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function CardList<Row>({
  label,
  testId,
  rows,
  rowKey,
  columns,
  rowAttributes,
  rowNote,
  cardHeadingLevel,
}: ResponsiveTableProps<Row>): ReactElement {
  return (
    <ul aria-label={label} data-testid={testId} data-layout="cards" className="space-y-3 text-sm tabular-nums">
      {rows.map((row) => (
        <Card
          key={rowKey(row)}
          row={row}
          columns={columns}
          attributes={rowAttributes?.(row)}
          note={rowNote?.(row) ?? null}
          headingLevel={cardHeadingLevel}
        />
      ))}
    </ul>
  );
}

function Card<Row>({
  row,
  columns,
  attributes,
  note,
  headingLevel,
}: {
  row: Row;
  columns: readonly TableColumn<Row>[];
  attributes: RowAttributes | undefined;
  note: RowNote | null;
  headingLevel: 2 | 3 | 4;
}): ReactElement {
  const shown = columnsBefore(columns, note).filter((column) => column.card !== "none");
  const placed = (place: CardPlace): TableColumn<Row>[] =>
    shown.filter((column) => (column.card ?? "field") === place);
  const content = (column: TableColumn<Row>): ReactNode => (column.cardCell ?? column.cell)(row);
  const Heading = `h${String(headingLevel)}` as "h2" | "h3" | "h4";
  const pairs = shown.filter((column) => {
    const place = column.card ?? "field";
    return place === "field" || place === "wide";
  });

  return (
    <li {...attributes} className="min-w-0 space-y-2 rounded border border-line bg-surface p-3">
      <div className="flex items-start gap-3">
        <Heading className="min-w-0 flex-1 text-base font-semibold break-words">
          {placed("title").map((column) => (
            <span key={column.key} data-testid={column.testId}>
              {content(column)}
            </span>
          ))}
        </Heading>
        {placed("action").map((column) => (
          <div key={column.key} data-testid={column.testId} className="shrink-0">
            {content(column)}
          </div>
        ))}
      </div>
      {placed("status").map((column) => (
        <div key={column.key} data-testid={column.testId} className="space-y-1">
          <span className="sr-only">{column.header}: </span>
          {content(column)}
        </div>
      ))}
      {pairs.length === 0 ? null : (
        <dl className="grid grid-cols-[max-content_minmax(0,1fr)] gap-x-3 gap-y-1">
          {pairs.map((column) =>
            column.card === "wide" ? (
              <div key={column.key} className="col-span-2 space-y-1">
                <dt className="text-fg-muted">{column.header}</dt>
                <dd data-testid={column.testId} className="min-w-0 break-words">
                  {content(column)}
                </dd>
              </div>
            ) : (
              <div key={column.key} className="contents">
                <dt className="text-fg-muted">{column.header}</dt>
                <dd data-testid={column.testId} className="min-w-0 break-words">
                  {content(column)}
                </dd>
              </div>
            ),
          )}
        </dl>
      )}
      {placed("detail").map((column) => (
        <div key={column.key} data-testid={column.testId}>
          {content(column)}
        </div>
      ))}
      {note === null ? null : <p className="text-fg-muted">{note.content}</p>}
    </li>
  );
}
