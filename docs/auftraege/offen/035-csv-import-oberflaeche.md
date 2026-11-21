# Auftrag 035 – Oberfläche: CSV-Import der Geräteliste

Meilenstein: M1 · Freigabestufe: B · Status: zur Prüfung

## Ziel

„Verwalten“ lädt eine Geräteliste als CSV hoch und sieht im Probelauf, was angelegt, geändert oder fehlerhaft wäre. Danach übernimmt er sie.

## Umfang

- Seite `/import` (Platzhalter aus 023 ersetzen), nur für die Rolle `manage`. Andere sehen einen Hinweis statt des Formulars; den Navigationseintrag blendet seit 030 `navigation.ts` aus.
- Schritt 1: Datei wählen → Probelauf (`dry_run=true`) über `POST /api/v1/imports/devices/` (generierter Client, `multipart`, CSRF-Header aus 030).
- Schritt 2: Bericht:
  - Zähler je Ebene (angelegt, geändert, unverändert).
  - Fehler mit Zeile, Spalte und Meldung; die Meldung kommt übersetzt vom Backend (034).
  - 413 zeigt die Obergrenze.
- Schritt 3: „Übernehmen“ nur ohne Fehler → zweiter Aufruf mit `dry_run=false`; danach Bericht und Link zur Struktur.
- Kurze Beschreibung des erwarteten Formats (13 Spalten) auf der Seite.
- Texte in `import.json` (seit 018 angelegt), Deutsch und Englisch.
- Vitest: Ablauf Probelauf → Übernehmen, Fehleranzeige, Sichtbarkeit je Rolle.
- Playwright, neue Datei `web/e2e/import.spec.ts`:
  - Anmelden über `fixtures.ts` als `manage`.
  - Eine im Test erzeugte kleine CSV mit zwei Geräten hochladen. Alle Werte sind eindeutig je Lauf: Standort `e2e-site-<suffix>`, Anlage `e2e-plant-<suffix>`, Geräte `e2e-device-<suffix>-1` und `-2`, IP-Adressen aus `testIp()`.
  - Der Probelauf zeigt 2 angelegte Geräte; nach „Übernehmen“ sind die Geräte in der Struktur sichtbar.
  - Eine CSV mit ungültiger IP zeigt den Fehler mit Zeilennummer.

## Nicht-Ziele

