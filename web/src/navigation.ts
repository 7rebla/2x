// Entries of the main navigation, read by components/Layout.tsx, and the role
// each page needs, read by routes.tsx.
//
// Each entry names a path from routes.tsx, the key of its text in the "nav"
// catalog and the role that may see it (E-40). Layout shows only the entries
// the signed-in user's role allows; routes.tsx shows "no permission" instead
// of a page whose role is missing. Pages that later work orders build keep
// their entry here unchanged.
import type navCatalog from "./locales/en/nav.json";
import { hasRole, type Role } from "./session.ts";

/** Key of a page name in locales/<language>/nav.json. */
export type NavTextKey = Exclude<keyof typeof navCatalog, "label">;

export interface NavigationEntry {
  /** Address of the page, as in routes.tsx. */
  readonly path: string;
  /** Text of the entry in the "nav" catalog. */
  readonly textKey: NavTextKey;
  /** Marks the entry as current only for exactly this path (not for paths below it). */
  readonly end?: boolean;
  /** Role needed to see the entry and open the page ("manage" includes "read"). */
  readonly requires: Role;
}

/** Order of the entries in the header. Pages with a parameter (device, file) and the sign-in page are not listed. */
export const navigation: readonly NavigationEntry[] = [
  { path: "/", textKey: "structure", end: true, requires: "read" },
  { path: "/import", textKey: "import", requires: "manage" },
  // The change log names users; only "manage" may read it (E-43, work order 028, question 3).
  { path: "/audit", textKey: "audit", requires: "manage" },
  { path: "/selftest", textKey: "selftest", requires: "read" },
];

/** Entries the given role may see; none without a role. */
export function visibleNavigation(role: Role | null): readonly NavigationEntry[] {
  return navigation.filter((entry) => hasRole(role, entry.requires));
}

/** Role a page needs: the one of its navigation entry, "read" for pages without an entry. */
export function requiredRole(path: string): Role {
  return navigation.find((entry) => entry.path === path)?.requires ?? "read";
}
