# Auftrag 015 – ARCHITECTURE.md und README

Meilenstein: M0 · Freigabestufe: B · Status: erledigt

## Ziel

Ein Mitentwickler versteht aus zwei englischen Dokumenten, wie das Gerüst aufgebaut ist und wie er es startet und prüft. a7 kann die Abnahme von M0 anhand der README Schritt für Schritt nachvollziehen.

## Umfang

- `docs/ARCHITECTURE.md` (Englisch), beschränkt auf das, was nach M0 wirklich vorhanden ist:
  - Container und ihre Aufgaben: `api`, `worker`, `db`, `valkey`, `docling`; Ollama außerhalb auf dem Host.
  - Aufbau des Repositories (Abschnitt 6 der Startunterlage) und der Django-Apps mit je einem Satz zum vorgesehenen Zweck.
  - Aufbau der Compose-Dateien (`compose.yaml` im Wurzelverzeichnis mit `include`, Dateien unter `deploy/compose`, Profile `dev` und `e2e`).
  - Weg einer Anfrage der Testseite durch alle Schichten (Oberfläche → API → Datenbank; API → Broker → Worker → Ergebnis).
  - Die drei Warteschlangen und wofür sie vorgesehen sind.
  - Wie der API-Client der Oberfläche aus dem OpenAPI-Schema entsteht.
  - Tabelle der Umgebungsvariablen (`TWOX_...`) mit Bedeutung und Vorgabe, abgeglichen mit `.env.example`.
  - Qualitätswerkzeuge und die Befehle dafür (einschließlich `pytest` und `pytest -m worker`); welche Prüfungen in der CI laufen und welche nicht (Docling, Ollama, Prüffragen).
- `README.md` (Englisch) im Wurzelverzeichnis:
  - Ein Absatz, was 2x ist (aus Abschnitt 1 der Startunterlage), Hinweis auf den frühen Stand.
  - Voraussetzungen: Docker mit Compose; Ollama optional und außerhalb der Container.
  - Schnellstart: `.env.example` kopieren, `docker compose up`, Adresse der Testseite.
  - Prüfbefehle `check_llm` und `check_docling` mit der Bedeutung ihrer Ausgaben.
  - Befehle für Lint, Typprüfung, Tests, Browser-Test, Lizenzprüfung und Suche nach Geheimnissen.
  - Hinweis zur Größe und Anlaufzeit des Docling-Images.
  - Lizenz (Apache-2.0).

## Nicht-Ziele

- Beschreibung von Funktionen, die es noch nicht gibt (Einlesen, Suche, Auskunft, Anmeldung). Höchstens ein Verweis auf `docs/ROADMAP.md`.
- Installationsanleitung für fremde Rechner (M6).
- Änderungen an Code, Compose-Dateien oder CI. Stimmt ein Befehl nicht: nicht den Code ändern, sondern im Kurzbericht melden.
- `docs/DECISIONS.md`, `docs/STATUS.md`, `docs/ROADMAP.md`, `CLAUDE.md` – pflegt die Leitstelle.

## Betroffene Bereiche (Ordner, Dateien)

- `docs/ARCHITECTURE.md` (neu)
- `README.md` (neu)

## Akzeptanzkriterien (prüfbar)

Vorher `.env.example` nach `.env` kopieren (falls nicht vorhanden) und darin `TWOX_API_PORT=18015` setzen; alle Läufe mit `-p twox-015`.

0. Vorab: `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren oder ausführen; Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. Jeder Befehl aus der README (Schnellstart, Prüfbefehle, Lint, Typprüfung, Tests, Browser-Test, Lizenzprüfung, Suche nach Geheimnissen im Verzeichnis) wurde im Arbeitsverzeichnis in der angegebenen Reihenfolge ausgeführt und verhält sich wie beschrieben. Die Liste der Befehle mit Ergebnis steht im Kurzbericht. Ausnahme: Für `check_llm` genügt eine der beiden beschriebenen Ausgaben (`OK:` oder `FAILED:`).
2. Jede Umgebungsvariable aus `.env.example` steht in der Tabelle und umgekehrt: `git grep -o -h -E 'TWOX_[A-Z_]+' -- .env.example | sort -u` und derselbe Befehl für `docs/ARCHITECTURE.md` liefern dieselbe Liste.
3. Jeder in den Dokumenten genannte Dienst, Pfad und Befehl existiert: alle Dienstnamen gegen `docker compose -p twox-015 --profile dev --profile e2e config --services`, alle genannten Pfade gegen `git ls-files`.
4. Beide Dateien sind auf Englisch; `git grep -n -I -E '[äöüÄÖÜß]' -- README.md docs/ARCHITECTURE.md` ist leer.
5. Keine persönlichen Angaben und keine rechnerspezifischen Pfade: `git grep -n -i -e 'a7' -e 'Desktop' -- README.md docs/ARCHITECTURE.md` ist leer.
6. Die Dokumente nennen keine Funktion als vorhanden, die es nach M0 nicht gibt (Durchsicht durch die Leitstelle).
7. `git diff --stat main...HEAD` zeigt nur `README.md`, `docs/ARCHITECTURE.md` und diese Auftragsdatei.
8. Die Suche nach Geheimnissen bleibt ohne Fund: `docker compose -p twox-015 -f deploy/compose/compose.tools.yaml run --rm gitleaks-dir` endet mit Exit-Code 0.
9. Abräumen: `docker compose -p twox-015 down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

