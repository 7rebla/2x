import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";

import { PagePlaceholder } from "../components/PagePlaceholder.tsx";

/** Structure of sites, areas, plants and devices (address /). Placeholder until work order 032. */
export function StructurePage(): ReactElement {
  const { t } = useTranslation("nav");
  return <PagePlaceholder heading={t("structure")} />;
}
