import type { ReactElement } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../api/errors.ts";
import { Icon, type IconProps } from "../icons/Icon.tsx";

/**
 * Error state of a page or a part of it. For an API error it shows the HTTP
 * status and, if the API sent one, its error text (shown as sent: it is data).
 */
export function ErrorMessage({ error }: { error: unknown }): ReactElement {
  const { t } = useTranslation(["common", "auth"]);

  let summary: string;
  let icon: IconProps["name"] = "error";
  let detail: string | null = null;
  if (error instanceof ApiError) {
    detail = error.detail;
    if (error.kind === "http" && error.status === 403) {
      // A 403 with a valid session (an expired one leads to the sign-in page,
      // see session.ts): the role does not allow this.
      summary = t("auth:noPermission");
      icon = "noPermission";
    } else if (error.kind === "http" && error.status !== null) {
      summary = t("error.http", { status: error.status });
    } else if (error.kind === "network") {
      summary = t("error.network");
    } else {
      summary = t("error.invalidAnswer");
    }
  } else {
    summary = t("error.unexpected");
  }

  return (
    <div
      role="alert"
      data-testid="error-message"
      className="space-y-1 rounded border border-danger-line bg-danger-soft p-4 text-danger"
    >
      <p data-testid="error-summary">
        <Icon name={icon} className="mr-2" decorative />
        {summary}
      </p>
      {detail === null ? null : (
        <p className="text-sm">
          {t("error.detailLabel")}: <span data-testid="error-detail">{detail}</span>
        </p>
      )}
    </div>
  );
}
