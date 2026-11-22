# Auftrag 045 – Celery und Einlese-Einstellungen für lange Aufträge

Meilenstein: M2 · Freigabestufe: C · Status: zur Prüfung

## Ziel

Celery und die Einstellungen des Einlesens sind für lange Aufträge vorbereitet: Routen je Warteschlange, Prefetch, Zeitlimits unter dem `visibility_timeout`, weiches Herunterfahren, Worker-Prozesse, Fristen und Abschnittsgröße. Alle Werte stehen an einer Stelle und werden beim Start auf Stimmigkeit geprüft. So berühren die Ablauf-Aufträge (046, 048) weder `settings.py` noch `compose.yaml`.

## Umfang

- `backend/twox/config/settings.py`, Celery-Abschnitt:
  - `CELERY_TASK_ROUTES`: `twox.ingest.convert` und `twox.ingest.poll` → `ingest`, `twox.ingest.embed` → `embed`.
  - `CELERY_WORKER_PREFETCH_MULTIPLIER = 1`.
  - `CELERY_BROKER_TRANSPORT_OPTIONS` mit ausdrücklichem `visibility_timeout` (3 600 s, Vorgabe des Redis-Transports).
  - `CELERY_WORKER_SOFT_SHUTDOWN_TIMEOUT` größer 0.
  - Konstanten `TWOX_TASK_SOFT_TIME_LIMIT` und `TWOX_TASK_TIME_LIMIT` für die Einlese-Aufgaben (Vorschlag 300 und 360 s), deutlich unter dem `visibility_timeout`.
- Einlese-Einstellungen (Umgebungsvariablen mit Vorgabe):
  - `TWOX_INGEST_MAX_RETRIES` (5);
  - `TWOX_INGEST_POLL_MIN_SECONDS` (10), `TWOX_INGEST_POLL_MAX_SECONDS` (60);
  - `TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS` (7 200; wird je Anfrage als `document_timeout` geschickt, höchstens die Grenze des Docling-Dienstes aus 041);
  - `TWOX_INGEST_TIMEOUT_SECONDS` (9 000; zählt erst ab dem Status `started` bei Docling, nicht während der Wartezeit in der Docling-Warteschlange);
  - `TWOX_SECTION_MAX_CHARS` (2 000);
  - `TWOX_EMBED_TASK_MAX_SECONDS` (240; so lange bettet eine Aufgabe höchstens ein, dann plant sie sich für den Rest neu ein, 048).
- Prüfung beim Start (eigene Funktion mit Test): alle Werte ganze Zahlen größer 0; `TWOX_INGEST_TIMEOUT_SECONDS` > `TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS`; `TWOX_EMBED_TASK_MAX_SECONDS` < `TWOX_TASK_SOFT_TIME_LIMIT` < `TWOX_TASK_TIME_LIMIT` < `visibility_timeout`; `POLL_MIN` ≤ `POLL_MAX`.
- `deploy/compose/compose.yaml`: Dienst `worker` mit `--concurrency` nach Frage 1; neue Variablen in `x-backend-environment`. Neue Variablen in `.env.example`.
- Tests: `backend/tests/config/test_celery.py` (Routen über den Router von Celery, Prefetch, Zeitlimits), `backend/tests/config/test_settings.py` (Prüfung beim Start, jede verletzte Bedingung einzeln).

## Nicht-Ziele

- Keine Aufgaben und kein Ablauf (046, 048).
- Kein Celery beat, keine periodischen Aufgaben.
- Kein eigener Worker-Dienst je Warteschlange (Frage 1, Option b).

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/config/settings.py` (Celery-Abschnitt, `TWOX_INGEST_*`, `TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS`, `TWOX_SECTION_MAX_CHARS`, `TWOX_EMBED_TASK_MAX_SECONDS`)
- `deploy/compose/compose.yaml` (Dienst `worker`, `x-backend-environment`), `.env.example`
- `backend/tests/config/test_celery.py`, `backend/tests/config/test_settings.py`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-045`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18045` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Tests:
   - `D run --rm backend-dev pytest tests/config -v` endet mit Exit-Code 0.
   - `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen.
   - `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
3. `D run --rm backend-dev ruff check .` meldet `All checks passed!`, `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0, `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
4. Weitere Prüfungen wie in `ci.yml`, jeweils ohne Unterschied zum eingecheckten Stand:
   - `D run --rm backend-dev python manage.py makemessages -l de --add-location=file`, danach `git diff --exit-code -I '^"POT-Creation-Date:' -- backend/locale`;
   - `D run --rm backend-dev python manage.py makemigrations --check --dry-run` endet mit Exit-Code 0;
   - `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0;
   - `D run --rm -v "$PWD/web/openapi:/out" backend-dev python manage.py spectacular --file /out/schema.yml` (unter Git Bash mit vorangestelltem `MSYS_NO_PATHCONV=1`), danach `git diff --exit-code -- web/openapi`.
