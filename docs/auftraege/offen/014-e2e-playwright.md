# Auftrag 014 – Playwright-Test der Testseite

Meilenstein: M0 · Freigabestufe: C · Status: zur Prüfung

## Ziel

Ein Browser-Test belegt automatisch die Abnahme von M0: Die von Django ausgelieferte Testseite zeigt einen Wert aus der Datenbank und ein Ergebnis aus dem Worker. Der Test läuft lokal im Container und in der CI.

## Umfang

- `web/playwright.config.ts` und `web/e2e/selftest.spec.ts`. Der Test öffnet die von Django ausgelieferte Seite und erwartet:
  - eine sichtbare Versionsnummer der Datenbank (Muster Zahl.Zahl),
  - das sichtbare Worker-Ergebnis `pong`,
  - keinen Fehlerzustand und keine Fehlermeldung in der Browser-Konsole.
- Nur ein Browser: Chromium.
- Dienst `e2e` (Profil `e2e`) in `deploy/compose/compose.web.yaml` auf Grundlage des offiziellen Playwright-Images, dessen Version exakt zur Version von `@playwright/test` passt. Die Adresse der API kommt aus einer Umgebungsvariable (Vorgabe `http://api:8000`). Der Dienst hat **kein** `depends_on` auf Dienste anderer Dateien und keinen Host-Port.
- `compose.yaml` im Wurzelverzeichnis: Die `include`-Liste nimmt `deploy/compose/compose.web.yaml` auf. Damit liegen `e2e` und `api` im selben Projekt und Netz, und der Aufruf ist derselbe wie überall (`docker compose` im Wurzelverzeichnis, `.env` im Wurzelverzeichnis). `web-dev` und `e2e` stehen in Profilen und starten bei `docker compose up` nicht mit.
- npm-Skript `e2e`.
- `.github/workflows/ci.yml`:
  - neuer Job `e2e` (Images bauen, `db`, `valkey`, `worker`, `api` starten, Test ausführen, bei Fehlschlag Protokolle und Playwright-Bericht ausgeben),
  - im Job `web` zusätzlich `npm run api:generate` gefolgt von `git diff --exit-code -- web/src/api` (der eingecheckte Client ist aktuell).
- Liste der Abnahmebefehle für M0 im Kurzbericht (für a7 zum Nachvollziehen).

## Nicht-Ziele

- Weitere Browser, Bildvergleiche, Tests weiterer Seiten.
- Docling in der CI.
- Änderungen an der Testseite oder am Backend. Fehlt dem Test trotz Auftrag 012 ein stabiles Merkmal: nur ein Testmerkmal (`data-testid`) ergänzen.

## Betroffene Bereiche (Ordner, Dateien)

- `web/e2e/**`, `web/playwright.config.ts` (neu)
- `web/package.json`, `web/package-lock.json`
- `web/src/**` nur für Testmerkmale, falls nötig
- `web/scripts/` (nur die Regeldatei der Lizenzprüfung, falls nötig)
- `deploy/compose/compose.web.yaml` (Dienst `e2e`)
- `compose.yaml` im Wurzelverzeichnis (eine Zeile in `include`)
- `.github/workflows/ci.yml` (Job `e2e`, Aktualitätsprüfung des Clients)

## Akzeptanzkriterien (prüfbar)

Alle Befehle im Wurzelverzeichnis. `D` steht für `docker compose -p twox-014`, `W` für `docker compose -p twox-014 -f deploy/compose/compose.web.yaml`. Vorher `.env.example` nach `.env` kopieren (falls nicht vorhanden) und darin `TWOX_API_PORT=18014` setzen.

