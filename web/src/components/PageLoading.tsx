// States of a page whose code is loaded only when it is opened (work order 062):
// a calm loading state while the code arrives, and a notice with "Reload" if it
// cannot be loaded (for example after a new build while the page was open).
import { Component, type ComponentType, lazy, type ReactElement, type ReactNode, Suspense, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Icon } from "../icons/Icon.tsx";
import { Loading } from "./Loading.tsx";

/**
 * The loading state appears only after this many milliseconds, so a page that
 * arrives quickly (the usual case on the own server) does not flash it.
 */
export const PAGE_LOADING_DELAY_MS = 300;

/**
 * Shown while the code of a page is loaded. It keeps some room, so the footer
 * does not jump, and shows the common loading state (turning icon and loading
 * shimmer, pattern D; both stand still with reduced motion) after a short delay.
 */
export function PageLoading(): ReactElement {
  const { t } = useTranslation("common");
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setVisible(true);
    }, PAGE_LOADING_DELAY_MS);
    return () => {
      window.clearTimeout(timer);
    };
  }, []);
  return (
    <div data-testid="page-loading" aria-busy="true" className="min-h-24 py-2">
      {visible ? <Loading label={t("pageLoad.loading")} /> : null}
    </div>
  );
}

/** Reloads the whole application from the server (new build, new parts). */
export function reloadApplication(): void {
  window.location.reload();
}

/** Notice for a page whose code could not be loaded, with a button that reloads the application. */
export function PageLoadFailed({ onReload = reloadApplication }: { onReload?: () => void }): ReactElement {
  const { t } = useTranslation("common");
  return (
    <div
      role="alert"
      data-testid="page-load-failed"
      className="space-y-3 rounded border border-danger-line bg-danger-soft p-4 text-danger"
    >
      <p data-testid="page-load-failed-summary">
        <Icon name="error" className="mr-2" decorative />
        {t("pageLoad.failed")}
      </p>
      <p className="text-sm text-fg">{t("pageLoad.failedHint")}</p>
      <button
        type="button"
        onClick={onReload}
        data-testid="page-reload"
        className="inline-flex items-center gap-2 rounded border border-line-strong bg-surface px-3 py-1 text-fg hover:bg-surface-muted"
      >
        <Icon name="retry" decorative />
        {t("pageLoad.reload")}
      </button>
    </div>
  );
}

/** The code of a page could not be loaded (network error, or the file is gone after a new build). */
export class PageLoadError extends Error {
  readonly reason: unknown;

  constructor(reason: unknown) {
    super("The code of a page could not be loaded.");
    this.name = "PageLoadError";
    this.reason = reason;
  }
}

interface BoundaryProps {
  children: ReactNode;
  onReload?: () => void;
}

interface BoundaryState {
  error: { value: unknown } | null;
}

/**
 * Catches a PageLoadError of the page inside and shows PageLoadFailed. Every
 * other error is passed on to the router, which shows its own error state.
 */
export class PageLoadBoundary extends Component<BoundaryProps, BoundaryState> {
  override state: BoundaryState = { error: null };

  static getDerivedStateFromError(error: unknown): BoundaryState {
    return { error: { value: error } };
  }

  override render(): ReactNode {
    const { error } = this.state;
    if (error === null) {
      return this.props.children;
    }
    if (error.value instanceof PageLoadError) {
      return <PageLoadFailed onReload={this.props.onReload} />;
    }
    // Not a loading problem: the error element of the route handles it.
    throw error.value;
  }
}

export interface LazyPage {
  /** Element for the route: the page with its loading state and its notice for a failed load. */
  readonly element: ReactElement;
  /** Loads the code of the page ahead of time (used by the tests). */
  readonly preload: () => Promise<void>;
}

/**
 * A page that is loaded when it is opened. `load` imports the module of the
 * page and returns its component, e.g.
 * `lazyPage(async () => (await import("./pages/MapPage.tsx")).MapPage)`.
 */
export function lazyPage(load: () => Promise<ComponentType>): LazyPage {
  const Page = lazy(async () => {
    try {
      return { default: await load() };
    } catch (error) {
      throw new PageLoadError(error);
    }
  });
  return {
    element: (
      <PageLoadBoundary>
        <Suspense fallback={<PageLoading />}>
          <Page />
        </Suspense>
      </PageLoadBoundary>
    ),
    preload: async () => {
      await load();
    },
  };
}
