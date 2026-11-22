import type { ReactElement, ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, Outlet, useLocation } from "react-router";

import { Icon } from "../icons/Icon.tsx";
import { hasRole, loginPathFor, type Role, useRole, useSession } from "../session.ts";
import { usePageTitle } from "../hooks/usePageTitle.ts";
import { ErrorMessage } from "./ErrorMessage.tsx";
import { Loading } from "./Loading.tsx";
import { AnimatedHeading } from "./TextMotion.tsx";

/**
 * Route element around every page except /login: without a session it sends
 * the browser to the sign-in page, which returns to this address afterwards.
 */
export function RequireSession(): ReactElement {
  const session = useSession();
  const location = useLocation();
  switch (session.status) {
    case "loading":
      return <Loading />;
    case "error":
      return <ErrorMessage error={session.error} />;
    case "signed-out":
      return <Navigate to={loginPathFor(`${location.pathname}${location.search}${location.hash}`)} replace />;
    case "signed-in":
      return <Outlet />;
  }
}

/**
 * Shows `children` only to a user whose role includes `role`; everyone else
 * gets a "no permission" notice. No redirect and no sign-out: the session is
 * valid, only the permission is missing.
 */
export function RequireRole({ role, children }: { role: Role; children: ReactNode }): ReactElement {
  const access = useRole();
  if (hasRole(access.role, role)) {
    return <>{children}</>;
  }
  return <NoPermissionPage />;
}

/**
 * `RequireRole` replacing a whole page (work order 091): browser title and the
 * h1 of the page like every other page, above the notice.
 */
export function NoPermissionPage(): ReactElement {
  const { t } = useTranslation("auth");
  usePageTitle(t("noPermissionHeading"));
  return (
    <section data-testid="no-permission-page" className="space-y-4">
      <AnimatedHeading text={t("noPermissionHeading")} />
      <NoPermission />
    </section>
  );
}

/** Notice (no heading, no title) for a part of a page or an action the signed-in user's role does not allow. */
export function NoPermission(): ReactElement {
  const { t } = useTranslation("auth");
  return (
    <p role="alert" data-testid="no-permission" className="rounded border border-warning-line bg-warning-soft p-4 text-warning">
      <Icon name="noPermission" className="mr-2" decorative />
      {t("noPermission")}
    </p>
  );
}