5. `D exec -T worker celery -A twox.config inspect active_queues` nennt `ingest`, `embed` und `default`; `D exec -T worker celery -A twox.config inspect stats` zeigt die eingestellte Zahl an Prozessen.
6. Mit `D run --rm -e TWOX_INGEST_TIMEOUT_SECONDS=60 backend-dev python manage.py check` endet der Befehl mit einer klaren Fehlermeldung (Frist kleiner als `document_timeout`) und Exit-Code ungleich 0.
7. Der Kurzbericht enthält eine Tabelle aller Zeitwerte (Celery, Einlesen, Docling-Grenze aus 041) mit Begründung.
8. Abräumen: `D --profile dev down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

- **Nachtrag der Leitstelle (E-59, KI optional):** Einbettungen, Vektorsuche und alles, was ein Modell braucht, sind eine aktivierbare Zusatzfunktion. Schalter `TWOX_AI_ENABLED` (Einstellung in `settings.py`, Standard `False`; `.env.example` mit Kommentar). Bei „aus“: kein Aufruf von Ollama, keine Einbettungs-Aufgaben, Einlesen endet nach den Abschnitten erfolgreich, die Suche arbeitet nur mit der Stichwortsuche, Selbsttest und Oberfläche zeigen „KI nicht aktiviert“ als neutralen Zustand (kein Fehler, kein Warnsymbol). Jede KI-abhängige Stelle braucht einen Test für beide Zustände; die CI läuft mit „aus“ und mit „an“ plus Attrappe.

Voraussetzung: 044 ist nach `main` zusammengeführt (dieselben Dateien `settings.py`, `compose.yaml`, `.env.example`).

- Welle 3, parallel zu 047.
- **Keine neue Abhängigkeit.** Reine Konfiguration im Rahmen von E-29.
- `acks_late` und `reject_on_worker_lost` setzen erst die Aufgaben selbst (046, 048), weil sie nur für idempotente Aufgaben gelten.
- Laut Celery-Doku liefert der Redis-Transport eine Nachricht nach dem `visibility_timeout` erneut aus, wenn sie nicht bestätigt ist; deshalb laufen keine Aufgaben, die länger brauchen, und `worker_soft_shutdown_timeout` > 0 wird empfohlen.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

1. **Worker-Prozesse (Vormerkung aus 008).**
   - (a) ein Worker-Dienst für alle drei Warteschlangen, `--concurrency 4`, Prefetch 1;
   - (b) eigener Dienst `worker-ingest` (nur `ingest`) neben `worker` (`embed`, `default`);
   - (c) Celery-Vorgabe (ein Prozess je Kern, hier 16).
   Empfehlung: (a). Die Rechenlast liegt in Docling und Ollama; die Aufgaben fragen nur kurz ab und planen sich neu ein, kein Prozess wartet lange. (b) ist später nur eine andere `--queues`-Liste.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Akzeptanzkriterien sind erfüllt; die Läufe fanden am 22.11.2026 im Container statt. Keine neue Abhängigkeit. Zwei Festlegungen über den Wortlaut hinaus (Warteschlange `embed` nur bei KI an; `REMAP_SIGTERM` und `stop_grace_period` am Worker) stehen unter „Abweichungen“ zur Entscheidung.

### Was wurde gebaut?

- `backend/twox/config/settings.py`, Celery-Abschnitt:
  - `CELERY_TASK_ROUTES`: `twox.ingest.convert` und `twox.ingest.poll` → `ingest`, `twox.ingest.embed` → `embed`; alles andere weiter `default`.
  - `CELERY_WORKER_PREFETCH_MULTIPLIER = 1`.
  - `TWOX_BROKER_VISIBILITY_TIMEOUT_SECONDS = 3600`, `CELERY_BROKER_TRANSPORT_OPTIONS = {"visibility_timeout": 3600}`.
  - Konstanten `TWOX_TASK_SOFT_TIME_LIMIT = 300`, `TWOX_TASK_TIME_LIMIT = 360`; zusätzlich als `CELERY_TASK_SOFT_TIME_LIMIT`/`CELERY_TASK_TIME_LIMIT` für alle Aufgaben gesetzt (Sicherheitsnetz: keine Aufgabe überlebt den `visibility_timeout`; einzelne Aufgaben können kürzere Werte setzen).
  - `CELERY_WORKER_SOFT_SHUTDOWN_TIMEOUT = 60.0`.
  - `task_queues(ai_enabled)`: `CELERY_TASK_QUEUES` ist `ingest`, `embed`, `default` bei KI an und nur `ingest`, `default` bei KI aus (E-59, siehe Abweichungen).
- Einlese-Einstellungen (Umgebungsvariable, Vorgabe): `TWOX_INGEST_MAX_RETRIES` (5), `TWOX_INGEST_POLL_MIN_SECONDS` (10), `TWOX_INGEST_POLL_MAX_SECONDS` (60), `TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS` (7 200), `TWOX_INGEST_TIMEOUT_SECONDS` (9 000), `TWOX_SECTION_MAX_CHARS` (2 000), `TWOX_EMBED_TASK_MAX_SECONDS` (240). Dazu die Konstante `TWOX_DOCLING_MAX_DOCUMENT_TIMEOUT_SECONDS = 7200` (Grenze des Docling-Dienstes).
- Prüfung beim Start: `check_ingest_timing(...)` (nur Schlüsselwort-Argumente), am Ende von `settings.py` aufgerufen; eine Verletzung wirft `ImproperlyConfigured` mit beiden Namen und Werten und stoppt API, Worker und jeden `manage.py`-Befehl. Geprüft: alle Werte ganze Zahlen > 0 (auch `bool` abgewiesen); `DOCLING_DOCUMENT_TIMEOUT` ≤ Docling-Grenze; `INGEST_TIMEOUT` > `DOCLING_DOCUMENT_TIMEOUT`; `POLL_MIN` ≤ `POLL_MAX`; `POLL_MAX` < `visibility_timeout` (zusätzlich, siehe unten); `EMBED_TASK_MAX` < `TASK_SOFT_TIME_LIMIT` < `TASK_TIME_LIMIT` < `visibility_timeout`.
- `deploy/compose/compose.yaml`: sieben neue Variablen in `x-backend-environment`; Dienst `worker` mit `--concurrency 4`, ohne `--queues` (verbraucht alle Warteschlangen aus `CELERY_TASK_QUEUES`), `REMAP_SIGTERM: SIGQUIT` nur am Worker, `stop_grace_period: 90s`.
- `.env.example`: die sieben Variablen mit Kommentar.
- Tests:
  - `backend/tests/config/test_celery.py`: Routen über `celery_app.amqp.router` (in frischem Interpreter je Zustand KI an/aus), `embed` bei KI aus → `QueueNotFound`, `task_routes`, Prefetch, `visibility_timeout`, Zeitlimits, weiches Herunterfahren; `test_three_queues_are_configured` ersetzt durch `test_queues_match_the_ai_switch`.
  - `backend/tests/config/test_settings.py`: Vorgaben, Übernahme aus der Umgebung, ungültige Zahlen je Variable, Startabbruch bei `TWOX_INGEST_TIMEOUT_SECONDS=60` und `TWOX_EMBED_TASK_MAX_SECONDS=300`; `check_ingest_timing` mit gültigen Werten, mit gleichen Abfragegrenzen und jede Bedingung einzeln verletzt (7 Fälle) sowie jeder Wert einzeln ungültig (10 Namen × 5 Werte).
  - `backend/tests/config/test_worker.py` (Markierung `worker`): Rundweg je konfigurierter Warteschlange statt fester Liste; neu: laufender Worker verbraucht genau die konfigurierten Warteschlangen, `max-concurrency` 4, `prefetch_count` 4.

### Zeitwerte mit Begründung (Kriterium 7)

| Wert | Größe | Begründung |
| --- | --- | --- |
| `visibility_timeout` (Redis-Transport) | 3 600 s | Vorgabe von Celery, ausdrücklich gesetzt. Größte Grenze: keine Aufgabe und kein Countdown darf ihn erreichen, sonst liefert Valkey die Nachricht doppelt aus |
| `TWOX_TASK_TIME_LIMIT` / `CELERY_TASK_TIME_LIMIT` | 360 s | harte Grenze je Aufgabe, ein Zehntel des `visibility_timeout`; Prozess wird ersetzt |
| `TWOX_TASK_SOFT_TIME_LIMIT` / `CELERY_TASK_SOFT_TIME_LIMIT` | 300 s | 60 s vor der harten Grenze: Zeit zum Aufräumen und Neueinplanen |
| `TWOX_EMBED_TASK_MAX_SECONDS` | 240 s | Einbettungs-Aufgabe hört rechtzeitig vor der weichen Grenze auf; 60 s Puffer für einen laufenden Stapel (Socket-Zeitlimit je Anfrage 120 s aus 044 – siehe offene Frage 2) |
| `CELERY_WORKER_SOFT_SHUTDOWN_TIMEOUT` | 60 s | Abfragen und Senden an Docling enden darin; längere Aufgaben werden abgebrochen und sofort wieder eingereiht statt nach 1 h |
| `stop_grace_period` (Worker) | 90 s | länger als das weiche Herunterfahren, sonst tötet Docker den Worker vorher |
| `TWOX_INGEST_POLL_MIN_SECONDS` / `_MAX_SECONDS` | 10 s / 60 s | Docling braucht ~5 s je Seite (041); bei kurzen Dokumenten schnelle Rückmeldung, bei langen höchstens eine Abfrage je Minute. Countdown < `visibility_timeout` |
| `TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS` | 7 200 s | E-55: 2 h je Dokument, gleich `DOCLING_SERVE_MAX_DOCUMENT_TIMEOUT`; darf nur kleiner gestellt werden |
| Docling-Grenze (`DOCLING_SERVE_MAX_DOCUMENT_TIMEOUT`, `DEFAULT_DOCUMENT_TIMEOUT_SECONDS` in `docling.py`, `TWOX_DOCLING_MAX_DOCUMENT_TIMEOUT_SECONDS`) | 7 200 s | aus 041/E-55; nach 057 ggf. anheben (2 000 Seiten × 5 s ≈ 2,8 h) |
| `TWOX_INGEST_TIMEOUT_SECONDS` | 9 000 s | 2,5 h ab Status `started`: 30 min über `document_timeout`, damit Docling seinen eigenen Fehler zuerst meldet; Wartezeit in der Docling-Warteschlange zählt nicht |
| `TWOX_INGEST_MAX_RETRIES` | 5 | vorübergehende Fehler (Docling, Ollama nicht erreichbar) |
| Selbsttest (010/017) | 5 s | unverändert |

### Wie wurde getestet?

`D` = `docker compose -p twox-045` im Wurzelverzeichnis des Arbeitsverzeichnisses, `.env` aus `.env.example` mit `TWOX_API_PORT=18045`, Docker Engine 29.9.3, Compose v5.7.0.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version` 29.9.3, `docker compose version` v5.7.0, beide Exit-Code 0 |
| 1 | erfüllt | Build Exit-Code 0; `up -d --wait`: `migrate-1 Exited`, `db`, `valkey`, `api`, `worker` `Healthy`, Exit-Code 0 |
| 2 | erfüllt | `pytest tests/config`: `339 passed, 5 deselected`, Exit 0. `pytest` (KI an, aus `.env`): `1613 passed, 5 deselected`, Exit 0, nichts übersprungen. Zusätzlich mit `TWOX_AI_ENABLED=false`: `1612 passed, 4 deselected`, Exit 0. `pytest -m worker`: `5 passed` (KI an), `4 passed` (KI aus, Worker mit KI aus neu gestartet) |
| 3 | erfüllt | `All checks passed!`; `151 files already formatted`, Exit 0; `Success: no issues found in 150 source files` |
| 4 | erfüllt | `makemessages` + `git diff … backend/locale` Exit 0; `makemigrations --check --dry-run`: `No changes detected`; `License check passed.`; `spectacular` + `git diff -- web/openapi` Exit 0 |
| 5 | erfüllt | `inspect active_queues`: `default`, `embed`, `ingest`; `inspect stats`: `max-concurrency` 4, 4 Einträge in `pool.processes`, `prefetch_count` 4. Mit KI aus: nur `default`, `ingest` |
| 6 | erfüllt | `django.core.exceptions.ImproperlyConfigured: TWOX_INGEST_TIMEOUT_SECONDS (60) must be greater than TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS (7200), the document_timeout sent to Docling; …`, Exit-Code 1 (Traceback davor, Meldung in der letzten Zeile) |
| 7 | erfüllt | Tabelle oben |
| 8 | erfüllt | `D --profile dev --profile e2e down -v` und `D --profile dev down -v` Exit 0; keine Container und Volumes von `twox-045` mehr |

