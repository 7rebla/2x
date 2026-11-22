// Test helper: renders the whole app (frame, routes, TanStack Query) at one address.
import type { QueryClient } from "@tanstack/react-query";
import { fireEvent, render, type RenderResult, screen } from "@testing-library/react";
import { createMemoryRouter } from "react-router";

import { installClientConfig } from "../api/client.ts";
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
  installClientConfig();
  installApiErrorHandling();
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  const queryClient = createQueryClient();
  const result = render(<App router={router} queryClient={queryClient} />);
  return { ...result, router, queryClient };
}

/** Opens the user menu in the header (role, settings link, language, sign-out) once the user is known. */
export async function openUserMenu(): Promise<void> {
  const button = await screen.findByTestId("user-menu-button");
  if (button.getAttribute("aria-expanded") !== "true") {
    fireEvent.click(button);
  }
}
