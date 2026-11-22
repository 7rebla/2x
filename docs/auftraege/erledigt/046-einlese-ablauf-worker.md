# Auftrag 046 – Einlese-Ablauf im Worker: Umwandeln, Abschnitte speichern

Meilenstein: M2 · Freigabestufe: B · Status: erledigt

## Ziel

Ein Einlese-Auftrag (`IngestJob`) läuft im Celery-Worker auf der Warteschlange `ingest` durch: Inhalt aus dem Speicher lesen, von Docling umwandeln lassen oder ein vorhandenes Ergebnis gleichen Inhalts wiederverwenden, die Docling-Antwort speichern, Abschnitte bilden und schreiben. Jeder Fehler endet als sichtbarer Status mit Fehlerart. Lange Umwandlungen blockieren keinen Worker-Prozess; ein Neustart von Docling führt zu neuem Einreichen statt zu einer falschen Meldung.

## Umfang

- `backend/twox/ingest/pipeline.py` (Logik, ohne Celery testbar) und `backend/twox/ingest/tasks.py` (dünne Celery-Hülle, Zeitlimits aus 045, `acks_late` und `reject_on_worker_lost` nur für die idempotenten Aufgaben).
- **`twox.ingest.convert(job_id)`**:
  - Unbekannte `job_id`: nichts tun, nur protokollieren (Warnung), Rückgabe ohne Ausnahme.
  - Auftrag nicht `queued`: nichts tun (Idempotenz).
  - Setzt `running`, Schritt `convert`, `started_at`.
  - **Wiederverwendung:** Gibt es einen Auftrag (gleiche oder andere Version) mit derselben Prüfsumme des Inhalts und gespeicherter Docling-Antwort (`result_blob_key`), dann Docling überspringen, `reused_from` und `result_blob_key` übernehmen und direkt zum Schritt `sections`.
  - Sonst Inhalt über `get_blob_storage().open_blob()` öffnen; `BlobNotFoundError` ergibt `failed`/`content_missing`.
  - Über `DocumentConverter.submit` mit neutralem Dateinamen `version-<id><endung>` und `document_timeout` aus `TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS` einreichen; `docling_task_id` merken; `poll` mit `countdown` einplanen.
- **`twox.ingest.poll(job_id)`**:
  - Fragt einmal ab und plant sich mit wachsendem Abstand neu ein (`TWOX_INGEST_POLL_MIN_SECONDS` bis `..._MAX_SECONDS`).
  - Beim ersten Status `started` wird `docling_started_at` gesetzt. Die Frist `TWOX_INGEST_TIMEOUT_SECONDS` zählt ab dort; die Wartezeit in der Docling-Warteschlange (`pending`) zählt nicht.
  - Bei Erfolg: `fetch` schreibt die Antwort in eine temporäre Datei, die sofort mit `store_blob` gespeichert wird (`result_blob_key`); erst danach wird sie über `load_result` ausgewertet (`page_count`).
- **Schritt `sections`**: `build_sections` (043) mit `TWOX_SECTION_MAX_CHARS`; in einer Transaktion die Abschnitte dieser Version ersetzen (`bulk_create` über `section_rows` aus 042) und `section_count` setzen. Danach `done` (den Schritt `embed` hängt 048 an).
- **Fehlerbehandlung:**
  - `DoclingUnavailableError`: neuer Versuch mit wachsendem Abstand bis `TWOX_INGEST_MAX_RETRIES`, dann `failed`/`docling_unavailable`.
  - `DoclingTaskLostError`: neu einreichen (zählt gegen `TWOX_INGEST_MAX_RETRIES`), danach `failed`/`docling_unavailable`.
  - `DoclingRejectedError`: sofort `failed`/`docling_rejected`.
  - `DoclingConversionError` und `UnsupportedDocumentError`: `failed`/`conversion_failed`.
  - Frist abgelaufen: `failed`/`timeout`.
  - Unerwartete Ausnahme: `failed`/`internal`, Einzelheiten nur ins Server-Protokoll.
  - `finished_at` wird immer gesetzt.
  - `error_detail` nur über `sanitize_error_detail()`: entfernt Pfade, URLs, IP- und MAC-Adressen und den Dateinamen, kürzt auf 2 000 Zeichen; der Rohtext geht nur ins Server-Protokoll.
