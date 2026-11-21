import type { ReactElement } from "react";
import { useRouteError } from "react-router";

import { ErrorMessage } from "./ErrorMessage.tsx";

/** Shown by the router when a page fails to render; the frame around it stays. */
export function RouteError(): ReactElement {
  const error = useRouteError();
  return <ErrorMessage error={error} />;
}
