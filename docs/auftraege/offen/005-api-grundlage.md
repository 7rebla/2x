# Auftrag 005 – API-Grundlage

Meilenstein: M0 · Freigabestufe: C · Status: zur Prüfung

## Ziel

Die API läuft als eigener Container: Django REST Framework mit OpenAPI-Beschreibung, ein Health-Endpunkt, automatische Migrationen beim Start. `docker compose up` ohne weitere Angaben startet Datenbank und API.

## Umfang

- Django REST Framework mit drf-spectacular: Standard-Berechtigung `IsAuthenticated`. Ein Endpunkt `GET /api/v1/health/` (ausdrücklich `AllowAny`) liefert `{"status": "ok"}`. Das OpenAPI-Schema ist über `python manage.py spectacular` erzeugbar.
- Eigenes Benutzermodell nach a7s Antwort auf Frage 2 (bei (a): `accounts.User` als unveränderte Ableitung von `AbstractUser`, ohne Zusatzfelder, mit erster Migration; bei (b) entfällt der Punkt).
- `deploy/compose/compose.yaml`:
  - Dienst `api`: Stufe `runtime`, ASGI-Server nach Frage 1, Healthcheck auf `/api/v1/health/`, Host-Port nur auf `127.0.0.1:${TWOX_API_PORT:-8000}`, `extra_hosts: ["host.docker.internal:host-gateway"]`.
  - Migrationen laufen beim Start automatisch (einmaliger Dienst oder Startskript; Wahl im Kurzbericht begründen).
- `.env.example` um `TWOX_API_PORT` ergänzen.
- Typen für DRF in der mypy-Konfiguration (Plugin von djangorestframework-stubs).
- Tests unter `backend/tests/config/` (und `backend/tests/accounts/`, falls Benutzermodell):
  - Health-Endpunkt antwortet 200 mit `{"status": "ok"}`.
  - Ein Endpunkt ohne ausdrückliche Freigabe verlangt Anmeldung (Standard-Berechtigung greift; Ansicht nur im Test).
  - Das Schema enthält den Pfad `/api/v1/health/`.
  - Bei Frage 2 (a): `AUTH_USER_MODEL` ist `accounts.User`; ein Benutzer lässt sich anlegen.

## Nicht-Ziele

- Anmeldeseiten, Rollen, django-allauth, Protokoll (M1). Das Benutzermodell hier ist nur die leere Hülle, damit die erste Migration stimmt.
- Weitere fachliche Modelle.
- Celery, Valkey (Auftrag 008), Testseite (Aufträge 010, 012), Auslieferung der Oberfläche (Auftrag 013).
- Swagger-Oberfläche (`drf-spectacular[sidecar]` wäre eine weitere Abhängigkeit).

## Betroffene Bereiche (Ordner, Dateien)

- `backend/pyproject.toml`, `backend/uv.lock`
- `backend/twox/config/settings.py`, `backend/twox/config/urls.py`, neue Datei für die Health-Ansicht in `backend/twox/config/`
- `backend/twox/accounts/` (Modell und Migration, nur bei Frage 2 (a))
- `backend/tests/config/`, `backend/tests/accounts/`
- `backend/Dockerfile` (nur Startbefehl der Stufe `runtime`, Startskript falls gewählt)
- `deploy/compose/compose.yaml` (Dienst `api`, Migrationen)
- `.env.example`

## Akzeptanzkriterien (prüfbar)

Alle Befehle im Wurzelverzeichnis. `D` steht für `docker compose -p twox-005`. Vorher `.env.example` nach `.env` kopieren (falls nicht vorhanden) und darin `TWOX_API_PORT=18005` setzen.

