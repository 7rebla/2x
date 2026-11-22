import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  // Django serves the built files below /static/ (no Node server in production).
  base: "/static/",
  plugins: [react(), tailwindcss()],
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    // Vitest empties CSS files; the contrast test reads the theme tokens as raw text.
    css: { include: [/\/src\/index\.css\?raw$/] },
  },
});
