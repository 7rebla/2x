# Auftrag 027 – Testkonto in CI, Anmeldung im Browser-Test, Selbsttest nur für Angemeldete

Meilenstein: M1 · Freigabestufe: C · Status: zur Prüfung

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

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

Keine eigenen. Es gelten die Antworten zu Auftrag 016 (Frage 1), 020 und 025.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Was wurde gebaut?**

- Backend: `SelftestView` ohne `AllowAny` und ohne leere `authentication_classes`; es gelten `SessionAuthentication` und `CanRead`. Docstring neu (steht auch im Schema und im Client).
- Tests: `test_selftest.py` ruft den Selbsttest als Benutzer mit Rolle `read` auf. `test_selftest_needs_no_credentials_and_rejects_writes` ist ersetzt durch `test_selftest_needs_a_signed_in_user_with_role` (anonym 403, ohne Rolle 403, `read` 200; eine abgewiesene Anfrage stellt keine Aufgabe in die Warteschlange) und `test_selftest_rejects_writes` (405). Der Schematest erwartet jetzt `security: [{cookieAuth: []}]`.
- `test_api.py`: `/api/v1/selftest/` aus `OPEN_PATHS` entfernt. Neu `test_every_exception_is_still_needed`: jeder Eintrag in `OPEN_PATHS` (anonym) und `ROLELESS_PATHS` (ohne Rolle) muss wirklich offen sein. Damit fällt ein veralteter Ausnahme-Eintrag künftig auf (Hinweis aus 025).
- Testkonto: `.env.example` mit `TWOX_E2E_USERNAME=e2e-manager` und `TWOX_E2E_PASSWORD=dev-only-e2e-password`. `compose.web.yaml` reicht beide an `e2e` durch (`${…:-}`, damit `W` ohne `.env` nicht warnt). `ci.yml`, Job `e2e`: Schritt `Create test account` nach „Start services and wait until healthy“. `README.md`, Abschnitt „Browser test“: derselbe Schritt mit Hinweis auf die Entwicklungswerte.
- Playwright: neu `web/e2e/fixtures.ts` mit `signIn(page)`, einem erweiterten `test` (jede Seite startet angemeldet) und den Hilfen `uniqueSuffix()`, `testName(art)` (`e2e-<art>-<suffix>`) und `testIp(n)` (192.0.2.1 bis 192.0.2.254). Die Anmeldung: `/` öffnen (setzt `csrftoken`), dann `POST /_allauth/browser/v1/auth/login` mit `X-CSRFToken` per `fetch` in der Seite; geprüft werden Status 200 und das Cookie `sessionid` im Browser-Kontext. Bei einem Fehler nennt die Meldung Status und Antwort von allauth (z. B. 400 `too_many_login_attempts`), nie das Kennwort. `selftest.spec.ts`, `i18n.spec.ts` und `navigation.spec.ts` importieren `test` und `expect` aus `./fixtures`. Neu `web/e2e/fixtures.spec.ts`: prüft über `/api/v1/me/`, dass die Seite als Testkonto mit Rolle `manage` angemeldet ist, sowie die drei Hilfen.
- Schema und Client neu erzeugt (Beschreibung und `security` des Selbsttests).

**Wie wurde getestet?** (Compose-Projekte `twox-027` und `twox-027-web`, `TWOX_API_PORT=18027`)

| Kriterium | Ergebnis |
| --- | --- |
| 0 `docker version`, `docker compose version` | Exit 0 (Compose 5.7.0) |
| 1 Build und `up -d --wait` | Exit 0, alle Dienste healthy |
| 2 Selbsttest anonym | `403` |
| 3 „Create test account“ zweimal | Exit 0 („Created …“, dann „Updated …“). Gegenprobe: ohne die Variable auf der Host-Seite bricht der Befehl mit „No password“ ab, `-e` ohne Wert nimmt den Wert also wirklich aus der Umgebung des Aufrufs |
| 4 ruff check / ruff format --check / mypy | `All checks passed!` / Exit 0 / `Success: no issues found in 96 source files` |
| 5 pytest / pytest -m worker | 487 passed, 4 deselected, 0 übersprungen / 4 passed |
| 6 Schema neu erzeugt | nach dem Commit kein Unterschied |
| 7 web-dev: npm ci, lint, typecheck, test, build, licenses, api:generate | je Exit 0; nach dem Commit kein Unterschied in `web/openapi` und `web/src/api` |
| 8 Browser-Test (pull, npm ci, Testkonto, e2e) | `8 passed`, Exit 0 |
| 9 dasselbe ohne `down -v` | `8 passed`, Exit 0 |
| 10 `gitleaks-dir` | `no leaks found`, Exit 0 |
| 11 Abräumen beider Projekte mit `down -v` | Exit 0 |

