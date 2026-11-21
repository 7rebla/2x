# Auftrag 008 – Celery-Worker mit Valkey

Meilenstein: M0 · Freigabestufe: C · Status: zur Prüfung

## Ziel

Ein Celery-Worker läuft als eigener Container, nutzt Valkey als Broker und Ergebnisspeicher und bedient drei getrennte Warteschlangen. Ein Rauchtest belegt, dass ein Auftrag hin- und das Ergebnis zurückkommt.

## Umfang

- `backend/twox/config/celery.py` (Celery-Anwendung) und Anbindung in `backend/twox/config/__init__.py`.
- Celery-Einstellungen in `settings.py` aus Umgebungsvariablen (`TWOX_CELERY_BROKER_URL`, `TWOX_CELERY_RESULT_BACKEND`); Serialisierung nur JSON.
- Drei Warteschlangen nach Abschnitt 5.2 mit englischen Namen: `ingest` (Einlesen), `embed` (Einbetten), `default` (Sonstiges). Ohne Angabe landet ein Auftrag in `default`.
- Eine Aufgabe `ping` im Paket `twox.config`, die die Zeichenkette `pong` zurückgibt.
- `deploy/compose/compose.yaml`: Dienste `valkey` (festes Versions-Tag, Healthcheck, kein Host-Port) und `worker` (Stufe `runtime`, bedient alle drei Warteschlangen, Healthcheck, `extra_hosts` wie bei `api`, kein Host-Port). `api`, `worker` und `backend-dev` erhalten die Broker-Variablen.
- `.env.example` um die neuen Variablen ergänzen.
- pytest-Konfiguration: Markierung `worker` für Tests, die einen laufenden Worker brauchen. Der Lauf ohne Angabe (`pytest`) wählt sie ab (`addopts` mit `-m "not worker"`); `pytest -m worker` führt genau sie aus.
- Tests unter `backend/tests/config/`:
  - Einheitstest: `ping` liefert `pong`; die drei Warteschlangen sind konfiguriert; Standard-Warteschlange ist `default`.
  - Integrationstest (Markierung `worker`): schickt `ping` an den laufenden Worker und liest das Ergebnis innerhalb von 10 Sekunden. Läuft kein Worker, schlägt der Test mit einer klaren Meldung fehl – er wird nicht übersprungen.

## Nicht-Ziele

- Fachliche Aufgaben (Einlesen, Einbetten) – ab M2.
- Mehrere Worker-Container je Warteschlange, Zeitplaner (Celery Beat), Überwachungsoberfläche (Flower).
- Die Testseite (Aufträge 010 und 012).
- Das Paket `valkey` (valkey-py) oder `celery-redis-plus`: kombu nutzt sie nicht bzw. sie wären zusätzliche Abhängigkeiten.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/pyproject.toml`, `backend/uv.lock`
- `backend/twox/config/celery.py` (neu), `backend/twox/config/__init__.py`, `backend/twox/config/settings.py`, Datei für die Aufgabe `ping` in `backend/twox/config/`
- `backend/tests/config/` (neue Testdateien)
- `backend/scripts/` (nur die Regeldatei der Lizenzprüfung, falls ein mitgezogenes Paket eine bereits genehmigte Lizenz in neuer Schreibweise trägt)
- `deploy/compose/compose.yaml`
- `.env.example`

## Akzeptanzkriterien (prüfbar)

Alle Befehle im Wurzelverzeichnis. `D` steht für `docker compose -p twox-008`. Vorher `.env.example` nach `.env` kopieren (falls nicht vorhanden) und darin `TWOX_API_PORT=18008` setzen.

0. Vorab: `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren oder ausführen; Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. `D up -d --wait` (ohne Dienstnamen) endet mit Exit-Code 0; `D ps` zeigt `db`, `valkey`, `worker` und `api` als `healthy`.
2. `D exec worker celery -A twox.config inspect ping` antwortet mit `pong`.
3. `D exec worker celery -A twox.config inspect active_queues` nennt `ingest`, `embed` und `default`.
4. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen; die Ausgabe nennt die abgewählten Worker-Tests als `deselected`.
5. `D run --rm backend-dev pytest -m worker` endet bei laufendem Worker mit Exit-Code 0, mindestens 1 Test bestanden.
6. Gegenprobe: Nach `D stop worker` schlägt `D run --rm backend-dev pytest -m worker` fehl, und die Meldung nennt den nicht erreichbaren Worker. Danach `D start worker`.
7. `D run --rm backend-dev ruff check .` meldet `All checks passed!`; `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0; `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
8. `D exec worker python -c "from django.conf import settings; print(settings.CELERY_BROKER_URL)"` zeigt eine Adresse mit dem Schema `redis://` und dem Host `valkey`.
9. `D ps --format json` zeigt für `valkey` und `worker` keinen veröffentlichten Host-Port.
10. Lizenzprüfung: `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0. Meldet sie ein mitgezogenes Paket mit nicht gedeckter Lizenz: nichts in die Erlaubt-Liste schreiben, Frage in den Auftrag, Status „wartet auf a7“.
11. Abräumen: `D down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

