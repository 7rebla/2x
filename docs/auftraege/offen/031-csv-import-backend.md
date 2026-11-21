# Auftrag 031 – CSV-Import der Geräteliste (Backend, App assets)

Meilenstein: M1 · Freigabestufe: C · Status: zur Prüfung

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

**Status: zur Prüfung.** Alle Akzeptanzkriterien erfüllt, Läufe am 22.11.2026 im Container auf dem committeten Stand. Keine offene Frage an a7.

### Was wurde gebaut?

- `backend/twox/assets/csv_import.py`:
  - `parse(stream) -> ParsedFile`: liest zeilenweise Bytes (`readline`), dekodiert jede Zeile streng als UTF-8 (BOM am Anfang toleriert), `csv.reader` mit Dialekt `excel` und `strict=True`. Fehler als `RowError(line, column, message)`; `line` ist die Zeile, in der der Datensatz beginnt (Zeilenumbrüche in Anführungszeichen zählen mit), `None` für die ganze Datei.
    - Datei- bzw. Abbruchfehler: falscher Kopf (Zeile 1, mit „Missing“/„Not expected“, Hinweis bei Semikolon), kein UTF-8 (Zeile und Byte), leere Datei, Feld über `csv.field_size_limit()` (Zeilenfehler, danach Abbruch), sonst kaputtes CSV, Zeile über 8 MiB, mehr als 10 000 Zeilen, mehr als 1000 Fehler.
    - Zeilenprüfung mit `DeviceListRowSerializer` (DRF): Längen wie im Modell, Kennungsformat `validate_key`, IP (`IPAddressField`, IPv6 normalisiert, leer → `None`), NUL-Zeichen; Leerzeichen am Rand werden entfernt. Zeile mit `device_id` braucht `device_name`; Zeile ohne `device_id` darf nur `notes` haben (→ `Plant.notes`).
    - Widersprüche: gleiche `plant_id` mit anderem `site`, `area` oder `plant_name` (Fehler an der Spalte, Verweis auf die erste Zeile), doppelte `device_id`, zwei Zeilen ohne Gerät mit verschiedenen Notizen für dieselbe Anlage.
  - `apply(parsed, user, dry_run) -> ImportReport`: bei Fehlern aus `parse` kein Datenbankzugriff. Sonst alles in `acting_as(user)` und einer `transaction.atomic()`; Probelauf mit `set_rollback(True)`. Abgleich: Standort über Namen, Bereich über (Standort, Name), Anlage und Gerät über die Kennung (`in_bulk`). Angelegt und geändert wird einzeln mit `save()`, nur wenn sich ein Wert unterscheidet; nie gelöscht. Gerät wechselt die Anlage, Anlage den Bereich. Zähler `created`/`updated`/`unchanged` je Ebene. Ein `IntegrityError` (gleichzeitige Änderung) rollt alles zurück und wird als Fehler an der gerade geschriebenen Zeile gemeldet (Spalte nach Constraint), Zähler dann 0.
  - Meldungen mit `gettext`.
