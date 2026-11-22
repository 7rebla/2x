# Pages, routes and data fetching

## Addresses

All addresses are in `../routes.tsx` (react-router, data mode, no framework mode and no Node server).
Django serves `index.html` for every path except `api/`, `static/`, `admin/`, `_allauth/` and `accounts/`,
so each address can be opened directly or reloaded.

| Address | Page file | Built by work order |
| --- | --- | --- |
| `/` | `StructurePage.tsx` | 032 |
| `/map` | `MapPage.tsx` (loaded lazily) | 039 |
| `/search` | `SearchPage.tsx` (loaded lazily) | 054 |
| `/ingest` | `IngestPage.tsx` (loaded lazily) | 055 |
| `/devices/:deviceId` | `DevicePage.tsx` | 032 |
| `/documents/:documentId` | `DocumentPage.tsx` | 036 |
| `/import` | `ImportPage.tsx` | 035 |
| `/audit` | `AuditPage.tsx` | 033 |
| `/login` | `LoginPage.tsx` | 030 |
| `/selftest` | `SelftestPage.tsx` | (done, M0) |
| `/settings` | `SettingsPage.tsx` (from the user menu, role `read`) | 070 |
| anything else | `../components/NotFound.tsx` | – |

A work order that builds a page replaces only its file here (and fills its own catalog, see `../locales/README.md`).
Routes, the frame (`../components/Layout.tsx`) and the navigation stay as they are.

## Frame and navigation

- `../components/Layout.tsx` draws the header (name, navigation, user menu) around every page, always on one line:
  every navigation entry has an icon (`../navigation.ts`, `../icons/README.md`); below 1280 px (`xl`) only the icons show,
  with the text as accessible name and tooltip, and a navigation that is still too wide scrolls on its own. From
  1280 px the header is wider than the page content (`max-w-7xl`), so the seven entries of M2 show their texts in
  German and English on one line (work order 055; `../../e2e/navigation.spec.ts` checks 1024 and 1280 px).
  The user menu (`../components/UserMenu.tsx`) is a button with the user name; it opens a panel with the role,
  the link to the settings, the language switch and "Sign out". Before sign-in the language switch stands in the header.
  An account without a role sees a hint above the page.
- `../navigation.ts` lists the navigation entries as data: path, key of the text in `nav.json` and the role
  that may see the entry (`requires`). `Layout` shows only the entries the user's role allows;
  `/import` and `/audit` need `manage`, the others `read`. Pages with a parameter and the sign-in page are not listed.
- Page headings are `<h2>`, written with `AnimatedHeading` (`MaskedTitle` for the device and file title, `../components/TextMotion.tsx`); the `<h1>` is the name in the header.
- Colours only through the theme tokens (`bg-surface`, `text-fg-muted`, `border-line` …), never Tailwind's palette; see `../theme/README.md`.
- A page that throws while rendering shows `ErrorMessage` inside the frame (`../components/RouteError.tsx`).

## Sign-in and roles

- The sign-in state comes from `GET /api/v1/me/` (`../session.ts`, one TanStack query). DRF answers a missing
  session with 403, so 403 from `/api/v1/me/` means "signed out".
- Every page except `/login` sits inside `RequireSession` (`../components/SessionGuards.tsx`): without a session
  the browser goes to `/login?next=<address>` and comes back after signing in. `next` accepts only paths of
  this application (`safeNextPath`); `/admin/…` is opened as a page of its own.
- Every page also sits inside `RequireRole` with the role from `navigation.ts` (`read` for pages without an entry).
  A missing role shows "no permission" in the frame, without a redirect.
- A 403 of any other API call makes the app ask `/api/v1/me/` again: 403 there means the session expired
  (to the sign-in page), 200 means only the permission is missing (`ErrorMessage` shows "no permission").
- Buttons that write are shown only to `manage`:

  ```tsx
  import { useRole } from "../session.ts";

  const { canManage } = useRole();
  return canManage ? <button type="button">…</button> : null;
  ```

- Sign-in and sign-out go through the browser API of django-allauth (`../api/auth.ts`); allauth is not part of
  the OpenAPI schema. `../api/client.ts` adds `X-CSRFToken` (from the cookie `csrftoken`) to every writing
  request and `Accept-Language` to every request, for the generated client and for `auth.ts`.

