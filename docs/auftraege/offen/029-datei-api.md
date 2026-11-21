# Auftrag 029 – API für Dateien: hochladen, Versionen, sicher herunterladen

Meilenstein: M1 · Freigabestufe: C · Status: zur Prüfung

## Ziel

Dateien je Gerät lassen sich über die API hochladen, um neue Versionen ergänzen, auflisten und herunterladen. Dubletten werden gemeldet. Zu große Uploads werden abgewiesen, bevor sie den Server füllen. Heruntergeladene Dateien kann der Browser nicht als Seite der Anwendung ausführen.

## Umfang

- Endpunkte in `twox/files/urls.py`, mit den Rechten aus 021:
  - `GET /api/v1/devices/{device_id}/documents/`: Dateien des Geräts mit neuester Version (`CanRead`).
  - `POST /api/v1/devices/{device_id}/documents/`: neue Datei, `multipart/form-data` mit `file`, `title` (optional, Standard Dateiname) und `kind` (`CanManage`). Antwort 201 mit Dokument, Version 1 und `duplicates`.
  - `GET /api/v1/documents/{id}/`: Datei mit allen Versionen (`CanRead`).
  - `POST /api/v1/documents/{id}/versions/`: neue Version (`CanManage`). 409 mit Verweis auf die vorhandene Version, wenn der Inhalt der neuesten Version gleicht.
  - `GET /api/v1/document-versions/{id}/download/`: Inhalt (`CanRead`).
- Fehlerbilder:
  - `kind=configuration` ergibt 400 mit verständlicher Meldung, wenn a7 bei Auftrag 024, Frage 2 so entscheidet.
  - Unbekanntes Gerät ergibt 404.
  - Meldungen mit `gettext` markieren.
- Größenobergrenze `settings.TWOX_UPLOAD_MAX_BYTES` (seit 016), schon vor dem Lesen des Inhalts durchgesetzt:
  - Neu `backend/twox/files/uploads.py` mit zwei Teilen: einer Prüfung von `CONTENT_LENGTH` vor dem Parsen und einem eigenen Upload-Handler, der beim Überschreiten mitten im Datenstrom abbricht (`StopUpload`).
  - Antwort ist 413; es bleibt keine temporäre Datei zurück.
  - Die Upload-Ansichten setzen `MultiPartParser` und diesen Handler selbst; global bleibt JSON.
  - `uploads.py` nutzt später auch der CSV-Import (031).
  - Djangos Speicher-Grenzen so lassen, dass große Dateien temporär auf die Platte gehen. `FILE_UPLOAD_TEMP_DIR` bleibt beim Systemstandard; durch die Prüfung ist das je Anfrage begrenzt. Im Kurzbericht festhalten.
- Sicheres Herunterladen:
  - Antwort immer als `FileResponse(as_attachment=True, filename=…)` mit dem bereinigten Originalnamen, gestreamt über die Speicher-Schnittstelle aus 022.
  - `X-Content-Type-Options: nosniff` und `Content-Security-Policy: sandbox`.
  - `Content-Type` nur aus einer festen Erlaubt-Liste für die Arten aus Startunterlage 4 (PDF, Office, Markdown und Text, Bilder ohne SVG); sonst `application/octet-stream`. Die Liste steht im Code und im Kurzbericht.
- Antworten typisiert im Schema, auch `multipart` und die Binärantwort. Schema und Client neu erzeugen.
- `backend/twox/files/admin.py`: Dokumente und Versionen nur lesend; Zugang nur für Superuser (Admin-Seite aus 016).
- Tests `backend/tests/files/`:
  - Hochladen und zweite Version; 409 bei gleichem Inhalt; Dubletten-Hinweis über Gerätegrenzen.
  - Der Download liefert die gleichen Bytes (Prüfsumme).
  - Rechte: anonym 403; `read` darf nicht hochladen, aber herunterladen.
  - 413 bei einem Body knapp über der Grenze, ohne Restdatei im temporären Verzeichnis.
  - 404 für ein unbekanntes Gerät.
  - Ein Upload mit `content_type` `text/html` oder `image/svg+xml` wird als `application/octet-stream` mit `attachment`, `nosniff` und `sandbox` ausgeliefert.
  - Ein Dateiname mit Pfadanteilen oder Steuerzeichen erscheint bereinigt in `Content-Disposition`.
  - CSRF: Mit `APIClient(enforce_csrf_checks=True)` und angemeldet als `manage` ergibt ein Multipart-POST ohne `X-CSRFToken` 403, mit Token 201.
