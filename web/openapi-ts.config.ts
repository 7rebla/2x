// Configuration of the API client generator (@hey-api/openapi-ts).
// Regenerate the client with `npm run api:generate` (see web/openapi/README.md).
import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  // Leading "./" is required: a bare "a/b" is read as a Hey API registry shorthand.
  input: "./openapi/schema.yml",
  output: "./src/api/generated",
  // "@tanstack/react-query" adds typed query options and keys per endpoint
  // (src/api/generated/@tanstack/react-query.gen.ts) for TanStack Query.
  plugins: [
    "@hey-api/client-fetch",
    "@hey-api/typescript",
    "@hey-api/sdk",
    "@tanstack/react-query",
  ],
});
