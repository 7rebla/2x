import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";

import { LoadingText } from "./TextMotion.tsx";

/** Loading state of a page or a part of it (with the loading shimmer, pattern D). */
export function Loading({ label }: { label?: string }): ReactElement {
  const { t } = useTranslation("common");
  return (
    <p role="status" data-testid="loading" className="text-fg-muted">
      <LoadingText text={label ?? t("loading")} />
    </p>
  );
}