0. Vorab: `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren oder ausführen; Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. `D config --services` nennt `db`, `valkey`, `worker`, `api`, `docling`; mit `D --profile dev --profile e2e config --services` zusätzlich `backend-dev`, `web-dev` und `e2e`. `W config` (die Web-Datei allein) endet weiter mit Exit-Code 0.
2. `D up -d --wait db valkey worker api` endet mit Exit-Code 0; `D ps` zeigt weder `web-dev` noch `e2e` als gestartet.
3. `D --profile e2e run --rm e2e` endet mit Exit-Code 0; die Ausgabe nennt mindestens einen bestandenen Test und 0 fehlgeschlagene.
4. Gegenprobe: Nach `D stop worker` endet derselbe Befehl mit Exit-Code ungleich 0, und die Meldung zeigt, dass `pong` nicht erschien. Danach `D start worker`.
5. Die Version des Playwright-Images und die Version von `@playwright/test` in `web/package-lock.json` stimmen überein (beide im Kurzbericht genannt).
6. `W run --rm web-dev npm run lint`, `npm run typecheck` und `npm run test` enden mit Exit-Code 0; Vitest führt die Playwright-Dateien nicht aus und umgekehrt.
7. Lizenzprüfung: `W run --rm web-dev npm run licenses` endet mit Exit-Code 0. Meldet sie ein Paket mit nicht gedeckter Lizenz: Frage in den Auftrag, Status „wartet auf a7“.
8. `git grep -n 'uses:' -- .github/workflows/ci.yml` zeigt weiterhin nur `actions/checkout`.
9. Jeder Befehl des neuen Jobs `e2e` und die Aktualitätsprüfung des Clients laufen lokal mit Exit-Code 0 durch (Liste im Kurzbericht).
10. Testberichte und Aufzeichnungen sind nicht eingecheckt: `git check-ignore -q web/playwright-report web/test-results` endet mit Exit-Code 0, und `git status --short` zeigt nach einem Lauf nichts Neues. Fehlt ein Eintrag in der `.gitignore`: nicht selbst ändern, im Kurzbericht melden.
11. Abräumen: `D down -v` endet mit Exit-Code 0.
12. Nach dem Push durch die Leitstelle (auf a7s Freigabe): `gh run list --workflow ci.yml --limit 1 --json conclusion` zeigt `success` einschließlich des Jobs `e2e`. Diesen Punkt prüft die Leitstelle; bis dahin bleibt der Auftrag „zur Prüfung“.

## Vorgaben und Hinweise

**Nachtrag der Leitstelle (21.11.2026, aus der Prüfung von Auftrag 002):** Der Dienst `web-dev` liegt im Profil `dev`. Deshalb gilt abweichend vom Wortlaut dieses Auftrags: Bauen mit `build web-dev` oder `--profile dev build`; Abräumen mit `--profile dev down -v` (bei Playwright zusätzlich `--profile e2e`); den Dienst immer über `run --rm web-dev` ansprechen – ein bloßes `build`, `up` oder `down -v` ohne Profil tut nichts und meldet trotzdem Erfolg. `git check-ignore -q` nimmt nur einen Pfad je Aufruf. Zugelassene Lizenzen bei reinen Entwicklungs- und Build-Paketen zusätzlich: BlueOak-1.0.0, CC-BY-3.0, CC-BY-4.0, CC0-1.0 (E-25).

- **Voraussetzung:** Die Aufträge 011, 012 und 013 sind zusammengeführt (und damit alle davor außer 004 und 007).
- **Abhängigkeiten.** Mit der Freigabe der Auftragsliste genehmigt a7 `@playwright/test`, das offizielle Playwright-Container-Image und den darin enthaltenen Browser Chromium (nur für Tests, nicht Teil des Produkts). Mitgezogene npm-Pakete sind mitgenehmigt, soweit die Lizenzprüfung sie durchlässt. Jede weitere direkte Abhängigkeit ist nicht genehmigt.
- **Stand der Recherche vom 21.11.2026 (belegt):** `@playwright/test` 1.65.1, Apache-2.0, Node >=20.
- **Ungeprüft und an der Quelle zu prüfen:** Name und Tags des Images `mcr.microsoft.com/playwright` und dass es exakt zur Paketversion passen muss; Lizenz des Images und der mitgelieferten Browser (Chromium BSD; Firefox MPL-2.0 und WebKit LGPL werden nicht verwendet). Ist eine Lizenz nicht feststellbar oder nicht zulässig: nicht einbauen, Frage in den Auftrag, Status „wartet auf a7“.
- **Ungeprüft:** dass Dienste aus zwei per `include` eingebundenen Dateien ein gemeinsames Standardnetz haben (Kriterium 3 ist der Nachweis). Klappt es nicht: Befund und Vorschlag in den Auftrag, nicht auf `-f`-Ketten ausweichen (dabei richten sich relative Pfade nach der ersten Datei, und `compose.web.yaml` würde allein nicht mehr gleich funktionieren).
- Das Image ist groß. Lokal als Hintergrundbefehl ziehen; die erwartete Laufzeit des CI-Jobs nennen. Überschreitet der Job voraussichtlich etwa 10 Minuten: Vorschlag in den Kurzbericht, keine Fremd-Action eigenmächtig einbauen.
- Der Test wartet auf Inhalte (mit Zeitlimit), nicht mit festen Pausen.
- Parallele Arbeitsverzeichnisse: immer mit `-p twox-014` und Port 18014 arbeiten.
- Sprache: Code und Testnamen Englisch.
- Abnahmeliste im Kurzbericht: `docker compose up -d --wait` im Wurzelverzeichnis; Testseite unter `http://localhost:8000/` zeigt Datenbankversion und `pong`; Browser-Test; `check_docling`; `check_llm` (mit dem Hinweis, dass `OK:` ein laufendes Ollama voraussetzt); CI-Läufe `ci.yml` und `secrets.yml` grün.
- `.gitignore`, `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Im Kurzbericht Name, Version, Lizenz und Quelle nennen.
- Kein Push. Die Leitstelle committet nach `main` und pusht auf a7s Freigabe.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

Keine zum Start.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Die lokal prüfbaren Kriterien 0–11 sind erfüllt; die Läufe fanden am 21.11.2026 im Container statt. Kriterium 12 (Lauf auf GitHub) ist offen und folgt nach dem Push durch die Leitstelle. Keine offene Frage an a7; zwei Hinweise zum Image unter „Abweichungen und Hinweise“.

### Was wurde gebaut?

- `web/playwright.config.ts`: nur Projekt `chromium` (`devices["Desktop Chrome"]`), `testDir ./e2e`, ein Worker, keine Wiederholungen, `forbidOnly` bei gesetztem `CI`, Zeitlimit je Erwartung 20 s (die API wartet bis 5 s auf den Worker), Berichte `list` und `html` (`open: "never"`) nach `web/playwright-report`, Ausgaben nach `web/test-results` (Spur und Bildschirmfoto nur bei Fehlschlag). Adresse aus `TWOX_E2E_API_URL`, Vorgabe `http://api:8000`.
- **Host-Kopf:** Django nimmt nur Namen aus `TWOX_ALLOWED_HOSTS` an, und `.env.example` nennt nur `localhost` und `127.0.0.1`. Ein Aufruf mit `Host: api` ergibt 400 (geprüft: `fetch('http://api:8000/')` im Dienst `e2e` → `400`). Der Browser öffnet deshalb `http://localhost:8000/`, und Chromium löst `localhost` per Startoption `--host-resolver-rules=MAP localhost api` auf den Dienst `api` auf. Backend und `.env.example` bleiben unverändert. Ist die Adresse selbst `localhost`/`127.0.0.1`, entfällt die Umleitung.
- `web/e2e/selftest.spec.ts`: ein Test. Öffnet `/` (Status 200) und wartet auf `database-version` mit Muster `\d+\.\d+`, `worker-result` = `pong`, `database-status` und `worker-status` = `OK`; danach keine Elemente `selftest-loading`, `selftest-error`, `database-error`, `worker-error` und keine Konsolenfehler (`console` vom Typ `error` und `pageerror`). Nur Warten auf Inhalte, keine festen Pausen. Kein neues Testmerkmal nötig, `web/src` unverändert.
- `web/package.json`: Skript `e2e` (`playwright test`), Entwicklungsabhängigkeit `@playwright/test` `1.65.1` (exakt). `web/tsconfig.json`: `playwright.config.ts` und `e2e` in `include` (damit Typprüfung und typbasiertes ESLint sie erfassen). Weil `@types/node` keine Abhängigkeit ist, deklariert die Konfiguration `process.env` lokal.
- `deploy/compose/compose.web.yaml`: Dienst `e2e` im Profil `e2e`, Image `mcr.microsoft.com/playwright:v1.65.1-noble@sha256:1507cbfc550a63a6b7396791ca4f00df17beb56342d2447b3f106c306f525579` (Multi-Plattform-Index), `init: true`, `shm_size: 1gb` (statt `ipc: host`), `CI=true`, `TWOX_E2E_API_URL` mit Vorgabe, Bind-Mount `../../web` und dasselbe Volume `web_node_modules` wie `web-dev`. Kein `depends_on`, kein Host-Port, kein Bau. Kopfkommentar um die Aufrufe ergänzt.
- `compose.yaml`: `include` nimmt `deploy/compose/compose.web.yaml` auf.
- `.github/workflows/ci.yml`: neuer Job `e2e` als letzter Block (bestehende Jobs unverändert): Check out (`actions/checkout` per SHA wie in den anderen Jobs, `persist-credentials: false`; `permissions: contents: read` gilt workflow-weit), Versionen, `cp .env.example .env`, `docker compose --profile dev build migrate api worker web-dev`, `docker compose --profile e2e pull e2e`, `docker compose --profile dev run --rm web-dev npm ci`, `docker compose up -d --wait --wait-timeout 300 db valkey worker api`, `docker compose --profile e2e run --rm e2e`; bei Fehlschlag `ps -a`, `logs` und Liste plus Inhalt der `error-context.md` aus `web/test-results`. Zeitlimit 20 min. Docling startet nicht.
- **Aktualitätsprüfung des Clients:** steht schon im Job `web` (Auftrag 011, Schritt „API client up to date“: `npm run api:generate`, `git diff --exit-code -- web/openapi web/src/api` und `git status --porcelain`). Ich habe sie nicht doppelt eingebaut; der Schritt lief lokal mit (siehe Kriterium 9).

