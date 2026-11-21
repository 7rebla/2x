import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";

import { PagePlaceholder } from "../components/PagePlaceholder.tsx";

/** Change log (address /audit). Placeholder until work order 033. */
export function AuditPage(): ReactElement {
  const { t } = useTranslation("nav");
  return <PagePlaceholder heading={t("audit")} />;
}
