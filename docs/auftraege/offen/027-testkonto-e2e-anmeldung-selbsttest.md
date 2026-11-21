# Auftrag 027 – Testkonto in CI, Anmeldung im Browser-Test, Selbsttest nur für Angemeldete

Meilenstein: M1 · Freigabestufe: C · Status: offen

## Ziel

Der Selbsttest-Endpunkt ist nur noch für angemeldete Benutzer mit Rolle erreichbar (Vormerkung aus Auftrag 010 und `docs/STATUS.md`). Der Browser-Test meldet sich mit einem Testkonto an. Das Konto legt die CI mit einem wiederholbaren Befehl an, den alle späteren Aufträge wörtlich übernehmen.

## Umfang

- Backend:
  - `SelftestView` ohne `AllowAny` und ohne leere `authentication_classes`. Es gelten `SessionAuthentication` und die Standardklasse `CanRead` (025).
  - Docstring angepasst.
  - Tests in `backend/tests/config/test_selftest.py`: anonym 403, angemeldet ohne Rolle 403, mit Rolle `read` 200. Der Test `test_selftest_needs_no_credentials_and_rejects_writes` wird entsprechend ersetzt.
  - `backend/tests/config/test_api.py`: `/api/v1/selftest/` aus `OPEN_PATHS` entfernen.
- Testkonto:
  - `.env.example`: `TWOX_E2E_USERNAME=e2e-manager` und `TWOX_E2E_PASSWORD=dev-only-e2e-password`. Das sind reine Entwicklungswerte; das Kennwort erfüllt die Prüfer aus 016.
  - `deploy/compose/compose.web.yaml`: beide Variablen an den Dienst `e2e` durchreichen.
  - `.github/workflows/ci.yml`, Job `e2e`: nach „Start services and wait until healthy“ ein Schritt `Create test account` mit genau diesem Inhalt:
    ```
    set -a; . ./.env; set +a
    docker compose exec -T -e TWOX_ACCOUNT_PASSWORD=\"$TWOX_E2E_PASSWORD\" api python manage.py create_account \"$TWOX_E2E_USERNAME\" --role manage --update
    ```
    Durch `--update` (Auftrag 021) läuft der Schritt beliebig oft, auch ohne `down -v`.
  - `README.md`, Abschnitt „Browser test“: derselbe Schritt in derselben Form, mit Hinweis auf die Entwicklungswerte.
- Playwright:
  - Neu `web/e2e/fixtures.ts`, ein gemeinsamer Anmelde-Schritt über die API:
    - `/` aufrufen (setzt `csrftoken`).
    - `POST /_allauth/browser/v1/auth/login` mit `X-CSRFToken` und den Werten aus `TWOX_E2E_USERNAME` und `TWOX_E2E_PASSWORD`.
    - Das Sitzungs-Cookie landet im Browser-Kontext der Seite.
  - Dazu in derselben Datei die Hilfen für Testdaten:
    - `uniqueSuffix()`, eindeutig je Lauf.
    - Namen nach dem Muster `e2e-<art>-<suffix>`.
    - `testIp(n)` aus dem Dokumentationsbereich 192.0.2.0/24.
  - Alle vorhandenen Spezifikationen nutzen den Anmelde-Schritt: `selftest.spec.ts`, `i18n.spec.ts` (018) und `navigation.spec.ts` (023).
- Schema und Client neu erzeugen (Beschreibung und Sicherheitsangabe des Selbsttests ändern sich).

## Nicht-Ziele

- Anmeldeseite, Umleitung und Benutzeranzeige in der Oberfläche (030).
- OIDC, Zwei-Faktor, Kennwort ändern.
- Die übrige Doku in `README.md` und `docs/ARCHITECTURE.md` (Auftrag 038); hier nur der Abschnitt „Browser test“.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/config/selftest.py`, `backend/tests/config/test_selftest.py`, `backend/tests/config/test_api.py`
- `.env.example`, `deploy/compose/compose.web.yaml`, `.github/workflows/ci.yml` (Job `e2e`), `README.md` (Abschnitt „Browser test“)
- `web/e2e/` (neu `fixtures.ts`; `selftest.spec.ts`, `i18n.spec.ts`, `navigation.spec.ts`)
- `web/openapi/schema.yml`, `web/src/api/generated/**`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-027`, `W` für `docker compose -p twox-027-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18027` setzen.
- Unter Git Bash vor Befehlen mit `/out/…` `MSYS_NO_PATHCONV=1` setzen.
- Im Schritt „Create test account“ steht `D exec` für `docker compose exec`.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev web-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Anonym liefert der Selbsttest 403:
   ```
   D exec api python -c \"import urllib.request as u, urllib.error as e
   try: u.urlopen('http://localhost:8000/api/v1/selftest/')
   except e.HTTPError as x: print(x.code)\"
   ```
   gibt `403` aus.
3. Der Schritt „Create test account“ wie in `ci.yml` endet zweimal hintereinander mit Exit-Code 0.
4. Prüfungen und Typen:
   - `D run --rm backend-dev ruff check .` meldet `All checks passed!`.
   - `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0.
   - `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
5. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen. `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
6. `D run --rm -v \"$PWD/web/openapi:/out\" backend-dev python manage.py spectacular --file /out/schema.yml`, danach zeigt `git diff --exit-code -- web/openapi` keinen Unterschied.
7. Oberfläche:
   - `W --profile dev build web-dev`, `W run --rm web-dev npm ci`.
   - Dann `… npm run lint`, `… npm run typecheck`, `… npm run test`, `… npm run build` und `… npm run licenses`, je Exit-Code 0.
   - `W run --rm web-dev npm run api:generate`; danach zeigt `git diff --exit-code -- web/openapi web/src/api` keinen Unterschied.
8. Browser-Test wie im neuen `ci.yml`-Job:
   - `D --profile e2e pull e2e`
   - `D --profile dev run --rm web-dev npm ci`
   - Schritt „Create test account“
   - `D --profile e2e run --rm e2e` meldet alle Fälle bestanden, Exit-Code 0.
9. Kriterium 8 noch einmal ohne `down -v`: bleibt grün.
10. Geheimnissuche: `docker compose -f deploy/compose/compose.tools.yaml run --rm gitleaks-dir` endet mit Exit-Code 0.
11. Abräumen: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); 017, 018, 020, 021, 023 und 025 sind nach `main` zusammengeführt.

- Welle 4, parallel zu 026.
- **Reihenfolge beim Zusammenführen: nach 026.** Dieser Auftrag erzeugt Schema und Client auf dem neuen `main` neu; nichts wird von Hand gemischt.
- Einziger Auftrag der Welle mit `.env.example`, `compose.web.yaml`, `ci.yml`, `README.md` und `web/e2e/`.
- **Keine neue Abhängigkeit.**
- Stufe C wegen Rechten (Selbsttest) und Testkonto in der CI.
- Die Werte in `.env.example` sind Entwicklungswerte. Die Geheimnissuche muss grün bleiben; Namen wie bei den vorhandenen Einträgen (`dev-only-…`).
- Den Schritt „Create test account“ übernehmen die Aufträge 030 bis 037 wörtlich. Nicht ohne Rückfrage an die Leitstelle ändern.
- Testdaten-Regel für alle Browser-Tests (CLAUDE.md, Leitplanke 9): keine erfundenen Anlagen, die echt wirken; Namen über `uniqueSuffix()`; IP-Adressen nur aus 192.0.2.0/24.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine eigenen. Es gelten die Antworten zu Auftrag 016 (Frage 1), 020 und 025.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
