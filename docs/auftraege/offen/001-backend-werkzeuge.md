# Auftrag 001 – Backend: Werkzeuge und Container

Meilenstein: M0 · Freigabestufe: C · Status: offen

## Ziel

Ein leeres Django-Projekt `twox` läuft im Container gegen PostgreSQL mit pgvector. Lint, Typprüfung und Tests laufen über `docker compose`. Die API selbst (DRF, Health-Endpunkt, Dienst `api`) folgt in Auftrag 005.

## Umfang

- `backend/pyproject.toml` und `backend/uv.lock` (Projektname `twox`, Python 3.14, verwaltet mit uv).
- `backend/Dockerfile` mit zwei Stufen:
  - `dev`: mit Entwicklungswerkzeugen. Darf als root laufen (nur Entwicklung und CI), damit Schreibzugriffe im eingebundenen Ordner auf jedem Rechner funktionieren.
  - `runtime`: ohne Entwicklungswerkzeuge, Prozess läuft nicht als root.
  - Basis `python:3.14-slim`. Die virtuelle Umgebung liegt **außerhalb** des später eingebundenen Quelltext-Ordners (zum Beispiel `UV_PROJECT_ENVIRONMENT=/opt/venv`) und im PATH, sodass `pytest`, `ruff`, `mypy` und `python` ohne Vorsatz aufrufbar sind.
  - Die Zwischenspeicher von mypy, Ruff und pytest liegen per Umgebungsvariable unter `/tmp`, nicht im eingebundenen Ordner.
- `backend/.dockerignore` (Bau-Kontext ist in diesem Auftrag `backend/`).
- Django-Projekt nach Abschnitt 6 der Startunterlage: `backend/manage.py`, `backend/twox/config/` (`settings.py`, `urls.py`, `asgi.py`).
- Leere Django-Apps (nur `__init__.py` und `apps.py`, keine Modelle, keine Ansichten) für `assets`, `files`, `ingest`, `search`, `answers`, `profiles`, `accounts`, `importers`, alle in `INSTALLED_APPS`.
- Einstellungen ausschließlich aus Umgebungsvariablen mit Vorsatz `TWOX_`: `TWOX_SECRET_KEY`, `TWOX_DEBUG`, `TWOX_ALLOWED_HOSTS`, Datenbankzugang (`TWOX_DB_HOST`, `TWOX_DB_PORT`, `TWOX_DB_NAME`, `TWOX_DB_USER`, `TWOX_DB_PASSWORD`), `TWOX_LLM_BASE_URL` (Vorgabe `http://host.docker.internal:11434/v1`), `TWOX_DOCLING_URL` (Vorgabe `http://docling:5001`). Die beiden letzten werden hier nur definiert, noch nicht benutzt.
- `deploy/compose/compose.yaml` mit den Diensten:
  - `db`: Image `pgvector/pgvector` mit festem Versions-Tag, benanntes Volume, Healthcheck, kein Host-Port.
  - `backend-dev` (Profil `dev`): Stufe `dev`, bindet `backend/` als Quelltext ein, wartet auf `db` (healthy), `extra_hosts: ["host.docker.internal:host-gateway"]`.
  - Alle Pfade (Bau-Kontext, Bind-Mount) sind relativ zu `deploy/compose` geschrieben.
- `compose.yaml` im Wurzelverzeichnis nach a7s Antwort auf Frage 1 (Empfehlung: `include` auf `deploy/compose/compose.yaml`).
- `.env.example` im Wurzelverzeichnis mit allen Variablen und Entwicklungswerten (keine echten Geheimnisse).
- Konfiguration von Ruff (Linter und Formatter, einschließlich der Regelgruppe `DJ`), mypy im strengen Modus mit Django-Plugin, pytest mit pytest-django gegen die echte PostgreSQL.
- Tests unter `backend/tests/config/`:
  - Die Datenbank ist PostgreSQL; `vector` und `pg_trgm` stehen in `pg_available_extensions`.
  - Die Einstellungen lassen sich ohne laufende Datenbank importieren.
  - Alle acht Apps sind installiert.

## Nicht-Ziele

- DRF, drf-spectacular, Health-Endpunkt, Dienst `api`, ASGI-Server, automatische Migrationen, Benutzermodell (Auftrag 005).
- Celery, Valkey, docling-serve, Ollama-Prüfung (Aufträge 007, 008, 009).
- Modelle jeder Art. Aktivieren der Erweiterungen per Migration (`CREATE EXTENSION`) folgt in M2.
- django-allauth, django-storages, pgvector-Python-Paket (ab M1/M2).
- CI (Auftrag 011), Lizenz-Regeln (Auftrag 006).

## Betroffene Bereiche (Ordner, Dateien)

- `backend/**` (neu)
- `deploy/compose/compose.yaml` (neu)
- `compose.yaml` im Wurzelverzeichnis (neu, falls Frage 1 so entschieden)
- `.env.example` (neu)

## Akzeptanzkriterien (prüfbar)