0. Vorab: `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren oder ausführen; Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. `D --profile dev build` endet mit Exit-Code 0.
2. `D up -d --wait` (ohne Dienstnamen – so lautet die Abnahme von M0) endet mit Exit-Code 0; `D ps` zeigt `db` und `api` als `healthy`. Scheitert `--wait` an einem beendeten Migrations-Container: die Variante mit Startskript wählen.
3. `D exec api python -c "import urllib.request as u; print(u.urlopen('http://localhost:8000/api/v1/health/').read().decode())"` gibt `{"status":"ok"}` aus (Leerzeichen egal).
4. `D config` zeigt für `api` den veröffentlichten Port `18005` auf `127.0.0.1` (die `.env` im Wurzelverzeichnis wirkt).
5. `D exec api sh -c 'id -u'` gibt nicht `0` aus (läuft nicht als root).
6. `D run --rm backend-dev ruff check .` meldet `All checks passed!`; `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0.
7. `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
8. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen; die oben genannten Testfälle sind dabei.
9. `D run --rm backend-dev python manage.py makemigrations --check --dry-run` meldet `No changes detected`.
10. `D run --rm backend-dev python manage.py spectacular --file /tmp/schema.yml` endet mit Exit-Code 0 und ohne Warnungen.
11. Neustart: `D down` (ohne `-v`) und erneut `D up -d --wait` endet mit Exit-Code 0 (Migrationen laufen ein zweites Mal ohne Fehler).
12. Abräumen: `D down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

- **Voraussetzung:** Auftrag 001 ist zusammengeführt.
- **Abhängigkeiten.** Mit der Freigabe der Auftragsliste genehmigt a7 diese direkten Abhängigkeiten: djangorestframework, drf-spectacular, ASGI-Server nach Frage 1 (Laufzeit); `djangorestframework-stubs[compatible-mypy]` (Entwicklung). Mitgezogene Pakete sind mitgenehmigt, soweit ihre Lizenz MIT, Apache-2.0, BSD oder PostgreSQL-Lizenz ist. Jede weitere direkte Abhängigkeit ist nicht genehmigt. Ergibt die Prüfung (`D run --rm backend-dev pip-licenses`) eine andere Lizenz oder ist sie nicht feststellbar: nicht einbauen, Frage in den Auftrag, Status „wartet auf a7“.
- **Versionen (Stand der Recherche vom 21.11.2026, an PyPI belegt):** djangorestframework 3.18.3 · drf-spectacular 0.30.0 · uvicorn 0.54.0 · granian 2.8.9 · djangorestframework-stubs 3.18.2 (verlangt django-stubs >=6.1.2). Alle BSD-3-Clause bzw. MIT (Stubs). Vor dem Festschreiben auf neuere Fehlerkorrekturen prüfen.
- **Ungeprüft und hier zu prüfen:** drf-spectacular 0.30.0 führt Django 6.1 nicht im Classifier; die Kombination ist aber bei NetBox 4.7.5 im Einsatz. Läuft sie nicht fehlerfrei: nicht ausweichen, sondern Frage in den Auftrag. Ob `docker compose up -d --wait` einen erfolgreich beendeten einmaligen Dienst als Erfolg wertet, hängt von der Compose-Version ab (Kriterium 2 ist der Nachweis).
- **Stufe C** wegen neuer Abhängigkeiten und wegen des Benutzermodells (Datenmodell, Anmeldung). `AUTH_USER_MODEL` lässt sich nach der ersten Migration nur mit Aufwand ändern.
- Djangos eingebautes Tasks-Framework (`django.tasks`) wird nicht verwendet; die Unterlage legt Celery fest.
- Der Start der Stufe `runtime` darf keine Geheimnisse im Image brauchen; alle Werte kommen aus der Umgebung.
- Parallele Arbeitsverzeichnisse: immer mit `-p twox-005` und Port 18005 arbeiten (die Leitstelle nutzt 8000). Abrufe laufen im Container (`exec`), nicht über den Host-Port.
- Sprache: Code, Bezeichner, Kommentare und Commit-Nachrichten Englisch. Jede Funktion hat Typangaben.
- Paperless-ngx ist GPL-3.0: weder Code noch Konfiguration von dort übernehmen.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Im Kurzbericht je Abhängigkeit Name, festgeschriebene Version, Lizenz und Quelle nennen.
- Kein Push. Die Leitstelle committet nach `main` und pusht auf a7s Freigabe.
- Die Fragen unten beantwortet a7 mit der Freigabe der Liste; die Leitstelle trägt die Antworten vor dem Start ein. Fehlt eine Antwort: nicht raten, Status „wartet auf a7“.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

