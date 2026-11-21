# Auftrag 020 – Anmeldung mit lokalen Konten über django-allauth, mit Ratenbegrenzung

Meilenstein: M1 · Freigabestufe: C · Status: offen

## Ziel

Benutzer melden sich mit lokalem Konto (Benutzername und Kennwort) an und ab. Die Oberfläche nutzt dafür die Browser-Schnittstelle von django-allauth im Headless-Modus am selben Ursprung (Startunterlage 5.2: „lokale Konten, OpenID Connect und Zwei-Faktor über django-allauth“). Fehlversuche werden begrenzt, über alle API-Prozesse hinweg. OpenID Connect und Zwei-Faktor brauchen später nur Einstellung und Extra.

## Umfang

- Abhängigkeit `django-allauth[headless]` 65.22.1 (nach Frage 1 und 2) in `backend/pyproject.toml` und `backend/uv.lock`.
- Einstellungen:
  - `allauth`, `allauth.account` und `allauth.headless` in `INSTALLED_APPS`.
  - `allauth.account.middleware.AccountMiddleware`.
  - `AUTHENTICATION_BACKENDS`: `ModelBackend` und das Backend von allauth.
  - `HEADLESS_ONLY = True`, `HEADLESS_CLIENTS = (\"browser\",)`, `ACCOUNT_LOGIN_METHODS = {\"username\"}`.
  - Keine Selbstregistrierung: eigener `ACCOUNT_ADAPTER` mit `is_open_for_signup` = `False`.
  - Keine E-Mail-Bestätigung und kein E-Mail-Versand (Betrieb ohne Internet).
  - `HEADLESS_FRONTEND_URLS` nur, soweit allauth sie verlangt.
  - Weitere Pflichtangaben laut Doku der Version (z. B. ob `django.contrib.sites` nötig ist) im Kurzbericht nennen.
- Ratenbegrenzung:
  - `ACCOUNT_RATE_LIMITS` ausdrücklich setzen, mindestens `login_failed` und `login`, Werte nach Frage 3.
  - Gezählt wird im gemeinsamen Valkey-Zwischenspeicher aus 016, nicht je Prozess.
- Fehlgeschlagene Anmeldungen landen mit Benutzername, ohne Kennwort, im Serverprotokoll (z. B. über das Signal `user_login_failed`).
- `config/urls.py`: `_allauth/` (Headless) und `accounts/` einbinden, soweit allauth das verlangt. Beide Pfade sind seit 016 vom Catch-all der Oberfläche ausgenommen.
- Tests `backend/tests/accounts/test_login.py`:
  - Eine geschützte Ansicht gibt es noch nicht. Deshalb wird eine Prüfansicht nur im Test angelegt, nach dem Muster von `ProbeView` mit `@pytest.mark.urls` in `tests/config/test_api.py`.
  - `POST /_allauth/browser/v1/auth/login` mit gültigem Konto und CSRF-Token ergibt 200; danach liefert die Prüfansicht mit dem Sitzungs-Cookie 200.
  - Falsches Kennwort: 400, keine Sitzung, Eintrag im Serverprotokoll ohne Kennwort (`caplog`).
  - Ohne CSRF-Token: 403.
  - Nach der in Frage 3 festgelegten Zahl falscher Kennwörter antwortet die Anmeldung mit 429 (oder dem Code, den allauth dafür nutzt; im Kurzbericht nennen), auch mit richtigem Kennwort.
  - `GET /_allauth/browser/v1/auth/session` meldet angemeldet und abgemeldet richtig; `DELETE` meldet ab.
  - Registrierung ist abgeschaltet: Ein Aufruf des Signup-Endpunkts wird abgewiesen.
- Lizenzprüfung: `MIT-0` (cffi) nur nach Freigabe (Frage 2) in `backend/scripts/license-rules.txt` aufnehmen.

## Nicht-Ziele

- Rollen, Konto-Endpunkt `me`, Anlegen von Konten (021). Anmeldeseite der Oberfläche und Umleitung der Admin-Anmeldung (030).
- OpenID Connect (`socialaccount`) und Zwei-Faktor (`mfa`): nicht installieren. Im Kurzbericht festhalten, welche Einstellungen später nötig sind.
- Kennwort zurücksetzen per E-Mail; Kennwort ändern (Frage an a7 in 030).
- `XSessionTokenAuthentication`, JWT (erst für Nicht-Browser-Clients).

## Betroffene Bereiche (Ordner, Dateien)

- `backend/pyproject.toml`, `backend/uv.lock`, ggf. `backend/scripts/license-rules.txt`
- `backend/twox/config/settings.py`, `backend/twox/config/urls.py`
- neu: `backend/twox/accounts/adapter.py`
- neu: `backend/tests/accounts/test_login.py`; `backend/tests/config/test_settings.py` (Apps)

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-020`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18020` setzen.
- Unter Git Bash vor Befehlen mit `/out/…` `MSYS_NO_PATHCONV=1` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0. `D logs migrate` zeigt die Migrationen von `account` als angewendet.
2. `D exec api python -c \"import urllib.request as u; print(u.urlopen('http://localhost:8000/_allauth/browser/v1/config').status)\"` gibt `200` aus.
3. Prüfungen und Typen:
   - `D run --rm backend-dev ruff check .` meldet `All checks passed!`.
   - `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0.
   - `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
4. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen. `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
5. `D run --rm backend-dev python manage.py makemigrations --check --dry-run` meldet `No changes detected`.
6. `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0. Im Kurzbericht steht die vollständige Liste der neu im Lock stehenden Pakete mit Version und Lizenz.
7. `D run --rm -v \"$PWD/web/openapi:/out\" backend-dev python manage.py spectacular --file /out/schema.yml`, danach zeigt `git diff --exit-code -- web/openapi` keinen Unterschied.
8. Der Browser-Test bleibt grün:
   - `D --profile dev build migrate api worker web-dev`
   - `D --profile e2e pull e2e`
   - `D --profile dev run --rm web-dev npm ci`
   - `D up -d --wait --wait-timeout 300 db valkey worker api`
   - `D --profile e2e run --rm e2e` meldet alle Fälle bestanden, Exit-Code 0.
9. Abräumen: `D --profile dev --profile e2e down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); 016 ist nach `main` zusammengeführt; Antworten von a7 auf Frage 1 bis 3.

- Welle 2, parallel zu 021 (`accounts`-Rollen) und 022 (Speicher).
- Dieser Auftrag ist der einzige der Welle mit `settings.py`, `config/urls.py`, `pyproject.toml` und `uv.lock`.
- Nicht anfassen: `twox/accounts/models.py`, `views.py`, `urls.py`, `permissions.py`, `admin.py` und die Migrationen von `accounts` (alles 021).
- **Neue Abhängigkeiten (nur nach Frage 2):**
  - django-allauth 65.22.1: MIT; an PyPI geprüft: Python ab 3.11, das Extra `headless` verlangt `pyjwt[crypto]>=2.0,<3`.
  - pyjwt 2.15.1: MIT.
  - cryptography 50.0.2: Apache-2.0 OR BSD-3-Clause.
  - cffi 2.1.1: `MIT-0`, steht noch nicht in den Lizenzregeln.
  - pycparser 3.12: BSD-3-Clause.
  - asgiref ist schon im Projekt.
  - Ungeprüft sind die im Rad von cryptography gebündelten Bibliotheken (OpenSSL). Im Kurzbericht nennen, was im Rad liegt.
- Muster laut allauth-Doku (headless): Der Client „browser“ nutzt die Django-Sitzung mit Cookie, es gilt CSRF-Schutz. Das passt zu `SessionAuthentication` aus 016.
- Laut allauth-Doku schützt `login_failed` nur die Anmeldung von allauth, nicht das Anmeldeformular des Admins. Bis Auftrag 030 die Admin-Anmeldung umleitet, ist dieses Formular ohne Begrenzung. Das gilt nur in der Entwicklung, im Kurzbericht vermerken.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

1. **Anmeldeverfahren**
   - (a) django-allauth im Headless-Modus, Client „browser“ (Sitzung und CSRF am selben Ursprung); die Oberfläche baut ihre eigene Anmeldeseite.
   - (b) django-allauth mit seinen serverseitig erzeugten Seiten (`/accounts/login/`). Keine Headless-Schnittstelle, kein pyjwt und kein cryptography, aber Seiten außerhalb der React-Oberfläche.
   - (c) Ohne allauth: eigene kleine Anmelde-Endpunkte mit `django.contrib.auth`. Das weicht von Startunterlage 5.2 ab.
   - Empfehlung: (a). Entspricht der Startunterlage, eine einheitliche Oberfläche in zwei Sprachen, OIDC und 2FA später ohne Umbau.
2. **Neue Abhängigkeiten** django-allauth[headless] samt pyjwt, cryptography, cffi (Lizenz MIT-0) und pycparser zulassen und MIT-0 in die Lizenzregeln aufnehmen?
   - (a) Ja.
   - (b) Nein; dann gilt Frage 1, Option (b) oder (c).
   - Empfehlung: (a). MIT-0 ist MIT ohne Nennungspflicht.
3. **Grenzen für Anmeldeversuche**
   - (a) Die Standardwerte von allauth ausdrücklich setzen: `login_failed` 10 je Minute und IP-Adresse sowie 5 je 5 Minuten und Konto; `login` 30 je Minute und IP-Adresse.
   - (b) Strenger, z. B. 5 Fehlversuche je 15 Minuten und Konto.
   - Empfehlung: (a). Die Werte stammen aus der allauth-Doku, die Zählung läuft gemeinsam in Valkey.
4. **OpenID Connect und Zwei-Faktor in M1?**
   - (a) Nicht in M1; eigene Aufträge nach der Abnahme von M1.
   - (b) In M1, mit weiteren Abhängigkeiten: certifi unter MPL-2.0, fido2 mit MPL-2.0-Anteilen.
   - Empfehlung: (a). Die M1-Abnahme verlangt beides nicht; die Lizenzfragen können getrennt entschieden werden.

Konten (wer legt sie an, Selbstregistrierung): siehe Auftrag 021, Frage 2.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
