# 2x

2x is a self-hosted, open-source application for small and medium-sized manufacturing companies.
For every device and plant it collects the documentation and the current configuration files, builds a profile from them and answers questions about them, with a source for every answer and a language model that runs on the company's own hardware.

**Status: early scaffold (milestone M0).** What exists today is the skeleton: the containers, the tooling, the CI and one test page that goes through all layers (web UI, API, database, task queue, worker).
Importing documents, search, answers, profiles and login do not exist yet; they are planned in the milestones listed in [docs/ROADMAP.md](docs/ROADMAP.md).
In code and configuration the project is called `twox`, because Python packages and environment variables cannot start with a digit.

How the scaffold is put together is described in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Requirements

- **Docker with the Compose plugin.** Everything runs in Linux containers; nothing is installed on the host (no Python, no Node).
  The root `compose.yaml` uses `include`, so an old Compose v1 (`docker-compose`) does not work.
- **Disk space:** the document converter image (Docling) alone needs about 7.6 GB on disk (about 2.2 GB download).
- **Optional: [Ollama](https://ollama.com/)** on the host, outside the containers. Nothing in M0 uses a model yet; only the check command `check_llm` talks to it.

## Quick start

Run everything from the repository root.

1. Create your local configuration from the template. It holds development values only and is never committed:

   ```sh
   cp .env.example .env
   ```

   (Windows PowerShell: `Copy-Item .env.example .env`)

2. Build and start all services and wait until every one is healthy:

   ```sh
   docker compose up -d --wait
   ```

   The first start takes a while: the backend image is built (including the web UI) and the Docling image is downloaded. Start it as a background command if your tool has a time limit.
   After the download the services usually become healthy within about half a minute.

3. Open the test page: <http://localhost:8000/selftest>

   It shows two cards: **Database - OK** with the PostgreSQL server version, and **Worker - OK** with the result `pong` and the round-trip time.
   "Check again" repeats the test. If the worker is stopped, the worker card turns red and shows the error from the API.

Stop the services with `docker compose down`. To also delete the data volumes (database, Valkey, the `node_modules` volume of the web tooling), run:

```sh
docker compose --profile dev --profile e2e down -v
```

## Services and networks

| Service | Role | Reachable from |
| --- | --- | --- |
| `api` | Django API and the built web UI (ASGI server uvicorn) | the host, port 8000 on `127.0.0.1` only |
| `worker` | Celery worker for the queues `ingest`, `embed`, `default` | compose network only |
| `db` | PostgreSQL with pgvector | compose network only |
| `valkey` | Valkey, message broker and result store for Celery | compose network only |
| `migrate` | applies the database migrations once, then exits | - |
| `docling` | docling-serve, document conversion (CPU) | `api` and `worker` only, over the internal network `docling-internal` |

- `docling` is attached only to the network `docling-internal`, which is marked `internal`: it has no route to the internet, and only `api` and `worker` are attached to it as well (decision E-32).
  `docling` also starts with its telemetry and remote services switched off; see `deploy/compose/compose.yaml`.
- Ollama is not a container. `api` and `worker` reach it on the host through `host.docker.internal` (set via `extra_hosts`).
- The development services `backend-dev`, `web-dev` (profile `dev`) and `e2e` (profile `e2e`) start only when named; see below.

Exact image versions are pinned in the compose files under `deploy/compose/`, in `backend/Dockerfile` and `web/Dockerfile`; package versions in `backend/uv.lock` and `web/package-lock.json`.

## Check commands

Two Django management commands check the external services. Each prints exactly one line that starts with `OK:` (exit code 0) or `FAILED:` (exit code 1). Both accept `--timeout SECONDS` (per step, default 5).

### `check_docling`

```sh
docker compose exec api python manage.py check_docling
```

- `OK: docling-serve <version> at http://docling:5001`: the service resolves, accepts connections and reports its version.
- `FAILED: ...`: the line names the failing step, for example `cannot resolve host 'docling'` (container not running in this compose project), `connection refused` (not listening yet) or `unexpected response`.

Run it in `api` or `worker`. `backend-dev` is deliberately not attached to the Docling network, so the command fails there with `cannot resolve host`.
`OK` means the server answers; Docling loads its models only with the first conversion.

### `check_llm`

```sh
docker compose exec api python manage.py check_llm
```

It reads `TWOX_LLM_BASE_URL` (default `http://host.docker.internal:11434/v1`) and asks the OpenAI-compatible interface for its model list.

- `OK: <address>/models is reachable, N model(s) reported`: Ollama (or another OpenAI-compatible server) answers. `0 model(s)` is fine in M0: no model is needed yet.
- `FAILED: cannot resolve host ...`: the container cannot resolve the host name; check `extra_hosts` in the compose file and that Docker is running.
- `FAILED: connection refused by ...`: Ollama is not running, or it listens on an address the containers cannot reach (see `OLLAMA_HOST` in the Ollama documentation).
- `FAILED: timeout ...`: something accepts the connection but does not answer, or a firewall drops it.
- `FAILED: unexpected response ...`: the address answers, but not with a model list.

On the development machine (Docker with WSL 2 on Windows) Ollama with its default binding was reachable without any change. Other setups, for example Docker directly on Linux, have not been checked.

## Development commands

The commands below are the ones the CI runs (`.github/workflows/ci.yml`), in the same form. Run them from the repository root after copying `.env.example` to `.env`.

### Backend (service `backend-dev`, profile `dev`)

```sh
docker compose --profile dev build migrate api worker backend-dev
docker compose up -d --wait --wait-timeout 300 db valkey worker api

docker compose run --rm backend-dev ruff check .
docker compose run --rm backend-dev ruff format --check .
docker compose run --rm backend-dev mypy .
docker compose run --rm backend-dev pytest
docker compose run --rm backend-dev pytest -m worker
docker compose run --rm backend-dev python manage.py makemigrations --check --dry-run
docker compose run --rm backend-dev sh scripts/check-licenses.sh
```

- `pytest` runs against the real PostgreSQL in `db` and skips the tests marked `worker`.
- `pytest -m worker` runs only those; they need the `valkey` and `worker` services running.
- `sh scripts/check-licenses.sh` is the licence check of the Python packages; it fails on every licence that is not allowed in `backend/scripts/license-rules.txt`.

Translation catalogue up to date (regenerates `backend/locale/de/LC_MESSAGES/django.po` from the texts marked with `gettext` or `gettext_lazy`; any difference apart from the creation date means the catalogue is out of date):

```sh
docker compose run --rm backend-dev python manage.py makemessages -l de --add-location=file
git diff --exit-code -I '^"POT-Creation-Date:' -- backend/locale
test -z "$(git status --porcelain --untracked-files=all -- backend/locale)"
```

- After a change to backend texts, run `makemessages` as above, translate every new entry in `django.po` and remove `fuzzy` flags; `pytest` fails while the catalogue has untranslated or fuzzy entries (`tests/config/test_i18n.py`).
- The API answers in German if the request asks for it (`Accept-Language: de`), otherwise in English.
- Compiled catalogues (`.mo`) are never committed. The runtime image compiles them in a build stage; `pytest` compiles them into a temporary directory outside `/app`. GNU gettext (GPL) is a tool of the `dev` image and that build stage only, not part of the runtime image (E-46).

OpenAPI schema up to date (regenerates `web/openapi/schema.yml`; any difference means the checked-in schema is out of date):

```sh
docker compose run --rm -v "$PWD/web/openapi:/out" backend-dev \
  python manage.py spectacular --file /out/schema.yml
git diff --exit-code -- web/openapi
```

The `$PWD` form is for a POSIX shell (Linux, macOS, the CI). In Git Bash on Windows put `MSYS_NO_PATHCONV=1` in front of the `docker compose` command; otherwise Git Bash rewrites `/out/schema.yml` into a Windows path and the command fails with `FileNotFoundError`.
`web/openapi/README.md` explains how schema and API client are regenerated.

### Web UI (service `web-dev`, profile `dev`)

The CI runs the web tooling with the web compose file alone:

```sh
docker compose -f deploy/compose/compose.web.yaml --profile dev build web-dev
docker compose -f deploy/compose/compose.web.yaml run --rm web-dev npm ci
docker compose -f deploy/compose/compose.web.yaml run --rm web-dev npm run lint
docker compose -f deploy/compose/compose.web.yaml run --rm web-dev npm run typecheck
docker compose -f deploy/compose/compose.web.yaml run --rm web-dev npm run test
docker compose -f deploy/compose/compose.web.yaml run --rm web-dev npm run build
docker compose -f deploy/compose/compose.web.yaml run --rm web-dev npm run licenses
docker compose -f deploy/compose/compose.web.yaml run --rm web-dev npm run api:generate
```

- `lint` is ESLint, `typecheck` is `tsc --noEmit`, `test` is Vitest, `licenses` is the licence check of the npm packages (rules in `web/scripts/license-rules.txt`).
- `api:generate` regenerates the API client from the schema; afterwards `git diff --exit-code -- web/openapi web/src/api` must show no change.
- With `-f deploy/compose/compose.web.yaml` Compose uses a project of its own (named after the folder, `compose`) with its own `node_modules` volume. The browser test below uses the root project instead.

### Browser test (service `e2e`, profile `e2e`)

Playwright tests open the web UI in Chromium, signed in with a test account; among other things they expect the database version and `pong` from the worker on the self-test page, which only signed-in users with a role may call. First create the test account (step "Create test account" in `.github/workflows/ci.yml`, in Git Bash or another POSIX shell):

```sh
docker compose --profile e2e pull e2e
docker compose --profile dev run --rm web-dev npm ci
docker compose up -d --wait --wait-timeout 300 db valkey worker api
set -a; . ./.env; set +a
TWOX_ACCOUNT_PASSWORD="$TWOX_E2E_PASSWORD" docker compose exec -T -e TWOX_ACCOUNT_PASSWORD api python manage.py create_account "$TWOX_E2E_USERNAME" --role manage --update
docker compose --profile e2e run --rm e2e
```

Expected output: all tests passed, exit code 0. `e2e` uses the packages that `web-dev` installed (`npm ci`) in the shared volume.

- `TWOX_E2E_USERNAME` and `TWOX_E2E_PASSWORD` in `.env.example` are development values. Never use them for a real account.
- The password reaches the container as a variable name only (`-e TWOX_ACCOUNT_PASSWORD` without a value), not as a command-line argument.
- With `--update` the step can run again and again, also without `down -v`; it sets the role and password of the existing account.
- The tests sign in through the sign-in API of django-allauth (`web/e2e/fixtures.ts`). Test data follow the rules there: names `e2e-<kind>-<suffix>` with a suffix unique per run, IP addresses only from 192.0.2.0/24.

### Test factory

The test factory (`testfactory/`) is the reference plant 2x is developed against: real equipment with public documentation. Its checks need no network and no vendor material:

```sh
docker compose -f deploy/compose/testfactory.yaml build check
docker compose -f deploy/compose/testfactory.yaml run --rm check ruff check --config backend/pyproject.toml testfactory
docker compose -f deploy/compose/testfactory.yaml run --rm check ruff format --config backend/pyproject.toml --check testfactory
docker compose -f deploy/compose/testfactory.yaml run --rm check mypy --config-file testfactory/mypy.ini testfactory
docker compose -f deploy/compose/testfactory.yaml run --rm check-offline python -m unittest discover -s testfactory/tests -t . -v
docker compose -f deploy/compose/testfactory.yaml run --rm fetch python -m testfactory.manifest_tools check
docker compose -f deploy/compose/testfactory.yaml run --rm fetch python -m testfactory.manifest_tools format --check
docker compose -f deploy/compose/testfactory.yaml run --rm fetch python -m testfactory.manifest_tools check --complete testdata/klein/manifest.yaml
docker compose -f deploy/compose/testfactory.yaml run --rm fetch python -m testfactory.manifest_tools format --check testdata/klein/manifest.yaml
```

**Licences of vendor documents:** vendor manuals and files are never committed to this repository. `testfactory/manifest.yaml` records for every document where it comes from, its checksum and its terms of use; `testfactory/fetch.py` downloads it onto your own machine into `testfactory/extern/`, which Git ignores.
Documents that may only be downloaded by hand (the Siemens system manual, decision E-27) are never fetched automatically; `fetch.py` only verifies them once you have placed them yourself.
Only material under an explicitly free licence is checked in (`testdata/klein/`). Details, including the fetch commands: [testfactory/README.md](testfactory/README.md).

### Secret scan

```sh
docker compose -f deploy/compose/compose.tools.yaml run --rm gitleaks-dir
```

Scans the files of the working directory with gitleaks (no network, findings redacted); exit code 0 means no finding. It also reads files Git ignores, such as your `.env`.
`gitleaks-git` scans the whole Git history instead; it needs a normal clone (the workflow `.github/workflows/secrets.yml` runs it on every push).

### What the CI does not run

The CI (`.github/workflows/ci.yml`, jobs `backend`, `web`, `testfactory`, `e2e`) does not start `docling` and has no Ollama, so `check_docling` and `check_llm` run only locally. It does not run `testfactory/fetch.py`, and the test questions (`testfactory/questions.yaml`) are not yet run against a model.

## Security notes

- **Port:** only `api` publishes a port, and only on `127.0.0.1` (default 8000, `TWOX_API_PORT`). Nothing is reachable from other machines.
- **No login yet:** authentication arrives with milestone M1. The API is closed by default (every view requires a signed-in user unless it opts out), and there is no way to sign in yet. The only endpoints are the two open ones, `/api/v1/health/` and `/api/v1/selftest/`. Do not expose the port to a network.
- **`TWOX_DEBUG`:** `.env.example` sets `TWOX_DEBUG=true` for development, so Django shows detailed error pages (a 404 in the browser lists the URL patterns). Outside development leave `TWOX_DEBUG` empty or set it to `false`; the default in `backend/twox/config/settings.py` is off.
- **Development values only:** `.env.example` contains no real secrets; never put production secrets into it. `.env` is ignored by Git.
- **No telemetry:** the project's own code sends nothing anywhere. The `docling` service has its telemetry switched off and has no route to the internet. Operation without internet is a design goal; the first start needs the internet only to download images and packages.

## Licence

2x is licensed under the [Apache License 2.0](LICENSE).

The licence notices of the third-party code shipped in the web UI are generated during the image build and served at `/static/THIRD-PARTY-NOTICES.txt` (for example <http://localhost:8000/static/THIRD-PARTY-NOTICES.txt>).
Every dependency, its licence and every exception is recorded in [docs/DECISIONS.md](docs/DECISIONS.md) (written in German, like the work orders and the status).