## Fetching data

Pages read and write through TanStack Query with the options the generator writes per endpoint:

```tsx
import { useQuery } from "@tanstack/react-query";
import { selftestRetrieveOptions } from "../api/generated/@tanstack/react-query.gen.ts";
import { ErrorMessage } from "../components/ErrorMessage.tsx";
import { Loading } from "../components/Loading.tsx";

const query = useQuery(selftestRetrieveOptions());
if (query.isPending) return <Loading />;
if (query.isError) return <ErrorMessage error={query.error} />;
```

- `../api/errors.ts` turns every failed call into an `ApiError` with `kind` (`http`, `network`, `invalid-answer`),
  the HTTP `status` and the API's text (`detail` of DRF, or a plain-text body). `ErrorMessage` shows status and text.
- `../api/queryClient.ts` holds the defaults: only a missing answer is tried again (twice); HTTP errors show at once.
- `main.tsx` installs both (and the client configuration) once. Tests render the whole app with
  `../test/renderApp.tsx` and fake the server with `../test/fakeApi.ts` (who `/api/v1/me/` reports, other answers).
- The self-test page keeps its own loading code from M0 (`../api/selftest.ts`).

## Structure and devices

- `StructurePage.tsx` (`/`) loads the four lists (`sites`, `areas`, `plants`, `devices`) and builds the tree
  site > area > plant > device in the browser (`structure/tree.ts`), with the number of devices on every level.
  The search filters that tree in the browser by name, key or IP address; it sends no request.
- `DevicePage.tsx` (`/devices/:deviceId`) shows every field of one device, the chain as breadcrumb and
  `../components/DeviceFiles.tsx` (the files of the device, see "Files").
  An id that cannot be a device id, or a 404 of the API, shows `NotFound`.
- `structure/forms.tsx` holds the forms of all four levels: React 19 form actions (`useActionState`),
  no form library, the generated mutation options of TanStack Query. Only `manage` sees the buttons (`useRole()`).
- Field errors: `structure/save.ts` sends a write call with a fetch of its own that keeps a copy of a 400 answer
  (the shared `ApiError` keeps only status and `detail`). DRF's messages then appear at their fields
  (`aria-invalid`, `aria-describedby`); keys without a field (`non_field_errors`, `detail`) appear above the fields.
  The entry stays in the form.
- After saving, every cached answer except the sign-in state is fetched again (`reloadAfterSave`), then the form closes.
- Tests fake the structure API with `structure/testData.ts` (names `Test …`, addresses from 192.0.2.0/24).
- Device class (E-53, work order 074): `structure/deviceClass.ts` lists the classes and maps each to its icon
  (`deviceClassIcon()`, `../icons/README.md`). A device row in the tree shows the icon and the label of its class
  instead of the word "device"; the device page shows the icon before the name and in the breadcrumb, and the class
  as the field "Device class". Plants show the plant icon (`PLANT_ICON`).

## Files

- `../components/DeviceFiles.tsx` (on the device page) lists the files of the device with their newest version:
  title (link to the file page), kind, number, date, size, user, the checksum shortened (a click shows all of it)
  and a download link. Managers upload new files there; the kind "configuration" is shown but cannot be chosen,
  because configurations are rejected until redaction arrives in M5 (E-42); the form says so.
- `DocumentPage.tsx` (`/documents/:documentId`) shows one file with all versions, newest first, each with a
  download link, the form for a new version (managers) and the change log of the file (`AuditTrail`, managers only,
  because the change log API is readable for managers only).
