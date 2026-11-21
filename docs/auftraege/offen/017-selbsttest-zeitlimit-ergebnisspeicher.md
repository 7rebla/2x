# Auftrag 017 – Selbsttest: Zeitlimit, wenn der Ergebnisspeicher nicht antwortet

Meilenstein: M1 · Freigabestufe: B · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
