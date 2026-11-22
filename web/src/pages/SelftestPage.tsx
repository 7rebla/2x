import { type ReactElement, type ReactNode, useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import type { DatabaseCheck, WorkerCheck } from "../api/generated";
import { loadSelftest, type SelftestOutcome } from "../api/selftest.ts";
import { AnimatedHeading, LoadingText } from "../components/TextMotion.tsx";

type PageState = { kind: "loading" } | SelftestOutcome;

/** Test page: shows the database and worker checks of GET /api/v1/selftest/. */
export function SelftestPage(): ReactElement {
  const { t } = useTranslation("selftest");
  const [state, setState] = useState<PageState>({ kind: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    // Any error outside the generated client must end in a visible state, never in endless loading.
    const outcome = loadSelftest(controller.signal).catch(
      (): SelftestOutcome => ({ kind: "unexpected-error" }),
    );
    void outcome.then((result) => {
      if (!controller.signal.aborted) {
        setState(result);
      }
    });
    return () => {
      controller.abort();
    };
  }, [attempt]);

  const recheck = useCallback((): void => {
    setState({ kind: "loading" });
    setAttempt((previous) => previous + 1);
  }, []);

  const loading = state.kind === "loading";

  return (
    <section className="w-full max-w-xl space-y-4" aria-busy={loading}>
      <div className="flex items-center justify-between gap-4">
        <AnimatedHeading text={t("heading")} />
        <button
          type="button"
          onClick={recheck}
          disabled={loading}
          className="rounded bg-accent px-4 py-2 text-on-accent hover:bg-accent-strong disabled:opacity-50"
        >
          {loading ? t("checking") : t("recheck")}
        </button>
      </div>
      <p className="text-fg-muted">{t("intro")}</p>
      <SelftestBody state={state} />
    </section>
  );
}

function SelftestBody({ state }: { state: PageState }): ReactElement {
  const { t } = useTranslation(["selftest", "auth"]);
  switch (state.kind) {
    case "loading":
      return (
        <p role="status" data-testid="selftest-loading">
          <LoadingText text={t("checking")} />
        </p>
      );
    case "unreachable":
      return <ApiError message={t("apiUnreachable")} />;
    case "http-error":
      // 403 with a valid session: the role is missing (an expired session
      // leads to the sign-in page instead, see session.ts).
      return (
        <ApiError
          message={state.status === 403 ? t("auth:noPermission") : t("apiHttpError", { status: state.status })}
        />
      );
    case "invalid-answer":
      return <ApiError message={t("apiInvalidAnswer")} />;
    case "unexpected-error":
      return <ApiError message={t("unexpectedError")} />;
    case "answered":
      return (
        <div className="space-y-4">
          <DatabaseCard check={state.selftest.database} />
          <WorkerCard check={state.selftest.worker} />
        </div>
      );
  }
}

function ApiError({ message }: { message: string }): ReactElement {
  return (
    <p
      role="alert"
      data-testid="selftest-error"
      className="rounded border border-danger-line bg-danger-soft p-4 text-danger"
    >
      {message}
    </p>
  );
}

function DatabaseCard({ check }: { check: DatabaseCheck }): ReactElement {
  const { t } = useTranslation("selftest");
  return (
    <Card heading={t("database.heading")} ok={check.ok} testId="database">
      {check.ok ? (
        <Field label={t("database.serverVersion")}>
          <span data-testid="database-version">{check.server_version}</span>
        </Field>
      ) : (
        <CheckError message={check.error} testId="database-error" />
      )}
    </Card>
  );
}

function WorkerCard({ check }: { check: WorkerCheck }): ReactElement {
  const { t } = useTranslation("selftest");
  return (
    <Card heading={t("worker.heading")} ok={check.ok} testId="worker">
      {check.ok ? (
        <Field label={t("worker.result")}>
          <span data-testid="worker-result">{check.result}</span>
        </Field>
      ) : (
        <CheckError message={check.error} testId="worker-error" />
      )}
      <Field label={t("worker.duration")}>
        <span data-testid="worker-duration">
          {t("worker.durationValue", { duration: check.duration_ms })}
        </span>
      </Field>
    </Card>
  );
}

function Card({
  heading,
  ok,
  testId,
  children,
}: {
  heading: string;
  ok: boolean;
  testId: string;
  children: ReactNode;
}): ReactElement {
  const { t } = useTranslation("selftest");
  return (
    <article
      data-testid={`${testId}-check`}
      className={`rounded border p-4 ${ok ? "border-success-line bg-success-soft" : "border-danger-line bg-danger-soft"}`}
    >
      <h3 className="flex items-center justify-between font-semibold">
        <span data-testid={`${testId}-heading`}>{heading}</span>
        <span data-testid={`${testId}-status`} className={ok ? "text-success" : "text-danger"}>
          {ok ? t("statusOk") : t("statusFailed")}
        </span>
      </h3>
      <dl className="mt-2 space-y-1">{children}</dl>
    </article>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }): ReactElement {
  return (
    <div className="flex gap-2">
      <dt className="text-fg-muted">{label}:</dt>
      <dd>{children}</dd>
    </div>
  );
}

function CheckError({ message, testId }: { message: string; testId: string }): ReactElement {
  const { t } = useTranslation("selftest");
  return (
    <Field label={t("errorLabel")}>
      <span role="alert" data-testid={testId} className="text-danger">
        {message}
      </span>
    </Field>
  );
}
