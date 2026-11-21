import { QueryClient } from "@tanstack/react-query";

import { ApiError } from "./errors.ts";

/** How often a query is tried again after the API did not answer at all. */
export const NETWORK_RETRIES = 2;

/**
 * Only a missing answer is worth another try. An HTTP error (403, 404, 500 …)
 * or an unreadable answer comes back the same way, so it is shown at once.
 */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  return error instanceof ApiError && error.kind === "network" && failureCount < NETWORK_RETRIES;
}

/** Cache and fetch rules for all pages. One instance per app (and per test). */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: shouldRetry },
      mutations: { retry: false },
    },
  });
}
