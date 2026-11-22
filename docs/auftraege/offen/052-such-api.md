# Auftrag 052 – Such-API

Meilenstein: M2 · Freigabestufe: C · Status: zur Prüfung

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
- Nachtrag Leitstelle (Prüfung 047): `backend/twox/search/interface.py`, `backend/twox/search/postgres.py`, `backend/tests/search/test_keyword_search.py`, `backend/tests/search/test_vector_search.py`, `backend/twox/answers/embeddings.py`, `backend/twox/config/settings.py` (nur die neue Zeitgrenze), `.env.example`, `backend/twox/search/evaluation.py`, `backend/tests/search/test_evaluation.py` – nur für die fünf Punkte unten

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

- **Nachtrag der Leitstelle (Prüfung 047):** (1) `HitLocation` hat keinen Dateinamen der Version. Ergänze `version_filename: str` (aus `files_documentversion.original_filename`) in der Schnittstelle und in `postgres.py`, mit Test; die API liefert ihn als `version.original_filename`. (2) Ausschlüsse mit `-Wort` wirken bisher nur auf den Stichwortzweig, nicht auf exakte Kennungstreffer (`192.168.0.5 -pump` findet auch Abschnitte mit „pump“). Ausschlüsse sollen für alle Treffer gelten; dafür den negierten Teil der Anfrage auch auf den exakten Zweig anwenden, Test „Kennung -Wort“. Dasselbe gilt für die Vektorliste aus 050: Abschnitte mit einem ausgeschlossenen Wort fallen auch dort heraus; Test „Frage -Wort“ mit Vektortreffer. (3) Die Antwort unterscheidet „KI nicht aktiviert“ (`TWOX_AI_ENABLED` aus, neutraler Zustand nach E-59) von „Sprachmodell nicht erreichbar“ (Rückfall wegen Ausfall), z. B. als dreiwertiges Feld `semantic` mit `used`/`disabled`/`unavailable`; dafür `SearchResult` in `interface.py` erweitern. (4) Eigene, kurze Zeitgrenze für Einbettungen von Suchanfragen (neue Einstellung `TWOX_SEARCH_EMBED_TIMEOUT_SECONDS`, Vorgabe 20, in `settings.py` und `.env.example`) und die Modellprüfung (`/api/tags`) je Prozess zwischenspeichern statt bei jeder Suche; die Cloud-Prüfung aus 044 bleibt. Hängt Ollama, wartet eine Suche sonst bis zu 2 × 120 s. (5) Einen Schalter in `SearchRequest` für „nur Stichwortsuche“ ergänzen und `override_settings(TWOX_AI_ENABLED=False)` in `backend/twox/search/evaluation.py` (056) dadurch ersetzen; `override_settings` ist nicht thread-sicher und gehört nicht in Produktcode.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

1. **Wie bleiben Suchtexte aus den Protokollen?** (uvicorn schreibt standardmäßig Pfad und Abfrageteil ins Zugriffsprotokoll; der `api`-Dienst startet ohne `--no-access-log`.)
   - (a) Suche per `POST` mit Text im Körper; die Suchseite hält den Text nicht in der Adresse (keine verlinkbaren Ergebnisse);
   - (b) `GET` mit `?q=`; ein Logfilter entfernt bei allen Pfaden den Abfrageteil aus dem Zugriffsprotokoll;
   - (c) Suchtexte stehen im Zugriffsprotokoll; als Grenze dokumentiert.
   Empfehlung: (b). Verlinkbare Suchergebnisse bleiben möglich, und auch andere Abfrageteile (Filter) landen nicht mehr im Protokoll.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

### Was wurde gebaut?

