# Auftrag 034 – Backend-Übersetzung Deutsch: gettext-Kataloge, Bau und Prüfung

Meilenstein: M1 · Freigabestufe: C · Status: zur Prüfung

## Ziel

Meldungen des Backends (Fehlermeldungen der API, Import-Fehler, Bezeichnungen im Admin) erscheinen auf Deutsch, wenn die Oberfläche Deutsch anfragt (`Accept-Language`, `LocaleMiddleware` aus 016), sonst auf Englisch (E-07). Kompilierte Kataloge entstehen nie im eingebundenen Quelltext (E-34). `pytest` läuft in einem frischen Arbeitsverzeichnis ohne Vorschritt.

## Umfang

- Katalog `backend/locale/de/LC_MESSAGES/django.po` für alle eigenen, mit `gettext` oder `gettext_lazy` markierten Texte.
  - Fehlende Markierungen im eigenen Code nachziehen, ohne Änderungen an Feldern, die eine Migration auslösen würden.
  - Alle Einträge übersetzt, keine unscharfen (`fuzzy`).
- Werkzeug nach Frage 1 (Empfehlung):
  - GNU gettext im Dev-Image (`backend/Dockerfile`, Stufe `dev`) für `makemessages` und die Tests.
  - Eine eigene Bau-Stufe übersetzt die Kataloge mit `compilemessages`. Nur die `.mo`-Dateien kommen ins Laufzeit-Image, nach `/app/locale`. Im Laufzeit-Image ist kein gettext.
  - `.mo`-Dateien stehen in `.gitignore` und werden nie committet.
- Tests ohne `.mo` im Quelltext:
  - `backend/tests/conftest.py` bekommt eine Fixture für die ganze Sitzung. Sie übersetzt die Kataloge aus `/app/locale` mit `msgfmt` in ein temporäres Verzeichnis außerhalb von `/app` und setzt `LOCALE_PATHS` für die Tests darauf (z. B. `override_settings`).
  - `pytest` braucht damit keinen Vorschritt; im Bind-Mount entsteht keine `.mo`-Datei.
- CI, Job `backend` (`.github/workflows/ci.yml`): ein Schritt `Translation catalogue up to date` nach den Tests:
  ```
  docker compose run --rm backend-dev python manage.py makemessages -l de
  git diff --exit-code -I '^\"POT-Creation-Date:' -- backend/locale
  test -z \"$(git status --porcelain --untracked-files=all -- backend/locale)\"
  ```
  `git status` meldet dabei auch versehentlich entstandene `.mo`-Dateien nicht, weil sie ignoriert sind; dafür sorgt der Test unten. Dieselben Befehle in `README.md` unter „Backend“.
- Tests `backend/tests/config/test_i18n.py`:
  - Mit `Accept-Language: de` liefern API-Fehlermeldungen den deutschen Text, mit `en` den englischen. Beispiele: Import mit falschem Kopf, 409 bei doppelter Version.
  - Die Meldungen von Django und DRF (z. B. 403 ohne Anmeldung) kommen auf Deutsch.
  - `msgattrib --untranslated` und `msgattrib --only-fuzzy` auf den Katalog liefern keine Einträge.
  - Unter `/app` liegt keine `.mo`-Datei.

## Nicht-Ziele

- Übersetzung der Oberfläche (018 und die Seiten-Aufträge).
- Weitere Sprachen. Übersetzung von Daten; Geräte-Notizen bleiben, wie sie sind.

## Betroffene Bereiche (Ordner, Dateien)

- neu: `backend/locale/de/LC_MESSAGES/django.po`
- `backend/Dockerfile` (Stufen `dev` und `runtime`, neue Bau-Stufe)
- `.gitignore`, `.github/workflows/ci.yml` (Job `backend`), `README.md` (Abschnitt „Backend“)
- `backend/tests/conftest.py`, neu `backend/tests/config/test_i18n.py`
- eigener Code nur zum Markieren fehlender Texte (`backend/twox/**`, ohne Modelle)

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-034`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18034` setzen.
- Unter Git Bash vor Befehlen mit `/out/…` `MSYS_NO_PATHCONV=1` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Laufzeit-Image:
   - `D exec api sh -c \"command -v msgfmt\"` endet mit Exit-Code ungleich 0 (kein gettext im Laufzeit-Image).
   - `D exec api sh -c \"ls locale/de/LC_MESSAGES/django.mo\"` endet mit Exit-Code 0.
