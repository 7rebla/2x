# Auftrag 053 – Oberfläche: Einlese-Status auf Datei- und Geräteseite

Meilenstein: M2 · Freigabestufe: B · Status: offen

## Ziel

In der Oberfläche ist je Dateiversion sichtbar, ob sie eingelesen ist: in der Warteschlange, läuft, fertig, gescheitert oder übersprungen. Fehler erscheinen mit verständlicher Meldung; Verwalter können das Einlesen erneut anstoßen. Das erfüllt „Fehler sind sichtbar“ der Abnahme M2 und „Statusanzeige, neuer Versuch“ aus Startunterlage 4.

## Umfang

- **Dateiseite** (`web/src/pages/DocumentPage.tsx`, `web/src/components/files/`):
  - Je Version ein Status-Abzeichen: „In Warteschlange“, „Wird eingelesen“ (mit Schritt), „Eingelesen“ (Seiten- und Abschnittszahl), „Fehler“, „Übersprungen“.
  - Bei Fehler oder Überspringen die übersetzte Meldung zur Fehlerart, der technische Text aufklappbar.
  - Schaltfläche „Erneut einlesen“ nur für `manage`, nur ohne laufenden Auftrag; ruft `POST /api/v1/document-versions/{id}/ingest/` über den erzeugten Client; 409 wird als Meldung angezeigt.
  - Solange ein Auftrag `queued` oder `running` ist, fragt die Seite alle 5 Sekunden neu ab (TanStack Query `refetchInterval`), sonst nicht.
- **Geräteseite** (`web/src/components/DeviceFiles.tsx`): kleines Abzeichen für die neueste Version jeder Datei.
- Bausteine `IngestStatusBadge` und `IngestError` als eigene Komponenten in `web/src/components/files/IngestStatus.tsx`, damit 055 sie wiederverwendet.
- Texte in `web/src/locales/de/files.json` und `en/files.json`: eine Meldung je Fehlerart aus 042, dazu ein Text für unbekannte Fehlerarten.
- **Tests:**
  - Vitest: alle Zustände, Schaltfläche je Rolle (`manager` und `reader` aus `test/fakeApi.ts`), 409, Abfragen nur bei laufendem Auftrag, unbekannte Fehlerart, `error_detail` nur als Text.
  - Playwright `web/e2e/ingest-status.spec.ts` (als `e2e-manager`):
    - Eine im Test erzeugte `.txt`-Datei hochladen: erscheint als „Übersprungen“ mit Begründung (Formatprüfung aus 049, ohne Docling).
    - Eine im Test erzeugte kleine Markdown-Datei hochladen: zeigt einen der Zustände „In Warteschlange“, „Wird eingelesen“ oder „Fehler“ (in der CI fehlt Docling).
    - Zustand „Fehler“ mit Schaltfläche: Antwort über `page.route` mit einer selbst geschriebenen Antwort hergestellt, nicht durch Warten auf die Wiederholungen.

## Nicht-Ziele

- Keine Übersicht aller Aufträge (055), keine Suchseite (054).
- Keine Änderung an API und erzeugtem Client.
- Keine Änderung an `web/src/test/fakeApi.ts` (054 läuft gleichzeitig); Testdaten in `web/src/components/files/testData.ts`.
- Kein Zusammenlegen der Feldfehler-Hilfen (bekannte M1-Grenze).

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/pages/DocumentPage.tsx`, `web/src/pages/DocumentPage.test.tsx`
- neu: `web/src/components/files/IngestStatus.tsx`, `web/src/components/files/IngestStatus.test.tsx`; `web/src/components/files/testData.ts`
- `web/src/components/DeviceFiles.tsx`, `web/src/components/DeviceFiles.test.tsx`
- `web/src/locales/de/files.json`, `web/src/locales/en/files.json`
- neu: `web/e2e/ingest-status.spec.ts`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-053`, `W` für `docker compose -p twox-053-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18053` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. Oberfläche wie im CI-Job `web`: `W --profile dev build web-dev` und `W run --rm web-dev npm ci`, danach `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build` und `npm run licenses`, je über `W run --rm web-dev …`, mit Exit-Code 0. Vite meldet keine Warnung zur Bündelgröße über 500 kB; die Größe des Hauptbündels steht im Kurzbericht.
2. `W run --rm web-dev npm run api:generate`, danach `git diff --exit-code -- web/openapi web/src/api` ohne Unterschied.
3. Browser-Test wie im CI-Job `e2e`: `D --profile dev build migrate api worker web-dev`, `D --profile e2e pull e2e`, `D --profile dev run --rm web-dev npm ci`, `D up -d --wait --wait-timeout 300 db valkey worker api`; dann der Schritt „Create test account“ aus `ci.yml` wörtlich, nur mit `D` statt `docker compose` (Kennwort nur über den Variablennamen `TWOX_ACCOUNT_PASSWORD`); dann `D --profile e2e run --rm e2e`: alle Fälle bestanden, darunter `ingest-status.spec.ts`, Exit-Code 0.
4. Ein zweiter Lauf von Kriterium 3 ohne `down -v` bleibt grün.
5. Lokal, mit Docling und Modell: Eine PDF-Datei aus `testdata/klein/` hochladen. Die Dateiseite zeigt ohne Neuladen nacheinander „In Warteschlange“ oder „Wird eingelesen“ und dann „Eingelesen“ mit Seitenzahl. Beschreibung im Kurzbericht.
6. Abräumen: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: 051 ist nach `main` zusammengeführt (Feld `ingest` und Endpunkte im erzeugten Client).

- Welle 7, parallel zu 052 und danach zu 054.
- **Keine neue Abhängigkeit.**
- Texte aus der API (`error_detail`) nur als Text darstellen, nie als HTML.
- Bezeichnungen in beiden Sprachen; Englisch ist der Schlüsselkatalog (TypeScript prüft die Schlüssel).
- In der CI läuft kein Docling. Kein Test wartet auf `done` oder auf das Ende der Wiederholungen.
- Die CI hat nur das Testkonto `e2e-manager` (Rolle `manage`); Verhalten der Rolle `read` deshalb in Vitest.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