### Neue Abhängigkeiten

| Name | Version | Lizenz | Quelle | Art |
| --- | --- | --- | --- | --- |
| @playwright/test | 1.65.1 | Apache-2.0 | npm-Registry (`npm view @playwright/test`, im Container am 21.11.2026: `latest` 1.65.1, `license` Apache-2.0), https://github.com/microsoft/playwright | direkt, nur Entwicklung |
| playwright, playwright-core | 1.65.1 | Apache-2.0 | `web/package-lock.json`, Lizenzprüfung | mitgezogen |
| Image `mcr.microsoft.com/playwright:v1.65.1-noble` | Digest `sha256:1507cbfc…525579` (Index; amd64 `sha256:766137e2…dd0a9`, arm64 `sha256:56be08ac…aba4`) | Playwright Apache-2.0 (LICENSE im Repository microsoft/playwright); Chromium BSD-3-Clause (Kopf von `/ms-playwright/chromium_headless_shell-1255/chrome-linux64/LICENSE.headless_shell`: „The Chromium Project“ mit BSD-Text, danach Lizenzen der Drittbestandteile); Node.js 26.13.1 MIT; Grundsystem Ubuntu 24.04.5 gemischt, ungeprüft | Label `org.opencontainers.image.source=https://github.com/microsoft/playwright`, `org.opencontainers.image.version=1.65.1`; Doku https://playwright.dev/docs/docker; Dockerfile `utils/docker/Dockerfile.noble` | unveränderte Testlaufzeit (E-23), nicht im Produkt |

