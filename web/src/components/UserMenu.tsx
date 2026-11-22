import { useQueryClient } from "@tanstack/react-query";
import { type ReactElement, useState } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, useNavigate } from "react-router";

import { signOut } from "../api/auth.ts";
import type { Me } from "../api/generated";
import { dropUserData, forgetSession, hasRole, LOGIN_PAGE_PATH } from "../session.ts";

/** Signed-in user, role, the link to the settings and the sign-out button in the page header. */
export function UserMenu({ user }: { user: Me }): ReactElement {
  const { t } = useTranslation(["auth", "nav"]);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);

  const onSignOut = async (): Promise<void> => {
    setPending(true);
    setFailed(false);
    const result = await signOut();
    if (result.kind !== "signed-out") {
      setPending(false);
      setFailed(true);
      return;
    }
    // Signed out on the server: forget the user first, so that the sign-in
    // page does not send the browser straight back, then drop the old data.
    forgetSession(queryClient);
    await navigate(LOGIN_PAGE_PATH, { replace: true });
    dropUserData(queryClient);
  };

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
      <span className="text-fg-muted">
        {t("signedInAs")} <strong data-testid="user-name" className="text-fg">{user.username}</strong>
      </span>
      <span className="text-fg-muted">
        {t("roleLabel")}:{" "}
        <span data-testid="user-role" className="text-fg">
          {user.role === null ? t("role.none") : t(`role.${user.role}`)}
        </span>
      </span>
      {/* Settings of this browser (work order 070); like every page they need a role. */}
      {hasRole(user.role, "read") ? (
        <NavLink to="/settings" data-testid="settings-link" className="nav-link" data-label={t("nav:settings")}>
          {t("nav:settings")}
        </NavLink>
      ) : null}
      <button
        type="button"
        onClick={() => void onSignOut()}
        disabled={pending}
        data-testid="sign-out"
        className="rounded border border-line-strong px-3 py-1 text-fg hover:bg-surface-muted disabled:opacity-50"
      >
        {pending ? t("signingOut") : t("signOut")}
      </button>
      {failed ? (
        <span role="alert" data-testid="sign-out-error" className="text-danger">
          {t("error.signOutFailed")}
        </span>
      ) : null}
    </div>
  );
}
