# Auftrag 029 – API für Dateien: hochladen, Versionen, sicher herunterladen

Meilenstein: M1 · Freigabestufe: C · Status: offen

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

1. **Größenobergrenze für Uploads** (der Standardwert wird in Auftrag 016 gesetzt)
   - (a) Einstellbar über `TWOX_UPLOAD_MAX_BYTES`, Standard 200 MB.
   - (b) Einstellbar, mit anderem Standardwert, den a7 nennt.
   - (c) Ohne Grenze.
   - Empfehlung: (a). Der Wert ist ein Vorschlag der Leitstelle, keine Vorgabe der Startunterlage. Ohne Grenze könnte jedes Konto mit Rolle „Verwalten“ den Speicher füllen.

Dubletten und Konfigurationen: siehe Auftrag 024. Löschen: siehe Auftrag 026.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
