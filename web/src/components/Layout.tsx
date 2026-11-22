import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, Outlet } from "react-router";

import { LanguageSwitch } from "../LanguageSwitch.tsx";
import { visibleNavigation } from "../navigation.ts";
import { useSession } from "../session.ts";
import { BrandMark } from "./BrandMark.tsx";
import { UserMenu } from "./UserMenu.tsx";

/**
 * Frame of every page: header with name, navigation, language switch and user
 * area. The navigation shows only the entries the signed-in user's role
 * allows; without a session (sign-in page) it is not shown at all.
 */
export function Layout(): ReactElement {
  const { t } = useTranslation(["common", "nav", "auth"]);
  const session = useSession();
  const user = session.status === "signed-in" ? session.user : null;
  const entries = user === null ? [] : visibleNavigation(user.role);
  return (
    <div className="flex min-h-screen flex-col bg-canvas text-fg">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center gap-x-8 gap-y-4 px-4 py-4">
          <h1 className="text-3xl font-semibold tracking-tight">
            <BrandMark />
          </h1>
          <div className="flex-1">
            {entries.length > 0 ? (
              <nav aria-label={t("nav:label")}>
                <ul className="flex flex-wrap gap-x-5 gap-y-2">
                  {entries.map((entry) => {
                    const label = t(`nav:${entry.textKey}`);
                    return (
                      <li key={entry.path}>
                        {/* Navigation line (pattern C): data-label reserves the width of the bold label. */}
                        <NavLink to={entry.path} end={entry.end ?? false} className="nav-link" data-label={label}>
                          {label}
                        </NavLink>
                      </li>
                    );
                  })}
                </ul>
              </nav>
            ) : null}
          </div>
          <LanguageSwitch />
          <div data-testid="user-area">{user === null ? null : <UserMenu user={user} />}</div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 space-y-4 px-4 py-8">
        {user !== null && user.role === null ? (
          <p role="status" data-testid="no-role" className="rounded border border-warning-line bg-warning-soft p-4 text-warning">
            {t("auth:noRole")}
          </p>
        ) : null}
        <Outlet />
      </main>
    </div>
  );
}