- **Endpunkt** `GET /api/v1/search/` (`backend/twox/search/api.py`, `urls.py`, eingebunden in `config/urls.py`), Rechte `CanRead`: anonym und ohne Rolle 403, `read`, `manage` und Superuser 200; andere Methoden 405. Parameter: `q` Pflicht, 1–500 Zeichen nach dem Kürzen; `device` und `plant` als IDs, je wiederholbar, höchstens 100 Werte; `limit` 1–50, Vorgabe 20. Ungültige Werte: 400 mit Fehler am Feld (DRF-Meldungen, deutsch übersetzt durch DRF).
- **Antwort:** `{"semantic": "used" | "disabled" | "unavailable", "hits": [...]}`, je Treffer `section_id`, `score`, `match_kinds` (`exact`/`keyword`/`semantic`), `snippet` (reiner Text), `highlights` als Liste von `{start, end}` (Positionen in Unicode-Codepoints des Ausschnitts), `page_start`, `page_end`, `heading_path`, `locations` mit `document {id, title}`, `version {id, number, original_filename, is_latest}`, `device {id, key, name}`, `plant {id, key, name}`. Die View ruft nur `get_search_backend()` auf, keine eigene SQL.
- **Logfilter** (`backend/twox/config/logging.py`, `DropQueryString`): schneidet in jedem Datensatz von `uvicorn.access` den Abfrageteil vom Pfad ab. `LOGGING` definiert dafür den Logger `uvicorn.access` mit uvicorns eigenem `AccessFormatter` (stdout) und dem Filter.
- **Nachtrag (1)** `HitLocation.version_filename` aus `files_documentversion.original_filename`; API liefert es als `version.original_filename`.
- **Nachtrag (2)** Ausschlüsse gelten für alle Treffer: Die negierten Teile werden aus dem von PostgreSQL erzeugten `tsquery`-Text gelesen (`negated_parts`, `!'wort'`, `!( 'a' <-> 'b' )`; doppelte Negation `--wort` schließt nichts aus) und als `NOT (…)` auf alle Kandidaten angewandt (exakt, Stichwort, Vektor); bei Phrasen mit der Nachprüfung je Konfiguration wie im Stichwortzweig. Die Vektorsuche lässt solche Abschnitte schon vor dem Nehmen der 50 nächsten weg, die Liste bleibt voll.
- **Nachtrag (3)** `SearchResult.semantic` vom Typ `SemanticState` (`used`, `disabled`, `unavailable`); `semantic_used` bleibt als Eigenschaft.
- **Nachtrag (4)** Neue Einstellung `TWOX_SEARCH_EMBED_TIMEOUT_SECONDS` (Vorgabe 20; `settings.py`, `.env.example`, `deploy/compose/compose.yaml`). `embeddings.get_query_embedder()` liefert je Prozess eine Instanz (neu bei geänderten Einstellungen); die Prüfung gegen `/api/tags` gilt 300 s (`QUERY_MODEL_CHECK_SECONDS`), eine gescheiterte Prüfung wird nicht gemerkt; die Namensprüfung auf Cloud-Modelle läuft vor jeder Anfrage. Die Einlese-Seite (`get_embedder`, 120 s) ist unverändert.
- **Nachtrag (5)** `SearchRequest.keyword_only`; `evaluation.py` nutzt `replace(request, keyword_only=True)` statt `override_settings`.

### Wie wurde getestet?

Neue Tests: `tests/search/test_api.py` (Rechte, Methoden, 15 ungültige Parameterfälle, Länge nach Kürzen, deutsche Feldmeldung, Antwortform mit Attrappe für alle drei Zustände, Ausschnitt mit Markup bleibt Text, IP-Suche mit Seite und Gerät, gleicher Inhalt an zwei Geräten = ein Treffer mit zwei Fundorten und eigenen Dateinamen, Filter Anlage, Grenze `limit`, `semantic` disabled/used/unavailable, Suchtext nicht im Log, Schema), `tests/config/test_logging.py` (Filter, andere Datensätze unverändert, Reihenfolge uvicorn-dann-Django-Konfiguration ergibt Zugriffsprotokoll ohne Abfrageteil). Erweitert: `test_keyword_search.py` (Dateiname, „Kennung -Wort“ für IP, `PLC-01`, `E1234`, Wortformen, Phrase, doppelte Negation, Parser, Zustände bei AI an/aus, `keyword_only`), `test_vector_search.py` („Frage -Wort“ mit Vektortreffer, volle Vektorliste trotz Ausschluss, Zustände, Zeitgrenze, Modellliste einmal für mehrere Suchen, erneut nach 300 s mit inzwischen Cloud-Modell, gescheiterte Prüfung nicht gemerkt, hängender Dienst: Rückfall nach 1 s), `test_evaluation.py` (Stichwortliste mit `keyword_only`, Schalter bleibt an), `test_settings.py` (neue Variable). Kein Test spricht ein echtes Ollama an.

