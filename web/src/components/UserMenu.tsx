import { useQueryClient } from "@tanstack/react-query";
import { type ReactElement, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

import { signOut } from "../api/auth.ts";
import type { Me } from "../api/generated";
import { dropUserData, forgetSession, LOGIN_PAGE_PATH } from "../session.ts";

/** Signed-in user, role and the sign-out button in the page header. */
export function UserMenu({ user }: { user: Me }): ReactElement {
  const { t } = useTranslation("auth");
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
      <span className="text-slate-600">
        {t("signedInAs")} <strong data-testid="user-name" className="text-slate-900">{user.username}</strong>
      </span>
      <span className="text-slate-600">
        {t("roleLabel")}:{" "}
        <span data-testid="user-role" className="text-slate-900">
          {user.role === null ? t("role.none") : t(`role.${user.role}`)}
        </span>
      </span>
      <button
        type="button"
        onClick={() => void onSignOut()}
        disabled={pending}
        data-testid="sign-out"
        className="rounded border border-slate-300 px-3 py-1 text-slate-900 hover:bg-slate-100 disabled:opacity-50"
      >
        {pending ? t("signingOut") : t("signOut")}
      </button>
      {failed ? (
        <span role="alert" data-testid="sign-out-error" className="text-red-800">
          {t("error.signOutFailed")}
        </span>
      ) : null}
    </div>
  );
}
