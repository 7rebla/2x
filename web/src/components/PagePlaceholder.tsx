import type { ReactElement, ReactNode } from "react";
import { useTranslation } from "react-i18next";

/** Stand-in for a page that a later work order builds. */
export function PagePlaceholder({
  heading,
  children,
}: {
  heading: string;
  children?: ReactNode;
}): ReactElement {
  const { t } = useTranslation("common");
  return (
    <section data-testid="page-placeholder" className="space-y-4">
      <h2 className="text-2xl font-semibold">{heading}</h2>
      {children}
      <p className="text-slate-600">{t("placeholder")}</p>
    </section>
  );
}
