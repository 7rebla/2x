# 2x

2x is a self-hosted, open-source application for small and medium-sized manufacturing companies.
For every device and plant it collects the documentation and the current configuration files, builds a profile from them and answers questions about them, with a source for every answer and a language model that runs on the company's own hardware.

**Status: milestone M1 "devices and files" is built; its acceptance is still open.** On top of the scaffold of M0 (containers, tooling, CI, a self-test page through all layers) 2x now has:

- sign-in with local accounts and the two roles "Manage" and "Read";
- the structure of a company (site, area, plant, device) in a web UI and an API, editable by managers;
- an import of the device list from a CSV file, with a dry run first;
- documents per device: upload, versions, download;
- a change log of who changed what and when;
- a web UI and API messages in German and English.

Not there yet: reading the content of documents (conversion, search), answers with sources, device profiles and configuration files. They are planned in the milestones of [docs/ROADMAP.md](docs/ROADMAP.md) (in German). A simplified interactive map of structure, devices and IP networks (milestone M1b, work order 039) is in progress and not part of what is described here.
In code and configuration the project is called `twox`, because Python packages and environment variables cannot start with a digit.

How 2x is put together is described in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md); its known limits are listed there under [Limits and known gaps](docs/ARCHITECTURE.md#limits-and-known-gaps).

## Requirements

- **Docker with the Compose plugin.** Everything runs in Linux containers; nothing is installed on the host (no Python, no Node).
  The root `compose.yaml` uses `include`, so an old Compose v1 (`docker-compose`) does not work.
- **Disk space:** the document converter image (Docling) alone needs about 7.6 GB on disk (about 2.2 GB download).
- **Optional: [Ollama](https://ollama.com/)** on the host, outside the containers. Nothing in M1 uses a model yet; only the check command `check_llm` talks to it.

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

3. Create the first account. There is no self-registration; accounts are made on the command line or by a superuser in the admin.

   A **superuser** may do everything, including the Django admin. Django asks for the user name (the examples below use `admin`), an email address (may stay empty) and the password twice:

   ```sh
   docker compose exec api python manage.py createsuperuser
   ```

   Further accounts get one of the two roles, `manage` or `read` (see [Security notes](#security-notes)). The command asks for the password twice:

   ```sh
   docker compose exec api python manage.py create_account reader --role read
   ```

   - Passwords need at least 12 characters and must pass Django's other standard checks (not too common, not only digits, not too close to the user name).
   - Without a terminal, `create_account` reads the password from the environment variable `TWOX_ACCOUNT_PASSWORD`. Pass it to the container as a variable name only, never as a value on the command line; the step "Create test account" under [Browser test](#browser-test-service-e2e-profile-e2e) shows how.
   - An existing account is an error, unless `--update` is given: then the command sets the role and the password of the account (and creates it if it is missing), so it can run again and again. It never makes an account a superuser and never takes that right away.

4. Sign in: open <http://localhost:8000/>. The browser goes to the sign-in page and, after signing in, back to the structure of the company (empty at first).

5. Import the device list. As a manager, open **Import** (<http://localhost:8000/import>), choose a CSV file (format below, for example `testfactory/layout/devices.csv` of the test factory) and start the dry run. It shows what would be created or changed, or every error with line and column. Only a dry run without errors offers **Apply**, which saves the same file.

   On the command line the same import runs in the development container `backend-dev`, which sees the test factory's device list at `/testfactory/layout/` (read-only). `--user` names the account that the change log records; it needs the role `manage` (a superuser has it). `backend-dev` is in the compose profile `dev`; build its image once with the command of the CI, `docker compose --profile dev build migrate api worker backend-dev`. Without `--commit` it is a dry run:

   ```sh
   docker compose run --rm backend-dev python manage.py import_devices /testfactory/layout/devices.csv --user admin
   docker compose run --rm backend-dev python manage.py import_devices /testfactory/layout/devices.csv --user admin --commit
   ```

   For the test factory the result is 1 site, 3 areas, 10 plants and 13 devices. A second import changes nothing (everything "unchanged").

6. Optional: the self-test page <http://localhost:8000/selftest> shows two cards: **Database - OK** with the PostgreSQL server version, and **Worker - OK** with the result `pong` and the round-trip time.
   "Check again" repeats the test. If the worker is stopped, the worker card turns red and shows the error from the API.

Stop the services with `docker compose down`. To also delete the data volumes (database, Valkey, the uploaded files in `media-data`, the `node_modules` volume of the web tooling), run:

```sh
docker compose --profile dev --profile e2e down -v
```

## The web UI

| Address | Page | Who |
| --- | --- | --- |
| `/` | Structure: tree of sites, areas, plants and devices with the number of devices, search by name, key or IP address; forms to create and change entries | `read`; forms `manage` |
| `/devices/<id>` | One device with all its fields and its files; editing the device and uploading a new file | `read`; editing and upload `manage` |
| `/documents/<id>` | One file with all versions (newest first), download of every version, upload of a new version, change log of the file | `read`; upload and change log `manage` |
| `/import` | Import of the device list (dry run, then apply) | `manage` |
| `/audit` | Change log, filtered by kind of object and user | `manage` |
| `/selftest` | Self-test of database and worker | `read` |
| `/login` | Sign-in | everyone |
| `/admin/` | Django admin; deleting entries is possible only here | superusers |

The language switch in the header changes between German and English; the first choice follows the browser.
Nothing can be deleted in the web UI or the API. A superuser can delete sites, areas, plants and devices in the admin, as long as nothing hangs below them; files, versions and the change log are read-only there.

## Device list (CSV)

The import takes exactly the format of `testfactory/layout/devices.csv` (decision E-44):

- UTF-8 (a byte order mark at the start is accepted), comma as separator, double quotes as in RFC 4180 (a value may hold commas, quotes and line breaks).
- The first line names exactly these 13 columns, in this order:
  `site`, `area`, `plant_id`, `plant_name`, `device_id`, `device_name`, `manufacturer`, `model`, `software_version`, `ip_address`, `address_source`, `protocols`, `notes`.
- One line per device. `site` and `area` are names, `plant_id` and `device_id` are keys (lower-case letters, digits and `-`; a plant key is unique among all plants, a device key among all devices, across all sites), `plant_name` and `device_name` are names. The other columns go unchanged into the fields of the device; `ip_address` must be an IPv4 or IPv6 address or empty.
- A line without `device_id` names a plant without devices; its `notes` become the notes of the plant.

Rules of the import:

- Plants and devices are matched by their keys, sites by name, areas by site and name.
- New entries are created, existing ones updated where a value differs; nothing is ever deleted. A device may move to another plant, a plant to another area. Sites and areas are never renamed.
- Contradictions inside the file are errors: the same `plant_id` with another name, area or site, or the same `device_id` twice.
- All or nothing: one error in the file, and nothing is saved. A dry run saves nothing either. Without a choice, the API and the command both do a dry run.
- Values are stored as text exactly as given, apart from spaces at the start and end.
- Limits: at most 10,000 lines, 8 MiB per line, and at most 1,000 errors are listed. Through the web UI the upload limit applies as well (`TWOX_UPLOAD_MAX_BYTES`).
- Every created or changed entry appears in the change log with the importing user.

## Configuration

All variables and their defaults are listed in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#configuration). New in milestone M1:

| Variable | Meaning |
| --- | --- |
| `TWOX_CACHE_URL` | Django cache in Valkey (database 2), shared by all API processes; holds the counters of the sign-in rate limit. Default `redis://valkey:6379/2`. |
| `TWOX_MEDIA_ROOT` | Directory of the uploaded files inside `api` and `worker`. Default `/data/media`, where compose mounts the volume `media-data`; change both together or not at all. |
| `TWOX_UPLOAD_MAX_BYTES` | Largest accepted upload in bytes, decimal: default `200000000` (200 MB). |
| `TWOX_E2E_USERNAME`, `TWOX_E2E_PASSWORD` | Test account of the browser test. Development values in `.env.example`; never use them for a real account. |

`create_account` also reads `TWOX_ACCOUNT_PASSWORD` (see above); it is not part of `.env`.

## Services and networks

| Service | Role | Reachable from |
| --- | --- | --- |
| `api` | Django API, the built web UI and the Django admin (ASGI server uvicorn) | the host, port 8000 on `127.0.0.1` only |
| `worker` | Celery worker for the queues `ingest`, `embed`, `default` | compose network only |
| `db` | PostgreSQL with pgvector | compose network only |
| `valkey` | Valkey: message broker and result store for Celery, cache with the counters of the sign-in rate limit | compose network only |
| `migrate` | applies the database migrations once, then exits | - |
| `docling` | docling-serve, document conversion (CPU) | `api` and `worker` only, over the internal network `docling-internal` |

- `docling` is attached only to the network `docling-internal`, which is marked `internal`: it has no route to the internet, and only `api` and `worker` are attached to it as well (decision E-32).
  `docling` also starts with its telemetry and remote services switched off; see `deploy/compose/compose.yaml`.
- Ollama is not a container. `api` and `worker` reach it on the host through `host.docker.internal` (set via `extra_hosts`).
- The development services `backend-dev`, `web-dev` (profile `dev`) and `e2e` (profile `e2e`) start only when named; see below.
- Data volumes: `db-data` (database), `valkey-data` (Valkey), `media-data` (uploaded files, mounted in `api` and `worker` at `/data/media`) and `web_node_modules` (packages of the web tooling).

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

- `OK: <address>/models is reachable, N model(s) reported`: Ollama (or another OpenAI-compatible server) answers. `0 model(s)` is fine in M1: no model is needed yet.
- `FAILED: cannot resolve host ...`: the container cannot resolve the host name; check `extra_hosts` in the compose file and that Docker is running.
- `FAILED: connection refused by ...`: Ollama is not running, or it listens on an address the containers cannot reach (see `OLLAMA_HOST` in the Ollama documentation).
- `FAILED: timeout ...`: something accepts the connection but does not answer, or a firewall drops it.
- `FAILED: unexpected response ...`: the address answers, but not with a model list.

On the development machine (Docker with WSL 2 on Windows) Ollama with its default binding was reachable without any change. Other setups, for example Docker directly on Linux, have not been checked.

## Maintenance

An upload is first written to a temporary file below `<TWOX_MEDIA_ROOT>/tmp/` (`upload-*.part`) and removed when it is stored or fails. Only a hard stop of the process (for example `SIGKILL` or out of memory) can leave such a file behind. Nothing removes them automatically; this command deletes those older than 24 hours (`--older-than-hours N`, at least 1):

```sh
docker compose exec api python manage.py remove_stale_uploads
```

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
- The tests sign in through the sign-in API of django-allauth (`web/e2e/fixtures.ts`), once per Playwright worker, so they stay well below the rate limit of the sign-in. Test data follow the rules there: names `e2e-<kind>-<suffix>` with a suffix unique per run, IP addresses only from 192.0.2.0/24.

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
- **Not ready for a network yet:** 2x runs over plain HTTP. What is still missing for operation over HTTPS behind a reverse proxy follows in milestone M6 (see the last point). Until then do not expose the port to a network.
- **Sign-in:** local accounts with user name and password, through the headless API of django-allauth on the application's own sign-in page `/login` (decision E-38). The browser holds only Django's session cookie (`HttpOnly`, `SameSite=Lax`), no token; the session lives in the database and lasts 8 hours.
  Every writing request of a signed-in user needs the CSRF token: the web UI sends the value of the cookie `csrftoken` in the header `X-CSRFToken`.
- **No self-service in M1:** no self-registration, no password reset by email, no change of one's own password, no email addresses; the allauth endpoints for these answer 404. Passwords and roles are set by a superuser in the admin or with `create_account --update`.
- **Rate limit of the sign-in:** at most 5 failed sign-ins per account in 5 minutes and 10 per IP address and minute, and at most 30 sign-in attempts per IP address and minute (allauth's defaults, set explicitly). The counters live in Valkey (`TWOX_CACHE_URL`), are shared by all API processes and survive a restart of `api`.
  A locked account gets HTTP 400 with the code `too_many_login_attempts` (also with the right password), the limit per IP address HTTP 429; the sign-in page explains both. Failed sign-ins are logged on the server with the user name only, never with password or IP address.
- **Roles** (decision E-40): two Django groups, `manage` and `read`.
  - `read` reads the structure, the files and the self-test and downloads files.
  - `manage` may also create and change structure entries, upload files, import the device list and read the change log.
  - A superuser counts as `manage`. A signed-in account without a role sees no data (HTTP 403).
  - Every API endpoint needs a role unless it says otherwise; the only exceptions are `/api/v1/health/` (open, for the container health check) and `/api/v1/me/` (any signed-in account). A test (`backend/tests/config/test_api.py`) fails for any other endpoint that is open.
- **Admin:** `/admin/` is for active superusers only. Sign in on `/login` first: the admin's own sign-in form is replaced by a redirect to `/login` and never signs anyone in, so the rate limit always applies. Signed-in accounts that are not superusers get 403.
- **Self-test:** `/api/v1/selftest/` and the page `/selftest` need a signed-in account with a role.
- **Files:** uploads go into the volume `media-data`, stored by their SHA-256 checksum. There is no public URL for them; they leave the server only through the API, for signed-in accounts with a role.
  A download is always an attachment (`Content-Disposition: attachment`) with `X-Content-Type-Options: nosniff` and `Content-Security-Policy: sandbox`; only PDF, Office and OpenDocument formats, Markdown, plain text and raster images keep their content type, everything else (HTML and SVG included) is sent as `application/octet-stream`. File names are cleaned of path parts and control characters.
  Uploads larger than `TWOX_UPLOAD_MAX_BYTES` (200 MB) are refused with HTTP 413 before Django reads the body.
- **Configuration files are not accepted yet** (decision E-42): they can contain passwords and keys, which are redacted only from milestone M5 on. The API refuses the kind `configuration` with HTTP 400. A configuration uploaded as an ordinary document is not recognised; do not upload configurations at all until M5.
- **Change log** (django-auditlog, decision E-43): every change to sites, areas, plants, devices, files, versions and accounts (including role, the active flag and the superuser right) with time, user and old and new values. It stores no IP addresses, no password hashes and no values from request headers. Only managers read it (`/audit`, `/api/v1/audit-log/`); superusers also see it read-only in the admin.
  It is not tamper-proof: the management command `auditlogflush` that comes with django-auditlog deletes entries and is not blocked, and anyone with access to the database can change the table. Protection in the database is to be checked again before version 0.1. Further gaps are listed under [Limits and known gaps](docs/ARCHITECTURE.md#limits-and-known-gaps).
- **Missing for HTTPS (milestone M6):** secure cookies, `CSRF_TRUSTED_ORIGINS`, HSTS and a content security policy for the pages; behind a reverse proxy also `ALLAUTH_TRUSTED_PROXY_COUNT` (otherwise every failed sign-in counts against the proxy's address); an installation guide and an `.env` template for testers without debug mode and without development passwords.
- **`TWOX_DEBUG`:** `.env.example` sets `TWOX_DEBUG=true` for development, so Django shows detailed error pages (a 404 in the browser lists the URL patterns). Outside development leave `TWOX_DEBUG` empty or set it to `false`; the default in `backend/twox/config/settings.py` is off.
- **Development values only:** `.env.example` contains no real secrets; never put production secrets into it. `.env` is ignored by Git.
- **No telemetry:** the project's own code sends nothing anywhere. The `docling` service has its telemetry switched off and has no route to the internet. Operation without internet is a design goal; the first start needs the internet only to download images and packages.

## Licence

2x is licensed under the [Apache License 2.0](LICENSE).

The licence notices of the third-party code shipped in the web UI are generated during the image build and served at `/static/THIRD-PARTY-NOTICES.txt` (for example <http://localhost:8000/static/THIRD-PARTY-NOTICES.txt>).
Every dependency, its licence and every exception is recorded in [docs/DECISIONS.md](docs/DECISIONS.md) (written in German, like the work orders and the status).
