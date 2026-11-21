# Auftrag 001 – Backend: Werkzeuge und Container

Meilenstein: M0 · Freigabestufe: C · Status: erledigt (Frage 5: PSF-2.0 ist durch E-23 gedeckt)

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

5. **(neu, vom Auftragsbearbeiter, 21.11.2026) typing_extensions steht unter PSF-2.0.** Das Paket wird von mypy, django-stubs und django-stubs-ext zwingend mitgezogen (nur Entwicklung; im `runtime`-Image ist es nicht installiert). PSF-2.0 ist die Lizenz von Python selbst, freizügig und ohne Copyleft, steht aber nicht in der Liste „MIT, Apache-2.0, BSD, PostgreSQL“ und ist kein im Auftrag genannter bekannter Fall. Ohne das Paket gibt es kein mypy (Antwort auf Frage 2). Es steht bereits in `uv.lock` auf dem Auftragszweig; zusammengeführt ist nichts.
   - (a) PSF-2.0 als zulässige freizügige Lizenz ins Entscheidungsprotokoll aufnehmen; Zweig kann unverändert zusammengeführt werden.
   - (b) Ablehnen: dann entfällt mypy; Frage 2 müsste neu entschieden werden (pyright), Kriterium 5 und die Konfiguration ändern sich.
   - Empfehlung: (a).

## Kurzbericht (füllt der Auftragsbearbeiter aus)

### Was wurde gebaut?

- `backend/pyproject.toml`, `backend/uv.lock`: Projekt `twox`, `requires-python >=3.14,<3.15`, `[tool.uv] package = false`. Konfiguration für Ruff (E, W, F, I, N, UP, B, C4, SIM, ANN, DJ, RUF; Zeilenlänge 100), mypy (`strict`, Django-Plugin) und pytest (pytest-django, `--strict-markers`, `--strict-config`).
- `backend/Dockerfile`: Stufen `base`, `builder`, `runtime-deps`, `dev`, `runtime` (Standardziel). Virtuelle Umgebung in `/opt/venv` und im PATH. `dev` läuft als root, Zwischenspeicher über `MYPY_CACHE_DIR`, `RUFF_CACHE_DIR` und `PYTEST_ADDOPTS=-o cache_dir=…` unter `/tmp`, `PYTHONDONTWRITEBYTECODE=1`. `runtime` enthält nur Django und psycopg, Benutzer `twox` (UID 10001), kein uv.
- `backend/.dockerignore`, `backend/manage.py`, `backend/twox/config/{settings,urls,asgi}.py`, acht leere Apps (`__init__.py`, `apps.py`).
- `deploy/compose/compose.yaml` (Dienste `db` und `backend-dev`), `compose.yaml` im Wurzelverzeichnis mit `include`, `.env.example`.
- Tests: `backend/tests/config/test_database.py`, `backend/tests/config/test_settings.py` (16 Testfälle).

### Wie wurde getestet?

