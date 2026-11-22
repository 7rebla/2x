import { type Selftest, selftestRetrieve } from "./generated";

/** Upper bound for one self-test call; the backend itself waits at most about 5 s per check. */
export const SELFTEST_TIMEOUT_MS = 15_000;

/** Result of one call to GET /api/v1/selftest/. */
export type SelftestOutcome =
  | { kind: "answered"; selftest: Selftest }
  | { kind: "unreachable" }
  | { kind: "http-error"; status: number }
  | { kind: "invalid-answer" }
  | { kind: "unexpected-error" };

/**
 * Calls the self-test endpoint through the generated client.
 *
 * The URL is relative (`/api/v1/selftest/`): UI and API share one origin.
 * Network errors and timeouts become "unreachable", any non-2xx answer becomes "http-error",
 * and a 2xx answer that is not the expected JSON object becomes "invalid-answer"
 * (for example an HTML page from a proxy or a dev server).
 * The timeout uses AbortController and setTimeout only, so older browsers are not excluded.
 */
export async function loadSelftest(signal: AbortSignal): Promise<SelftestOutcome> {
  const controller = new AbortController();
  const abort = (): void => {
    controller.abort();
  };
  const timer = setTimeout(abort, SELFTEST_TIMEOUT_MS);
  if (signal.aborted) {
    abort();
  } else {
    signal.addEventListener("abort", abort, { once: true });
  }
  try {
    return await requestSelftest(controller.signal);
  } finally {
    clearTimeout(timer);
    signal.removeEventListener("abort", abort);
  }
}

async function requestSelftest(signal: AbortSignal): Promise<SelftestOutcome> {
  const result = await selftestRetrieve({ parseAs: "json", signal });
  if (result.response === undefined) {
    return { kind: "unreachable" };
  }
  if (!result.response.ok) {
    return { kind: "http-error", status: result.response.status };
  }
  if (!hasAllChecks(result.data)) {
    return { kind: "invalid-answer" };
  }
  return { kind: "answered", selftest: result.data };
}

/** Guards the page against answers that do not have the shape of the generated type. */
function hasAllChecks(data: Selftest | undefined): data is Selftest {
  const value: unknown = data;
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return isObject(record.database) && isObject(record.worker) && isObject(record.ai);
}

function isObject(value: unknown): boolean {
  return typeof value === "object" && value !== null;
}