1. **ASGI-Server** (nötig für den späteren Antwort-Stream; die Unterlage nennt keinen).
   - (a) uvicorn 0.54.0 (BSD-3-Clause): am weitesten verbreitet, Python bis 3.14.
   - (b) granian 2.8.9 (BSD-3-Clause): Vorbild Paperless-ngx, Python bis 3.15.
   - Empfehlung: (a) uvicorn, weil am weitesten verbreitet und damit am besten von KI-Werkzeugen beherrscht (Auswahlregel 5.1). Ein späterer Wechsel betrifft nur den Startbefehl.
2. **Eigenes Benutzermodell schon in M0?** Django empfiehlt, `AUTH_USER_MODEL` vor der ersten Migration festzulegen. Das Datenmodell ist a7s Entscheidung; Anmeldung und Rollen selbst bleiben M1.
   - (a) Jetzt `accounts.User` als unveränderte Ableitung von `AbstractUser` (keine Zusatzfelder) mit erster Migration.
   - (b) Erst in M1; bis dahin Djangos Standard-Benutzer. Ein Wechsel in M1 verlangt dann, die Datenbanken der Entwicklung neu anzulegen.
   - Empfehlung: (a).

## Kurzbericht (füllt der Auftragsbearbeiter aus)

### Was wurde gebaut?

- `backend/pyproject.toml`, `backend/uv.lock`: neue direkte Abhängigkeiten djangorestframework, drf-spectacular, uvicorn (Laufzeit) und `djangorestframework-stubs[compatible-mypy]` (Entwicklung). mypy lädt zusätzlich `mypy_drf_plugin.main`. Ruff: Ausnahme für erzeugte Migrationen (`E501`, `RUF012`).
- `backend/twox/config/health.py`: `HealthView` (`AllowAny`, ohne Authentifizierung) mit `HealthSerializer` für das Schema. `backend/twox/config/urls.py`: `GET /api/v1/health/`.
- `backend/twox/config/settings.py`: `django.contrib.auth`, `django.contrib.contenttypes`, `rest_framework`, `drf_spectacular` in `INSTALLED_APPS`; `AUTH_USER_MODEL = "accounts.User"`; `REST_FRAMEWORK` (Standard-Berechtigung `IsAuthenticated`, nur JSON, Schema-Klasse von drf-spectacular); `SPECTACULAR_SETTINGS`.
- `backend/twox/accounts/models.py` und `migrations/0001_initial.py`: `User` als unveränderte Ableitung von `AbstractUser`.
- `backend/Dockerfile`: Stufe `runtime` startet `uvicorn twox.config.asgi:application --host 0.0.0.0 --port 8000 --lifespan off`.
- `deploy/compose/compose.yaml`: Dienste `migrate` (einmalig) und `api` (Healthcheck, Port nur auf `127.0.0.1:${TWOX_API_PORT:-8000}`, `extra_hosts`).
- `.env.example`: `TWOX_API_PORT=8000`, Hinweis zu `TWOX_ALLOWED_HOSTS`.
- Tests: `backend/tests/config/test_api.py` (8 Fälle), `backend/tests/accounts/test_user_model.py` (3 Fälle); `test_settings.py` angepasst (der Test „genau acht Apps“ zählt jetzt nur Apps mit Vorsatz `twox.`).

**Migrationen: einmaliger Dienst `migrate`, kein Startskript.** Begründung: Nach Abschnitt 5.4 läuft die API später in vielen Instanzen; mit einem Startskript würden alle gleichzeitig migrieren. Der Dienst `api` wartet per `service_completed_successfully` auf `migrate`. Compose v5.7.0 wertet den erfolgreich beendeten Dienst bei `up -d --wait` als Erfolg (Kriterium 2 und 11 belegen das). Der Dienst `migrate` nutzt dieselbe Stufe `runtime`; Compose baut dafür ein zweites, inhaltsgleiches Image (`…-migrate`, gleiche Schichten).

### Wie wurde getestet?

