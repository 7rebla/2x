# Auftrag 030 – Anmeldung in der Oberfläche, Rollen in der Navigation, Admin über dieselbe Anmeldung

Meilenstein: M1 · Freigabestufe: C · Status: offen

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

1. **Eigenes Kennwort in M1 ändern können?**
   - (a) Nicht in M1: Superuser setzen Kennwörter im Admin oder mit `create_account --update`. Vorgemerkt für M6, bevor erste Tester Zugang haben.
   - (b) In M1 als eigener kleiner Auftrag nach diesem (Endpunkt der allauth-Browser-Schnittstelle zum Kennwortwechsel und eine Seite in der Oberfläche).
   - Empfehlung: (a). Die M1-Abnahme verlangt es nicht; spätestens mit Version 0.1 nötig.

Anmeldeverfahren und Admin: siehe Auftrag 016, Fragen 1 und 3, sowie Auftrag 020.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
