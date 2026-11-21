// All addresses of the user interface (react-router, data mode).
//
// Django serves index.html for every path except api/, static/, admin/,
// _allauth/ and accounts/ (E-39), so each address below can be opened directly.
// Later work orders replace only their own file in pages/; the routes, the
// frame (components/Layout.tsx) and the navigation (navigation.ts) stay.
import type { RouteObject } from "react-router";

import { Layout } from "./components/Layout.tsx";
import { NotFound } from "./components/NotFound.tsx";
import { RouteError } from "./components/RouteError.tsx";
import { AuditPage } from "./pages/AuditPage.tsx";
import { DevicePage } from "./pages/DevicePage.tsx";
import { DocumentPage } from "./pages/DocumentPage.tsx";
import { ImportPage } from "./pages/ImportPage.tsx";
import { LoginPage } from "./pages/LoginPage.tsx";
import { SelftestPage } from "./pages/SelftestPage.tsx";
import { StructurePage } from "./pages/StructurePage.tsx";

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
          { index: true, element: <StructurePage /> },
          { path: "devices/:deviceId", element: <DevicePage /> },
          { path: "documents/:documentId", element: <DocumentPage /> },
          { path: "import", element: <ImportPage /> },
          { path: "audit", element: <AuditPage /> },
          { path: "login", element: <LoginPage /> },
          { path: "selftest", element: <SelftestPage /> },
          { path: "*", element: <NotFound /> },
        ],
      },
    ],
  },
];
