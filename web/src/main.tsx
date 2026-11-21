import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter } from "react-router";

// Sets up the translations (and <html lang>) before the first render.
import "./i18n.ts";
import { installClientConfig } from "./api/client.ts";
import { installApiErrorHandling } from "./api/errors.ts";
import { createQueryClient } from "./api/queryClient.ts";
import { App } from "./App.tsx";
import { routes } from "./routes.tsx";
import "./index.css";

const container = document.getElementById("root");
if (container === null) {
  throw new Error("Root element #root is missing in index.html");
}

installClientConfig();
installApiErrorHandling();

createRoot(container).render(
  <StrictMode>
    <App router={createBrowserRouter(routes)} queryClient={createQueryClient()} />
  </StrictMode>,
);
