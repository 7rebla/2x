# Auftrag 012 – Testseite, Teil Oberfläche

Meilenstein: M0 · Freigabestufe: C · Status: zur Prüfung

## Ziel

Die Oberfläche zeigt auf einer Testseite den Wert aus der Datenbank und das Ergebnis aus dem Worker. Sie spricht die API über einen Client an, der aus der OpenAPI-Beschreibung erzeugt wird (Abschnitt 5.2).

## Umfang

- OpenAPI-Schema des Backends als Datei `web/openapi/schema.yml` (eingecheckt), erzeugt mit `python manage.py spectacular`.
- Client-Generator nach a7s Antwort auf Frage 1 in Auftrag 002 (Empfehlung dort: `@hey-api/openapi-ts`). npm-Skript `api:generate` erzeugt den Client nach `web/src/api/generated/` (eingecheckt).
- Die Testseite ersetzt den Platzhalter aus Auftrag 002 und zeigt:
  - Datenbank: Zustand und `server_version`.
  - Worker: Zustand, `result` und Dauer.
  - Ladezustand, Fehlerzustand je Teil (mit dem Fehlertext der API) und einen eigenen Zustand, wenn die API gar nicht antwortet.
  - Eine Schaltfläche zum erneuten Prüfen.
- Alle sichtbaren Texte liegen gesammelt in einem Modul (Englisch), damit die spätere Übersetzung (Deutsch/Englisch) sie an einer Stelle findet.
- Stabile Testmerkmale (`data-testid`) an den Werten für Datenbankversion, Worker-Ergebnis und Fehlerzustand (für Auftrag 014).
- Vitest-Tests mit nachgestellter API: alles in Ordnung · Worker ausgefallen · API nicht erreichbar · erneutes Prüfen löst einen neuen Abruf aus.
- Die API wird mit relativem Pfad (`/api/...`) angesprochen; Oberfläche und API kommen im Betrieb vom selben Ursprung (Auftrag 013).

## Nicht-Ziele

- Auslieferung der gebauten Oberfläche durch Django (Auftrag 013), Playwright-Test (Auftrag 014).
- Übersetzungsbibliothek, Routing, Anmeldung, Gestaltung über das Nötige hinaus.
- Änderungen am Backend und an Compose-Dateien.

## Betroffene Bereiche (Ordner, Dateien)

- `web/openapi/schema.yml` (neu)
- `web/src/**` (Testseite, Texte, `api/generated/`)
- `web/package.json`, `web/package-lock.json` (Generator, Skript `api:generate`), Konfigurationsdatei des Generators
- ESLint-Konfiguration nur, um den erzeugten Code auszunehmen
- `web/scripts/` (nur die Regeldatei der Lizenzprüfung, falls ein mitgezogenes Paket eine bereits genehmigte Lizenz in neuer Schreibweise trägt)

## Akzeptanzkriterien (prüfbar)

`W` steht für `docker compose -p twox-012 -f deploy/compose/compose.web.yaml`, `B` für `docker compose -p twox-012`. Vorher `.env.example` nach `.env` kopieren (falls nicht vorhanden).

0. Vorab: `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren oder ausführen; Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. `B run --rm backend-dev python manage.py spectacular --file /tmp/schema.yml` erzeugt ein Schema, das inhaltsgleich mit `web/openapi/schema.yml` ist (Vergleich und Ergebnis im Kurzbericht).
2. `W run --rm web-dev npm ci` endet mit Exit-Code 0 ohne `ERESOLVE`.
3. `W run --rm web-dev npm run api:generate` endet mit Exit-Code 0; danach zeigt `git diff --exit-code -- web/src/api` keine Änderung (der eingecheckte Client ist aktuell).
4. `W run --rm web-dev npm run lint` und `W run --rm web-dev npm run typecheck` enden mit Exit-Code 0.
5. `W run --rm web-dev npm run test` endet mit Exit-Code 0; die vier oben genannten Fälle sind dabei, 0 fehlgeschlagen.
6. `W run --rm web-dev npm run build` endet mit Exit-Code 0.
7. Im Quelltext der Oberfläche steht keine feste Serveradresse: `git grep -n -E 'https?://' -- web/src` zeigt keine Treffer außerhalb von Kommentaren und erzeugtem Code ohne Laufzeitwirkung.
8. Die Typen der Antwort stammen aus dem erzeugten Client, nicht aus handgeschriebenen Kopien: `git grep -n 'server_version' -- web/src` zeigt Treffer nur im erzeugten Code, in der Testseite und in Tests.
9. Lizenzprüfung: `W run --rm web-dev npm run licenses` endet mit Exit-Code 0. Meldet sie ein Paket mit nicht gedeckter Lizenz: nichts in die Erlaubt-Liste schreiben, Frage in den Auftrag, Status „wartet auf a7“.
10. `web/openapi/schema.yml` ist UTF-8 mit LF-Zeilenenden: `git ls-files --eol web/openapi/schema.yml` zeigt `i/lf w/lf`.
11. Abräumen: `W down -v` und `B down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

