# Auftrag 037 – Nachweis der M1-Abnahme

Meilenstein: M1 · Freigabestufe: B · Status: zur Prüfung

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

**Was wurde gebaut?**

- `web/e2e/m1-acceptance.spec.ts`: ein Browser-Test in sechs Schritten (`test.step`).
  1. Anmelden über die Anmeldeseite: `/import` ohne Sitzung führt nach `/login?next=%2Fimport`, danach zurück auf `/import` mit Rolle „Manage“. Der Test nutzt bewusst nicht die gemeinsame Sitzung aus `fixtures.ts`.
  2. Import von `/testfactory/layout/devices.csv` über `/import` mit Probelauf und „Übernehmen“. Vorab prüft der Test über `GET /api/v1/devices/`, ob `dps-plc` schon da ist.
     - Frische Datenbank: Angelegt 1/3/10/13 und Geändert 0, im Probelauf und nach dem Speichern.
     - Liste schon geladen: Angelegt 0, Geändert 0, Unverändert 1/3/10/13.
  3. Struktur, Suche „Testfabrik“:
     - die Bereiche Fertigungslinie, Netzübergang und Roboterzelle, insgesamt 13 Geräte;
     - `dps-plc` mit `192.168.0.90`;
     - `aps-charging` mit „0 devices“ und Notiz. Die Strukturseite zeigt Anlagennotizen nicht an; der Test liest die Notiz im Formular „Edit plant“ und bricht dann ab.
  4. Über den Link in der Struktur zu `dps-plc`. Dort eine im Test erzeugte Textdatei als Version 1 hochladen, auf der Dateiseite geänderten Inhalt als Version 2. Titel und Inhalt sind je Lauf eindeutig. Geprüft werden:
     - die Versionen 2 und 1 mit Benutzer;
     - die volle Prüfsumme (im Test mit `crypto.subtle` berechnet, beide verschieden) und die Kurzform.
  5. Protokoll unter `/audit`, gefiltert nach Objektart und Benutzer:
     - Nur auf frischer Datenbank: die Einträge des Imports mit „Created“, Benutzer und Zeitpunkt. Das sind der Standort, die drei Bereiche, `aps-charging` und alle 13 Geräte; bei `dps-plc` zusätzlich `ip_address: (empty) → 192.168.0.90`.
     - Immer: „File version“ mit `<Titel> v2` über `<Titel> v1`, je „Created“, Benutzer und Zeitpunkt (Attribut `datetime`).
  6. Erneuter Probelauf derselben Datei: Angelegt 0, Geändert 0, Unverändert 1/3/10/13.

  Die Konsole muss ab der Anmeldung fehlerfrei sein. Davor ist das 403 des Konto-Endpunkts ohne Sitzung erwartet.
- `backend/tests/acceptance/` (`__init__.py`, `test_m1.py`): derselbe Ablauf über die API mit der echten Datei aus `/testfactory/layout`, in vier Tests.
  - Import: Probelauf, Speichern, Struktur mit Bereichen, IP und Notiz.
  - Protokoll des Imports: Anzahl „create“ je Ebene mit Akteur `manage`.
  - Wiederholung: Probelauf und Speichern unverändert, keine neuen Protokolleinträge.
  - Datei mit zwei Versionen: Prüfsummen und Protokoll von `files.document` und `files.documentversion` mit Akteur, Zeitpunkt, `object_id` und `sha256`.
- `deploy/compose/compose.web.yaml`: Der Dienst `e2e` bindet `../../testfactory/layout:/testfactory/layout:ro` ein.

**Wie wurde getestet?** Projekte `twox-037` und `twox-037-web`, `TWOX_API_PORT=18037`.

