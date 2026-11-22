import {
  type ReactElement,
  type RefObject,
  useEffect,
  useId,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import { useTranslation } from "react-i18next";
import { NavigationType, NavLink, Outlet, useLocation, useNavigationType } from "react-router";

import type { Me } from "../api/generated";
import { Icon } from "../icons/Icon.tsx";
import { LanguageSwitch } from "../LanguageSwitch.tsx";
import { type NavigationEntry, visibleNavigation } from "../navigation.ts";
import { useSession } from "../session.ts";
import { BrandMark, typingRunFor } from "./BrandMark.tsx";
import { Button } from "./ui/Button.tsx";
import { UserMenu, UserMenuContent } from "./UserMenu.tsx";

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
 * Below this width (768 px, Tailwind's `md`) the navigation and the user menu
 * fold into one menu behind a button (E-65 point 3, work order 082).
 */
export const NARROW_QUERY = "(width < 48rem)";

function watchNarrow(onChange: () => void): () => void {
  try {
    if (typeof window.matchMedia !== "function") {
      return () => undefined;
    }
    const list = window.matchMedia(NARROW_QUERY);
    list.addEventListener("change", onChange);
    return () => {
      list.removeEventListener("change", onChange);
    };
  } catch {
    return () => undefined;
  }
}

function isNarrow(): boolean {
  try {
    return typeof window.matchMedia === "function" && window.matchMedia(NARROW_QUERY).matches;
  } catch {
    return false;
  }
}

/** Whether the window is narrower than 768 px; false where matchMedia is missing (tests). */
function useNarrowScreen(): boolean {
  return useSyncExternalStore(watchNarrow, isNarrow, () => false);
}

/**
 * The entries of the main navigation. In the header bar (from 768 px) each
 * shows its icon; from 1280 px (`xl`) the text next to it, from 768 to 1279 px
 * the short text (`nav:short.*`, 13 px on a 16 px line, E-65 point 5) below it. The full text stays the
 * accessible name and tooltip: the short text is drawn by CSS from
 * `data-short` (`.nav-short` in index.css) inside an `aria-hidden` element, so
 * it is neither read out twice nor part of the link's text. In the menu below
 * 768 px every entry shows icon and full text on a line of its own.
 */
function NavigationList({
  entries,
  inMenu,
  onChoose,
}: {
  entries: readonly NavigationEntry[];
  inMenu: boolean;
  onChoose?: () => void;
}): ReactElement {
  const { t } = useTranslation("nav");
  return (
    <ul className={inMenu ? "flex flex-col gap-y-1" : "flex w-max items-center xl:gap-x-1 xl:p-1"}>
      {entries.map((entry) => {
        const label = t(entry.textKey);
        return (
          <li key={entry.path}>
            <NavLink
              to={entry.path}
              end={entry.end ?? false}
              className={
                inMenu
                  ? "nav-link w-full py-2"
                  : "nav-link max-xl:flex-col max-xl:gap-0.5 max-xl:px-1 max-xl:py-0.5 max-xl:-outline-offset-2"
              }
              title={label}
              onClick={onChoose}
            >
              <Icon name={entry.icon} size={20} decorative />
              {/* Navigation line (pattern C): data-label reserves the width of the bold label. */}
              <span className={inMenu ? "nav-label" : "nav-label max-xl:sr-only"} data-label={label}>
                {label}
              </span>
              {inMenu ? null : (
                <span
                  className="nav-short text-meta leading-4 xl:hidden"
                  data-short={t(`short.${entry.textKey}`)}
                  aria-hidden="true"
                />
              )}
            </NavLink>
          </li>
        );
      })}
    </ul>
  );
}

/**
 * Below 768 px: the button "Menu" opens a panel under the header with every
 * navigation entry and the content of the user menu. It closes on Escape (the
 * focus goes back to the button), when the focus leaves button and panel, on a click outside, on every change of the
 * address and when the window grows to 768 px. Choosing an entry closes it
 * and puts the focus on the button; the new page then moves it on to its
 * heading (work order 078).
 */
function NavigationMenu({ user, entries }: { user: Me; entries: readonly NavigationEntry[] }): ReactElement {
  const { t } = useTranslation("nav");
  const location = useLocation();
  const panelId = useId();
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  // Open only for the address it was opened on, like the user menu.
  const [openOn, setOpenOn] = useState<string | null>(null);
  const open = openOn === location.key;

  useEffect(
    () =>
      watchNarrow(() => {
        setOpenOn(null);
      }),
    [],
  );

  useEffect(() => {
    if (!open) {
      return undefined;
    }
    const onPointerDown = (event: PointerEvent): void => {
      const target = event.target;
      if (
        target instanceof Node &&
        buttonRef.current?.contains(target) !== true &&
        panelRef.current?.contains(target) !== true
      ) {
        setOpenOn(null);
      }
    };
    const onKeyDown = (event: globalThis.KeyboardEvent): void => {
      if (event.key === "Escape") {
        setOpenOn(null);
        buttonRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const close = (): void => {
    setOpenOn(null);
    buttonRef.current?.focus();
  };

  return (
    // Disclosure navigation (WAI-ARIA APG): when the focus moves on to an element outside button and panel
    // (Tab after the last entry, Shift+Tab before the button), the panel closes and the focus stays where it went,
    // so it never rests on content hidden under the panel (WCAG 2.4.11). A focus that goes nowhere (a click on
    // text inside the panel, another window) leaves it open; a click outside closes it through pointerdown.
    <div
      onBlur={(event) => {
        const next = event.relatedTarget;
        if (open && next instanceof Node && !event.currentTarget.contains(next)) {
          setOpenOn(null);
        }
      }}
    >
      <Button
        ref={buttonRef}
        type="button"
        variant="ghost"
        icon={open ? "close" : "menu"}
        aria-expanded={open}
        aria-controls={panelId}
        data-testid="navigation-menu-button"
        onClick={() => {
          setOpenOn(open ? null : location.key);
        }}
        className="whitespace-nowrap"
      >
        {t("menu")}
      </Button>
      <div
        ref={panelRef}
        id={panelId}
        hidden={!open}
        data-testid="navigation-menu"
        className="absolute inset-x-0 top-full z-30 max-h-[calc(100dvh-5rem)] overflow-y-auto border-b border-line bg-surface shadow-lg"
      >
        <div className={`${PAGE_GRID} space-y-4 py-4`}>
          {entries.length > 0 ? (
            <nav aria-label={t("label")} data-testid="main-navigation">
              <NavigationList entries={entries} inMenu onChoose={close} />
            </nav>
          ) : null}
          <div className={entries.length > 0 ? "border-t border-line pt-4 text-sm" : "text-sm"}>
            <UserMenuContent user={user} />
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Frame of every page: skip link, header with name, navigation and user menu
 * (before sign-in: the language switch), and the page content. The navigation
 * shows only the entries the signed-in user's role allows; without a session
 * (sign-in page) it is not shown at all. Below 768 px navigation and user menu
 * sit behind the button "Menu" (`NavigationMenu`). The heading of the page is
 * its `h1`; the name in the header is a link, not a heading.
 */
export function Layout(): ReactElement {
  const { t } = useTranslation(["common", "nav", "auth"]);
  const session = useSession();
  const user = session.status === "signed-in" ? session.user : null;
  const entries = user === null ? [] : visibleNavigation(user.role);
  const narrow = useNarrowScreen();
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
      <header className="relative border-b border-line bg-surface">
        {/*
          One line in every language and at every width: the navigation never
          wraps. From 1280 px (xl) each entry shows icon and text; from 768 to
          1279 px the icon above a short text, as high as one entry at 1280 px
          (42 px), so the header keeps its height. If the entries do not fit
          (a long user name at 768 px), the navigation scrolls on its own
          instead of covering the user menu or widening the page; there the
          focus ring is drawn inside the entry, so the scroll box does not cut
          it off. Below 768 px
          navigation and user menu sit behind the button "Menu" (E-65 point 3,
          work order 082). Header and page content share one grid (PAGE_GRID,
          E-65), so the brand mark and the page heading start on the same line
          at every width.
        */}
        <div data-testid="header-grid" className={`${PAGE_GRID} flex items-center gap-x-4 py-4`}>
          <div className="text-3xl font-semibold tracking-tight">
            <BrandMark typing={typingRunFor(session.status)} />
          </div>
          <div className="min-w-0 flex-1">
            {!narrow && entries.length > 0 ? (
              <nav aria-label={t("nav:label")} data-testid="main-navigation" className="overflow-x-auto max-md:hidden">
                <NavigationList entries={entries} inMenu={false} />
              </nav>
            ) : null}
          </div>
          {/* Before sign-in the language is chosen here; afterwards in the user menu and on the settings page. */}
          {user === null ? <LanguageSwitch /> : null}
          <div data-testid="user-area" className="shrink-0">
            {user === null ? null : narrow ? <NavigationMenu user={user} entries={entries} /> : <UserMenu user={user} />}
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
