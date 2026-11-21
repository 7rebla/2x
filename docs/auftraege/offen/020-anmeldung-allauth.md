# Auftrag 020 – Anmeldung mit lokalen Konten über django-allauth, mit Ratenbegrenzung

Meilenstein: M1 · Freigabestufe: C · Status: zur Prüfung

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

**Status: zur Prüfung.** Alle Akzeptanzkriterien erfüllt; Prüfungen am 21.11.2026 im Container nach dem letzten Code-Stand.

### Was wurde gebaut?

- `backend/pyproject.toml`, `backend/uv.lock`: `django-allauth[headless]>=65.22.1,<65.23`. `uv lock` (im Builder-Image, weil das Dev-Image mit altem Lock nicht baut) hat genau die fünf erwarteten Pakete ergänzt. mypy-Override `follow_untyped_imports = true` für `allauth.*`: allauth hat Annotationen, aber kein `py.typed`; ohne Override wäre jeder Import `Any` bzw. ein Fehler unter `strict`.
- `backend/scripts/license-rules.txt`: `allow | MIT-0` mit Verweis auf E-45.
- `backend/twox/config/settings.py`:
  - `allauth`, `allauth.account`, `allauth.headless` in `INSTALLED_APPS`; `AccountMiddleware` als letzte Middleware (nach Authentication).
  - `AUTHENTICATION_BACKENDS` = `ModelBackend` + `allauth.account.auth_backends.AuthenticationBackend`.
  - `HEADLESS_ONLY = True`, `HEADLESS_CLIENTS = ("browser",)`, `ACCOUNT_LOGIN_METHODS = {"username"}`, `ACCOUNT_ADAPTER = "twox.accounts.adapter.AccountAdapter"`, `ACCOUNT_EMAIL_VERIFICATION = "none"`, `ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS = False`.
  - `ACCOUNT_RATE_LIMITS = {"login_failed": "10/m/ip,5/300s/key", "login": "30/m/ip"}` (Frage 3 a; dieselbe Schreibweise wie der Standard in allauth 65.22.1). allauth zählt über `django.core.cache.cache`, also im `RedisCache` aus 016 (Valkey, Datenbank 2).
  - `LOGGING`: Logger `twox` ab INFO auf stderr (Djangos eigenes Logging unverändert).
  - Kein `HEADLESS_FRONTEND_URLS`: allauth verlangt sie nur für Links in E-Mails (siehe Abweichung 1).
- `backend/twox/config/urls.py`: `_allauth/` → `allauth.headless.urls`, `accounts/` → `allauth.urls`. Mit `HEADLESS_ONLY` und ohne `socialaccount` registriert `accounts/` derzeit keine Pfade (getestet: `/accounts/login/` ist 404); eingebunden, weil allauth dort später die Rückrufadressen von OpenID Connect erwartet.
- neu `backend/twox/accounts/adapter.py` (`AccountAdapter`):
  - `is_open_for_signup` → `False`.
  - `send_mail` und `send_confirmation_mail` senden nichts (Protokollzeile „No email sent …“); `get_reset_password_from_key_url` gibt `""` zurück.
  - `authentication_failed` schreibt `Failed sign-in for username '<name>'.` (WARNING, Logger `twox.accounts.adapter`); `pre_authenticate` schreibt bei Sperre durch die Ratenbegrenzung `Sign-in blocked by the rate limit for username '<name>'.`. Nur der Benutzername, mit `%r` (keine Zeilenumbrüche aus Eingaben im Protokoll), kein Kennwort, keine IP-Adresse.
  - Gewählt statt des Signals `user_login_failed`: Der Haken gehört zum Adapter (eine Datei im Auftragsbereich), ein Signal hätte eine Registrierung in `accounts/apps.py` gebraucht (gleicher Ordner wie 021). Folge: Fehlversuche über das Admin-Formular werden nicht protokolliert (fällt mit 030 weg).

