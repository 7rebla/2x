import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router";

import { PagePlaceholder } from "../components/PagePlaceholder.tsx";

/** One device (address /devices/:deviceId). Placeholder until work order 032. */
export function DevicePage(): ReactElement {
  const { t } = useTranslation("nav");
  const { deviceId } = useParams();
  return (
    <PagePlaceholder heading={t("device")}>
      <p data-testid="device-id" className="font-mono">
        {deviceId}
      </p>
    </PagePlaceholder>
  );
}