- `backend/tests/config/expected_paths/files.py`: die fünf Pfade. Der Aufzähl-Test aus 025 bleibt ohne neue Ausnahme grün.

## Nicht-Ziele

- Oberfläche (036). Fortschrittsanzeige.
- Löschen von Dateien oder Versionen. Vorschau im Browser.
- Einlese-Auftrag nach dem Upload (M2).
- Einschränkung der hochladbaren Dateiarten.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/files/`: neu `serializers.py`, `views.py`, `admin.py`, `uploads.py`; `urls.py` füllen
- `backend/tests/files/` (neue Testdateien), `backend/tests/config/expected_paths/files.py`
- `web/openapi/schema.yml`, `web/src/api/generated/**`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-029`, `W` für `docker compose -p twox-029-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18029` setzen.
- Unter Git Bash vor Befehlen mit `/out/…` `MSYS_NO_PATHCONV=1` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Prüfungen und Typen:
   - `D run --rm backend-dev ruff check .` meldet `All checks passed!`.
   - `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0.
   - `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
3. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen. `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
4. `D run --rm backend-dev python manage.py makemigrations --check --dry-run` meldet `No changes detected`.
5. Schema:
   - `D run --rm -v \"$PWD/web/openapi:/out\" backend-dev python manage.py spectacular --file /out/schema.yml` endet ohne Warnungen.
   - Das committete Schema enthält die fünf Pfade.
   - `git diff --exit-code -- web/openapi` zeigt danach keinen Unterschied.
6. Client:
   - `W --profile dev build web-dev`, `W run --rm web-dev npm ci`, `W run --rm web-dev npm run api:generate`; danach zeigt `git diff --exit-code -- web/openapi web/src/api` keinen Unterschied.
   - `W run --rm web-dev npm run typecheck` endet mit Exit-Code 0.
7. Abräumen: `D --profile dev down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); 016, 021, 022, 024 und 025 sind nach `main` zusammengeführt; Antwort von a7 auf Frage 1 (für 016).

- Welle 5, parallel zu 028 und 030.
- **Reihenfolge beim Zusammenführen: nach 028.** Dieser Auftrag erzeugt Schema und Client auf dem neuen `main` neu.
- `settings.py`, `.env.example` und `compose.yaml` nicht anfassen; die Einstellung und ihre Einträge stehen seit 016 und 022.
- Keine Migration in `files`; die Modelle stehen seit 024.
- **Keine neue Abhängigkeit.**
- Die Prüfsumme berechnet der Server, nicht der Browser (Dienst aus 024).
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

1. **Größenobergrenze für Uploads** (der Standardwert wird in Auftrag 016 gesetzt)
   - (a) Einstellbar über `TWOX_UPLOAD_MAX_BYTES`, Standard 200 MB.
   - (b) Einstellbar, mit anderem Standardwert, den a7 nennt.
   - (c) Ohne Grenze.
   - Empfehlung: (a). Der Wert ist ein Vorschlag der Leitstelle, keine Vorgabe der Startunterlage. Ohne Grenze könnte jedes Konto mit Rolle „Verwalten“ den Speicher füllen.

Dubletten und Konfigurationen: siehe Auftrag 024. Löschen: siehe Auftrag 026.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Akzeptanzkriterien erfüllt, Läufe am 21.11.2026 im Container auf dem committeten Stand. Keine offene Frage an a7; eine Abweichung (Punkt 1 unten, `asgi.py`) entscheidet die Leitstelle.

**Was wurde gebaut?**

- Endpunkte (`backend/twox/files/urls.py`, `views.py`), fünf Operationen auf vier Pfaden:
  - `GET /api/v1/devices/{device_id}/documents/` (`device_documents_list`, `CanManageOrReadOnly`, lesend also `read`/`manage`): Dateien des Geräts nach Titel, je mit `latest_version`.
  - `POST` auf denselben Pfad (`device_documents_create`, nur `manage`): `multipart/form-data` mit `file`, `title` (optional, sonst bereinigter Dateiname), `kind` (Standard `document`). 201 mit `document`, `version` (Nummer 1) und `duplicates` (Gerät mit Id, Kennung, Name; Dokument mit Id, Titel; Version mit Id, Nummer).
  - `GET /api/v1/documents/{document_id}/` (`document_retrieve`, `CanRead`): Datei mit allen Versionen, älteste zuerst.
  - `POST /api/v1/documents/{document_id}/versions/` (`document_version_create`, nur `manage`): neue Version, 201 wie oben. Gleicher Inhalt wie die neueste Version: 409 mit `detail`, `code: duplicate_version` und `existing_version` (die vorhandene Version).
  - `GET /api/v1/document-versions/{version_id}/download/` (`document_version_download`, `CanRead`): Inhalt als Anhang.
  - Fehler: `kind=configuration` → 400 `{"kind": ["Configuration files are not accepted yet: …"]}` (Meldung aus dem Dienst, mit `gettext`); unbekannte Art → 400; unbekanntes Gerät, Dokument, Version → 404; JSON statt Formular → 415. Alle eigenen Meldungen mit `gettext` markiert.
  - Prüfsumme, Dubletten, Nummern und Bereinigung kommen aus dem Dienst von 024 (`create_document`, `add_version`); die Ansichten rechnen nichts selbst.
- `backend/twox/files/uploads.py` (Größengrenze `TWOX_UPLOAD_MAX_BYTES`, Antwort 413 `{"detail": "The file is larger than the limit of … bytes."}`):
  - `check_content_length`: vergleicht `CONTENT_LENGTH` vor dem Parsen mit Grenze plus `MULTIPART_OVERHEAD_BYTES` (64 KiB für Rahmen und Formularfelder).
  - `LimitedUploadHandler`: steht vor den Handlern aus `FILE_UPLOAD_HANDLERS`, zählt die Dateibytes und bricht über der Grenze mit `StopUpload(connection_reset=True)` ab; Django schließt dann die Datei des nächsten Handlers, die temporäre Datei verschwindet.
  - `LimitedUploadView` (Basisklasse für Upload-Ansichten, auch für 031 gedacht): setzt `MultiPartParser` (global bleibt JSON) und installiert Prüfung und Handler in `initial()` **vor** der Authentifizierung – die CSRF-Prüfung der Sitzung liest das Formular bereits. `upload_data()` liefert das Formular oder 413.
  - `RequestBodyLimitMiddleware` (ASGI), siehe Abweichung 1.
  - Djangos Speichergrenzen bleiben unverändert: Dateiteile über `FILE_UPLOAD_MAX_MEMORY_SIZE` (2,5 MB) gehen in eine temporäre Datei in `FILE_UPLOAD_TEMP_DIR` (Systemstandard, im Container `/tmp`). Je Anfrage ist das durch die Prüfungen oben auf Grenze plus 64 KiB begrenzt. `settings.py` nicht geändert.
- `backend/twox/files/downloads.py` (neu, siehe Abweichung 2): `BlobDownloadResponse` = `FileResponse(as_attachment=True, filename=clean_filename(...))`, gelesen über `get_blob_storage().open_blob()`. Setzt `X-Content-Type-Options: nosniff` und `Content-Security-Policy: sandbox`. `Content-Disposition` nach RFC 6266/5987 von Django (`filename="…"` mit Escapes, sonst `filename*=utf-8''…`); der gespeicherte Name wird beim Herunterladen noch einmal bereinigt. Blöcke zu 64 KiB; unter ASGI liest `__aiter__` Block für Block in einem Thread (sonst sammelt Django eine synchrone Datei komplett im Speicher, siehe Abweichung 3). Die Ansicht ignoriert `Accept` (keine 406 beim Herunterladen).
- **Erlaubt-Liste für `Content-Type`** (`SAFE_CONTENT_TYPES`), alles andere wird `application/octet-stream`:
  - PDF: `application/pdf`
  - Office: `application/msword`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `application/vnd.ms-excel`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `application/vnd.ms-powerpoint`, `application/vnd.openxmlformats-officedocument.presentationml.presentation`, `application/vnd.oasis.opendocument.text`, `application/vnd.oasis.opendocument.spreadsheet`, `application/vnd.oasis.opendocument.presentation`
  - Markdown und Text: `text/markdown`, `text/plain`
  - Bilder ohne SVG: `image/png`, `image/jpeg`, `image/gif`, `image/webp`, `image/tiff`, `image/bmp`
- `backend/twox/files/serializers.py`: Dokument, Dokument mit Versionen, Version, Dublette, Upload-Ergebnis, die beiden Formulare (Datei im Schema als `format: binary`), 409-Antwort, Fehlerantwort. Hochgeladen von/angelegt von als Benutzername oder `null`.
- `backend/twox/files/admin.py`: `Document` (mit Versionen als Inline) und `DocumentVersion` nur lesend – kein Hinzufügen, Ändern, Löschen; Zugang wie die ganze Admin-Seite nur für aktive Superuser.
- Aus STATUS vorgemerkt (022): Befehl `python manage.py remove_stale_uploads [--older-than-hours N]` (`backend/twox/files/management/commands/`, Standard 24 h, mindestens 1 h) löscht `<TWOX_MEDIA_ROOT>/tmp/upload-*.part`, die älter als die Frist sind; Symlinks und andere Namen bleiben. Nicht automatisch beim Start (dafür müsste `compose.yaml` geändert werden), siehe Grenzen.
- Schema (`web/openapi/schema.yml`) und Client (`web/src/api/generated/**`) neu erzeugt: fünf Operationen, Anfragen als `multipart/form-data` (`formDataBodySerializer`, Datei `Blob | File`), Download-Antwort `*/*` binär (`Blob | File`), Fehlerantworten 403/404/409/413 typisiert.
- `backend/tests/config/expected_paths/files.py`: die vier Pfade. `tests/config/test_api.py` unverändert und grün, keine neue Ausnahme.

**Wie wurde getestet?** `D` = `docker compose -p twox-029`, `W` = `docker compose -p twox-029-web -f deploy/compose/compose.web.yaml`, `.env` aus `.env.example` mit `TWOX_API_PORT=18029`, Docker Engine 29.9.3, Compose v5.7.0.

Neue Tests (101 Fälle): `tests/files/test_api.py` (33), `test_uploads.py` (17), `test_downloads.py` (36, davon 18 je erlaubtem Typ), `test_admin.py` (5), `test_remove_stale_uploads.py` (6), `tests/config/test_asgi.py` (4). Abgedeckt u. a.: Hochladen und zweite Version, Liste und Detail; 409 bei gleichem Inhalt (keine Version angelegt); Dubletten-Hinweis über Gerätegrenzen (Inhalt nur einmal gespeichert); Download mit gleicher Prüfsumme und `Content-Length`; anonym 403 auf allen fünf Operationen; `read` lädt herunter, aber nicht hoch; 404 für unbekanntes Gerät (GET und POST), Dokument, Version; `text/html`, `image/svg+xml`, `application/xhtml+xml` als `application/octet-stream` mit `attachment`, `nosniff`, `sandbox`; Dateiname `../../etc/sub\dir\re<0x01>port<0x7f>.pdf` (roh gesendet) erscheint als `report.pdf`; eine an den Diensten vorbei gespeicherte Zeile mit `C:\dir/../in"ject\r\nX-Evil: 1.txt` wird als `attachment; filename="in\"jectX-Evil: 1.txt"` ausgeliefert, ohne Kopfzeilen-Einschleusung; Umlaute nach RFC 5987; CSRF mit `APIClient(enforce_csrf_checks=True)` als `manage`: ohne Token 403, mit Token 201; Grenze: Datei genau an der Grenze 201, ein Byte darüber 413 mitten im Datenstrom (Django hatte eine temporäre Datei angelegt, sie ist danach weg, `FILE_UPLOAD_TEMP_DIR` und Speicher leer), Body ein Byte über Grenze plus 64 KiB 413 vor dem Parsen (keine temporäre Datei angelegt), dasselbe, wenn die CSRF-Prüfung das Formular liest, und für eine neue Version; feste Zahl von Abfragen für die Liste; Schema mit `multipart/form-data` und binärer Antwort; ASGI-Middleware mit Test-App und mit dem echten Django-ASGI-Handler; Streaming unter ASGI ohne Warnung in Blöcken zu 64 KiB.

| AK | Ergebnis |
| --- | --- |
| 0 | erfüllt: `docker version` und `docker compose version` Exit 0 |
| 1 | erfüllt: Bau Exit 0, `up -d --wait` Exit 0 (db, valkey, api, worker healthy) |
| 2 | erfüllt: `All checks passed!`; `112 files already formatted`, Exit 0; `Success: no issues found in 112 source files` |
| 3 | erfüllt: `583 passed, 4 deselected`, 0 fehlgeschlagen, 0 übersprungen (`-rs` ohne Eintrag); `pytest -m worker`: `4 passed` |
| 4 | erfüllt: `No changes detected` |
| 5 | erfüllt: `spectacular` ohne Ausgabe, Exit 0; Schema enthält die fünf Operationen (vier Pfade); danach `git diff --exit-code -- web/openapi` Exit 0, keine unversionierte Datei |
| 6 | erfüllt: Bau `web-dev`, `npm ci`, `api:generate` Exit 0, danach `git diff --exit-code -- web/openapi web/src/api` Exit 0; `typecheck` Exit 0 |
| 7 | erfüllt: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` Exit 0; danach kein Container, Volume oder Netz `twox-029*` |

