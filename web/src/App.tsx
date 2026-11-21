import { type QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactElement } from "react";
import { RouterProvider } from "react-router/dom";

/** The router type of react-router's data mode (browser router in the app, memory router in tests). */
export type AppRouter = Parameters<typeof RouterProvider>[0]["router"];

/** Root of the user interface: data fetching (TanStack Query) around the router. */
export function App({
  router,
  queryClient,
}: {
  router: AppRouter;
  queryClient: QueryClient;
}): ReactElement {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
