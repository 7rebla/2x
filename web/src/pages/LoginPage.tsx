import { useQueryClient } from "@tanstack/react-query";
import { type ReactElement, type SubmitEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useSearchParams } from "react-router";

import { type SignInResult, signIn } from "../api/auth.ts";
import { openServerPage } from "../browserLocation.ts";
import { ErrorMessage } from "../components/ErrorMessage.tsx";
import { BrandMark } from "../components/BrandMark.tsx";
import { Loading } from "../components/Loading.tsx";
import { Button } from "../components/ui/Button.tsx";
import { Input } from "../components/ui/fields.tsx";
import { isServerPage, refreshSession, safeNextPath, useSession } from "../session.ts";
import { AnimatedHeading } from "../components/TextMotion.tsx";
import { usePageTitle } from "../hooks/usePageTitle.ts";

/** Why the last sign-in did not work; "missing-input" is checked before anything is sent. */
type Failure = Exclude<SignInResult, { kind: "signed-in" }> | { kind: "missing-input" };

/** Edge of the brand mark above the sign-in card (px); larger than in the header (36 px). */
export const CARD_BRAND_SIZE = 48;

/**
 * Sign-in page (address /login). Signs in through django-allauth and then
 * continues to ?next= (a path of this application only, see safeNextPath).
 * A user who is signed in already continues at once. The form is a centred
 * card (`max-w-sm`) with the brand mark and the name above it (work order
 * 086, E-65 point 7); fields and button are equally high and equally wide.
 */
export function LoginPage(): ReactElement {
  const { t } = useTranslation("auth");
  usePageTitle(t("heading"));
  const session = useSession();
  const [searchParams] = useSearchParams();
  const next = safeNextPath(searchParams.get("next"));

  if (session.status === "loading") {
    return <Loading />;
  }
  if (session.status === "signed-in") {
    return <Continue to={next} />;
  }
  return (
    <section data-testid="login-page" className="mx-auto w-full max-w-sm space-y-6 sm:pt-8">
      {/* The brand above the card (E-65 point 7); its name types like the one in the header (pattern E, run sign-in). */}
      <div className="flex justify-center text-4xl font-semibold tracking-tight">
        <BrandMark size={CARD_BRAND_SIZE} typing="sign-in" link={false} />
      </div>
      <div data-testid="login-card" className="space-y-4 rounded-lg border border-line bg-surface p-6 shadow-sm">
        <AnimatedHeading text={t("heading")} />
        <p className="text-fg-muted">{t("intro")}</p>
        {session.status === "error" ? <ErrorMessage error={session.error} /> : null}
        <LoginForm />
      </div>
    </section>
  );
}

/** Leaves the sign-in page: inside the web UI by the router, to the admin by a page load. */
function Continue({ to }: { to: string }): ReactElement {
  const { t } = useTranslation("auth");
  const serverPage = isServerPage(to);
  useEffect(() => {
    if (serverPage) {
      openServerPage(to);
    }
  }, [serverPage, to]);
  if (serverPage) {
    return <Loading label={t("continuing")} />;
  }
  return <Navigate to={to} replace />;
}

function LoginForm(): ReactElement {
  const { t } = useTranslation("auth");
  const queryClient = useQueryClient();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState<Failure | null>(null);

  const submit = async (): Promise<void> => {
    if (username.trim() === "" || password === "") {
      setFailure({ kind: "missing-input" });
      return;
    }
    setPending(true);
    setFailure(null);
    const result = await signIn(username.trim(), password);
    if (result.kind === "signed-in") {
      try {
        // On success the page re-renders as "signed in" and continues to ?next=.
        if ((await refreshSession(queryClient)) !== null) {
          return;
        }
        setFailure({ kind: "http-error", status: 403 });
      } catch {
        setFailure({ kind: "network" });
      }
    } else {
      setFailure(result);
    }
    setPending(false);
    setPassword("");
  };

  const onSubmit = (event: SubmitEvent<HTMLFormElement>): void => {
    event.preventDefault();
    void submit();
  };

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-4" data-testid="login-form">
      <label className="block space-y-1">
        <span className="text-sm text-fg-muted">{t("username")}</span>
        <Input
          name="username"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          required
          value={username}
          onChange={(event) => {
            setUsername(event.target.value);
          }}
          className="w-full"
        />
      </label>
      <label className="block space-y-1">
        <span className="text-sm text-fg-muted">{t("password")}</span>
        <Input
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => {
            setPassword(event.target.value);
          }}
          className="w-full"
        />
      </label>
      {failure === null ? null : <SignInError failure={failure} />}
      <Button type="submit" variant="primary" loading={pending} className="w-full">
        {pending ? t("submitting") : t("submit")}
      </Button>
    </form>
  );
}

function SignInError({ failure }: { failure: Failure }): ReactElement {
  return (
    <p
      role="alert"
      data-testid="login-error"
      data-reason={failure.kind}
      className="rounded border border-danger-line bg-danger-soft p-3 text-danger"
    >
      <FailureText failure={failure} />
    </p>
  );
}

function FailureText({ failure }: { failure: Failure }): string {
  const { t } = useTranslation("auth");
  switch (failure.kind) {
    case "wrong-credentials":
      return t("error.wrongCredentials");
    case "locked":
      return t("error.locked");
    case "rate-limited":
      return t("error.rateLimited");
    case "missing-input":
      return t("error.missingInput");
    case "invalid":
      return t("error.invalid");
    case "expired-page":
      return t("error.expiredPage");
    case "http-error":
      return t("error.http", { status: failure.status });
    case "network":
      return t("error.network");
  }
}
