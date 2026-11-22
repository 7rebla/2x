import { type ReactElement, useEffect, useState } from "react";

// Result count of a filtered list (work order 089): how many entries the
// list holds, or that none match. The region is a polite live region
// (role="status"), so screen readers announce a new count once the list has
// loaded, without interrupting.
//
// Screen readers announce only changes inside a live region that already
// exists. The caller therefore keeps the region in place while the list
// reloads (outside any part that a new filter mounts afresh) and passes
// `count={null}` while it does not know the number: the region is then empty,
// and the new number is announced when it arrives. An unchanged number (a
// list that is polled) changes nothing in the page and is not read again.
// A filter that changes with every key press should pass the count only once
// the list for the finished input has loaded, never per key.

/** The number of entries of a list, for the filter it was loaded with. */
export interface CountReport {
  /** The filter, as the key that mounts the list afresh. */
  readonly filterKey: string;
  readonly count: number;
}

/**
 * Keeps the number of entries of a list whose part is mounted afresh for every
 * filter (`key={filterKey}`). That part reports what it loaded with `report`
 * (stable, from an effect); `count` is that number while it belongs to the
 * current filter, null otherwise (a new filter is loading).
 */
export function useResultCount(filterKey: string): [count: number | null, report: (report: CountReport) => void] {
  const [last, setLast] = useState<CountReport | null>(null);
  return [last?.filterKey === filterKey ? last.count : null, setLast];
}

/**
 * Reports the loaded number of entries (`undefined` while nothing is loaded)
 * of the list part to `useResultCount` of its parent, once per new number.
 */
export function useReportCount(
  filterKey: string,
  count: number | undefined,
  report: (report: CountReport) => void,
): void {
  useEffect(() => {
    if (count !== undefined) {
      report({ filterKey, count });
    }
  }, [filterKey, count, report]);
}

export interface ResultCountProps {
  /** Number of entries of the whole list (all pages); null while unknown (loading, error). */
  count: number | null;
  /** The text for one or more entries, for example `t("resultCount", { count })` ("120 entries"). */
  text: (count: number) => string;
  /** The text for no entries, for example "No entries found." */
  empty: string;
  /** Test id of the region. */
  testId?: string;
  /** Test id of the text for one or more entries. */
  countTestId?: string;
  /** Test id of the text for no entries. */
  emptyTestId?: string;
}

/**
 * The number of entries of a filtered list as a polite live region:
 * "120 entries" in small secondary text, or the text for no entries in
 * secondary text of the normal size (it stands in place of the list).
 */
export function ResultCount({ count, text, empty, testId, countTestId, emptyTestId }: ResultCountProps): ReactElement {
  return (
    <div role="status" data-testid={testId}>
      {count === null ? null : count === 0 ? (
        <p data-testid={emptyTestId} className="text-fg-muted">
          {empty}
        </p>
      ) : (
        <p data-testid={countTestId} className="text-sm text-fg-muted">
          {text(count)}
        </p>
      )}
    </div>
  );
}