Zusätzlich wie in der CI: Lizenzprüfung Python `License check passed.`; web-Job komplett (`lint`, `typecheck`, `test` 73 passed, `build`, `licenses` `License check passed.`, `api:generate` ohne Unterschied); e2e-Job (Bau mit `web-dev`, `pull e2e`, `npm ci`, Playwright) `5 passed`.

Live gegen uvicorn im `api`-Container geprüft (Wegwerf-Testkonto mit Rolle `manage`, Kennwort im Container erzeugt und nie ausgegeben): Anmeldung über allauth, Upload 5 MB (201, Name `../evil/Handbuch Ölpumpe.pdf` → `Handbuch Ölpumpe.pdf`), gleicher Inhalt 409, HTML-Version 201, Download v1 mit gleicher Prüfsumme und `filename*=utf-8''Handbuch%20%C3%96lpumpe.pdf`, Download der HTML-Version als `application/octet-stream`, `nosniff`, `sandbox`. `Content-Length: 300000000` → 413 sofort; ein Body ohne Länge (chunked) wird nach rund 200 MB mit 413 abgebrochen; in `/tmp` bleibt nichts liegen; im Log keine Streaming-Warnung von Django.

**Zweig und Arbeitsverzeichnis:** Zweig `worktree-agent-a762d9b4486f2d55e`, Arbeitsverzeichnis `.claude/worktrees/agent-a762d9b4486f2d55e`. Nicht gepusht, nichts zusammengeführt.