| Kriterium | Ergebnis |
| --- | --- |
| 0 | erfüllt: Docker 29.9.3, Compose v5.7.0 |
| 1 | erfüllt: Build und `up -d --wait` Exit 0 |
| 2 | erfüllt: `tests/search tests/config` 669 bestanden (vor den Ergänzungen in `test_settings.py`; diese danach mit `test_logging.py` 170 bestanden); `pytest` 2262 bestanden, 0 fehlgeschlagen, 0 übersprungen (6 abgewählt, Marker `worker`); `pytest -m worker` 6 bestanden |
| 3 | erfüllt: `All checks passed!`, Format ohne Änderung, mypy `Success: no issues found in 191 source files` |
| 4 | erfüllt: `makemessages` ohne Unterschied (keine neuen eigenen Meldungen; Fehlermeldungen kommen übersetzt aus DRF), keine Migration, Lizenzprüfung bestanden, Schema neu erzeugt und eingecheckt (keine Warnungen) |
| 5 | erfüllt: lint, typecheck, test (571 bestanden), build, licenses Exit 0; `api:generate` erzeugt den eingecheckten Stand |
| 6 | erfüllt: Testkonto wie in `ci.yml`, Playwright 41 bestanden |
| 7 | erfüllt: zwei anonyme Aufrufe (403) und angemeldete Aufrufe (200) mit `?q=zzprobe…`: `D logs api` enthält `zzprobe` 0-mal, aber `"GET /api/v1/search/ HTTP/1.1" 403 Forbidden` bzw. `200 OK`; auch in den Protokollen aller Dienste 0 Treffer. Django-`LOGGING` erreicht `uvicorn.access` nach dem Start von uvicorn. |
| 8 | teilweise, siehe Abweichung 1: BetrSichV.pdf über die Datei-API hochgeladen, Einlesen startete selbst, `done` nach 295 s, 60 Seiten, 140 Abschnitte, alle eingebettet (Ollama am Host). Über HTTP durch uvicorn mit Sitzung von `e2e-manager`: `q=Prüfung` 200, 70 ms (erste Suche, mit Modellprüfung), `semantic: used`, erster Treffer S. 30–31, `keyword`+`semantic`, hervorgehoben „Prüfung“; `q=Wer darf Arbeitsmittel prüfen?` 54 ms, S. 12; `q=Explosionsgefährdung -Aufzug` 42 ms, S. 30–31 |
| 9 | erfüllt: beide `down -v` Exit 0 |

### Zweig und Arbeitsverzeichnis

Zweig `worktree-agent-abd2a4320ac3ec085`, Arbeitsverzeichnis `.claude/worktrees/agent-abd2a4320ac3ec085`. Commits: `c09aa07` (Such-Schnittstelle: Nachträge 1–5), `3974ed4` (API, Logfilter, Tests), `6d68964` (Schema und Client), dazu dieser Kurzbericht. Nicht gepusht, nichts zusammengeführt.

### Abweichungen

1. **Kriterium 8 nicht im Browser:** Ich habe kein Kennwort in eine Browseroberfläche eingegeben. Stattdessen wurde im `api`-Container eine Sitzung für `e2e-manager` serverseitig angelegt und `/api/v1/search/` über echtes HTTP durch uvicorn aufgerufen (Werte oben). Der Blick im Browser steht für a7 oder die Leitstelle aus.
2. **`plant.id` in der Antwort** zusätzlich zu `key` und `name`: Der Filter `plant` nimmt IDs (wie `SearchRequest.plant_ids` und `device`), daher braucht die Oberfläche die ID. Bei Bedarf leicht zu entfernen.
3. **`highlights` als Objekte `{start, end}`** statt Zahlenpaaren; besser typisiert im erzeugten Client. Positionen sind Unicode-Codepoints (Python), nicht UTF-16-Einheiten: 054 sollte mit `Array.from(snippet)` schneiden, sonst verrutschen Hervorhebungen nach Zeichen außerhalb der BMP.
4. **`semantic` dreiwertig statt bool** (Nachtrag 3). Für eine Anfrage ganz ohne Suchbares (nur Sonderzeichen) gilt bei KI an `used` (Modell nicht nötig), bei aus `disabled`. `keyword_only` meldet ebenfalls `disabled`; die API setzt es nie.
5. **Außerhalb der genannten Bereiche, notwendig:** `deploy/compose/compose.yaml` (eine Zeile, damit `TWOX_SEARCH_EMBED_TIMEOUT_SECONDS` den Container erreicht), `backend/tests/search/conftest.py` und `fake_embedder.py` (Attrappe auch für `get_query_embedder`, Zwischenspeicher je Test leeren), `backend/tests/config/test_settings.py` (Test der neuen Variable).
6. **`uvicorn --no-access-log`** würde das Zugriffsprotokoll nicht mehr abschalten, weil Django den Logger danach neu mit Handler konfiguriert (Kommentar in `settings.py`). Der Dienst nutzt den Schalter nicht; Abschalten ginge über `LOGGING`.
7. Die Suchanfrage wird samt `-Wort` eingebettet; das ausgeschlossene Wort beeinflusst den Anfragevektor leicht. Die Ausschlussregel selbst gilt trotzdem für alle Treffer.
8. README/ARCHITECTURE nicht ergänzt (gehört zu 059): neuer Endpunkt, neue Variable `TWOX_SEARCH_EMBED_TIMEOUT_SECONDS`, Logfilter.

### Fragen an a7

Keine blockierenden.
