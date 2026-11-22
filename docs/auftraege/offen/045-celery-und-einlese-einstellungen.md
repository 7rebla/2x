# Auftrag 045 – Celery und Einlese-Einstellungen für lange Aufträge

Meilenstein: M2 · Freigabestufe: C · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