- **Voraussetzung:** Auftrag 005 ist zusammengeführt (und damit 001); die Lizenzprüfung aus Auftrag 006 liegt auf `main`.
- **Abhängigkeiten.** Mit der Freigabe der Auftragsliste genehmigt a7 diese direkten Abhängigkeiten: `celery[redis]` (zieht kombu und den Client redis-py nach), `celery-types` (nur Entwicklung) und das Image `valkey/valkey`. Mitgezogene Pakete (zum Beispiel billiard, vine, amqp, click) sind mitgenehmigt, soweit die Lizenzprüfung sie durchlässt (Kriterium 10). Jede weitere direkte Abhängigkeit ist nicht genehmigt.
- **Versionen (Stand der Recherche vom 21.11.2026, belegt):** celery 5.7.0 (BSD-3-Clause) · kombu 5.7.0 (BSD-3-Clause; das Extra `redis` verlangt redis >=6.4,<9) · redis-py 8.1.0 (MIT) · celery-types 0.26.0 (Apache-2.0) · Valkey 9.2.0 vom 19.11.2026 (BSD-3-Clause), gepflegt außerdem 9.1.4.
- **Celery kennt kein `valkey://`.** Valkey läuft über den Redis-Transport: Adresse `redis://valkey:6379/0`, Ergebnisse zum Beispiel in Datenbank 1. Die Celery-Doku nennt offiziell nur Redis.
- **Ungeprüft und hier zu prüfen:** ob redis-py 8.x fehlerfrei mit der gewählten Valkey-Version arbeitet. Der Integrationstest ist der Nachweis; das Ergebnis mit den genauen Versionen gehört in den Kurzbericht. Klappt es nicht: nicht auf andere Pakete ausweichen, sondern Frage in den Auftrag. Ebenso: Lizenz des Images `valkey/valkey` an der Quelle bestätigen.
- Die mitgezogenen Pakete von Celery im Kurzbericht mit Lizenz auflisten.
- Djangos eingebautes Tasks-Framework wird nicht verwendet; die Unterlage legt Celery fest. Im Kurzbericht einen Satz für das Entscheidungsprotokoll vorschlagen.
- Zugriffe auf die Warteschlange laufen später über eine eigene Schnittstelle (Abschnitt 7). Hier nur die Grundkonfiguration, keine fachliche Schnittstelle erfinden.
- Die Regel für alle späteren Aufträge: `pytest` ohne Angabe braucht nur die Datenbank; der volle Lauf besteht aus `pytest` und `pytest -m worker` bei laufendem Worker (so auch in der CI).
- Parallele Arbeitsverzeichnisse: immer mit `-p twox-008` und Port 18008 arbeiten.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle.
- Kein Push. Die Leitstelle committet nach `main` und pusht auf a7s Freigabe.
- Die Frage unten beantwortet a7 mit der Freigabe der Liste. Fehlt die Antwort: nicht raten, Status „wartet auf a7“.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

