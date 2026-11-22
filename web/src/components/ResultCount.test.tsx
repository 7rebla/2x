import { cleanup, render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, describe, expect, it } from "vitest";

import { type CountReport, ResultCount, useReportCount, useResultCount } from "./ResultCount.tsx";

afterEach(() => {
  cleanup();
});

const text = (count: number): string => `${String(count)} entries found`;

describe("ResultCount", () => {
  it("is a polite live region that is empty while the number is unknown", () => {
    render(<ResultCount count={null} text={text} empty="Nothing found." testId="count" />);
    const region = screen.getByTestId("count");
    expect(region.getAttribute("role")).toBe("status");
    // role="status" is polite by itself; nothing makes it assertive.
    expect(region.getAttribute("aria-live")).toBeNull();
    expect(region.textContent).toBe("");
  });

  it("shows the number in small secondary text", () => {
    render(<ResultCount count={120} text={text} empty="Nothing found." countTestId="total" emptyTestId="none" />);
    const total = screen.getByTestId("total");
    expect(total.textContent).toBe("120 entries found");
    expect(total.className).toContain("text-sm");
    expect(total.className).toContain("text-fg-muted");
    expect(screen.queryByTestId("none")).toBeNull();
  });

  it("shows the text for no entries in place of the number", () => {
    render(<ResultCount count={0} text={text} empty="Nothing found." countTestId="total" emptyTestId="none" />);
    expect(screen.getByTestId("none").textContent).toBe("Nothing found.");
    expect(screen.getByTestId("none").className).toContain("text-fg-muted");
    expect(screen.queryByTestId("total")).toBeNull();
  });
});

/** A list part mounted afresh per filter that reports `count` once it has loaded. */
function Part({
  filterKey,
  count,
  report,
}: {
  filterKey: string;
  count: number | undefined;
  report: (report: CountReport) => void;
}): ReactElement {
  useReportCount(filterKey, count, report);
  return <p>{filterKey}</p>;
}

function List({ view }: { view: { filterKey: string; count: number | undefined } }): ReactElement {
  const [count, report] = useResultCount(view.filterKey);
  return (
    <>
      <ResultCount count={count} text={text} empty="Nothing found." testId="count" />
      <Part key={view.filterKey} filterKey={view.filterKey} count={view.count} report={report} />
    </>
  );
}

describe("useResultCount and useReportCount", () => {
  it("keep the region and give the number of the current filter only", () => {
    const { rerender } = render(<List view={{ filterKey: "a", count: undefined }} />);
    const region = screen.getByTestId("count");
    expect(region.textContent).toBe("");

    rerender(<List view={{ filterKey: "a", count: 3 }} />);
    expect(region.textContent).toBe("3 entries found");

    // A new filter: the old number does not stay while the new list loads.
    rerender(<List view={{ filterKey: "b", count: undefined }} />);
    expect(screen.getByTestId("count")).toBe(region);
    expect(region.textContent).toBe("");

    rerender(<List view={{ filterKey: "b", count: 0 }} />);
    expect(region.textContent).toBe("Nothing found.");
    expect(screen.getByTestId("count")).toBe(region);
  });
});
