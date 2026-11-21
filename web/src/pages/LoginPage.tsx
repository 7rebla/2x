import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";

import { PagePlaceholder } from "../components/PagePlaceholder.tsx";

/** Sign-in page (address /login). Placeholder until work order 030. */
export function LoginPage(): ReactElement {
  const { t } = useTranslation("nav");
  return <PagePlaceholder heading={t("login")} />;
}