Zusätzlich: e2e wie in `ci.yml` (Worker-Start geändert): Testkonto angelegt, Playwright `41 passed`. `D stop worker` dauerte 3 s, Protokoll `worker: Cold shutdown (MainProcess)`, Exit 0 – SIGTERM löst also den kalten Ablauf mit weichem Herunterfahren aus. **Nicht geprüft:** das Warten von 60 s mit einer laufenden Aufgabe, weil es noch keine lange Aufgabe gibt (046/048). `git status` nach den Läufen sauber. Die Testumgebung „2x“ und „twox-leit“ sind nicht berührt.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-af8c7bf3d2030762b`
- Arbeitsverzeichnis: `.claude/worktrees/agent-af8c7bf3d2030762b` (relativ zum Projektordner)

### Abweichungen und Hinweise

1. **Warteschlange `embed` nur bei KI an (E-59, Nachtrag).** Die Aufgaben gibt es erst in 048; damit bei „aus“ keine Einbettungs-Aufgabe eingeplant werden kann, fehlt dann die Warteschlange `embed`. Wegen `CELERY_TASK_CREATE_MISSING_QUEUES = False` scheitert das Einplanen sofort mit `QueueNotFound` statt eine Nachricht liegen zu lassen. Der Worker startet deshalb ohne `--queues`. 048 prüft den Schalter trotzdem selbst vor dem Einplanen. Kriterium 5 nennt `embed`, weil `.env.example` KI an hat; mit KI aus fehlt `embed` absichtlich.
2. **`REMAP_SIGTERM: SIGQUIT` und `stop_grace_period: 90s` am Worker.** Laut Celery 5.7.0 (`celery/apps/worker.py`, `celery/worker/worker.py`) wirkt `worker_soft_shutdown_timeout` nur beim kalten Herunterfahren (SIGQUIT). `docker stop` schickt SIGTERM, das ohne Umleitung ein warmes Herunterfahren ohne Zeitgrenze ist, und Docker tötet nach 10 s. Ohne die beiden Zeilen hätte die Einstellung keine Wirkung.
3. **Zeitlimits global gesetzt** (`CELERY_TASK_SOFT_TIME_LIMIT`/`CELERY_TASK_TIME_LIMIT`), nicht nur als Konstanten für die Einlese-Aufgaben.
4. **Zusätzliche Prüfung** `TWOX_INGEST_POLL_MAX_SECONDS` < `visibility_timeout`: Bei Redis wird eine Aufgabe mit Countdown über den `visibility_timeout` hinaus doppelt ausgeliefert. Und `TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS` ≤ 7 200 (Grenze des Dienstes, laut Auftrag „höchstens“).
5. **`test_worker.py`** liegt nicht in der Liste der betroffenen Dateien, musste aber mit: Die feste Liste `default, ingest, embed` schlägt bei KI aus fehl.
6. **Lokal vorhanden:** Images `twox-045-*`, `web/node_modules` (ignoriert, für den e2e-Lauf).

### Offene Fragen an a7

1. **Docling-Grenze einstellbar machen?** `TWOX_DOCLING_DOCUMENT_TIMEOUT_SECONDS` ist einstellbar, aber nur bis 7 200. Die Grenze selbst steht an drei Stellen: `DOCLING_SERVE_MAX_DOCUMENT_TIMEOUT` in `compose.yaml`, `DEFAULT_DOCUMENT_TIMEOUT_SECONDS` in `twox/ingest/docling.py` (lehnt größere Werte ab) und `TWOX_DOCLING_MAX_DOCUMENT_TIMEOUT_SECONDS` in `settings.py`. Optionen: (a) so lassen und nach 057 an allen drei Stellen ändern; (b) Folgeauftrag: eine Variable `TWOX_DOCLING_MAX_DOCUMENT_TIMEOUT_SECONDS` in `.env`, die Compose an Docling weitergibt und die `docling.py` liest. Empfehlung: (b) zusammen mit dem Ergebnis von 057 (berührt `ingest/docling.py`, nicht Teil dieses Auftrags).
2. **Einbettung und Socket-Zeitlimit:** `TWOX_EMBED_TIMEOUT_SECONDS` (120 s, 044) wird nicht gegen `TWOX_EMBED_TASK_MAX_SECONDS` + Puffer geprüft. Ein Stapel, der bei 239 s beginnt und 120 s braucht, überschreitet die weiche Grenze von 300 s. Empfehlung: 048 beginnt einen neuen Stapel nur, wenn noch `TWOX_EMBED_TIMEOUT_SECONDS` bis zur weichen Grenze bleiben; oder eine Prüfung `EMBED_TIMEOUT` < `TASK_SOFT_TIME_LIMIT − EMBED_TASK_MAX` hier nachziehen (würde mit den heutigen Vorgaben 120 < 60 scheitern, also Werte anpassen).