3. `D run --rm backend-dev pytest` endet in einem frischen Arbeitsverzeichnis ohne Vorschritt mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen. `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
4. Danach findet `git status --porcelain --ignored -- backend/locale` keine `.mo`-Datei.
5. Der Schritt `Translation catalogue up to date` wie in `ci.yml` endet mit Exit-Code 0.
6. Deutsche Meldung der API:
   ```
   D exec api python -c \"import urllib.request as u, urllib.error as e
   r=u.Request('http://localhost:8000/api/v1/me/', headers={'Accept-Language':'de'})
   try: u.urlopen(r)
   except e.HTTPError as x: print(x.read().decode())\"
   ```
   gibt die DRF-Meldung auf Deutsch aus.
7. Prüfungen und Typen:
   - `D run --rm backend-dev ruff check .` meldet `All checks passed!`.
   - `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0.
   - `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
8. `D run --rm backend-dev python manage.py makemigrations --check --dry-run` meldet `No changes detected`. `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0.
9. `D run --rm -v \"$PWD/web/openapi:/out\" backend-dev python manage.py spectacular --file /out/schema.yml`, danach zeigt `git diff --exit-code -- web/openapi` keinen Unterschied.
10. Der Browser-Test bleibt grün (Image geändert):
    - `D --profile dev build migrate api worker web-dev`
    - `D --profile e2e pull e2e`
    - `D --profile dev run --rm web-dev npm ci`
    - Schritt „Create test account“ wie in `ci.yml`
    - `D --profile e2e run --rm e2e` meldet alle Fälle bestanden.
