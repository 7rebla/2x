// Test helper: renders the whole app (frame, routes, TanStack Query) at one address.
import type { QueryClient } from "@tanstack/react-query";
import { render, type RenderResult } from "@testing-library/react";
import { createMemoryRouter } from "react-router";

import { installApiErrorHandling } from "../api/errors.ts";
import { createQueryClient } from "../api/queryClient.ts";
import { App, type AppRouter } from "../App.tsx";
import { routes } from "../routes.tsx";

export interface RenderedApp extends RenderResult {
  router: AppRouter;
  queryClient: QueryClient;
}

/** Same setup as main.tsx, with a memory router instead of the browser address bar. */
export function renderApp(path: string): RenderedApp {
  installApiErrorHandling();
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const queryClient = createQueryClient();
  const result = render(<App router={router} queryClient={queryClient} />);
  return { ...result, router, queryClient };
}
