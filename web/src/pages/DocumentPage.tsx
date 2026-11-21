import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router";

import { PagePlaceholder } from "../components/PagePlaceholder.tsx";

/** One file with its versions (address /documents/:documentId). Placeholder until work order 036. */
export function DocumentPage(): ReactElement {
  const { t } = useTranslation("nav");
  const { documentId } = useParams();
  return (
    <PagePlaceholder heading={t("document")}>
      <p data-testid="document-id" className="font-mono">
        {documentId}
      </p>
    </PagePlaceholder>
  );
}
