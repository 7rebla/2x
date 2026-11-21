import type { ReactElement } from "react";

import { SelftestPage } from "./SelftestPage.tsx";
import { texts } from "./texts.ts";

export function App(): ReactElement {
  return (
    <main className="flex min-h-screen flex-col items-center gap-8 bg-slate-50 p-8 text-slate-900">
      <h1 className="text-5xl font-semibold tracking-tight">{texts.appTitle}</h1>
      <SelftestPage />
    </main>
  );
}