- **Tests** (`backend/tests/ingest/test_pipeline.py`, `test_tasks_worker.py`):
  - Ablauf mit einer Attrappe von `DocumentConverter`, die die Testdaten aus 041 liefert: Abschnitte mit Seiten gespeichert, Status `done`, Zähler gesetzt, neutraler Dateiname gesendet.
  - Wiederverwendung: zweite Version mit gleichem Inhalt ruft Docling nicht auf, `reused_from` gesetzt.
  - Jeder Fehlerweg ergibt den erwarteten Status und die Fehlerart, darunter `content_missing` und `DoclingTaskLostError` → neu eingereicht.
  - Frist: eine Attrappe, die lange `pending` meldet, führt nicht zu `timeout`; lange `started` schon.
  - `sanitize_error_detail` mit einem Docling-Fehlertext, der einen Pfad, eine URL, eine IP und einen Dateinamen enthält.
  - Zweiter Aufruf von `convert` oder `poll` mit einem fertigen Auftrag ändert nichts; unbekannte `job_id` ergibt keine Ausnahme.
  - Erneutes Einlesen ersetzt die Abschnitte; während des Laufs bleiben die alten Abschnitte bis zum Ersetzen bestehen.
  - `pytest -m worker`: `convert` mit einer nicht vorhandenen `job_id` landet über den echten Worker in `ingest` und endet ohne Ausnahme (Ergebnis über den Ergebnisspeicher). Kein Test des Workers mit Datenbankzustand: der Worker liest die Hauptdatenbank, die Tests die Testdatenbank.

## Nicht-Ziele

- Kein Anstoß nach dem Upload und kein Verwaltungsbefehl (049).
- Keine Einbettungen (048), keine API (051).
- Keine Änderung an `twox/files/`, `settings.py` oder `compose.yaml`.

## Betroffene Bereiche (Ordner, Dateien)

- neu: `backend/twox/ingest/pipeline.py`, `backend/twox/ingest/tasks.py`
- neu: `backend/tests/ingest/test_pipeline.py`, `backend/tests/ingest/test_tasks_worker.py`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-046`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18046` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Tests:
   - `D run --rm backend-dev pytest tests/ingest -v` endet mit Exit-Code 0.
   - `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen.
   - `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0, einschließlich des neuen Tests.
3. `D run --rm backend-dev ruff check .` meldet `All checks passed!`, `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0, `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
4. Weitere Prüfungen wie in `ci.yml`, jeweils ohne Unterschied zum eingecheckten Stand:
   - `D run --rm backend-dev python manage.py makemessages -l de --add-location=file`, danach `git diff --exit-code -I '^"POT-Creation-Date:' -- backend/locale`;
   - `D run --rm backend-dev python manage.py makemigrations --check --dry-run` endet mit Exit-Code 0;
   - `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0;
   - `D run --rm -v "$PWD/web/openapi:/out" backend-dev python manage.py spectacular --file /out/schema.yml` (unter Git Bash mit vorangestelltem `MSYS_NO_PATHCONV=1`), danach `git diff --exit-code -- web/openapi`.
5. Lokal mit Docling, nicht in der CI: `D up -d --wait --wait-timeout 600 docling`. `testdata/klein/recht/BetrSichV.pdf` und die vier Markdown-Dateien aus `testdata/klein/opnsense/markdown/` über die API hochladen (wie README „Files“), dann mit `D exec -T api python manage.py shell -c '...'` je Version einen `IngestJob` anlegen und `convert` senden, alle gleichzeitig. Ergebnis: alle `done`, keiner `timeout`; BetrSichV mit 60 Seiten und Abschnitten mit Seiten 1 bis 60. Laufzeiten und Abschnittszahlen im Kurzbericht.
6. Lokal: Dieselbe PDF-Datei bei einem zweiten Gerät hochladen und anstoßen: Der Auftrag ist ohne Docling-Aufruf `done` (`reused_from` gesetzt, `D logs docling` zeigt keine zweite Umwandlung).
7. Lokal: `D restart docling` während einer laufenden Umwandlung: Der Auftrag endet `done` oder nach den Wiederholungen mit `failed`/`docling_unavailable`, nie mit `docling_rejected`.
8. Lokal: Mit gestopptem Docling (`D stop docling`) endet ein Auftrag nach den Wiederholungen mit `failed`/`docling_unavailable`. Der Worker bleibt für `default` ansprechbar: `D exec -T api python manage.py shell -c 'from twox.config.taskqueue import ping_worker; print(ping_worker(10))'` liefert ein Ergebnis.
9. Abräumen: `D --profile dev down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