**Nachtrag der Leitstelle (21.11.2026):** `.env.example` setzt `TWOX_DEBUG=true` für die Entwicklung; im Browser zeigt Django deshalb bei 404 die URL-Liste. Die README muss sagen, dass `TWOX_DEBUG` für jeden Betrieb außerhalb der Entwicklung leer bzw. `false` bleibt (Vorgabe in `settings.py` ist aus). Für M6 (Installation in 10 Minuten) braucht es eine eigene Vorlage ohne Debug – als Hinweis für den M6-Auftrag in den Kurzbericht.

- **Voraussetzung:** Die Aufträge 006, 007, 009, 013 und 014 sind zusammengeführt (damit alle M0-Aufträge außer der Messung 004, die für die Doku nicht gebraucht wird).
- **Keine neue Abhängigkeit**, kein Werkzeug zur Doku-Erzeugung. Schaubilder als Text oder als Mermaid-Block im Markdown (wird von GitHub dargestellt; nichts wird installiert). Stufe B gilt nur, solange das so bleibt.
- Sprache nach Abschnitt 7: README und Entwicklerdoku Englisch.
- Keine Auszüge aus fremden Handbüchern, kein Material des Arbeitgebers (Leitplanke 1, Abschnitt 10.4).
- Versionen nicht im Fließtext wiederholen, sondern auf die Dateien verweisen, in denen sie festgeschrieben sind (`uv.lock`, `package-lock.json`, Compose-Dateien). So veraltet die Doku nicht.
- Der Start aller Container einschließlich Docling dauert beim ersten Mal lange (Image mehrere Gigabyte); als Hintergrundbefehl starten.
- Parallele Arbeitsverzeichnisse: immer mit `-p twox-015` und Port 18015 arbeiten. In der README steht der Normalfall (Port 8000, kein `-p`).
- Kein Push. Die Leitstelle committet nach `main` und pusht auf a7s Freigabe.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Akzeptanzkriterien erfüllt; die Läufe fanden am 21.11.2026 statt. Keine offene Frage an a7.

### Was wurde gebaut?

- `README.md` (neu, Englisch): Zweck in zwei Sätzen und Hinweis auf den frühen Stand (Verweis auf `docs/ROADMAP.md`), Voraussetzungen (Docker mit Compose-Plugin, Plattenbedarf Docling, Ollama optional auf dem Host), Schnellstart (`cp .env.example .env`, `docker compose up -d --wait`, `http://localhost:8000/` mit erwarteter Anzeige), Dienste und Netze (Docling nur im internen Netz, E-32), Prüfbefehle `check_docling` und `check_llm` mit allen Ausgängen, Entwicklerbefehle wörtlich wie in `ci.yml` (Backend, Oberfläche, Browser-Test, Testfabrik, Geheimnissuche), was die CI nicht prüft, Sicherheitshinweise (Port nur 127.0.0.1, keine Anmeldung bis M1, `TWOX_DEBUG` nur in der Entwicklung, keine Telemetrie), Lizenz Apache-2.0 mit Verweis auf `/static/THIRD-PARTY-NOTICES.txt` und `docs/DECISIONS.md`. Testfabrik mit Lizenzhinweis (keine Herstellerunterlagen im Repository, `fetch.py` lädt lokal, Siemens nur von Hand, E-27).
- `docs/ARCHITECTURE.md` (neu, Englisch): Container mit Mermaid-Schaubild und Tabelle, Netze, Einschränkungen von Docling (nur RapidOCR, kein Vorwärmen), Stufen der Dockerfiles, Aufbau des Repositorys, die neun Django-Apps bzw. `config` mit vorgesehenem Zweck und Inhalt in M0, Aufbau der Compose-Dateien und Profile, Weg der Testseiten-Anfrage (Mermaid-Sequenzdiagramm und fünf Schritte), die drei Warteschlangen, API und erzeugter Client, Tabelle der 13 Umgebungsvariablen (Bedeutung, Wert in `.env.example`, Verhalten ohne Wert), Qualitätswerkzeuge, was die CI prüft und was nicht (Docling, Ollama, Prüffragen, `fetch.py`).
- Keine Änderung an Code, Compose-Dateien oder CI.