**Pflichtangaben laut allauth 65.22.1** (am installierten Quelltext geprüft): `django.contrib.sites` ist **nicht** nötig (allauth fragt nur `apps.is_installed`). Nötig sind die drei Apps, `AccountMiddleware`, das Backend und die URL-Einbindung `_allauth/`. `manage.py check` meldet keine Probleme. allauth bringt 9 Migrationen der App `account` mit (`EmailAddress`, `EmailConfirmation`); `headless` hat keine.

**Später für OpenID Connect und Zwei-Faktor** (nicht installiert; aus der allauth-Doku, nicht am Quelltext nachgeprüft): OIDC – App `allauth.socialaccount` und `allauth.socialaccount.providers.openid_connect`, Extra `socialaccount` (zieht laut Fragen-Liste certifi/MPL-2.0 und requests nach), `SOCIALACCOUNT_PROVIDERS["openid_connect"]` mit `APPS` (client_id, secret, `server_url`), `HEADLESS_FRONTEND_URLS["socialaccount_login_error"]`; die Rückrufadressen liegen dann unter `accounts/oidc/<id>/login/callback/` (deshalb ist `accounts/` schon eingebunden). Zwei-Faktor – App `allauth.mfa`, Extra `mfa` (fido2), `MFA_SUPPORTED_TYPES` und ggf. `MFA_PASSKEY_*`; Rate-Limit-Einträge `mfa_*` prüfen. Beides fügt Migrationen hinzu.

**Antwortcode bei Sperre:** Nach 5 falschen Kennwörtern für ein Konto antwortet allauth mit **400** und Fehlercode `too_many_login_attempts` (nicht 429), auch bei richtigem Kennwort. **429** kommt erst über die Grenze `login` (31. Anmeldeversuch je Minute und IP-Adresse). Beides ist getestet.

### Neue Pakete im Lock (alle Laufzeit)

Lizenz laut Paket-Metadaten (`License-Expression`) im Container, gegengelesen mit `check-licenses.sh`:

| Paket | Version | Lizenz | mitgezogen von |
| --- | --- | --- | --- |
| django-allauth | 65.22.1 | MIT | direkt (Extra `headless`) |
| pyjwt | 2.15.1 | MIT | django-allauth[headless] (`pyjwt[crypto]`) |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | pyjwt[crypto] |
| cffi | 2.1.1 | MIT-0 | cryptography (nur CPython) |
| pycparser | 3.12 | BSD-3-Clause | cffi (nur CPython) |

asgiref und Django waren schon im Lock. Keine weiteren Änderungen am Lock. Lizenzprüfung: 58 Pakete (vorher 53).

**Im Rad gebündelte Bestandteile** (linux/x86_64, abgelesen an Rad, `ldd` und SBOM):

- cryptography 50.0.2 (`cp311-abi3-manylinux_2_34_x86_64`, gebaut mit maturin): eine einzige Bibliothek `_rust.abi3.so`, hängt nur von `libc` und `libgcc_s` ab. **OpenSSL 4.0.3 (29 Sep 2026) ist statisch eingebunden** (Zeichenkette in der Datei und `openssl_version_text()` zur Laufzeit), Lizenz Apache-2.0. Das Rad liefert zwei CycloneDX-SBOMs unter `dist-info/sboms/`: `sbom.json` nennt nur `openssl 4.0.3` (ohne Lizenzangabe); `cryptography-rust.cyclonedx.json` nennt 39 Rust-Crates: die eigenen `cryptography-*` (Apache-2.0 OR BSD-3-Clause), asn1/asn1_derive (BSD-3-Clause), openssl 0.10.81 (Apache-2.0), openssl-sys 0.9.117 und pem (MIT), sonst MIT OR Apache-2.0. Auffällig: `self_cell 1.3.0` mit „Apache-2.0 OR GPL-2.0-only“ (Wahl Apache-2.0 möglich), `target-lexicon` „Apache-2.0 WITH LLVM-exception“ und `unicode-ident` „(MIT OR Apache-2.0) AND Unicode-3.0“ – die letzten beiden gehören zu Bauwerkzeugen (pyo3-build-config, proc-macro2/syn) und landen nach meinem Verständnis nicht im Binärcode; nicht am Binärcode nachgeprüft. Kein GPL-only, kein AGPL, keine Nutzungsbeschränkung.
- cffi 2.1.1 (`cp314-manylinux2014_x86_64`): `_cffi_backend.so` hängt nur von `libc`/`libpthread` ab, kein Ordner `cffi.libs`. **libffi ist statisch eingebunden** (`ffi_call` in der Datei); Version nicht ablesbar, keine SBOM im Rad. libffi steht unter MIT (Wissensstand, nicht am Rad belegt).
- pyjwt, pycparser, django-allauth: reiner Python-Code.

