# Pages, routes and data fetching

## Addresses

All addresses are in `../routes.tsx` (react-router, data mode, no framework mode and no Node server).
Django serves `index.html` for every path except `api/`, `static/`, `admin/`, `_allauth/` and `accounts/`,
so each address can be opened directly or reloaded.

| Address | Page file | Built by work order |
| --- | --- | --- |
| `/` | `StructurePage.tsx` | 032 |
| `/devices/:deviceId` | `DevicePage.tsx` | 032 |
| `/documents/:documentId` | `DocumentPage.tsx` | 036 |
| `/import` | `ImportPage.tsx` | 035 |
| `/audit` | `AuditPage.tsx` | 033 |
| `/login` | `LoginPage.tsx` | 030 |
| `/selftest` | `SelftestPage.tsx` | (done, M0) |
| anything else | `../components/NotFound.tsx` | – |

A work order that builds a page replaces only its file here (and fills its own catalog, see `../locales/README.md`).
Routes, the frame (`../components/Layout.tsx`) and the navigation stay as they are.

## Frame and navigation

- `../components/Layout.tsx` draws the header (name, navigation, language switch, user area) around every page.
  The user area is empty until work order 030.
- `../navigation.ts` lists the navigation entries as data: path and key of the text in `nav.json`.
  Work order 030 adds the role per entry. Pages with a parameter and the sign-in page are not listed.
- Page headings are `<h2>`; the `<h1>` is the name in the header.
- A page that throws while rendering shows `ErrorMessage` inside the frame (`../components/RouteError.tsx`).

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
- `main.tsx` installs both once. Tests render the whole app with `../test/renderApp.tsx`.
- The self-test page keeps its own loading code from M0 (`../api/selftest.ts`).
