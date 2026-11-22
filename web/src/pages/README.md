# Pages, routes and data fetching

## Addresses

All addresses are in `../routes.tsx` (react-router, data mode, no framework mode and no Node server).
Django serves `index.html` for every path except `api/`, `static/`, `admin/`, `_allauth/` and `accounts/`,
so each address can be opened directly or reloaded.

| Address | Page file | Loaded | Built by work order |
| --- | --- | --- | --- |
| `/` | `StructurePage.tsx` | main bundle | 032 |
| `/map` | `MapPage.tsx` | on demand (`lazyPage()`) | 039 |
| `/search` | `SearchPage.tsx` | on demand (`lazyPage()`) | 054 |
| `/ingest` | `IngestPage.tsx` | on demand (`lazyPage()`) | 055, 064 |
| `/devices/:deviceId` | `DevicePage.tsx` | on demand (`lazyPage()`) | 032 |
| `/documents/:documentId` | `DocumentPage.tsx` | on demand (`lazyPage()`) | 036 |
| `/import` | `ImportPage.tsx` | on demand (`lazyPage()`) | 035 |
| `/audit` | `AuditPage.tsx` | on demand (`lazyPage()`) | 033 |
| `/login` | `LoginPage.tsx` | main bundle | 030 |
| `/selftest` | `SelftestPage.tsx` | on demand (`lazyPage()`) | (done, M0) |
| `/settings` | `SettingsPage.tsx` (from the user menu, role `read`) | on demand (`lazyPage()`) | 070 |
| anything else | `../components/NotFound.tsx` | main bundle | – |

A work order that builds a page replaces only its file here (and fills its own catalog, see `../locales/README.md`).
Routes, the frame (`../components/Layout.tsx`) and the navigation stay as they are.

### Loading on demand

Only the sign-in page and the start page (`/`, structure) are part of the main bundle. Every other page is
loaded when it is opened (work order 062): `routes.tsx` wraps it with `lazyPage()` from
`../components/PageLoading.tsx`, which combines `React.lazy`, `Suspense` and a boundary:

- While the code arrives, `PageLoading` keeps some room and shows the common loading state after 300 ms
  (turning icon and loading shimmer, pattern D; both stand still with reduced motion).
- If the code cannot be loaded (connection lost, or a new build replaced the files while the page was open),
  `PageLoadFailed` explains this and offers "Reload". Every other error of the page goes to the route's
  error element as before.
- A new page is added to the `pages` table in `routes.tsx`; tests get its code through `preloadPages()`,
  which `../test/renderApp.tsx` calls once per test file.

## Frame and navigation

