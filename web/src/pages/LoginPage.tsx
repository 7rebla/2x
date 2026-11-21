import { useQueryClient } from "@tanstack/react-query";
import { type ReactElement, type SubmitEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useSearchParams } from "react-router";

import { type SignInResult, signIn } from "../api/auth.ts";
import { openServerPage } from "../browserLocation.ts";
import { ErrorMessage } from "../components/ErrorMessage.tsx";
import { Loading } from "../components/Loading.tsx";
import { isServerPage, refreshSession, safeNextPath, useSession } from "../session.ts";

/** Why the last sign-in did not work; "missing-input" is checked before anything is sent. */
type Failure = Exclude<SignInResult, { kind: "signed-in" }> | { kind: "missing-input" };

/**
 * Sign-in page (address /login). Signs in through django-allauth and then
 * continues to ?next= (a path of this application only, see safeNextPath).
 * A user who is signed in already continues at once.
 */
export function LoginPage(): ReactElement {
  const { t } = useTranslation("auth");
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
    <section className="w-full max-w-sm space-y-4">
      <h2 className="text-2xl font-semibold">{t("heading")}</h2>
      <p className="text-slate-600">{t("intro")}</p>
      {session.status === "error" ? <ErrorMessage error={session.error} /> : null}
      <LoginForm />
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
        <span className="text-sm text-slate-600">{t("username")}</span>
        <input
          name="username"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          required
          value={username}
          onChange={(event) => {
            setUsername(event.target.value);
          }}
          className="w-full rounded border border-slate-300 bg-white px-3 py-2"
        />
      </label>
      <label className="block space-y-1">
        <span className="text-sm text-slate-600">{t("password")}</span>
        <input
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => {
            setPassword(event.target.value);
          }}
          className="w-full rounded border border-slate-300 bg-white px-3 py-2"
        />
      </label>
      {failure === null ? null : <SignInError failure={failure} />}
      <button
        type="submit"
        disabled={pending}
        className="rounded bg-slate-800 px-4 py-2 text-white disabled:opacity-50"
      >
        {pending ? t("submitting") : t("submit")}
      </button>
    </form>
  );
}

function SignInError({ failure }: { failure: Failure }): ReactElement {
  return (
    <p
      role="alert"
      data-testid="login-error"
      data-reason={failure.kind}
      className="rounded border border-red-300 bg-red-50 p-3 text-red-800"
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
