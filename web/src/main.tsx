import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

// Sets up the translations (and <html lang>) before the first render.
import "./i18n.ts";
import { App } from "./App.tsx";
import "./index.css";

const container = document.getElementById("root");
if (container === null) {
  throw new Error("Root element #root is missing in index.html");
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
