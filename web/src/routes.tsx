// All addresses of the user interface (react-router, data mode).
//
// Django serves index.html for every path except api/, static/, admin/,
// _allauth/ and accounts/ (E-39), so each address below can be opened directly.
// Later work orders replace only their own file in pages/; the routes, the
// frame (components/Layout.tsx) and the navigation (navigation.ts) stay.
//
// Every page except /login needs a session (RequireSession) and a role
// (RequireRole, from navigation.ts).
import type { ReactElement } from "react";
import type { RouteObject } from "react-router";

import { Layout } from "./components/Layout.tsx";
import { NotFound } from "./components/NotFound.tsx";
import { lazyPage } from "./components/PageLoading.tsx";
import { RouteError } from "./components/RouteError.tsx";
import { RequireRole, RequireSession } from "./components/SessionGuards.tsx";
import { requiredRole } from "./navigation.ts";
import { LoginPage } from "./pages/LoginPage.tsx";
import { StructurePage } from "./pages/StructurePage.tsx";

// The sign-in page and the start page (structure) come with the main bundle.
// Every other page is loaded when it is opened (work order 062), so the
// browser loads less at the start; the map brings React Flow along.
const pages = {
  map: lazyPage(async () => (await import("./pages/MapPage.tsx")).MapPage),
  search: lazyPage(async () => (await import("./pages/SearchPage.tsx")).SearchPage),
  ingest: lazyPage(async () => (await import("./pages/IngestPage.tsx")).IngestPage),
  device: lazyPage(async () => (await import("./pages/DevicePage.tsx")).DevicePage),
  document: lazyPage(async () => (await import("./pages/DocumentPage.tsx")).DocumentPage),
  import: lazyPage(async () => (await import("./pages/ImportPage.tsx")).ImportPage),
  audit: lazyPage(async () => (await import("./pages/AuditPage.tsx")).AuditPage),
  selftest: lazyPage(async () => (await import("./pages/SelftestPage.tsx")).SelftestPage),
  settings: lazyPage(async () => (await import("./pages/SettingsPage.tsx")).SettingsPage),
};

/** Loads the code of every page that is loaded on demand (tests, so the first render needs no extra wait). */
export async function preloadPages(): Promise<void> {
  await Promise.all(Object.values(pages).map((page) => page.preload()));
}

/** A page that needs the role of `path` in navigation.ts ("read" if it has no entry). */
function guarded(path: string, page: ReactElement): ReactElement {
  return <RequireRole role={requiredRole(path)}>{page}</RequireRole>;
}

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <Layout />,
    // Only if the frame itself fails; errors of a page are caught below.
    errorElement: <RouteError />,
    children: [
      {
        // Keeps the frame around a page that fails to render.
        errorElement: <RouteError />,
        children: [
          { path: "login", element: <LoginPage /> },
          {
            element: <RequireSession />,
            children: [
              { index: true, element: guarded("/", <StructurePage />) },
              { path: "map", element: guarded("/map", pages.map.element) },
              { path: "search", element: guarded("/search", pages.search.element) },
              { path: "ingest", element: guarded("/ingest", pages.ingest.element) },
              { path: "devices/:deviceId", element: guarded("/devices", pages.device.element) },
              { path: "documents/:documentId", element: guarded("/documents", pages.document.element) },
              { path: "import", element: guarded("/import", pages.import.element) },
              { path: "audit", element: guarded("/audit", pages.audit.element) },
              { path: "selftest", element: guarded("/selftest", pages.selftest.element) },
              // Reached from the user menu (work order 070); no entry in navigation.ts, so role "read".
              { path: "settings", element: guarded("/settings", pages.settings.element) },
              { path: "*", element: <NotFound /> },
            ],
          },
        ],
      },
    ],
  },
];
