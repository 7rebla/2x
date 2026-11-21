# Auftrag 017 – Selbsttest: Zeitlimit, wenn der Ergebnisspeicher nicht antwortet

Meilenstein: M1 · Freigabestufe: B · Status: zur Prüfung

## Ziel

Der Selbsttest antwortet innerhalb von etwa 5 Sekunden, auch wenn der Broker erreichbar ist, der Ergebnisspeicher aber nicht. Das ist die offene Nacharbeit 2 aus Auftrag 010, vorgemerkt in `docs/STATUS.md`.

## Umfang

- In `backend/twox/config/taskqueue.py` bekommt nur der Aufruf der API (`ping_worker`) eine eigene Instanz des Ergebnisspeichers. Sie hat kurze Socket-Zeitlimits und keine langen Wiederholungen (Vorschlag (a) aus 010). Die Einstellungen der Celery-App und damit des Workers bleiben unverändert.
- Laut 010 sind drei Stellen betroffen: `result.get()`, `result.forget()` und das Abonnement des Ergebniskanals in `apply_async`. Alle drei laufen über die begrenzte Instanz oder werden anders begrenzt.
- Ein Ausfall des Ergebnisspeichers erscheint als eigene Unterklasse von `TaskQueueError`, z. B. `ResultStoreUnavailableError` mit dem Text `result store not reachable`. Der Text enthält weder Adresse noch Kennwort. Heute wird derselbe Text als `BrokerUnavailableError` gemeldet; das wird getrennt.
- Tests in `backend/tests/config/test_selftest.py`:
  - Die API-Instanz trägt die Zeitlimits, `app.conf` enthält sie nicht (analog zu `test_socket_timeouts_reach_the_connection_but_not_the_app_settings`).
  - Ein nicht antwortender Ergebnisspeicher (im Test nachgestellt) führt innerhalb der Grenze zu `ok: false` mit der neuen Meldung.

## Nicht-Ziele

- Änderung der Antwortfelder des Selbsttests oder der Oberfläche.
- Beschränkung auf angemeldete Benutzer (Auftrag 027).
- Einstellungen des Workers.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/config/taskqueue.py`, bei Bedarf `backend/twox/config/selftest.py` (nur Zuordnung der Fehlertexte)
- `backend/tests/config/test_selftest.py`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-017`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18017` setzen.
- Unter Git Bash vor Befehlen mit `/out/…` `MSYS_NO_PATHCONV=1` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Praktischer Beleg (Broker erreichbar, Ergebnisspeicher an einer nicht antwortenden Adresse):
   - Befehl: `D run --rm -e TWOX_CELERY_RESULT_BACKEND=redis://10.255.255.1:6379/1 backend-dev python manage.py shell -c \"import time; from twox.config.selftest import check_worker; t=time.monotonic(); print(check_worker(), round(time.monotonic()-t, 1))\"`
   - Erwartet: `'ok': False` mit gefülltem `error` und eine Dauer von höchstens 7 Sekunden.
   - Weist die Umgebung die Adresse sofort ab, eine andere nicht antwortende Adresse wählen und im Kurzbericht nennen.
3. Bei laufendem Worker liefert `D exec api python -c \"import urllib.request as u; print(u.urlopen('http://localhost:8000/api/v1/selftest/').read().decode())\"` weiter `ok: true` und `pong`.
4. Prüfungen und Typen:
   - `D run --rm backend-dev ruff check .` meldet `All checks passed!`.
   - `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0.
   - `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
5. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen. `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
6. `D run --rm backend-dev python manage.py makemigrations --check --dry-run` meldet `No changes detected`.
7. `D run --rm -v \"$PWD/web/openapi:/out\" backend-dev python manage.py spectacular --file /out/schema.yml`, danach zeigt `git diff --exit-code -- web/openapi` keinen Unterschied.
8. Abräumen: `D --profile dev down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“).

- Welle 1, parallel zu 016, 018 und 019. `settings.py` nicht ändern; das gehört in dieser Welle zu 016.
- **Keine neue Abhängigkeit.**
- Grundlage: Auftrag 010, Abschnitt „Nacharbeit nach Prüfung“, Punkt 2.
  - Vorschlag (b), ein Hilfsthread mit `future.result(timeout)`, nur dann, wenn (a) nachweislich nicht trägt.
  - In diesem Fall im Kurzbericht begründen.
- Fehlertexte Englisch, ohne interne Einzelheiten; Einzelheiten nur ins Serverprotokoll.
- Auftrag 027 ändert `selftest.py` und `test_selftest.py` später (Welle 4).
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Akzeptanzkriterien sind erfüllt; die Läufe fanden am 21.11.2026 im Container statt. Keine neue Abhängigkeit, `settings.py` und `selftest.py` sind nicht berührt.

### Was wurde gebaut?

- `backend/twox/config/taskqueue.py`:
  - `ping_worker` baut je Aufruf eine eigene Celery-App (`bounded_app`). Sie liest dieselbe Quelle wie `twox.config.celery` (Django-Einstellungen, Präfix `CELERY_`) und bekommt zusätzlich `result_store_settings(t)`: `redis_socket_timeout` und `redis_socket_connect_timeout` = t, `redis_retry_on_timeout` aus, `result_backend_always_retry` aus, `retry_policy` mit `max_retries: 0`. Damit hat sie eine eigene Instanz des Ergebnisspeichers. Die App des Workers bleibt unverändert.
  - Warum eine eigene App und nicht nur ein eigenes Backend-Objekt: Celery abonniert den Ergebniskanal in `send_task` immer über das Backend der sendenden App; ein anderes Backend lässt sich dort nicht übergeben. `ignore_result=True` würde das Abonnement zwar überspringen, aber der Worker speichert dann auch kein Ergebnis.
  - Ablauf: Broker verbinden (wie bisher, ein Versuch, Socket-Zeitlimits) → `watch_result`: `PING` an den Ergebnisspeicher und Abonnement des Ergebniskanals → erst dann Senden mit `send_task` (findet den Kanal schon abonniert, spricht den Ergebnisspeicher nicht mehr an) → `result.get()` → `result.forget()`. Alle drei Stellen aus 010 laufen über die begrenzte Instanz.
  - Die Prüfung vor dem Senden ist nötig, weil (1) Celery Fehler des Abonnements in `send_task` als Broker-Fehler (`OperationalError`) meldet und (2) beim Abonnement mit Wiederverbindung zwei Verbindungsversuche stattfinden (gemessen: 2 × Zeitlimit). Ein ausgefallener Ergebnisspeicher verhindert so auch, dass ein Ping in der Warteschlange liegen bleibt.
  - Neue Unterklasse `ResultStoreUnavailableError(TaskQueueError)` mit dem Text `result store not reachable` (ohne Adresse oder Kennwort). Bisher kam dieser Text als `BrokerUnavailableError`.
  - Nach einem Ausfall des Ergebnisspeichers wird `forget()` nicht mehr versucht (keine zweite Wartezeit). Am Ende schließt `close_result_store` die Verbindungen der App (auch die des Ergebniskanals) und `app.close()`.
- `backend/tests/config/test_selftest.py`: Die Einheitstests von `ping_worker` laufen jetzt über die echte begrenzte App mit gefälschter Broker-Verbindung (Hilfsklasse `FakeQueue`). Neu:
  - `test_result_store_timeouts_reach_the_api_instance_but_not_the_app_settings`: Die Instanz der API trägt Socket-Zeitlimits 5, `retry_on_timeout` aus, `max_retries` 0, `always_retry` aus. Die App des Workers und ihr Backend enthalten das nicht. Broker, Ergebnisspeicher, Serialisierung und Standard-Warteschlange stimmen in beiden Apps überein.
  - `test_ping_worker_turns_result_store_error_into_safe_error`: Fehler des Ergebnisspeichers (mit Adresse und Kennwort im Text) ergeben `ResultStoreUnavailableError`, keine Interna, kein `forget()`.
  - `test_silent_result_store_is_a_partial_failure_within_the_limit`: echter, nicht antwortender Ergebnisspeicher. Ein lauschender Socket auf 127.0.0.1 nimmt nie an; der Kern schließt den TCP-Aufbau ab, es kommt aber kein Byte zurück. `check_worker(1.0)` liefert `ok: false` mit `result store not reachable` in unter 2 s (gemessen 1,01 s), und nichts wurde gesendet.
  - Der Test „Broker nicht erreichbar“ setzt die Broker-Adresse jetzt in den Django-Einstellungen statt in `ping.app.conf`, weil die begrenzte App dort liest.
- `docs/ARCHITECTURE.md` (eigener Commit): Abschnitt 4 des Selbsttest-Ablaufs beschreibt die eigene Instanz; die alte Zeile „Known limit …“ ist durch den neuen Stand ersetzt.

### Wie wurde getestet?

`D` = `docker compose -p twox-017` im Wurzelverzeichnis des Arbeitsverzeichnisses, `.env` aus `.env.example` mit `TWOX_API_PORT=18017`, Docker Engine 29.9.3, Compose v5.7.0, Celery 5.7.0, redis-py 8.1.0.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version` (29.9.3) und `docker compose version` (v5.7.0), Exit-Code 0 |
| 1 | erfüllt | Build Exit-Code 0; `up -d --wait …` Exit-Code 0, `db`, `valkey`, `api`, `worker` Healthy (nach dem letzten Code-Stand neu gebaut) |
| 2 | erfüllt | Befehl wie im Auftrag mit `redis://10.255.255.1:6379/1`: `{'ok': False, 'result': '', 'duration_ms': 5035, 'error': 'result store not reachable'} 5.0`. Die Adresse wurde nicht sofort abgewiesen. Einzelheiten (`Timeout connecting to server`) nur im Protokoll. Gegenprobe mit dem alten `taskqueue.py`: keine Antwort innerhalb von 120 s, mit `timeout 120` abgebrochen (Exit-Code 124) |
| 3 | erfüllt | `{"database":{"ok":true,…},"worker":{"ok":true,"result":"pong","duration_ms":33,"error":""}}` |
| 4 | erfüllt | `All checks passed!`; `52 files already formatted` (Exit-Code 0); `Success: no issues found in 52 source files` |
| 5 | erfüllt | `113 passed, 4 deselected`, Exit-Code 0, nichts übersprungen; `pytest -m worker`: `4 passed, 113 deselected`, Exit-Code 0 |
| 6 | erfüllt | `No changes detected` |
| 7 | erfüllt | `spectacular --file /out/schema.yml` Exit-Code 0, `git diff --exit-code -- web/openapi` Exit-Code 0, keine unversionierten Dateien |
| 8 | erfüllt | `D --profile dev --profile e2e down -v` Exit-Code 0; keine Container und Volumes von `twox-017` mehr. Projekt `2x` nicht angefasst |

