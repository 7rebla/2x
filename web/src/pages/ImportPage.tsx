import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";

import { PagePlaceholder } from "../components/PagePlaceholder.tsx";

/** Import of the device list and of documents (address /import). Placeholder until work order 035. */
export function ImportPage(): ReactElement {
  const { t } = useTranslation("nav");
  return <PagePlaceholder heading={t("import")} />;
}
