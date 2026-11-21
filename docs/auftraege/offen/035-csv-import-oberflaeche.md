# Auftrag 035 – Oberfläche: CSV-Import der Geräteliste

Meilenstein: M1 · Freigabestufe: B · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