- **Nachtrag der Leitstelle (E-59, KI optional):** Einbettungen, Vektorsuche und alles, was ein Modell braucht, sind eine aktivierbare Zusatzfunktion. Schalter `TWOX_AI_ENABLED` (Einstellung in `settings.py`, Standard `False`; `.env.example` mit Kommentar). Bei „aus“: kein Aufruf von Ollama, keine Einbettungs-Aufgaben, Einlesen endet nach den Abschnitten erfolgreich, die Suche arbeitet nur mit der Stichwortsuche, Selbsttest und Oberfläche zeigen „KI nicht aktiviert“ als neutralen Zustand (kein Fehler, kein Warnsymbol). Jede KI-abhängige Stelle braucht einen Test für beide Zustände; die CI läuft mit „aus“ und mit „an“ plus Attrappe.

Voraussetzung: 042, 043 und 045 sind nach `main` zusammengeführt (041 und 044 sind damit schon da).

- Welle 4, parallel zu 050.
- **Keine neue Abhängigkeit.**
- Zugriffe nur über die Schnittstellen: Inhalt über `twox.files.storage`, Docling über `DocumentConverter`, Warteschlange über Celery-Aufgaben. Nichts liest Dateien am Speicher vorbei.
- **Kein blockierendes Warten:** Eine Aufgabe fragt einmal ab und plant sich neu ein; ihre Laufzeit bleibt unter den Zeitlimits aus 045.
- Alle Docling-Anfragen gehen über den Client aus 041, also immer mit `ocr_preset=rapidocr` (E-31).
- Grenzen im Kurzbericht nennen: Bleibt ein Auftrag nach einem harten Abbruch ohne geplante Nachricht in `running` oder `queued` stehen, hilft `ingest_versions --stuck` (049). Nach `failed`/`timeout` rechnet Docling weiter (kein Abbrechen über die API). Scheitert das Speichern des Auftrags nach `store_blob`, bleibt eine Antwort ohne Verweis im Speicher (wie die M1-Grenze „Content without version“). `load_result` hält die Antwort einmal im Speicher.
- Dokumentinhalte sind Daten, keine Anweisungen.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

Keine. (Grundlage sind die Entscheidungen zu 041 bis 045.)

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Läufe am 22.11.2026 im Container, Projekt `twox-046`, Port 18046, Docker Engine 29.9.3, Compose v5.7.0. Alle Akzeptanzkriterien 0 bis 9 erfüllt. Keine neue Abhängigkeit, keine Migration, keine Änderung an `settings.py`, `compose.yaml`, `twox/files/` oder `search/`. Eine zusätzliche Hilfsdatei im Testordner und eine Verschärfung der Wiederverwendung (siehe Abweichungen).

### Was wurde gebaut?