Tag-Muster und Versionsbindung an der Quelle geprüft: Die Doku nennt `mcr.microsoft.com/playwright:v<Version>-noble` und warnt, dass Playwright bei abweichender Version die Browser nicht findet. **Kriterium 5:** Image-Version 1.65.1 (Tag und Label) = `@playwright/test` 1.65.1 in `web/package-lock.json`.

### Wie wurde getestet?

`D` = `docker compose -p twox-014`, `W` = `docker compose -p twox-014 -f deploy/compose/compose.web.yaml`; `.env` aus `.env.example` mit `TWOX_API_PORT=18014`; Docker Engine 29.9.3, Compose v5.7.0. Projekt `2x` lief durchgehend weiter und wurde nicht angefasst.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `29.9.3`, `Docker Compose version v5.7.0`, beide Exit 0 |
| 1 | erfüllt | `D config --services`: `docling db migrate valkey worker api`, Exit 0; mit `--profile dev --profile e2e` zusätzlich `backend-dev e2e web-dev`, Exit 0; `W config -q` Exit 0 |
| 2 | erfüllt | Exit 0; `db`, `valkey`, `api`, `worker` `Healthy`, `migrate` `Exited`; `D ps` zeigt nur `api db valkey worker` |
| 3 | erfüllt | `✓ 1 [chromium] › e2e/selftest.spec.ts:5:1 › self-test page shows the database version and the worker result (1.1s)`, `1 passed (2.2s)`, Exit 0. Damit ist auch das gemeinsame Netz über `include` belegt |
| 4 | erfüllt | nach `D stop worker`: `✘ … (25.7s)`, `Locator: getByTestId('worker-result')`, `Expected: "pong"`, `Error: element(s) not found`, `1 failed`, Exit 1; die Seite zeigt `no result from a worker within 5 seconds`. Danach `D start worker` Exit 0, erneuter Lauf `1 passed`, Exit 0 |
| 5 | erfüllt | Image `v1.65.1-noble` (Label `1.65.1`), Paket `@playwright/test` 1.65.1 |
| 6 | erfüllt | `lint` Exit 0, `typecheck` Exit 0, `test` Exit 0 mit „Test Files 3 passed (3)“, „Tests 10 passed (10)“ (nur `src/`); Playwright meldet genau 1 Test aus `e2e/` |
| 7 | erfüllt | 394 Pakete, „License check passed.“, Exit 0; Regeldatei unverändert |
| 8 | erfüllt | drei Treffer, alle `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1` (Zeilen 29, 91, 148) |
| 9 | erfüllt | siehe Tabelle unten |
| 10 | erfüllt | `git check-ignore -q web/playwright-report` Exit 0, `git check-ignore -q web/test-results` Exit 0 (je ein Aufruf); `git status --short` nach den Läufen ohne neue Einträge. `.gitignore` unverändert |
| 11 | erfüllt | `D down -v` Exit 0 (entfernt auch `web_node_modules`, weil das Volume über `include` zum Projekt gehört); zusätzlich `D --profile dev --profile e2e down -v` und `W --profile dev --profile e2e down -v` Exit 0. Danach keine Container, Volumes oder Netze von `twox-014` |
| 12 | offen, nach Push | prüft die Leitstelle |

