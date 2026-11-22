# Auftrag 069 – Zugriffsprotokoll ohne Client-Adresse

Meilenstein: M2 · Freigabestufe: C (entschieden mit E-62) · Status: zur Prüfung

Voraussetzung: E-62; 052 und 059 sind auf `main`.

## Ziel

Das Zugriffsprotokoll von uvicorn enthält bei jeder Anfrage die Client-Adresse mit Port (Formatter `uvicorn_access` in `backend/twox/config/settings.py`, `%(client_addr)s`), auch bei fehlgeschlagenen Anmeldungen. Nach E-62 fällt sie weg – wie schon die Suchtexte (Logfilter aus 052). Methode, Pfad (ohne Query-String) und Status bleiben.

## Umfang

- Formatter des Zugriffsprotokolls ohne Client-Adresse; zusätzlich ein Filter (neben `DropQueryString` in `backend/twox/config/logging.py`), der die Adresse aus dem Datensatz entfernt, damit auch andere Formatter oder Handler sie nicht ausgeben.
- Prüfen, ob an anderer Stelle Client-Adressen protokolliert werden (Django-Logger, allauth, Anmeldebegrenzung, Celery); falls ja, im Kurzbericht nennen und – soweit ohne Funktionsverlust möglich – ebenfalls entfernen. Die Anmeldebegrenzung darf intern weiter mit der Adresse rechnen (sie wird nicht protokolliert).
- Tests in `backend/tests/config/test_logging.py`: Zugriffsprotokoll-Zeile ohne Adresse, mit Query-String-Entfernung zusammen, Anmeldeversuch (fehlgeschlagen) erzeugt keine Zeile mit Adresse; Reihenfolge uvicorn/Django wie in 052.
- README (Sicherheitshinweise, „Rate limit of the sign-in“, „Search texts“) und `docs/ARCHITECTURE.md` (Abschnitt „Logging“) nachziehen: Grenze aus 059 entfällt.

## Nicht-Ziele

