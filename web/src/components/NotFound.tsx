import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { AnimatedHeading } from "./TextMotion.tsx";

/** Page for an address the user interface does not know. */
export function NotFound(): ReactElement {
  const { t } = useTranslation("common");
  return (
    <section data-testid="not-found" className="space-y-4">
      <AnimatedHeading text={t("notFound.heading")} />
      <p className="text-fg-muted">{t("notFound.text")}</p>
      <Link to="/" className="text-accent underline hover:text-accent-strong">
        {t("notFound.home")}
      </Link>
    </section>
  );
}