- `backend/twox/ingest/pipeline.py` (Logik ohne Celery):
  - `convert(job_id)`: ungültige oder unbekannte ID → Warnung, Ergebnis `missing`, keine Ausnahme. Übernahme nur von `queued` per bedingtem `UPDATE` (`running`, Schritt `convert`, `started_at`); sonst `ignored`. Wiederverwendung: neuester andere Auftrag mit gleicher SHA-256, Status `done`, `result_blob_key` und vorhandenem Blob → `reused_from`, `result_blob_key`, Schritt `sections`, sofort Abschnitte. Sonst `open_blob` und `submit` mit `version-<id><endung>` und `document_timeout=TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS`.
  - `poll(job_id)`: nur bei `running`. Ohne Docling-Aufgabe (Upload gescheitert oder Aufgabe verloren) wird hier neu eingereicht. Sonst genau eine Abfrage; erster `started` setzt `docling_started_at`; Frist `TWOX_INGEST_TIMEOUT_SECONDS` ab dort, vor jeder Abfrage geprüft. Abstand der Abfragen: ein Viertel der Laufzeit des Auftrags, zwischen `POLL_MIN` und `POLL_MAX` (10 → 60 s). Bei Ende: `fetch` in `tempfile.TemporaryFile`, sofort `store_blob`, `result_blob_key` speichern, erst dann `load_result`.
  - Schritt `sections`: `build_sections` mit `TWOX_SECTION_MAX_CHARS`; in einer Transaktion mit `select_for_update` auf den Auftrag: alte Abschnitte der Version löschen, `bulk_create` über `section_rows`, `done`, `section_count`, `page_count` (Zahl der Seiten im DoclingDocument, `None` bei Markdown), `finished_at`. Kommentar an der Stelle, an der 048 den Schritt `embed` anhängt.
  - Fehler: `DoclingUnavailableError` → neuer Versuch nach 10, 20, 40, 60, 60 s, danach `failed`/`docling_unavailable`; `DoclingTaskLostError` → Aufgabe vergessen und neu einreichen, zählt mit; `DoclingRejectedError` → sofort `docling_rejected`; `DoclingConversionError`, `UnsupportedDocumentError` → `conversion_failed` (bei Status `failure`/`skipped` mit den Fehlertexten aus der Docling-Antwort); `BlobNotFoundError` → `content_missing`; Frist → `timeout`; `SoftTimeLimitExceeded` → `timeout`; alles andere → `internal` mit festem Text, Einzelheiten nur per `logger.exception`. `finished_at` immer gesetzt. Zähler der Versuche ist `attempts` (über den ganzen Auftrag, nicht je Schritt).
  - `sanitize_error_detail(text, filenames=...)`: entfernt Dateiname (auch letzter Pfadteil und Stamm ab 4 Zeichen), URLs, Windows-, UNC- und POSIX-Pfade, MAC- (drei Schreibweisen), IPv6- (über `ipaddress` geprüft, damit Uhrzeiten bleiben) und IPv4-Adressen, Steuerzeichen; kürzt auf 2 000 Zeichen. Rohtext geht per `logger.warning` ins Server-Protokoll.
  - `partial_success` endet `done`; `error_detail` enthält dann einen Hinweis wie „converted with 1 errors on pages 3“.
- `backend/twox/ingest/tasks.py`: `twox.ingest.convert` und `twox.ingest.poll` mit `acks_late=True`, `reject_on_worker_lost=True`, `soft_time_limit`/`time_limit` aus 045 (300/360). Die Aufgabe plant `poll` mit `countdown` neu ein und liefert das Ergebnis als Text (`missing`, `ignored`, `polling`, `done`, `failed`).
- Tests:
  - `backend/tests/ingest/fake_converter.py` (neu, Hilfsdatei): `FakeConverter` mit den echten Docling-Ergebnissen aus 041, `NoDocling`, Fixture `isolated_services` (eigener Blob-Speicher, Docling- und Ollama-Adresse ins Leere, `get_document_converter` und `get_embedder` lassen jeden Test scheitern, der sie erreicht).
  - `test_pipeline.py` (44 Testfunktionen, 56 Fälle): ganzer Ablauf PDF (Abschnitte mit Seiten 1–5, Zähler, Zeiten) und Markdown (ohne Seiten); neutraler Name und gesendeter Inhalt; Antwort gespeichert; Wiederverwendung (anderes Gerät, neue Version, fehlender Blob, gescheiterter Auftrag); `content_missing`; Unavailable mit wachsendem Abstand bis `failed`; Unavailable mit Erholung; TaskLost beim Abfragen und beim Abholen → neu eingereicht; TaskLost dauerhaft → `docling_unavailable`, nie `docling_rejected`; Rejected; Docling-Fehlerantwort mit Pfad, URL, IP und Dateiname bereinigt; `skipped`; Antwort ohne Dokument; unbekanntes Schema; `partial_success`; unerwartete Ausnahme nur im Protokoll; weiche Zeitgrenze; Frist (`pending` lange ohne `timeout`, `started` lange mit `timeout`, erster Start gemerkt); Idempotenz (zweites `convert`/`poll` auf `done`/`failed`/`running`/`queued`, wiederholte Nachricht nach Absturz baut aus dem gespeicherten Ergebnis); unbekannte und ungültige IDs; erneutes Einlesen ersetzt die Abschnitte erst am Ende; `sanitize_error_detail`; beide Zustände von `TWOX_AI_ENABLED`.
  - `test_tasks_worker.py`: Namen, Route `ingest`, `acks_late`/`reject_on_worker_lost`/Zeitlimits, Celerys `Request.on_failure` mit `WorkerLostError` legt die Nachricht zurück (`requeue=True`); Aufgabenkette im Prozess bis `done` für KI an und aus ohne weitere Nachricht an den Broker; unbekannte ID; `pytest -m worker`: `convert` mit unbekannter ID über den echten Worker → `missing` aus dem Ergebnisspeicher.

