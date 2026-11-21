import type { ReactElement } from "react";

export function App(): ReactElement {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-50 p-8 text-slate-900">
      <h1 className="text-5xl font-semibold tracking-tight">2x</h1>
      <p className="max-w-md text-center text-slate-600">
        This page is a placeholder. The user interface is under construction.
      </p>
    </main>
  );
}
