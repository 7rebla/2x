import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";

/** Loading state of a page or a part of it. */
export function Loading({ label }: { label?: string }): ReactElement {
  const { t } = useTranslation("common");
  return (
    <p role="status" data-testid="loading" className="text-slate-600">
      {label ?? t("loading")}
    </p>
  );
}