Alle Befehle mit `docker compose -p twox-001` im Wurzelverzeichnis des Arbeitsverzeichnisses, Docker Engine 29.9.3, Compose v5.7.0.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version` und `docker compose version` Exit-Code 0 |
| 1 | erfüllt | `Image twox-001-backend-dev Built`, Exit-Code 0 |
| 2 | erfüllt | Exit-Code 0; `twox-001-db-1 … Up 3 seconds (healthy)` |
| 3 | erfüllt | `Python 3.14.10` |
| 4 | erfüllt | `All checks passed!`; `26 files already formatted`, Exit-Code 0 |
| 5 | erfüllt | `Success: no issues found in 26 source files` |
| 6 | erfüllt | `16 passed in 5.66s`, Exit-Code 0, nichts übersprungen, keine Warnungen; die drei geforderten Testfälle sind dabei |
| 7 | erfüllt | `System check identified no issues (0 silenced).`; `No changes detected` |
| 8 | erfüllt | `git status --short --ignored` zeigt nur `.env` und `STARTUNTERLAGE.md`; kein Zwischenspeicher-Ordner, auch kein ignorierter |
| 9 | erfüllt | `D --profile dev config` zeigt `TWOX_DB_NAME: envprobe` (backend-dev) und `POSTGRES_DB: envprobe` (db); danach zurückgestellt (0 Treffer) |
| 10 | erfüllt | `CREATE TABLE`; nach `down` und `up`: `count 0`, Exit-Code 0. `data_directory` ist `/var/lib/postgresql/18/docker`, Server ist PostgreSQL 18.7 |
| 11 | erfüllt, mit Hinweis | 21 Pakete mit Lizenz gelistet. pip-licenses blendet sich selbst, prettytable und wcwidth standardmäßig aus (sichtbar mit `--with-system`) |
| 12 | erfüllt | 12 Treffer: nur Variablennamen, die Entwicklungswerte in `.env.example` und der Testwert `test-only` |
| 13 | erfüllt | `down -v` Exit-Code 0; neues `up -d --wait db` Exit-Code 0, `volume_probe` nicht mehr vorhanden; abschließend `down -v` Exit-Code 0 |

Zusätzlich geprüft (kein Kriterium): `docker build --target runtime backend` baut; im Container `uid=10001(twox)`, keine der Werkzeuge uv, ruff, mypy, pytest vorhanden, `python manage.py check` ohne Fehler. Die Stufe `runtime` wird von keinem Compose-Dienst gebaut (der Dienst `api` folgt in Auftrag 005).

Zu prüfende Punkte aus den Hinweisen:

- pytest-django 4.14.0 läuft mit Django 6.1.3 fehlerfrei und ohne Warnung.
- Das Image `ghcr.io/astral-sh/uv` existiert; Tag `0.13.9` ist vorhanden (linux/amd64) und wird benutzt.
- Neuere Fehlerkorrekturen: keine. PyPI und Docker Hub nennen am 21.11.2026 genau die im Auftrag genannten Versionen als neueste.

### Festgeschriebene Versionen, Lizenzen, Quellen (für das Entscheidungsprotokoll)

Lizenz laut PyPI-Metadaten der jeweiligen Version (https://pypi.org/project/NAME/), gegengeprüft mit pip-licenses im Container.

| Name | Version | Lizenz | Rolle |
| --- | --- | --- | --- |
| Django | 6.1.3 | BSD-3-Clause | Laufzeit, direkt |
| psycopg | 3.3.9 | LGPL-3.0-only | Laufzeit, direkt |
| psycopg-binary | 3.3.9 | LGPL-3.0-only | Laufzeit, über psycopg |
| asgiref | 3.13.0 | BSD-3-Clause | Laufzeit, über Django |
| sqlparse | 0.6.1 | BSD | Laufzeit, über Django |
| tzdata | 2026.6 | Apache-2.0 | nur in `uv.lock` (Windows), im Container nicht installiert |
| ruff | 0.17.6 | MIT | Entwicklung, direkt |
| mypy | 2.4.1 | MIT | Entwicklung, direkt |
| django-stubs | 6.1.2 | MIT | Entwicklung, direkt |
| pytest | 9.2.0 | MIT | Entwicklung, direkt |
| pytest-django | 4.14.0 | BSD | Entwicklung, direkt |
| pip-licenses | 5.5.5 | MIT | Entwicklung, direkt |
| django-stubs-ext | 6.1.2 | MIT | Entwicklung, über django-stubs |
| types-PyYAML | 6.0.12.20261113 | Apache-2.0 | Entwicklung, über django-stubs |
| typing_extensions | 4.16.0 | **PSF-2.0** | Entwicklung, über mypy und django-stubs |
| pathspec | 1.1.1 | **MPL-2.0** | Entwicklung, über mypy |
| librt | 0.17.0 | MIT | Entwicklung, über mypy |
| ast-serialize | 0.13.1 | MIT | Entwicklung, über mypy |
| mypy_extensions | 1.2.0 | MIT | Entwicklung, über mypy |
| iniconfig | 2.3.1 | MIT | Entwicklung, über pytest |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | Entwicklung, über pytest |
| pluggy | 1.7.0 | MIT | Entwicklung, über pytest |
| Pygments | 2.21.0 | BSD-2-Clause | Entwicklung, über pytest |
| colorama | 0.4.6 | BSD | nur in `uv.lock` (Windows), im Container nicht installiert |
| prettytable | 3.19.0 | BSD-3-Clause | Entwicklung, über pip-licenses |
| wcwidth | 0.9.4 | MIT | Entwicklung, über prettytable |
| uv | 0.13.9 | MIT OR Apache-2.0 | Werkzeug, Image `ghcr.io/astral-sh/uv:0.13.9` |
| Python | 3.14.10 | PSF-2.0 (`LICENSE.txt` im Image) | Image `python:3.14.10-slim` (Debian 13) |
| PostgreSQL | 18.7 | PostgreSQL-Lizenz (`copyright`-Datei im Image) | Image `pgvector/pgvector:0.8.7-pg18` (Debian 12) |
| pgvector | 0.8.7 | PostgreSQL-Lizenz (nicht erneut an der Quelle abgerufen) | im selben Image |

Außerhalb von MIT, Apache-2.0, BSD und PostgreSQL-Lizenz:

- psycopg und psycopg-binary: LGPL-3.0-only (bekannter Fall, unverändert eingebunden).
- pathspec: MPL-2.0 (bekannter Fall, nur Entwicklung).
- typing_extensions: PSF-2.0 (neuer Fall, siehe Frage 5; nur Entwicklung).
- Python im Basis-Image: PSF-2.0.
- Beide Images bauen auf Debian auf und enthalten Systempakete unter weiteren Lizenzen, darunter GPL (unverändertes Basis-Image, kein eigener Code). Einzeln geprüft wurde das nicht.
- In psycopg-binary gebündelt (Dateien in `psycopg_binary.libs`): libpq, libssl und libcrypto (OpenSSL 3), libkrb5, libgssapi_krb5, libk5crypto, libkrb5support, libcom_err, libldap, liblber, libsasl2, libkeyutils, libcrypt. Die mitgelieferte SBOM nennt nur drei davon und keine Lizenzen. Die Lizenzen dieser Bibliotheken konnte ich nicht an der Quelle belegen; nach meiner Kenntnis sind libkeyutils und libcrypt LGPL, der Rest freizügig. Das gehört in die Prüfung von Auftrag 006.

### Python 3.14 und spätere Pakete (nur an PyPI gelesen, nichts installiert)

| Paket | neueste Version | `requires-python` | Classifier |
| --- | --- | --- | --- |
| django-allauth | 65.22.1 | >=3.11 | 3.11 bis 3.15 |
| django-storages | 1.14.6 | >=3.7 | nur bis 3.12 |
| pgvector | 0.5.1 | >=3.10 | keine Angabe |
| openai | 3.57.0 | >=3.10 | bis 3.14 |

Kein Paket schließt 3.14 aus. django-storages nennt 3.13 und 3.14 nicht; ob es dort läuft, ist ungeprüft.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-aaa7e1830a99d5713`
- Arbeitsverzeichnis: `.claude/worktrees/agent-aaa7e1830a99d5713` (relativ zum Projektordner)

