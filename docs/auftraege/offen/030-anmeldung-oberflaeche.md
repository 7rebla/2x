# Auftrag 030 – Anmeldung in der Oberfläche, Rollen in der Navigation, Admin über dieselbe Anmeldung

Meilenstein: M1 · Freigabestufe: C · Status: zur Prüfung

## Ziel

Benutzer melden sich in der Oberfläche an und ab. Die Oberfläche kennt Benutzer und Rolle und blendet Seiten aus, für die die Rolle fehlt. Wer keine Berechtigung hat, landet nicht in einer Anmelde-Schleife. Der Admin nutzt dieselbe Anmeldung mit derselben Ratenbegrenzung; einen zweiten, ungeschützten Anmeldeweg gibt es nicht mehr.

## Umfang

- Seite `/login` ersetzt den Platzhalter aus 023:
  - Benutzername, Kennwort, Fehlermeldung, Hinweis bei Ratenbegrenzung.
  - Aufruf der Browser-Schnittstelle von allauth (`/_allauth/browser/v1/auth/login`, `…/auth/session`) über eine kleine, typisierte Hülle in `web/src/api/auth.ts`; allauth steht nicht im OpenAPI-Schema.
  - Nach der Anmeldung zurück zur Seite aus `next`. Nur Pfade derselben Anwendung, keine fremden Adressen.
- Client-Konfiguration in `web/src/api/` (nicht im generierten Code):
  - Schreibende Anfragen senden `X-CSRFToken` aus dem Cookie `csrftoken`.
  - Alle Anfragen senden `Accept-Language` mit der gewählten Sprache.
- Anmeldezustand:
  - Beim Start `GET /api/v1/me/`.
  - Ohne Anmeldung leitet jede Seite außer `/login` nach `/login` um und kehrt danach zurück.
  - Antwortet eine Abfrage mit 403, wird `GET /api/v1/me/` erneut gefragt:
    - Ist auch das 403, ist die Sitzung abgelaufen; dann Umleitung zur Anmeldung.
    - Ist es 200, fehlt nur die Berechtigung; dann ein Hinweis „keine Berechtigung“, keine Umleitung, keine Abmeldung.
- Kopf (`Layout.tsx`): Benutzername, Rolle (übersetzt), „Abmelden“. Ein Konto ohne Rolle sieht einen Hinweis, dass ihm keine Rolle zugewiesen ist.
- `useRole()` für spätere Seiten: Schaltflächen zum Schreiben nur für `manage`.
- `web/src/navigation.ts`: je Eintrag eine Rollenangabe (z. B. `requires: \"manage\"`), von `Layout` ausgewertet.
  - `/import` verlangt `manage`.
  - `/audit` je nach Antwort zu Auftrag 028, Frage 3.
  - Die Seiten-Aufträge 033 und 035 müssen die Navigation dann nicht mehr ändern.
- Texte in `auth.json` (seit 018 angelegt), Deutsch und Englisch.
- Admin (Frage 3 zu Auftrag 016):
  - Das Anmeldeformular der Admin-Seite in `backend/twox/config/admin_site.py` leitet auf `/login?next=<Admin-Pfad>` um.
  - Test in `backend/tests/config/test_admin.py`: `/admin/login/` leitet um, ein POST an das alte Formular meldet niemanden an, und ein über allauth angemeldeter Superuser erreicht `/admin/`.
- Vitest:
  - Anmeldeformular und Fehleranzeige.
  - Der CSRF-Header wird gesetzt.
  - Umleitung ohne Anmeldung.
  - Keine Umleitung bei 403 mit gültiger Sitzung.
  - Navigation je Rolle; Konto ohne Rolle.
- Playwright, neue Datei `web/e2e/login.spec.ts` (Testkonto aus 027):
  - Ein falsches Kennwort zeigt eine Fehlermeldung.
  - Die Anmeldung über die Seite zeigt den Benutzernamen.
  - Abmelden führt zu `/login`.
  - `/selftest` ohne Anmeldung führt zu `/login` und nach der Anmeldung zurück.
  - Der Fall „Konto ohne Rolle“ wird nur mit Vitest geprüft; die CI legt nur ein Testkonto an.

## Nicht-Ziele

