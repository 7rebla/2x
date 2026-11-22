# Auftrag 040 – Datenbank: Erweiterungen vector und pg_trgm, Paket pgvector

Meilenstein: M2 · Freigabestufe: C · Status: zur Prüfung

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

**Status: zur Prüfung.** Alle Akzeptanzkriterien erfüllt; Läufe am 22.11.2026 im Container. Keine offene Frage, die den Auftrag aufhält.

### Was wurde gebaut?

- `backend/pyproject.toml`, `backend/uv.lock`: `pgvector>=0.5.1,<0.6`. `uv lock` lief wie verlangt mit `D run --rm --no-deps backend-dev uv lock` (das Dev-Image war vorher mit der alten Lock-Datei gebaut; der Quellbaum ist eingebunden). Ergebnis: `Added pgvector v0.5.1`, sonst keine Änderung im Lock, keine mitgezogenen Pakete, kein NumPy.
- `backend/twox/config/settings.py`: `django.contrib.postgres` in `INSTALLED_APPS` (nach `django.contrib.staticfiles`, mit Kommentar).
- neu `backend/twox/ingest/migrations/__init__.py` und `0001_extensions.py`: `VectorExtension()` und `TrigramExtension()`, ohne Abhängigkeiten. Djangos `CreateExtension` legt eine Erweiterung nur an, wenn sie fehlt; rückwärts entfernt sie beide.
- `backend/tests/config/test_database.py`: vier neue Fälle – `vector` und `pg_trgm` stehen in `pg_extension`; `'[1,2,3]'::vector <=> '[1,2,4]'::vector` liefert eine Zahl (gegen den von Hand gerechneten Kosinusabstand geprüft); `similarity('abc', 'abd')` liefert eine Zahl zwischen 0 und 1; `django.contrib.postgres` ist installiert. Der bisherige Verfügbarkeitstest bleibt unverändert.
- mypy brauchte keine Ausnahme: pgvector bringt eigene Typangaben mit (`Success: no issues found`). `backend/scripts/license-rules.txt` blieb unverändert (pip-licenses erkennt MIT).

### Wie wurde getestet?

Alle Befehle mit `D` = `docker compose -p twox-040` im Wurzelverzeichnis des Arbeitsverzeichnisses, `.env` aus `.env.example` mit `TWOX_API_PORT=18040`. Docker Engine 29.9.3, Compose v5.7.0. Kriterien 1, 5 und 6 liefen nach `down -v` noch einmal frisch auf dem committeten Stand.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version` (29.9.3), `docker compose version` (v5.7.0), Exit-Code 0 |
| 1 | erfüllt | vier Images `Built`, Exit-Code 0; `up -d --wait` Exit-Code 0; `D ps -a`: `migrate Exited (0)`, `db`, `valkey`, `worker`, `api` healthy; Protokoll `Applying ingest.0001_extensions... OK` |
| 2 | erfüllt | `test_database.py -v`: `6 passed` (die vier neuen dabei); `pytest`: `1101 passed, 4 deselected`, nichts übersprungen; `pytest -m worker`: `4 passed, 1101 deselected` |
| 3 | erfüllt | `All checks passed!`; `136 files already formatted`; `Success: no issues found in 136 source files` |
| 4 | erfüllt | `makemessages`: Exit-Code 0, `git diff -- backend/locale` ohne Unterschied; `makemigrations --check --dry-run`: `No changes detected`; Lizenzprüfung: `pgvector 0.5.1 MIT`, `License check passed.`; `spectacular`: Exit-Code 0, `git diff -- web/openapi` ohne Unterschied |
| 5 | erfüllt | `pg_trgm`, `plpgsql`, `vector` |
| 6 | erfüllt | `D run --rm migrate`: `No migrations to apply.`, Exit-Code 0 |
| 7 | erfüllt | `D --profile dev down -v` Exit-Code 0 |

Zusätzlich: `migrate ingest zero` entfernt beide Erweiterungen, `migrate ingest` legt sie wieder an.

**Befund für den Betrieb ohne Superuser (M6):** `select name, version, trusted, superuser from pg_available_extension_versions where name in ('vector','pg_trgm')` ergibt im Image `pgvector/pgvector:0.8.7-pg18`: `pg_trgm` 1.3 bis 1.6 `trusted = t`; `vector` 0.8.7 `trusted = f`, `superuser = t`. `pg_trgm` kann also jede Rolle mit `CREATE` auf der Datenbank anlegen, `vector` nur ein Superuser. Im Compose-Aufbau ist der Datenbankbenutzer `twox` Superuser (`rolsuper = t`), deshalb läuft die Migration. Ohne Superuser muss ein Administrator `CREATE EXTENSION vector` vor der ersten Migration ausführen; die Migration überspringt eine vorhandene Erweiterung. Das steht auch im Docstring der Migration.

### Vorschlag für die Abhängigkeitstabelle in `docs/DECISIONS.md`

| pgvector 0.5.1 (pgvector-python; reines Python, keine Pflichtabhängigkeiten, kein NumPy) | MIT | Feldtypen, Indizes und `VectorExtension` für die Erweiterung `vector` in Django; Quelle PyPI `pgvector` (https://github.com/pgvector/pgvector-python) | 040 | E-55 |

### Zweig und Arbeitsverzeichnis

Zweig `worktree-agent-a0b2b48071e03c11e`, Arbeitsverzeichnis `.claude/worktrees/agent-a0b2b48071e03c11e`. Nicht gepusht.

### Abweichungen

- `uv lock` mit `--no-deps` aufgerufen, damit dafür keine Datenbank startet; sonst wie im Auftrag.
- Zusätzlicher Testfall „`django.contrib.postgres` ist installiert“ in `test_database.py` statt in `test_settings.py`, weil `test_settings.py` nicht im Auftragsbereich liegt.
- Hinweis zum Zusammenführen mit 041: Beide Aufträge berühren `backend/twox/ingest/`. 040 legt nur `migrations/` an; legt 041 Modelle mit Migration an, muss deren Migration auf `ingest.0001_extensions` aufbauen.
