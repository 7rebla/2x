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
| `/ask` | `AnswerPage.tsx` (no navigation entry before work order 134, role `read`) | on demand (`lazyPage()`) | 132 |
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
  - From 768 to 1279 px the icon above a short text (metadata size `text-meta`, 13 px, on a 16 px line, E-65 point 5; `nav:short.*` in
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
  one column, two from 1024 px (`lg`) and three from 1280 px (`xl`). The sign-in page (work order 086, E-65 point 7)
  is a centred card inside the grid (`mx-auto max-w-sm`, `bg-surface`, border `line`, `p-6`) with the brand mark
  (48 px) and the name above it; that name stands still (only the header's name types) and is `aria-hidden`,
  since it repeats the header's link; heading, introduction, error and form sit in the card, fields and the
  primary button have the full width of the card and the same height (36 px). The language switch stays in the
  header. `../../e2e/login.spec.ts` measures the card at 375, 1024 and 1600 px.
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
- Answers (M3) do not go through TanStack Query: `POST /api/v1/answers/` is a stream of server-sent events.
  `../api/answers.ts` (`streamAnswer`) asks through the generated `answer()` and checks every event
  (`answer/events.ts`); `answer/useAnswerStream.ts` keeps the state (`idle`, `streaming`, `done`, `error`) for the
  page. Rules: a question is never sent again on its own (no retry, not even after a network error); failures are
  `ApiError`s like everywhere else (a 403 goes to `onForbidden`, 409 `ai_disabled` is its own cause `ai-disabled`);
  `cancel()` and leaving the page abort the stream. The streamed text is provisional until `done` replaces it
  with the checked text (`verified`), and it stays a plain string. Only whether answers are available
  (`GET /api/v1/answers/status/`) is a query: `answersStatusQueryOptions()`.

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
- Breadcrumb (work order 089): `../components/Breadcrumb.tsx` draws the trail of the device page and of the file page.
  `Breadcrumb` is a named `<nav>` ("Location of the device", "Location of the file") with an ordered list; every
  level has the icon of its kind (decorative) and its name as text, levels are separated by "›" from the style sheet,
  the trail wraps between levels on narrow screens. The last level is the page itself (`aria-current="page"`, bold,
  no link). `useDeviceCrumbs(device)` gives the levels Structure (link to `/`), site, area, plant with its key and the
  device with the icon of its class (a link to its page wherever it is not the last level).
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
- Above the title the file page shows where the file sits (work order 089): Structure › site › area › plant › device ›
  file, the same trail as the device page with the device as a link and the file title as the current level. Until the
  device is loaded, or if it cannot be, the trail is Structure › "Device 12" (link) › file.
- Tables on the desktop (work order 079): version, date, size and user never wrap (`whitespace-nowrap`). The user
  stands as a detail line below the upload time ("Uploaded"), the checksum as a quiet detail line ("SHA-256 1a2b…",
  no disclosure triangle, full value as tooltip and on click) below the title or the file name. Download is an icon
  button (`DownloadIconLink`, 28 px, name in `aria-label` and tooltip); its column heading is for screen readers only.
  File names (`FileName`) wrap at word boundaries (`break-words`, never `break-all`) and are cut after two lines with
  the full name as tooltip; the text content stays the full name. The building blocks are in
  `../components/files/parts.tsx`. A scroll box around a table with screen-reader texts is `relative`, so those
  absolute texts do not widen the page on a phone.
- Narrow screens (work order 081, E-65 (2)): below 768 px the four data tables (files of a device, versions of a file,
  ingest jobs, change log) are stacked cards, a list with one heading per card, through `ResponsiveTable`
  (`../components/ui/README.md`, "Data tables and cards"). A file card: the title as heading (`h3`), the download
  button next to it, the ingest state below, then kind, version, upload time with user and size as pairs, the checksum
  at the end ("No version" in place of the pairs from version on). A version card: "Version N" as heading (`h3`),
  download, ingest state with message and button, then upload time with user, size and file name, the checksum at the
  end. Nothing scrolls sideways at 375 px (`../../e2e/tables-narrow.spec.ts`).
- Ingestion state (work order 053): the building blocks are in `../components/files/IngestStatus.tsx` and are meant to
  be reused (055). `IngestStatusBadge` shows the newest job of a version (field `ingest`): queued, ingesting (with the
  step), ingested (pages and sections), error, skipped, or not ingested; `compact` leaves out step and counts (device
  page). `IngestError` shows the translated message per kind of error (one per `error_code`, a general text for
  unknown kinds) and folds the technical `error_detail` away (rendered as text only). For a job of a version that was
  converted only in part (`partly_converted`) it shows the hint "Converted only in part" in its own paragraph
  (`warning`, with icon), whatever the state: alone for a done job and for a queued or running embedding job, below the
  error message for a failed embedding (work order 089). `IngestRetryButton` (managers, documents only,
  hidden while a job is queued or running) calls `POST /api/v1/document-versions/<id>/ingest/`; a 409 appears as
  "already being ingested", a 400 as "configurations are not ingested". The file page and the device page poll every
  5 s (`INGEST_POLL_INTERVAL_MS`) while a shown version has a queued or running job, and not otherwise. Skipped and
  queued are neutral, not errors; with the AI features off (E-59) missing embeddings are not shown at all.
  Known limit: a change of state found by polling is not announced to screen readers (no live region; work order 053).
  The same holds for `/ingest`, where only a changed number of jobs is announced (result count, work order 089).
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
- Above the entries the result count says how many entries the filter found, of all pages ("120 entries found" /
  "120 Einträge gefunden"), or "No entries found." in place of the list (`ResultCount`, see "Result count").
- Below 768 px every entry is a card (work order 081): the object with its id as heading (`h2` on `/audit`; the file
  page passes `cardHeadingLevel={3}` below its section heading), the action below it, then time, user and object type
  as pairs and the changes over the full width of the card, with "Technical details" folded away as in the table.
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
- A hit (`search/SearchHitView.tsx`, with the building blocks of `../components/sources/`, shared with the answer page) shows the page ("p. 31", "pp. 31–32"; German "S. 31", "S. 31–32"), the heading
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
- The snippet is plain text. `../components/sources/snippet.ts` cuts it into pieces by the `highlights` of the API, which count
  Unicode code points: the snippet is split with `Array.from` first, so marks do not slip after an emoji or another
  character outside the BMP. The found places are `<mark>` elements with text inside; nothing is rendered as HTML.
  A mark has no side padding (`px-0`, `box-decoration-clone`, `MARK_CLASS`), so a mark inside a word such as
  "IP-Addresses" leaves no gaps.
- Tests fake the search API with `search/testData.ts` (test sentences only, devices of `structure/testData.ts`).

## Ask

- `AnswerPage.tsx` (`/ask`, role `read`, work order 132) asks a question about the ingested documents through
  `answer/useAnswerStream.ts` (work order 131) and shows the answer with its sources. It has no navigation entry yet
  (work order 134); `routes.tsx` loads it on demand with `lazyPage()`. Texts are in the namespace `answers`; the
  sources reuse the keys of `search` for page, version and places.
- Form (`answer/AnswerForm.tsx`): a text area "Question" (at most 500 characters after trimming, counted by code point
  like the server; above that a hint, `aria-invalid` and the button disabled), "Ask" and, while an answer streams,
  "Cancel". The button sends, Ctrl+Enter (Cmd+Enter) as well; Enter alone starts a new line. `?q=` only fills the
  field, nothing is ever sent on its own (D14 (i)); the question goes into the body of the POST, never into the
  address, and nothing is stored (D7). The form builds the whole request (`answerRequest()` with an `AnswerScope`),
  so the limit to devices and plants (work order 133) is added there.
- Availability (`answer/answerView.ts`, `availabilityOf()`): `GET /api/v1/answers/status/` with `enabled=false`,
  or a 409 `ai_disabled` of the stream, shows a calm hint "AI features switched off" with a link to the search;
  `chat_model_configured=false`, `available=false` or a 503 `chat_not_configured` shows "Answers are not available
  at the moment". In both cases field and button are disabled (D10 (a), E-59). If the status cannot be read, the
  form stays usable and the server decides.
- Status region: one `role="status"` line with the changes of state only ("Searching for sources…", "Writing the
  answer…", "Done", "Cancelled"), never every piece of text. No focus changes on a change of state.
- The answer (`answer/AnswerCard.tsx`) is an `article` named "Answer". While it streams it has `aria-busy="true"`,
  no `aria-live` and no typing animation, and its numbers are plain text. After `done` the checked text replaces the
  pieces (D9). The text is rendered as text only (no HTML, no Markdown, no links of its own, never through i18next).
  `answer/answerText.ts` cuts it into text and source numbers (`[2]`, `[2, 3]`, `[2; 3]`, as the citation check of the
  server reads them). A number becomes a link to `#source-n` only if `cited` of `done` holds it and the source is
  evidence; its name is "Source 2: <title>, page 14" ("pages 3–4"; a Markdown source names its headings instead of
  the page). A click focuses the source card (`tabIndex={-1}`) without changing the address. `removed_sentences` above
  0 adds the line "Statements without evidence were removed." (D8 (c)), without the removed text.
- Sources (`answer/SourceList.tsx`): an `ol` named "Sources" with the sources the answer cites, in the order of their
  numbers; sources that were given to the model but not cited are left out (they back no statement). A card shows
  number, page or pages, heading path, the snippet of the server (already cut to 300 characters) and the places
  (`../components/sources/`, `toSearchLocation()` of `answer/events.ts`). A source without page and without heading
  path is no evidence: no link, and in the list the mark "Place without a page".
- End states, each with icon and text: no evidence (icon `noEvidence`, the fixed sentence of the catalog in the
  shown language whatever the server sent, no sources, a link to the search with the question, which enters the
  address only on that click); contradiction (icon `contradiction`, a hint, and every cited source marked with a
  border in `warning` and the text "Contradicting place": the server reports a contradiction only with at least two
  cited sources); errors with `role="alert"` (`ErrorMessage` for API errors, a fixed text per code for an `error`
  event and for a stream that broke off; the `detail` of an `error` event is not shown).
- Tests: `AnswerPage.test.tsx` drives the stream with `fakeEventStream()` of `../test/fakeApi.ts` and the events of
  `answer/testData.ts`; `../../e2e/answer-page.spec.ts` checks the page without a chat model in German and English.

## Ingest overview

- `IngestPage.tsx` (`/ingest`, role `read`, entry "Ingestion" / "Einlesen" with the icon `ingest`) lists the ingest
  jobs of all devices through `GET /api/v1/ingest-jobs/` (`ingestJobsListOptions`), newest first, 50 per page with
  "previous" and "next" like `/audit`. `routes.tsx` loads it on demand with `lazyPage()`.
- Filters: status, device and the switch "Also show older attempts" / "Auch ältere Versuche zeigen", all in the address
  (`/ingest?status=…&device=…&older=1`) and applied at once. Without a status the page asks for `failed`, `running` and
  `queued` (what needs attention); one state can be chosen, and `all` sends no status, so ingested and skipped jobs
  show as well. An unknown status means the default, a device value that cannot be an id means all devices, a device
  that is not in the list is named by its id. A new filter starts on page 1.
- Between the filters and the list the result count says how many jobs the filter found, of all pages ("120 jobs
  found" / "120 Aufträge gefunden"), or in place of the list that nothing is open (default view) or that no job
  matches (`ResultCount`, see "Result count"). The pagination below the list keeps "Page 1 of 3".
- Newest job only (work order 064): every job is one attempt (E-55). Without the switch the page sends `latest=true`,
  so the API lists only the newest job of each version (the job of the field `ingest`, embedding jobs included) and
  applies status and device to those. A failed attempt that a later one has ingested is therefore not "open" any
  more. With `?older=1` the page sends no `latest` and lists every attempt.
- A row shows the device (link, key), the file (link to `/documents/:id`) with version and file name, the status with
  its step and the page and section counts (`IngestStatusBadge`), the translated message with the technical text to
  unfold (`IngestError`), the times (created, finished) and, for `manage` only, who started the job ("System" for
  none; the API sends `null` to `read`, E-57). All three building blocks come from
  `../components/files/IngestStatus.tsx` (work order 053); `error_detail` and every name are rendered as text.
- Below 768 px every job is a card (work order 081, `ResponsiveTable`): the file (link) as heading (`h2`), status,
  message and button below it, then device, version with file name, times and (managers) "Started by" as pairs.
- "Ingest again" (`IngestRetryButton`) stands on every row of a manager whose job is not queued or running and is the
  newest job of its version. A row with `is_latest` false (only with older attempts shown) says "Older attempt" and
  has no button, wherever the newer job is listed; the API decides, not the order of the page.
- While a listed job is queued or running, the page asks again every 5 seconds (`INGEST_POLL_INTERVAL_MS`) and says
  so; otherwise it does not poll. With the AI features switched off (E-59) no job has the step "embed".
- Tests fake the list (with `latest` and `is_latest`) and `POST …/ingest/` inside `IngestPage.test.tsx`;
  `../../e2e/ingest.spec.ts` uploads a plain-text file, which the format check skips without a converter, and checks
  the switch with answers of its own (`page.route`).

## Result count

Work order 089 (finding Ü12 of the UI analysis). `../components/ResultCount.tsx` is the shared building block for the
number of entries of a filtered list; the change log (`AuditTrail`, so also on `/audit`) and `/ingest` use it. The
structure search keeps its own region of the same kind (work order 083).

```tsx
const [count, reportCount] = useResultCount(filterKey); // in the part that stays
<ResultCount count={count} text={(n) => t("resultCount", { count: n })} empty={t("empty")}
  testId="audit-result-count" countTestId="audit-total" emptyTestId="audit-empty" />
<ListPages key={filterKey} filterKey={filterKey} reportCount={reportCount} />
// inside ListPages, after its query:
useReportCount(filterKey, query.data?.count, reportCount);
```

- **A polite live region:** `role="status"` (polite by itself), with the number in small secondary text
  ("120 entries found", plural forms `resultCount_one`/`_other` in the catalog of the page) or, for none, the text for
  an empty list in secondary text of the normal size; that text stands in place of the list, there is no second one.
- **The region stays in place.** Screen readers announce only changes inside a region that already exists, so the
  region lives outside the part that a new filter mounts afresh (`key={filterKey}`). `useResultCount` keeps the
  number the list part reports with `useReportCount`; while a new filter loads, or after an error, the region is empty
  (`count` is null), and the new number is announced when it arrives. Turning pages keeps the number.
- **No noise:** an unchanged number (a list that is polled, the same filter applied again) changes nothing in the page
  and is not read again. A filter that changes with every key press must report its number only once the list for the
  finished input has loaded, never per key; the filters of `/audit` (applied with a button) and `/ingest` (choices)
  do not change per key.
- Tests: `../components/ResultCount.test.tsx`, "result count" in `../components/AuditTrail.test.tsx` and in
  `IngestPage.test.tsx`, `../../e2e/audit.spec.ts` and `../../e2e/ingest.spec.ts`.

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
  zoom between 0.6 and 1.25 (`FIT_VIEW_OPTIONS`), so the 13 px metadata of the nodes never shrink below about 8 px (the 12 px labels in capitals about 7 px); a
  larger structure is then reached by panning, the overview or zooming out by hand. The search still fits all its
  matches, at any zoom.
- The legend is a small box in the top right corner of the map (React Flow `Panel`, `role="note"`, named "Legend"):
  a sample of the dashed line with its meaning, and the network sizes (below 640 px for screen readers only, so the
  narrow map stays free). The sample is decorative; screen readers hear "Dashed line:" instead.
- A device node shows the icon of its class with the class as tooltip; the label of the node names the class too.
- Node components live in `map/nodes.tsx`; every text from the data is rendered as text. Under jsdom the tests stub
  `ResizeObserver`, `DOMMatrixReadOnly`, `offsetWidth`/`offsetHeight` and `getBBox` (`map/MapPage.test.tsx`).
