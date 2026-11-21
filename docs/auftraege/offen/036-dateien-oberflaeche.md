# Auftrag 036 – Oberfläche: Dateien je Gerät hochladen, Versionen, herunterladen

Meilenstein: M1 · Freigabestufe: B · Status: offen

## Ziel

Auf der Geräteseite sieht man die Dateien des Geräts mit ihren Versionen und kann sie herunterladen. Als „Verwalten“ lädt man neue Dateien und neue Versionen hoch. Dubletten und abgewiesene Uploads werden verständlich gemeldet.

## Umfang

- Bereich „Dateien“ auf der Geräteseite (Platzhalter-Komponente aus 032 ersetzen):
  - Liste mit Titel, Art und neuester Version (Nummer, Datum, Größe, Benutzer).
  - Die Prüfsumme gekürzt, beim Aufklappen vollständig.
- Dateiseite `/documents/:documentId` (Platzhalter aus 023 ersetzen):
  - Alle Versionen mit Download-Link je Version.
  - Das Protokoll des Dokuments über `AuditTrail` aus 033.
- Hochladen (nur `manage`):
  - Neue Datei (Datei, Titel, Art) und neue Version.
  - 409 zeigt „Inhalt gleicht Version N“.
  - Der Dubletten-Hinweis aus der Antwort nennt die anderen Fundstellen mit Link.
  - 413 zeigt die Obergrenze.
  - Die Ablehnung von Konfigurationsdateien (Antwort zu Auftrag 024, Frage 2) wird verständlich angezeigt; das Formular weist darauf hin.
- Texte in `files.json` (seit 018 angelegt), Deutsch und Englisch; Größen und Daten über `Intl`.
- Vitest: Liste, Upload-Ablauf mit nachgebildetem Client, Anzeige von 409, Dubletten und 413, Sichtbarkeit je Rolle.
- Playwright, neue Datei `web/e2e/files.spec.ts`:
  - Anmelden über `fixtures.ts` als `manage`.
  - Über die API Standort, Bereich, Anlage und Gerät mit `uniqueSuffix()` anlegen.
  - Eine im Test erzeugte Textdatei mit Inhalt je Lauf hochladen (Version 1), dann geänderten Inhalt als Version 2; beide Versionen sind sichtbar.
  - Version 1 herunterladen und den Inhalt prüfen.
  - Dieselbe Datei erneut hochladen zeigt die 409-Meldung.

## Nicht-Ziele

- Vorschau von Dateien im Browser, Löschen, Änderungsvergleich (M8), Einlese-Status (M2). Fortschrittsanzeige ist kein Muss.
- Änderungen am Backend, an `routes.tsx`, `navigation.ts`, `Layout.tsx`, `package.json`.

## Betroffene Bereiche (Ordner, Dateien)

- Komponenten unter `web/src/components/files/`, die Dateien-Komponente der Geräteseite, `web/src/pages/DocumentPage.tsx`
- `web/src/locales/*/files.json`, Tests
- neu: `web/e2e/files.spec.ts`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-036`, `W` für `docker compose -p twox-036-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18036` setzen.

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

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); 029, 032 und 033 sind nach `main` zusammengeführt.

- Welle 7, parallel zu 034 und 035. Nur die eigenen Dateien.
- **Keine neue Abhängigkeit.** Upload über den generierten Client (`multipart`); meldet er keinen Fortschritt, dann ohne Fortschrittsanzeige.
- Der Download läuft über die API mit Sitzung; es gibt keinen öffentlichen Medien-Pfad.
- Testdaten (CLAUDE.md, Leitplanke 9): keine erfundenen Anlagen, die echt wirken. Nur Namen nach dem Muster `e2e-<art>-<suffix>` und IP-Adressen aus 192.0.2.0/24, über `web/e2e/fixtures.ts`. Keine Herstellerunterlagen als Testdatei.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
