import type { ReactElement, ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { AnimatedHeading } from "./TextMotion.tsx";

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
      <AnimatedHeading text={heading} />
      {children}
      <p className="text-fg-muted">{t("placeholder")}</p>
    </section>
  );
}
