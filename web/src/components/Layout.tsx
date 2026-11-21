import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet } from "react-router";

import { LanguageSwitch } from "../LanguageSwitch.tsx";
import { visibleNavigation } from "../navigation.ts";
import { useSession } from "../session.ts";
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
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center gap-x-8 gap-y-4 px-4 py-4">
          <h1 className="text-3xl font-semibold tracking-tight">
            <Link to="/">{t("common:appTitle")}</Link>
          </h1>
          <div className="flex-1">
            {entries.length > 0 ? (
              <nav aria-label={t("nav:label")}>
                <ul className="flex flex-wrap gap-x-4 gap-y-2">
                  {entries.map((entry) => (
                    <li key={entry.path}>
                      <NavLink
                        to={entry.path}
                        end={entry.end ?? false}
                        className={({ isActive }) =>
                          isActive
                            ? "font-semibold text-slate-900 underline underline-offset-4"
                            : "text-slate-600 hover:text-slate-900"
                        }
                      >
                        {t(`nav:${entry.textKey}`)}
                      </NavLink>
                    </li>
                  ))}
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
          <p role="status" data-testid="no-role" className="rounded border border-amber-300 bg-amber-50 p-4 text-amber-900">
            {t("auth:noRole")}
          </p>
        ) : null}
        <Outlet />
      </main>
    </div>
  );
}