- Ingestion state (work order 053): the building blocks are in `../components/files/IngestStatus.tsx` and are meant to
  be reused (055). `IngestStatusBadge` shows the newest job of a version (field `ingest`): queued, ingesting (with the
  step), ingested (pages and sections), error, skipped, or not ingested; `compact` leaves out step and counts (device
  page). `IngestError` shows the translated message per kind of error (one per `error_code`, a general text for
  unknown kinds) and folds the technical `error_detail` away (rendered as text only); for a done job that was
  converted only in part (`partly_converted`) it shows that hint. `IngestRetryButton` (managers, documents only,
  hidden while a job is queued or running) calls `POST /api/v1/document-versions/<id>/ingest/`; a 409 appears as
  "already being ingested", a 400 as "configurations are not ingested". The file page and the device page poll every
  5 s (`INGEST_POLL_INTERVAL_MS`) while a shown version has a queued or running job, and not otherwise. Skipped and
  queued are neutral, not errors; with the AI features off (E-59) missing embeddings are not shown at all.
- Downloads are plain links to `/api/v1/document-versions/<id>/download/`; the API answers with
  `Content-Disposition: attachment` and the session cookie goes along.
- Uploads go through the generated client (multipart/form-data) in `../components/files/upload.ts`, with a fetch of
  its own that keeps a copy of 400, 409 and 413 answers: field errors appear at their fields, 409 names the version
  with the same content, 413 the limit (read from the API's message), and the duplicates of a successful upload
  appear with links to the device and the file. There is no progress display (the client reports none).
- File names, titles and user names are rendered as text, never through the interpolation of i18next.
- Tests fake the file API with `../components/files/testData.ts`. Under jsdom, Node's Request cannot read
  jsdom files, so tests use `textFile()` and `fakeUploadApi()`, which send forms as multipart text.

## Device list import

- `ImportPage.tsx` (`/import`, role `manage`) uploads the device list as CSV through the generated
  `devicesImportMutation` (`multipart/form-data`, CSRF header from `../api/client.ts`). The page describes the
  13 columns (`deviceListColumns`, the order of E-44) and the optional 14th column `device_class`
  (`deviceListOptionalColumn`, E-53) with its values (`deviceClasses` from `structure/deviceClass.ts`, which the
  device form uses for its choice as well; labels under `deviceClass` in `assets.json`).
- Step 1 sends the file with `dry_run=true`. The answer is always a report (200, `../components/ImportReportView.tsx`):
  counts per level (created, changed, unchanged) or, if the file has errors, every error with line, column and
  the message of the API. Values from the file and messages are shown as text.
- Only a dry run without errors offers "Apply": the same file again with `dry_run=false`. After saving, the cached
  answers are fetched again (`reloadAfterSave`) and the page links to the structure. Choosing another file drops
  the report.
- 400 (form not accepted) shows the messages of the API (`structure/save.ts`), 413 the API's message with the upload
  limit, everything else `ErrorMessage`.
- Under jsdom, Node's fetch sends a jsdom `File` without its content; `ImportPage.test.tsx` therefore checks the
  file handed to `FormData.append` and reads the other fields from the multipart body.

## Search

- `SearchPage.tsx` (`/search`, role `read`, entry "Search" with the icon `search`) searches the ingested files through
  `GET /api/v1/search/` (`searchOptions` of the generated client). `routes.tsx` loads it with `lazy()`, like the map.
- The form has one field for a term, an identifier or a question (at most 500 characters) and a choice of device
  (`GET /api/v1/devices/`, grouped by plant; "All devices" first). Sending the form (Enter or the button) writes the
  trimmed text and the device into the browser address, `/search?q=…&device=…` (question 1 of work order 052): a
  search can be linked, reloaded and reached with Back. A device value that cannot be an id is ignored; a device that
  is not in the list is named by its id. The API drops the query part from its access log (work order 052).
- States: no search text (a hint, no request), loading, no hits, error (`ErrorMessage`), hits.
- `semantic` of the answer: `unavailable` shows the hint "Keyword search only – language model not reachable";
  `disabled` (AI features switched off, E-59) shows one calm line, no warning; `used` shows nothing.
- A hit (`search/SearchHitView.tsx`) shows the page ("p. 31", "pp. 31–32"; German "S. 31", "S. 31–32"), the heading
  path, how it was found (exact, keyword, meaning), the snippet and every place it is stored at: file (link to
  `/documents/:id`), version with its file name, "Older version" when `is_latest` is false, device (link to
  `/devices/:id`) and plant.
- The snippet is plain text. `search/snippet.ts` cuts it into pieces by the `highlights` of the API, which count
  Unicode code points: the snippet is split with `Array.from` first, so marks do not slip after an emoji or another
  character outside the BMP. The found places are `<mark>` elements with text inside; nothing is rendered as HTML.
- Tests fake the search API with `search/testData.ts` (test sentences only, devices of `structure/testData.ts`).

## Ingest overview

- `IngestPage.tsx` (`/ingest`, role `read`, entry "Ingestion" / "Einlesen" with the icon `ingest`) lists the ingest
  jobs of all devices through `GET /api/v1/ingest-jobs/` (`ingestJobsListOptions`), newest first, 50 per page with
  "previous" and "next" like `/audit`. `routes.tsx` loads it with `lazy()`.
- Filters: status, device and the switch "Also show older attempts" / "Auch ältere Versuche zeigen", all in the address
  (`/ingest?status=…&device=…&older=1`) and applied at once. Without a status the page asks for `failed`, `running` and
  `queued` (what needs attention); one state can be chosen, and `all` sends no status, so ingested and skipped jobs
  show as well. An unknown status means the default, a device value that cannot be an id means all devices, a device
  that is not in the list is named by its id. A new filter starts on page 1.
- Newest job only (work order 064): every job is one attempt (E-55). Without the switch the page sends `latest=true`,
  so the API lists only the newest job of each version (the job of the field `ingest`, embedding jobs included) and
  applies status and device to those. A failed attempt that a later one has ingested is therefore not "open" any
  more. With `?older=1` the page sends no `latest` and lists every attempt.
- A row shows the device (link, key), the file (link to `/documents/:id`) with version and file name, the status with
  its step and the page and section counts (`IngestStatusBadge`), the translated message with the technical text to
  unfold (`IngestError`), the times (created, finished) and, for `manage` only, who started the job ("System" for
  none; the API sends `null` to `read`, E-57). All three building blocks come from
  `../components/files/IngestStatus.tsx` (work order 053); `error_detail` and every name are rendered as text.
- "Ingest again" (`IngestRetryButton`) stands on every row of a manager whose job is not queued or running and is the
  newest job of its version. A row with `is_latest` false (only with older attempts shown) says "Older attempt" and
  has no button, wherever the newer job is listed; the API decides, not the order of the page.
- While a listed job is queued or running, the page asks again every 5 seconds (`INGEST_POLL_INTERVAL_MS`) and says
  so; otherwise it does not poll. With the AI features switched off (E-59) no job has the step "embed".
- Tests fake the list (with `latest` and `is_latest`) and `POST …/ingest/` inside `IngestPage.test.tsx`;
  `../../e2e/ingest.spec.ts` uploads a plain-text file, which the format check skips without a converter, and checks
  the switch with answers of its own (`page.route`).

## Map

- `MapPage.tsx` (`/map`, role `read`) is an interactive preview of milestone M7 (work order 039, E-48), drawn with
  React Flow (`@xyflow/react`). `routes.tsx` loads it with `lazy()`, so React Flow is not part of the main bundle.
- It reads the same four lists as the structure page. `map/graph.ts` turns them into nodes and edges: sites, areas and
  plants as groups (parent nodes), devices inside their plant, and one network node per IPv4 /24 or IPv6 /64 that
  holds a device address. The only edges are the dashed "device is in network" lines. Nothing else is derived; links
  from configuration files come with M5/M7.
- The layout is a grid per group, computed from fixed node sizes; inputs are sorted first, so the same data gives the
  same positions. Moved nodes are not saved; a reload, or new data, restores the layout.
- A click or Enter on a device opens `/devices/:id`. Selected, focused and found devices are highlighted with their
  network line. The search (name, key, IP address) marks matches and fits the view to them. The network nodes can be
  hidden. The React Flow attribution link stays visible (the project asks to remove it only with a Pro subscription).
- A device node shows the icon of its class with the class as tooltip; the label of the node names the class too.
- Node components live in `map/nodes.tsx`; every text from the data is rendered as text. Under jsdom the tests stub
  `ResizeObserver`, `DOMMatrixReadOnly`, `offsetWidth`/`offsetHeight` and `getBBox` (`map/MapPage.test.tsx`).