Zusätzlich aus dem CI-Job `backend`: `makemigrations --check --dry-run` („No changes detected“) und Lizenzprüfung Python („License check passed.“). Die YAML-Syntax von `ci.yml` ist mit PyYAML im Container geprüft; der Schritt wird wörtlich so geladen wie oben.

**Testkennwort in CI – Wahl und Begründung:** Erkennbarer Testwert aus `.env.example` (`dev-only-e2e-password`), kein Geheimnis des Repositorys und kein im Lauf erzeugter Wert.
- Das Konto lebt nur in der Wegwerf-Datenbank des CI-Laufs; die API ist dort nur auf 127.0.0.1 des Runners veröffentlicht.
- Der Wert ist ohnehin öffentlich und als Entwicklungswert erkennbar (`dev-only-…`, wie die übrigen Einträge); die Geheimnissuche bleibt grün.
- Er gilt lokal und in CI gleich, ohne Sonderweg; ein erzeugtes Kennwort hätte den vorgegebenen Schritt geändert, den 030 bis 037 wörtlich übernehmen.
- Im Log erscheint er nicht: Der Schritt gibt nichts aus außer „Updated/Created account 'e2e-manager' …“, GitHub zeigt nur den Skripttext mit `"$TWOX_E2E_PASSWORD"`, nicht den Wert, und `docker compose` bekommt nur den Variablennamen.

**Zweig und Arbeitsverzeichnis:** Zweig `worktree-agent-ae8b0022753c35ce0`, Arbeitsverzeichnis `.claude/worktrees/agent-ae8b0022753c35ce0`.

**Abweichungen**

1. **Schritt „Create test account“ nicht wörtlich wie im Auftrag.** Der Auftrag schreibt `-e TWOX_ACCOUNT_PASSWORD="$TWOX_E2E_PASSWORD"`; damit stünde der Wert in den Argumenten von `docker compose` (Prozessliste). Nach dem Hinweis aus 021 (`docs/STATUS.md`) und der Vorgabe der Leitstelle steht dort nur der Variablenname:
   ```
   set -a; . ./.env; set +a
   TWOX_ACCOUNT_PASSWORD="$TWOX_E2E_PASSWORD" docker compose exec -T -e TWOX_ACCOUNT_PASSWORD api python manage.py create_account "$TWOX_E2E_USERNAME" --role manage --update
   ```
   Diese Form übernehmen 030 bis 037; die Leitstelle sollte sie in deren Auftragstexten angleichen.
2. **Anmeldung per `fetch` in der Seite statt über Playwrights Request-Client.** `page.request` läuft in Node und kennt die Abbildung `localhost` → `api` nicht (die gilt nur in Chromium, `playwright.config.ts`); in CI liefe die Anmeldung damit ins Leere. Ablauf und Endpunkt sind wie vorgegeben.
3. **Zusätzlich** `web/e2e/fixtures.spec.ts` und der Test `test_every_exception_is_still_needed` (beide im genannten Bereich), damit die Änderung selbst getestet ist.
4. `gitleaks-git` lässt sich im Arbeitsverzeichnis nicht ausführen (`/repo is not a readable Git repository`: Die `.git`-Datei eines Worktrees zeigt auf einen Pfad, den der Container nicht sieht). Nicht gefordert; `gitleaks-dir` ist grün.

**Hinweise**

- Jede Spezifikation meldet sich je Test einmal an. allauth begrenzt Anmeldungen auf 30 je Minute und IP-Adresse; bei deutlich mehr Browser-Tests (030–037) ggf. auf eine Anmeldung je Worker mit `storageState` umstellen.
- Der Job `testfactory` ist nicht berührt und wurde nicht ausgeführt.
