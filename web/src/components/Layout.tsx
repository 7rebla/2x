import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet } from "react-router";

import { LanguageSwitch } from "../LanguageSwitch.tsx";
import { navigation } from "../navigation.ts";

/** Frame of every page: header with name, navigation, language switch and user area. */
export function Layout(): ReactElement {
  const { t } = useTranslation(["common", "nav"]);
  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-5xl flex-wrap items-center gap-x-8 gap-y-4 px-4 py-4">
          <h1 className="text-3xl font-semibold tracking-tight">
            <Link to="/">{t("common:appTitle")}</Link>
          </h1>
          <nav aria-label={t("nav:label")} className="flex-1">
            <ul className="flex flex-wrap gap-x-4 gap-y-2">
              {navigation.map((entry) => (
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
          <LanguageSwitch />
          {/* Signed-in user and sign-out; filled by work order 030. */}
          <div data-testid="user-area" />
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
