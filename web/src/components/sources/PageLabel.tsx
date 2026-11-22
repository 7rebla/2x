// Page or pages of a section ("p. 31", "pp. 31–32"; German "S. 31", "S. 31–32"),
// shared by the search and the answer page (work orders 054, 132).
import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";

import type { SearchHit } from "../../api/generated";
import { pageRange } from "./snippet.ts";

/** The pages of a section; nothing for a section without a page (Markdown, for example). */
export function PageLabel({ pages }: { pages: Pick<SearchHit, "page_start" | "page_end"> }): ReactElement | null {
  const { t } = useTranslation("search");
  const range = pageRange(pages.page_start, pages.page_end);
  if (range === null) {
    return null;
  }
  const text =
    range.length === 1 ? t("page.one", { page: range[0] }) : t("page.range", { start: range[0], end: range[1] });
  return (
    <span data-testid="search-hit-page" className="font-semibold text-fg tabular-nums">
      {text}
    </span>
  );
}
