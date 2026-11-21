# Auftrag 025 – API-Rechte: Standard nur mit Rolle, Prüfung aller Pfade

Meilenstein: M1 · Freigabestufe: C · Status: offen

## Ziel

Eine API-Ansicht, deren Rechteklasse vergessen wurde, ist nicht mehr für jeden Angemeldeten offen. Offen ist sie nur noch für Konten mit Rolle. Ein Test prüft alle Pfade unter `/api/v1/`, auch die der späteren Aufträge.

## Umfang

- `settings.py`: `DEFAULT_PERMISSION_CLASSES` = `twox.accounts.permissions.CanRead` (aus 021), nach Frage 1.
- `backend/tests/config/test_api.py`:
  - Die Tests zur bisherigen Standardklasse (`test_default_permission_is_is_authenticated`, `test_view_without_own_permission_serves_authenticated_user` u. a.) auf `CanRead` umstellen: anonym 403, angemeldet ohne Rolle 403, mit Rolle `read` 200.
  - Neuer Test, der alle Pfade unter `/api/v1/` aus dem URL-Verzeichnis aufzählt, nicht nur aus dem Schema.
  - Er ruft jeden Pfad mit jeder erlaubten Methode auf; Platzhalter werden mit einer beliebigen Kennung gefüllt.
  - Erwartet: anonym 403 und angemeldet ohne Rolle 403.
  - Ausnahmen stehen als feste Listen im Test:
    - `OPEN_PATHS` (anonym erlaubt): `/api/v1/health/`, bis Auftrag 027 auch `/api/v1/selftest/`.
    - `ROLELESS_PATHS` (angemeldet ohne Rolle erlaubt): `/api/v1/me/`.
  - Ein neuer Pfad, der ohne Eintrag in einer der Listen offen ist, lässt den Test scheitern.
- `backend/tests/config/test_settings.py`: Standard-Rechteklasse.

## Nicht-Ziele

- Neue Endpunkte. Rechte je Objekt oder Standort.
- Änderung am Selbsttest (Auftrag 027).

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/config/settings.py` (eine Zeile)
- `backend/tests/config/test_api.py`, `backend/tests/config/test_settings.py`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-025`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18025` setzen.
- Unter Git Bash vor Befehlen mit `/out/…` `MSYS_NO_PATHCONV=1` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Prüfungen und Typen:
   - `D run --rm backend-dev ruff check .` meldet `All checks passed!`.
   - `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0.
   - `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
3. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen. `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
4. Gegenprobe: Im Kurzbericht ist belegt, dass der Aufzähl-Test scheitert, wenn eine Test-Ansicht ohne eigene Rechteklasse unter `/api/v1/` hängt und die Standardklasse vorübergehend `IsAuthenticated` ist (Lauf vor der Änderung).
5. `D run --rm backend-dev python manage.py makemigrations --check --dry-run` meldet `No changes detected`.
6. `D run --rm -v \"$PWD/web/openapi:/out\" backend-dev python manage.py spectacular --file /out/schema.yml`, danach zeigt `git diff --exit-code -- web/openapi` keinen Unterschied.
7. Abräumen: `D --profile dev down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); 016 und 021 sind nach `main` zusammengeführt; Antwort von a7 auf Frage 1.

- Welle 3, parallel zu 023 und 024. Einziger Auftrag der Welle mit `settings.py` und `test_api.py`.
- **Keine neue Abhängigkeit.**
- Jeder spätere Auftrag mit neuem Endpunkt muss diesen Test grün halten. Eine neue Ausnahme braucht eine Begründung im Kurzbericht und ist Sache der Leitstelle.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

1. **Standardrecht der API**
   - (a) Jede Ansicht ohne eigene Rechteklasse verlangt eine Rolle (`CanRead`). Ausnahmen (`health`, `me`) stehen ausdrücklich im Test.
   - (b) Es bleibt bei „angemeldet“ (`IsAuthenticated`); jede Ansicht muss ihre Rolle selbst prüfen.
   - Empfehlung: (a). Ein vergessener Eintrag öffnet dann keinen Endpunkt für Konten ohne Rolle.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