### Wie wurde getestet?

`D` = `docker compose -p twox-046`, `.env` aus `.env.example` (ohne BOM) mit `TWOX_API_PORT=18046`, also KI an.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | Engine 29.9.3, Compose v5.7.0, Exit 0 |
| 1 | erfüllt | Bau Exit 0 (zweimal, zuletzt mit dem neuen Code); `up -d --wait …` Exit 0, alle `Healthy` |
| 2 | erfüllt | `pytest tests/ingest`: `322 passed, 1 deselected`; `pytest`: `1852 passed, 6 deselected`, mit `-rs` nichts übersprungen; `pytest -m worker`: `6 passed` (einschließlich des neuen Tests). Zusätzlich mit `-e TWOX_AI_ENABLED=false`: `pytest tests/ingest tests/config/test_celery.py` `343 passed` |
| 3 | erfüllt | `All checks passed!`; `162 files already formatted`; `Success: no issues found in 161 source files` |
| 4 | erfüllt | `makemessages` ohne Unterschied in `backend/locale`; `No changes detected`; `License check passed.`; `spectacular` ohne Unterschied in `web/openapi` |
| 5 | erfüllt | siehe unten |
| 6 | erfüllt | Auftrag 6 (BetrSichV.pdf an Gerät 2): `done` in 0,22 s, `reused_from` 1, 60 Seiten, 140 Abschnitte; `D logs docling` zählt weiter 5 Einreichungen (`POST /v1/convert/file/async`), keine sechste |
| 7 | erfüllt | Auftrag 7 (veränderte Kopie, siehe unten): `D restart docling` 80 s nach dem Einreichen. Protokoll: `retry 1 of 5 after: docling-serve refused the connection`, `retry 2 of 5 after: docling-serve does not know the task`, neu eingereicht, `done` mit 60 Seiten und 140 Abschnitten, `attempts` 2; kein `docling_rejected` |
| 8 | erfüllt | `D stop docling`, Auftrag 8: nach 5 Wiederholungen (≈ 3,5 min) `failed`/`docling_unavailable`, Detail `the host name of docling-serve does not resolve (gave up after 5 retries)`. `ping_worker(10)` liefert `pong` während des Laufs und danach |
| 9 | erfüllt | `D --profile dev down -v` Exit 0; keine Container und Volumes `twox-046*` mehr |

Kriterium 5: fünf Uploads über die Datei-API (`POST /api/v1/devices/<id>/documents/`, jeweils 201), dann fünf `IngestJob` und fünf `convert.delay` unmittelbar hintereinander:

| Auftrag | Datei | Status | Seiten | Abschnitte | Seiten der Abschnitte | Laufzeit |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | BetrSichV.pdf | done | 60 | 140 | 1–60 | 291,7 s (Docling: 257,8 s) |
| 2 | backups.md | done | – | 4 | – | 291,5 s |
| 3 | firewall_groups.md | done | – | 2 | – | 291,5 s |
| 4 | sftp-backup.md | done | – | 4 | – | 291,5 s |
| 5 | updates.md | done | – | 4 | – | 291,4 s |

