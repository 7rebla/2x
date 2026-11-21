# Auftrag 034 – Backend-Übersetzung Deutsch: gettext-Kataloge, Bau und Prüfung

Meilenstein: M1 · Freigabestufe: C · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
