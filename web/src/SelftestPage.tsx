import { type ReactElement, type ReactNode, useCallback, useEffect, useState } from "react";

import type { DatabaseCheck, WorkerCheck } from "./api/generated";
import { loadSelftest, type SelftestOutcome } from "./api/selftest.ts";
import { texts } from "./texts.ts";

type PageState = { kind: "loading" } | SelftestOutcome;

/** Test page: shows the database and worker checks of GET /api/v1/selftest/. */
export function SelftestPage(): ReactElement {
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
        <h2 className="text-2xl font-semibold">{texts.selftest.heading}</h2>
        <button
          type="button"
          onClick={recheck}
          disabled={loading}
          className="rounded bg-slate-800 px-4 py-2 text-white disabled:opacity-50"
        >
          {loading ? texts.selftest.checking : texts.selftest.recheck}
        </button>
      </div>
      <p className="text-slate-600">{texts.selftest.intro}</p>
      <SelftestBody state={state} />
    </section>
  );
}

function SelftestBody({ state }: { state: PageState }): ReactElement {
  switch (state.kind) {
    case "loading":
      return (
        <p role="status" data-testid="selftest-loading">
          {texts.selftest.checking}
        </p>
      );
    case "unreachable":
      return <ApiError message={texts.selftest.apiUnreachable} />;
    case "http-error":
      return <ApiError message={texts.selftest.apiHttpError(state.status)} />;
    case "invalid-answer":
      return <ApiError message={texts.selftest.apiInvalidAnswer} />;
    case "unexpected-error":
      return <ApiError message={texts.selftest.unexpectedError} />;
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
      className="rounded border border-red-300 bg-red-50 p-4 text-red-800"
    >
      {message}
    </p>
  );
}

function DatabaseCard({ check }: { check: DatabaseCheck }): ReactElement {
  return (
    <Card heading={texts.selftest.database.heading} ok={check.ok} testId="database">
      {check.ok ? (
        <Field label={texts.selftest.database.serverVersion}>
          <span data-testid="database-version">{check.server_version}</span>
        </Field>
      ) : (
        <CheckError message={check.error} testId="database-error" />
      )}
    </Card>
  );
}

function WorkerCard({ check }: { check: WorkerCheck }): ReactElement {
  return (
    <Card heading={texts.selftest.worker.heading} ok={check.ok} testId="worker">
      {check.ok ? (
        <Field label={texts.selftest.worker.result}>
          <span data-testid="worker-result">{check.result}</span>
        </Field>
      ) : (
        <CheckError message={check.error} testId="worker-error" />
      )}
      <Field label={texts.selftest.worker.duration}>
        <span data-testid="worker-duration">
          {texts.selftest.worker.durationValue(check.duration_ms)}
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
  return (
    <article
      data-testid={`${testId}-check`}
      className={`rounded border p-4 ${ok ? "border-green-300 bg-green-50" : "border-red-300 bg-red-50"}`}
    >
      <h3 className="flex items-center justify-between font-semibold">
        {heading}
        <span data-testid={`${testId}-status`} className={ok ? "text-green-800" : "text-red-800"}>
          {ok ? texts.selftest.statusOk : texts.selftest.statusFailed}
        </span>
      </h3>
      <dl className="mt-2 space-y-1">{children}</dl>
    </article>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }): ReactElement {
  return (
    <div className="flex gap-2">
      <dt className="text-slate-600">{label}:</dt>
      <dd>{children}</dd>
    </div>
  );
}

function CheckError({ message, testId }: { message: string; testId: string }): ReactElement {
  return (
    <Field label={texts.selftest.errorLabel}>
      <span role="alert" data-testid={testId} className="text-red-800">
        {message}
      </span>
    </Field>
  );
}
