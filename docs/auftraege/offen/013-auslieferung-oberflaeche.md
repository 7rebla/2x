# Auftrag 013 – Auslieferung der Oberfläche durch Django

Meilenstein: M0 · Freigabestufe: C · Status: zur Prüfung

## Ziel

Die Oberfläche wird fertig gebaut von Django ausgeliefert; im Betrieb läuft kein Node-Server (Abschnitt 5.2). Unter `/` des Dienstes `api` erscheint die Oberfläche aus `web/`.

## Umfang

- Mehrstufiger Image-Bau: Eine Node-Stufe baut die Oberfläche (`npm ci`, `npm run build`); das Ergebnis wird in die Stufe `runtime` des Backend-Images kopiert. Im fertigen Image ist kein Node enthalten.
- Django liefert unter `/` die `index.html` der Oberfläche und unter `/static/` die gebauten Dateien aus – nach a7s Antwort auf Frage 1.
- Statische Dateien werden beim Bau des Images eingesammelt (`collectstatic`), nicht beim Start.
- `deploy/compose/compose.yaml`: Bau-Kontext und Stufen so anpassen, dass `api` und `worker` das Image mit der Oberfläche nutzen. Dienstnamen und Aufrufe bleiben unverändert.
- `.dockerignore` im Wurzelverzeichnis als **Positivliste**: alles ausschließen, nur `backend/` und `web/` zulassen, darin wiederum `node_modules`, `dist`, Zwischenspeicher und `.env` ausschließen. So gelangen weder `.git`, `.claude/` (Arbeitsverzeichnisse anderer Aufträge), `testfactory/`, `testdata/` noch `docs/` in den Bau-Kontext.
- Tests unter `backend/tests/config/`:
  - `/` liefert HTML mit dem Wurzelelement der Oberfläche (im Test aus einem vorbereiteten Verzeichnis, nicht aus dem echten Build).
  - `/api/...` wird nicht von der Auslieferung der Oberfläche abgefangen.
  - Ein unbekannter Pfad unter `/static/` liefert 404.

## Nicht-Ziele

