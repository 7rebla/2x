# Auftrag 010 – Testseite, Teil API

Meilenstein: M0 · Freigabestufe: C · Status: zur Prüfung

## Ziel

Ein API-Endpunkt liefert einen Wert aus der Datenbank und ein Ergebnis, das der Celery-Worker berechnet hat. Er ist die Datenquelle der Testseite (Auftrag 012) und belegt den Weg durch API, Datenbank, Broker und Worker.

## Umfang

- Endpunkt `GET /api/v1/selftest/`, nur lesend, mit typisierter Antwort (Serializer), damit das OpenAPI-Schema vollständig ist:
  - `database`: `ok` (Wahrheitswert), `server_version` (Zeichenkette, aus `SHOW server_version`), `error` (Zeichenkette oder leer).
  - `worker`: `ok` (Wahrheitswert), `result` (Zeichenkette, erwartet `pong`), `duration_ms` (Zahl), `error` (Zeichenkette oder leer).
- Der Endpunkt schickt die Aufgabe `ping` (aus Auftrag 008) in die Warteschlange `default` und wartet höchstens 5 Sekunden auf das Ergebnis.
- Teilausfälle führen nicht zu einem Serverfehler: Die Antwort hat HTTP 200, der betroffene Teil hat `ok: false` und einen kurzen Fehlertext ohne interne Einzelheiten (keine Zugangsdaten, keine Verbindungszeichenketten, kein Stacktrace).
- Eintrag in `backend/twox/config/urls.py`.
- Tests unter `backend/tests/config/`:
  - Datenbankteil: `ok` ist wahr, `server_version` beginnt mit der Hauptversion der laufenden PostgreSQL.
  - Workerteil, Ausfall (Broker nicht erreichbar bzw. Zeitlimit, im Test nachgestellt): HTTP 200, `ok` ist falsch, `error` ist gefüllt.
  - Der Fehlertext enthält weder Kennwort noch Broker- oder Datenbankadresse.
  - Das Schema enthält den Pfad und die Antwortfelder.
  - Workerteil, Erfolg (Markierung `worker`, gegen den laufenden Worker): `ok` ist wahr, `result` ist `pong`.

## Nicht-Ziele

- Die Seite in der Oberfläche (Auftrag 012).
- Zustand von Docling und Ollama in der Antwort (dafür gibt es `check_docling` und `check_llm`).
- Ein Datenbankmodell. Der Wert kommt ohne neue Tabelle aus der Datenbank.
- Anmeldung (M1).

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/config/` (neue Datei(en) für Ansicht und Serializer, `urls.py`) – oder nach a7s Antwort auf Frage 1
- `backend/tests/config/` (neue Testdateien)

## Akzeptanzkriterien (prüfbar)

Alle Befehle im Wurzelverzeichnis. `D` steht für `docker compose -p twox-010`. Vorher `.env.example` nach `.env` kopieren (falls nicht vorhanden) und darin `TWOX_API_PORT=18010` setzen. `ABRUF` steht für `D exec api python -c "import urllib.request as u; print(u.urlopen('http://localhost:8000/api/v1/selftest/').read().decode())"`.

0. Vorab: `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren oder ausführen; Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. `D up -d --wait db valkey worker api` endet mit Exit-Code 0.
2. `ABRUF` gibt JSON aus mit `database` → `ok: true` und einer `server_version`, sowie `worker` → `ok: true` und `result: pong`.
3. Nach `D stop worker` gibt `ABRUF` innerhalb von etwa 6 Sekunden JSON aus mit `worker` → `ok: false` und gefülltem `error`; `database` bleibt `ok: true`. Kein HTTP-Fehler. Danach `D start worker`.
4. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen.
5. `D run --rm backend-dev pytest -m worker` endet bei laufendem Worker mit Exit-Code 0; der Erfolgsfall des Selftests ist dabei.
6. `D run --rm backend-dev python manage.py spectacular --file /tmp/schema.yml` endet ohne Warnungen; das Schema enthält `/api/v1/selftest/` mit den Feldern `database` und `worker` (Nachweis im Test und im Kurzbericht).
7. `D run --rm backend-dev ruff check .` meldet `All checks passed!`; `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
8. `D run --rm backend-dev python manage.py makemigrations --check --dry-run` meldet `No changes detected` (kein neues Modell).
9. Abräumen: `D down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

