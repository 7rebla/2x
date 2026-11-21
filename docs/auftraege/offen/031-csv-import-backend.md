# Auftrag 031 – CSV-Import der Geräteliste (Backend, App assets)

Meilenstein: M1 · Freigabestufe: C · Status: offen

## Ziel

Eine Geräteliste im Format von `testfactory/layout/devices.csv` lässt sich mit Probelauf und Fehlerliste importieren (Startunterlage 4: „per CSV importieren“). Jede Änderung erscheint im Protokoll mit dem importierenden Benutzer. Die Geräteliste der Testfabrik ist der Abnahmefall. Kaputte oder zu große Dateien enden als Fehlerbericht, nie als Serverfehler.

## Umfang

- Der Import gehört zur Struktur und liegt deshalb in der App `assets` (Startunterlage 6: `/assets` Standort, Bereich, Anlage, Gerät). `importers` bleibt der Plugin-Schnittstelle der Einlese-Module vorbehalten.
- Format nach Frage 1 (Empfehlung: genau die 13 Spalten der Testfabrik):
  - Spalten `site, area, plant_id, plant_name, device_id, device_name, manufacturer, model, software_version, ip_address, address_source, protocols, notes`.
  - UTF-8, ein BOM wird toleriert. Trennzeichen Komma, Anführungszeichen nach RFC 4180.
- Zuordnung:
  - `site` → `Site.name`; `area` → `Area.name` am Standort.
  - `plant_id` und `plant_name` → `Plant.key` und `Plant.name`; `device_id` und `device_name` → `Device.key` und `Device.name`.
  - Die übrigen Spalten 1:1; eine leere `ip_address` bleibt leer.
  - Eine Zeile ohne `device_id` legt nur die Anlage an; `notes` geht dann an `Plant.notes`.
- Regeln nach Frage 2 (Empfehlung):
  - Abgleich über `Plant.key` und `Device.key`.
  - Vorhandene Objekte werden aktualisiert, neue angelegt, nichts wird gelöscht.
  - Ein Gerät kann die Anlage wechseln.
  - Widersprüche innerhalb der Datei sind Fehler: gleiche `plant_id` mit anderem Namen oder Bereich, doppelte `device_id`.
- Ablauf in `backend/twox/assets/csv_import.py`:
  - `parse(stream) -> ParsedFile` mit Fehlern je Zeile (Zeilennummer, Spalte, Meldung).
    - Ein falscher Spaltenkopf ist ein Fehler für die ganze Datei.
    - Bytes, die kein UTF-8 sind, sind ein Dateifehler mit Meldung.
    - Ein Feld über der Grenze des `csv`-Moduls ist ein Zeilenfehler.
  - `apply(parsed, user, dry_run) -> ImportReport` mit Zählern je Ebene (`created`, `updated`, `unchanged`) und Fehlerliste.
    - Alles läuft in einer Transaktion; bei Fehlern oder `dry_run` wird zurückgerollt.
    - Gespeichert wird einzeln über `save()`, sonst entstehen keine Protokolleinträge. Der Akteur kommt über `acting_as` aus 028.
  - Fehlermeldungen mit `gettext` markieren (für 034).
- API `POST /api/v1/imports/devices/`, in `twox/assets/urls.py`:
  - `multipart` mit `file` und `dry_run` (Standard `true`); Antwort `ImportReport`.
  - Rechte: `CanManage`.
  - Parser und Größenprüfung aus `twox/files/uploads.py` (029); bei Überschreitung 413.
- Management-Befehl `import_devices <pfad> --user <name> [--commit]` in `twox/assets/management/commands/`. Ohne `--commit` ist es ein Probelauf.
- Tests `backend/tests/assets/`:
  - Abnahmefall mit der echten Datei:
    - `testfactory/layout/` wird in `backend-dev` schreibgeschützt eingebunden (siehe Betroffene Bereiche).
    - Erwartet: 1 Standort, 3 Bereiche (Fertigungslinie, Roboterzelle, Netzübergang), 10 Anlagen, 13 Geräte.
    - Die Anlage `aps-charging` ist ohne Gerät und hat eine Notiz.
    - 6 Geräte haben keine IP-Adresse; Umlaute bleiben unverändert.
  - Ein zweiter Import derselben Datei ergibt 0 angelegt und 0 geändert.
  - Ein geänderter Wert in einer Zeile ergibt genau 1 geändertes Gerät und einen Protokolleintrag mit Akteur sowie altem und neuem Wert.
  - Ein Probelauf ändert nichts.
  - Fehler mit Zeilennummer bei: falschem Kopf, ungültiger IP, doppelter `device_id`, widersprüchlicher Anlage, Datei in Latin-1, Feld über der Grenze.
  - 413 bei Überschreitung der Größengrenze.
  - Rechte: nur `manage`.
  - CSRF: Mit `APIClient(enforce_csrf_checks=True)` ergibt ein POST ohne Token 403, mit Token 200.
- `backend/tests/config/expected_paths/assets.py`: Pfad ergänzen. Schema und Client neu erzeugen.

## Nicht-Ziele

