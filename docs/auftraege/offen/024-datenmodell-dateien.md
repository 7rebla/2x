# Auftrag 024 – Datenmodell Dateien und Versionen mit Prüfsumme und Dubletten-Erkennung

Meilenstein: M1 · Freigabestufe: C · Status: offen

## Ziel

Jedes Gerät hat Dateien. Jede Datei hat unveränderliche Versionen mit Prüfsumme und Zeitpunkt (Startunterlage 4 und 5.7). Dubletten werden über die Prüfsumme erkannt. Eine Dienstschicht kapselt das Anlegen, damit API (029), Abnahme (037) und später das Einlesen (M2) denselben Weg nutzen.

## Umfang

- Modelle in `backend/twox/files/models.py`, Felder nach Frage 1 (Empfehlung):
  - `Document`:
    - `device`: FK auf `assets.Device`, `PROTECT`.
    - `title`: höchstens 200 Zeichen.
    - `kind`: `document` oder `configuration`.
    - `created_at`.
    - `created_by`: FK auf den Benutzer, `PROTECT`, leer erlaubt für Systemvorgänge.
  - `DocumentVersion`:
    - `document`: FK, `PROTECT`.
    - `number`: 1, 2, … je Dokument, eindeutig zusammen mit `document`.
    - `blob_key`, `sha256` (64 Zeichen, Index), `size`.
    - `content_type`: höchstens 100 Zeichen, Format `typ/untertyp` geprüft.
    - `original_filename`: höchstens 255 Zeichen.
    - `uploaded_by`: FK auf den Benutzer, `PROTECT`, leer erlaubt.
    - `created_at`.
    - Unveränderlich: `save()` auf einer bestehenden Version löst einen Fehler aus.
  - `verbose_name` mit `gettext_lazy`.
- Migration `files/migrations/0001_initial.py`.
- Dienst `backend/twox/files/services.py`:
  - `create_document(device, upload, title, kind, user) -> UploadResult`
  - `add_version(document, upload, user) -> UploadResult`
  - Beide schreiben über die Speicher-Schnittstelle aus 022 und laufen in einer Transaktion.
  - Die Versionsnummer wird ohne Wettlauf vergeben (Sperre auf das Dokument).
  - Bereinigung von Dateiname und Titel:
    - Pfadanteile entfernen (alles bis zum letzten `/` oder `\\`).
    - Steuerzeichen entfernen.
    - Auf die Feldlänge kürzen.
    - Ein leerer Name wird durch einen festen Ersatz ersetzt.
  - Konfigurationen nach Frage 2 (Empfehlung (a)): Mit `kind=configuration` gibt es eigens den Fehler `ConfigurationNotAcceptedError`; nichts wird gespeichert.
  - Dubletten nach Frage 3:
    - Gleiche Prüfsumme wie die neueste Version desselben Dokuments: Fehler `DuplicateVersionError` mit Verweis auf diese Version; keine neue Version.
    - Gleiche Prüfsumme an anderer Stelle: Die Version wird angelegt; `UploadResult.duplicates` nennt die anderen Fundstellen (Dokument, Version, Gerät).
  - Größenobergrenze `settings.TWOX_UPLOAD_MAX_BYTES` (seit 016) zusätzlich im Dienst prüfen (Fehler `UploadTooLargeError`).
  - Fehlermeldungen mit `gettext` markieren (für 034).
- Tests `backend/tests/files/`:
  - Zwei Versionen hintereinander ergeben die Nummern 1 und 2.
  - Gleiche Bytes als neue Version ergeben `DuplicateVersionError`.
  - Gleiche Bytes an einem anderen Gerät werden angelegt und als Dublette gemeldet; der Inhalt liegt nur einmal im Speicher.
  - Eine Version ist unveränderlich.
  - `PROTECT` verhindert das Löschen eines Geräts mit Dateien.
  - Eine zu große Datei wird abgewiesen.
  - Dateinamen wie `../../etc/passwd`, `C:\\x\\y.pdf` und Namen mit Steuerzeichen oder über 255 Zeichen werden bereinigt.
  - `kind=configuration` wird abgewiesen (bei Antwort (a) auf Frage 2).