- **Voraussetzung:** Die Aufträge 005 und 008 sind zusammengeführt.
- **Keine neue Abhängigkeit.**
- **Stufe C wegen der Berechtigung:** Der Endpunkt ist in M0 ohne Anmeldung erreichbar (ausdrücklich `AllowAny`), weil es noch keine Anmeldung gibt. Er gibt nur die Versionsnummer der Datenbank und `pong` aus. a7 genehmigt das mit der Freigabe der Liste. Im Kurzbericht als Folgeaufgabe für M1 vermerken: Endpunkt auf angemeldete Benutzer beschränken (er stößt bei jedem Aufruf eine Aufgabe an).
- Der Zugriff auf die Warteschlange soll an einer Stelle gekapselt sein (Abschnitt 7: Schnittstellen vor Umsetzung), damit Tests den Ausfall nachstellen können.
- Die Antwortfelder sind die Schnittstelle zu Auftrag 012; Namen nicht ändern. Abweichungen im Kurzbericht nennen.
- Auftrag 009 läuft gleichzeitig und ändert `deploy/compose/compose.yaml`; dieser Auftrag fasst die Datei nicht an.
- Parallele Arbeitsverzeichnisse: immer mit `-p twox-010` und Port 18010 arbeiten.
- Sprache: Code, Feldnamen und Fehlertexte Englisch; jede Funktion hat Typangaben.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle.
- Kein Push. Die Leitstelle committet nach `main` und pusht auf a7s Freigabe.
- Die Frage unten beantwortet a7 mit der Freigabe der Liste. Fehlt die Antwort: nicht raten, Status „wartet auf a7“.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

1. **Wo liegt der Code der Testseite?** Abschnitt 6 sieht keinen allgemeinen Bereich für so etwas vor.
   - (a) Im Paket `twox/config` (keine neue App, keine Abweichung vom Repository-Aufbau).
   - (b) Eine neue App, zum Beispiel `twox/system` – Abweichung von Abschnitt 6, dafür ein fester Platz für eine spätere Statusseite.
   - Empfehlung: (a). Die Seite ist Gerüst; wird später eine Statusseite gewünscht, lässt sich das dann entscheiden.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Akzeptanzkriterien sind erfüllt; die Läufe fanden am 21.11.2026 im Container statt. Keine neue Abhängigkeit, `deploy/compose/compose.yaml` ist nicht berührt.

### Was wurde gebaut?

- `backend/twox/config/taskqueue.py` (neu): die eine Stelle für den Zugriff der API auf die Warteschlange. `ping_worker(timeout_seconds)` schickt `ping` an `default` und wartet insgesamt höchstens etwa `timeout_seconds`. Fehler kommen als `TaskQueueError` (Unterklassen `BrokerUnavailableError`, `WorkerTimeoutError`) mit kurzem, unbedenklichem Text; die Originalausnahme hängt nur für das Serverprotokoll daran. Die Verbindung zum Broker wird mit genau einem Versuch aufgebaut (`ensure_connection(max_retries=0, …)`), sonst wiederholt kombu bei nicht erreichbarem Broker sehr lange. Der Auftrag bekommt `expires` (ein nicht abgeholter Ping bleibt nicht liegen), das Ergebnis wird danach mit `forget()` aus Valkey entfernt.
- `backend/twox/config/selftest.py` (neu): `SelftestView` (`AllowAny`, ohne Authentifizierung), Serializer `SelftestSerializer` mit `DatabaseCheckSerializer` und `WorkerCheckSerializer`, Prüfungen `check_database()` (`SHOW server_version`, keine Tabelle) und `check_worker()` (Zeitlimit 5 Sekunden). Teilausfälle ergeben HTTP 200 mit `ok: false`; Fehlertexte: `database not reachable`, `message broker not reachable`, `no result from a worker within 5 seconds`, `unexpected result from the worker`, `worker check failed` (jeder andere Fehler; dessen Text wird nicht weitergegeben). Einzelheiten landen nur im Protokoll der API (`logger.warning` mit Stacktrace).
- `backend/twox/config/urls.py`: `GET /api/v1/selftest/`.
- Tests: `backend/tests/config/test_selftest.py` (14 Fälle ohne Worker, 1 Fall mit Markierung `worker`); in `backend/tests/config/test_api.py` heißt der Test „nur der Health-Pfad im Schema“ jetzt `test_schema_lists_exactly_the_known_paths` und erwartet beide Pfade.

Antwortfelder wie im Auftrag, Namen unverändert. `duration_ms` ist eine ganze Zahl (Millisekunden, auch im Fehlerfall gefüllt). Leere Felder sind die leere Zeichenkette `""`, nicht `null`. Schema-Komponenten: `Selftest`, `DatabaseCheck`, `WorkerCheck`; Operation `selftest_retrieve`.

Beispielantwort (Kriterium 2):

```json
{"database":{"ok":true,"server_version":"18.7 (Debian 18.7-1.pgdg12+2)","error":""},"worker":{"ok":true,"result":"pong","duration_ms":383,"error":""}}
```

### Wie wurde getestet?

