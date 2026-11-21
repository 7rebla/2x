# Auftrag 005 – API-Grundlage

Meilenstein: M0 · Freigabestufe: C · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
