import { type ReactElement, type ReactNode, useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import type { AiCheck, DatabaseCheck, WorkerCheck } from "../api/generated";
import { loadSelftest, type SelftestOutcome } from "../api/selftest.ts";
import { AnimatedHeading, LoadingText } from "../components/TextMotion.tsx";
import { Icon } from "../icons/Icon.tsx";

type PageState = { kind: "loading" } | SelftestOutcome;

/** Test page: shows the database, worker and AI checks of GET /api/v1/selftest/. */
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
          className="inline-flex items-center gap-2 rounded bg-accent px-4 py-2 text-on-accent hover:bg-accent-strong disabled:opacity-50"
        >
          <Icon name="retry" size={20} decorative />
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
          <Icon name="loading" className="mr-2 animate-spin text-fg-muted" decorative />
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
          <AiCard check={state.selftest.ai} />
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
      <Icon name="error" className="mr-2" decorative />
      {message}
    </p>
  );
}

function DatabaseCard({ check }: { check: DatabaseCheck }): ReactElement {
  const { t } = useTranslation("selftest");
  return (
    <Card heading={t("database.heading")} tone={check.ok ? "ok" : "failed"} testId="database">
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
    <Card heading={t("worker.heading")} tone={check.ok ? "ok" : "failed"} testId="worker">
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

/**
 * The AI features are optional (E-59): switched off is a neutral state, not an error,
 * so the card shows neither error colours nor a warning sign.
 */
function AiCard({ check }: { check: AiCheck }): ReactElement {
  const { t } = useTranslation("selftest");
  if (!check.enabled) {
    return (
      <Card
        heading={t("ai.heading")}
        tone="neutral"
        testId="ai"
        note={<span data-testid="ai-disabled">{t("ai.disabled")}</span>}
      />
    );
  }
  const ok = check.ok === true;
  return (
    <Card heading={t("ai.heading")} tone={ok ? "ok" : "failed"} testId="ai">
      <Field label={t("ai.model")}>
        <span data-testid="ai-model">{check.model ?? ""}</span>
      </Field>
      {ok ? (
        <Field label={t("ai.dimensions")}>
          <span data-testid="ai-dimensions">{t("ai.dimensionsValue", { dimensions: check.dimensions ?? 0 })}</span>
        </Field>
      ) : (
        <CheckError message={check.error ?? ""} testId="ai-error" />
      )}
    </Card>
  );
}

type Tone = "ok" | "failed" | "neutral";

const toneStyles: Record<Tone, { card: string; status: string }> = {
  ok: { card: "border-success-line bg-success-soft", status: "text-success" },
  failed: { card: "border-danger-line bg-danger-soft", status: "text-danger" },
  neutral: { card: "border-line bg-surface-muted", status: "text-fg-muted" },
};

const toneIcons = { ok: "success", failed: "error", neutral: "info" } as const;

function Card({
  heading,
  tone,
  testId,
  note,
  children,
}: {
  heading: string;
  tone: Tone;
  testId: string;
  note?: ReactNode;
  children?: ReactNode;
}): ReactElement {
  const { t } = useTranslation("selftest");
  const statusText = { ok: t("statusOk"), failed: t("statusFailed"), neutral: t("statusDisabled") }[tone];
  return (
    <article data-testid={`${testId}-check`} className={`rounded border p-4 ${toneStyles[tone].card}`}>
      <h3 className="flex items-center justify-between font-semibold">
        <span data-testid={`${testId}-heading`}>{heading}</span>
        {/* Status as icon and text, never by colour alone. */}
        <span data-testid={`${testId}-status`} className={`inline-flex items-center gap-1.5 ${toneStyles[tone].status}`}>
          <Icon name={toneIcons[tone]} decorative />
          {statusText}
        </span>
      </h3>
      {note === undefined ? null : <p className="mt-2 text-fg-muted">{note}</p>}
      {children === undefined ? null : <dl className="mt-2 space-y-1">{children}</dl>}
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
