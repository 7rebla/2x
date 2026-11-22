import { useQueryClient } from "@tanstack/react-query";
import { type KeyboardEvent, type ReactElement, useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { NavLink, useLocation, useNavigate } from "react-router";

import { signOut } from "../api/auth.ts";
import type { Me } from "../api/generated";
import { Icon } from "../icons/Icon.tsx";
import { LanguageSwitch } from "../LanguageSwitch.tsx";
import { dropUserData, forgetSession, hasRole, LOGIN_PAGE_PATH } from "../session.ts";

/**
 * User menu in the page header: a button with the user name opens a small
 * panel with role, the link to the settings, the language and the sign-out
 * button. The panel closes on Escape, on a click outside and on every change
 * of the address, so a link in it never leaves it open.
 */
export function UserMenu({ user }: { user: Me }): ReactElement {
  const { t } = useTranslation(["auth", "nav"]);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const panelId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  // The panel is open only for the address it was opened on.
  const [openOn, setOpenOn] = useState<string | null>(null);
  const open = openOn === location.key;
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!open) {
      return undefined;
    }
    const onPointerDown = (event: PointerEvent): void => {
      if (event.target instanceof Node && rootRef.current?.contains(event.target) !== true) {
        setOpenOn(null);
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [open]);

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>): void => {
    if (event.key === "Escape" && open) {
      setOpenOn(null);
      buttonRef.current?.focus();
    }
  };

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

  const roleText = user.role === null ? t("role.none") : t(`role.${user.role}`);

  return (
    <div ref={rootRef} className="relative" onKeyDown={onKeyDown}>
      <button
        ref={buttonRef}
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        aria-label={`${t("userMenu")}: ${user.username}`}
        data-testid="user-menu-button"
        onClick={() => {
          setOpenOn(open ? null : location.key);
        }}
        className="inline-flex max-w-48 items-center gap-2 whitespace-nowrap rounded px-2 py-1 text-sm text-fg hover:bg-surface-muted"
      >
        <Icon name="user" size={20} decorative />
        {/* On narrow screens only the icon shows; the button keeps its name through aria-label. */}
        <strong data-testid="user-name" className="truncate font-semibold max-sm:sr-only">
          {user.username}
        </strong>
      </button>
      <div
        id={panelId}
        hidden={!open}
        data-testid="user-menu"
        className="absolute right-0 top-full z-20 mt-2 w-64 space-y-3 rounded border border-line bg-surface p-3 text-sm shadow-lg"
      >
        <dl className="space-y-1">
          <div className="flex gap-1">
            <dt className="text-fg-muted">{t("signedInAs")}</dt>
            <dd className="truncate font-semibold">{user.username}</dd>
          </div>
          <div className="flex gap-1">
            <dt className="text-fg-muted">{t("roleLabel")}:</dt>
            <dd data-testid="user-role">{roleText}</dd>
          </div>
        </dl>
        {/* Settings of this browser (work order 070); like every page they need a role. */}
        {hasRole(user.role, "read") ? (
          <NavLink to="/settings" data-testid="settings-link" className="nav-link">
            <Icon name="settings" size={20} decorative />
            <span className="nav-label" data-label={t("nav:settings")}>
              {t("nav:settings")}
            </span>
          </NavLink>
        ) : null}
        <LanguageSwitch />
        <button
          type="button"
          onClick={() => void onSignOut()}
          disabled={pending}
          data-testid="sign-out"
          className="inline-flex items-center gap-2 rounded border border-line-strong px-3 py-1 text-fg hover:bg-surface-muted disabled:opacity-50"
        >
          <Icon name="signOut" decorative />
          {pending ? t("signingOut") : t("signOut")}
        </button>
        {failed ? (
          <p role="alert" data-testid="sign-out-error" className="text-danger">
            <Icon name="error" className="mr-2" decorative />
            {t("error.signOutFailed")}
          </p>
        ) : null}
      </div>
    </div>
  );
}
