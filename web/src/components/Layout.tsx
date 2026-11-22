import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet } from "react-router";

import { Icon } from "../icons/Icon.tsx";
import { LanguageSwitch } from "../LanguageSwitch.tsx";
import { visibleNavigation } from "../navigation.ts";
import { useSession } from "../session.ts";
import { UserMenu } from "./UserMenu.tsx";

/**
 * Frame of every page: header with name, navigation and user menu (before
 * sign-in: the language switch). The navigation shows only the entries the
 * signed-in user's role allows; without a session (sign-in page) it is not
 * shown at all.
 */
export function Layout(): ReactElement {
  const { t } = useTranslation(["common", "nav", "auth"]);
  const session = useSession();
  const user = session.status === "signed-in" ? session.user : null;
  const entries = user === null ? [] : visibleNavigation(user.role);
  return (
    <div className="flex min-h-screen flex-col bg-canvas text-fg">
      <header className="border-b border-line bg-surface">
        {/*
          One line in every language and at every width: the navigation never
          wraps; below 1024 px its entries shrink to their icons (the text
          stays as accessible name and tooltip), and if even that does not
          fit, the navigation scrolls on its own instead of the page.
        */}
        <div className="mx-auto flex w-full max-w-5xl items-center gap-x-6 px-4 py-4">
          <h1 className="text-3xl font-semibold tracking-tight">
            <Link to="/">{t("common:appTitle")}</Link>
          </h1>
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
                          <span className="nav-label max-lg:sr-only" data-label={label}>
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
      <main className="mx-auto w-full max-w-5xl flex-1 space-y-4 px-4 py-8">
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
