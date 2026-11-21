# Auftrag 022 – Dateispeicher: Schnittstelle, atomare Ablage nach Prüfsumme, Volume

Meilenstein: M1 · Freigabestufe: C · Status: offen

## Ziel

Hochgeladene Dateien landen unveränderlich in einem Speicher hinter einer Schnittstelle (CLAUDE.md: „Schnittstellen vor Umsetzung“). Im kleinen Betrieb ist das ein Docker-Volume. Später kommt ein S3-kompatibler Speicher als zweite Umsetzung derselben Schnittstelle dazu (Startunterlage 5.2 und 5.4), ohne dass sich der übrige Code ändert. Gleichzeitiges Hochladen und Abbrüche hinterlassen keine falschen oder halben Dateien.

## Umfang

- `backend/twox/files/storage.py`:
  - Eine schmale Schnittstelle (`Protocol`) mit:
    - `store_blob(stream) -> StoredBlob` (Schlüssel, SHA-256, Größe);
    - `open_blob(key) -> IO[bytes]`;
    - `blob_exists(key) -> bool`.
  - Eine Umsetzung für das Dateisystem mit dem Wurzelverzeichnis `settings.TWOX_MEDIA_ROOT` (aus 016) und eine Funktion, die die gültige Umsetzung liefert.
  - Keine öffentlichen URLs, kein Löschen von Inhalten in M1.
- Ablage nach Frage 1 (Empfehlung: inhaltsadressiert):
  - Der Schlüssel hat die Form `sha256/ab/cd/<sha256>`.
  - Geschrieben wird erst in eine temporäre Datei im selben Volume (z. B. `<root>/tmp/`). Dabei werden Prüfsumme und Größe in Blöcken berechnet.
  - Danach wird die Datei atomar unter den Schlüssel gelegt (`os.link` oder `os.replace`).
  - Liegt der Schlüssel schon vor: Größe vergleichen; die temporäre Datei wird verworfen.
  - Nie Djangos Umbenennung bei vorhandenem Namen (`get_available_name`); der gespeicherte Name ist immer gleich dem Schlüssel.
  - Bei einem Fehler oder Abbruch wird die temporäre Datei entfernt. Unter dem Schlüssel entsteht nie eine halbe Datei.
- `open_blob` und `blob_exists` prüfen den Schlüssel gegen `^sha256/[0-9a-f]{2}/[0-9a-f]{2}/[0-9a-f]{64}$`; sonst kommt eine definierte Ausnahme. Damit sind keine Pfade außerhalb der Ablage lesbar.
- Compose `deploy/compose/compose.yaml`:
  - Benanntes Volume `media-data`, eingebunden unter `/data/media` in `api` und `worker` (beschreibbar).
  - `TWOX_MEDIA_ROOT` und `TWOX_UPLOAD_MAX_BYTES` im gemeinsamen Umgebungsblock (Einstellungen seit 016).
- `backend/Dockerfile`, Stufe `runtime`: Verzeichnis `/data/media` anlegen und dem Benutzer `twox` (uid/gid 10001) übergeben, damit das neue Volume mit diesem Besitzer entsteht. `/app` bleibt schreibgeschützt.
- `.env.example`: `TWOX_MEDIA_ROOT` und `TWOX_UPLOAD_MAX_BYTES` mit Kommentar.
- Tests `backend/tests/files/` (neu, mit eigener Fixture für ein temporäres Wurzelverzeichnis; kein Volume nötig):
  - Gleiche Bytes ergeben denselben Schlüssel und werden nur einmal geschrieben.
  - Die Prüfsumme stimmt mit `hashlib` überein.
  - Eine große Datei (z. B. 20 MB, im Test erzeugt) wird blockweise verarbeitet.
  - Zwei gleichzeitige `store_blob` mit gleichem Inhalt (Threads) ergeben einen Schlüssel und eine Datei mit richtigem Inhalt.
  - Ein im Test abgebrochener Schreibvorgang hinterlässt weder eine Datei unter dem Schlüssel noch eine temporäre Datei.
  - Ungültige Schlüssel wie `../x` oder `sha256/zz/…` werden abgewiesen.
  - Ein unbekannter gültiger Schlüssel ergibt die definierte Ausnahme.

