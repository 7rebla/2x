import { type ReactElement, type RefObject, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { NavigationType, NavLink, Outlet, useLocation, useNavigationType } from "react-router";

import { Icon } from "../icons/Icon.tsx";
import { LanguageSwitch } from "../LanguageSwitch.tsx";
import { visibleNavigation } from "../navigation.ts";
import { useSession } from "../session.ts";
import { BrandMark, typingRunFor } from "./BrandMark.tsx";
import { UserMenu } from "./UserMenu.tsx";

/** Id of the page content, the target of the skip link. */
export const MAIN_CONTENT_ID = "inhalt";

/**
 * The one page grid (E-65 point 1, work order 080): header and page content
 * are equally wide (at most 80rem, 1280 px) with the same side padding, so the
 * left edges of brand mark and page heading are on one line at every width.
 */
export const PAGE_GRID = "mx-auto w-full max-w-7xl px-4";

/**
 * Paragraphs directly inside a page's section (introductions and other running
 * text) are held to a readable line length of about 65 characters.
 */
export const PAGE_PROSE = "[&>section>p]:max-w-prose";

/**
 * After a change of page, moves the focus to the heading (`h1`) of the new
 * page (work order 078, WCAG 2.4.3), so keyboard and screen reader users start
 * reading there instead of staying in the navigation. Not on the first load:
 * neither the first page nor a redirect before the user has done anything
 * (to the sign-in page) takes the focus. Pages that arrive later (loaded on
 * demand, data still loading) are watched until their heading shows; the
 * watch ends with the next change of page or as soon as the user clicks or
 * presses a key, and it never takes the focus from an element the user moved
 * to in the meantime.
 */
function useHeadingFocus(main: RefObject<HTMLElement | null>): void {
  const { pathname } = useLocation();
  const navigationType = useNavigationType();
  const shownPath = useRef(pathname);
  const interacted = useRef(false);
  const stopWatch = useRef<(() => void) | null>(null);

  useEffect(() => {
    const onInteraction = (): void => {
      interacted.current = true;
      stopWatch.current?.();
    };
    document.addEventListener("pointerdown", onInteraction, true);
    document.addEventListener("keydown", onInteraction, true);
    return () => {
      document.removeEventListener("pointerdown", onInteraction, true);
      document.removeEventListener("keydown", onInteraction, true);
    };
  }, []);

  useEffect(() => {
    if (shownPath.current === pathname) {
      // First render; a change of the query or the hash alone is no new page.
      return undefined;
    }
    shownPath.current = pathname;
    const container = main.current;
    if (container === null || (navigationType === NavigationType.Replace && !interacted.current)) {
      return undefined;
    }
    const origin = document.activeElement;
    let focused: HTMLElement | null = null;
    const focusHeading = (): void => {
      const heading = container.querySelector<HTMLElement>("h1");
      if (heading === null || heading === focused) {
        return;
      }
      const active = document.activeElement;
      if (active !== null && active !== document.body && active !== origin && active !== focused) {
        // The user has moved on; leave the focus where it is.
        stop();
        return;
      }
      if (!heading.hasAttribute("tabindex")) {
        heading.tabIndex = -1;
      }
      heading.focus();
      focused = heading;
    };
    const observer = new MutationObserver(focusHeading);
    const stop = (): void => {
      observer.disconnect();
      stopWatch.current = null;
    };
    stopWatch.current = stop;
    observer.observe(container, { childList: true, subtree: true });
    focusHeading();
    return stop;
  }, [main, pathname, navigationType]);
}

/**
 * Frame of every page: skip link, header with name, navigation and user menu
 * (before sign-in: the language switch), and the page content. The navigation
 * shows only the entries the signed-in user's role allows; without a session
 * (sign-in page) it is not shown at all. The heading of the page is its `h1`;
 * the name in the header is a link, not a heading.
 */
export function Layout(): ReactElement {
  const { t } = useTranslation(["common", "nav", "auth"]);
  const session = useSession();
  const user = session.status === "signed-in" ? session.user : null;
  const entries = user === null ? [] : visibleNavigation(user.role);
  const main = useRef<HTMLElement>(null);
  useHeadingFocus(main);
  return (
    <div className="flex min-h-screen flex-col bg-canvas text-fg">
      {/* First stop of the keyboard (WCAG 2.4.1): above the window until it has the focus, then at the top left. */}
      <a
        href={`#${MAIN_CONTENT_ID}`}
        data-testid="skip-link"
        className="fixed top-2 left-2 z-50 -translate-y-[calc(100%+1rem)] rounded border border-line-strong bg-surface px-4 py-2 font-semibold text-accent underline focus:translate-y-0"
        onClick={(event) => {
          // Focus the content without writing the fragment into the address.
          event.preventDefault();
          main.current?.focus();
        }}
      >
        {t("common:skipToContent")}
      </a>
      <header className="border-b border-line bg-surface">
        {/*
          One line in every language and at every width: the navigation never
          wraps; below 1280 px (xl) its entries shrink to their icons (the text
          stays as accessible name and tooltip), and if even that does not
          fit, the navigation scrolls on its own instead of the page. Header
          and page content share one grid (PAGE_GRID, E-65), so the brand mark
          and the page heading start on the same line at every width.
        */}
        <div data-testid="header-grid" className={`${PAGE_GRID} flex items-center gap-x-4 py-4`}>
          <div className="text-3xl font-semibold tracking-tight">
            <BrandMark typing={typingRunFor(session.status)} />
          </div>
          <div className="min-w-0 flex-1">
            {entries.length > 0 ? (
              <nav aria-label={t("nav:label")} data-testid="main-navigation" className="overflow-x-auto">
                <ul className="flex w-max items-center gap-x-1 p-1">
                  {entries.map((entry) => {
                    const label = t(`nav:${entry.textKey}`);
                    return (
                      <li key={entry.path}>
                        <NavLink to={entry.path} end={entry.end ?? false} className="nav-link" title={label}>
                          <Icon name={entry.icon} size={20} decorative />
                          {/* Navigation line (pattern C): data-label reserves the width of the bold label. */}
                          <span className="nav-label max-xl:sr-only" data-label={label}>
                            {label}
                          </span>
                        </NavLink>
                      </li>
                    );
                  })}
                </ul>
              </nav>
            ) : null}
          </div>
          {/* Before sign-in the language is chosen here; afterwards in the user menu and on the settings page. */}
          {user === null ? <LanguageSwitch /> : null}
          <div data-testid="user-area" className="shrink-0">
            {user === null ? null : <UserMenu user={user} />}
          </div>
        </div>
      </header>
      {/*
        Focused by the skip link and after a change of page (its h1); no ring around content that is not a control.
        Running text directly in a page (its introduction) keeps a readable line length (max-w-prose); tables,
        cards and the map take the whole grid.
      */}
      <main
        ref={main}
        id={MAIN_CONTENT_ID}
        tabIndex={-1}
        className={`${PAGE_GRID} flex-1 space-y-4 py-8 focus:outline-none [&_h1:focus]:outline-none ${PAGE_PROSE}`}
      >
        {user !== null && user.role === null ? (
          <p role="status" data-testid="no-role" className="rounded border border-warning-line bg-warning-soft p-4 text-warning">
            <Icon name="warning" className="mr-2" decorative />
            {t("auth:noRole")}
          </p>
        ) : null}
        <Outlet />
      </main>
    </div>
  );
}