1. **Valkey-Version.**
   - (a) 9.1.x (aktuell 9.1.4), fest auf die Unterversion gelegt.
   - (b) 9.2.0 – erst am 19.11.2026 erschienen.
   - Empfehlung: (a), aus demselben Grund wie bei PostgreSQL 19: zwei Tage alt ist für ein Gerüst zu frisch. Der Bearbeiter prüft das genaue Tag auf Docker Hub.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Akzeptanzkriterien sind erfüllt; die Läufe fanden am 21.11.2026 im Container statt. Für die Leitstelle zu beachten: eine neue Zeile in der Regeldatei der Lizenzprüfung (python-dateutil, siehe unten) und die Einträge fürs Entscheidungsprotokoll.

### Was wurde gebaut?

- `backend/pyproject.toml`, `backend/uv.lock`: `celery[redis]>=5.7.0,<5.8` (Laufzeit), `celery-types>=0.26.0,<0.27` (Entwicklung). pytest: Markierung `worker`, `addopts` um `-m "not worker"` ergänzt.
- `backend/twox/config/celery.py`: Celery-Anwendung `twox`, Einstellungen aus den Django-Einstellungen mit Vorsatz `CELERY_`; `backend/twox/config/__init__.py` stellt sie als `celery_app` bereit.
- `backend/twox/config/tasks.py`: Aufgabe `twox.config.ping`, gibt `pong` zurück.
- `backend/twox/config/settings.py`: `CELERY_BROKER_URL` und `CELERY_RESULT_BACKEND` aus `TWOX_CELERY_BROKER_URL` und `TWOX_CELERY_RESULT_BACKEND` (Vorgabe `redis://valkey:6379/0` und `/1`), Serialisierung und angenommene Inhalte nur JSON, Warteschlangen `ingest`, `embed`, `default`, Standard `default`.
- `deploy/compose/compose.yaml`: Dienste `valkey` (`valkey/valkey:9.1.4`, Healthcheck `valkey-cli ping`, Volume `valkey-data`, kein Host-Port) und `worker` (Stufe `runtime`, `celery -A twox.config worker --queues ingest,embed,default`, Healthcheck über `celery inspect ping` an genau diesen Worker, `extra_hosts`, kein Host-Port). Die Broker-Variablen stehen im gemeinsamen Anker, also bei `migrate`, `api`, `worker` und `backend-dev`. `api` wartet zusätzlich auf `valkey`; `backend-dev` hängt weiter nur an `db`.
- `.env.example`: die zwei neuen Variablen.
- `backend/scripts/license-rules.txt`: eine neue Schreibweise (siehe „Lizenzprüfung“).
- Tests: `backend/tests/config/test_celery.py` (13 Fälle, ohne Broker) und `backend/tests/config/test_worker.py` (3 Fälle mit Markierung `worker`: je ein Hin- und Rückweg über `default`, `ingest` und `embed`).

Über den Wortlaut des Auftrags hinaus festgelegt:

- Jede Warteschlange hat eine eigene Vermittlung (Exchange) und einen eigenen Schlüssel gleichen Namens. Mit der Kurzform `Queue("ingest")` hingen alle drei an derselben Vermittlung `default` mit demselben Schlüssel; das war im ersten Lauf an `inspect active_queues` zu sehen und ist behoben.
- `CELERY_TASK_CREATE_MISSING_QUEUES = False`: Ein falsch geschriebener Warteschlangenname ist ein Fehler und erzeugt keine vierte Warteschlange, die niemand bedient.
- `CELERY_RESULT_ACCEPT_CONTENT = ["json"]`, `CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True`, `CELERY_TIMEZONE = "UTC"`.

### Wie wurde getestet?

