# Auftrag 032 – Oberfläche: Struktur und Geräte anzeigen, anlegen, bearbeiten

Meilenstein: M1 · Freigabestufe: B · Status: offen

## Ziel

In der Oberfläche sind Standorte, Bereiche, Anlagen und Geräte sichtbar. „Verwalten“ kann sie anlegen und bearbeiten, „Lesen“ nur ansehen.

## Umfang

- Seite Struktur (`/`, Platzhalter aus 023 ersetzen):
  - Baum oder verschachtelte Liste Standort > Bereich > Anlage > Gerät, mit Anzahl der Geräte.
  - Suche nach Name, Kennung oder IP-Adresse; bei der Größe genügt eine Suche im Browser.
- Geräteseite `/devices/:deviceId` (Platzhalter aus 023 ersetzen):
  - Alle Felder; die Kette als Brotkrumen.
  - Ein Bereich „Dateien“ als Platzhalter für 036, als eigene Komponente, die 036 ersetzt.
  - Lange Freitexte (Notizen, Adressherkunft) werden vollständig und mit Zeilenumbruch angezeigt.
- Formulare für Anlegen und Bearbeiten aller vier Ebenen:
  - React-19-Formulare, keine Formular-Bibliothek.
  - Feldfehler aus der 400-Antwort der API am Feld anzeigen.
  - Nach dem Speichern die Daten neu laden.
- Schaltflächen zum Anlegen und Bearbeiten nur für die Rolle `manage` (`useRole()` aus 030); die API prüft ohnehin.
- Texte in `assets.json` (seit 018 angelegt), Deutsch und Englisch, mit übersetzten Feldbezeichnungen.
- Vitest: Darstellung, Sichtbarkeit je Rolle, Feldfehler.
- Playwright, neue Datei `web/e2e/assets.spec.ts`:
  - Anmelden über `fixtures.ts` (027) als `manage`.
  - Standort, Bereich, Anlage und Gerät anlegen; Namen und Kennungen mit `uniqueSuffix()`, IP-Adresse aus `testIp()`.
  - Das Gerät bearbeiten (z. B. den Softwarestand); die Änderung ist sichtbar.
  - Eine ungültige IP zeigt den Feldfehler.

## Nicht-Ziele

- Löschen. Import (035). Dateien (036). Protokoll (033).
- Änderungen am Backend, an `routes.tsx`, `navigation.ts`, `Layout.tsx`, `package.json`.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/pages/` (Struktur- und Geräteseite, Formulare)
- `web/src/components/` (nur neue Komponenten)
- `web/src/locales/*/assets.json` und Tests
- neu: `web/e2e/assets.spec.ts`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-032`, `W` für `docker compose -p twox-032-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18032` setzen.

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
4. Kriterium 3 noch einmal ohne `down -v`: bleibt grün.
5. Abräumen: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); 026 und 030 sind nach `main` zusammengeführt.

- Welle 6, parallel zu 031 (Backend) und 033 (Protokollseite). Nur die eigenen Dateien. Ist eine Änderung an gemeinsamen Dateien unvermeidlich, vorher Rückfrage an die Leitstelle.
- **Keine neue Abhängigkeit.**
- Testdaten (CLAUDE.md, Leitplanke 9): keine erfundenen Anlagen, die echt wirken. Nur Namen nach dem Muster `e2e-<art>-<suffix>` und IP-Adressen aus 192.0.2.0/24, über die Hilfen in `web/e2e/fixtures.ts`. Kein Test verlässt sich auf Daten anderer Spezifikationen.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