Vorschlag für die Tabelle „Abhängigkeiten“: `django-allauth 65.22.1 (Extra headless) mit pyjwt 2.15.1, cryptography 50.0.2, cffi 2.1.1, pycparser 3.12 | MIT; cryptography Apache-2.0 OR BSD-3-Clause; cffi MIT-0; pycparser BSD-3-Clause; im cryptography-Rad statisch OpenSSL 4.0.3 (Apache-2.0) und Rust-Crates laut SBOM (MIT/Apache/BSD; self_cell wahlweise Apache-2.0); im cffi-Rad statisch libffi (MIT) | Anmeldung (E-38) | 020 | E-45`.

### Wie wurde getestet?

`D` = `docker compose -p twox-020`, `.env` aus `.env.example` mit `TWOX_API_PORT=18020`; Docker Engine 29.9.3, Compose v5.7.0.

| AK | Ergebnis |
| --- | --- |
| 0 | erfüllt: `docker version` (29.9.3) und `docker compose version` (v5.7.0), Exit 0 |
| 1 | erfüllt: Bau Exit 0, `up -d --wait` Exit 0; `D logs migrate` zeigt `account.0001_initial` bis `account.0009_emailaddress_unique_primary_email ... OK` |
| 2 | erfüllt: `200` |
| 3 | erfüllt: `All checks passed!`; `71 files already formatted` (Exit 0); `Success: no issues found in 71 source files` |
| 4 | erfüllt: `213 passed, 4 deselected`, 0 fehlgeschlagen, 0 übersprungen; `pytest -m worker`: `4 passed` |
| 5 | erfüllt: `No changes detected` |
| 6 | erfüllt: `License check passed.` (58 Pakete, darunter `MIT-0` 1) |
| 7 | erfüllt: `spectacular` Exit 0, `git diff --exit-code -- web/openapi` ohne Unterschied, keine neuen Dateien. Schema und Client unverändert, der web-Job war nicht nötig |
| 8 | erfüllt: Bau, `pull e2e`, `npm ci` (420 Pakete) Exit 0; `2 passed` |
| 9 | erfüllt: `down -v` Exit 0; danach kein Container und kein Volume des Projekts `twox-020` |

`backend/tests/accounts/test_login.py` (22 Fälle; Prüfansicht `ProbeView` nur im Test, `@pytest.mark.urls`, Client mit `enforce_csrf_checks=True`, CSRF-Cookie über `/`; MD5-Hasher nur in diesem Modul für Tempo): Anmeldung 200 und danach Prüfansicht 200 mit Sitzungs-Cookie (vorher 403); falsches Kennwort 400 `username_password_mismatch`, keine Sitzung, genau eine WARNING-Zeile mit Benutzername, kein Kennwort im Protokoll; unbekannter Benutzer ebenso; ohne CSRF-Token 403; nach 5 Fehlversuchen 400 `too_many_login_attempts` auch mit richtigem Kennwort und Protokollzeile zur Sperre; Zählung je Konto über neue Clients hinweg; 4 Fehlversuche sperren nicht; nach `cache.clear()` ist das Konto wieder frei (Zählung im Django-Cache); 31. Versuch je IP 429; `GET session` 401 abgemeldet / 200 angemeldet; `DELETE session` 401 und danach abgemeldet; `DELETE` ohne CSRF 403, Sitzung bleibt; Signup 403, kein Benutzer angelegt, `config` meldet `is_open_for_signup: false`; Kennwort-Rücksetzung für bekannte und unbekannte Adresse je 200 ohne E-Mail; E-Mail-Adresse hinzufügen 200 ohne E-Mail; `config` 200 mit `login_methods ["username"]`; Client `app` nicht vorhanden (404); `/accounts/login/` und `/accounts/signup/` 404; Einstellungen (Ratenbegrenzung, Backends, Headless). `tests/config/test_settings.py`: drei allauth-Apps installiert, `socialaccount`, `mfa`, `usersessions` und `django.contrib.sites` nicht; Middleware-Liste mit `AccountMiddleware`.

