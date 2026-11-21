# Auftrag 037 – Nachweis der M1-Abnahme

Meilenstein: M1 · Freigabestufe: B · Status: offen

## Ziel

Ein automatischer Test und eine kurze Anleitung belegen die Abnahme von M1 (`docs/ROADMAP.md`): „Geräteliste der Testfabrik per CSV geladen (testfactory/layout/devices.csv); eine Datei mit zwei Versionen; das Protokoll zeigt die Änderungen“. a7 kann denselben Ablauf von Hand im Browser nachvollziehen.

## Umfang

- Playwright, neue Datei `web/e2e/m1-acceptance.spec.ts` (läuft im CI-Job `e2e`):
  1. Anmelden über die Anmeldeseite mit dem Testkonto (Rolle `manage`).
  2. Auf `/import` die Datei `/testfactory/layout/devices.csv` hochladen. Dafür bekommt der Dienst `e2e` das Verzeichnis `../../testfactory/layout` schreibgeschützt eingebunden.
     - Auf frischer Datenbank zeigt der Probelauf 1 Standort, 3 Bereiche, 10 Anlagen und 13 Geräte als neu; dann „Übernehmen“.
     - Sind die Daten schon da, zeigt er 0 angelegt und 0 geändert.
     - Der Test erkennt den Fall vorab über die API und prüft beide Wege.
  3. Die Struktur zeigt die drei Bereiche (Fertigungslinie, Roboterzelle, Netzübergang), das Gerät `dps-plc` mit IP `192.168.0.90` und die Anlage `aps-charging` ohne Gerät mit Notiz.
  4. Beim Gerät `dps-plc` eine im Test erzeugte Datei hochladen (Version 1), dann geänderten Inhalt als Version 2. Der Inhalt ist je Lauf eindeutig. Beide Versionen sind mit unterschiedlicher Prüfsumme sichtbar.
  5. Das Protokoll zeigt:
     - die Einträge des Imports mit Benutzer (auf frischer Datenbank);
     - die beiden Versionen des Dokuments mit Benutzer und Zeitpunkt.
  6. Eine Wiederholung des Imports derselben Datei meldet 0 angelegt und 0 geändert.
- Backend-Test `backend/tests/acceptance/test_m1.py` mit demselben Ablauf über die API: Import der echten Datei aus `/testfactory/layout` (eingebunden seit 031), zwei Versionen, Protokolleinträge mit Akteur. Damit läuft der Nachweis auch ohne Browser.
- Die Schrittfolge für die Abnahme von Hand steht im Kurzbericht dieses Auftrags. README und `docs/` zieht Auftrag 038 nach.

## Nicht-Ziele

- Neue Funktionen. Fehler, die dabei auffallen, werden im Kurzbericht genannt und nicht hier behoben; Ausnahme sind Kleinigkeiten in Tests.
- Änderungen an `testfactory/`.

## Betroffene Bereiche (Ordner, Dateien)

- neu: `web/e2e/m1-acceptance.spec.ts`
- neu: `backend/tests/acceptance/` (`__init__.py`, `test_m1.py`)
- `deploy/compose/compose.web.yaml`: Dienst `e2e`, zusätzliches Volume `../../testfactory/layout:/testfactory/layout:ro`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-037`, `W` für `docker compose -p twox-037-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18037` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev web-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Backend:
   - `D run --rm backend-dev pytest tests/acceptance -v` endet mit Exit-Code 0.
   - `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen.
   - `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
3. Prüfungen und Typen:
   - `D run --rm backend-dev ruff check .` meldet `All checks passed!`.
   - `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0.
   - `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
4. Browser-Test wie in `ci.yml`, Job `e2e`:
   - `D --profile e2e pull e2e`
   - `D --profile dev run --rm web-dev npm ci`
   - Schritt „Create test account“ wie in `ci.yml`
   - `D --profile e2e run --rm e2e` meldet alle Fälle bestanden, darunter `m1-acceptance.spec.ts`, Exit-Code 0.
5. Ein zweiter Lauf von Kriterium 4 ohne `down -v`, mit allen Schritten, bleibt grün.
6. Oberfläche:
   - `W --profile dev build web-dev`, `W run --rm web-dev npm ci`.
   - Dann `W run --rm web-dev npm run lint` und `… npm run typecheck`, je Exit-Code 0.
7. Abräumen: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); 031, 032, 033, 034, 035 und 036 sind nach `main` zusammengeführt.

- Welle 8, parallel zu 038 (Doku). Einziger Auftrag der Welle mit Tests und `compose.web.yaml`.
- **Keine neue Abhängigkeit.**
- Abnahmefall aus Auftrag 106: genau `testfactory/layout/devices.csv`, unverändert. Erwartete Zahlen laut Datei: 14 Datenzeilen, 13 Geräte, 10 Anlagen, 3 Bereiche, 1 Standort.
- Die hochgeladene Datei wird im Test erzeugt: keine Herstellerunterlage, nichts aus `testfactory/extern/`.
- Die Abnahme selbst nimmt a7 vor (Stufe C); dieser Auftrag liefert nur den Nachweis.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
