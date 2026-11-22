# 2x

2x is a self-hosted, open-source application for small and medium-sized manufacturing companies.
For every device and plant it collects the documentation and the current configuration files, builds a profile from them and answers questions about them, with a source for every answer and a language model that runs on the company's own hardware.

**Status: milestone M2 "ingestion and search" is built; its acceptance is still open.** On top of the scaffold of M0 and of milestone M1 (devices and files) 2x now has:

- sign-in with local accounts and the two roles "Manage" and "Read";
- the structure of a company (site, area, plant, device) in a web UI and an API, editable by managers;
- an import of the device list from a CSV file, with a dry run first;
- documents per device: upload, versions, download;
- a change log of who changed what and when;
- a simplified interactive map of structure, devices and IP networks (preview of milestone M7);
- **ingestion** of every uploaded document: conversion with Docling (PDF, Office, Markdown, images), sections with page and headings, the state of every job on the file and device pages and on the ingest overview `/ingest`;
- a **search** over the ingested documents (`/search`): keywords in German and English, identifiers such as IP addresses or part numbers word for word, and, with the optional AI features, questions by meaning; every hit names file, version, page or headings and device;
- a web UI and API messages in German and English.

The **AI features are optional** (decision E-59): embeddings and the search by meaning need a model server (Ollama) and suitable hardware and are switched on with `TWOX_AI_ENABLED`. Without them everything above works, the search with keywords and identifiers only.

Not there yet: answers with sources from a language model, device profiles and configuration files. They are planned in the milestones of [docs/ROADMAP.md](docs/ROADMAP.md) (in German).
In code and configuration the project is called `twox`, because Python packages and environment variables cannot start with a digit.

