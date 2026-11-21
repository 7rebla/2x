import { type Selftest, selftestRetrieve } from "./generated";

/** Upper bound for one self-test call; the backend itself waits at most about 5 s per check. */
export const SELFTEST_TIMEOUT_MS = 15_000;

/** Result of one call to GET /api/v1/selftest/. */
export type SelftestOutcome =
  | { kind: "answered"; selftest: Selftest }
  | { kind: "unreachable" }
  | { kind: "http-error"; status: number };

/**
 * Calls the self-test endpoint through the generated client.
 *
 * The URL is relative (`/api/v1/selftest/`): UI and API share one origin.
 * Network errors and timeouts become "unreachable"; any non-2xx answer becomes "http-error".
 */
export async function loadSelftest(signal: AbortSignal): Promise<SelftestOutcome> {
  const result = await selftestRetrieve({
    signal: AbortSignal.any([signal, AbortSignal.timeout(SELFTEST_TIMEOUT_MS)]),
  });
  if (result.response === undefined) {
    return { kind: "unreachable" };
  }
  if (result.data === undefined || !result.response.ok) {
    return { kind: "http-error", status: result.response.status };
  }
  return { kind: "answered", selftest: result.data };
}