- `backend/twox/assets/integrity.py` (neu): Zuordnung der vier Unique-Constraints zu Feld und Meldung (`unique_violation`, Name aus `__cause__.diag.constraint_name` von psycopg). Die Meldungen sind dieselben Konstanten, die die Serializer nutzen.
- Nachtrag der Leitstelle: `save_checked()` in `views.py` kapselt `serializer.save()` in `transaction.atomic()`; ein `IntegrityError` einer der vier Constraints wird zu 400 mit Feldfehler (`{"name": [...]}` bzw. `{"key": [...]}`), andere `IntegrityError` bleiben 500. Gilt für Anlegen und Ändern aller vier Ressourcen (`perform_create`/`perform_update`, bei Geräten in `create`/`update`).
- `serializers.py`: `DeviceImportFormSerializer` (`file`, `dry_run` mit Standard `true`), `ImportReportSerializer`, `ImportCountsSerializer`, `ImportRowErrorSerializer`.
- `views.py`/`urls.py`: `POST /api/v1/imports/devices/` (`DeviceImportView`, Unterklasse von `LimitedUploadView` aus 029, `CanManage`, `operation_id` `devices_import`). Antwort 200 mit `ImportReport` (`dry_run`, `saved`, `rows`, `sites`/`areas`/`plants`/`devices`, `errors`), auch wenn die Datei Fehler hat; 400 nur bei ungültigem Formular; 413 über die Upload-Grenze.
- `management/commands/import_devices.py`: `import_devices <pfad> --user <name> [--commit]`; Konto muss aktiv sein und die Rolle `manage` haben. Ausgabe je Ebene, Fehler auf stderr (`line 3, ip_address: …`), dann Exit-Code 1.
- `deploy/compose/compose.yaml`: nur `backend-dev`, Volume `../../testfactory/layout:/testfactory/layout:ro`.
- `tests/config/expected_paths/assets.py`: `/api/v1/imports/devices/`. Schema und Client neu erzeugt.
- Tests (140 neu): `tests/assets/test_csv_import.py` (82), `test_import_api.py` (30), `test_import_command.py` (12), `test_integrity.py` (16), Hilfen in `csv_files.py`.
  - Abnahmefall mit der echten Datei: 1 Standort, 3 Bereiche (Fertigungslinie, Roboterzelle, Netzübergang), 10 Anlagen, 13 Geräte; `aps-charging` ohne Gerät mit Notiz; 6 Geräte ohne IP; jeder Wert jeder Zeile gleich der Datei (Umlaute unverändert). Zweiter Import: 0 angelegt, 0 geändert, keine neuen Protokolleinträge. Ein geänderter `software_version`: genau 1 geändertes Gerät, ein Eintrag mit Akteur und `[alt, neu]`. Probelauf ändert nichts und schreibt keine Einträge.
  - Fehler mit Zeilennummer: falscher Kopf (5 Varianten), ungültige IP (4), doppelte `device_id`, widersprüchliche Anlage (Name, Bereich, Standort), Latin-1, Feld über der Grenze (und genau an der Grenze angenommen), dazu Zeilenzählung über Zeilenumbrüche in Anführungszeichen, kaputtes Quoting, Feldanzahl, Pflichtspalten, Kennungen, NUL, Grenzen für Zeilen, Zeilenlänge und Fehlerzahl.
  - API: Rechte (anonym, ohne Rolle, `read` 403; `manage`, Superuser 200), ohne Feld `dry_run` Probelauf, `false`/`0` speichert, Fehlerbericht, beliebige Bytes ergeben Bericht statt 500, 400/415, 413 knapp über und 200 genau an der Grenze, CSRF ohne Token 403 und mit Token 200, Schema.
  - Wettlauf: alle vier Constraints beim Anlegen und Ändern mit ausgeschalteten Serializer-Prüfungen (400 am Feld, nichts gespeichert, Verbindung danach nutzbar); dazu ein echter Wettlauf mit zwei Threads und zwei Anfragen (`transaction=True`, Barriere in `pre_save`): Ergebnis 201 und 400 mit Feldfehler, ein Standort.
- `tests/assets/test_api.py`: Abfragegrenze beim Gerät-Ändern von 8 auf 10 (SAVEPOINT und RELEASE SAVEPOINT des Nachtrags).

### Wie wurde getestet?

`D` = `docker compose -p twox-031`, `W` = `docker compose -p twox-031-web -f deploy/compose/compose.web.yaml`, `.env` aus `.env.example` mit `TWOX_API_PORT=18031`. Docker Engine 29.9.3, Compose v5.7.0.

| AK | Ergebnis |
| --- | --- |
| 0 | erfüllt: `docker version`, `docker compose version` Exit 0 |
| 1 | erfüllt: Bau Exit 0, `up -d --wait` Exit 0 (db, valkey, api, worker healthy) |
| 2 | erfüllt: `create_account importer1 --role manage --update` (Kennwort nur über `-e TWOX_ACCOUNT_PASSWORD`) Exit 0; erster `import_devices … --commit`: `sites: 1 created`, `areas: 3 created`, `plants: 10 created`, `devices: 13 created`, `Saved.`; zweiter: alle `0 created, 0 updated` (1/3/10/13 unchanged) |
| 3 | erfüllt: `All checks passed!`; `131 files already formatted`; `Success: no issues found in 131 source files` |
| 4 | erfüllt: `1067 passed, 4 deselected`, `-rs` ohne Eintrag (0 übersprungen), Abnahmefall läuft mit; `pytest -m worker`: `4 passed` |
| 5 | erfüllt: `No changes detected` |
| 6 | erfüllt: `spectacular` ohne Ausgabe, Exit 0; danach `git diff --exit-code -- web/openapi` Exit 0, keine unversionierte Datei |
| 7 | erfüllt: Bau, `npm ci`, `api:generate` Exit 0, danach kein Unterschied in `web/openapi web/src/api`; `typecheck` Exit 0 |
| 8 | erfüllt: `build check` Exit 0; `unittest` 215 Tests `OK (skipped=1)`, Exit 0 (der Skip ist vorhanden und nicht von diesem Auftrag) |
| 9 | erfüllt: siehe unten |

