// The note "Limited to: device …" above the form of the answer page (work
// order 133), with a button that lifts the limit. It is not a live region:
// it only changes when the address does.
import { useQuery } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";

import { devicesListOptions, plantsListOptions } from "../../api/generated/@tanstack/react-query.gen.ts";
import { Button } from "../../components/ui/Button.tsx";
import { Icon } from "../../icons/Icon.tsx";
import type { ScopeAddress } from "./scope.ts";

/** Nothing without a limit. The lists are the ones the form loads as well (same query keys). */
export function ScopeChip({ scope, onReset }: { scope: ScopeAddress; onReset: () => void }): ReactElement | null {
  const { t } = useTranslation("answers");
  const devices = useQuery(devicesListOptions());
  const plants = useQuery(plantsListOptions());

  let kind: string;
  let name: string;
  if (scope.device !== null) {
    const id = scope.device;
    const found = devices.data?.find((item) => item.id === id);
    kind = t("scope.kindDevice");
    // "Unknown" once the list lacks the id; the bare id while it loads or failed.
    name =
      found !== undefined
        ? `${found.name} (${found.key})`
        : devices.isSuccess
          ? t("scope.unknownDevice", { id })
          : t("scope.byId", { id });
  } else if (scope.plant !== null) {
    const id = scope.plant;
    const found = plants.data?.find((item) => item.id === id);
    kind = t("scope.kindPlant");
    name =
      found !== undefined ? found.name : plants.isSuccess ? t("scope.unknownPlant", { id }) : t("scope.byId", { id });
  } else {
    return null;
  }

  return (
    <div
      data-testid="answer-scope"
      className="flex max-w-prose flex-wrap items-center gap-x-3 gap-y-2 rounded border border-line bg-surface px-3 py-2 text-sm"
    >
      <p className="min-w-0 flex-1 break-words">
        <Icon name="filter" className="mr-2 text-fg-muted" decorative />
        {`${t("scope.limitedTo")} ${kind} `}
        <strong data-testid="answer-scope-name">{name}</strong>
      </p>
      <Button type="button" size="sm" icon="resetFilter" data-testid="answer-scope-reset" onClick={onReset}>
        {t("scope.reset")}
      </Button>
    </div>
  );
}