- Playwright-Test (Auftrag 014), Doku (Auftrag 015).
- Ein zusätzlicher Reverse-Proxy-Container, TLS, Sicherheits-Header – später.
- Entwicklungs-Server von Vite mit Weiterleitung an die API.
- Der Antwort-Stream (M3).
- Änderungen unter `web/` und an `.github/workflows/`.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/Dockerfile` (oder Verlagerung des Dockerfiles, wenn der Bau-Kontext es verlangt – dann im Kurzbericht begründen), `backend/.dockerignore` (entfällt, falls der Kontext wechselt)
- `.dockerignore` im Wurzelverzeichnis (neu)
- `backend/pyproject.toml`, `backend/uv.lock` (falls Frage 1 mit WhiteNoise entschieden)
- `backend/twox/config/settings.py`, `backend/twox/config/urls.py`, Ansicht für die Startseite in `backend/twox/config/`
- `backend/tests/config/` (neue Testdateien)
- `backend/scripts/` (nur die Regeldatei der Lizenzprüfung, falls nötig)
- `deploy/compose/compose.yaml`

## Akzeptanzkriterien (prüfbar)

Alle Befehle im Wurzelverzeichnis. `D` steht für `docker compose -p twox-013`. Vorher `.env.example` nach `.env` kopieren (falls nicht vorhanden) und darin `TWOX_API_PORT=18013` setzen. `HOLE <Pfad>` steht für `D exec api python -c "import urllib.request as u,sys; r=u.urlopen('http://localhost:8000'+sys.argv[1]); print(r.status, r.headers.get('Content-Type')); print(r.read(300).decode(errors='replace'))" <Pfad>`.

0. Vorab: `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren oder ausführen; Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. `D --profile dev build` endet mit Exit-Code 0.
2. `D up -d --wait db valkey worker api` endet mit Exit-Code 0; alle vier Dienste sind `healthy`. (Docling ist hier bewusst nicht dabei; den Start aller Container prüft Auftrag 009 und die Abnahme.)
3. `HOLE /` zeigt Status 200, `text/html` und das Wurzelelement der Oberfläche (`<div id="root">`).
4. Die in der ausgelieferten `index.html` genannten Skript- und Stil-Dateien unter `/static/` liefern mit `HOLE` Status 200 und den passenden Inhaltstyp (JavaScript bzw. CSS).
5. `HOLE /api/v1/selftest/` liefert weiterhin JSON mit `database.ok: true` und `worker.ok: true`; `HOLE /api/v1/health/` liefert `{"status":"ok"}`.
6. `D exec api sh -c 'command -v node || echo no-node'` gibt `no-node` aus.
7. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen; `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0; `ruff check .` meldet `All checks passed!`; `mypy .` meldet `Success: no issues found`. Der Dienst `backend-dev` funktioniert weiter ohne gebaute Oberfläche.
8. Die Befehle aus `.github/workflows/ci.yml` (Jobs `backend` und `web`) laufen lokal unverändert mit Exit-Code 0 durch – der Workflow selbst wird nicht geändert. Liste mit Ergebnis im Kurzbericht.
9. Lizenzprüfung: `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0.
10. Bau-Kontext: Die Ausgabe von `D build api` nennt die übertragene Kontextgröße; sie liegt im Bereich von `backend/` und `web/` ohne `node_modules` (Wert in den Kurzbericht). Eine Probedatei unter `.claude/` ändert den Build-Cache nicht (zweiter Build läuft vollständig aus dem Cache).
11. `D down` (ohne `-v`) und erneutes `D up -d --wait db valkey worker api`: `HOLE /` zeigt dieselbe Seite.
12. Abräumen: `D down -v` endet mit Exit-Code 0.
13. Sichtprüfung durch die Leitstelle nach dem Zusammenführen von 012 und 013: `http://localhost:8000/` zeigt im Browser die Testseite mit der Versionsnummer der Datenbank und `pong`. (Automatisiert wird das in Auftrag 014.)

## Vorgaben und Hinweise

**Nachtrag der Leitstelle (21.11.2026, aus der Prüfung von Auftrag 002):** Der Dienst `web-dev` liegt im Profil `dev`. Deshalb gilt abweichend vom Wortlaut dieses Auftrags: Bauen mit `build web-dev` oder `--profile dev build`; Abräumen mit `--profile dev down -v` (bei Playwright zusätzlich `--profile e2e`); den Dienst immer über `run --rm web-dev` ansprechen – ein bloßes `build`, `up` oder `down -v` ohne Profil tut nichts und meldet trotzdem Erfolg. `git check-ignore -q` nimmt nur einen Pfad je Aufruf. Zugelassene Lizenzen bei reinen Entwicklungs- und Build-Paketen zusätzlich: BlueOak-1.0.0, CC-BY-3.0, CC-BY-4.0, CC0-1.0 (E-25).