Alle Befehle im Wurzelverzeichnis des Arbeitsverzeichnisses. `D` steht für `docker compose -p twox-001`. Vorher `.env.example` nach `.env` kopieren (`.env` wird nicht eingecheckt).

0. Vorab: `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren oder ausführen; Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. `D --profile dev build` endet mit Exit-Code 0.
2. `D up -d --wait db` endet mit Exit-Code 0; `D ps` zeigt `db` als `healthy`.
3. `D run --rm backend-dev python --version` gibt `Python 3.14.x` aus.
4. `D run --rm backend-dev ruff check .` meldet `All checks passed!`; `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0. (Belegt zugleich, dass die Werkzeuge trotz Bind-Mount sichtbar sind.)
5. `D run --rm backend-dev mypy .` meldet `Success: no issues found` (bei anderer Antwort auf Frage 2 der entsprechende Befehl mit 0 Fehlern).
6. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen; die drei oben genannten Testfälle sind dabei.
7. `D run --rm backend-dev python manage.py check` meldet `System check identified no issues`; `D run --rm backend-dev python manage.py makemigrations --check --dry-run` meldet `No changes detected`.
8. Nach den Läufen zeigt `git status --short` keine Zwischenspeicher-Ordner (`.mypy_cache`, `.ruff_cache`, `.pytest_cache`, `.venv`, `__pycache__`).
9. Wirkung der `.env` bei `include`: In der `.env` vorübergehend `TWOX_DB_NAME=envprobe` setzen; `D config` zeigt `envprobe` in der Umgebung von `db` bzw. `backend-dev`. Danach zurückstellen. Zeigt `D config` den Wert nicht: Frage in den Auftrag (betrifft Frage 1).
10. Datenpfad von PostgreSQL: `D exec db psql -U twox -d twox -c 'CREATE TABLE volume_probe (id int)'` (Benutzer und Datenbank nach `.env.example`), dann `D down` (ohne `-v`), `D up -d --wait db`, dann `D exec db psql -U twox -d twox -c 'SELECT count(*) FROM volume_probe'` liefert `0` ohne Fehler (die Daten haben das Neuanlegen des Containers überstanden).
11. `D run --rm backend-dev pip-licenses` listet alle installierten Pakete mit Lizenz. Im Kurzbericht einzeln: alles, was nicht MIT, Apache-2.0, BSD oder PostgreSQL-Lizenz ist.
12. `git grep -n -i -E 'password|secret' -- backend deploy compose.yaml .env.example` zeigt nur Variablennamen und Entwicklungswerte, keine echten Geheimnisse.
13. Abräumen: `D down -v` endet mit Exit-Code 0; ein erneutes `D up -d --wait db` startet sauber von null; zum Schluss wieder `D down -v`.

## Vorgaben und Hinweise

- **Voraussetzung:** keine. Das Grundgerüst der Leitstelle (Repository, `.gitignore`, `.gitattributes`, `CLAUDE.md`) ist vorhanden.
- **Abhängigkeiten.** Mit der Freigabe der Auftragsliste genehmigt a7 diese direkten Abhängigkeiten:
  - Laufzeit: Django 6.1.x, `psycopg[binary]` (LGPL-3.0-only, zulässig nach Leitplanke 7 als unverändert eingebundene Bibliothek).
  - Entwicklung: ruff, mypy, `django-stubs[compatible-mypy]`, pytest, pytest-django, pip-licenses (wird in Auftrag 006 gebraucht).
  - Werkzeug und Images: uv, `python:3.14-slim`, `pgvector/pgvector`.
  - Mitgezogene Pakete sind mitgenehmigt, soweit ihre Lizenz MIT, Apache-2.0, BSD oder PostgreSQL-Lizenz ist. Jede weitere direkte Abhängigkeit ist nicht genehmigt.
  - Ergibt die Prüfung an der Quelle für eine genannte oder mitgezogene Abhängigkeit eine andere Lizenz oder ist sie nicht feststellbar: im Kurzbericht einzeln aufführen. Bekannte Fälle, über die a7 in Auftrag 006 entscheidet: psycopg (LGPL-3.0-only) und pathspec (MPL-2.0, kommt über mypy, nur Entwicklung). Jeder weitere Fall: nicht einbauen, Frage in den Auftrag, Status „wartet auf a7“.