**Nachtrag der Leitstelle (21.11.2026, aus der Prüfung von Auftrag 002):** Der Dienst `web-dev` liegt im Profil `dev`. Deshalb gilt abweichend vom Wortlaut dieses Auftrags: Bauen mit `build web-dev` oder `--profile dev build`; Abräumen mit `--profile dev down -v` (bei Playwright zusätzlich `--profile e2e`); den Dienst immer über `run --rm web-dev` ansprechen – ein bloßes `build`, `up` oder `down -v` ohne Profil tut nichts und meldet trotzdem Erfolg. `git check-ignore -q` nimmt nur einen Pfad je Aufruf. Zugelassene Lizenzen bei reinen Entwicklungs- und Build-Paketen zusätzlich: BlueOak-1.0.0, CC-BY-3.0, CC-BY-4.0, CC0-1.0 (E-25).

- **Voraussetzung:** Die Aufträge 002 und 010 sind zusammengeführt (und damit 005, 006 und 008).
- **Abhängigkeiten.** Mit der Freigabe der Auftragsliste genehmigt a7 den Client-Generator nach seiner Antwort auf Frage 1 in Auftrag 002: bei (a) oder (c) `@hey-api/openapi-ts`, bei (b) `openapi-typescript` und `openapi-fetch`. Mitgezogene Pakete sind mitgenehmigt, soweit die Lizenzprüfung sie durchlässt (Kriterium 9). Jede weitere direkte Abhängigkeit ist nicht genehmigt.
- **Stand der Recherche vom 21.11.2026 (belegt):** `@hey-api/openapi-ts` 0.99.0 (MIT, Node >=22.18, Peer typescript >=5.5.3) · openapi-typescript 7.13.0 (MIT, Peer typescript ^5.x) · openapi-fetch 0.17.0 (MIT).
- `@hey-api/openapi-ts` ist eine 0.x-Version: exakt festschreiben. Ungeprüft und an der Paketdoku zu prüfen: ob der erzeugte Client ein zusätzliches Laufzeitpaket braucht. Falls ja: nicht einfach installieren, sondern Frage in den Auftrag, Status „wartet auf a7“.
- Schema erzeugen: Unter Windows PowerShell 5.1 schreibt die Umleitung mit `>` UTF-16. Das Schema daher im Container in eine Datei im eingebundenen Ordner schreiben lassen oder Git Bash verwenden.
- Der erzeugte Code wird nicht von Hand geändert.
- Die Feldnamen kommen aus Auftrag 010 (`database.ok`, `database.server_version`, `worker.ok`, `worker.result`, `worker.duration_ms`, jeweils `error`).
- Auftrag 013 läuft gleichzeitig und ändert Backend, Dockerfile und Compose; dieser Auftrag bleibt unter `web/`. Die Prüfung „Client ist aktuell“ hängt Auftrag 014 in die CI ein.
- Dieser Auftrag startet den Dienst `api` nicht und braucht keinen Host-Port.
- Keine Telemetrie, keine externen Schriften oder Skripte (Leitplanke 6).
- Sprache: Code und Texte Englisch.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Im Kurzbericht Name, Version, Lizenz und Quelle des Generators nennen.
- Kein Push. Die Leitstelle committet nach `main` und pusht auf a7s Freigabe.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

Keine eigenen. Maßgeblich ist die Antwort auf Frage 1 in Auftrag 002 (TypeScript-Version und Client-Generator). Fehlt sie: Status „wartet auf a7“.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Akzeptanzkriterien sind erfüllt; die Läufe fanden am 21.11.2026 im Container statt. Keine offene Frage an a7.

### Was wurde gebaut?