`D` = `docker compose -p twox-008` im Wurzelverzeichnis des Arbeitsverzeichnisses, `.env` mit `TWOX_API_PORT=18008`, Docker Engine 29.9.3, Compose v5.7.0. Die Kriterien 1, 4, 5, 10 und 11 liefen nach der letzten Änderung noch einmal von leerem Zustand aus (`down -v`, dann `up -d --wait`).

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version` (29.9.3) und `docker compose version` (v5.7.0), beide Exit-Code 0 |
| 1 | erfüllt | Exit-Code 0; `migrate-1 Exited`, `valkey-1 Healthy`, `db-1 Healthy`, `api-1 Healthy`, `worker-1 Healthy`; `D ps`: `api`, `db`, `valkey`, `worker` jeweils `(healthy)`, `migrate` `Exited (0)` |
| 2 | erfüllt | `-> celery@44b3f35c9f31: OK` / `pong` / `1 node online.` |
| 3 | erfüllt | drei Einträge: `'name': 'ingest', 'exchange': {'name': 'ingest', …`, ebenso `embed` und `default` |
| 4 | erfüllt | `55 passed, 3 deselected in 14.88s`, Exit-Code 0, nichts übersprungen |
| 5 | erfüllt | `3 passed, 55 deselected in 1.01s`, Exit-Code 0 |
| 6 | erfüllt | nach `D stop worker`: `3 failed, 55 deselected in 31.25s`, Exit-Code 1, Meldung `Failed: Celery worker not reachable: no result for 'ping' from queue 'embed' within 10 seconds. Start it with …`. Nach `D start worker` wieder `3 passed` |
| 7 | erfüllt | `All checks passed!`; `42 files already formatted`, Exit-Code 0; `Success: no issues found in 42 source files` |
| 8 | erfüllt | `redis://valkey:6379/0` |
| 9 | erfüllt | `valkey` und `worker`: `Publishers` nur mit `PublishedPort 0` und leerer Adresse (die Ports 6379 und 8000 sind im Image deklariert, aber nicht veröffentlicht); einziger veröffentlichter Port: `api` auf `127.0.0.1:18008` |
| 10 | erfüllt, mit Ergänzung der Regeldatei | erster Lauf: Exit-Code 1, `python-dateutil 2.9.0.post0: license "Apache Software License; BSD License" is not allowed`. Nach Eintrag der Schreibweise: `52 packages`, `License check passed.`, Exit-Code 0 |
| 11 | erfüllt | `D down -v` Exit-Code 0 (`Volume twox-008_valkey-data Removed`, `Volume twox-008_db-data Removed`); danach `--profile dev down -v`; keine Container und Volumes des Projekts `twox-008` mehr. Das Projekt `2x` der Leitstelle lief durchgehend weiter (`api` und `db` healthy) |

Die Kriterien 2, 3, 6, 7, 8 und 9 liefen auf dem endgültigen Stand des Codes, aber vor dem Eintrag in die Regeldatei der Lizenzprüfung und vor dem letzten Neuaufbau von leerem Zustand; danach änderte sich nur noch die Regeldatei.

Zusätzlich: `python manage.py check` ohne Befund, `makemigrations --check --dry-run`: `No changes detected`. Der Worker läuft als Benutzer mit UID 10001. Nach den Läufen zeigt `git status --short --ignored` nur `.env` und `STARTUNTERLAGE.md`.

Nicht geprüft: Verhalten, wenn Valkey ganz fehlt (der Test fängt dafür `OperationalError` ab und meldet ebenfalls „Celery worker not reachable“; dieser Zweig lief nicht). Ebenso nicht geprüft: Verhalten des Workers nach einem Ausfall von Valkey im laufenden Betrieb.

**Zu prüfender Punkt „redis-py 8.x mit Valkey“:** redis-py 8.1.0 arbeitet mit Valkey 9.1.4 über celery 5.7.0 und kombu 5.7.0 fehlerfrei: Aufträge über alle drei Warteschlangen, Ergebnisse aus Datenbank 1, Fernsteuerung (`inspect ping`, `inspect active_queues`). Im gesichteten Protokoll des Workers (Start und erster Auftrag) keine Warnung und kein Fehler.

### Lizenzprüfung

Die Prüfung meldete genau ein Paket: python-dateutil 2.9.0.post0 (von celery mitgezogen) mit der Angabe „Apache Software License; BSD License“ – zwei Classifier, die das Skript absichtlich nicht als Auswahl wertet. Die Datei `LICENSE` des Pakets nennt Apache-2.0 und eine BSD-Lizenz; beide stehen auf der Liste der Leitplanke 7. Gemäß Hinweis der Leitstelle ist die Schreibweise wörtlich als `allow | Apache Software License; BSD License` eingetragen. Keine Lizenz außerhalb der zugelassenen Liste.

### Festgeschriebene Versionen, Lizenzen, Quellen (für das Entscheidungsprotokoll)

Direkte Abhängigkeiten:

| Name | Version | Lizenz | Quelle |
| --- | --- | --- | --- |
| celery (mit Extra `redis`) | 5.7.0 | BSD-3-Clause | https://pypi.org/project/celery/ |
| celery-types (nur Entwicklung) | 0.26.0 | Apache-2.0 | https://pypi.org/project/celery-types/ |
| Image `valkey/valkey` | 9.1.4 (Debian 13; Digest `sha256:3ab0eca823ebbf0fe352476ebac330ac9e5f14b592b9a954eab296d341e81b0e`) | BSD-3-Clause | https://hub.docker.com/r/valkey/valkey · Lizenz: `COPYING` im Tag 9.1.4 von https://github.com/valkey-io/valkey („SPDX-License-Identifier: BSD-3-Clause“) |

Das Tag `9.1.4` ist laut Docker Hub vom 18.11.2026 und das neueste der Reihe 9.1. Das Image wird unverändert als Laufzeit benutzt. Die Lizenzen der Python-Pakete stammen aus der Ausgabe von pip-licenses im Container.

Mitgezogene Pakete (Lizenz wie von pip-licenses gemeldet):

| Name | Version | Lizenz |
| --- | --- | --- |
| kombu | 5.7.0 | BSD-3-Clause |
| redis (redis-py) | 8.1.0 | MIT |
| amqp | 5.4.2 | BSD License |
| billiard | 4.3.2 | BSD License |
| vine | 5.1.0 | BSD License |
| click-didyoumean | 0.3.1 | MIT License |
| click-plugins | 1.1.1.2 | BSD License |
| click-repl | 0.4.1 | MIT |
| prompt-toolkit | 3.0.53 | BSD License |
| python-dateutil | 2.9.0.post0 | Apache Software License; BSD License |
| six | 1.17.0 | MIT License |
| tzlocal | 5.4.5 | MIT |

click 8.5.1 (BSD-3-Clause) war schon vorher vorhanden.

Vorschlag für einen Satz im Entscheidungsprotokoll: „Hintergrundarbeit läuft über Celery, wie in Abschnitt 5.2 der Startunterlage festgelegt; Djangos eingebautes Tasks-Framework wird nicht verwendet. Valkey wird über Celerys Redis-Transport angesprochen (Adressen mit `redis://`), weil Celery kein `valkey://` kennt; der Client ist redis-py.“

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-aa0fe36fce1a33f0b`
- Arbeitsverzeichnis: `.claude/worktrees/agent-aa0fe36fce1a33f0b` (relativ zum Projektordner)

### Abweichungen

- Keine Abweichung vom Auftrag oder von der Startunterlage.
- Die Lock-Datei entstand nicht mit `D run --rm backend-dev uv lock`: Das Image `backend-dev` baut mit `uv sync --locked` und lässt sich mit geänderter `pyproject.toml` und alter Lock-Datei nicht bauen. Stattdessen wurde die Stufe `builder` desselben Dockerfiles gebaut und `uv lock` darin ausgeführt (gleiche Versionen von uv und Python, nichts unter Windows installiert). Das Hilfs-Image ist wieder gelöscht.
- Der Worker startet mit Celerys Vorgabe für die Zahl der Prozesse (einer je Prozessorkern, auf diesem Rechner 16). Eine feste Zahl oder eine Variable dafür ist nicht Teil des Auftrags; Vorschlag: mit den fachlichen Aufgaben in M2 festlegen.
- `valkey` hat ein benanntes Volume `valkey-data` (das Image deklariert `/data` ohnehin als Volume); `down -v` entfernt es.
- Die Images `twox-008-api`, `-worker`, `-migrate` und `-backend-dev` liegen noch lokal vor.
