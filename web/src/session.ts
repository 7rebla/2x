// Sign-in state of the web UI: who is signed in and with which role.
//
// The state comes from GET /api/v1/me/ (one TanStack query, key
// sessionQueryKey). DRF answers a missing sign-in with 403, not 401
// (SessionAuthentication), so 403 from /api/v1/me/ means "signed out". A 403
// from any other call only says "not allowed" or "session expired"; the
// listener from watchForbidden asks /api/v1/me/ again to tell the two apart.
import { type QueryClient, queryOptions, useQuery } from "@tanstack/react-query";

import { onForbidden } from "./api/client.ts";
import { ApiError } from "./api/errors.ts";
import { type Me, meRetrieve, type RoleEnum } from "./api/generated";

/** Role of a user (E-40): "manage" may read and write, "read" may only read. */
export type Role = RoleEnum;

export const sessionQueryKey = ["session", "me"] as const;

/** How long the answer of /api/v1/me/ counts as fresh; a 403 of any call asks again at once. */
export const SESSION_STALE_MS = 60_000;

function isMe(value: unknown): value is Me {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    typeof record.username === "string" &&
    (record.role === null || record.role === "manage" || record.role === "read") &&
    typeof record.is_superuser === "boolean"
  );
}

/** The signed-in user, or null if nobody is signed in (403). Other failures throw an ApiError. */
export async function loadSession(signal?: AbortSignal): Promise<Me | null> {
  let data: unknown;
  try {
    ({ data } = await meRetrieve({ signal, throwOnError: true }));
  } catch (error) {
    if (error instanceof ApiError && error.kind === "http" && error.status === 403) {
      return null;
    }
    throw error;
  }
  if (!isMe(data)) {
    throw new ApiError("invalid-answer", 200, null);
  }
  return data;
}

/** Query of the sign-in state; every component that needs it shares this one query. */
export const sessionQuery = queryOptions({
  queryKey: sessionQueryKey,
  queryFn: ({ signal }): Promise<Me | null> => loadSession(signal),
  staleTime: SESSION_STALE_MS,
});

/** Asks /api/v1/me/ now (after signing in) and stores the answer. */
export async function refreshSession(queryClient: QueryClient): Promise<Me | null> {
  return queryClient.query({ ...sessionQuery, staleTime: 0 });
}

/** After signing out: nobody is signed in (without asking the API again). */
export function forgetSession(queryClient: QueryClient): void {
  queryClient.setQueryData(sessionQueryKey, null);
}

/** Removes every cached answer except the sign-in state. */
export function dropUserData(queryClient: QueryClient): void {
  queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== sessionQueryKey[0] });
}

/**
 * After a 403 of any API call, asks /api/v1/me/ again: if that is 403 too, the
 * session has expired and the guard sends the user to the sign-in page; if it
 * is 200, only the permission is missing and the page shows its error.
 * Returns the function that stops watching.
 */
export function watchForbidden(queryClient: QueryClient): () => void {
  return onForbidden(() => {
    void queryClient.invalidateQueries({ queryKey: sessionQueryKey });
  });
}

export type Session =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "signed-out" }
  | { status: "signed-in"; user: Me };

/** The current sign-in state. A failed re-check keeps a known user signed in. */
export function useSession(): Session {
  const query = useQuery(sessionQuery);
  if (query.data === null) {
    return { status: "signed-out" };
  }
  if (query.data !== undefined) {
    return { status: "signed-in", user: query.data };
  }
  if (query.isError) {
    return { status: "error", error: query.error };
  }
  return { status: "loading" };
}

/** True if `role` includes the rights of `required` ("manage" includes "read"). */
export function hasRole(role: Role | null, required: Role): boolean {
  if (role === null) {
    return false;
  }
  return role === "manage" || required === "read";
}

export interface RoleAccess {
  /** Role of the signed-in user; null if nobody is signed in or the account has no role. */
  readonly role: Role | null;
  readonly canRead: boolean;
  /** Only users with "manage" see buttons that write. */
  readonly canManage: boolean;
}

/** Role of the signed-in user, for pages that show or hide actions. */
export function useRole(): RoleAccess {
  const session = useSession();
  const role = session.status === "signed-in" ? session.user.role : null;
  return { role, canRead: hasRole(role, "read"), canManage: hasRole(role, "manage") };
}

// Paths outside the web UI (urls.py, E-39). A sign-in never continues to one
// of these, except the admin, which is opened as a page of its own.
const NON_UI_SEGMENTS = new Set(["api", "static", "_allauth", "accounts"]);
const SERVER_PAGE_SEGMENTS = new Set(["admin"]);
const PARSE_BASE = "http://twox.invalid";

export const LOGIN_PAGE_PATH = "/login";

function firstSegment(pathname: string): string {
  return pathname.split("/")[1] ?? "";
}

function hasControlCharacter(text: string): boolean {
  for (const character of text) {
    const code = character.charCodeAt(0);
    if (code < 0x20 || code === 0x7f) {
      return true;
    }
  }
  return false;
}

/**
 * The address to continue to after signing in: a path of this application
 * from ?next=, otherwise "/". Foreign addresses ("https://…", "//host"),
 * API paths and the sign-in page itself are never accepted.
 *
 * Every check runs on the normalised result (dot segments resolved,
 * backslashes turned into slashes), because that is what the browser is sent
 * to: "/x/..//host" must not become "//host".
 */
export function safeNextPath(raw: string | null): string {
  if (raw === null || !raw.startsWith("/")) {
    return "/";
  }
  let url: URL;
  try {
    url = new URL(raw, PARSE_BASE);
  } catch {
    return "/";
  }
  if (url.origin !== PARSE_BASE) {
    return "/";
  }
  const path = `${url.pathname}${url.search}${url.hash}`;
  if (
    !path.startsWith("/") ||
    path.startsWith("//") ||
    path.includes("\\") ||
    hasControlCharacter(path) ||
    NON_UI_SEGMENTS.has(firstSegment(url.pathname)) ||
    url.pathname === LOGIN_PAGE_PATH
  ) {
    return "/";
  }
  return path;
}

/** True for a path that Django serves itself (the admin), not the web UI. */
export function isServerPage(path: string): boolean {
  return SERVER_PAGE_SEGMENTS.has(firstSegment(path));
}

/** Address of the sign-in page that returns to `path` afterwards. */
export function loginPathFor(path: string): string {
  return path === "/" ? LOGIN_PAGE_PATH : `${LOGIN_PAGE_PATH}?next=${encodeURIComponent(path)}`;
}