- `web/openapi/schema.yml`: OpenAPI-Schema des Backends (drf-spectacular), im Container `backend-dev` direkt in den eingebundenen Ordner geschrieben (UTF-8, LF).
- `web/openapi-ts.config.ts`: Konfiguration des Generators (Eingabe `./openapi/schema.yml`, Ausgabe `./src/api/generated`, Plugins `@hey-api/client-fetch`, `@hey-api/typescript`, `@hey-api/sdk`). npm-Skript `api:generate` (`openapi-ts`).
- `web/src/api/generated/` (16 Dateien, eingecheckt, nicht von Hand geändert, von ESLint ausgenommen): Typen `Selftest`, `DatabaseCheck`, `WorkerCheck`, SDK-Funktion `selftestRetrieve` und der Fetch-Client. Der Client wird als Quelltext in die Ausgabe kopiert; **kein zusätzliches Laufzeitpaket** (geprüft an der Paketdoku und an den Importen des erzeugten Codes: nur relative Importe). URL relativ (`/api/v1/selftest/`), keine Serveradresse.
- `web/openapi/README.md`: wo Schema und Client liegen, wie man beide neu erzeugt, Liste der `data-testid` für Auftrag 014.
- `web/src/api/selftest.ts`: dünne Hülle um `selftestRetrieve` mit den Ergebnissen „answered“, „unreachable“ (Netzfehler oder Zeitlimit 15 s), „http-error“ (Status ≠ 2xx), „invalid-answer“ (2xx, aber kein JSON-Objekt mit beiden Prüfungen, z. B. eine HTML-Seite eines Proxys).
- `web/src/SelftestPage.tsx`: ersetzt den Platzhalter. Zeigt Datenbank (Zustand, `server_version`) und Worker (Zustand, `result`, Dauer), Ladezustand, Fehlertext der API je Teil, eigenen Fehlerzustand für „API antwortet nicht“ und HTTP-Fehler, Schaltfläche „Check again“ (während des Ladens gesperrt). `App.tsx` bindet sie ein.
- `web/src/texts.ts`: alle sichtbaren Texte (Englisch) an einer Stelle.
- `data-testid`: `database-version`, `worker-result`, `worker-duration`, `database-status`, `worker-status`, `database-error`, `worker-error`, `selftest-error`, `selftest-loading`.
- `web/tsconfig.json`: Konfigurationsdatei des Generators in `include` (sonst meldet die typbasierte ESLint-Prüfung sie). `web/eslint.config.js`: `src/api/generated` ausgenommen.

**Generator:** `@hey-api/openapi-ts` 0.99.0 (exakt), MIT, Quelle npm-Registry (`npm view`, Abruf 21.11.2026 im Container) und https://github.com/hey-api/hey-api. Nur Entwicklungsabhängigkeit. Mitgezogen: 42 Pakete, alle außerhalb des Produktionsbaums; Lizenzen MIT, außer argparse 2.0.1 (Python-2.0), dotenv 17.4.2 (BSD-2-Clause), color-support 1.1.3 und semver (ISC) – alle schon erlaubt. Die Regeldatei der Lizenzprüfung ist unverändert.

### Wie wurde getestet?