Alle Befehle mit `docker compose -p twox-005` im Wurzelverzeichnis des Arbeitsverzeichnisses, `.env` mit `TWOX_API_PORT=18005`, Docker Engine 29.9.3, Compose v5.7.0. Die Läufe fanden nach der letzten Änderung statt.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version` (29.9.3) und `docker compose version` (v5.7.0), beide Exit-Code 0 |
| 1 | erfüllt | `Image twox-005-backend-dev Built`, `…-migrate Built`, `…-api Built`, Exit-Code 0 |
| 2 | erfüllt | Exit-Code 0; `migrate-1 Exited`, `db-1 Healthy`, `api-1 Healthy`; `D ps`: `api … (healthy)`, `db … (healthy)` |
| 3 | erfüllt | `{"status":"ok"}` |
| 4 | erfüllt | `host_ip: 127.0.0.1`, `target: 8000`, `published: "18005"` |
| 5 | erfüllt | `10001` |
| 6 | erfüllt | `All checks passed!`; `33 files already formatted`, Exit-Code 0 |
| 7 | erfüllt | `Success: no issues found in 33 source files` |
| 8 | erfüllt | `27 passed in 7.08s`, Exit-Code 0, nichts übersprungen, keine Warnungen; die geforderten Fälle sind dabei |
| 9 | erfüllt | `No changes detected` |
| 10 | erfüllt | Exit-Code 0, keine Ausgabe (keine Warnungen). Zusätzlich `spectacular --validate`: Exit-Code 0 |
| 11 | erfüllt | `down` Exit-Code 0; `up -d --wait` Exit-Code 0; Protokoll von `migrate`: `No migrations to apply.` |
| 12 | erfüllt | `--profile dev down -v` Exit-Code 0; keine Container und kein Volume des Projekts `twox-005` mehr vorhanden |

Zusätzlich: `python manage.py check` meldet `System check identified no issues (0 silenced).` Nach den Läufen zeigt `git status --short --ignored` nur die geänderten Dateien sowie `.env` und `STARTUNTERLAGE.md`.

Zu prüfende Punkte aus den Hinweisen:

- drf-spectacular 0.30.0 läuft mit Django 6.1.3 und DRF 3.18.3 fehlerfrei und ohne Warnung (Schema erzeugt und validiert).
- `up -d --wait` mit einmaligem Dienst: funktioniert mit Compose v5.7.0 (siehe oben). Mit älteren Compose-Versionen nicht geprüft.
- Neuere Fehlerkorrekturen: `uv lock` hat innerhalb der gesetzten Grenzen genau die im Auftrag genannten Versionen gewählt. PyPI habe ich darüber hinaus nicht gesondert abgefragt.

### Festgeschriebene Versionen, Lizenzen, Quellen (für das Entscheidungsprotokoll)

Lizenz laut Paket-Metadaten der installierten Version, ausgegeben von `pip-licenses --with-system` im Container (Quelle der Pakete: PyPI, https://pypi.org/project/NAME/). Die Projektseiten habe ich nicht zusätzlich abgerufen.

| Name | Version | Lizenz | Rolle |
| --- | --- | --- | --- |
| djangorestframework | 3.18.3 | BSD-3-Clause | Laufzeit, direkt |
| drf-spectacular | 0.30.0 | BSD-3-Clause | Laufzeit, direkt |
| uvicorn | 0.54.0 | BSD-3-Clause | Laufzeit, direkt (ohne Extra `standard`) |
| click | 8.5.1 | BSD-3-Clause | Laufzeit, über uvicorn |
| h11 | 0.16.0 | MIT | Laufzeit, über uvicorn |
| PyYAML | 6.0.4 | MIT | Laufzeit, über drf-spectacular |
| uritemplate | 4.2.0 | BSD-3-Clause OR Apache-2.0 | Laufzeit, über drf-spectacular |
| inflection | 0.5.1 | MIT | Laufzeit, über drf-spectacular |
| jsonschema | 4.26.0 | MIT | Laufzeit, über drf-spectacular |
| jsonschema-specifications | 2025.9.1 | MIT | Laufzeit, über jsonschema |
| referencing | 0.37.0 | MIT | Laufzeit, über jsonschema |
| rpds-py | 2026.9.1 | MIT | Laufzeit, über jsonschema und referencing |
| attrs | 26.1.0 | MIT | Laufzeit, über jsonschema und referencing |
| djangorestframework-stubs | 3.18.2 | MIT | Entwicklung, direkt |

Alle neuen Pakete liegen innerhalb von MIT, Apache-2.0 und BSD. Keine neue Ausnahme. Die übrigen Pakete und ihre Versionen sind gegenüber Auftrag 001 unverändert. rpds-py und PyYAML enthalten übersetzten Code (Rust bzw. C) als fertige Wheels; die Lizenzen darin gebündelter Fremdbestandteile habe ich nicht geprüft (wie bei psycopg-binary ein Punkt für Auftrag 006).

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a34a619951205c83d`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a34a619951205c83d` (relativ zum Projektordner)

### Abweichungen und Hinweise

- **Authentifizierung ist ausdrücklich leer** (`DEFAULT_AUTHENTICATION_CLASSES: []`). DRF würde sonst Sitzung und HTTP-Basic einschalten; welche Anmeldung gilt, entscheidet M1 (Stufe C). Folge: Jede Ansicht ohne eigene Freigabe antwortet bis M1 mit 403 (nicht 401, weil es kein Anmeldeverfahren gibt). Getestet ist beides: anonym 403, mit angemeldetem Benutzer 200. Bitte in M1 bewusst setzen.
- **Nur `django.contrib.auth` und `contenttypes`** sind dazugekommen (Voraussetzung für `AbstractUser`). Keine Sitzungen, kein Admin, keine Auth-Middleware, keine Passwort-Validatoren (`AUTH_PASSWORD_VALIDATORS` ist leer) – alles M1.
- **Nur JSON:** Renderer und Parser sind auf JSON beschränkt; die durchklickbare DRF-Oberfläche ist aus (sie bräuchte Templates und statische Dateien).
- **Health-Endpunkt prüft nur den Prozess**, nicht die Datenbank (so verlangt). Eine Prüfung der Bausteine ist Auftrag 010.
- **Healthcheck braucht `localhost` in `TWOX_ALLOWED_HOSTS`.** Er ruft `http://localhost:8000/api/v1/health/` im Container auf (per Python, das Image hat kein curl). Steht `localhost` nicht in der Liste und ist `TWOX_DEBUG` aus, antwortet Django mit 400 und der Dienst wird nie `healthy`. In `.env.example` vermerkt. Ob das für den Betrieb so bleiben soll, ist nicht entschieden.
- **Ruff-Ausnahme für Migrationen** (`E501`, `RUF012`) in `pyproject.toml`: Die von Django erzeugte Migration hält die Regeln nicht ein; sie von Hand umzuschreiben wäre fehleranfällig. Die Migration ist mit `ruff format` formatiert, sonst unverändert.
- **uvicorn mit einem Prozess** und ohne Extra `standard` (kein uvloop, httptools). Anzahl der Prozesse und Proxy-Kopfzeilen sind nicht eingestellt.
- **Schema:** Es gibt keinen Schema-Endpunkt, nur `manage.py spectacular`. Die Version im Schema ist fest `0.0.0`.
- Der zweite Commit (Benutzermodell) ist für sich allein nicht lauffähig; `AUTH_USER_MODEL` folgt im dritten. Geprüft ist der Endstand.
- `backend/pyproject.toml` und `backend/uv.lock` sind geändert (nur die genannten Abhängigkeiten, das mypy-Plugin und die Ruff-Ausnahme) – beim Zusammenführen mit 006 und 101 zu beachten. `uv.lock` danach im Container mit `uv lock` neu erzeugen statt von Hand zusammenzuführen.
- Die Images `twox-005-backend-dev`, `twox-005-api` und `twox-005-migrate` liegen noch lokal vor; Container, Netz und Volume sind entfernt.
- Nicht geprüft: Abruf über den Host-Port 18005 (laut Auftrag nur im Container), Bau unter Linux/CI, ältere Compose-Versionen.
- Keine offenen Fragen an a7.
