import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

/** Page for an address the user interface does not know. */
export function NotFound(): ReactElement {
  const { t } = useTranslation("common");
  return (
    <section data-testid="not-found" className="space-y-4">
      <h2 className="text-2xl font-semibold">{t("notFound.heading")}</h2>
      <p className="text-slate-600">{t("notFound.text")}</p>
      <Link to="/" className="text-slate-900 underline">
        {t("notFound.home")}
      </Link>
    </section>
  );
}