### Abweichungen und Hinweise

- **Basis-Image** ist `python:3.14.10-slim` statt `python:3.14-slim`, weil der Auftrag an anderer Stelle Images mit fester Version verlangt. Die Images sind per Tag festgelegt, nicht per Digest.
- **`INSTALLED_APPS` enthält nur die acht eigenen Apps**, keine `django.contrib`-Apps. Grund: Das Benutzermodell kommt in Auftrag 005; `django.contrib.auth` vorher einzutragen würde die Entscheidung vorwegnehmen. Middleware: nur Security, Common, Clickjacking.
- **`TWOX_SECRET_KEY` und `TWOX_DB_PASSWORD` haben keine Vorgabe.** Fehlen sie, bricht der Import der Einstellungen mit einer klaren Meldung ab (getestet). Alle anderen Variablen haben Vorgaben; eine leere Variable gilt als nicht gesetzt.
- Compose bricht ohne `.env` mit „Copy .env.example to .env first“ ab, auch bei `up db`.
- `uv.lock` wurde in einem Wegwerf-Container (Python-Image plus uv) erzeugt, weil die Stufe `dev` die Datei schon zum Bauen braucht. Künftig: `docker compose run --rm backend-dev uv lock`.
- Die Compose-Dateien setzen keinen Projektnamen. Ohne `-p` nimmt Compose den Ordnernamen. Ob ein fester Name (`name: twox`) gewünscht ist, habe ich nicht entschieden.
- `.gitignore`: Es fehlt kein Eintrag.
- Das Image `twox-001-backend-dev` liegt noch lokal vor; Container, Netz und Volume sind entfernt.
- Nicht geprüft: Erreichbarkeit von Ollama über `host.docker.internal` (Auftrag 007), Bau unter Linux/CI (Auftrag 011).
