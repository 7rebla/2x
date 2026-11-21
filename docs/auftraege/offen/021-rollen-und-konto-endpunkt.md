# Auftrag 021 – Rollen „Verwalten“ und „Lesen“, Konto-Endpunkt, Befehl zum Anlegen von Konten

Meilenstein: M1 · Freigabestufe: C · Status: offen

## Ziel

Es gibt die Rollen „Verwalten“ und „Lesen“ (Startunterlage 4). Die API kann sie prüfen, die Oberfläche kann sie abfragen. Konten mit Rolle lassen sich ohne Oberfläche wiederholbar anlegen, für Betrieb, CI und Abnahme.

## Umfang

- Rollen als Django-Gruppen nach Frage 1 (Empfehlung):
  - Gruppen `manage` und `read`, angelegt per Datenmigration in `accounts` (`0002_…`).
  - Anzeigenamen „Verwalten“/„Manage“ und „Lesen“/„Read“ mit `gettext_lazy`.
- `backend/twox/accounts/roles.py`: Konstanten und `user_role(user) -> Literal[\"manage\", \"read\"] | None`. Ein Superuser zählt als `manage`.
- `backend/twox/accounts/permissions.py`, DRF-Rechteklassen:
  - `CanRead`: angemeldet und Rolle `read` oder `manage`.
  - `CanManageOrReadOnly`: lesende Methoden für `read` und `manage`, schreibende nur für `manage`.
  - `CanManage`: nur `manage`.
  - Wer angemeldet ist, aber keine Rolle hat, bekommt mit diesen Klassen 403.
- Endpunkt `GET /api/v1/me/` in `twox/accounts/urls.py` (eingebunden seit 016):
  - Rechte: `IsAuthenticated`, also auch ohne Rolle erreichbar.
  - Felder: `username`, `role` (`manage`, `read` oder `null`), `is_superuser`.
  - Typisierter Serializer, im Schema enthalten.
- Management-Befehl `create_account <username> --role manage|read [--update]`:
  - Das Kennwort kommt aus der Umgebungsvariable `TWOX_ACCOUNT_PASSWORD` oder interaktiv, nie als Argument. Ohne Variable und ohne Terminal bricht der Befehl mit Exit-Code ungleich 0 ab.
  - Das Kennwort wird mit den Prüfern aus 016 geprüft.
  - Bestehendes Konto ohne `--update`: Fehler, Exit-Code ungleich 0.
  - Mit `--update`: setzt Rolle und Kennwort des bestehenden Kontos (oder legt es an), Exit-Code 0. Damit ist der Befehl wiederholbar; die CI nutzt ihn so (Auftrag 027).
  - Der Befehl setzt nie `is_staff` oder `is_superuser`.
- `backend/twox/accounts/admin.py`: `accounts.User` mit Djangos `UserAdmin` registrieren. Die Admin-Seite aus 016 lässt nur Superuser ein.
- Tests `backend/tests/accounts/`:
  - Rechteklassen für alle Kombinationen (anonym, ohne Rolle, `read`, `manage`, Superuser) mit lesenden und schreibenden Methoden.
  - `me` anonym (403), ohne Rolle (200, `role: null`), mit Rolle.
  - Befehl:
    - Das Kennwort steht nicht in der Ausgabe.
    - Ein schwaches Kennwort wird abgewiesen.
    - Ein zweiter Aufruf ohne `--update` scheitert, mit `--update` gelingt er und ändert das Kennwort.
    - `is_staff` und `is_superuser` bleiben `False`.
  - Die Gruppen existieren nach der Migration.
- `backend/tests/config/expected_paths/accounts.py`: `/api/v1/me/` ergänzen.
- Schema und Client neu erzeugen.

## Nicht-Ziele

