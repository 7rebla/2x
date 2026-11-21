import { type ReactElement, useId } from "react";
import { useTranslation } from "react-i18next";

/**
 * Files of a device on the device page. Placeholder: work order 036 replaces
 * this component (same name and props) with the list and upload of files.
 */
export function DeviceFiles({ deviceId }: { deviceId: number }): ReactElement {
  const { t } = useTranslation("assets");
  const headingId = useId();
  return (
    <section
      aria-labelledby={headingId}
      data-testid="device-files"
      data-device-id={deviceId}
      className="space-y-2 rounded border border-slate-200 bg-white p-4"
    >
      <h3 id={headingId} className="font-semibold">
        {t("files.heading")}
      </h3>
      <p className="text-slate-600">{t("files.placeholder")}</p>
    </section>
  );
}