11. Abräumen: `D --profile dev --profile e2e down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); 016, 026, 028, 029 und 031 sind nach `main` zusammengeführt, damit alle Backend-Texte von M1 vorhanden sind; Antwort von a7 auf Frage 1.

- Welle 7, parallel zu 035 und 036 (Oberfläche).
- Einziger Auftrag der Welle mit `backend/Dockerfile`, `ci.yml`, `README.md` und Backend-Code.
- Laut Django-Doku brauchen `makemessages` und `compilemessages` die GNU-gettext-Werkzeuge (mindestens 0.19). Zur Laufzeit liest Django die `.mo`-Dateien mit dem `gettext`-Modul von Python.
- Lizenz: Die Programme von GNU gettext stehen unter GPL, libintl unter LGPL (laut GNU-Handbuch).
  - Dauerhaft im Dev-Image und in einer Bau-Stufe zu liegen ist eine **neue Lizenzausnahme**. Die Einträge zu pandoc und poppler-utils taugen nicht als Vorbild: Beide sind nur Einmalwerkzeuge in keinem Projekt-Image.
  - Version des Debian-Pakets (an packages.debian.org geprüft): gettext 0.23.1-2 in Debian trixie. Ungeprüft ist, ob `python:3.14.10-slim` auf trixie beruht; die tatsächlich installierte Version im Kurzbericht nennen.
- Nach diesem Auftrag muss jeder Auftrag mit neuen Backend-Texten den Katalog aktualisieren und übersetzen; der CI-Schritt und `test_i18n.py` prüfen das.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

1. **GNU gettext (GPL) für die Backend-Übersetzung zulassen?** Das ist eine neue Lizenzausnahme nach Leitplanke 7.
   - (a) gettext dauerhaft im Dev-Image und in einer Bau-Stufe, nicht im Laufzeit-Image, nicht eingebunden. `.mo` entstehen beim Bau und in den Tests außerhalb des Quelltexts und werden nicht committet.
   - (b) `.mo`-Dateien committen (Binärdateien im Repository); gettext nur im Dev-Image.
   - (c) Kein gettext: Backend-Meldungen bleiben Englisch, die Oberfläche übersetzt bekannte Fehlercodes selbst.
   - Empfehlung: (a). Die Ausgabe eines GPL-Programms fällt laut GPL-FAQ grundsätzlich nicht unter die GPL; das Werkzeug wird nicht ausgeliefert.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Was wurde gebaut?**

- Katalog `backend/locale/de/LC_MESSAGES/django.po`: 73 Einträge, alle übersetzt, keine `fuzzy` (auch nicht im Kopf). Darin die Rollen-Anzeigenamen „Verwalten“/„Lesen“ (`ROLE_LABELS`), alle Import-Meldungen, Datei-Meldungen (413, 409, Konfiguration), Eindeutigkeits-Meldungen der Struktur, Modell- und Feldbezeichnungen. Begriffe wie in der Oberfläche (Standort, Bereich, Anlage, Gerät, Kennung, Softwarestand); Anrede „Sie“. `document` heißt „Dokument“, weil derselbe Text auch die Art (Dokument/Konfiguration) bezeichnet.
- Nachgezogene Markierungen (ohne Modelle, keine Migration): Titel des Admins (`admin_site.py`, „2x-Verwaltung“), Namen der Apps im Admin (`apps.py` von accounts „Konten“, assets „Struktur“, files „Dateien“; englisch „Accounts“, „Structure“, „Files“ – vorher zeigte der Admin „Assets“).
- `twox/files/uploads.py`: Die 413-Antwort der ASGI-Hülle entsteht vor Django und damit vor `LocaleMiddleware`; sie war deshalb immer Englisch. Neue Funktion `scope_language()` wählt die Sprache wie `LocaleMiddleware` aus `Accept-Language` (Sprach-Cookie und URL-Präfix werden nicht ausgewertet; beides nutzt das Projekt nicht).
- `backend/Dockerfile`: GNU gettext im Dev-Image (Stufe `dev`) und in der neuen Bau-Stufe `locale-build`, die `compilemessages` ausführt, alle Nicht-`.mo`-Dateien entfernt und prüft, dass eine `.mo` entstanden ist. Das Laufzeit-Image übernimmt nur `/app/locale` mit den `.mo`-Dateien. Installierte Version: Debian-Paket gettext 0.23.1-2, `msgfmt (GNU gettext-tools) 0.23.1`; `python:3.14.10-slim` beruht auf Debian trixie (13.7).
- `.gitignore`: `*.mo`.
- `backend/tests/conftest.py`: Fixture für die ganze Sitzung übersetzt jede `.po` unter `LOCALE_PATHS` mit `msgfmt --check` nach `/tmp/pytest-of-…/locale…` und setzt `LOCALE_PATHS` per `override_settings` darauf.
- `backend/tests/config/test_i18n.py` (26 Fälle): Import mit falschem Kopf de/en, Django-Meldung im Import auf Deutsch, 409 bei doppelter Version de/en, DRF-403 auf `/api/v1/me/` mit `de`, `de-DE,…`, `en`, `fr` und ohne Kopf, 413 der ASGI-Hülle de/en/ohne Kopf, `scope_language`, Rollen- und Admin-Bezeichnungen auf Deutsch, `msgattrib --untranslated`/`--only-fuzzy` leer, keine `.mo` unter `/app`, Test-Kataloge liegen außerhalb von `/app`. Eine Fixture setzt nach jedem Test die Standardsprache zurück (`LocaleMiddleware` lässt die Sprache der letzten Anfrage aktiv).
- CI-Job `backend`: Schritt „Translation catalogue up to date“ nach den Worker-Tests, Befehle wörtlich wie im Auftrag; dieselben Befehle mit Hinweisen in `README.md` unter „Backend“.

**Wie wurde getestet?** (Compose-Projekt `twox-034`, `TWOX_API_PORT=18034`)

0. `docker version`, `docker compose version`: Exit 0.
1. Bau `migrate api worker backend-dev` und `up -d --wait …`: Exit 0.
2. `exec api sh -c "command -v msgfmt"`: Exit 127 (ungleich 0). `ls locale/de/LC_MESSAGES/django.mo`: Exit 0. Zusätzlich im laufenden Laufzeit-Image: kein `msg*`, `xgettext`, `gettextize`, `autopoint`, `envsubst` in `/usr/bin`, keine `libgettextpo`/`libgettextlib`/`libgettextsrc` in `/usr/lib/x86_64-linux-gnu`, `dpkg-query` kennt weder `gettext`, `gettext-base` noch `libgettextpo0`; unter `/app/locale` liegt nur `de/LC_MESSAGES/django.mo`.
3. `pytest` in diesem Arbeitsverzeichnis ohne Vorschritt: 1093 bestanden, 0 fehlgeschlagen, 0 übersprungen (4 abgewählt = Worker). `pytest -m worker`: 4 bestanden.
4. `git status --porcelain --ignored -- backend/locale`: leer; keine `.mo` unter `backend/`.
5. Schritt „Translation catalogue up to date“: Exit 0, `git status` leer.
6. Deutsche Meldung: `{"detail":"Anmeldedaten fehlen."}`.
7. `ruff check`: „All checks passed!“; `ruff format --check`: Exit 0; `mypy`: „Success: no issues found in 132 source files“.
8. `makemigrations --check --dry-run`: „No changes detected“; Lizenzprüfung: Exit 0.
9. OpenAPI-Schema neu erzeugt: kein Unterschied (Schema und Client unverändert).
10. Bau `migrate api worker web-dev`, `pull e2e`, `npm ci`, Testkonto, `e2e`: 15 bestanden. Das Testkonto habe ich unter PowerShell angelegt (Werte aus `.env`, Kennwort nur als Variablenname `-e TWOX_ACCOUNT_PASSWORD`), nicht mit dem Bash-Schritt, weil `.env` nicht über Git Bash eingelesen werden sollte.
11. `down -v` mit beiden Profilen: Exit 0.
- `ci.yml` mit PyYAML geladen: gültig, neuer Schritt an der richtigen Stelle.

**Zweig und Arbeitsverzeichnis:** Zweig `worktree-agent-a46dcf69fe1eb72ea`, Arbeitsverzeichnis `.claude/worktrees/agent-a46dcf69fe1eb72ea`.

**Abweichungen**

- `backend/tests/config/test_settings.py` (nicht im Auftrag genannt) geändert: Der Test prüfte `settings.LOCALE_PATHS`, das in den Tests jetzt auf die übersetzten Kopien zeigt; er liest den Wert nun aus dem Settings-Modul selbst.
- `backend/twox/files/uploads.py` geändert (mehr als reines Markieren): Ohne die Änderung bliebe die 413-Antwort der ASGI-Hülle immer Englisch.
- `backend/twox/config/settings.py`: nur der Kommentar zu den Katalogen.
- Nicht übersetzt: Meldungen der Verwaltungsbefehle (`create_account`, `import_devices`, `check_*`; Django-Befehle laufen ohne Sprachwahl) und die Fehlertexte des Selbsttests (`database not reachable` u. ä.; technische Diagnose der Testseite). Hilfetexte und Beschreibungen im OpenAPI-Schema bleiben Englisch (Entwicklerdoku), daher keine Schemaänderung.

**Hinweise und offene Punkte**

- `makemessages` schreibt Zeilennummern in die Fundstellen (`#: twox/…py:NN`). Verschiebt eine Änderung Zeilen in einer Datei mit markierten Texten, schlägt der CI-Schritt fehl, bis `makemessages` neu läuft; parallele Backend-Zweige geraten in der `.po` leicht in Konflikt. Abhilfe wäre ein eigener `makemessages`-Befehl mit `--add-location=file` (Fundstelle nur mit Datei). Nicht umgesetzt, weil der Auftrag den Befehl wörtlich vorgibt – Entscheidung der Leitstelle bzw. von a7.
- `get_object_or_404` liefert über DRF „No Device matches the given query.“; dieser Text stammt von Django ohne Übersetzung und bleibt Englisch.
- Die Lizenzausnahme für gettext (E-46) steht noch nicht in der Abhängigkeitstabelle von `docs/DECISIONS.md`; das ändert nur die Leitstelle. Vorschlag: „GNU gettext 0.23.1 (Debian trixie, Paket gettext 0.23.1-2) | GPL (Programme), LGPL (libintl), Version der Lizenz nicht einzeln geprüft | makemessages, compilemessages, msgfmt in den Tests; nur Dev-Image und Bau-Stufe `locale-build`, nicht im Laufzeit-Image | 034 | E-46“.