**Kriterium 9:** Die `run`-Schritte wurden mit PyYAML (Wegwerf-Container, `--network none`) aus `ci.yml` unverändert als Dateien herausgeschrieben und in Git Bash mit `bash --noprofile --norc -eo pipefail <Datei> < /dev/null` ausgeführt (`COMPOSE_PROJECT_NAME=twox-014`, `TWOX_API_PORT=18014` als Umgebung, weil Schritt 3 die `.env` überschreibt). Images aus dem lokalen Cache.

| Job | Schritt | Exit | s | Ausgabe |
| --- | --- | --- | --- | --- |
| e2e | 2 Versionen | 0 | 1 | wie Kriterium 0 |
| e2e | 3 `.env` | 0 | 0 | – |
| e2e | 4 Bauen | 0 | 3 | `twox-014-migrate`, `-api`, `-worker`, `-web-dev` Built |
| e2e | 5 Image ziehen | 0 | 0 | `… v1.65.1-noble@sha256:1507cbfc… Pulled` |
| e2e | 6 npm ci | 0 | 8 | `added 417 packages` |
| e2e | 7 Start | 0 | 20 | `db`, `valkey`, `api`, `worker` `Healthy` |
| e2e | 8 Browser-Test | 0 | 3 | `1 passed (1.7s)` |
| e2e | 9 nur bei Fehlschlag | 0 | – | Gegenprobe mit gestopptem Worker: Schritt 8 Exit 1, danach Schritt 9 Exit 0 mit `ps -a`, Protokollen (`WorkerTimeoutError: no result from a worker within 5 seconds`), Dateiliste (`error-context.md`, `test-failed-1.png`, `trace.zip`, `.last-run.json`) und dem Inhalt von `error-context.md` (Fehler, Seitenausschnitt mit `alert: no result from a worker within 5 seconds`) |
| web | 11 Client aktuell (unverändert aus 011) | 0 | – | `./src/api/generated · 4 files`, keine Abweichung |

**Laufzeit:** lokal (warmer Cache) etwa 35 s für den Job. Auf dem Runner kommen hinzu: kalter Bau der Runtime-Images (Backend und Oberfläche) und `web-dev`, das Ziehen des Playwright-Images (amd64 komprimiert rund 966 MB, entpackt 3,67 GB) sowie die Basis-Images. Erwartet: etwa 5–8 Minuten, nicht gemessen. Damit unter der Grenze von etwa 10 Minuten; kein Vorschlag nötig. Plattenbedarf (14 GB Runner-SSD) sollte reichen, ist aber erst im ersten Lauf belegt.