**Abweichungen**

1. **`backend/twox/config/asgi.py` geändert (nicht im Auftrag genannt), eigener Commit `8c16f49` mit `tests/config/test_asgi.py`.** Djangos ASGI-Handler (uvicorn) liest den ganzen Body in eine temporäre Datei, bevor eine Ansicht läuft (`ASGIHandler.read_body`, Django 6.1.3). Die im Auftrag verlangten Prüfungen in der Ansicht kämen im Betrieb also erst, nachdem ein beliebig großer Upload schon auf der Platte liegt; das Ziel „abgewiesen, bevor sie den Server füllen" wäre nicht erreicht, und die Annahme „durch die Prüfung ist das je Anfrage begrenzt" träfe nicht zu. Deshalb umhüllt `RequestBodyLimitMiddleware` (in `uploads.py`) die ASGI-Anwendung: `Content-Length` über Grenze plus 64 KiB → 413, ohne dass Django liest; ein Body ohne Länge wird gezählt und über derselben Schranke abgebrochen. Gilt für alle Pfade (JSON-Anfragen liegen weit darunter). Ohne diesen Commit bleibt alles andere funktionsfähig, nur ist die Grenze im Betrieb unter ASGI dann nicht vor dem Spoolen wirksam.
2. Zusätzliche neue Dateien im genannten Bereich: `twox/files/downloads.py` (Erlaubt-Liste und Download-Antwort), `twox/files/management/commands/remove_stale_uploads.py`, `tests/files/conftest.py`, `tests/files/helpers.py`. `test_services.py` und `test_storage.py` unverändert.
3. Nicht verlangt, aber für „gestreamt" nötig: Unter ASGI würde Django eine `FileResponse` mit synchroner Datei vollständig in den Speicher lesen (`StreamingHttpResponse.__aiter__` mit `sync_to_async(list)`), bei 200 MB also 200 MB RAM je Download. `BlobDownloadResponse.__aiter__` liest stattdessen blockweise.
4. „Die fünf Pfade": Es sind fünf Endpunkte, aber GET und POST teilen sich einen Pfad; `expected_paths/files.py` hat daher vier Pfade.
5. Reihenfolge der Antworten: Die Größenprüfung läuft vor der Authentifizierung. Eine anonyme Anfrage mit zu großem `Content-Length` bekommt 413 statt 403. Umgekehrt liest bei einem angemeldeten Konto mit Rolle `read` die CSRF-Prüfung von DRF das Formular (bis zur Grenze) ein, bevor 403 kommt; das lässt sich bei `SessionAuthentication` nicht vermeiden.
6. Ein leeres `kind` im Formular gilt nach DRF-Regel für Formulare als „nicht angegeben" und ergibt `document`; nur unbekannte Werte ergeben 400.
7. Fehlerform bei Konfiguration: beim Anlegen am Feld (`{"kind": [...]}`), bei einer neuen Version eines (auf anderem Weg angelegten) Konfigurations-Dokuments unter `non_field_errors`.
8. Das Schema beschreibt 403/404/413 mit `ErrorDetail` (`detail`) und 409 mit eigenem Typ; 400 ohne Körper-Schema (Feldfehler je Formularfeld). `latest_version` ist im Schema nullbar (nur ein Dokument ganz ohne Version, das über die Dienste nicht entstehen kann).

**Grenzen (für 038)**

- `remove_stale_uploads` läuft nur von Hand (oder per Zeitplan des Betreibers), nicht beim Start; ein Start-Hook bräuchte `compose.yaml`.
- Nach einem harten Abbruch (SIGKILL, OOM) mitten im Parsen kann eine temporäre Datei von Djangos `TemporaryFileUploadHandler` in `/tmp` des `api`-Containers liegen bleiben (Schreibschicht des Containers, bis er neu erstellt wird). Djangos ASGI-Spool-Datei ist unbenannt und verschwindet mit dem Prozess.
- Ein Download eines Blobs, der im Speicher fehlt, ergibt 500 (Inkonsistenz, nicht verdeckt).
- Reihenfolge beim Zusammenführen: Nach 026, 027 und 028 müssen Schema und Client auf dem neuen `main` neu erzeugt werden; dieser Zweig wurde auf dem Stand `25fa4d7` erzeugt.

Keine neue Abhängigkeit. `settings.py`, `.env.example`, `compose.yaml`, Migrationen, `storage.py`, `services.py`, `docs/DECISIONS.md` und `docs/STATUS.md` nicht geändert. Kein Push.