- Änderungen am Backend. Fortschrittsanzeige.
- Import der Testfabrik-Datei im Browser-Test; das macht die Abnahme (037).
- Änderungen an `routes.tsx`, `navigation.ts`, `Layout.tsx`, `package.json`.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/pages/ImportPage.tsx`, ggf. neue Komponenten unter `web/src/components/`, `web/src/locales/*/import.json`, Tests
- neu: `web/e2e/import.spec.ts`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-035`, `W` für `docker compose -p twox-035-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18035` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. Oberfläche:
   - `W --profile dev build web-dev`, `W run --rm web-dev npm ci`.
   - Dann `… npm run lint`, `… npm run typecheck`, `… npm run test`, `… npm run build` und `… npm run licenses`, je Exit-Code 0.
2. `W run --rm web-dev npm run api:generate`, danach zeigt `git diff --exit-code -- web/openapi web/src/api` keinen Unterschied.
3. Browser-Test wie in `ci.yml`, Job `e2e`:
   - `D --profile dev build migrate api worker web-dev`
   - `D --profile e2e pull e2e`
   - `D --profile dev run --rm web-dev npm ci`
   - `D up -d --wait --wait-timeout 300 db valkey worker api`
   - Schritt „Create test account“ wie in `ci.yml`
   - `D --profile e2e run --rm e2e` meldet alle Fälle bestanden, Exit-Code 0.
4. Kriterium 3 noch einmal ohne `down -v`: bleibt grün; insbesondere zeigt der Probelauf wieder 2 angelegte Geräte.
5. Abräumen: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); 030 und 031 sind nach `main` zusammengeführt.

- Welle 7, parallel zu 034 (Backend) und 036 (Dateiseite). Nur die eigenen Dateien.
- **Keine neue Abhängigkeit.**
- Testdaten (CLAUDE.md, Leitplanke 9): keine erfundenen Anlagen, die echt wirken. Nur Namen nach dem Muster `e2e-<art>-<suffix>` und IP-Adressen aus dem Dokumentationsbereich 192.0.2.0/24, über `web/e2e/fixtures.ts`.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Kriterien 0–5 erfüllt; Läufe am 22.11.2026 im Container (Docker Engine 29.9.3, Compose v5.7.0). Keine neue Abhängigkeit, keine offene Frage an a7.

### Was wurde gebaut?

- `web/src/pages/ImportPage.tsx` (`/import`, ersetzt den Platzhalter): Beschreibung des Formats (13 Spalten als Konstante `deviceListColumns` in der Reihenfolge nach E-44, UTF-8/Komma, Abgleich über `plant_id`/`device_id`, nie löschen, Anlagenzeile ohne `device_id`, alles oder nichts). Dateiauswahl → „Probelauf starten“ (`dry_run=true`) über `devicesImportMutation` des erzeugten Clients (multipart, CSRF-Kopf aus `api/client.ts`). „Übernehmen“ erscheint nur nach einem Probelauf ohne Fehler und sendet dieselbe Datei mit `dry_run=false`; danach Bericht, `reloadAfterSave` und Link „Zur Struktur“. Eine andere Datei verwirft den Bericht. 400 zeigt die Meldungen der API (über `save()` aus `structure/save.ts`), 413 einen eigenen Hinweis plus die Meldung der API mit der Obergrenze, alles andere `ErrorMessage`.
- `web/src/components/ImportReportView.tsx` (neu): Zusammenfassung (Probelauf/gespeichert/Fehlerzahl, Plural), Tabelle je Ebene mit angelegt/geändert/unverändert, bei Fehlern stattdessen Tabelle Zeile/Spalte/Meldung („ganze Datei“ bzw. „–“ bei `null`). Werte und Meldungen nur als Text.
- `web/src/locales/{de,en}/import.json`: alle Texte, gleiche Schlüssel.
- `web/src/pages/README.md`: Abschnitt „Device list import“.
- Vitest `web/src/pages/ImportPage.test.tsx` (12 Fälle): Formatbeschreibung und gesperrter Knopf ohne Datei; Probelauf → Zähler → Übernehmen (zwei POST, `dry_run` `true`/`false`, CSRF-Kopf, multipart, dieselbe Datei), Link zur Struktur; Fehleranzeige mit Zeile/Spalte/Meldung, Markup in der Meldung bleibt Text, kein „Übernehmen“; Einzahl; Fehler beim Übernehmen; Dateiwechsel; 413; 400; 500; Deutsch; Rolle `read` sieht den Hinweis und sendet nichts; Rolle `manage` sieht das Formular.
- Playwright `web/e2e/import.spec.ts` (2 Fälle): eigene CSV mit `e2e-site-…`, `e2e-area-…`, `e2e-plant-…`, `e2e-device-…-1`/`-2`, IPs aus `testIp()`; Probelauf zeigt 2 angelegte Geräte (und je 1 Standort/Bereich/Anlage), Struktur danach noch leer für diesen Standort, „Übernehmen“, beide Geräte in der Struktur unter der Anlage, erneuter Probelauf zeigt 2 unverändert. Zweiter Fall: ungültige IP `192.0.2.256` in der zweiten Gerätezeile → genau ein Fehler in Zeile 3, Spalte `ip_address`, kein „Übernehmen“, nichts gespeichert. Keine Konsolenfehler.

### Wie wurde getestet?

`D` = `docker compose -p twox-035`, `W` = `docker compose -p twox-035-web -f deploy/compose/compose.web.yaml`; `.env` aus `.env.example` (ohne BOM) mit `TWOX_API_PORT=18035`. Die Umgebungen „2x“ und „twox-leit“ wurden nicht berührt.

| AK | Ergebnis |
| --- | --- |
| 0 | erfüllt: `docker version` (Server 29.9.3), `docker compose version` (v5.7.0), Exit 0 |
| 1 | erfüllt: `W --profile dev build web-dev`, `npm ci`; `lint`, `typecheck` ohne Meldung; `test`: 16 Dateien, 269 Fälle bestanden; `build`: `index-….js 489.46 kB` (gzip 149.75 kB); `licenses`: „License check passed.“ – je Exit 0 |
| 2 | erfüllt: `npm run api:generate` Exit 0; `git diff --exit-code -- web/openapi web/src/api` Exit 0, `git status --porcelain --untracked-files=all` dort leer |
| 3 | erfüllt: Bau, `pull e2e`, `npm ci`, `up -d --wait` (alle gesund), „Create test account“ wie in `ci.yml` („Created account 'e2e-manager' …“), `D --profile e2e run --rm e2e`: „17 passed“, Exit 0 |
| 4 | erfüllt: ohne `down -v` erneut `up --wait`, „Create test account“ („Updated …“), e2e: „17 passed“, Exit 0; der Probelauf zeigte wieder 2 angelegte Geräte (Test prüft das) |
| 5 | erfüllt: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` Exit 0; danach kein Container und kein Volume mit `twox-035` |

„Create test account“ lief in PowerShell: Werte aus `.env` gelesen, Kennwort nur als Umgebungsvariable `TWOX_ACCOUNT_PASSWORD` und an `docker compose exec -T -e TWOX_ACCOUNT_PASSWORD` nur als Variablenname übergeben.

### Zweig und Arbeitsverzeichnis

Zweig `worktree-agent-ab771ef1b216c0f3d`, Arbeitsverzeichnis `.claude/worktrees/agent-ab771ef1b216c0f3d`. Nicht gepusht, nicht zusammengeführt.

### Abweichungen und Hinweise

1. **`web/src/routes.test.tsx` geändert** (nicht im Bereich genannt, aber nötig): Der Fall „%s shows the page %s“ erwartete für `/import` den Platzhalter. `/import` ist aus der Liste genommen und hat einen eigenen Fall („/import shows the import page“). 036 ändert dieselbe Liste (Eintrag `/documents/42`) – beim Zusammenführen ist ein kleiner Konflikt in diesem Block wahrscheinlich; beide Einträge verlassen die Liste.
2. **`web/src/pages/README.md`** um einen Abschnitt am Ende ergänzt; 036 hängt dort vermutlich ebenfalls an (Konflikt am Dateiende möglich, beide Abschnitte behalten).
3. **Knopfname:** „Übernehmen“ / „Apply“ (nach dem Auftrag; die Leitstelle nannte „Speichern“).
4. **413:** Die Obergrenze steht in der Meldung der API (übersetzt mit 034); die Seite zeigt dazu einen eigenen Satz. Die Seite kennt die Grenze nicht selbst und prüft die Größe nicht vorab.
5. **Vitest und multipart:** Unter jsdom sendet Nodes fetch eine jsdom-`File` ohne Inhalt (im Browser kein Problem, der Playwright-Test lädt echt hoch). Der Test prüft deshalb die an `FormData.append` übergebene Datei (Identität) und liest `dry_run` aus dem multipart-Rumpf. Keine Änderung an gemeinsamen Testhilfen.
6. **Rolle:** Die Sichtbarkeit regelt weiter `RequireRole` aus 030 (Hinweis „keine Berechtigung“); die Seite prüft die Rolle nicht zusätzlich.
7. `routes.tsx`, `navigation.ts`, `Layout.tsx`, `package.json`, `api/errors.ts`, Schema und erzeugter Client unverändert.