- **Voraussetzung:** Die Aufträge 002, 009 und 010 sind zusammengeführt (und damit 001, 005, 006, 008). Auftrag 011 liegt ebenfalls auf `main` (für Kriterium 8).
- **Abhängigkeiten.** Mit der Freigabe der Auftragsliste genehmigt a7 – wenn er Frage 1 mit (a) beantwortet – das Paket WhiteNoise. Jede weitere direkte Abhängigkeit ist nicht genehmigt. Ergibt die Lizenzprüfung (Kriterium 9) eine nicht gedeckte Lizenz: nicht einbauen, Frage in den Auftrag, Status „wartet auf a7“.
- **Stand der Recherche vom 21.11.2026 (belegt):** WhiteNoise 6.12.0, MIT; der Classifier nennt Django nur bis 6.0. Ob es unter Django 6.1 fehlerfrei läuft, ist ungeprüft – die Kriterien 3 und 4 sind der Nachweis. Klappt es nicht: nicht ausweichen, sondern Frage in den Auftrag.
- Vite baut mit `base: "/static/"` (Auftrag 002). Die Pfade in der `index.html` müssen zu Djangos `STATIC_URL` passen.
- Der Bau-Kontext braucht `backend/` und `web/`. Auftrag 012 läuft gleichzeitig und ändert nur Inhalte unter `web/`; ausgeliefert wird, was dort zum Zeitpunkt des Baus liegt (Platzhalter oder Testseite).
- Hinweis für später (ungeprüft): Beim Antwort-Stream darf keine Zwischenschicht puffern oder komprimieren. Hier keine Komprimierung einschalten, die später Streams betrifft.
- Der Image-Bau darf keine Geheimnisse brauchen; `collectstatic` muss ohne Datenbank und ohne echte `TWOX_SECRET_KEY` laufen.
- Parallele Arbeitsverzeichnisse: immer mit `-p twox-013` und Port 18013 arbeiten.
- Sprache: Code Englisch; jede Funktion hat Typangaben.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Im Kurzbericht Name, Version, Lizenz und Quelle nennen.
- Kein Push. Die Leitstelle committet nach `main` und pusht auf a7s Freigabe.
- Die Frage unten beantwortet a7 mit der Freigabe der Liste. Fehlt die Antwort: nicht raten, Status „wartet auf a7“.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

1. **Womit liefert Django die gebauten Dateien aus?** Die Unterlage sagt „fertig gebaut von Django ausgeliefert“, nennt aber kein Mittel. Djangos eigene Auslieferung statischer Dateien ist nur für die Entwicklung gedacht.
   - (a) WhiteNoise 6.12.0 (MIT): eine zusätzliche Python-Bibliothek, kein weiterer Container.
   - (b) Ein Reverse-Proxy als weiterer Container (zum Beispiel nginx oder Caddy): ein Baustein mehr als in Abschnitt 5.2 vorgesehen.
   - Empfehlung: (a). Es entspricht der Unterlage am genauesten und hält die Zahl der Bausteine klein. Ein Proxy kann im Skalierungspfad später davor.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle prüfbaren Kriterien sind erfüllt; die Läufe fanden am 21.11.2026 im Container statt. Kriterium 8 ist nur sinngemäß prüfbar, weil `.github/workflows/ci.yml` auf `main` noch fehlt (siehe Abweichungen). Keine offene Frage an a7.

### Was wurde gebaut?

- `backend/Dockerfile` (bleibt an seinem Ort, Bau-Kontext jetzt das Wurzelverzeichnis):
  - neue Stufe `web-build` (`node:24-slim`): `npm ci`, `npm run build`, danach `THIRD-PARTY-NOTICES.txt` neben dem Build (siehe Lizenzhinweise);
  - neue Stufe `static`: `collectstatic` beim Bau, mit Wegwerfwerten für `TWOX_SECRET_KEY` und `TWOX_DB_PASSWORD` nur in diesem `RUN` (nicht im Image), ohne Datenbank;
  - `runtime` kopiert nur `/app/staticfiles` dazu. Dateien gehören root und sind für `twox` (UID 10001) nur lesbar. Kein Node im Image.
  - `dev` baut die Oberfläche nicht (BuildKit baut nur die nötigen Stufen).
