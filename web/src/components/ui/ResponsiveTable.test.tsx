import { act, cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { fakeMatchMedia } from "../../test/fakeMatchMedia.ts";
import { ResponsiveTable, type ResponsiveTableProps, type TableColumn, WIDE_TABLE_QUERY } from "./ResponsiveTable.tsx";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

interface Part {
  id: number;
  name: string;
  state: string;
  size: string | null;
  note: string;
}

const PARTS: Part[] = [
  { id: 1, name: "Test valve", state: "Ready", size: "1 kB", note: "test note 1" },
  { id: 2, name: "Test pump", state: "Waiting", size: null, note: "test note 2" },
];

const COLUMNS: TableColumn<Part>[] = [
  {
    key: "name",
    header: "Name",
    card: "title",
    testId: "part-name",
    className: "test-name-cell",
    cell: (part) => (
      <>
        {part.name}
        <span data-testid="table-only-detail">detail of {part.name}</span>
      </>
    ),
    cardCell: (part) => part.name,
  },
  { key: "state", header: "State", card: "status", testId: "part-state", cell: (part) => part.state },
  { key: "size", header: "Size", testId: "part-size", headerTestId: "size-heading", cell: (part) => part.size },
  { key: "note", header: "Note", card: "wide", testId: "part-note", cell: (part) => part.note },
  {
    key: "open",
    header: "Open",
    headerHidden: true,
    card: "action",
    cell: (part) => <a href={`/parts/${String(part.id)}`}>open {part.name}</a>,
  },
  { key: "secret", header: "Internal", card: "none", testId: "part-internal", cell: () => "internal" },
  {
    key: "extra",
    header: "Extra",
    table: false,
    card: "detail",
    testId: "part-extra",
    cell: (part) => `extra ${String(part.id)}`,
  },
];

function renderParts(more: Partial<ResponsiveTableProps<Part>> = {}): void {
  render(
    <ResponsiveTable
      label="Test parts"
      testId="parts"
      rows={PARTS}
      rowKey={(part) => part.id}
      columns={COLUMNS}
      rowAttributes={(part) => ({ "data-testid": "part", "data-part": part.id })}
      rowNote={(part) => (part.size === null ? { from: "size", content: "No size yet" } : null)}
      cardHeadingLevel={3}
      rowClassName="test-row"
      noteClassName="test-note"
      {...more}
    />,
  );
}

function parts(): HTMLElement[] {
  return screen.getAllByTestId("part");
}

function part(index: number): HTMLElement {
  const found = parts()[index];
  if (found === undefined) {
    throw new Error(`no part ${String(index)}`);
  }
  return found;
}

describe("wide: a table", () => {
  it("is a table when the browser has no media queries", () => {
    renderParts();

    const table = screen.getByRole("table", { name: "Test parts" });
    expect(table.dataset.testid).toBe("parts");
    expect(screen.queryByRole("list")).toBeNull();
    expect(screen.getAllByRole("columnheader").map((header) => header.textContent)).toEqual([
      "Name",
      "State",
      "Size",
      "Note",
      "Open",
      "Internal",
    ]);
    for (const header of screen.getAllByRole("columnheader")) {
      expect(header.getAttribute("scope")).toBe("col");
    }
    expect(screen.getByRole("columnheader", { name: "Open" }).querySelector(".sr-only")?.textContent).toBe("Open");
    expect(screen.getByTestId("size-heading").textContent).toBe("Size");
  });

  it("is a table from 768 px on", () => {
    fakeMatchMedia({ [WIDE_TABLE_QUERY]: true });
    renderParts();

    expect(screen.getByRole("table", { name: "Test parts" })).toBeDefined();
    expect(screen.queryByRole("list")).toBeNull();
  });

  it("puts every column into a cell, with the row attributes and classes", () => {
    renderParts();

    const first = part(0);
    expect(first.tagName).toBe("TR");
    expect(first.dataset.part).toBe("1");
    expect(first.className).toBe("test-row");
    expect(within(first).getByTestId("part-name").className).toBe("test-name-cell");
    expect(within(first).getByTestId("part-name").textContent).toBe("Test valvedetail of Test valve");
    expect(within(first).getByTestId("part-state").textContent).toBe("Ready");
    expect(within(first).getByTestId("part-size").textContent).toBe("1 kB");
    expect(within(first).getByTestId("part-internal").textContent).toBe("internal");
    expect(within(first).queryByTestId("part-extra")).toBeNull();
    expect(within(first).getAllByRole("cell")).toHaveLength(6);
  });

  it("replaces the columns from the note on with one cell", () => {
    renderParts();

    const second = part(1);
    const cells = within(second).getAllByRole("cell");
    expect(cells.map((item) => item.textContent)).toEqual(["Test pumpdetail of Test pump", "Waiting", "No size yet"]);
    expect(cells[2]?.getAttribute("colspan")).toBe("4");
    expect(cells[2]?.className).toBe("test-note");
  });
});

describe("narrow: cards", () => {
  it("is a list with the same name and one card per row below 768 px", () => {
    fakeMatchMedia({ [WIDE_TABLE_QUERY]: false });
    renderParts();

    expect(screen.queryByRole("table")).toBeNull();
    const list = screen.getByRole("list", { name: "Test parts" });
    expect(list.dataset.testid).toBe("parts");
    expect(list.dataset.layout).toBe("cards");
    expect(within(list).getAllByRole("listitem")).toHaveLength(2);
    expect(part(0).tagName).toBe("LI");
    expect(part(0).dataset.part).toBe("1");
  });

  it("gives every card a heading of the asked level with the card content of the title column", () => {
    fakeMatchMedia({ [WIDE_TABLE_QUERY]: false });
    renderParts();

    expect(screen.getAllByRole("heading", { level: 3 }).map((heading) => heading.textContent)).toEqual([
      "Test valve",
      "Test pump",
    ]);
    expect(screen.queryByTestId("table-only-detail")).toBeNull();
  });

  it("shows the status with a label for screen readers, the pairs as a description list and the action", () => {
    fakeMatchMedia({ [WIDE_TABLE_QUERY]: false });
    renderParts();

    const first = part(0);
    const state = within(first).getByTestId("part-state");
    expect(state.textContent).toBe("State: Ready");
    expect(state.querySelector(".sr-only")?.textContent).toBe("State: ");

    const terms = Array.from(first.querySelectorAll("dt")).map((term) => term.textContent);
    expect(terms).toEqual(["Size", "Note"]);
    expect(within(first).getByTestId("part-size").tagName).toBe("DD");
    expect(within(first).getByTestId("part-size").textContent).toBe("1 kB");
    expect(within(first).getByTestId("part-note").parentElement?.className).toContain("col-span-2");

    expect(within(first).getByRole("link", { name: "open Test valve" }).getAttribute("href")).toBe("/parts/1");
    expect(within(first).queryByTestId("part-internal")).toBeNull();
    expect(within(first).getByTestId("part-extra").textContent).toBe("extra 1");
  });

  it("shows the note in place of the columns it replaces", () => {
    fakeMatchMedia({ [WIDE_TABLE_QUERY]: false });
    renderParts();

    const second = part(1);
    expect(within(second).getByText("No size yet").tagName).toBe("P");
    expect(within(second).queryByTestId("part-size")).toBeNull();
    expect(within(second).queryByTestId("part-note")).toBeNull();
    expect(within(second).queryByTestId("part-extra")).toBeNull();
    expect(within(second).queryByRole("link")).toBeNull();
    expect(within(second).getByTestId("part-state").textContent).toBe("State: Waiting");
  });

  it("uses heading level 2 or 4 when asked", () => {
    fakeMatchMedia({ [WIDE_TABLE_QUERY]: false });
    renderParts({ cardHeadingLevel: 2 });
    expect(screen.getAllByRole("heading", { level: 2 })).toHaveLength(2);
    cleanup();

    renderParts({ cardHeadingLevel: 4 });
    expect(screen.getAllByRole("heading", { level: 4 })).toHaveLength(2);
  });
});

describe("changes of the window width", () => {
  it("turns into cards and back when the width crosses 768 px", () => {
    const media = fakeMatchMedia({ [WIDE_TABLE_QUERY]: true });
    renderParts();
    expect(screen.getByRole("table", { name: "Test parts" })).toBeDefined();

    act(() => {
      media.set(WIDE_TABLE_QUERY, false);
    });
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.getByRole("list", { name: "Test parts" })).toBeDefined();

    act(() => {
      media.set(WIDE_TABLE_QUERY, true);
    });
    expect(screen.getByRole("table", { name: "Test parts" })).toBeDefined();
  });

  it("keeps the table when the media query throws", () => {
    vi.stubGlobal("matchMedia", () => {
      throw new Error("test: no media queries");
    });
    renderParts();
    expect(screen.getByRole("table", { name: "Test parts" })).toBeDefined();
  });
});
