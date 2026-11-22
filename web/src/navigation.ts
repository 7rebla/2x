// Entries of the main navigation, read by components/Layout.tsx, and the role
// each page needs, read by routes.tsx.
//
// Each entry names a path from routes.tsx, the key of its text in the "nav"
// catalog and the role that may see it (E-40). Layout shows only the entries
// the signed-in user's role allows; routes.tsx shows "no permission" instead
// of a page whose role is missing. Pages that later work orders build keep
// their entry here unchanged.
import type { IconName } from "./icons/names.ts";
import type navCatalog from "./locales/en/nav.json";
import { hasRole, type Role } from "./session.ts";

/** Key of a page name in locales/<language>/nav.json. */
export type NavTextKey = Exclude<keyof typeof navCatalog, "label" | "menu" | "short">;

/**
 * Key of a navigation entry: a page name that also has a short text under
 * "short" in nav.json (shown below the icon from 768 to 1279 px, work order 082).
 */
export type NavEntryKey = keyof typeof navCatalog.short & NavTextKey;

export interface NavigationEntry {
  /** Address of the page, as in routes.tsx. */
  readonly path: string;
  /**
   * Text of the entry in the "nav" catalog (`nav:<key>`, accessible name and
   * tooltip) and its short text (`nav:short.<key>`).
   */
  readonly textKey: NavEntryKey;
  /** Icon of the entry: next to the text from 1280 px, above the short text below (work orders 071, 082). */
  readonly icon: IconName;
  /** Marks the entry as current only for exactly this path (not for paths below it). */
  readonly end?: boolean;
  /** Role needed to see the entry and open the page ("manage" includes "read"). */
  readonly requires: Role;
}

/**
 * Order of the entries in the header. Pages with a parameter (device, file),
 * the sign-in page and the pages of the user menu (settings, self-test) are
 * not listed.
 */
export const navigation: readonly NavigationEntry[] = [
  { path: "/", textKey: "structure", icon: "structure", end: true, requires: "read" },
  // Interactive preview of the map (work order 039, E-48).
  { path: "/map", textKey: "map", icon: "map", requires: "read" },
  // Search in the ingested files (work order 054).
  { path: "/search", textKey: "search", icon: "search", requires: "read" },
  // Questions answered from the documents (page: work order 132, entry: work
  // order 134). Next to the search, as both lead into the documents.
  { path: "/ask", textKey: "ask", icon: "answer", requires: "read" },
  // Overview of the ingest jobs of all devices (work order 055).
  { path: "/ingest", textKey: "ingest", icon: "ingest", requires: "read" },
  { path: "/import", textKey: "import", icon: "import", requires: "manage" },
  // The change log names users; only "manage" may read it (E-43, work order 028, question 3).
  { path: "/audit", textKey: "audit", icon: "audit", requires: "manage" },
  // The self-test has no entry here: it is an operations page and moved to the
  // user menu (work order 134, E-69), so /selftest needs "read" like every page
  // without an entry.
];

/** Entries the given role may see; none without a role. */
export function visibleNavigation(role: Role | null): readonly NavigationEntry[] {
  return navigation.filter((entry) => hasRole(role, entry.requires));
}

/** Role a page needs: the one of its navigation entry, "read" for pages without an entry. */
export function requiredRole(path: string): Role {
  return navigation.find((entry) => entry.path === path)?.requires ?? "read";
}