- Anmeldung (020), Benutzerverwaltung in der Oberfläche.
- Rechte je Standort oder je Objekt.
- Ein Rollenfeld am Benutzermodell; `test_user_model.py` bleibt unverändert.
- Standard-Rechteklasse der API (Auftrag 025).

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/accounts/`:
  - neu: `roles.py`, `permissions.py`, `serializers.py`, `views.py`, `admin.py`, `management/commands/create_account.py`, `migrations/0002_…`
  - `urls.py` füllen
- `backend/tests/accounts/` (neue Testdateien), `backend/tests/config/expected_paths/accounts.py`
- `web/openapi/schema.yml`, `web/src/api/generated/**`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-021`, `W` für `docker compose -p twox-021-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18021` setzen.
- Unter Git Bash vor Befehlen mit `/out/…` `MSYS_NO_PATHCONV=1` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Konto anlegen und wiederholen (`<Testkennwort>` ist ein selbst gewählter Entwicklungswert):
   - `D exec -T -e TWOX_ACCOUNT_PASSWORD=<Testkennwort> api python manage.py create_account reader1 --role read` endet mit Exit-Code 0; die Ausgabe enthält das Kennwort nicht.
   - Derselbe Aufruf noch einmal endet mit Exit-Code ungleich 0.
   - Mit `--update` endet er mit Exit-Code 0.
3. Anonym:
   ```
   D exec api python -c \"import urllib.request as u, urllib.error as e
   try: u.urlopen('http://localhost:8000/api/v1/me/')
   except e.HTTPError as x: print(x.code)\"
   ```
   gibt `403` aus.
4. Prüfungen und Typen:
   - `D run --rm backend-dev ruff check .` meldet `All checks passed!`.
   - `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0.
   - `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
5. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen. `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
6. `D run --rm backend-dev python manage.py makemigrations --check --dry-run` meldet `No changes detected`.
7. Schema:
   - `D run --rm -v \"$PWD/web/openapi:/out\" backend-dev python manage.py spectacular --file /out/schema.yml` endet ohne Warnungen.
   - Das committete Schema enthält `/api/v1/me/`.
   - `git diff --exit-code -- web/openapi` zeigt danach keinen Unterschied.
8. Client:
   - `W --profile dev build web-dev`, `W run --rm web-dev npm ci`, `W run --rm web-dev npm run api:generate`; danach zeigt `git diff --exit-code -- web/openapi web/src/api` keinen Unterschied.
   - `W run --rm web-dev npm run typecheck` und `… npm run test` enden mit Exit-Code 0.
9. Abräumen: `D --profile dev down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); 016 ist nach `main` zusammengeführt; Antwort von a7 auf Frage 1.

- Welle 2, parallel zu 020 und 022.
- Nicht anfassen: `settings.py`, `config/urls.py`, `pyproject.toml`, `accounts/adapter.py` (020).
- Einziger Auftrag der Welle mit Migrationen von `accounts` und mit Änderungen an Schema und Client.
- **Keine neue Abhängigkeit.**
- `<Testkennwort>` ist ein selbst gewählter Entwicklungswert und wird nicht in Dateien committet.
- Die Rechteklassen nutzen die Aufträge 025, 026, 028, 029 und 031. Ihre Namen im Kurzbericht nennen und nicht nachträglich umbenennen.
- Der genaue Aufruf mit `--update` wird in Auftrag 027 der CI-Schritt für das Testkonto. Die Bedeutung von `--update` (Rolle und Kennwort setzen, Exit-Code 0) nicht ändern.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

1. **Wie werden die Rollen abgebildet?**
   - (a) Zwei Django-Gruppen (`manage`, `read`) und eigene DRF-Rechteklassen, die die Gruppenzugehörigkeit prüfen.
   - (b) Django-Gruppen mit Modellrechten und DRF `DjangoModelPermissions`. Die Datenmigration muss dann die Rechte aller späteren Modelle kennen.
   - (c) Ein Feld `role` am Benutzermodell.
   - Empfehlung: (a). Zwei feste Rollen, keine Rechtepflege je Modell; Gruppen sind im Admin sichtbar und später um Rechte je Standort erweiterbar.
2. **Wer legt Konten an?**
   - (a) Nur Superuser, im Admin und mit `create_account`; keine Selbstregistrierung, kein Kennwort-Zurücksetzen per E-Mail in M1.
   - (b) Offene Registrierung mit Freischaltung durch „Verwalten“.
   - (c) Zusätzlich eine Benutzerverwaltung für „Verwalten“ in der Oberfläche.
   - Empfehlung: (a) in M1.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