- **Versionen (Stand der Recherche vom 21.11.2026, an PyPI und Docker Hub belegt):** Python 3.14.10 · Django 6.1.3 · psycopg 3.3.9 · uv 0.13.9 · ruff 0.17.6 · mypy 2.4.1 · django-stubs 6.1.2 (verlangt mypy >=1.13,<2.5) · pytest 9.2.0 · pytest-django 4.14.0 · pip-licenses 5.5.5 · `pgvector/pgvector:0.8.7-pg18`. Vor dem Festschreiben an der Originalquelle prüfen, ob es neuere Fehlerkorrekturen gibt. Versionen über `uv.lock` festschreiben; uv selbst und die Images mit fester Version.
- **Ungeprüft und hier zu prüfen:**
  - pytest-django 4.14.0 nennt Django 6.1 nicht offiziell. Läuft es nicht fehlerfrei: nicht ausweichen, sondern Frage in den Auftrag.
  - Ob das Image `ghcr.io/astral-sh/uv` existiert und welche Tags es hat. Sonst uv in fester Version aus PyPI installieren.
  - Lizenzen der Images `python` und `pgvector/pgvector` (PostgreSQL selbst) und der in `psycopg-binary` gebündelten Bibliotheken (libpq, OpenSSL): im Kurzbericht nennen, was die Quelle sagt.
  - Weitere von mypy mitgezogene Pakete (laut Prüfbefund: librt, ast-serialize, mypy_extensions, typing_extensions): Lizenz je Paket in den Kurzbericht.
- **Python-Version (Abschnitt 5.2: „M0 legt die Version fest, die alle Abhängigkeiten tragen“):** Nur lesend an PyPI prüfen, ohne Installation, ob die in 5.2 genannten späteren Pakete Python 3.14 tragen: django-allauth, django-storages, pgvector, ein OpenAI-kompatibler Client. Stand der Recherche: django-allauth 3.11–3.15, pgvector >=3.10, django-storages nennt im Classifier nur bis 3.12 (letztes Release April 2025). Ergebnis in den Kurzbericht als Grundlage für Frage 4.
- **PostgreSQL 18:** Der Datenpfad ist anders als bis Version 17. Das Volume gehört auf `/var/lib/postgresql` (nicht `/var/lib/postgresql/data`). Kriterium 10 prüft das.
- Das mypy-Plugin importiert die Django-Einstellungen. `DJANGO_SETTINGS_MODULE` muss im Container gesetzt sein, und der Import darf keine Datenbankverbindung öffnen.
- Keine Fremdbibliothek zum Lesen der Umgebungsvariablen (kein django-environ); `os.environ` reicht.
- Parallele Arbeitsverzeichnisse: immer mit dem Projektnamen `-p twox-001` arbeiten. Dieser Auftrag veröffentlicht keinen Host-Port.
- Sprache: Code, Bezeichner, Kommentare und Commit-Nachrichten Englisch. Jede Funktion hat Typangaben.
- Paperless-ngx ist GPL-3.0: weder Code noch Konfiguration von dort übernehmen.
- `.gitignore`, `.gitattributes`, `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Fehlt ein Eintrag in der `.gitignore` (Kriterium 8): nicht selbst ändern, im Kurzbericht melden.
- Im Kurzbericht je Abhängigkeit Name, festgeschriebene Version, Lizenz und Quelle nennen. Unter „Zweig und Arbeitsverzeichnis“ den vollständigen Pfad des Arbeitsverzeichnisses angeben (Nachweis für den Prüfpunkt aus Abschnitt 8.6).
- Kein Push. Die Leitstelle committet nach `main` und pusht auf a7s Freigabe.
- Die Fragen unten beantwortet a7 mit der Freigabe der Liste; die Leitstelle trägt die Antworten vor dem Start ein. Fehlt eine Antwort: nicht raten, Status „wartet auf a7“.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

1. **Wo liegt die Compose-Datei, damit `docker compose up` (Abnahme M0) ohne Zusatz funktioniert?** Abschnitt 6 nennt nur `/deploy/compose`.
   - (a) Nur `deploy/compose/compose.yaml`; Aufruf immer mit `-f deploy/compose/compose.yaml`.
   - (b) Zusätzlich eine kleine `compose.yaml` im Wurzelverzeichnis, die per `include` auf die Dateien unter `deploy/compose` verweist.
   - Empfehlung: (b). Die Abnahme und das Ziel „Start in 10 Minuten“ gelten dann wörtlich; die eigentliche Konfiguration bleibt in `deploy/compose`. Alle Kriterien der M0-Aufträge sind für (b) geschrieben.
2. **Typprüfung** (Unterlage: „mypy mit django-stubs oder pyright“).
   - (a) mypy im strict-Modus mit django-stubs (so auch Paperless-ngx). mypy zieht pathspec (MPL-2.0) als Entwicklungspaket mit; siehe Auftrag 006 Frage 2.
   - (b) pyright (kein Django-Plugin, lädt Node nach).
   - Empfehlung: (a).
3. **PostgreSQL-Version** (Unterlage: „17 oder neuer“).
   - (a) 18 (`pgvector/pgvector:0.8.7-pg18`), Support bis November 2030.
   - (b) 17, Support bis November 2029.
   - (c) 19.0 – erst am 16.11.2026 erschienen.
   - Empfehlung: (a).
4. **Python 3.14** als Festlegung nach Abschnitt 5.2 – bitte bestätigen. Laut Recherche die höchste Version, die alle M0-Bausteine tragen (Celery, kombu, django-stubs, drf-spectacular, pytest-django und uvicorn führen 3.15 nicht). Offen ist django-storages (siehe Hinweise).

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