Zusätzlich wie in der CI: Lizenzprüfung Python `License check passed.` (59 Pakete); web-Job komplett (`lint`, `typecheck`, `test` 173 passed, `build`, `licenses` `License check passed.`, `api:generate` ohne Unterschied); testfactory-Job komplett (ruff, format, mypy, unittest, Manifest-Prüfungen, kein `testfactory/extern`), mit `-p twox-031-tf`; e2e (Bau mit `web-dev`, `pull e2e`, `npm ci`, `up`, Schritt „Create test account“ wie in `ci.yml`, `run e2e`): `12 passed`.

Am laufenden Dienst (uvicorn, Laufzeit-Image, Sitzung von `importer1`): Datei ohne Feld `dry_run` → 200, Probelauf; `dry_run=false` → 200, gespeichert; ohne CSRF-Token → 403; Latin-1 mit falscher IP → 200 mit Fehler in Zeile 2 (Abbruch beim ersten Nicht-UTF-8-Byte); `Content-Length: 300000000` → 413.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a6728618563308860`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a6728618563308860`
- Nicht gepusht, nichts zusammengeführt.

### Abweichungen und Hinweise

1. **Zusätzliche Datei `twox/assets/integrity.py`** (im genannten Ordner): gemeinsame Zuordnung Constraint → Feld/Meldung für Views und Import. Die Meldungen der Serializer kommen jetzt von dort (Text unverändert).
2. **Fehler in der Datei ergeben 200, nicht 400.** Die Antwort ist immer ein `ImportReport`; ob gespeichert wurde, sagt `saved`, die Fehler stehen in `errors`. 400 gibt es nur für ein ungültiges Formular. Für 035 ist so ein einziger Antworttyp im Client nötig.
3. **Eigene Grenzen** über das Verlangte hinaus: höchstens 10 000 Zeilen, 8 MiB je physischer Zeile, 1000 gelistete Fehler (Konstanten in `csv_import.py`). Sie begrenzen Speicher, Laufzeit und Antwortgröße auch beim Befehl, der keine Upload-Grenze hat.
4. **Nach einem Lesefehler** (kein UTF-8, Feld über der Grenze, kaputtes Quoting, Zeile zu lang) bricht das Lesen ab; spätere Zeilen werden nicht geprüft (die Meldung sagt das). Grund: Nach einem Fehler mitten in einem mehrzeiligen Feld wären die Folgefehler irreführend. Bei Feldern über der Grenze ist die Spalte unbekannt (`column = null`).
5. **`dry_run` im Formular:** DRF liest ein fehlendes Boolean-Feld in Formularen als `false`. `FormBooleanField` setzt deshalb `default_empty_html = empty`, sonst würde ein Formular ohne `dry_run` speichern. Getestet.
6. **Leerzeichen am Rand** jedes Werts werden entfernt (DRF-Standard), sonst bleibt der Text unverändert. Werte, die mit `=`, `+`, `-` oder `@` beginnen, werden unverändert gespeichert; ein späterer CSV-Export muss sie gegen Formel-Injektion entschärfen (im Modul-Docstring vermerkt).
7. **Standorte und Bereiche** werden über den Namen gefunden und nie umbenannt; `updated` ist dort immer 0. Notizen einer Anlage ändern sich nur über eine Zeile ohne `device_id`.
8. **Der Befehl verlangt die Rolle `manage`** für `--user` (sonst stünde ein „Lesen“-Konto als Akteur im Protokoll).
9. Der Import ist synchron in der Anfrage (kein Celery). Bei 10 000 Zeilen sind das einige zehntausend Abfragen; für die Testfabrik unerheblich.
10. Der Thread-Test nutzt `transaction=True` und legt die Gruppe `manage` bei Bedarf selbst an, weil ein früherer transaktionaler Test die Daten der Datenmigration leeren kann.

Keine neue Abhängigkeit. `settings.py`, `.env.example`, `testfactory/`, `twox/importers/`, `web/` außer Schema und erzeugtem Client, `docs/DECISIONS.md` und `docs/STATUS.md` nicht geändert. Kein Push.