- `../components/Layout.tsx` draws the header (name, navigation, user menu) around every page, always on one line
  and 76 px high at every width. Every navigation entry has an icon (`../navigation.ts`, `../icons/README.md`).
  Three forms (E-65 point 3, work order 082):
  - From 1280 px (`xl`) icon and text side by side; the seven entries of M2 fit on one line in German and English
    (work order 055), a navigation that is still too wide scrolls on its own.
  - From 768 to 1279 px the icon above a short text (13 px on a 16 px line, E-65 point 5; `nav:short.*` in
    `locales/*/nav.json`, at most ten characters and part of the full text). The full text stays the link's text,
    accessible name and tooltip; the short text is drawn by CSS (`.nav-short` in `../index.css`) inside an
    `aria-hidden` element. Where it fits, the short text is a whole word of the full name (English: the full names,
    "Log" for "Change log"). Two German compounds are cut to their last part, because the whole word does not fit
    at 768 px next to a user name as wide as its button: "Karte" for "Landkarte" (29 px more) and "Protokoll" for
    "Änderungsprotokoll". If the entries still do not fit, the navigation scrolls on its own instead of covering
    the user menu or widening the page; the focus ring of an entry is then drawn inside it (`-outline-offset-2`), so
    the scroll box does not cut it off.
  - Below 768 px (`NARROW_QUERY`, read with `matchMedia`) the header holds only the name and the button "Menu"
    (`aria-expanded`, `aria-controls`). It opens a panel under the header with every entry (icon and full text, one
    per line) and the content of the user menu (`UserMenuContent`). The panel closes on Escape (focus back on the
    button), as soon as the focus leaves button and panel (Tab after "Sign out", Shift+Tab before the button; the
    focus stays where it went, WAI-ARIA disclosure navigation), on a click outside, on a choice (focus on the button, then on the new page's heading) and when the window
    grows to 768 px.
  `../../e2e/navigation.spec.ts` checks one line at 768, 1024 and 1280 px in German and English, 768 px in German
  with a long user name, and the menu at 375 px, also with the keyboard alone.
- Page grid (work order 080, E-65 point 1): header and page content share one grid, `PAGE_GRID` in
  `../components/Layout.tsx` (`max-w-7xl`, at most 1280 px, `px-4`), so the brand mark and the page heading start on
  the same line at every width (`../../e2e/layout.spec.ts` measures 375, 1024 and 1600 px). Tables, cards and the map
  take the whole grid. Paragraphs directly inside a page's `<section>` (the introduction) are held to `max-w-prose` by
  `PAGE_PROSE` on `<main>`; a page needs no class of its own for that. Form pages keep a narrow column at the left edge
  of the grid: settings `max-w-2xl`; the self-test keeps heading and button at `max-w-xl` and sets its result cards in
  one column, two from 1024 px (`lg`) and three from 1280 px (`xl`). The sign-in page follows with work order 086.
  The user menu (`../components/UserMenu.tsx`) is a button with the user name; it opens a panel with the role,
  the link to the settings, the language switch and "Sign out". Before sign-in the language switch stands in the header.
  An account without a role sees a hint above the page.
- `../navigation.ts` lists the navigation entries as data: path, key of the text in `nav.json` and the role
  that may see the entry (`requires`). `Layout` shows only the entries the user's role allows;
  `/import` and `/audit` need `manage`, the others `read`. Pages with a parameter and the sign-in page are not listed.
- Headings (work order 078): the page heading is the only `<h1>` of the page, written with `AnimatedHeading`
  (`MaskedTitle` for the device and file title, `../components/TextMotion.tsx`; both default to level 1). Sections of a
  page are `<h2>`, parts inside them `<h3>`. The name in the header is a link to `/`, not a heading.
- Browser title (WCAG 2.4.2): every page calls `usePageTitle(<text of its heading>)` from `../hooks/usePageTitle.ts`
  before any early return, which sets "Structure – 2x" (page, en dash, `common:appTitle`). The device and file pages
  pass the name once it is loaded and `null` for a 404, so `NotFound` names the page. Without a page the title is the
  name of the application.
- Skip link and focus (WCAG 2.4.1, 2.4.3): the first stop of the keyboard is the link "Skip to content" / "Zum Inhalt";
  it focuses `<main id="inhalt" tabIndex={-1}>` without writing a fragment into the address. After a change of page
  (another path; not a change of the query, not the first load, not a redirect before the user has done anything)
  `Layout` moves the focus to the `<h1>` of the new page, also when it arrives later (loaded on demand, data still
  loading), but never takes the focus back from an element the user moved to.
- Colours only through the theme tokens (`bg-surface`, `text-fg-muted`, `border-line` …), never Tailwind's palette; see `../theme/README.md`.
- Buttons, text fields and choices only through the building blocks `Button`, `Input`, `Select` and `Textarea`
  (`../components/ui/README.md`): one height per size (36 px, 28 px), one disabled and one loading state.
- A page that throws while rendering shows `ErrorMessage` inside the frame (`../components/RouteError.tsx`).

## Sign-in and roles

- The sign-in state comes from `GET /api/v1/me/` (`../session.ts`, one TanStack query). DRF answers a missing
  session with 403, so 403 from `/api/v1/me/` means "signed out".
- Every page except `/login` sits inside `RequireSession` (`../components/SessionGuards.tsx`): without a session
  the browser goes to `/login?next=<address>` and comes back after signing in. `next` accepts only paths of
  this application (`safeNextPath`); `/admin/…` is opened as a page of its own.
- Every page also sits inside `RequireRole` with the role from `navigation.ts` (`read` for pages without an entry).
  A missing role shows "no permission" in the frame, without a redirect. This replacement is a page of its own
  (work order 091, `NoPermissionPage` in `../components/SessionGuards.tsx`): `usePageTitle` "No permission – 2x",
  the only `<h1>` (`AnimatedHeading`) and the notice below. `NoPermission` alone is the notice for a part of a page
  or an action, without heading and title.
- A 403 of any other API call makes the app ask `/api/v1/me/` again: 403 there means the session expired
  (to the sign-in page), 200 means only the permission is missing (`ErrorMessage` shows "no permission").
- Buttons that write are shown only to `manage`:

  ```tsx
  import { Button } from "../components/ui/Button.tsx";
  import { useRole } from "../session.ts";

  const { canManage } = useRole();
  return canManage ? <Button type="button">…</Button> : null;
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
  Below the search field a live region (`role="status"`) says how many devices the search shows, or that nothing
  matches; without a search it is empty.
- Tree layout (work order 083, E-65 point 4):
  - A row of a site, area or plant has its describing parts (kind, name, key, device count) on the left, wrapping
    on narrow screens, and the actions "Edit" and "New …" as icon buttons (pencil, plus; `Button` `ghost`, `sm`)
    on the right. Their `aria-label` names action and item ("Edit plant …") and is also the tooltip. With a fine
    pointer (mouse) the actions are transparent until the row is hovered or holds the focus; on touch screens they
    always show. The fade is a transition, so it stops with reduced motion.
  - The devices of a plant form one grid (rows are subgrids): class, name, key and IP address stand in the same
    columns on every row. The class shows as icon plus text from 640 px (`sm`); below that as icon with the class
    as tooltip and for screen readers, and key and address go to a second line under the name. From 1024 px (`lg`)
    the class, key and address columns have a least width (11rem, 8rem, 8rem), so the rows of different plants line
    up as well, as long as no value is longer.
  - Areas and plants with children have a fold button before the row (`aria-expanded`, `aria-controls` while
    open; "Contents of area …", "Devices of plant …"). Folded children are not rendered; the device count stays.
    `structure/collapse.ts` keeps the folded branches per browser in `localStorage` (`twox.structure.collapsed`,
    every access in `try/catch`; without a storage the tree starts unfolded). A search unfolds every hit without
    changing the stored choice; folding during a search lasts for that search text only, unfolding is stored.
    "New plant" and "New device" unfold their area or plant.
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
  and a download button. Managers upload new files there; the kind "configuration" is shown but cannot be chosen,
  because configurations are rejected until redaction arrives in M5 (E-42); the form says so.
- `DocumentPage.tsx` (`/documents/:documentId`) shows one file with all versions, newest first, each with a
  download button, the form for a new version (managers) and the change log of the file (`AuditTrail`, managers only,
  because the change log API is readable for managers only).
- Tables on the desktop (work order 079): version, date, size and user never wrap (`whitespace-nowrap`). The user
  stands as a detail line below the upload time ("Uploaded"), the checksum as a quiet detail line ("SHA-256 1a2b…",
  no disclosure triangle, full value as tooltip and on click) below the title or the file name. Download is an icon
  button (`DownloadIconLink`, 28 px, name in `aria-label` and tooltip); its column heading is for screen readers only.
  File names (`FileName`) wrap at word boundaries (`break-words`, never `break-all`) and are cut after two lines with
  the full name as tooltip; the text content stays the full name. The building blocks are in
  `../components/files/parts.tsx`. A scroll box around a table with screen-reader texts is `relative`, so those
  absolute texts do not widen the page on a phone.
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
  Known limit: a change of state found by polling is not announced to screen readers (no live region; work order 053).
  The same holds for `/ingest`.
- Downloads are plain links to `/api/v1/document-versions/<id>/download/`; the API answers with
  `Content-Disposition: attachment` and the session cookie goes along.
- Uploads go through the generated client (multipart/form-data) in `../components/files/upload.ts`, with a fetch of
  its own that keeps a copy of 400, 409 and 413 answers: field errors appear at their fields, 409 names the version
  with the same content, 413 the limit (read from the API's message), and the duplicates of a successful upload
  appear with links to the device and the file. There is no progress display (the client reports none).
- Both upload forms choose the file with `FileInput` (`../components/ui/FileInput.tsx`, work order 088): a button,
  the chosen name, dropping a file on the frame. "Upload" stays disabled with the hint "Choose a file first." until a
  file is chosen; after each submission the chooser is empty again. A submission without a file by other means still
  shows "Please choose a file." at the field and calls no API.
- File names, titles and user names are rendered as text, never through the interpolation of i18next.
- Tests fake the file API with `../components/files/testData.ts`. Under jsdom, Node's Request cannot read
  jsdom files, so tests use `textFile()` and `fakeUploadApi()`, which send forms as multipart text.

## Change log entries

- `../components/AuditTrail.tsx` shows the entries of `/api/v1/audit-log/` on `/audit` and on the file page. Time,
  user, action and object type never wrap.
- Changes (work order 079): known field names are translated (`field` in `audit.json`, the API name as tooltip;
  `auditFieldNames` lists them, taken from the logged models in `backend/twox/accounts/audit.py`); an unknown field
  shows its name as it came. Technical fields (`TECHNICAL_AUDIT_FIELDS`: id, storage key, checksum and the ids of other
  objects) are folded away under "Technical details" / "Technische Angaben", like the technical text of an ingest
  error. Runs of 32 or more hex digits are cut like the checksums of the file table, with the full value as tooltip.
- Nothing is lost: "Technical details" also holds the raw `changes` of the entry exactly as the API sent them, as JSON
  with one field per line (`rawJson()`), including the pairs that are empty on both sides and therefore not listed.

## Device list import

- `ImportPage.tsx` (`/import`, role `manage`) uploads the device list as CSV through the generated
  `devicesImportMutation` (`multipart/form-data`, CSRF header from `../api/client.ts`). The page describes the
  13 columns (`deviceListColumns`, the order of E-44) and the optional 14th column `device_class`
  (`deviceListOptionalColumn`, E-53) with its values (`deviceClasses` from `structure/deviceClass.ts`, which the
  device form uses for its choice as well; labels under `deviceClass` in `assets.json`).
- The CSV file is chosen or dropped with `FileInput` (work order 088); "Start dry run" stays disabled with the hint
  "Choose a file first." until there is one.
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
  `GET /api/v1/search/` (`searchOptions` of the generated client). `routes.tsx` loads it on demand with `lazyPage()`, like every page except sign-in and structure.
- The form has one field for a term, an identifier or a question (at most 500 characters) and a choice of device
  (`GET /api/v1/devices/`, grouped by plant; "All devices" first). Sending the form (Enter or the button) writes the
  trimmed text and the device into the browser address, `/search?q=…&device=…` (question 1 of work order 052): a
  search can be linked, reloaded and reached with Back. A device value that cannot be an id is ignored; a device that
  is not in the list is named by its id. The API drops the query part from its access log (work order 052).
- States: no search text (a hint, no request), loading, no hits, error (`ErrorMessage`), hits.
- `semantic` of the answer: `unavailable` shows the hint "Keyword search only – language model not reachable";
  `disabled` (AI features switched off, E-59) shows one calm line, no warning; `used` shows nothing.
- A hit (`search/SearchHitView.tsx`) shows the page ("p. 31", "pp. 31–32"; German "S. 31", "S. 31–32"), the heading
  path, how it was found (exact, keyword, meaning), the snippet and the places it is stored at: file (link to
  `/documents/:id`), version with its file name, "Older version" when `is_latest` is false, device (link to
  `/devices/:id`) and plant.
- Compact hits (work order 087): only the first place is shown. Further places sit behind a ghost button
  "+10 more devices" / "+10 weitere Geräte" (`aria-expanded`, `aria-controls` on the list of places), which opens
  and closes them; it says "places" / "Fundstellen" instead when one device holds the text more than once
  (`hiddenPlacesKind`). A hit with one place has no button.
- Each kind (exact, keyword, meaning) explains itself: the short name stays visible, the explanation is the
  `title` of the badge and follows the name as `sr-only` text ("Exact: An identifier from the search …"), in German
  and English (`matchKind.hint.*` in `locales/*/search.json`).
- The snippet is plain text. `search/snippet.ts` cuts it into pieces by the `highlights` of the API, which count
  Unicode code points: the snippet is split with `Array.from` first, so marks do not slip after an emoji or another
  character outside the BMP. The found places are `<mark>` elements with text inside; nothing is rendered as HTML.
  A mark has no side padding (`px-0`, `box-decoration-clone`, `MARK_CLASS`), so a mark inside a word such as
  "IP-Addresses" leaves no gaps.
- Tests fake the search API with `search/testData.ts` (test sentences only, devices of `structure/testData.ts`).

## Ingest overview

- `IngestPage.tsx` (`/ingest`, role `read`, entry "Ingestion" / "Einlesen" with the icon `ingest`) lists the ingest
  jobs of all devices through `GET /api/v1/ingest-jobs/` (`ingestJobsListOptions`), newest first, 50 per page with
  "previous" and "next" like `/audit`. `routes.tsx` loads it on demand with `lazyPage()`.
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
  React Flow (`@xyflow/react`). `routes.tsx` loads it on demand with `lazyPage()`, so React Flow is not part of the main bundle.
- It reads the same four lists as the structure page. `map/graph.ts` turns them into nodes and edges: sites, areas and
  plants as groups (parent nodes), devices inside their plant, and one network node per IPv4 /24 or IPv6 /64 that
  holds a device address. The only edges are the dashed "device is in network" lines. Nothing else is derived; links
  from configuration files come with M5/M7.
- The layout is a grid per group, computed from fixed node sizes; inputs are sorted first, so the same data gives the
  same positions. Moved nodes are not saved; a reload, or new data, restores the layout.
- A click or Enter on a device opens `/devices/:id`. Selected, focused and found devices are highlighted with their
  network line. The search (name, key, IP address) marks matches and fits the view to them. The network nodes can be
  hidden. The React Flow attribution link stays visible (the project asks to remove it only with a Pro subscription).
- Size and zoom (work order 080): the map takes the whole width of the page grid and reaches down to the bottom of the
  window (`useRestHeight`: window height minus the map's place in the page minus the 32 px padding of `main`, measured
  again on resize; at least 28rem as before, 70vh until measured). Fitting the view, on opening and with "Fit view", keeps the
  zoom between 0.6 and 1.25 (`FIT_VIEW_OPTIONS`), so the 12 px texts of the nodes never shrink below about 7 px; a
  larger structure is then reached by panning, the overview or zooming out by hand. The search still fits all its
  matches, at any zoom.
- The legend is a small box in the top right corner of the map (React Flow `Panel`, `role="note"`, named "Legend"):
  a sample of the dashed line with its meaning, and the network sizes (below 640 px for screen readers only, so the
  narrow map stays free). The sample is decorative; screen readers hear "Dashed line:" instead.
- A device node shows the icon of its class with the class as tooltip; the label of the node names the class too.
- Node components live in `map/nodes.tsx`; every text from the data is rendered as text. Under jsdom the tests stub
  `ResizeObserver`, `DOMMatrixReadOnly`, `offsetWidth`/`offsetHeight` and `getBBox` (`map/MapPage.test.tsx`).