## Nicht-Ziele

- API und Oberfläche (029, 036). Einlese-Auftrag (M2).
- Löschen von Dateien oder Versionen (Stufe C, nicht in M1).
- Erkennung des Dateityps aus dem Inhalt.
- Schwärzen von Zugangsdaten (M5).

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/files/models.py`, `backend/twox/files/migrations/` (neu), neu `backend/twox/files/services.py`
- `backend/tests/files/` (neue Testdateien)

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-024`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18024` setzen.
- Unter Git Bash vor Befehlen mit `/out/…` `MSYS_NO_PATHCONV=1` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0. `D logs migrate` zeigt `files.0001_initial` als angewendet.
2. Prüfungen und Typen:
   - `D run --rm backend-dev ruff check .` meldet `All checks passed!`.
   - `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0.
   - `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
3. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen. `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
4. `D run --rm backend-dev python manage.py makemigrations --check --dry-run` meldet `No changes detected`.
5. `D run --rm -v \"$PWD/web/openapi:/out\" backend-dev python manage.py spectacular --file /out/schema.yml`, danach zeigt `git diff --exit-code -- web/openapi` keinen Unterschied (kein Endpunkt in diesem Auftrag).
6. Abräumen: `D --profile dev down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); 016, 019 und 022 sind nach `main` zusammengeführt; Antworten von a7 auf Frage 1 bis 3.

- Welle 3, parallel zu 023 und 025.
- Einziger Auftrag mit Migrationen von `files`. `settings.py`, `assets/` und `storage.py` nicht anfassen.
- **Keine neue Abhängigkeit.**
- Leitplanke 5: Zugangsdaten aus Konfigurationen werden beim Import geschwärzt und weder gespeichert noch indexiert. Geschwärzt wird erst ab M5. Deshalb die Frage 2; bei Antwort (b) die Abweichung im Kurzbericht nennen.
- Laut Startunterlage 5.6 folgt auf den Upload später ein Einlese-Auftrag in der Warteschlange. Die Dienstschicht so schneiden, dass M2 dort ansetzen kann; hier wird nichts aufgerufen.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

1. **Felder von Datei und Version**
   - (a) Wie im Umfang, mit `kind` (Dokument oder Konfiguration). Startunterlage 4 und 5.6 unterscheiden beide, und das Einlesen in M2 und M5 wählt daran seinen Weg.
   - (b) Ohne `kind`; die Art wird erst beim Einlesen bestimmt.
   - Empfehlung: (a).
2. **Konfigurationsdateien vor M5 annehmen?** Leitplanke 5: Zugangsdaten werden weder gespeichert noch indexiert; geschwärzt wird erst ab M5.
   - (a) In M1 nur `kind=document` annehmen; Konfigurationen werden abgewiesen, bis M5 das Schwärzen bringt.
   - (b) Konfigurationen annehmen und roh speichern. Das ist eine Abweichung von Leitplanke 5 bis M5; M5 braucht dann einen Weg, die Rohdaten zu entfernen.
   - Empfehlung: (a). Die M1-Abnahme braucht nur eine Datei mit zwei Versionen. Grenze: Wer eine Konfiguration als Dokument hochlädt, umgeht das; die Oberfläche weist darauf hin.
3. **Verhalten bei Dubletten**
   - (a) Gleicher Inhalt wie die neueste Version derselben Datei: abweisen (HTTP 409 in 029). Gleicher Inhalt an anderer Stelle: annehmen, mit Hinweis auf die Fundstellen; der Inhalt liegt nur einmal im Speicher.
   - (b) Jede Dublette abweisen.
   - (c) Alles annehmen, nur mit Hinweis.
   - Empfehlung: (a). Ein Handbuch kann zu mehreren Geräten gehören; eine unveränderte „neue Version“ ist dagegen ein Bedienfehler.

Die Größenobergrenze: siehe Auftrag 029, Frage 1.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