Keiner `timeout`, `attempts` überall 0. Docling hat einen lokalen Worker (E-55): Die Markdown-Dateien warteten in Docling hinter der PDF und waren dann in je unter 0,2 s umgewandelt; die Laufzeit ab `started_at` enthält diese Wartezeit, die Frist nicht.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-af2861b16f105df85`
- Arbeitsverzeichnis: `.claude/worktrees/agent-af2861b16f105df85` (relativ zum Projektordner)
- Commits: `Run ingest jobs in the worker: convert, poll, reuse, sections`, `Test the ingest flow and its tasks with a stand-in converter`, dazu dieser Kurzbericht. Nicht gepusht, nichts zusammengeführt.

### Abweichungen und Hinweise

1. **Wiederverwendung nur von `done`-Aufträgen.** Der Auftrag nennt nur „gespeicherte Docling-Antwort“. Ein Auftrag, dessen gespeicherte Antwort beim Lesen scheiterte (`conversion_failed` im Schritt `sections`), hat ebenfalls einen `result_blob_key`; würde er wiederverwendet, bekäme derselbe Inhalt nie wieder eine Chance bei Docling. Antworten von Fehlerstatus (`failure`, `skipped`) werden gar nicht gespeichert, nur gelesen.
2. **Zusätzliche Datei `backend/tests/ingest/fake_converter.py`** (Attrappe und Hilfen für beide Testdateien), wie `fake_docling.py` in 041.
3. **Uploads für Kriterium 5 bis 8** liefen über die echten API-Views mit Djangos Testclient im `api`-Container (angemeldet mit `force_login` als Konto mit Rolle `manage`, ohne Kennwort), nicht über einen Socket. Für 7 und 8 brauchte es Inhalte, die Docling noch nicht kannte (sonst greift die Wiederverwendung): zwei Kopien von `BetrSichV.pdf` mit angehängter Kommentarzeile, nur im Container erzeugt, nicht eingecheckt.
4. **`page_count` ist `None` bei Formaten ohne Seiten** (Markdown), wie `page_start`/`page_end` der Abschnitte.
5. **`partial_success` endet `done`** mit Hinweis in `error_detail` (Zahl der Fehler, Seiten). Falls die Oberfläche `error_detail` nur bei `failed` zeigen soll, bitte in 051/053 berücksichtigen.
6. **Beobachtung zu `tests/config/test_worker.py` (045):** Im ersten Gesamtlauf schlug `test_running_worker_consumes_the_configured_queues_with_four_processes` fehl, weil gleichzeitig Einlese-Aufträge liefen: Celery erhöht `prefetch_count` für reservierte Nachrichten mit Countdown, die Prüfung auf genau 4 stimmt dann nicht. Ohne laufende Aufträge grün (`6 passed`). In der CI laufen keine Aufträge; bei lokalen Läufen mit aktivem Einlesen tritt es wieder auf. Vorschlag für einen späteren Auftrag: dort `prefetch_count >= 4` oder die Prüfung über `pool.max-concurrency` allein.
7. **e2e nicht gelaufen:** Compose und Worker-Start sind unverändert; der Worker registriert nur zwei Aufgaben mehr.

Grenzen (wie im Auftrag vorgegeben, dazu eigene):

- Bleibt ein Auftrag nach einem harten Abbruch ohne geplante Nachricht in `running` oder `queued` stehen (z. B. Absturz zwischen Übernahme und Einreichen in `convert`, Broker beim Neueinplanen nicht erreichbar, Datenbank weg beim Schreiben von `failed`), hilft erst `ingest_versions --stuck` (049). `convert` auf einen `running` Auftrag tut absichtlich nichts.
- Nach `failed`/`timeout` rechnet Docling weiter (kein Abbrechen über die API); ebenso die verwaiste Aufgabe nach einem Neueinreichen.
- Scheitert das Speichern des Auftrags nach `store_blob`, bleibt eine Antwort ohne Verweis im Speicher (wie die M1-Grenze „Content without version“).
- `load_result` hält die Antwort einmal im Speicher; `build_sections` und die Abschnittszeilen ebenso.
- `reject_on_worker_lost`: Stirbt ein Prozess immer wieder an derselben Nachricht (z. B. Speichermangel beim Lesen einer riesigen Antwort), wird sie immer wieder eingereiht. Die harte Zeitgrenze bestätigt dagegen die Nachricht (`acks_on_timeout`), dort gibt es keine Schleife.
- Doppelte Nachrichten (z. B. von Hand erneut gesendet) führen zu parallelen Abfrageketten; sie enden gemeinsam, weil der letzte Schritt den Auftrag sperrt, kosten aber zusätzliche Abfragen und zählen Versuche doppelt.
- Der Zähler `attempts` gilt für den ganzen Auftrag; viele kurze Ausfälle während einer sehr langen Umwandlung können ihn aufbrauchen.

Keine offene Frage an a7.
