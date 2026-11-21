import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";

import { LanguageSwitch } from "./LanguageSwitch.tsx";
import { SelftestPage } from "./SelftestPage.tsx";

export function App(): ReactElement {
  const { t } = useTranslation("common");
  return (
    <main className="flex min-h-screen flex-col items-center gap-8 bg-slate-50 p-8 text-slate-900">
      <header className="flex w-full max-w-xl items-center justify-between gap-4">
        <h1 className="text-5xl font-semibold tracking-tight">{t("appTitle")}</h1>
        <LanguageSwitch />
      </header>
      <SelftestPage />
    </main>
  );
}
