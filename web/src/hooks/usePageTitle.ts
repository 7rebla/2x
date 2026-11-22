// Title of the browser tab per page (work order 078, WCAG 2.4.2): "Structure – 2x",
// for a device or a file its name. Tabs, history and bookmarks can then be told
// apart, and screen readers announce the new title after a change of page.
import { useEffect } from "react";
import { useTranslation } from "react-i18next";

/** Separator between the page and the name of the application (an en dash with spaces). */
export const TITLE_SEPARATOR = " – ";

/** The browser title for a page: "<page> – <app>", or the name of the application alone without a page. */
export function pageTitle(appTitle: string, page: string | null): string {
  const trimmed = page?.trim() ?? "";
  return trimmed === "" ? appTitle : `${trimmed}${TITLE_SEPARATOR}${appTitle}`;
}

/**
 * Sets the browser title while the calling page is shown; usually with the
 * text of its heading. `null` sets nothing, so a page can leave the title to a
 * page it shows instead (NotFound for an unknown device). When the page goes
 * away the title falls back to the name of the application, so a page without
 * a title of its own never shows the title of the page before.
 */
export function usePageTitle(page: string | null): void {
  const { t } = useTranslation("common");
  const appTitle = t("appTitle");
  useEffect(() => {
    if (page === null) {
      return undefined;
    }
    document.title = pageTitle(appTitle, page);
    return () => {
      document.title = appTitle;
    };
  }, [appTitle, page]);
}
