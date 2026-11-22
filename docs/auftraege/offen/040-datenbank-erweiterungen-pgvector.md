# Auftrag 040 – Datenbank: Erweiterungen vector und pg_trgm, Paket pgvector

Meilenstein: M2 · Freigabestufe: C · Status: offen

## Ziel

Die Datenbank hat die Erweiterungen `vector` (pgvector) und `pg_trgm` eingeschaltet, und Django kennt die Feldtypen und Indizes von pgvector. Das ist die Grundlage für das Datenmodell (042) und die Suche (047, 050). Vorgemerkt seit Auftrag 001: Die Erweiterungen kommen per Migration; das Paket pgvector-python ist eine neue Abhängigkeit.

## Umfang

- Neue Laufzeit-Abhängigkeit `pgvector>=0.5.1,<0.6` in `backend/pyproject.toml`. Lock-Datei im Container neu erzeugen: `docker compose run --rm backend-dev uv lock`. Kein NumPy: Seit 0.5.0 ist NumPy keine Abhängigkeit mehr.
- `django.contrib.postgres` in `INSTALLED_APPS` (`backend/twox/config/settings.py`), gebraucht für `TrigramExtension`, `GinIndex`, `OpClass` und die Volltext-Bausteine.
- Erste Migration der App `ingest`: `backend/twox/ingest/migrations/__init__.py` und `0001_extensions.py` mit `pgvector.django.VectorExtension()` und `django.contrib.postgres.operations.TrigramExtension()`.
- Tests in `backend/tests/config/test_database.py`:
  - Nach der Migration stehen `vector` und `pg_trgm` in `pg_extension` (installiert, nicht nur verfügbar). Der bisherige Test für die Verfügbarkeit bleibt.
  - `SELECT '[1,2,3]'::vector <=> '[1,2,4]'::vector` liefert eine Zahl.
  - `SELECT similarity('abc', 'abd')` liefert eine Zahl.
- Lizenzprüfung: pgvector muss mit MIT durch `scripts/check-licenses.sh` gehen. Regeln in `backend/scripts/license-rules.txt` nur ergänzen, falls das Werkzeug die Lizenz nicht erkennt.
- Im Kurzbericht einen Vorschlag für die Zeile der Abhängigkeitstabelle in `docs/DECISIONS.md`: Name, Version, Lizenz, Quelle, Zweck. Eintragen tut ihn die Leitstelle.

## Nicht-Ziele

- Keine Modelle, Felder oder Indizes (042).
- Kein NumPy, keine weiteren Pakete.
- Keine Änderung am Datenbank-Image.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/pyproject.toml`, `backend/uv.lock`, gegebenenfalls `backend/scripts/license-rules.txt`
- `backend/twox/config/settings.py` (nur `INSTALLED_APPS`)
- neu: `backend/twox/ingest/migrations/__init__.py`, `backend/twox/ingest/migrations/0001_extensions.py`
- `backend/tests/config/test_database.py`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-040`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18040` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0; der Dienst `migrate` endet mit Exit-Code 0 (`D ps -a`).
2. Tests:
   - `D run --rm backend-dev pytest tests/config/test_database.py -v` endet mit Exit-Code 0, die neuen Tests sind dabei.
   - `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen.
   - `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
3. `D run --rm backend-dev ruff check .` meldet `All checks passed!`, `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0, `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
4. Weitere Prüfungen wie in `ci.yml`, jeweils ohne Unterschied zum eingecheckten Stand:
   - `D run --rm backend-dev python manage.py makemessages -l de --add-location=file`, danach `git diff --exit-code -I '^"POT-Creation-Date:' -- backend/locale`;
   - `D run --rm backend-dev python manage.py makemigrations --check --dry-run` endet mit Exit-Code 0;
   - `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0, und die Liste nennt `pgvector` mit MIT;
   - `D run --rm -v "$PWD/web/openapi:/out" backend-dev python manage.py spectacular --file /out/schema.yml` (unter Git Bash mit vorangestelltem `MSYS_NO_PATHCONV=1`), danach `git diff --exit-code -- web/openapi`.
5. `D exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc "select extname from pg_extension order by 1"'` zeigt `pg_trgm` und `vector`.
6. Eine zweite Migration auf derselben Datenbank (`D run --rm migrate`) endet mit Exit-Code 0 und meldet keine Änderung.
7. Abräumen: `D --profile dev down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: M2-Liste von a7 freigegeben; Frage 1 (pgvector) entschieden.

- Welle 1, parallel zu 041 (andere Dateien).
- **Einzige neue Python-Abhängigkeit von M2:** pgvector 0.5.1, MIT (`license_expression`), `requires_python >=3.10`, keine Pflichtabhängigkeiten, hochgeladen am 09.10.2026; geprüft an https://pypi.org/pypi/pgvector/json am 22.11.2026.
- Python 3.14 und Django 6.1 nennt pgvector nicht ausdrücklich; das Paket ist reines Python. Bei Problemen anhalten und den Befund in den Auftrag schreiben, nicht umgehen.
- Meldet mypy fehlende Typen, eine Ausnahme wie bei allauth (`follow_untyped_imports`) in `pyproject.toml` eintragen und im Kurzbericht nennen.
- `CREATE EXTENSION` braucht Rechte; im Image hat `POSTGRES_USER` sie. Für den Betrieb ohne Superuser (M6) den Befund im Kurzbericht vermerken: `select name, trusted from pg_available_extension_versions where name in ('vector','pg_trgm')`.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

1. **Neue Abhängigkeit pgvector 0.5.1 (MIT) zulassen?**
   - (a) pgvector-python einbinden.
   - (b) Vektortyp ohne Paket über eigene Feldklassen und rohes SQL.
   Empfehlung: (a). Standardweg der pgvector-Macher für Django, MIT, ohne weitere Abhängigkeiten; (b) wäre eigener Code ohne Gewinn.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