How 2x is put together is described in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md); its known limits are listed there under [Limits and known gaps](docs/ARCHITECTURE.md#limits-and-known-gaps).

## Requirements

- **Docker with the Compose plugin.** Everything runs in Linux containers; nothing is installed on the host (no Python, no Node).
  The root `compose.yaml` uses `include`, so an old Compose v1 (`docker-compose`) does not work.
- **Disk space:** the document converter image (Docling) alone needs about 7.6 GB on disk (about 2.2 GB download).
- **Memory:** Docling converts on the CPU and needs a lot of memory for large manuals. Measured in work order 057: up to 6.6 GiB for a manual of 267 pages, 2.8 GiB when idle (Docker VM with 15.5 GiB and 16 CPUs). The `docling` service is limited to 8 GiB including swap (`TWOX_DOCLING_MEM_LIMIT`, decisions E-60 and E-62), so the Docker VM needs at least that much plus the other services.
- **Optional: [Ollama](https://ollama.com/)** on the host, outside the containers, for the AI features (see [Ingestion and search](#ingestion-and-search)). Without `TWOX_AI_ENABLED` nothing talks to it.

## Quick start

Run everything from the repository root.

1. Create your local configuration from the template. It holds development values only and is never committed:

   ```sh
   cp .env.example .env
   ```

   (Windows PowerShell: `Copy-Item .env.example .env`)

   The template switches the AI features on (`TWOX_AI_ENABLED=true`). Without Ollama and the embedding model, set it to `false`; otherwise every ingest job ends with an error in its last step (the sections are kept and found by keyword).

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

   For the test factory the result is 1 site, 3 areas, 10 plants and 13 devices, each with its device class (five PLCs, four controllers, one computer, one router, one robot, one firewall). A second import changes nothing (everything "unchanged").

6. Upload a document on a device page. It is ingested on its own; the file page shows the state ("Queued", "Ingesting", "Ingested" with pages and sections, "Error" or "Skipped"), and **Search** finds its content once it is ingested. Details: [Ingestion and search](#ingestion-and-search).

7. Optional: the self-test page <http://localhost:8000/selftest> shows three cards: **Database - OK** with the PostgreSQL server version, **Worker - OK** with the result `pong` and the round-trip time, and **AI features**: "Not enabled" (a neutral card, no error) with `TWOX_AI_ENABLED` off, otherwise OK with model and vector length, or the error. With the AI features on, the same card also names the chat model (`TWOX_CHAT_MODEL`) and whether it is ready; it only reads the model list of Ollama and lets the model generate nothing. While no chat model is set, the card stays OK with the calm hint "Chat model not set yet"; a set chat model that is missing, a cloud model or not able to generate text makes the card fail with the reason.
   "Check again" repeats the test. If the worker is stopped, the worker card turns red and shows the error from the API.

Stop the services with `docker compose down`. To also delete the data volumes (database, Valkey, the uploaded files and stored Docling answers in `media-data`, the `node_modules` volume of the web tooling), run:

```sh
docker compose --profile dev --profile e2e down -v
```

## The web UI

| Address | Page | Who |
| --- | --- | --- |
| `/` | Structure: tree of sites, areas, plants and devices with the number of devices, search by name, key or IP address; forms to create and change entries | `read`; forms `manage` |
| `/map` | Map: sites, areas, plants, devices and their IP networks as an interactive drawing (preview) | `read` |
| `/search` | Search in the ingested documents: one field for words, identifiers or a question, a choice of device; hits with page, headings, how they were found, a marked snippet and links to file and device | `read` |
| `/ingest` | Ingest overview: the ingest jobs of all devices, filtered by state and device; by default only what needs attention (error, running, queued) and only the newest job of each version | `read`; "Ingest again" and "Started by" `manage` |
| `/devices/<id>` | One device with all its fields and its files with their ingest state; editing the device and uploading a new file | `read`; editing and upload `manage` |
| `/documents/<id>` | One file with all versions (newest first), download and ingest state of every version, upload of a new version, change log of the file | `read`; upload, "Ingest again" and change log `manage` |
| `/import` | Import of the device list (dry run, then apply) | `manage` |
| `/audit` | Change log, filtered by kind of object and user | `manage` |
| `/selftest` | Self-test of database, worker and AI features | `read` |
| `/settings` | Settings (theme, accent colour, language, motion), from the user menu | `read` |
| `/login` | Sign-in | everyone |
| `/admin/` | Django admin; deleting entries is possible only here | superusers |

Below 1280 px the header shows the navigation as icons only (the text is the accessible name and the tooltip).
The language switch in the user menu (before sign-in: in the header) and on the settings page changes between German and English; the first choice follows the browser.
Nothing can be deleted in the web UI or the API. A superuser can delete sites, areas, plants and devices in the admin, as long as nothing hangs below them; files, versions, the change log, ingest jobs and sections are read-only there.

## Device list (CSV)

The import takes exactly the format of `testfactory/layout/devices.csv` (decisions E-44 and E-53):

- UTF-8 (a byte order mark at the start is accepted), comma as separator, double quotes as in RFC 4180 (a value may hold commas, quotes and line breaks).
- The first line names exactly these 13 columns, in this order:
  `site`, `area`, `plant_id`, `plant_name`, `device_id`, `device_name`, `manufacturer`, `model`, `software_version`, `ip_address`, `address_source`, `protocols`, `notes`.
  A 14th column `device_class` may follow as the last one; then every line has 14 values. Files with 13 columns stay valid.
- One line per device. `site` and `area` are names, `plant_id` and `device_id` are keys (lower-case letters, digits and `-`; a plant key is unique among all plants, a device key among all devices, across all sites), `plant_name` and `device_name` are names. The other columns go unchanged into the fields of the device; `ip_address` must be an IPv4 or IPv6 address or empty.
- `device_class` is the kind of device, one of `plc`, `controller` (controller or embedded device), `computer` (computer or edge device), `router`, `firewall`, `robot`, `other`, written exactly like this. Any other value is an error at its line and column. Without the column, or with an empty value, a new device gets `other` and an existing device keeps its class. In the web UI and the admin the class is a choice in the device form.
- A line without `device_id` names a plant without devices; its `notes` become the notes of the plant. Its device columns, `device_class` included, stay empty.

Rules of the import:

- Plants and devices are matched by their keys, sites by name, areas by site and name.
- New entries are created, existing ones updated where a value differs; nothing is ever deleted. A device may move to another plant, a plant to another area. Sites and areas are never renamed.
- Contradictions inside the file are errors: the same `plant_id` with another name, area or site, or the same `device_id` twice.
- All or nothing: one error in the file, and nothing is saved. A dry run saves nothing either. Without a choice, the API and the command both do a dry run.
- Values are stored as text exactly as given, apart from spaces at the start and end.
- Limits: at most 10,000 lines, 8 MiB per line, and at most 1,000 errors are listed. Through the web UI the upload limit applies as well (`TWOX_UPLOAD_MAX_BYTES`).
- Every created or changed entry appears in the change log with the importing user.

## Ingestion and search

Every upload of a document (kind `document`) starts its ingestion once the upload is saved; nothing else is needed. The worker sends the file to Docling, stores Docling's answer, cuts it into sections with page and headings and, with the AI features on, computes an embedding per section. How this works: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#ingestion).

- **Formats** (decision E-57): PDF, DOCX, XLSX, PPTX, Markdown (`.md`) and images (PNG, JPEG, TIFF, BMP, WEBP). Extension and content must match. Everything else (plain text, JSON, XML, YAML, `.conf`, HTML, ZIP, old Office formats …) is "Skipped" with the reason, at once and without Docling, and can still be downloaded. Configuration files (kind `configuration`) are not accepted at all before milestone M5.
- **States** of a job: queued, running (with the step `convert`, `sections` or `embed`), done, failed (with a kind of error and a cleaned technical text) or skipped. Every attempt is a job of its own; uploading or ingesting a version again adds a job and replaces the sections of that version only at the end.
- **Same content:** a file whose content was converted before (same SHA-256, on any device) reuses the stored Docling answer and the embeddings instead of converting it again.

### Docling

`docker compose up -d --wait` starts Docling together with the other services. If you started only some services (as the CI does), start it on its own:

```sh
docker compose up -d --wait docling
```

Healthy means only that the server runs: Docling loads its models with the first conversion. Check it with the command [`check_docling`](#check_docling), and try a conversion without saving anything. `--convert -` reads the file from standard input (`-T` turns off the terminal of `docker compose exec`); `--page-range FIRST LAST` limits the pages:

```sh
docker compose exec -T api python manage.py check_docling --convert - --page-range 1 2 < testdata/klein/recht/BetrSichV.pdf
```

Expected: `OK: converted 2 pages, 25 texts, 2 tables in 6.1s (docling: 3.4s)` (times vary; the first conversion after a start is slower). From standard input Docling sees a file called `upload.pdf`; for other formats give the extension with `--suffix`, for example `--suffix .md`. `--json-out -` prints Docling's JSON instead of the `OK:` line.

Measured on the development machine (work order 057, CPU only, one Docling worker): 0.65 to 1.7 s per page for the vendor manuals of the test factory, 4.3 s per page for the BetrSichV of `testdata/klein/` (60 pages, 258 s in Docling, 292 s for the whole job; work orders 046 and 057), at most 283 s for one manual (255 pages). Docling converts one document after the other; further jobs wait in its queue.

### AI features: embeddings with Ollama

1. Install Ollama on the host and load the embedding model there (about 1.2 GB):

   ```sh
   ollama pull bge-m3
   ```

   `bge-m3` (MIT, 1024 dimensions) is the default model (E-56). The measurement in work order 057 found no advantage of the compared model `qwen3-embedding:0.6b`; the decision about the model after the measurement is still open with a7, and until then `bge-m3` stays the default.

2. Set `TWOX_AI_ENABLED=true` in `.env` (the template does) and recreate `api` and `worker` with `docker compose up -d --wait`.

3. Check that the containers reach the model and that it embeds:

   ```sh
   docker compose exec api python manage.py check_llm --embed
   ```

   Expected: `OK: embedded a test sentence with bge-m3 at http://host.docker.internal:11434/v1/embeddings: 1024 dimensions in 0.04s` (the first call after the start of Ollama loads the model and takes a few seconds). With the AI features off the command prints `DISABLED: …` and exits with 0. More under [`check_llm`](#check_llm).

Measured (057): about 1.25 s per 100 sections with `bge-m3` once the model is loaded; the 2,623 sections of all test-factory manuals take 49 MB in the database, indexes included (about 19 kB per section).

#### Chat model for answers

Answers (milestone M3) need a second, local model that generates text. Which one becomes the default is decided after the measurement run (work order 128); until then `TWOX_CHAT_MODEL` stays empty, answers are unavailable and `manage.py` commands show the warning `twox.answers.W001`.

1. Load the chosen chat model on the host:

   ```sh
   ollama pull <chat model>
   ```

2. Set `TWOX_CHAT_MODEL=<chat model>` in `.env` (the name exactly as `ollama list` shows it) and recreate `api` and `worker` with `docker compose up -d --wait`. Cloud models (`…:cloud`, `…-cloud`) are refused, and so is a model without the capability `completion`, for example an embedding model.

3. Settings of Ollama on the host (environment variables of the Ollama service, not of the containers; concrete values are set after the model decision):

   - `OLLAMA_CONTEXT_LENGTH`: the context window in tokens. Ollama silently cuts a longer prompt to it, and the OpenAI-compatible interface `/v1` that 2x uses cannot set it per request. It has to hold the question, the retrieved sections and the answer. A larger window needs more memory (RAM or VRAM).
   - `OLLAMA_NUM_PARALLEL`: how many requests one loaded model answers at the same time. Each parallel slot needs its own share of the context memory.
   - `OLLAMA_KEEP_ALIVE`: how long a model stays loaded after the last request. Short saves memory, but the next answer first has to load the model again (several seconds for a large model). The embedding model and the chat model are loaded side by side, so the host needs memory for both.

4. Check the chat model with one short test prompt:

   ```sh
   docker compose exec api python manage.py check_llm --chat
   ```

   Expected: `OK: chat with <chat model>: first token after <x>s, <n> chunks in <y>s (<z> chunks/s)`; the answer itself is not shown. More under [`check_llm`](#check_llm).

**Logs of the host are sensitive data.** Ollama on the host can write prompts, and with them texts of the documents, into its own log, for example with debug logging (`OLLAMA_DEBUG`). Treat the Ollama log of the host like the documents themselves and leave debug logging off in operation.

### Starting and repeating ingestion

Uploads before M2, failed jobs or a new section size need a command. `ingest_versions` starts the ingestion of existing versions. `--user` names the account recorded as "Started by" (active, role `manage`); without `--commit` the command only counts and changes nothing:

```sh
docker compose exec api python manage.py ingest_versions --missing --user admin
docker compose exec api python manage.py ingest_versions --missing --user admin --commit
```

At least one selection is needed; several are combined:

| Option | Versions |
| --- | --- |
| `--missing` | versions without any ingest job (for example uploaded before M2) |
| `--failed` | versions whose newest job failed |
| `--stuck MINUTES` | jobs that are queued or running and were not updated for at least MINUTES minutes: they become failed (`timeout`) and their version starts again. For running jobs choose more than `TWOX_INGEST_TIMEOUT_SECONDS` (150 minutes), as the help of the command says: a shorter time can end a conversion that is still in progress, and Docling keeps converting it anyway. (Since work order 048 a job is also updated at every status query at Docling, at least once a minute.) `--stuck 0` takes every active job |
| `--all` | a new job for every version; builds the sections again with the current `TWOX_SECTION_MAX_CHARS` and reuses the stored Docling answers |
| `--version ID` | the version with this ID; may be given several times |

Only documents are taken, never configurations. A version with an active job that is not stuck is left alone. The output counts versions, created jobs, skipped formats, missing content, running and stuck jobs and ends with `Dry run: nothing was changed. Add --commit to start the jobs.` or `Saved.`

`embed_sections` computes the embeddings again, for example after the embedding model has changed or after the model service was down (the sections themselves stay). `--missing` (the default) takes the versions with sections without an embedding of `TWOX_EMBED_MODEL`, `--all` every version with sections, whose embeddings are cleared first:

```sh
docker compose exec api python manage.py embed_sections --user admin
docker compose exec api python manage.py embed_sections --all --user admin --commit
```

Without the AI features it prints `DISABLED: …` and creates nothing. After a change of `TWOX_EMBED_MODEL` the search by meaning finds only sections embedded with the new model, so run `embed_sections --all --user admin --commit` (or `--missing`, which takes every section of another model).

### Search

The page `/search` and `GET /api/v1/search/` search the newest ingested version of every document:

- **Keyword:** full-text search in German and English (word forms: "Steuerungen" finds "Steuerung") and as written. `-word` excludes a word, `"two words"` in quotes is a phrase.
- **Exact:** identifiers in the query (IPv4 and IPv6 addresses with or without prefix, MAC addresses, part numbers and codes such as `PLC-01`, `S7-1200` or `E1234`) are searched word for word: `192.168.0.5` does not find `192.168.0.50`.
- **Meaning** (AI features only): the query is embedded and the 50 nearest sections take part. Without the AI features the page says "Keyword search (AI features not enabled)" in a calm line; if the model service fails, the search falls back to keywords and says "Keyword search only – language model not reachable".
- **Order:** a query that is essentially identifiers (an identifier and at most one other word) puts the sections that contain them first; a question with words is ranked by keyword and meaning together, and an identifier in it counts only through these two (E-61). Without the search by meaning, exact hits always come first. Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#search).
- The same content on several devices is one hit with all its places. A hit from an older version is marked "Older version".

To measure how well the search finds what the test questions expect, `evaluate_search` reads a probe list on standard input and prints rank, Recall@5, Recall@10 and MRR for keyword, vector and combined search (never section texts):

```sh
docker compose exec -T api python manage.py evaluate_search < backend/twox/search/probes/m2.json
```

The probes refer to the manuals of the test factory (by manifest id and checksum). A place in the other language edition of the same manual counts as correct as well (E-61): the probes on the documentation of the production line expect the same pages in the German and the English edition. Where they are not uploaded the output lists them as `not ingested` and ends with `Not ingested: 7 of 7 probes`. `--json` prints the same as JSON.

The probe lists that ship with the application can be named instead of piped in, and other cut-offs than 5 and 10 can be asked for:

```sh
docker compose exec -T api python manage.py evaluate_search --probes m3 --cutoffs 5,8,10,12
```

- `--probes NAME` reads `backend/twox/search/probes/NAME.json` (`m2`: the probes of M2; `m3`: the baseline of M3 with one probe per test question, questions 3, 7 and 10 also in other words).
- `--cutoffs` takes whole numbers from 1 to 50 in ascending order; the output then shows Recall@k and the correct hits per k, and for probes with several expected pages the first rank of each page.
- A **control probe** (id `control-…`, empty list `expected`) asks for something no document answers (`control-11`). It is searched but not judged and does not count in Recall or MRR; the output lists its first 10 hits per kind with identifiers only (section, version, checksum, pages, device).
- A place in a Markdown file has no pages; a probe gives it by `heading_path` (the headings from the top, matched as a prefix) and `path` (the file in the repository) instead of `pages`.

### Acceptance of M2 by hand

In a test environment with the manuals of the test factory uploaded to their devices (`testfactory/fetch.py` downloads them; vendor material never goes into the repository), Docling running and an account with the role `manage`:

1. Open **Ingestion**, status filter "All": no job is "Ingesting" or "Queued", and there is no notice "Jobs are running …" above the table.
2. For every required manual (all PDF and Office manuals of the production line and of the UR5e, without ZIP files; E-58) set the device filter: the newest row of the file shows "Ingested" with pages and sections. ZIP files (`aps-calibration-*`) stay "Skipped" with the reason; that is the intended state.
3. Open **Search** and search for `192.168.0.100`: among the first three hits is the documentation of the production line, German or English edition (E-61), with page 18, 31 or 38 (test question 1), marked "Exact", the address highlighted.
4. Ask in your own words about the payload of the UR5e: among the first five hits is the German UR5e user manual with page 16, 101 or 102 (test question 9).
5. Ask how the UR5e is released again after a stop by a protective device (E-33): among the first five hits is the German user manual (page 81, 84, 86 or 252) or the English software handbook (page 46) (test question 10).
6. With the AI features off the hits have the calm line "Keyword search (AI features not enabled)" above them, without a warning icon; with the AI features on and the model service not reachable the notice "Keyword search only – language model not reachable".
7. Errors are visible (E-58): upload a damaged PDF made by yourself on a device, or stop Docling (`docker compose stop docling`) and upload a PDF. In **Ingestion** (status "Error") and on the file page the job shows "Error" with an understandable message and the cleaned text under "Technical details". With Docling stopped this takes the retries first: 10 + 20 + 40 + 60 + 60 = 190 s with the default values.
8. As a manager click "Ingest version 1 again": a new job appears at the top; with "Also show older attempts" the older one is marked "Older attempt". An account with the role `read` has no such button.

The browser test automates these checks. Its local part runs only when `TWOX_M2_LOCAL=1` is set and needs the uploaded manuals; `TWOX_M2_REQUIRED` lists the file names of the required manuals (comma-separated) and `TWOX_M2_FAILED_FILE` the file name of a job that failed on purpose (step 7). Create the test account first (see [Browser test](#browser-test-service-e2e-profile-e2e)), then:

```sh
TWOX_M2_LOCAL=1 TWOX_M2_REQUIRED=<file names, comma-separated> TWOX_M2_FAILED_FILE=<file name> docker compose --profile e2e run --rm e2e npx playwright test e2e/m2-acceptance.spec.ts -g "local part"
```

Without `-g "local part"` the CI part of the same file runs as well; it creates a test device and two small files. Without `TWOX_M2_LOCAL` the local part is skipped (as in the CI); with it but without the two other variables it fails with a message.

## Configuration

All variables and their defaults are listed in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#configuration). New in milestone M2 (all optional; the defaults are in `.env.example`):

| Variable | Meaning |
| --- | --- |
| `TWOX_AI_ENABLED` | Switches the AI features on (embeddings, search by meaning). Default off; `.env.example` switches them on. Off: the model service is never contacted. |
| `TWOX_EMBED_MODEL`, `TWOX_EMBED_DIMENSIONS` | Embedding model in Ollama (`bge-m3`) and its vector length (1024; must match the database column). |
| `TWOX_EMBED_BATCH_SIZE`, `TWOX_EMBED_TIMEOUT_SECONDS`, `TWOX_EMBED_QUERY_PREFIX` | Texts per request (16), time limit of one request while ingesting (120 s), text put in front of search queries only (empty for `bge-m3`). |
| `TWOX_SEARCH_EMBED_TIMEOUT_SECONDS` | Time limit for embedding a search query (20 s); after it the search falls back to keywords. |
| `TWOX_INGEST_MAX_RETRIES`, `TWOX_INGEST_POLL_MIN_SECONDS`, `TWOX_INGEST_POLL_MAX_SECONDS` | Retries after a temporary error (5) and the wait between two status queries at Docling (10 to 60 s). |
| `TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS`, `TWOX_INGEST_TIMEOUT_SECONDS` | Time limit sent to Docling per document (7,200 s, at most that) and the deadline of a conversion from its start at Docling (9,000 s). |
| `TWOX_DOCLING_QUEUE_TIMEOUT_SECONDS` | Deadline of a job whose Docling task never starts, from the start of the job (86,400 s = 24 hours, at least `TWOX_INGEST_TIMEOUT_SECONDS`); long, so that a large batch waiting in Docling's queue is not cut off. |
| `TWOX_DOCLING_MEM_LIMIT` | Memory limit of the `docling` service (`8g`, compose `mem_limit` and `memswap_limit` with the same value: the limit includes swap). Above it Docker stops and restarts Docling; the job retries and fails with `docling_unavailable` ("converter unavailable") if the document needs more every time. |
| `TWOX_SECTION_MAX_CHARS` | Largest section in characters (2,000). |
| `TWOX_EMBED_TASK_MAX_SECONDS` | One embedding task works at most this long, then continues in a new task (240 s). |

The ingestion values are checked against each other at start (`check_ingest_timing` in `backend/twox/config/settings.py`); a value that does not fit stops `api`, `worker` and every `manage.py` command with a message that names it. An embedding length that does not match the database column stops them as well with the AI features on (system check `twox.ingest.E001`) and is only a warning with them off (`twox.ingest.W001`).

## Services and networks

| Service | Role | Reachable from |
| --- | --- | --- |
| `api` | Django API, the built web UI and the Django admin (ASGI server uvicorn) | the host, port 8000 on `127.0.0.1` only |
| `worker` | Celery worker for ingestion (queue `ingest`), embeddings (queue `embed`, only with the AI features on) and everything else (`default`); four processes | compose network only |
| `db` | PostgreSQL with pgvector (vectors) and pg_trgm (identifier search) | compose network only |
| `valkey` | Valkey: message broker and result store for Celery, cache with the counters of the sign-in rate limit | compose network only |
| `migrate` | applies the database migrations once, then exits | - |
| `docling` | docling-serve, document conversion (CPU) | `api` and `worker` only, over the internal network `docling-internal` |

- `docling` is attached only to the network `docling-internal`, which is marked `internal`: it has no route to the internet, and only `api` and `worker` are attached to it as well (decision E-32).
  `docling` also starts with its telemetry and remote services switched off; see `deploy/compose/compose.yaml`.
- Ollama is not a container. `api` and `worker` reach it on the host through `host.docker.internal` (set via `extra_hosts`).
- `docker compose stop worker` gives running tasks 60 seconds to finish; ingest tasks that are cut off go back into the queue.
- The development services `backend-dev`, `web-dev` (profile `dev`) and `e2e` (profile `e2e`) start only when named; see below.
- Data volumes: `db-data` (database), `valkey-data` (Valkey), `media-data` (uploaded files and stored Docling answers, mounted in `api` and `worker` at `/data/media`) and `web_node_modules` (packages of the web tooling).

Exact image versions are pinned in the compose files under `deploy/compose/`, in `backend/Dockerfile` and `web/Dockerfile`; package versions in `backend/uv.lock` and `web/package-lock.json`.

## Check commands

Two Django management commands check the external services. Each prints exactly one line that starts with `OK:` (exit code 0) or `FAILED:` (exit code 1); `check_llm` may also print `DISABLED:` (exit code 0). Both accept `--timeout SECONDS` (per step of the reachability check, default 5).

### `check_docling`

```sh
docker compose exec api python manage.py check_docling
```

- `OK: docling-serve <version> at http://docling:5001`: the service resolves, accepts connections and reports its version.
- `FAILED: ...`: the line names the failing step, for example `cannot resolve host 'docling'` (container not running in this compose project), `connection refused` (not listening yet) or `unexpected response`.

Run it in `api` or `worker`. `backend-dev` is deliberately not attached to the Docling network, so the command fails there with `cannot resolve host`.
`OK` means the server answers; Docling loads its models only with the first conversion.

With `--convert PATH` (`-` for standard input) the command converts one file instead and prints `OK: converted N pages, N texts, N tables in X.Xs (docling: Y.Ys)` or `FAILED: <kind of error>: <message>`. `--page-range FIRST LAST`, `--suffix .EXT` and `--json-out -` work only together with `--convert`; see [Docling](#docling). Nothing is stored.

### `check_llm`

```sh
docker compose exec api python manage.py check_llm
```

It reads `TWOX_LLM_BASE_URL` (default `http://host.docker.internal:11434/v1`) and asks the OpenAI-compatible interface for its model list.

- `OK: <address>/models is reachable, N model(s) reported`: Ollama (or another OpenAI-compatible server) answers.
- `FAILED: cannot resolve host ...`: the container cannot resolve the host name; check `extra_hosts` in the compose file and that Docker is running.
- `FAILED: connection refused by ...`: Ollama is not running, or it listens on an address the containers cannot reach (see `OLLAMA_HOST` in the Ollama documentation).
- `FAILED: timeout ...`: something accepts the connection but does not answer, or a firewall drops it.
- `FAILED: unexpected response ...`: the address answers, but not with a model list.
- `DISABLED: AI features are not enabled (TWOX_AI_ENABLED is false); the model service was not contacted`: a normal state, not an error.

`--embed` embeds one fixed test sentence with `TWOX_EMBED_MODEL` instead (time limit `TWOX_EMBED_TIMEOUT_SECONDS`, not `--timeout`):

- `OK: embedded a test sentence with <model> at <address>/embeddings: <n> dimensions in <x>s`.
- `FAILED: EmbeddingRejectedError: model '<model>' is not loaded in Ollama; load it with: ollama pull <model>`: the model is missing on the host.
- `FAILED: EmbeddingRemoteModelError: ...`: the name is an Ollama cloud model; only local models are allowed, and the client never asks Ollama about cloud models.
- `FAILED: EmbeddingDimensionError: ...`: the model gives vectors of another length than `TWOX_EMBED_DIMENSIONS`.
- `WARNING: ...` comes first when `TWOX_LLM_BASE_URL` points to another machine than this one: a model server in the own network is allowed, but texts of the documents go there.

`--chat` lets `TWOX_CHAT_MODEL` answer one fixed, self-written test prompt instead (at most 32 tokens, temperature 0, fixed seed; time limit `TWOX_CHAT_TIMEOUT_SECONDS`, not `--timeout`). The answer of the model is never printed or logged. The chat interface delivers text pieces, not tokens, so the rate is counted in `chunks`. `--chat` and `--embed` cannot be combined.

- `OK: chat with <model>: first token after <x>s, <n> chunks in <y>s (<z> chunks/s)`: the time until the first text piece (the first call after a start of Ollama includes loading the model) and the pieces per second.
- `FAILED: invalid configuration: TWOX_CHAT_MODEL is empty`: no chat model is set (see [Chat model for answers](#chat-model-for-answers)).
- `FAILED: ChatRejectedError: model '<model>' is not loaded in Ollama; load it with: ollama pull <model>`: the model is missing on the host.
- `FAILED: ChatRejectedError: model '<model>' cannot generate text ...`: the model has no capability `completion`, for example an embedding model.
- `FAILED: ChatRemoteModelError: ...`: an Ollama cloud model, by name or by the local model list; it is never asked.
- `FAILED: ChatUnavailableError: ...`: no connection, no answer within `TWOX_CHAT_TIMEOUT_SECONDS`, or the answer broke off.
- `FAILED: empty answer: ...`: the model answered without any text within the 32 tokens, for example because it spent them on reasoning.
- `WARNING: ...` comes first, as with `--embed`.
- `DISABLED: ...` with the AI features off, as without options.

On the development machine (Docker with WSL 2 on Windows) Ollama with its default binding was reachable without any change. Other setups, for example Docker directly on Linux, have not been checked.

## Maintenance

An upload is first written to a temporary file below `<TWOX_MEDIA_ROOT>/tmp/` (`upload-*.part`) and removed when it is stored or fails. Only a hard stop of the process (for example `SIGKILL` or out of memory) can leave such a file behind. Nothing removes them automatically; this command deletes those older than 24 hours (`--older-than-hours N`, at least 1):

```sh
docker compose exec api python manage.py remove_stale_uploads
```

An ingest job can stay "Queued" or "Ingesting" after a hard stop (worker killed, Valkey not reachable when the job was sent). `ingest_versions --stuck MINUTES --user admin --commit` ends such jobs and starts their versions again; see [Starting and repeating ingestion](#starting-and-repeating-ingestion).

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
- No test reaches Docling or Ollama: the tests use stand-ins (`backend/tests/ingest/fake_docling.py`, `fake_converter.py`, `backend/tests/answers/fake_ollama.py`, `backend/tests/search/fake_embedder.py`) and set `TWOX_AI_ENABLED` themselves; every AI-dependent part is tested with the AI features off and on (E-59). `backend/tests/acceptance/test_m2.py` runs the whole path from upload to search through the real tasks against the Docling stand-in.
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
- Before measuring the bundle with `npm run build`, delete `web/dist/` and `web/playwright-report/`: Tailwind scans them as well when they lie in `web/`.

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

Expected output: all tests passed (the local part of the M2 acceptance test is skipped), exit code 0. `e2e` uses the packages that `web-dev` installed (`npm ci`) in the shared volume.

- `TWOX_E2E_USERNAME` and `TWOX_E2E_PASSWORD` in `.env.example` are development values. Never use them for a real account.
- The password reaches the container as a variable name only (`-e TWOX_ACCOUNT_PASSWORD` without a value), not as a command-line argument.
- With `--update` the step can run again and again, also without `down -v`; it sets the role and password of the existing account.
- The tests sign in through the sign-in API of django-allauth (`web/e2e/fixtures.ts`), once per Playwright worker, so they stay well below the rate limit of the sign-in. Test data follow the rules there: names `e2e-<kind>-<suffix>` with a suffix unique per run, IP addresses only from 192.0.2.0/24.
- The browser test needs neither Docling nor Ollama: an uploaded plain-text file is skipped at once by the format check, and answers that need a model come from `page.route` in the test.

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

The CI (`.github/workflows/ci.yml`, jobs `backend`, `web`, `testfactory`, `e2e`) does not start `docling` and has no Ollama. So `check_docling`, `check_llm`, a real conversion, real embeddings and `evaluate_search` with ingested manuals run only locally; the tests use stand-ins instead. The local part of the M2 acceptance test is skipped. The CI does not run `testfactory/fetch.py`, and the test questions (`testfactory/questions.yaml`) are not yet run against a language model.

## Security notes

- **Port:** only `api` publishes a port, and only on `127.0.0.1` (default 8000, `TWOX_API_PORT`). Nothing is reachable from other machines.
- **Not ready for a network yet:** 2x runs over plain HTTP. What is still missing for operation over HTTPS behind a reverse proxy follows in milestone M6 (see the last point). Until then do not expose the port to a network.
- **Sign-in:** local accounts with user name and password, through the headless API of django-allauth on the application's own sign-in page `/login` (decision E-38). The browser holds only Django's session cookie (`HttpOnly`, `SameSite=Lax`), no token; the session lives in the database and lasts 8 hours.
  Every writing request of a signed-in user needs the CSRF token: the web UI sends the value of the cookie `csrftoken` in the header `X-CSRFToken`.
- **No self-service yet:** no self-registration, no password reset by email, no change of one's own password, no email addresses; the allauth endpoints for these answer 404. Passwords and roles are set by a superuser in the admin or with `create_account --update`.
- **Rate limit of the sign-in:** at most 5 failed sign-ins per account in 5 minutes and 10 per IP address and minute, and at most 30 sign-in attempts per IP address and minute (allauth's defaults, set explicitly). The counters live in Valkey (`TWOX_CACHE_URL`), are shared by all API processes and survive a restart of `api`.
  A locked account gets HTTP 400 with the code `too_many_login_attempts` (also with the right password), the limit per IP address HTTP 429; the sign-in page explains both. The message of the sign-in adapter about a failed sign-in names the user name only, never the password or the IP address.
  The access log of uvicorn has one line per request, failed sign-ins included, but without the client address (decision E-62): it names method, path and status only. The rate limit still counts per IP address internally; that address is not logged.
- **Roles** (decision E-40): two Django groups, `manage` and `read`.
  - `read` reads the structure, the files, the ingest jobs and the self-test, downloads files and searches.
  - `manage` may also create and change structure entries, upload files, start an ingestion again, import the device list and read the change log, and sees who started an ingest job.
  - A superuser counts as `manage`. A signed-in account without a role sees no data (HTTP 403).
  - Every API endpoint needs a role unless it says otherwise; the only exceptions are `/api/v1/health/` (open, for the container health check) and `/api/v1/me/` (any signed-in account). A test (`backend/tests/config/test_api.py`) fails for any other endpoint that is open.
  - There are no rights per device (E-40): every account with a role searches and reads all documents.
- **Admin:** `/admin/` is for active superusers only. Sign in on `/login` first: the admin's own sign-in form is replaced by a redirect to `/login` and never signs anyone in, so the rate limit always applies. Signed-in accounts that are not superusers get 403.
- **Self-test:** `/api/v1/selftest/` and the page `/selftest` need a signed-in account with a role.
- **Files:** uploads go into the volume `media-data`, stored by their SHA-256 checksum. There is no public URL for them; they leave the server only through the API, for signed-in accounts with a role.
  A download is always an attachment (`Content-Disposition: attachment`) with `X-Content-Type-Options: nosniff` and `Content-Security-Policy: sandbox`; only PDF, Office and OpenDocument formats, Markdown, plain text and raster images keep their content type, everything else (HTML and SVG included) is sent as `application/octet-stream`. File names are cleaned of path parts and control characters.
  Uploads larger than `TWOX_UPLOAD_MAX_BYTES` (200 MB) are refused with HTTP 413 before Django reads the body.
- **Configuration files are not accepted yet** (decision E-42): they can contain passwords and keys, which are redacted only from milestone M5 on. The API refuses the kind `configuration` with HTTP 400, and nothing of that kind is ingested. A configuration uploaded as an ordinary document is not recognised: plain-text formats (`.txt`, `.conf`, JSON, XML, YAML …) are skipped by the format check, but a configuration saved as `.md` or as PDF is converted, cut into sections and found by the search. Do not upload configurations at all until M5. Details: [Configuration files](docs/ARCHITECTURE.md#configuration-files).
- **Default credentials in vendor manuals** (E-57): some manuals list the user names and passwords of the delivery state. They are ingested like any other text and every account with a role finds them in the search. They are public vendor information about the delivery state, not about this plant; redaction in documents is checked with M5.
- **Ingestion:** Docling gets the file under a neutral name (`version-<id>.pdf`), never the original name. The technical error text of a job is cleaned of file names, paths, URLs and IP and MAC addresses and shown to both roles; the raw text goes to the server log only. Who started a job (`requested_by`) is shown to managers only.
- **Search texts** are not logged: the API logs no query, and a filter (`backend/twox/config/logging.py`) cuts the query string off every line of the access log (method, path and status stay; the client address is not logged either). The search page keeps the text in its address (`/search?q=…`), so it stays in the browser history.
- **Model server:** with the AI features on, the texts of all sections and every search query go to `TWOX_LLM_BASE_URL`. `check_llm --embed` warns when it points to another machine. Ollama cloud models are refused by name and by the local model list.
- **Change log** (django-auditlog, decision E-43): every change to sites, areas, plants, devices, files, versions and accounts (including role, the active flag and the superuser right) with time, user and old and new values. It stores no IP addresses, no password hashes and no values from request headers. Only managers read it (`/audit`, `/api/v1/audit-log/`); superusers also see it read-only in the admin. Ingest jobs and sections are not in the change log; a job records who started it and when.
  It is not tamper-proof: the management command `auditlogflush` that comes with django-auditlog deletes entries and is not blocked, and anyone with access to the database can change the table. Protection in the database is to be checked again before version 0.1. Further gaps are listed under [Limits and known gaps](docs/ARCHITECTURE.md#limits-and-known-gaps).
- **Missing for HTTPS (milestone M6):** secure cookies, `CSRF_TRUSTED_ORIGINS`, HSTS and a content security policy for the pages; behind a reverse proxy also `ALLAUTH_TRUSTED_PROXY_COUNT` (otherwise every failed sign-in counts against the proxy's address); an installation guide and an `.env` template for testers without debug mode and without development passwords.
- **`TWOX_DEBUG`:** `.env.example` sets `TWOX_DEBUG=true` for development, so Django shows detailed error pages (a 404 in the browser lists the URL patterns). Outside development leave `TWOX_DEBUG` empty or set it to `false`; the default in `backend/twox/config/settings.py` is off.
- **Development values only:** `.env.example` contains no real secrets; never put production secrets into it. `.env` is ignored by Git.
- **No telemetry:** the project's own code sends nothing anywhere. The `docling` service has its telemetry switched off and has no route to the internet. Operation without internet is a design goal; the first start needs the internet only to download images and packages, and `ollama pull` the model once.

## Licence

2x is licensed under the [Apache License 2.0](LICENSE).

The licence notices of the third-party code shipped in the web UI are generated during the image build and served at `/static/THIRD-PARTY-NOTICES.txt` (for example <http://localhost:8000/static/THIRD-PARTY-NOTICES.txt>).
Every dependency, its licence and every exception is recorded in [docs/DECISIONS.md](docs/DECISIONS.md) (written in German, like the work orders and the status).
