import { defineConfig, devices } from "@playwright/test";

// The web UI has no Node types (@types/node is not a dependency); the config
// only reads environment variables.
declare const process: { readonly env: Readonly<Record<string, string | undefined>> };

// Address of the Django service that serves the test page and the API. Inside
// the compose network this is the service name `api`.
const apiUrl = new URL(process.env.TWOX_E2E_API_URL ?? "http://api:8000");

// Django only answers host names listed in TWOX_ALLOWED_HOSTS, and the
// development .env lists localhost and 127.0.0.1 only. The browser therefore
// opens http://localhost:<port>/ and Chromium resolves "localhost" to the API
// host: the Host header stays "localhost", nothing in the backend changes.
const loopbackHosts = new Set(["localhost", "127.0.0.1", "[::1]"]);
const mapToApiHost = !loopbackHosts.has(apiUrl.hostname);
const baseURL = mapToApiHost
  ? `${apiUrl.protocol}//localhost${apiUrl.port === "" ? "" : `:${apiUrl.port}`}`
  : apiUrl.origin;

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.spec.ts",
  outputDir: "./test-results",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: process.env.CI !== undefined && process.env.CI !== "",
  timeout: 60_000,
  expect: {
    // The self-test waits up to 5 s for the worker; leave room for a slow start.
    timeout: 20_000,
  },
  reporter: [["list"], ["html", { open: "never", outputFolder: "./playwright-report" }]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        launchOptions: {
          args: mapToApiHost ? [`--host-resolver-rules=MAP localhost ${apiUrl.hostname}`] : [],
        },
      },
    },
  ],
});
