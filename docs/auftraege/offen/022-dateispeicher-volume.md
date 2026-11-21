# Auftrag 022 – Dateispeicher: Schnittstelle, atomare Ablage nach Prüfsumme, Volume

Meilenstein: M1 · Freigabestufe: C · Status: zur Prüfung

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

**Status: zur Prüfung.** Alle Akzeptanzkriterien erfüllt, Läufe am 21.11.2026 im Container. Keine offene Frage an a7.

**Was wurde gebaut?**

- `backend/twox/files/storage.py` (neu):
  - `BlobStorage` (`Protocol`) mit `store_blob(stream) -> StoredBlob`, `open_blob(key) -> IO[bytes]`, `blob_exists(key) -> bool`. `stream` ist ein schmales `ReadableStream`-Protokoll (nur `read(size)`), damit später auch Djangos Upload-Objekte passen.
  - `StoredBlob` (unveränderliche Dataclass: `key`, `sha256`, `size`).
  - Ausnahmen: `BlobStorageError` als Basis; `InvalidBlobKeyError` (auch `ValueError`), `BlobNotFoundError` (auch `LookupError`), `BlobConflictError`.
  - `FileSystemBlobStorage(root)`: `mkstemp` in `<root>/tmp/`, Lesen und Prüfsumme in Blöcken zu 1 MiB (`CHUNK_SIZE`), `fsync`, Rechte `0440`, dann `os.link` nach `sha256/ab/cd/<sha256>`. `os.link` ersetzt nie: Von zwei gleichzeitigen Schreibern legt genau einer den Eintrag an. Liegt der Schlüssel schon vor, wird die Größe verglichen (bei Abweichung `BlobConflictError`, die vorhandene Datei bleibt unberührt). Die temporäre Datei wird in `finally` immer entfernt.
  - Schlüsselprüfung mit `fullmatch` auf `sha256/[0-9a-f]{2}/[0-9a-f]{2}/[0-9a-f]{64}`; zusätzlich müssen die beiden Ordner die ersten vier Zeichen der Prüfsumme wiederholen. Nicht-Strings werden abgewiesen.
  - `get_blob_storage()` liefert `FileSystemBlobStorage(settings.TWOX_MEDIA_ROOT)`. Keine URLs, kein Löschen.
- `backend/tests/files/test_storage.py` (neu, 29 Fälle, eigene Fixture mit temporärem Wurzelverzeichnis): gleicher Inhalt gleicher Schlüssel und nur einmal geschrieben (Inode, mtime, Linkzahl unverändert); Prüfsumme gleich `hashlib`; leere Datei; 20 MB in Blöcken (jeder `read` höchstens `CHUNK_SIZE`); vier Threads mit gleichem Inhalt über eine `Barrier` ergeben einen Schlüssel und eine Datei mit richtigem Inhalt; abgebrochener Datenstrom und Fehler bei `os.link` hinterlassen nichts; Konflikt bei falscher Größe; 13 ungültige Schlüssel (u. a. `../x`, `sha256/zz/…`, Großbuchstaben, Zeilenende, `tmp/…`, falsche Ordner); unbekannter gültiger Schlüssel (`blob_exists` gibt `False`, `open_blob` `BlobNotFoundError`); `get_blob_storage` folgt `TWOX_MEDIA_ROOT`.
- `deploy/compose/compose.yaml`: Volume `media-data`, eingebunden unter `/data/media` in `api` und `worker`; `TWOX_MEDIA_ROOT` und `TWOX_UPLOAD_MAX_BYTES` im gemeinsamen Umgebungsblock (leer heißt Standard aus `settings.py`).
- `backend/Dockerfile`, Stufe `runtime`: `install -d -m 0750 -o twox -g twox /data/media`. `/app` bleibt root-eigen und schreibgeschützt.
- `.env.example`: beide Variablen mit Kommentar (`/data/media`, `200000000`).

**Wie wurde getestet?** `D` = `docker compose -p twox-022`, `.env` aus `.env.example` mit `TWOX_API_PORT=18022`, Docker Engine 29.9.3, Compose v5.7.0, auf dem committeten Stand.

| AK | Ergebnis |
| --- | --- |
| 0 | erfüllt: beide Befehle Exit 0 |
| 1 | erfüllt: Bau Exit 0; `up -d --wait`: db, valkey, api, worker `Healthy`, Exit 0 |
| 2 | erfüllt: `api` und `worker` je `10001`, `10001`, `writable` |
| 3 | erfüllt: `touch: cannot touch '/app/probe': Permission denied`, Exit 1 |
| 4 | erfüllt (Befehle unten): `api` gibt `sha256/b5/95/b595b214…03de b595b214b5d4865e79bd091744879680590d80e7656edd099474752aa09703de 2` und `b'2x'` aus; `worker` gibt `True` aus. Gegenprobe `hashlib.sha256(b'2x')` ergibt denselben Wert. Im Volume: `-r--r----- 10001 10001`, `tmp/` leer |
| 5 | erfüllt: `All checks passed!`; `72 files already formatted`, Exit 0; `Success: no issues found in 72 source files` |
| 6 | erfüllt: `213 passed, 4 deselected`, 0 fehlgeschlagen, 0 übersprungen; `pytest -m worker`: `4 passed` |
| 7 | erfüllt: `No changes detected` |
| 8 | erfüllt: Bau, `pull e2e`, `npm ci` Exit 0; `2 passed` |
| 9 | erfüllt: `down -v` Exit 0; danach weder Container noch Volume des Projekts `twox-022` (vorher auch `twox-022_media-data`) |

Zusätzlich wie im CI-Job `backend`: `sh scripts/check-licenses.sh` meldet `License check passed.` (53 Pakete); `spectacular --file /out/schema.yml` ohne Änderung an `web/openapi`.

Befehle zu Kriterium 4 (Python-Code jeweils als ein Argument von `-c`):

```
D exec api python manage.py shell -c "import io; from twox.files.storage import get_blob_storage as g; s = g(); b = s.store_blob(io.BytesIO(b'2x')); print(b.key, b.sha256, b.size); print(s.open_blob(b.key).read())"
D exec worker python manage.py shell -c "from twox.files.storage import get_blob_storage as g; print(g().blob_exists('sha256/b5/95/b595b214b5d4865e79bd091744879680590d80e7656edd099474752aa09703de'))"
```

**Zweig und Arbeitsverzeichnis:** Zweig `worktree-agent-a62b0f840248257be`, Arbeitsverzeichnis `.claude/worktrees/agent-a62b0f840248257be`.

**Abweichungen**

- Keine vom Umfang. Zusätzlich zum Auftrag: `BlobConflictError` für einen vorhandenen Schlüssel mit anderer Größe (der Auftrag sagt nur „Größe vergleichen"); Schlüssel müssen in den Ordnern die Prüfsumme wiederholen; abgelegte Dateien sind `0440`. Kein Rückfall für Dateisysteme ohne harte Links (`os.link`); das Docker-Volume unterstützt sie. Eine künftige Umsetzung auf solchen Dateisystemen oder S3 bräuchte einen eigenen Weg.
- Hinweis für die Doku (038): `TWOX_MEDIA_ROOT` muss zum Einhängepunkt des Volumes passen; die Compose-Datei hängt fest unter `/data/media` ein.