- `.dockerignore` im Wurzelverzeichnis als Positivliste (`*`, dann `!backend/`, `!web/`); darin ausgeschlossen: `.env*`, Python-Zwischenspeicher, `backend/.venv`, `backend/staticfiles`, `web/node_modules`, `web/dist`, Playwright-Ausgaben, die Dockerfiles. `backend/.dockerignore` entfällt.
- `deploy/compose/compose.yaml`: `migrate`, `api`, `worker` und `backend-dev` bauen mit `context: ../..` und `dockerfile: backend/Dockerfile`. Dienstnamen, Ziele und Aufrufe unverändert.
- `backend/pyproject.toml`, `backend/uv.lock`: WhiteNoise (im Container mit `uv lock` erzeugt; nur `whitenoise` kam dazu). Außerdem ein `filterwarnings`-Eintrag für die Warnung „No directory at …staticfiles“, die WhiteNoise in `backend-dev` (ohne gebaute Oberfläche) je Test-Client ausgibt.
- `backend/twox/config/settings.py`: `django.contrib.staticfiles`, `whitenoise.middleware.WhiteNoiseMiddleware` direkt nach `SecurityMiddleware`, `STATIC_URL = "/static/"` (passt zu Vites `base`), `STATIC_ROOT = BASE_DIR / "staticfiles"`, `WEB_DIST_DIR` aus `TWOX_WEB_DIST_DIR` (Vorgabe `../web/dist`), `STATICFILES_DIRS` nur wenn der Ordner existiert, `STATICFILES_FINDERS` nur `FileSystemFinder` (sonst würden die Dateien der abgeschalteten DRF-Oberfläche mit ausgeliefert: 31 statt 4 Dateien), einfache `StaticFilesStorage` ohne Komprimierung, `WHITENOISE_USE_FINDERS = False`, `WHITENOISE_AUTOREFRESH = False`, `WHITENOISE_IMMUTABLE_FILE_TEST` für `/static/assets/` (Vite-Namen mit Prüfsumme).
- `backend/twox/config/webui.py` (neu): `web_index` liefert `STATIC_ROOT/index.html` mit `text/html; charset=utf-8` und `Cache-Control: no-cache`, nur GET/HEAD. Ohne Build: 404 mit kurzem Text. `urls.py`: genau `""`, kein Auffangmuster.
- Tests: `backend/tests/config/test_webui.py` (neu, 17 Fälle aus vorbereiteten Ordnern): `/` mit `<div id="root">`, HEAD/POST, JS und CSS unter `/static/` mit Inhaltstyp und `immutable`, vier unbekannte `/static/`-Pfade → 404, `/api/v1/health/` unberührt, `/api/`, `/api/v1/`, `/api/v1/unknown/`, `/unknown/` → 404 ohne Oberfläche, `/` ohne Build → 404, API ohne Build, `collectstatic` ohne Datenbank sammelt genau die drei Build-Dateien, fehlender Build ergibt keine `STATICFILES_DIRS`. `test_settings.py`: `run_python` nimmt optional Argumente.

**Lizenzhinweise (Ansatz).** Ohne neues Werkzeug: Die Stufe `web-build` schreibt `dist/THIRD-PARTY-NOTICES.txt`, ausgeliefert unter `/static/THIRD-PARTY-NOTICES.txt`. Sie enthält je Paket Name, Version, Lizenz, Homepage, Zweck und die **unveränderte** Lizenzdatei aus `node_modules`: react 19.3.1, react-dom 19.3.1, scheduler 0.28.0, @hey-api/openapi-ts 0.99.0 (Vorlage des erzeugten Clients), dazu vite 8.3.8 (der Modul-Preload-Helfer steht nachweislich im Bündel) und tailwindcss 4.3.5 (Basisstile im CSS; der Kopfkommentar `/*! tailwindcss v4.3.5 | MIT License */` bleibt ohnehin stehen). Alle MIT. Schutz gegen Vergessen: Der Bau bricht ab, wenn `npm ls --omit=dev` etwas anderes als `react react-dom scheduler` meldet. Begründung: Die Lizenzdateien kommen aus genau den installierten Versionen, und es braucht keine neue Abhängigkeit. Nachteil: Vites `LICENSE.md` enthält auch die Lizenzen der in Vite selbst gebündelten Werkzeuge, deshalb ist die Datei 105 KB groß (zu viel, aber nicht falsch). Kürzen hieße, eine Lizenzdatei zu verändern; habe ich gelassen.

