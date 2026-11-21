import { type QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactElement, useEffect } from "react";
import { RouterProvider } from "react-router/dom";

import { watchForbidden } from "./session.ts";

/** The router type of react-router's data mode (browser router in the app, memory router in tests). */
export type AppRouter = Parameters<typeof RouterProvider>[0]["router"];

/**
 * Root of the user interface: data fetching (TanStack Query) around the router.
 * A 403 of any API call makes the app ask /api/v1/me/ again (session.ts).
 */
export function App({
  router,
  queryClient,
}: {
  router: AppRouter;
  queryClient: QueryClient;
}): ReactElement {
  useEffect(() => watchForbidden(queryClient), [queryClient]);
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
