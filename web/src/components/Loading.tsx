import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";

import { Icon } from "../icons/Icon.tsx";
import { LoadingText } from "./TextMotion.tsx";

/** Loading state of a page or a part of it (turning icon and loading shimmer, pattern D; both stand still with reduced motion). */
export function Loading({ label }: { label?: string }): ReactElement {
  const { t } = useTranslation("common");
  return (
    <p role="status" data-testid="loading" className="text-fg-muted">
      <Icon name="loading" className="mr-2 animate-spin" decorative />
      <LoadingText text={label ?? t("loading")} />
    </p>
  );
}
