// Entries of the main navigation, read by components/Layout.tsx.
//
// Each entry names a path from routes.tsx and the key of its text in the
// "nav" catalog. Work order 030 adds the role that may see an entry.
import type navCatalog from "./locales/en/nav.json";

/** Key of a page name in locales/<language>/nav.json. */
export type NavTextKey = Exclude<keyof typeof navCatalog, "label">;

export interface NavigationEntry {
  /** Address of the page, as in routes.tsx. */
  readonly path: string;
  /** Text of the entry in the "nav" catalog. */
  readonly textKey: NavTextKey;
  /** Marks the entry as current only for exactly this path (not for paths below it). */
  readonly end?: boolean;
}

/** Order of the entries in the header. Pages with a parameter (device, file) and the sign-in page are not listed. */
export const navigation: readonly NavigationEntry[] = [
  { path: "/", textKey: "structure", end: true },
  { path: "/import", textKey: "import" },
  { path: "/audit", textKey: "audit" },
  { path: "/selftest", textKey: "selftest" },
];
