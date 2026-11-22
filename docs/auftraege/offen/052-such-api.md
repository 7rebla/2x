# Auftrag 052 – Such-API

Meilenstein: M2 · Freigabestufe: C · Status: offen

## Ziel

Ein Endpunkt macht die Suche über die Such-Schnittstelle für die Oberfläche nutzbar. Jeder Treffer nennt Fundorte (Dokument, Version, Gerät, Anlage), Seite und einen Ausschnitt mit Hervorhebungen; die Antwort sagt, ob die Bedeutungssuche mitgelaufen ist. Wer `read` hat, darf suchen. Suchtexte landen in keinem Protokoll, auch nicht im Zugriffsprotokoll von uvicorn (Frage 1).

## Umfang

- `GET /api/v1/search/` mit `CanRead`.
- Parameter: `q` Pflicht, 1 bis 500 Zeichen nach dem Kürzen; `device` und `plant` (Kennungen, je mehrfach); `limit` Vorgabe 20, höchstens 50. Ungültige Werte: 400 mit Feldfehlern.
- Antwort: `semantic` (bool) und `hits`, je Treffer `section_id`, `score`, `match_kinds`, `snippet`, `highlights` (Paare aus Start und Ende), `page_start`, `page_end`, `heading_path` und `locations` (je `document` mit `id`, `title`; `version` mit `id`, `number`, `original_filename`, `is_latest`; `device` mit `id`, `key`, `name`; `plant` mit `key`, `name`). Keine ganzen Abschnitte, kein HTML.
- Ausschließlich über `get_search_backend()` (047, 050); keine eigene SQL-Abfrage in der View.
- **Protokolle nach Frage 1 (Empfehlung b):** in `LOGGING` (`backend/twox/config/settings.py`) ein Filter für den Logger `uvicorn.access`, der bei allen Pfaden den Abfrageteil (`?…`) entfernt; Filterklasse in `backend/twox/config/logging.py` mit Test. Der Suchtext steht weder im Server- noch im Änderungsprotokoll.
- Neue Dateien `backend/twox/search/api.py` und `backend/twox/search/urls.py`, eingebunden in `backend/twox/config/urls.py`; `backend/tests/config/expected_paths/search.py`.
- Schema und Client neu erzeugen und einchecken; Meldungen in `django.po` übersetzen.
- **Tests:** Rechte (anonym und ohne Rolle 403, `read` und `manage` 200); Prüfung der Parameter; Aufbau der Antwort mit Attrappe des Such-Backends und mit echter Datenbank; IP-Suche liefert Seite und Gerät; gleicher Inhalt bei zwei Geräten ergibt einen Treffer mit zwei Fundorten; `semantic: false` bei Ausfall des Modells; Grenze `limit`; Logfilter entfernt den Abfrageteil.

## Nicht-Ziele

- Keine Oberfläche (054).
- Kein Speichern von Suchanfragen.
- Keine Antworten mit Sprachmodell (M3), keine Seitenvorschau.

## Betroffene Bereiche (Ordner, Dateien)

- neu: `backend/twox/search/api.py`, `backend/twox/search/urls.py`, `backend/twox/config/logging.py`
- `backend/twox/config/urls.py`, `backend/twox/config/settings.py` (nur `LOGGING`)
- neu: `backend/tests/config/expected_paths/search.py`; `backend/tests/config/expected_paths/__init__.py`
- neu: `backend/tests/search/test_api.py`, `backend/tests/config/test_logging.py`
- `backend/locale/de/LC_MESSAGES/django.po`
- `web/openapi/schema.yml`, `web/src/api/generated/**`
- Nachtrag Leitstelle (Prüfung 047): `backend/twox/search/interface.py`, `backend/twox/search/postgres.py`, `backend/tests/search/test_keyword_search.py` – nur für die beiden Punkte unten

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-052`, `W` für `docker compose -p twox-052-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18052` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev web-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Tests:
   - `D run --rm backend-dev pytest tests/search tests/config -v` endet mit Exit-Code 0.
   - `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen.
   - `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
3. `D run --rm backend-dev ruff check .` meldet `All checks passed!`, `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0, `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
4. Weitere Prüfungen wie in `ci.yml`, jeweils ohne Unterschied zum eingecheckten Stand:
   - `D run --rm backend-dev python manage.py makemessages -l de --add-location=file`, danach `git diff --exit-code -I '^"POT-Creation-Date:' -- backend/locale`;
   - `D run --rm backend-dev python manage.py makemigrations --check --dry-run` endet mit Exit-Code 0;
   - `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0;
   - `D run --rm -v "$PWD/web/openapi:/out" backend-dev python manage.py spectacular --file /out/schema.yml` (unter Git Bash mit vorangestelltem `MSYS_NO_PATHCONV=1`), danach `git diff --exit-code -- web/openapi`.
