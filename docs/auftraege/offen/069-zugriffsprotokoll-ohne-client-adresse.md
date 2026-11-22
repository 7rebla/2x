# Auftrag 069 – Zugriffsprotokoll ohne Client-Adresse

Meilenstein: M2 · Freigabestufe: C (entschieden mit E-62) · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