- OIDC, Zwei-Faktor, Kennwort ändern oder zurücksetzen (Frage 1).
- Benutzerverwaltung in der Oberfläche.
- Fachseiten (032, 033, 035, 036).

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/`: neu `pages/LoginPage.tsx` (ersetzt den Platzhalter), `api/auth.ts`, Client-Konfiguration und Anmeldezustand; `components/Layout.tsx`, `navigation.ts`, `locales/*/auth.json`; Tests
- neu: `web/e2e/login.spec.ts`
- `backend/twox/config/admin_site.py`, `backend/tests/config/test_admin.py`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-030`, `W` für `docker compose -p twox-030-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18030` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev web-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. `D exec api python -c \"import urllib.request as u; print(u.urlopen('http://localhost:8000/admin/login/').url)\"` gibt eine Adresse mit `/login?next=` aus.
3. Prüfungen und Typen:
   - `D run --rm backend-dev ruff check .` meldet `All checks passed!`.
   - `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0.
   - `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
4. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen. `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
5. Oberfläche:
   - `W --profile dev build web-dev`, `W run --rm web-dev npm ci`.
   - Dann `… npm run lint`, `… npm run typecheck`, `… npm run test`, `… npm run build` und `… npm run licenses`, je Exit-Code 0.
   - `W run --rm web-dev npm run api:generate`; danach zeigt `git diff --exit-code -- web/openapi web/src/api` keinen Unterschied.
6. Browser-Test wie in `ci.yml`, Job `e2e`:
   - `D --profile e2e pull e2e`
   - `D --profile dev run --rm web-dev npm ci`
   - Schritt „Create test account“ wie in `ci.yml`
   - `D --profile e2e run --rm e2e` meldet alle Fälle bestanden, darunter `login.spec.ts`, Exit-Code 0.
7. Abräumen: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

- **Nachtrag der Leitstelle (aus der Prüfung von 027):** `web/e2e/fixtures.ts` meldet heute jeden Test einzeln an; allauth erlaubt 30 Anmeldungen je Minute und IP. Stelle in diesem Auftrag auf eine Anmeldung je Worker um (`storageState`, z. B. über ein Setup-Projekt), damit die Tests aus 032–037 nicht sporadisch an der Grenze scheitern. Der Test mit falschem Kennwort darf das gemeinsame Testkonto nicht sperren (5 Fehlversuche je 5 Minuten und Konto): nimm dafür einen nicht existierenden Benutzernamen oder höchstens einen Fehlversuch.

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); 016, 020, 021, 023 und 027 sind nach `main` zusammengeführt; Antwort von a7 auf Auftrag 028, Frage 3 (Sichtbarkeit von `/audit`).

- Welle 5, parallel zu 028 und 029 (Backend).
- Einziger Auftrag der Welle mit `web/src/` und `web/e2e/`.
- Schema und Client ändern sich hier nicht.
- **Keine neue Abhängigkeit.**
- Stufe C wegen Anmeldung und Rechten.
- Hintergrund (DRF): Mit `SessionAuthentication` antwortet DRF auch bei fehlender Anmeldung mit 403, nicht 401. Deshalb die Gegenfrage an `me`.
- Testdaten-Regel aus 027 (`fixtures.ts`) beachten.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

1. **Eigenes Kennwort in M1 ändern können?**
   - (a) Nicht in M1: Superuser setzen Kennwörter im Admin oder mit `create_account --update`. Vorgemerkt für M6, bevor erste Tester Zugang haben.
   - (b) In M1 als eigener kleiner Auftrag nach diesem (Endpunkt der allauth-Browser-Schnittstelle zum Kennwortwechsel und eine Seite in der Oberfläche).
   - Empfehlung: (a). Die M1-Abnahme verlangt es nicht; spätestens mit Version 0.1 nötig.

Anmeldeverfahren und Admin: siehe Auftrag 016, Fragen 1 und 3, sowie Auftrag 020.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Kriterien 0–7 erfüllt; alle Läufe am 21.11.2026 im Container (Docker Engine 29.9.3, Compose v5.7.0). Keine offene Frage an a7. Keine neue Abhängigkeit.

### Was wurde gebaut?

**Backend (Admin):**
- `backend/twox/config/admin_site.py`: `TwoxAdminSite.login` ersetzt Djangos Anmeldeformular und meldet nie jemanden an.
  - Anonym (jede Methode, auch POST an das alte Formular): 302 auf `/login?next=<Admin-Pfad>`.
  - Angemeldeter Superuser: weiter zum Admin-Pfad.
  - Angemeldet ohne Zugang (z. B. nur `is_staff`): 403 statt Umleitung, sonst entstünde eine Anmelde-Schleife (`/admin/` → `/admin/login/` → `/login` → zurück).
  - `next` wird nur übernommen, wenn es ein Pfad dieses Hosts unter `/admin/` ist; sonst `/admin/`. `never_cache` und `login_not_required` wie bei Djangos Original.
- `backend/tests/config/test_admin.py`: 15 neue Fälle. `/admin/login/` leitet auf `/login?next=%2Fadmin%2F` um; ein Admin-Unterpfad landet über zwei Umleitungen dort; fremde und ungültige `next`-Werte (`https://…`, `//…`, `/api/…`, `/login`, `javascript:`, leer) werden zu `/admin/`; Admin-Pfad mit Query bleibt erhalten; POST mit richtigem Superuser-Kennwort an das alte Formular meldet niemanden an (mit und ohne CSRF-Prüfung); ein über `POST /_allauth/browser/v1/auth/login` angemeldeter Superuser erreicht `/admin/` (200); angemeldeter Superuser an `/admin/login/` geht weiter; angemeldet ohne Zugang → genau eine Umleitung, dann 403, Sitzung bleibt.

**Oberfläche (`web/src/`):**
- `api/client.ts` (neu, Client-Konfiguration): Interceptoren des erzeugten Clients. Schreibende Methoden senden `X-CSRFToken` aus dem Cookie `csrftoken`, alle Anfragen `Accept-Language` mit der gezeigten Sprache. Jede 403-Antwort (außer von `/api/v1/me/`) wird an Abonnenten gemeldet (`onForbidden`).
- `api/auth.ts` (neu): typisierte Hülle um allauth, `signIn` (`POST …/auth/login`) und `signOut` (`DELETE …/auth/session`), mit denselben Kopfzeilen. Ergebnis als Union: angemeldet (200, auch 409), falsche Daten (400 `username_password_mismatch`), Kontosperre (400 `too_many_login_attempts`), Ratenbegrenzung (429), sonstige 400, abgelaufene Seite (403 CSRF), anderer Status, keine Antwort. Abmelden gilt bei 401 (so antwortet allauth) als erfolgreich.
- `session.ts` (neu, Anmeldezustand): eine TanStack-Abfrage auf `GET /api/v1/me/`; 403 dort heißt „abgemeldet“ (Daten `null`). `watchForbidden` (in `App.tsx` eingehängt) fragt nach jeder 403 einer anderen Abfrage `me` erneut: 403 → abgemeldet → Umleitung zur Anmeldung; 200 → nur Hinweis. Dazu `useSession()`, `useRole()` (`role`, `canRead`, `canManage`), `hasRole()` („manage“ schließt „read“ ein), `safeNextPath()` (nur Pfade dieser Anwendung; `https://…`, `//…`, `/\…`, `/api/`, `/static/`, `/_allauth/`, `/accounts/` und `/login` werden zu `/`), `loginPathFor()`, `isServerPage()`.
- `components/SessionGuards.tsx` (neu): `RequireSession` (ohne Sitzung `<Navigate>` nach `/login?next=<Adresse>`; bei `/` ohne `next`), `RequireRole` und `NoPermission` (Hinweis „keine Berechtigung“, keine Umleitung, keine Abmeldung).
- `routes.tsx`: `/login` außerhalb, alle übrigen Seiten in `RequireSession`; jede Seite in `RequireRole` mit der Rolle aus `navigation.ts` (Seiten ohne Eintrag: `read`).
- `navigation.ts`: `requires` je Eintrag; `/` und `/selftest` `read`, `/import` und `/audit` `manage` (Frage 3 zu 028 und E-43: nur Verwalter lesen das Protokoll). `visibleNavigation(role)` und `requiredRole(path)`. Seiten-Aufträge 032–036 müssen hier nichts ändern.
- `components/Layout.tsx`: Navigation nur mit Sitzung und nur die Einträge der Rolle; Benutzerbereich über `components/UserMenu.tsx` (neu: Benutzername, übersetzte Rolle, „Abmelden“, Fehlermeldung bei gescheiterter Abmeldung). Konto ohne Rolle: Hinweis über der Seite, keine Navigation.
- `pages/LoginPage.tsx`: ersetzt den Platzhalter. Formular mit Benutzername und Kennwort (`autocomplete` gesetzt), eigene Fehlertexte je Ergebnis (auch beide Sperr-Fälle verständlich: Konto gesperrt bzw. zu viele Versuche von diesem Rechner), Kennwortfeld wird nach einem Fehler geleert. Nach der Anmeldung wird `me` neu geladen und zu `next` gewechselt; ein bereits angemeldeter Besucher von `/login` geht sofort weiter. `next` unter `/admin/` öffnet die Seite per Seitenladen (`browserLocation.ts`, neu, im Test ersetzbar).
- `components/ErrorMessage.tsx` und `pages/SelftestPage.tsx`: Eine 403 zeigt „keine Berechtigung“ statt „HTTP-Status 403“ (bei abgelaufener Sitzung erscheint die Seite gar nicht erst, weil zur Anmeldung umgeleitet wird).
- `locales/{de,en}/auth.json`: alle Texte der Anmeldung, Rollen, Hinweise.
- `main.tsx`, `test/renderApp.tsx`: `installClientConfig()`.
- `pages/README.md`: Abschnitt „Sign-in and roles“ mit Beispiel für `useRole()`.

**Vitest** (151 Fälle, davon neu bzw. neu gefasst): `api/client.test.ts` (CSRF-Cookie lesen; `X-CSRFToken` bei POST/PATCH/DELETE, nicht bei GET; `Accept-Language` folgt dem Sprachwechsel; 403-Meldung, nicht für `me`; allauth-Aufrufe mit CSRF und Sprache; Abbildung aller Antwortcodes), `pages/LoginPage.test.tsx` (Formular, Fehleranzeige je Fall auch auf Deutsch, leere Felder senden nichts, Rückkehr zu `next` mit Query, fremde `next`-Werte → `/`, Admin per Seitenladen, angemeldeter Besucher geht weiter), `session.test.tsx` (Umleitung ohne Anmeldung mit `next` für fünf Adressen; keine Umleitung bei 403 mit gültiger Sitzung, `me` zweimal gefragt, keine Abmeldung; abgelaufene Sitzung → Anmeldung; Navigation je Rolle; Leser auf `/import` und `/audit` → Hinweis; Konto ohne Rolle (de/en); Abmelden mit CSRF → `/login`; gescheitertes Abmelden; `useRole`, `hasRole`, `safeNextPath` mit 17 Fällen). `routes.test.tsx`, `App.test.tsx` und `errors.test.tsx` an die Anmeldung angepasst (Hilfe `test/fakeApi.ts`, neu).

**Playwright** (`web/e2e/`):
- `fixtures.ts` (Nachtrag der Leitstelle): Anmeldung einmal je Worker (`workerStorageState`, Worker-Fixture), jeder Test startet mit diesem `storageState`. Keine Dateien, kein Setup-Projekt nötig. Specs ohne Sitzung setzen `storageState: { cookies: [], origins: [] }`. Im Log eines Laufs: 1 Anmeldung des Workers + 4 aus `login.spec.ts` statt bisher 1 je Test.
- `login.spec.ts` (neu, ohne geteilte Sitzung): falsches Kennwort mit nicht existierendem Benutzernamen `e2e-nobody-<suffix>` (genau ein Fehlversuch, das Testkonto kann nicht gesperrt werden) zeigt die Meldung und setzt kein `sessionid`; Anmeldung über die Seite zeigt Benutzername und Rolle; Abmelden führt zu `/login` und beendet die Sitzung (danach führt `/selftest` wieder zur Anmeldung); `/selftest` ohne Anmeldung → `/login?next=%2Fselftest` → nach der Anmeldung zurück mit `pong`. Die Abmelde-Tests melden sich selbst an und berühren die geteilte Sitzung nicht.
- `fixtures.spec.ts`: öffnet zuerst `/` (die Seite startet jetzt leer) und prüft den Benutzernamen im Kopf.

### Wie wurde getestet?

`D` = `docker compose -p twox-030`, `W` = `docker compose -p twox-030-web -f deploy/compose/compose.web.yaml`; `.env` aus `.env.example` mit `TWOX_API_PORT=18030`. Die Testumgebung „2x“ und „twox-leit“ wurden nicht berührt.

| AK | Ergebnis |
| --- | --- |
| 0 | erfüllt: `docker version` (Server 29.9.3), `docker compose version` (v5.7.0), Exit 0 |
| 1 | erfüllt: Bau `migrate api worker backend-dev web-dev` und `up -d --wait` je Exit 0, alle Dienste healthy |
| 2 | erfüllt: `http://localhost:8000/login?next=%2Fadmin%2F` |
| 3 | erfüllt: `All checks passed!`; `103 files already formatted` (Exit 0); `Success: no issues found in 103 source files` |
| 4 | erfüllt: `725 passed, 4 deselected`, 0 fehlgeschlagen, 0 übersprungen; `pytest -m worker`: `4 passed` |
| 5 | erfüllt: `build web-dev`, `npm ci`, `lint`, `typecheck`, `test` (9 Dateien, 151 Fälle), `build` (`index-….js 439.05 kB`, gzip 137.77 kB), `licenses` (`License check passed.`), `api:generate` je Exit 0; danach `git diff --exit-code -- web/openapi web/src/api` ohne Unterschied |
| 6 | erfüllt: `pull e2e`, `npm ci`, „Create test account“ (`Created …`, beim zweiten Lauf `Updated …`) je Exit 0; `D --profile e2e run --rm e2e`: `12 passed`, darunter die vier Fälle aus `login.spec.ts`, Exit 0 (zweimal gelaufen, der zweite Lauf nach dem letzten Commit und Neubau) |
| 7 | erfüllt: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` Exit 0; danach kein Container und kein Volume mit `twox-030` |

Zusätzlich wie im CI-Job `backend`: `makemigrations --check --dry-run` (`No changes detected`), Lizenzprüfung Python (`License check passed.`), OpenAPI-Schema neu erzeugt ohne Unterschied. Geheimnissuche `gitleaks-dir`: `no leaks found`, Exit 0.

### Zweig und Arbeitsverzeichnis

Zweig `worktree-agent-a92bb24ee2559d8d2`, Arbeitsverzeichnis `.claude/worktrees/agent-a92bb24ee2559d8d2`. Nicht gepusht, nicht zusammengeführt.

### Abweichungen und Hinweise

1. **Mehr Dateien als genannt, alle in `web/src/`:** `session.ts`, `browserLocation.ts`, `components/SessionGuards.tsx`, `components/UserMenu.tsx`, `test/fakeApi.ts` (neu); `App.tsx`, `components/ErrorMessage.tsx`, `pages/SelftestPage.tsx` (403 als „keine Berechtigung“), `pages/README.md`. In `web/e2e/` zusätzlich `fixtures.spec.ts` angepasst.
2. **Admin für Angemeldete ohne Zugang: 403** statt Djangos Formular mit Hinweis. Eine Umleitung auf `/login` hätte eine Schleife erzeugt (die Seite schickt Angemeldete sofort zu `next` zurück).
3. **Abmelden führt zu `/login` ohne `next`.** Eine abgelaufene Sitzung führt dagegen zu `/login?next=<Seite>`.
4. **Konto ohne Rolle** sieht keine Navigation und auf jeder Seite „keine Berechtigung“ (alle Seiten verlangen mindestens `read`, wie die API nach E-40); dazu der Hinweis über der Seite.
5. **Fehlertexte der Anmeldung** stammen aus `auth.json` je Fehlercode von allauth; die (englische) Meldung von allauth selbst wird nicht gezeigt.
6. **Nicht geändert:** `README.md` (Abschnitt „Browser test“ stimmt weiterhin; der Hinweis auf die Anmeldung je Worker könnte mit 038 dazukommen). Der Admin bietet Superusern weiter `/admin/password_change/` an; das ist kein Anmeldeweg und entspricht Frage 1 (a) („Superuser setzen Kennwörter im Admin“).
7. Die Sitzungsabfrage gilt 60 Sekunden als frisch. Eine abgelaufene Sitzung fällt bei der nächsten 403 einer Abfrage auf, sonst beim nächsten Fensterfokus nach Ablauf der 60 Sekunden; ein reiner Seitenwechsel fragt `me` nicht neu.