- Keine Änderung an der Anmeldebegrenzung selbst.
- Keine neue Abhängigkeit.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/config/settings.py` (nur `LOGGING`), `backend/twox/config/logging.py`
- `backend/tests/config/test_logging.py`
- `README.md`, `docs/ARCHITECTURE.md` (nur die genannten Abschnitte)

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Alle Prüfungen des backend-Jobs aus `.github/workflows/ci.yml` sind grün.
2. Im eigenen Projekt: Anmeldung mit falschem Kennwort über die API und eine Suche; `docker compose logs api` enthält für beide Zeilen keine IP-Adresse (Ausgabe gekürzt im Kurzbericht).
3. `down -v` des eigenen Compose-Projekts endet mit Exit 0.

## Vorgaben und Hinweise

- Herkunft: E-62 (b), Befund aus der Prüfung von 059.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Was wurde gebaut?**

- `backend/twox/config/logging.py`: neuer Filter `DropClientAddress`. Er ersetzt in jedem Datensatz von `uvicorn.access` mit genau fünf Argumenten und Text an erster Stelle die Client-Adresse (mit Port) durch `-`. Die Zahl der Argumente bleibt, damit `AccessFormatter` und jeder andere Formatter weiter funktionieren; kein Datensatz wird verworfen. Andere Formen bleiben unverändert. Konstanten `CLIENT_ARGUMENT`, `ACCESS_ARGUMENTS`, `NO_CLIENT_ADDRESS`; Modul-Docstring nachgezogen. `DropQueryString` unverändert.
- `backend/twox/config/settings.py` (nur `LOGGING` und Kommentar davor): Format des Zugriffsprotokolls ohne `%(client_addr)s` (`%(levelprefix)s "%(request_line)s" %(status_code)s`), Filter `drop_client_address` vor `drop_query_string` am Logger `uvicorn.access`.
- `README.md` („Rate limit of the sign-in“: bekannte Grenze ersetzt; „Search texts“: Klammer berichtigt) und `docs/ARCHITECTURE.md` („Logging“: Grenze aus 059 entfernt, neuer Punkt „Access log without client addresses“).

Eine Zeile sieht jetzt so aus: `INFO:     "POST /_allauth/browser/v1/auth/login HTTP/1.1" 400 Bad Request`.

**Weitere Stellen mit Client-Adressen (geprüft):**

- Eigene Logger `twox.*`: keine Adresse (Anmelde-Adapter nennt nur den Benutzernamen; im Code kein Zugriff auf `REMOTE_ADDR` außer im Änderungsprotokoll, das sie nach E-43 schon verwirft).
- Django (`django.request`, `django.security`): Zeilen wie `Bad Request: /pfad`, `Forbidden (CSRF cookie not set.): /pfad` – ohne Adresse.
- allauth (65.x im Image): liest `REMOTE_ADDR` nur für die Anmeldebegrenzung (`core/internal/httpkit.py`), protokolliert sie nicht.
- Celery/Worker: keine Client-Adressen (Start-Banner nennt nur Kernelversion und Broker).
- uvicorn selbst: `uvicorn.error` schreibt die Adresse nur auf Stufe `trace` (Verbindungsereignisse, `httptools_impl.py`) und in den WebSocket-Protokollen; `trace` wird nicht genutzt, `websockets`/`wsproto` sind nicht installiert. Nicht geändert, in ARCHITECTURE vermerkt.
- Entfernt wurde also nur die Adresse im Zugriffsprotokoll; weitere Fundstellen gab es nicht.

**Wie wurde getestet?**

- `backend/tests/config/test_logging.py` (12 → 24 Tests): Filter ersetzt IPv4, IPv6 und leere Adresse und behält den Datensatz; andere Datensatzformen bleiben unberührt; auch uvicorns Standardformat und die reine Nachricht zeigen keine Adresse; Projektformat ohne `client_addr`; beide Filter zusammen (keine Adresse, kein Query-String); Reihenfolge uvicorn-dann-Django (`dictConfig(UVICORN_LOGGING)`, dann `settings.LOGGING`) mit beiden Filtern; fehlgeschlagene Anmeldung über den Django-Test-Client mit `REMOTE_ADDR=198.51.100.23`: 400, „Failed sign-in“ im Protokoll, Adresse weder in den Logger-Ausgaben noch in der zugehörigen Zugriffszeile.
- Eigenes Compose-Projekt `twox-069`, API-Port 18069.

| Kriterium | Ergebnis |
| --- | --- |
| 0 | erfüllt: `docker version` (29.9.3) und `docker compose version` (v5.7.0) Exit 0 |
| 1 | erfüllt: Bau Exit 0, `up -d --wait` Exit 0; ruff check, ruff format --check, mypy (192 Dateien), `pytest` 2353 bestanden (6 abgewählt), `pytest -m worker` 6 bestanden, makemessages ohne Diff, makemigrations --check, Lizenzprüfung, OpenAPI-Schema ohne Diff – alle Exit 0 |
| 2 | erfüllt: Konto `e2e-manager` (Entwicklungswerte aus `.env.example`) angelegt, über `/_allauth/browser/v1/auth/login` mit falschem Kennwort (400), dann richtig (200) angemeldet, `GET /api/v1/search/?q=zzprobe069` (200). `docker compose logs api` (gekürzt): `Failed sign-in for username 'e2e-manager'.` · `Bad Request: /_allauth/browser/v1/auth/login` · `INFO:     "POST /_allauth/browser/v1/auth/login HTTP/1.1" 400 Bad Request` · `INFO:     "POST /_allauth/browser/v1/auth/login HTTP/1.1" 200 OK` · `INFO:     "GET /api/v1/search/ HTTP/1.1" 200 OK`. Suche nach IPv4-Mustern im ganzen api-Protokoll: nur die Startzeile `Uvicorn running on http://0.0.0.0:8000`; kein `Adresse:Port`; `zzprobe069` 0-mal |
| 3 | erfüllt: `docker compose -p twox-069 --profile dev down -v` Exit 0, keine Container und Volumes übrig |

**Zweig und Arbeitsverzeichnis**

Zweig `worktree-agent-a8d235f5a85655b8a`, Arbeitsverzeichnis `.claude/worktrees/agent-a8d235f5a85655b8a`. Commits: `b83ac95` (Code und Tests), `c462dd7` (Doku), danach dieser Kurzbericht. Nicht gepusht.

**Abweichungen**

- Keine im Umfang. Die Anmelde-Zeile im Test wird nicht durch einen echten uvicorn-Prozess erzeugt, sondern als die Zeile, die uvicorn für die Anfrage schreibt, durch den konfigurierten Logger geschickt; der echte Lauf ist Kriterium 2.
- `README.md`: neben den genannten Punkten keine weiteren Stellen geändert.