### Wie wurde getestet?

`.env` aus `.env.example` mit `TWOX_API_PORT=18015`; alle Läufe mit `-p twox-015` im Arbeitsverzeichnis, Docker Engine 29.9.3, Compose v5.7.0. Das Projekt `2x` lief durchgehend weiter und wurde nicht angefasst.

| Nr. | Ergebnis | Nachweis (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version` (29.9.3) und `docker compose version` (v5.7.0), Exit 0 |
| 1 | erfüllt, mit einer Korrektur der README | siehe Befehlsliste unten |
| 2 | erfüllt | beide `git grep` (mit `sort -u`) liefern dieselben 13 Variablen (`diff` Exit 0) |
| 3 | erfüllt, mit Hinweis | alle Dienstnamen in `config --services` (Hauptdatei mit `--profile dev --profile e2e`: api, backend-dev, db, docling, e2e, migrate, valkey, web-dev, worker; `compose.tools.yaml`: gitleaks-dir, gitleaks-git; `testfactory.yaml`: check, check-offline, fetch). Alle genannten Repository-Pfade in `git ls-files`; Ausnahmen siehe Abweichungen |
| 4 | erfüllt | `git grep` ohne Treffer (Exit 1); beide Dateien sind reines ASCII |
| 5 | erfüllt | `git grep -i -e 'a7' -e 'Desktop'` ohne Treffer (Exit 1) |
| 6 | Durchsicht der Leitstelle | Nicht Vorhandenes ist als geplant bzw. „not present yet“ gekennzeichnet |
| 7 | erfüllt | vor dem Bericht: nur `README.md` und `docs/ARCHITECTURE.md`; mit diesem Commit zusätzlich die Auftragsdatei |
| 8 | erfüllt | `gitleaks-dir`: `no leaks found`, Exit 0 |
| 9 | erfüllt | `down -v` Exit 0 (Volumes `db-data`, `valkey-data`, `web_node_modules`, beide Netze entfernt); danach `--profile dev --profile e2e down -v` Exit 0; keine Container, Volumes oder Netze von `twox-015` mehr |

Befehle aus der README in deren Reihenfolge (jeweils mit `-p twox-015`):

| Befehl | Ergebnis |
| --- | --- |
| `up -d --wait` (alle Dienste mit Docling) | Exit 0 nach 21 s (Images im Cache), alle `healthy`, `migrate` beendet |
| Testseite `http://localhost:18015/` | `200 text/html`; `/api/v1/selftest/`: Datenbank `ok` (18.7), Worker `pong`; `/static/THIRD-PARTY-NOTICES.txt` 200 |
| `exec api python manage.py check_docling` | `OK: docling-serve 1.38.2 at http://docling:5001`, Exit 0 |
| `exec api python manage.py check_llm` | `OK: http://host.docker.internal:11434/v1/models is reachable, 0 model(s) reported`, Exit 0 |
| Backend: `--profile dev build …`, `up … db valkey worker api`, `ruff check .`, `ruff format --check .`, `mypy .`, `pytest`, `pytest -m worker`, `makemigrations --check --dry-run`, `sh scripts/check-licenses.sh` | alle Exit 0; `110 passed, 4 deselected`; `4 passed, 110 deselected`; 53 Pakete, `License check passed.` |
| Schema aktuell (`spectacular --file /out/schema.yml`, `git diff --exit-code -- web/openapi`) | erster Lauf in Git Bash **Exit 1** (`FileNotFoundError: 'C:/Program Files/Git/out/schema.yml'`, Pfadumschreibung von Git Bash). Mit `MSYS_NO_PATHCONV=1` Exit 0, Datei neu geschrieben, `git diff` Exit 0. README um diesen Hinweis ergänzt |
| Oberfläche mit `-f deploy/compose/compose.web.yaml`: `build web-dev`, `npm ci`, `lint`, `typecheck`, `test`, `build`, `licenses`, `api:generate`, danach `git diff --exit-code -- web/openapi web/src/api` | alle Exit 0; `Tests 10 passed (10)`; 394 Pakete, `License check passed.` |
| Browser-Test: `--profile e2e pull e2e`, `--profile dev run --rm web-dev npm ci`, `up … db valkey worker api`, `--profile e2e run --rm e2e` | alle Exit 0; `1 passed` |
| Testfabrik: alle neun Befehle aus `ci.yml` | alle Exit 0; `Ran 215 tests … OK (skipped=1)`; Manifeste `OK (31 entries)` bzw. `OK (10 entries)`, beide `already in canonical form` |
| `-f deploy/compose/compose.tools.yaml run --rm gitleaks-dir` | `no leaks found`, Exit 0 |
| `--profile dev --profile e2e down -v` | Exit 0 |

Nicht ausgeführt: `gitleaks-git` (im Arbeitsverzeichnis ist `.git` nur eine Verweisdatei; die README sagt, dass es einen normalen Klon braucht), `docker compose down` ohne `-v` (nur in der README erwähnt), die PowerShell-Variante `Copy-Item .env.example .env` (`.env` lag schon vor) und `docker compose -f deploy/compose/compose.web.yaml …` ohne `-p` (dass Compose dann das Projekt `compose` nimmt, ist nur mit `config` belegt: `name: compose`).

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a260e393c6aec0bce`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a260e393c6aec0bce` (relativ zum Projektordner)

### Abweichungen und Hinweise

- **Wort „Desktop“:** Die Leitstelle nannte als Voraussetzung „Docker Desktop/Engine“; Kriterium 5 verbietet das Wort. Die README sagt „Docker with the Compose plugin“ und erwähnt nur „Docker with WSL 2 on Windows“ als Entwicklungsrechner.
- **Pfade, die nicht in `git ls-files` stehen (Kriterium 3):** `.env` (legt der Nutzer an), `testfactory/extern/` (ignoriert, nur lokal), `/static/THIRD-PARTY-NOTICES.txt` (entsteht beim Bau des Images, URL-Pfad), `deploy/helm` und `testfactory/generated/` (ausdrücklich als „not present yet“ genannt, weil Abschnitt 6 der Startunterlage sie vorsieht). Kurzformen wie `celery.py` stehen in der Tabelle unter `backend/twox/config/`.
- **Zwei `TWOX_`-Variablen fehlen in `.env.example`:** `TWOX_WEB_DIST_DIR` (nur beim Bau, `backend/Dockerfile`) und `TWOX_E2E_API_URL` (`compose.web.yaml`). Wegen Kriterium 2 nennt `docs/ARCHITECTURE.md` sie nicht beim Namen, sondern beschreibt sie mit Verweis auf die Dateien.
- **Entwicklerbefehle der Oberfläche** stehen wie in `ci.yml` mit `-f deploy/compose/compose.web.yaml`. Ohne `-p` läuft das als eigenes Projekt `compose` mit eigenem `node_modules`-Volume; die README sagt das. Der Browser-Test nutzt das Hauptprojekt.
- **Schema-Prüfung in Git Bash** braucht `MSYS_NO_PATHCONV=1` (siehe oben). In `ci.yml` ist nichts zu ändern (Linux). Dieselbe Falle betrifft vermutlich den Befehl in `web/openapi/README.md` (`$(pwd)/web/openapi:/out`); dort nicht geändert, weil außerhalb des Bereichs.
- **Hinweis für M6:** `.env.example` ist eine Entwicklungsvorlage (`TWOX_DEBUG=true`, Entwicklungs-Kennwörter). Für „Installation in 10 Minuten“ braucht es eine eigene Vorlage ohne Debug und mit Aufforderung zu eigenen Geheimnissen.
- **Gelesen:** alle Kurzberichte 001–014 vollständig; von 101–114 nur 109 und 114 vollständig, die übrigen nicht im Einzelnen (die Testfabrik ist über `testfactory/README.md` beschrieben, auf die verwiesen wird).
- Lokal liegen noch die Images `twox-015-api`, `-worker`, `-migrate`, `-backend-dev`, `-web-dev`; die lokale `.env` (ignoriert) hat `TWOX_API_PORT=18015`.