5. Oberfläche wie im CI-Job `web`: `W --profile dev build web-dev` und `W run --rm web-dev npm ci`, danach `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build` und `npm run licenses`, je über `W run --rm web-dev …`, mit Exit-Code 0. `W run --rm web-dev npm run api:generate`, danach `git diff --exit-code -- web/openapi web/src/api` ohne Unterschied.
6. Browser-Test wie im CI-Job `e2e`: `D --profile e2e pull e2e`, `D --profile dev run --rm web-dev npm ci`; dann der Schritt „Create test account“ aus `ci.yml` wörtlich, nur mit `D` statt `docker compose` (Kennwort nur über den Variablennamen `TWOX_ACCOUNT_PASSWORD`); dann `D --profile e2e run --rm e2e`: alle Fälle bestanden, Exit-Code 0.
7. Zugriffsprotokoll: Nach einem Aufruf von `/api/v1/search/?q=zzprobe` (angemeldet oder anonym) enthält `D logs api` die Zeichenfolge `zzprobe` nicht, wohl aber den Pfad `/api/v1/search/`.
8. Lokal, mit eingelesener BetrSichV (wie 048, Kriterium 6): angemeldet über die Oberfläche liefert `/api/v1/search/?q=...` im Browser Treffer mit Seite; Beispiel und Antwortzeit im Kurzbericht.
9. Abräumen: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

- **Nachtrag der Leitstelle (E-59, KI optional):** Einbettungen, Vektorsuche und alles, was ein Modell braucht, sind eine aktivierbare Zusatzfunktion. Schalter `TWOX_AI_ENABLED` (Einstellung in `settings.py`, Standard `False`; `.env.example` mit Kommentar). Bei „aus“: kein Aufruf von Ollama, keine Einbettungs-Aufgaben, Einlesen endet nach den Abschnitten erfolgreich, die Suche arbeitet nur mit der Stichwortsuche, Selbsttest und Oberfläche zeigen „KI nicht aktiviert“ als neutralen Zustand (kein Fehler, kein Warnsymbol). Jede KI-abhängige Stelle braucht einen Test für beide Zustände; die CI läuft mit „aus“ und mit „an“ plus Attrappe.

Voraussetzung: 050 und 051 sind nach `main` zusammengeführt (051 wegen `urls.py`, Schema, Client, `django.po`, `expected_paths/__init__.py`). Frage 1 ist entschieden.

- Welle 7, parallel zu 053 (053 ändert weder Backend noch Client).
- **Keine neue Abhängigkeit.**
- Rechte wie bisher (E-40): `read` darf suchen; keine Rechte je Gerät in M2 (Hinweis in 047).
- Der Ausschnitt ist reiner Text; die Oberfläche setzt die Hervorhebung selbst (XSS).
- Dass Django-`LOGGING` den Logger `uvicorn.access` nach dem Start von uvicorn noch erreicht, ist ungeprüft; Kriterium 7 belegt es. Klappt es nicht, anhalten und den Befund in den Auftrag schreiben (Ausweichweg wäre `--no-access-log` oder `--log-config` im `backend/Dockerfile`, das ist eine neue Frage).
- Konflikte in `web/src/api/generated` und `schema.yml` durch Neuerzeugen lösen.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

- **Nachtrag der Leitstelle (Prüfung 047):** (1) `HitLocation` hat keinen Dateinamen der Version. Ergänze `version_filename: str` (aus `files_documentversion.original_filename`) in der Schnittstelle und in `postgres.py`, mit Test; die API liefert ihn als `version.original_filename`. (2) Ausschlüsse mit `-Wort` wirken bisher nur auf den Stichwortzweig, nicht auf exakte Kennungstreffer (`192.168.0.5 -pump` findet auch Abschnitte mit „pump“). Ausschlüsse sollen für alle Treffer gelten; dafür den negierten Teil der Anfrage auch auf den exakten Zweig anwenden, Test „Kennung -Wort“.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

1. **Wie bleiben Suchtexte aus den Protokollen?** (uvicorn schreibt standardmäßig Pfad und Abfrageteil ins Zugriffsprotokoll; der `api`-Dienst startet ohne `--no-access-log`.)
   - (a) Suche per `POST` mit Text im Körper; die Suchseite hält den Text nicht in der Adresse (keine verlinkbaren Ergebnisse);
   - (b) `GET` mit `?q=`; ein Logfilter entfernt bei allen Pfaden den Abfrageteil aus dem Zugriffsprotokoll;
   - (c) Suchtexte stehen im Zugriffsprotokoll; als Grenze dokumentiert.
   Empfehlung: (b). Verlinkbare Suchergebnisse bleiben möglich, und auch andere Abfrageteile (Filter) landen nicht mehr im Protokoll.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
