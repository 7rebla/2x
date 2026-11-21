# Auftrag 025 – API-Rechte: Standard nur mit Rolle, Prüfung aller Pfade

Meilenstein: M1 · Freigabestufe: C · Status: zur Prüfung

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

**Was wurde gebaut?**

- `settings.py`: `DEFAULT_PERMISSION_CLASSES = ["twox.accounts.permissions.CanRead"]`, Kommentar angepasst (verweist auf die Ausnahmelisten im Test).
- `tests/config/test_api.py`:
  - Prüfung aller Pfade: `api_endpoints()` läuft rekursiv durch das URL-Verzeichnis (`get_resolver()`, nicht das Schema) und sammelt jeden Pfad unter `/api/v1/`. Platzhalter werden gefüllt – bei `path()` über die Regex des Konverters, bei `re_path()` über die benannten Gruppen (Werte `1`, eine UUID, `x`; für `format` `json` bzw. `.json`, damit DRF nicht vor der Rechteprüfung 404 antwortet). Jeder gefüllte Pfad muss mit `resolve()` wieder auf dieselbe Ansicht führen, sonst scheitert der Test mit „extend fill_pattern“.
  - `paths_open_to()` ruft jeden Pfad mit jeder Methode der Ansicht auf (Methoden der Klasse bzw. `actions` eines ViewSets, dazu HEAD bei GET und OPTIONS) und listet jede Antwort ungleich 403. Eine Ansicht unter `/api/v1/`, die keine DRF-Ansicht ist, wird ebenfalls gemeldet (dort laufen keine DRF-Rechte).
  - `OPEN_PATHS = {/api/v1/health/, /api/v1/selftest/}`, `ROLELESS_PATHS = {/api/v1/me/}` mit Begründung im Kommentar. Ein Test prüft, dass jeder Eintrag einen existierenden Pfad nennt und die Listen sich nicht überschneiden; ein weiterer, dass jeder Schema-Pfad ohne Platzhalter auch gefunden wird.
  - Selbstprüfung der Prüfung: Die Test-URLs des Moduls enthalten zusätzlich `LeakyView` (`IsAuthenticated`, einmal als `path` mit `<int:pk>`, einmal als `re_path` mit Format-Endung) und eine reine Django-Ansicht. Zwei Tests erwarten genau diese Meldungen (ohne Rolle bzw. anonym); `ProbeView` ohne eigene Rechteklasse darf darin nicht vorkommen.
  - Bisherige Tests umgestellt: anonym 403, angemeldet ohne Rolle 403, mit `read`, `manage` und Superuser 200 (über Sitzung und über `APIRequestFactory`); die CSRF-Tests melden einen Benutzer mit Rolle `read` an. `test_default_permission_is_is_authenticated` entfällt, die Prüfung der Einstellung steht jetzt in `test_settings.py`.
- `tests/config/test_settings.py`: `test_default_permission_class_is_can_read` (Einstellung und `api_settings` ergeben `[CanRead]`).
- `twox/accounts/permissions.py`: `APIView` nur noch unter `TYPE_CHECKING` importiert (siehe Abweichungen).

**Wie wurde getestet?** `docker compose -p twox-025`, `.env` aus `.env.example` mit `TWOX_API_PORT=18025`, Docker Engine 29.9.3, Compose v5.7.0. Die Ergebnisse unten stammen aus dem Lauf nach dem Zusammenführen von `main` (Stand mit 023 und 024; 020 lag noch nicht auf `main`).

| AK | Ergebnis |
| --- | --- |
| 0 | erfüllt: `docker version` und `docker compose version` Exit 0 |
| 1 | erfüllt: Bau Exit 0, `up -d --wait` Exit 0 (db, valkey, api, worker healthy) |
| 2 | erfüllt: `All checks passed!`, `ruff format --check` Exit 0 (93 Dateien), `Success: no issues found in 93 source files` |
| 3 | erfüllt: `432 passed, 4 deselected`, 0 fehlgeschlagen, 0 übersprungen; `pytest -m worker`: `4 passed` |
| 4 | erfüllt, siehe Gegenprobe unten |
| 5 | erfüllt: `No changes detected` |
| 6 | erfüllt: `spectacular` ohne Ausgabe, `git diff --exit-code -- web/openapi` ohne Unterschied, keine neuen Dateien |
| 7 | erfüllt: `D --profile dev --profile e2e down -v` Exit 0 |

Zusätzlich wie in der CI: Lizenzprüfung Python `License check passed.`; e2e (`--profile e2e run --rm e2e`) `5 passed`. Schema und API-Client sind unverändert, der web-Job war daher nicht nötig.

**Gegenprobe (AK 4):** Erst die Tests geschrieben, `settings.py` noch mit `IsAuthenticated`, dann `pytest tests/config/test_api.py`: `3 failed, 18 passed`. Gescheitert sind `test_path_check_reports_views_open_without_role` (die Prüfung meldet zusätzlich `GET /api/v1/probe/: 200` und drei weitere Methoden der Test-Ansicht ohne eigene Rechteklasse – „Left contains 4 more items“), `test_view_without_own_permission_refuses_signed_in_user_without_role` und `test_view_without_own_permission_needs_a_role[no_role-403]` (jeweils 200 statt 403). Nach der Umstellung auf `CanRead` sind alle grün. Die Gegenprobe ist damit dauerhaft im Test: Wer die Standardklasse zurücksetzt, lässt ihn scheitern.

**Zweig und Arbeitsverzeichnis:** Zweig `worktree-agent-aa794516d72b8cbe2`, Arbeitsverzeichnis `.claude/worktrees/agent-aa794516d72b8cbe2`.

**Abweichungen und Hinweise**

1. `backend/twox/accounts/permissions.py` (nicht im Auftrag genannt) geändert: Mit `CanRead` als Standard entsteht sonst ein Kreisimport – `rest_framework.views` liest beim Import die Standardklasse, und `permissions.py` importierte `rest_framework.views`. Jetzt nur noch für die Typangaben unter `TYPE_CHECKING` (Python 3.14 wertet Annotationen verzögert aus). Ohne die Änderung startet weder Django noch pytest.
2. `settings.py`: neben der einen Zeile ist der Kommentar darüber angepasst (zwei Zeilen).
3. Die Prüfung meldet auch Nicht-DRF-Ansichten unter `/api/v1/`. Das geht über den Wortlaut hinaus, folgt aber dem Ziel: Dort greift keine DRF-Rechteklasse.
4. Hinweis für spätere Aufträge: Ein Platzhalter, für den keiner der Werte passt, oder ein Muster, das sich nicht füllen lässt, lässt den Test mit klarer Meldung scheitern; dann `PLACEHOLDER_VALUES` bzw. `fill_pattern` erweitern. Die allauth-Pfade unter `/_allauth/` liegen nicht unter `/api/v1/` und werden nicht geprüft.
5. Auftrag 020 lag bis zum Abschluss nicht auf `main`; `main` (mit 023 und 024) ist eingeführt. Nach dem Zusammenführen von 020 sollte die Leitstelle `pytest tests/config/test_api.py` noch einmal laufen lassen.

Keine neue Abhängigkeit. `docs/DECISIONS.md` und `docs/STATUS.md` nicht geändert. Kein Push.
