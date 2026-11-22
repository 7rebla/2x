// All addresses of the user interface (react-router, data mode).
//
// Django serves index.html for every path except api/, static/, admin/,
// _allauth/ and accounts/ (E-39), so each address below can be opened directly.
// Later work orders replace only their own file in pages/; the routes, the
// frame (components/Layout.tsx) and the navigation (navigation.ts) stay.
//
// Every page except /login needs a session (RequireSession) and a role
// (RequireRole, from navigation.ts).
import { lazy, type ReactElement, Suspense } from "react";
import type { RouteObject } from "react-router";

import { Layout } from "./components/Layout.tsx";
import { Loading } from "./components/Loading.tsx";
import { NotFound } from "./components/NotFound.tsx";
import { RouteError } from "./components/RouteError.tsx";
import { RequireRole, RequireSession } from "./components/SessionGuards.tsx";
import { requiredRole } from "./navigation.ts";
import { AuditPage } from "./pages/AuditPage.tsx";
import { DevicePage } from "./pages/DevicePage.tsx";
import { DocumentPage } from "./pages/DocumentPage.tsx";
import { ImportPage } from "./pages/ImportPage.tsx";
import { LoginPage } from "./pages/LoginPage.tsx";
import { SelftestPage } from "./pages/SelftestPage.tsx";
import { SettingsPage } from "./pages/SettingsPage.tsx";
import { StructurePage } from "./pages/StructurePage.tsx";

// The map page brings React Flow along; it is loaded only when the page is opened.
const MapPage = lazy(async () => {
  const module = await import("./pages/MapPage.tsx");
  return { default: module.MapPage };
});

// The search page (work order 054) is loaded when it is opened, too, so the main bundle does not grow with it.
const SearchPage = lazy(async () => {
  const module = await import("./pages/SearchPage.tsx");
  return { default: module.SearchPage };
});

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
              {
                path: "map",
                element: guarded(
                  "/map",
                  <Suspense fallback={<Loading />}>
                    <MapPage />
                  </Suspense>,
                ),
              },
              {
                path: "search",
                element: guarded(
                  "/search",
                  <Suspense fallback={<Loading />}>
                    <SearchPage />
                  </Suspense>,
                ),
              },
              { path: "devices/:deviceId", element: guarded("/devices", <DevicePage />) },
              { path: "documents/:documentId", element: guarded("/documents", <DocumentPage />) },
              { path: "import", element: guarded("/import", <ImportPage />) },
              { path: "audit", element: guarded("/audit", <AuditPage />) },
              { path: "selftest", element: guarded("/selftest", <SelftestPage />) },
              // Reached from the user menu (work order 070); no entry in navigation.ts, so role "read".
              { path: "settings", element: guarded("/settings", <SettingsPage />) },
              { path: "*", element: <NotFound /> },
            ],
          },
        ],
      },
    ],
  },
];