**Neue Abhängigkeit:** whitenoise 6.12.0, MIT (pip-licenses im Container: `MIT`), Quelle https://pypi.org/project/whitenoise/ und https://github.com/evansd/whitenoise. Läuft mit Django 6.1.3 fehlerfrei (Kriterien 3, 4 und die Tests). Keine weitere Abhängigkeit, auch keine mitgezogene.

### Wie wurde getestet?

`D` = `docker compose -p twox-013` im Wurzelverzeichnis, `.env` aus `.env.example` mit `TWOX_API_PORT=18013`, Docker Engine 29.9.3, Compose v5.7.0. Läufe auf dem committeten Stand.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `29.9.3`, `Docker Compose version v5.7.0`, beide Exit 0 |
| 1 | erfüllt | `D --profile dev build`: `Image twox-013-migrate Built`, `-worker`, `-api`, `-backend-dev Built`, Exit 0; im Protokoll `4 static files copied to '/app/staticfiles'` |
| 2 | erfüllt | Exit 0; `db`, `valkey`, `api`, `worker` jeweils `Healthy`, `migrate Exited` |
| 3 | erfüllt, mit Hinweis | `200 text/html; charset=utf-8`, Kopf der `index.html` mit `<script … src="/static/assets/index-CkvqiOjm.js">`. `<div id="root"></div>` steht nach Byte 300 und fehlt deshalb in der wörtlichen `HOLE`-Ausgabe; mit vollständigem Lesen im selben Container belegt (`'<div id="root"></div>'`), `Cache-Control: no-cache` |
| 4 | erfüllt | `/static/assets/index-CkvqiOjm.js`: `200 text/javascript; charset="utf-8"`; `/static/assets/index-BFyZW2wT.css`: `200 text/css; charset="utf-8"`; JS mit `max-age=315360000, public, immutable` |
| 5 | erfüllt | `{"database":{"ok":true,"server_version":"18.7 (Debian 18.7-1.pgdg12+2)","error":""},"worker":{"ok":true,"result":"pong","duration_ms":404,"error":""}}`; health: `{"status":"ok"}` |
| 6 | erfüllt | `no-node`; `id` im Dienst `api`: `uid=10001(twox)` |
| 7 | erfüllt | `110 passed, 4 deselected`, Exit 0, nichts übersprungen, keine Warnungen; `-m worker`: `4 passed, 110 deselected`, Exit 0; `All checks passed!`; `52 files already formatted`; `Success: no issues found in 52 source files`; `makemigrations --check`: `No changes detected`. `backend-dev` ohne gebaute Oberfläche |
| 8 | sinngemäß erfüllt | `ci.yml` fehlt auf `main`. Stattdessen die Befehle der Aufträge 001, 002, 005, 006, 008: backend wie Nr. 7 und 9; web (`-f deploy/compose/compose.web.yaml`, `run --rm web-dev`): `npm ci` „added 414 packages“, `lint=0`, `typecheck=0`, `test=0` („Tests 10 passed (10)“), `build=0`, `licenses=0` („391 packages … License check passed.“) |
| 9 | erfüllt | 53 Pakete, `whitenoise 6.12.0 MIT`, `License check passed.`, Exit 0. Regeldatei unverändert |
| 10 | erfüllt | Erster Bau von `api`: `transferring context: 469.10kB`. Gesamter Kontext (Wegwerf-Bau mit `COPY . /ctx`): 93 Dateien, 840 KB belegt, nur `backend` und `web`, darin weder `node_modules` noch `dist` noch `.env`. Probedatei `.claude/probe-013.txt` angelegt, `D build api`: Exit 0, alle 20 Schritte `CACHED`, kein Schritt neu ausgeführt; Probedatei wieder entfernt. Ebenso ganz aus dem Cache trotz vorhandenem `web/dist` auf dem Host |
| 11 | erfüllt | `D down` Exit 0, `D up -d --wait db valkey worker api` Exit 0; `/` liefert `200 text/html` mit denselben Dateinamen (`index-CkvqiOjm.js`, `index-BFyZW2wT.css`) und `<div id="root"></div>` |
| 12 | erfüllt | `D down -v` Exit 0 (Volumes und beide Netze entfernt); `D --profile dev down -v` Exit 0 („No resource found“); dazu `-f deploy/compose/compose.web.yaml --profile dev down -v` Exit 0 (Volume `web_node_modules`). Keine Container und Volumes von `twox-013` mehr. Projekt `2x` lief durchgehend weiter |
| 13 | vorab gesehen | siehe „So sieht die Seite aus“; die Sichtprüfung der Leitstelle nach dem Zusammenführen steht aus |