`D` = `docker compose -p twox-010` im Wurzelverzeichnis des Arbeitsverzeichnisses, `.env` aus `.env.example` mit `TWOX_API_PORT=18010`, Docker Engine 29.9.3, Compose v5.7.0. Alle Läufe auf dem committeten Stand des Codes.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version` (29.9.3) und `docker compose version` (v5.7.0), beide Exit-Code 0 |
| 1 | erfüllt | Exit-Code 0; `migrate-1 Exited`, `valkey-1 Healthy`, `db-1 Healthy`, `api-1 Healthy`, `worker-1 Healthy` |
| 2 | erfüllt | siehe Beispielantwort oben |
| 3 | erfüllt | nach `D stop worker`: `{"database":{"ok":true,"server_version":"18.7 …","error":""},"worker":{"ok":false,"result":"","duration_ms":5019,"error":"no result from a worker within 5 seconds"}}`, Exit-Code 0 (kein HTTP-Fehler). Im Container gemessen: 5,04 s je Abruf; mit `docker compose exec` von außen 7,4 s (der Rest ist der Start von `exec`). Danach `D start worker`, erneut `ok: true`, `pong` |
| 4 | erfüllt | `68 passed, 4 deselected in 16.15s`, Exit-Code 0, nichts übersprungen |
| 5 | erfüllt | `4 passed, 68 deselected in 1.38s`, Exit-Code 0; dabei `test_selftest.py::test_selftest_against_running_worker PASSED` |
| 6 | erfüllt | Exit-Code 0, keine Ausgabe (keine Warnungen); `/tmp/schema.yml` enthält `/api/v1/selftest/` mit `operationId: selftest_retrieve` und die Komponenten `Selftest` (Felder `database`, `worker`), `DatabaseCheck`, `WorkerCheck`. Im Test geprüft (`test_schema_contains_selftest_path_and_fields`, mit `--validate`) |
| 7 | erfüllt | `All checks passed!`; zusätzlich `ruff format --check`: `45 files already formatted`; `Success: no issues found in 45 source files` |
| 8 | erfüllt | `No changes detected` |
| 9 | erfüllt | `D down -v` Exit-Code 0 (`Volume twox-010_db-data Removed`, `Volume twox-010_valkey-data Removed`, `Network twox-010_default Removed`); danach `D --profile dev down -v` Exit-Code 0; keine Container und Volumes des Projekts `twox-010` mehr. Das Projekt `2x` der Leitstelle lief durchgehend weiter |

Zusätzlich geprüft:

- Valkey gestoppt (Broker nicht erreichbar): `"worker":{"ok":false,"result":"","duration_ms":4009,"error":"message broker not reachable"}`, Datenbank `ok: true`, 4,03 s, HTTP 200. Das Protokoll der API enthält die Einzelheiten (`Error -2 connecting to valkey:6379 …`), die Antwort nicht.
- Die Tests ohne Worker stellen den Ausfall so nach: echter Verbindungsversuch zu einer nicht auflösbaren Broker-Adresse mit Kennwort darin (`.invalid`), Zeitlimit des Workers (nachgestellt an `taskqueue.ping_worker`), unerwarteter Fehler mit Adresse im Text, Datenbankfehler mit Kennwort und Host im Text. Geprüft wird jeweils HTTP 200, `ok: false`, gefüllter `error` und dass der Text weder Kennwort noch Broker- oder Datenbankadresse, `redis://`, Port oder `Traceback` enthält. Dazu Einheitstests für `ping_worker` (Warteschlange `default`, `expires`, `retry=False`, Zeitlimit ≤ 5 s, `forget()`).
- Nach den Läufen zeigt `git status --short --ignored` nur `.env` und `STARTUNTERLAGE.md`.

Nicht geprüft: Verhalten, wenn Valkey erreichbar ist, aber der Ergebnisspeicher (Datenbank 1) nicht antwortet; dann greifen die Wiederholungen des Redis-Ergebnisspeichers von Celery, und die Wartezeit könnte 5 Sekunden übersteigen. Ebenso nicht geprüft: Netzwerk, das Pakete verwirft statt abzuweisen (dann begrenzt Celerys `broker_connection_timeout` von 4 s den Verbindungsaufbau).

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a49035818f4eef516`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a49035818f4eef516` (relativ zum Projektordner)

### Abweichungen und Hinweise

- Keine Abweichung vom Auftrag oder von der Startunterlage. Code nach Antwort auf Frage 1 im Paket `twox/config`.
- `apply_async(connection=…)` ist eine dokumentierte Option von Celery, fehlt aber in celery-types; dafür steht eine gezielte Ausnahme `# type: ignore[call-arg]` mit Kommentar in `taskqueue.py`.
- `server_version` ist der volle Wert von `SHOW server_version` und enthält beim offiziellen Image den Zusatz der Distribution (`18.7 (Debian 18.7-1.pgdg12+2)`). Soll die Testseite nur `18.7` zeigen, lässt sich das in 012 oder hier mit `server_version_num` lösen.
- Die Beschreibung der Operation im OpenAPI-Schema stammt aus dem Docstring der Ansicht (nennt die Freigabe für M0 und die Beschränkung in M1).
- **Folgeaufgabe für M1:** `GET /api/v1/selftest/` auf angemeldete Benutzer beschränken (`AllowAny` und leere `authentication_classes` entfernen); jeder Aufruf stößt eine Aufgabe an und belegt bis zu 5 Sekunden einen Thread der API.
- Die Images `twox-010-api`, `-worker`, `-migrate` und `-backend-dev` liegen noch lokal vor.
- Keine offenen Fragen an a7.