Zusätzlich geprüft, bei laufender API mit neuem Code:

- Drei Aufrufe nacheinander: `ok: true`, 12–14 ms.
- Worker gestoppt: `no result from a worker within 5 seconds`, 5,04 s.
- Valkey pausiert: `message broker not reachable`, 5,04 s.
- Nach `unpause`: sofort wieder `pong`.
- 20 Aufrufe hintereinander: Zahl der Clients in Valkey vorher und nachher 13, also keine liegen gebliebenen Verbindungen.
- Lizenzprüfung (`sh scripts/check-licenses.sh`): `License check passed.`
- Alle Prüfungen der Tabelle liefen auf dem committeten Stand. Die Typprüfung braucht kein neues `type: ignore`.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a4a8d885bf666e14f`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a4a8d885bf666e14f` (relativ zum Projektordner)
- Commits: `Bound the self-test when the result store does not answer`, `Describe the bounded result store in the architecture notes`, dazu dieser Kurzbericht

### Abweichungen und Hinweise

- Vorschlag (a) aus 010 trägt; (b) (Hilfsthread) wurde nicht gebraucht. Statt einer bloßen Backend-Instanz ist es eine eigene Celery-App je Aufruf (Begründung oben). Sie registriert keine Aufgaben, wird nicht zur aktuellen App und installiert keine Django-Erweiterung (`fixups=[]`).
- Die Konfigurationsquelle (`django.conf:settings`, Präfix `CELERY`) steht als Konstante in `taskqueue.py` und damit ein zweites Mal neben `celery.py`. Ein Test prüft, dass beide Apps dieselben Werte für Broker, Ergebnisspeicher, Serialisierung und Standard-Warteschlange haben. `celery.py` habe ich nicht geändert, weil es nicht im Auftrag steht.
- `docs/ARCHITECTURE.md` liegt außerhalb der genannten Dateien. Geändert wurden nur zwei Sätze, damit die Doku nicht veraltet ist, in einem eigenen Commit. Die Leitstelle kann ihn weglassen.
- Bekannte Grenze: Hört der Ergebnisspeicher mitten im Aufruf auf zu antworten (nach erfolgreicher Prüfung), endet das Warten nach 5 s als `no result from a worker …`, und `forget()` kann bis zu ein weiteres Socket-Zeitlimit (5 s) dauern. Höchstens etwa 10 s statt bisher unbegrenzt. Nicht nachgestellt.
- `selftest.py` brauchte keine Änderung: Der neue Fehler ist ein `TaskQueueError`, sein Text wird wie bisher angezeigt.
- Keine offenen Fragen an a7.
