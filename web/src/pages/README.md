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
  The user area shows the signed-in user, the role and "Sign out" (`../components/UserMenu.tsx`).
  An account without a role sees a hint above the page.
- `../navigation.ts` lists the navigation entries as data: path, key of the text in `nav.json` and the role
  that may see the entry (`requires`). `Layout` shows only the entries the user's role allows;
  `/import` and `/audit` need `manage`, the others `read`. Pages with a parameter and the sign-in page are not listed.
- Page headings are `<h2>`; the `<h1>` is the name in the header.
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