## Nicht-Ziele

- Datenmodell Datei und Version (024), Upload-API (029).
- django-storages und S3 (siehe Hinweise).
- Sicherung und Löschen von Dateien.

## Betroffene Bereiche (Ordner, Dateien)

- neu: `backend/twox/files/storage.py`, `backend/tests/files/` (neu)
- `deploy/compose/compose.yaml`, `.env.example`
- `backend/Dockerfile` (nur Stufe `runtime`)

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-022`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18022` setzen.
- Unter Git Bash vor Befehlen mit `/out/…` `MSYS_NO_PATHCONV=1` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. `D exec api sh -c \"id -u; stat -c %u /data/media; touch /data/media/probe && rm /data/media/probe && echo writable\"` gibt `10001`, `10001` und `writable` aus. Derselbe Befehl mit `worker` statt `api` ebenso.
3. `D exec api sh -c \"touch /app/probe\"` schlägt fehl (Exit-Code ungleich 0).
4. Gemeinsames Volume:
   - Ein Aufruf in `api` mit `D exec api python manage.py shell -c …` speichert die Bytes `2x` über die Schnittstelle.
   - Die Ausgabe nennt die SHA-256 von `2x` und liest `b'2x'` zurück.
   - Ein Aufruf in `worker` findet denselben Schlüssel (`True`).
   - Die genauen Befehle stehen im Kurzbericht.
5. Prüfungen und Typen:
   - `D run --rm backend-dev ruff check .` meldet `All checks passed!`.
   - `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0.
   - `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
6. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen. `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
7. `D run --rm backend-dev python manage.py makemigrations --check --dry-run` meldet `No changes detected`.
8. Der Browser-Test bleibt grün (Image geändert):
   - `D --profile dev build migrate api worker web-dev`
   - `D --profile e2e pull e2e`
   - `D --profile dev run --rm web-dev npm ci`
   - `D --profile e2e run --rm e2e` meldet alle Fälle bestanden.
9. Abräumen: `D --profile dev --profile e2e down -v` endet mit Exit-Code 0 und entfernt auch `media-data`.

## Vorgaben und Hinweise

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); 016 ist nach `main` zusammengeführt; Antworten von a7 auf Frage 1 und 2.

- Welle 2, parallel zu 020 und 021.
- Einziger Auftrag der Welle mit `compose.yaml`, `.env.example` und `backend/Dockerfile`. `settings.py` nicht anfassen; die Einstellungen kommen aus 016.
- **Keine neue Abhängigkeit.**
- **django-storages nicht aufnehmen:**
  - Version 1.14.6 (02.04.2025, BSD-3-Clause) erklärt nur Python bis 3.12 und Django bis 5.1 (Auftrag 001, Kurzbericht).
  - Auf master stehen Django bis 6.0 und Python bis 3.14, ein Release für Django 6.1 gibt es nicht.
  - S3 wird eine zweite Umsetzung der Schnittstelle, sobald ein Nutzer es braucht.
- Stufe C wegen Architektur (Ablage nach Prüfsumme, Volume).
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

1. **Ablage der Dateien**
   - (a) Inhaltsadressiert: Der Pfad wird aus der SHA-256 gebildet, gleicher Inhalt liegt nur einmal im Speicher, Versionen verweisen darauf.
   - (b) Je Version eine eigene Datei unter Gerät, Dokument und Versionsnummer.
   - Empfehlung: (a). Unveränderlich, Dubletten kosten keinen Platz, Pfade verraten keine Gerätenamen.
2. **S3 in M1?**
   - (a) Nein, nur das Volume; S3 bei Bedarf eines Nutzers (Startunterlage 5.4).
   - (b) Ja, mit django-storages trotz fehlender Erklärung für Django 6.1.
   - Empfehlung: (a).

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
