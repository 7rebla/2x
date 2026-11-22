# OpenAPI schema and generated API client

The web UI talks to the API only through a client generated from the backend's OpenAPI description.

| What | Where | Checked in |
| --- | --- | --- |
| OpenAPI schema of the backend (drf-spectacular) | `web/openapi/schema.yml` | yes |
| Generator configuration (`@hey-api/openapi-ts`) | `web/openapi-ts.config.ts` | yes |
| Generated client (types, SDK functions, fetch client, TanStack Query options) | `web/src/api/generated/` | yes, never edited by hand |
| Error handling (`ApiError`) and query defaults | `web/src/api/errors.ts`, `web/src/api/queryClient.ts` | yes |
| Hand-written wrapper of the self-test page | `web/src/api/selftest.ts` | yes |

The fetch client is copied into `src/api/generated/client/` and `core/` and needs no package.
The plugin `@tanstack/react-query` writes `src/api/generated/@tanstack/react-query.gen.ts` (query options and keys per endpoint);
that file imports the runtime package `@tanstack/react-query`. How pages use it: `web/src/pages/README.md`.
It uses relative URLs (`/api/v1/...`), because UI and API are served from the same origin.
The generator runs offline; the input must start with `./` (a bare `a/b` would be read as a Hey API registry shorthand).

## Regenerate after an API change

From the repository root (the services `backend-dev` and `web-dev` are in the compose profile `dev`):

1. Write the schema from the backend container into this folder. Mounting the folder keeps the file UTF-8 with LF line endings
   (do not redirect the output with `>` in Windows PowerShell 5.1, that writes UTF-16):

   ```sh
   docker compose run --rm -v "$PWD/web/openapi:/out" backend-dev \
     python manage.py spectacular --file /out/schema.yml
   ```

   This is the form of the CI, for a POSIX shell (Linux, macOS). In Git Bash on Windows put `MSYS_NO_PATHCONV=1` in front of
   `docker compose`; otherwise Git Bash rewrites `/out/schema.yml` into a Windows path and the command fails with `FileNotFoundError`:

   ```sh
   MSYS_NO_PATHCONV=1 docker compose run --rm -v "$PWD/web/openapi:/out" backend-dev \
     python manage.py spectacular --file /out/schema.yml
   ```

2. Generate the client from the schema:

   ```sh
   docker compose -f deploy/compose/compose.web.yaml run --rm web-dev npm run api:generate
   ```

3. Check that nothing else is needed: `git diff -- web/openapi web/src/api` shows the change,
   and `npm run typecheck`, `npm run lint` and `npm run test` in `web-dev` pass.

Up to date means: both steps leave `git diff --exit-code -- web/openapi web/src/api` without changes.

## Stable test ids of the self-test page

For end-to-end tests: `database-version`, `worker-result`, `worker-duration`, `database-status`, `worker-status`,
`database-error`, `worker-error` (error text of the API for one check), `selftest-error` (the API did not answer or answered with an HTTP error),
`selftest-loading`.