**So sieht die Seite aus** (Browser-Werkzeug der Sitzung, `http://127.0.0.1:18013/`): Titel „2x“, Überschrift „2x“, Abschnitt „Self-test“ mit Schaltfläche „Check again“ und dem Satz „Checks the database and the background worker through the API.“ Zwei grün hinterlegte Karten: „Database – OK – Server version: 18.7 (Debian 18.7-1.pgdg12+2)“ und „Worker – OK – Result: pong – Duration: 18 ms“. Tailwind-Stile greifen. Netzwerk: nur `GET /` 200, die zwei Dateien unter `/static/assets/` 200 und `GET /api/v1/selftest/` 200, alles gleicher Ursprung. Keine Konsolenmeldungen.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a1e68e69098d33433`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a1e68e69098d33433` (relativ zum Projektordner)

### Abweichungen und Hinweise

- **Kriterium 8:** `.github/workflows/ci.yml` gibt es auf `main` nicht (Auftrag 011 ist offen). Gelaufen sind die gleichen Befehle aus den Vorgängeraufträgen. Ob die CI aus 011 den Bau-Kontext oder `backend/.dockerignore` voraussetzt, ist ungeprüft. Beim Zusammenführen von 011 beachten: Der Kontext ist jetzt das Wurzelverzeichnis, `backend/.dockerignore` gibt es nicht mehr.
- **Kriterium 3:** `HOLE` liest nur 300 Byte, das Wurzelelement steht dahinter (siehe Tabelle).
- **Inhaltstyp der Dateien:** WhiteNoise schreibt `charset="utf-8"` in Anführungszeichen; das ist gültig, die Tests prüfen es so.
- **Nur der Build wird gesammelt** (`STATICFILES_FINDERS`). Mit dem Admin in M1 muss `AppDirectoriesFinder` dazu, sonst fehlen dessen Dateien.
- **Unbekannte Pfade** liefern mit `TWOX_DEBUG=true` Djangos HTML-Fehlerseite (Status 404), ohne Debug die knappe Standardseite.
- **WhiteNoise setzt `Access-Control-Allow-Origin: *`** auf statische Dateien (Vorgabe). Für öffentliche Build-Dateien unbedenklich; Sicherheits-Header sind laut Auftrag später dran.
- **Keine Komprimierung:** weder vorkomprimierte Dateien noch eine Komprimierungs-Middleware.
- **Commit-Zuschnitt:** Das Löschen von `backend/.dockerignore` ist versehentlich im Commit „Add WhiteNoise 6.12.0 …“ gelandet statt im Bau-Commit.
- **Image `node:24-slim`** nur per Tag festgelegt, wie in Auftrag 002.
- Lokal liegen noch die Images `twox-013-api`, `-worker`, `-migrate`, `-backend-dev`, `-web-dev`. Die lokale `.env` (ignoriert) hat `TWOX_API_PORT=18013`.
- `docs/DECISIONS.md` und `docs/STATUS.md` sind nicht angefasst. Fürs Entscheidungsprotokoll: whitenoise 6.12.0 (MIT) und die Lizenzhinweise im Image.