### Abnahmebefehle für M0 (für a7, im Wurzelverzeichnis)

1. `.env.example` nach `.env` kopieren (falls nicht vorhanden).
2. `docker compose up -d --wait` – alle Dienste einschließlich `docling` laufen und sind `healthy`.
3. Browser: `http://localhost:8000/` zeigt „Database – OK – Server version: …“ (Zahl.Zahl) und „Worker – OK – Result: pong“.
4. Browser-Test: `docker compose --profile dev run --rm web-dev npm ci`, danach `docker compose --profile e2e run --rm e2e` – Ausgabe `1 passed`, Exit 0.
5. `docker compose exec api python manage.py check_docling` – `OK: docling-serve …` (`backend-dev` hängt nicht am Docling-Netz).
6. `docker compose --profile dev run --rm backend-dev python manage.py check_llm` – `OK:` setzt ein laufendes Ollama auf dem Rechner voraus; sonst `FAILED: …`.
7. GitHub: letzte Läufe von `ci.yml` (Jobs `backend`, `web`, `e2e`) und `secrets.yml` grün, z. B. `gh run list --workflow ci.yml --limit 1 --json conclusion` und dasselbe für `secrets.yml`.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-aaaf215ba0032ac48`
- Arbeitsverzeichnis: `.claude/worktrees/agent-aaaf215ba0032ac48` (relativ zum Projektordner)

### Abweichungen und Hinweise

- **Host-Umleitung im Browser** (siehe oben) statt `api` in `TWOX_ALLOWED_HOSTS`. Alternative für die Leitstelle: `api` in `.env.example` aufnehmen (außerhalb meines Bereichs); dann könnte die Umleitung entfallen.
- **Inhalt des Images über Chromium hinaus:** Das offizielle Image enthält alle Browser: `chromium-1255`, `chromium_headless_shell-1255`, `firefox-1572` (MPL-2.0), `webkit-2388` (LGPL/BSD) und `ffmpeg-1013`. Der Ordner `chromium-1255` ist ein Chrome-for-Testing-Build; seine `ABOUT`-Datei nennt „Google Chrome“ und verweist auf die Nutzungsbedingungen, und er enthält einen Ordner `WidevineCdm` (proprietär). Für den kopflosen Lauf verwendet Playwright nach meiner Kenntnis `chromium_headless_shell` (Chromium, BSD); das habe ich nicht einzeln nachgewiesen. Alles bleibt unverändert im Image, wird nicht weitergegeben und ist nicht Teil des Produkts (E-23). Vorschlag fürs Entscheidungsprotokoll: Image mit Digest als Testlaufzeit eintragen und diesen Inhalt vermerken.
- **Image läuft als root** (Vorgabe des Images); Playwright schaltet dann den Chromium-Sandbox ab. Laut Doku für eigene, vertrauenswürdige Seiten in Ordnung; der Test öffnet nur die eigene Testseite.
- **`shm_size: 1gb` statt `ipc: host`:** Die Doku empfiehlt `--ipc=host`; ich habe den Speicher lieber begrenzt vergrößert, statt den IPC-Namensraum des Hosts zu teilen.
- **`e2e` braucht `npm ci` vorher** (gemeinsames Volume mit `web-dev`); der Dienst installiert selbst nichts. In der CI steht der Schritt davor; in der Abnahmeliste auch.
- **Node im Image ist 26.13.1** (in `web-dev` 24); `engines` (`>=24.15.0`) passt. Das Image führt nur `playwright test` aus, kein `npm ci`.
- **Kein eigener Schritt „Client aktuell“** im Job `web`: bestand schon (Auftrag 011).
- `.gitignore`, `docs/DECISIONS.md`, `docs/STATUS.md` und `web/src` sind nicht angefasst. Lokal liegen noch die Images `twox-014-api`, `-worker`, `-migrate`, `-web-dev` und das Playwright-Image; die lokale `.env` (ignoriert) hat `TWOX_API_PORT=18014`.