| Kriterium | Ergebnis |
| --- | --- |
| 0 | `docker version` und `docker compose version`: Exit-Code 0 (Engine 29.9.3, Compose 5.7.0) |
| 1 | Build und `up -d --wait`: Exit-Code 0 |
| 2 | `pytest tests/acceptance -v`: 4 bestanden. `pytest`: 1097 bestanden, 4 abgewählt (worker), 0 fehlgeschlagen, 0 übersprungen. `pytest -m worker`: 4 bestanden |
| 3 | `ruff check`: „All checks passed!“; `ruff format --check`: Exit-Code 0; `mypy .`: „Success: no issues found in 134 source files“ |
| 4 | Nach `down -v` auf frischer Datenbank: pull, `npm ci`, „Create test account“, e2e. 19 von 19 bestanden, darunter `m1-acceptance.spec.ts`. Weg „frische Datenbank“ |
| 5 | Zweiter Lauf ohne `down -v`, alle Schritte (pull, `npm ci`, Testkonto mit „Updated account“, e2e): 19 von 19 bestanden. Weg „schon geladen“ |
| 6 | `W --profile dev build web-dev`, `npm ci`, `npm run lint`, `npm run typecheck`: je Exit-Code 0. Zusätzlich `npm run test`: 334 Tests in 20 Dateien bestanden |
| 7 | `D --profile dev --profile e2e down -v` und `W --profile dev down -v`: je Exit-Code 0, keine Container und Volumes von `twox-037` übrig |

**Abnahme von Hand (für a7)**

Vorbereitung im Wurzelverzeichnis wie in README „Browser test“: `.env` aus `.env.example`, `docker compose up -d --wait db valkey worker api`, Testkonto mit dem Schritt „Create test account“ anlegen. Danach im Browser `http://localhost:<TWOX_API_PORT>/` öffnen.

1. Anmelden mit `e2e-manager` und dem Entwicklungskennwort aus `.env`. Oben steht der Benutzername mit der Rolle „Verwalten“ bzw. „Manage“.
2. Auf „Import“ die Datei `testfactory/layout/devices.csv` wählen und den Probelauf starten.
   - Frische Datenbank: 14 Zeilen; Angelegt: Standorte 1, Bereiche 3, Anlagen 10, Geräte 13.
   - Dann „Übernehmen“: „Gespeichert“ mit denselben Zahlen.
3. „Zur Struktur“ und nach „Testfabrik“ suchen.
   - Die Bereiche Fertigungslinie, Netzübergang und Roboterzelle.
   - Unter Wareneingang und -ausgang das Gerät `dps-plc` mit `192.168.0.90`.
   - Die Ladestation `aps-charging` mit 0 Geräten. Ihre Notiz steht im Bearbeiten-Formular der Anlage.
4. Das Gerät „SPS Wareneingang und -ausgang“ öffnen.
   - Eine beliebige eigene Textdatei hochladen (Version 1). Keine Herstellerunterlage verwenden.
   - Den Titel anklicken und dieselbe Datei mit geändertem Inhalt als neue Version hochladen (Version 2).
   - Beide Versionen stehen mit verschiedener Prüfsumme da; ein Klick auf die Kurzform zeigt die volle Prüfsumme.
5. Auf „Änderungsprotokoll“ filtern.
   - Objektart „Dateiversion“ und Benutzer `e2e-manager`: zwei Einträge „Angelegt“ (`<Titel> v2`, `<Titel> v1`) mit Benutzer und Zeitpunkt.
   - Objektart „Gerät“: die 13 Geräte des Imports mit Benutzer, bei `dps-plc` mit `ip_address`.
   - Die Dateiseite selbst zeigt nur Einträge zur Datei, nicht zu den Versionen (siehe STATUS zu 036).
6. Auf „Import“ dieselbe Datei erneut prüfen: Angelegt 0, Geändert 0, Unverändert 1/3/10/13.

**Zweig und Arbeitsverzeichnis:** Zweig `worktree-agent-a17b3dacf4581d93c`, Arbeitsverzeichnis `.claude/worktrees/agent-a17b3dacf4581d93c`. Nicht gepusht.

**Abweichungen**

- Kriterium 3 des Umfangs verlangt „aps-charging ohne Gerät mit Notiz“ in der Struktur. Die Strukturseite zeigt Anlagennotizen nicht an. Der Browser-Test liest die Notiz deshalb im Formular „Edit plant“ und speichert nichts. Kein Fehler, aber eine Lücke für die Sichtprüfung. Vorschlag für später: Notiz der Anlage in der Struktur anzeigen.
- Die Protokolleinträge des Imports prüft der Browser-Test nur auf frischer Datenbank, wie im Auftrag vorgesehen. Bei späteren Läufen können sie hinter Seite 1 liegen. Der Backend-Test prüft sie immer.
- Keine Fehler in der Anwendung gefunden. Keine neue Abhängigkeit; `testfactory/` unverändert.