`W` = `docker compose -p twox-012 -f deploy/compose/compose.web.yaml`, `B` = `docker compose -p twox-012`; Docker Engine 29.9.3, Compose v5.7.0. Gebaut mit `B build backend-dev` und `W build web-dev`. Letzter Lauf auf dem committeten Stand.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version` (29.9.3) und `docker compose version` (v5.7.0), Exit-Code 0 |
| 1 | erfüllt | `spectacular --file /tmp/schema.yml` Exit-Code 0; `cmp` gegen das eingebundene `web/openapi/schema.yml`: identisch, SHA-256 beider Dateien `ecee3400…f33ce6` |
| 2 | erfüllt | „added 414 packages“, Exit-Code 0, kein `ERESOLVE` |
| 3 | erfüllt | `api:generate` Exit-Code 0 („./src/api/generated · 4 files“); danach `git diff --exit-code -- web/src/api` Exit-Code 0, `git status --short` leer |
| 4 | erfüllt | `npm run lint` und `npm run typecheck`: Exit-Code 0, keine Meldung |
| 5 | erfüllt | „Tests 7 passed (7)“, Exit-Code 0. Fälle: Überschrift · alles in Ordnung · Worker ausgefallen (Fehlertext der API sichtbar) · API nicht erreichbar · HTTP-Fehler 502 · Antwort kein JSON · erneutes Prüfen löst genau einen neuen Abruf aus |
| 6 | erfüllt | „built in 327ms“, Exit-Code 0 |
| 7 | erfüllt | 5 Treffer, alle in Doku-Kommentaren (`{@link …}`) unter `web/src/api/generated/`; außerhalb des erzeugten Codes kein Treffer (Exit-Code 1) |
| 8 | erfüllt | Treffer nur in `api/generated/types.gen.ts` (1), `SelftestPage.tsx` (1), `App.test.tsx` (2) |
| 9 | erfüllt | 391 Pakete, „License check passed.“, Exit-Code 0 |
| 10 | erfüllt | `i/lf w/lf attr/text=auto eol=lf web/openapi/schema.yml` |
| 11 | erfüllt | `W --profile dev down -v` und `B --profile dev down -v`: Exit-Code 0; danach keine Container, Volumes oder Netze von `twox-012`. Projekt `2x` der Leitstelle lief durchgehend weiter |

Zusätzlich geprüft:

- Erzeugung ohne Netz: `api:generate` in einem Container mit `--network none` Exit-Code 0. Die Eingabe muss mit `./` beginnen; ohne das liest der Generator `openapi/schema.yml` als Kurzform für die Hey-API-Registry (erster Versuch scheiterte daran mit Fehlermeldung, ohne Abruf).
- `dist`: `kein-nachladen-css`, `kein-nachladen-html`, `kein-cdn` (Prüfungen aus Auftrag 002). Im JS-Bündel nur Namensräume (w3.org) und `react.dev/errors/` aus React.
- Im echten Browser: gebaute Seite kurz mit `vite preview` (vorübergehender Port nur auf 127.0.0.1, danach gestoppt) geöffnet. Einzige Anfragen: `/static/`, die zwei Dateien unter `/static/assets/` und `GET /api/v1/selftest/` (relativ, gleicher Ursprung). Weil dort keine API läuft, zeigte die Seite sichtbar „The API answered with HTTP status 404.“
- In den Tests läuft unter jsdom Nodes `Request`, das relative Adressen ablehnt (ein Browser löst sie gegen die Seitenadresse auf). Die Tests ersetzen deshalb `Request` durch eine Unterklasse, die wie der Browser auflöst, und `fetch` durch eine Attrappe; geprüft wird auch der Pfad `/api/v1/selftest/`.

Nicht geprüft: die Seite gegen die laufende API im Browser (braucht die Auslieferung durch Django aus Auftrag 013 oder einen Proxy; Gutfall und Worker-Ausfall sind nur mit nachgestellter API getestet).

### So sieht man die Seite

Nach Auftrag 013 über den Django-Dienst unter dem dort festgelegten Pfad (gleicher Ursprung wie die API). Bis dahin nur über die Tests oder vorübergehend mit `W run --rm -p 127.0.0.1:<port>:4173 web-dev sh -c 'npm run build && npx vite preview --host 0.0.0.0'` und `http://127.0.0.1:<port>/static/` – dann ohne API, also mit sichtbarem Fehlerzustand.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-adf1f214a9016922b`
- Arbeitsverzeichnis: `.claude/worktrees/agent-adf1f214a9016922b` (relativ zum Projektordner)

### Abweichungen und Hinweise

- **Zusätzliche Dateien**, im Umfang nicht einzeln genannt: `web/openapi/README.md`, `web/src/api/selftest.ts`, `web/src/texts.ts`, `web/src/SelftestPage.tsx`; `web/tsconfig.json` um die Generator-Konfiguration erweitert.
- **Zusätzlicher Zustand „invalid-answer“** (2xx ohne passendes JSON) und Zeitlimit 15 s je Abruf (`AbortSignal.timeout`), damit ein hängender Server als „antwortet nicht“ erscheint. `AbortSignal.any` braucht aktuelle Browser (Chrome 116, Firefox 124, Safari 17.4).
- **Der erzeugte Client-Code wird ausgeliefert** (im `dist`-Bündel). Er stammt aus den Vorlagen von `@hey-api/openapi-ts` (MIT). Die Lizenzprüfung sieht das nicht, weil der Generator nur Entwicklungsabhängigkeit ist. Vorschlag fürs Entscheidungsprotokoll: in der Zeile des Generators vermerken; ob ein MIT-Hinweis in die ausgelieferten Lizenzhinweise gehört, entscheidet die Leitstelle mit Auftrag 013.
- **Mitgezogene Werkzeuge** des Generators enthalten u. a. `open`, `default-browser`, `giget`, `c12` (Öffnen eines Browsers, Laden entfernter Konfiguration). Beim Aufruf mit lokaler Datei werden sie nicht genutzt; die Erzeugung ohne Netz ist belegt.
- `server_version` wird ungekürzt angezeigt (z. B. `18.7 (Debian 18.7-1.pgdg12+2)`).
- Schema-Neuerzeugung: Der Dienst `backend-dev` bindet nur `backend/` ein; deshalb wird `web/openapi` mit `-v` zusätzlich eingebunden (Befehl im README). Für die CI (Auftrag 014) gehört die Prüfung „Schema und Client aktuell“ zusammen: beide Schritte, danach `git diff --exit-code -- web/openapi web/src/api`.
- Die lokalen Images `twox-012-backend-dev` und `twox-012-web-dev` liegen noch vor.