- Oberfläche (035). Export als CSV.
- Andere Formate (Excel), Spaltenzuordnung durch den Benutzer, Erkennung des Trennzeichens.
- Änderungen an `testfactory/`; bei Antwort (a) auf Frage 1 ist keine nötig.
- Code in `twox/importers/`.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/assets/`: neu `csv_import.py` und `management/commands/import_devices.py`; `serializers.py`, `views.py`, `urls.py` ergänzen
- `backend/tests/assets/` (neue Testdateien), `backend/tests/config/expected_paths/assets.py`
- `deploy/compose/compose.yaml`: nur Dienst `backend-dev`, zusätzliches Volume `../../testfactory/layout:/testfactory/layout:ro`
- `web/openapi/schema.yml`, `web/src/api/generated/**`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-031`, `W` für `docker compose -p twox-031-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18031` setzen.
- Unter Git Bash vor Befehlen mit `/out/…` oder `/testfactory/…` `MSYS_NO_PATHCONV=1` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Import über den Befehl (`<Testkennwort>` ist ein selbst gewählter Entwicklungswert):
   - `TWOX_ACCOUNT_PASSWORD=<Testkennwort> D exec -T -e TWOX_ACCOUNT_PASSWORD api python manage.py create_account importer1 --role manage --update` (Wert nur in der Umgebung, nie als Argument; Hinweis aus 021/027)
   - Dann `D run --rm backend-dev python manage.py import_devices /testfactory/layout/devices.csv --user importer1 --commit`: gibt 1 Standort, 3 Bereiche, 10 Anlagen und 13 Geräte als angelegt aus.
   - Ein zweiter Aufruf meldet 0 angelegt und 0 geändert.
3. Prüfungen und Typen:
   - `D run --rm backend-dev ruff check .` meldet `All checks passed!`.
   - `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0.
   - `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
4. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen; der Abnahmefall mit der echten Datei läuft dabei mit. `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
5. `D run --rm backend-dev python manage.py makemigrations --check --dry-run` meldet `No changes detected`.
6. `D run --rm -v \"$PWD/web/openapi:/out\" backend-dev python manage.py spectacular --file /out/schema.yml` endet ohne Warnungen; `git diff --exit-code -- web/openapi` zeigt danach keinen Unterschied.
7. Client:
   - `W --profile dev build web-dev`, `W run --rm web-dev npm ci`, `W run --rm web-dev npm run api:generate`; danach zeigt `git diff --exit-code -- web/openapi web/src/api` keinen Unterschied.
   - `W run --rm web-dev npm run typecheck` endet mit Exit-Code 0.
8. Die Testfabrik-Prüfungen bleiben grün: `docker compose -f deploy/compose/testfactory.yaml build check` und `docker compose -f deploy/compose/testfactory.yaml run --rm check-offline python -m unittest discover -s testfactory/tests -t . -v` enden mit Exit-Code 0.
9. Abräumen: `D --profile dev down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

- **Nachtrag der Leitstelle (aus der Prüfung von 026):** Gleichzeitiges Anlegen derselben Kennung endet heute mit 500. Kapsle in diesem Auftrag `save()` in den Struktur-Views (`twox/assets/views.py`) in `transaction.atomic()`, fange `IntegrityError` ab und melde ihn je Constraint als Feldfehler (400); dazu ein Test, der den Wettlauf nachstellt. Der Import nutzt dieselben Constraints.

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); 019, 021, 026, 028 und 029 sind nach `main` zusammengeführt; Antworten von a7 auf Frage 1 und 2.

- Welle 6, parallel zu 032 und 033 (Oberfläche).
- Einziger Auftrag der Welle mit `compose.yaml`, Backend-Code, Schema und Client.
- **Keine neue Abhängigkeit.** Standardbibliothek `csv` und DRF-Serializer zur Zeilenprüfung.
  - Nicht django-import-export: Es erklärt nur Django bis 5.2 und Python bis 3.13 und zieht tablib und diff-match-patch nach.
- Abnahmefall laut Auftrag 106 und `testfactory/layout/description.md`: Die M1-Abnahme nutzt genau `testfactory/layout/devices.csv`.
  - Spaltenkopf und Inhalte sind durch `testfactory/tests/test_layout.py`, `test_crossrefs.py` und `test_evidence.py` festgeschrieben; die Datei nicht ändern.
  - Legt a7 andere Spalten fest, passt die Leitstelle die Testfabrik in einem eigenen Auftrag an.
- `<Testkennwort>` ist ein selbst gewählter Entwicklungswert und wird nicht committet.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

1. **Importformat**
   - (a) Genau die 13 Spalten von `testfactory/layout/devices.csv` als Format v1 (englische Spaltennamen, Komma, UTF-8).
   - (b) Eigenes Format mit deutschen Spaltennamen oder Semikolon (Excel mit deutscher Einstellung). Die Testfabrik-Datei müsste angepasst oder umgewandelt werden.
   - Empfehlung: (a). Kein Umbau der Testfabrik und ihrer Tests; Semikolon-Dateien können später dazukommen.
2. **Abgleich-Regeln**
   - (a) Anlegen und Aktualisieren über die Kennungen, nie löschen, alles oder nichts in einer Transaktion, Probelauf als Standard.
   - (b) Zusätzlich Geräte löschen, die in der Datei fehlen (Stufe C „Daten löschen“).
   - Empfehlung: (a).

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