Zusätzlich im laufenden Stack (Testkonto `test-probe` mit Testkennwort, per `manage.py shell` angelegt): 5 falsche Kennwörter, danach richtiges → 400 `too_many_login_attempts`. In Valkey Datenbank 2 liegen die Schlüssel `:1:allauth:rl:allauth.account:login_failed:5/300.0/key:<sha256>`, `…login_failed:10/60/ip:ip:127.0.0.1` und `…login:30/60/ip:ip:127.0.0.1`. Nach Neustart des API-Containers (neuer Prozess) bleibt die Sperre bestehen; nach `FLUSHDB` meldet die Anmeldung 200. `D logs api` zeigt fünf Zeilen `Failed sign-in for username 'test-probe'.` und zwei `Sign-in blocked …`; die Kennwörter kommen im Protokoll nicht vor. Zwei gleichzeitig laufende API-Prozesse habe ich nicht gestartet; die Gemeinsamkeit folgt aus der Ablage in Valkey.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-adb5586448f4c5180`
- Arbeitsverzeichnis: `.claude/worktrees/agent-adb5586448f4c5180` (relativ zum Projektordner)

### Abweichungen und Hinweise

1. **E-Mail-Wege von allauth führten ohne `HEADLESS_FRONTEND_URLS` zu Fehler 500.** Die Headless-API bietet weiter `auth/password/request` (anonym) und `account/email` (angemeldet). allauth baut den Link für die E-Mail, bevor es sie versendet, und verlangt dafür mit `HEADLESS_ONLY` eine Seiten-Adresse der Oberfläche. Gelöst ohne Frontend-URLs: Adapter baut keinen Bestätigungs- und Rücksetzlink und sendet nichts, `ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS = False`. Ergebnis: Rücksetzanfrage für bekannte und unbekannte Adresse gleich 200 (keine Aufzählung von Konten), keine E-Mail. Ein Zurücksetzen ist damit nicht möglich, weil der Schlüssel den Server nie verlässt. Die Endpunkte antworten aber weiter; ob sie ganz abgeschaltet werden sollen (z. B. 404 über eigene URL-Muster vor der allauth-Einbindung), wäre eine Frage für 030.
2. **Kennwort ändern ist per API möglich.** `POST /_allauth/browser/v1/account/password/change` ist für angemeldete Benutzer aktiv (allauth-Standard; Ratenbegrenzung `change_password` 5/m/user). E-38 sieht für M1 keine eigene Kennwortänderung vor; laut Auftrag Nicht-Ziel und Frage an a7 in 030. Ebenso kann ein angemeldeter Benutzer über `account/email` E-Mail-Adressen hinzufügen (ohne Bestätigung und ohne Versand). Nicht abgeschaltet, nur vermerkt.
3. **Admin-Anmeldung ohne Ratenbegrenzung und ohne Protokollzeile** bis Auftrag 030 (nur Entwicklung): `login_failed` gilt nur für allauth, und die Protokollzeile hängt am allauth-Adapter, nicht am Signal `user_login_failed`.
4. **IP-Zählung hinter einem Proxy:** allauth nimmt `REMOTE_ADDR` (`ALLAUTH_TRUSTED_PROXY_COUNT` = 0). Hinter einem Reverse-Proxy (M6) zählen alle Benutzer auf die Proxy-Adresse; dann `ALLAUTH_TRUSTED_PROXY_COUNT` oder `ALLAUTH_TRUSTED_CLIENT_IP_HEADER` setzen.
5. **Neue Einstellung `LOGGING`** (Logger `twox`, INFO, stderr) in `settings.py` – nicht ausdrücklich im Auftrag, aber nötig, damit die Zeilen ohne Umweg über Pythons Notfall-Handler im Serverprotokoll erscheinen.
6. **mypy-Override in `pyproject.toml`** (`follow_untyped_imports` für allauth), siehe oben.
7. Nicht geprüft: Lauf in der GitHub-CI (kein Push), Räder für arm64 oder musl, libffi-Version im cffi-Rad, Binärinhalt der Rust-Crates mit Sonderlizenz.

Keine offenen Fragen, die diesen Auftrag aufhalten. `docs/DECISIONS.md` und `docs/STATUS.md` nicht geändert.

### Nacharbeit (nach Prüfung der Leitstelle)

**Geschlossene Pfade.** `backend/twox/config/urls.py` hat jetzt ein Muster `CLOSED_ALLAUTH_PATH`. Es steht vor der Einbindung von `allauth.headless.urls` und antwortet über `closed_allauth_endpoint` mit 404, für die Clients `browser` und `app`. Die Pfade habe ich an `allauth/headless/account/urls.py` (65.22.1) im Container abgelesen:

- `/_allauth/{browser,app}/v1/account/password/change`
- `/_allauth/{browser,app}/v1/account/email`
- `/_allauth/{browser,app}/v1/auth/password/request`
- `/_allauth/{browser,app}/v1/auth/password/reset`

Das Muster trifft nur genau diese Pfade. Der Client `app` ist ohnehin nicht freigegeben (`HEADLESS_CLIENTS`), sein Pfad wäre also auch ohne das Muster 404. Der Adapter, der keine E-Mail versendet, bleibt als zweite Sicherung. Seine Tests in `test_login.py` laufen weiter gegen eine eigene Test-URL-Konfiguration ohne das Muster.

Damit sind die Abweichungen 1 und 2 oben erledigt, soweit sie Kennwort ändern, Zurücksetzen und E-Mail-Verwaltung betreffen.

**Tests:** neu `backend/tests/accounts/test_closed_endpoints.py`, 21 Fälle:
- Jeder der vier Pfade existiert in allauth selbst. Der Test gegen eine URL-Konfiguration nur mit allauth schlägt fehl, wenn allauth einen Pfad später umbenennt und das Muster ihn deshalb verfehlt.
- Je Pfad, Client und Zustand (anonym oder angemeldet) liefern GET und POST 404.
- Gegen die Projekt-URL-Konfiguration funktionieren weiter: `config` 200, `session` anonym 401, Anmeldung mit CSRF 200, `session` 200, Abmelden per `DELETE` 401, danach `session` 401.
- Im laufenden Stack zusätzlich geprüft: die vier Pfade 404, `auth/session` 401, `config` 200.

**Zusammenführen mit `main`:** `git merge main` (Merge-Commit `b22aa6f`) ohne Konflikte. `main` enthielt 017, 021, 022, 023 und 024. Danach liefen alle Prüfungen erneut, mit `docker compose -p twox-020` und `TWOX_API_PORT=18020`:

| Prüfung | Ergebnis |
| --- | --- |
| Bau `migrate api worker backend-dev web-dev`, `up --wait` | Exit 0 |
| config-Endpunkt im API-Container | 200 |
| `ruff check` | `All checks passed!` |
| `ruff format --check` | 96 Dateien formatiert, Exit 0 |
| `mypy` | `Success: no issues found in 96 source files` |
| `pytest` | `472 passed, 4 deselected`, nichts übersprungen |
| `pytest -m worker` | `4 passed` |
| `makemigrations --check --dry-run` | `No changes detected` |
| Lizenzprüfung | `License check passed.` (58 Pakete) |
| OpenAPI-Schema | unverändert, keine neuen Dateien; web-Job daher nicht nötig |
| e2e (`pull`, `npm ci` mit 425 Paketen, `up`, `run e2e`) | `5 passed` |
| `--profile dev --profile e2e down -v` | Exit 0; kein Container und kein Volume von twox-020 übrig |

**Commits der Nacharbeit:** `b22aa6f` (Merge von main), `9ae5f52` (Pfade schließen und Tests), dazu der Commit dieses Abschnitts.
