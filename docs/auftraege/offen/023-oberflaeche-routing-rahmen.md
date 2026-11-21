# Auftrag 023 – Oberfläche: Routing, Rahmen und Datenabruf

Meilenstein: M1 · Freigabestufe: C · Status: zur Prüfung

## Ziel

Die Oberfläche hat mehrere Seiten mit lesbaren Adressen, einen gemeinsamen Rahmen mit Navigation und einheitliche Lade- und Fehlerzustände. Spätere Aufträge ersetzen nur noch ihre eigene Seiten-Datei. Routen, Rahmen und Navigation ändern sie nicht.

## Umfang

- Routing nach Frage 1 (Empfehlung `react-router` 8, deklarativer oder Daten-Modus, kein Framework-Modus, kein Node-Server).
- Datenabruf nach Frage 2: Empfehlung `@tanstack/react-query` mit dem Plugin `@tanstack/react-query` von `@hey-api/openapi-ts`. Das Plugin kommt in `web/openapi-ts.config.ts`; danach den Client neu erzeugen.
- Seiten und Adressen, je eine Datei unter `web/src/pages/`, gesammelt in `web/src/routes.tsx`:
  - `/`: Struktur (Platzhalter für Auftrag 032).
  - `/devices/:deviceId`: Gerät (Platzhalter für 032).
  - `/documents/:documentId`: Datei (Platzhalter für 036).
  - `/import` (Platzhalter für 035), `/audit` (Platzhalter für 033), `/login` (Platzhalter für 030).
  - `/selftest`: die bestehende Selbsttest-Seite, bisher unter `/`.
- Navigation als Daten in `web/src/navigation.ts`: eine Liste der Einträge mit Pfad und Text-Schlüssel, ausgewertet von `Layout`. Auftrag 030 ergänzt dort die Rolle je Eintrag.
- Rahmen `web/src/components/Layout.tsx`: Kopf mit Namen, Navigation und Sprachumschalter aus 018. Ein Bereich für den angemeldeten Benutzer bleibt vorerst leer.
- Wiederverwendbare Komponenten: `Loading`, `ErrorMessage` (zeigt HTTP-Status und Text der API), `NotFound` (Seite für unbekannte Adressen der Oberfläche).
- Texte in `common.json` und `nav.json` (seit 018 angelegt), Deutsch und Englisch. Die Navigationstexte aller oben genannten Seiten kommen gleich mit.
- `backend/Dockerfile`, Stufe `web-build`: Liste der Laufzeitpakete und Hinweis-Schleife für `THIRD-PARTY-NOTICES.txt` ergänzen.
- Tests (Vitest): Die Navigation rendert die Seiten; eine unbekannte Adresse zeigt `NotFound`.
- Playwright:
  - `web/e2e/selftest.spec.ts` öffnet `/selftest` direkt. Damit ist auch die Auslieferung aus 016 geprüft. Die `data-testid`-Werte bleiben.
  - Neue Datei `web/e2e/navigation.spec.ts`: von `/` per Klick zu `/selftest`; eine unbekannte Adresse zeigt `NotFound`.

## Nicht-Ziele

- Anmeldung, Rollenanzeige, Sichtbarkeit je Rolle (030). Inhalte der Fachseiten (032, 033, 035, 036).
- Formular-Bibliothek, Komponentenbibliothek.

## Betroffene Bereiche (Ordner, Dateien)

- `web/package.json`, `web/package-lock.json`, `web/openapi-ts.config.ts`, `web/src/api/generated/**`
- `web/src/` (`main.tsx`, `App.tsx`, neu `routes.tsx`, `navigation.ts`, `pages/`, `components/`, `locales/*/common.json`, `locales/*/nav.json`) und Tests
- `web/e2e/selftest.spec.ts`, neu `web/e2e/navigation.spec.ts`
- `backend/Dockerfile` (nur Stufe `web-build`)

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `W` steht für `docker compose -p twox-023-web -f deploy/compose/compose.web.yaml`, `D` für `docker compose -p twox-023`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18023` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `W --profile dev build web-dev` und `W run --rm web-dev npm ci` enden mit Exit-Code 0.
2. `W run --rm web-dev npm run lint`, `… npm run typecheck`, `… npm run test`, `… npm run build` und `… npm run licenses` enden jeweils mit Exit-Code 0.
3. `W run --rm web-dev npm run api:generate`, danach zeigt `git diff --exit-code -- web/openapi web/src/api` keinen Unterschied.
4. `D --profile dev build migrate api worker web-dev` endet mit Exit-Code 0. Nach `D up -d --wait --wait-timeout 300 db valkey worker api` gibt `D exec api python -c \"import urllib.request as u; print(u.urlopen('http://localhost:8000/selftest').status)\"` `200` aus.
5. `THIRD-PARTY-NOTICES.txt` enthält die Kopfzeilen der neuen Laufzeitpakete mit den Versionen aus dem Lock. Prüfung wie in Auftrag 018, Kriterium 5; die Befehle stehen im Kurzbericht.
6. Browser-Test:
   - `D --profile e2e pull e2e`
   - `D --profile dev run --rm web-dev npm ci`
   - `D --profile e2e run --rm e2e` meldet alle Fälle bestanden, darunter `navigation.spec.ts`, Exit-Code 0.
7. Abräumen: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); 016 und 018 sind nach `main` zusammengeführt; Antworten von a7 auf Frage 1 und 2.

- Welle 3, parallel zu 024 (Datenmodell Dateien) und 025 (Standard-Rechte). Beide ändern weder Schema noch Client.
- Dieser Auftrag erzeugt den Client wegen des neuen Plugins vollständig neu. Deshalb läuft gleichzeitig kein Auftrag, der Schema oder Client ändert.
- Einziger Auftrag der Welle mit `web/package.json` und `backend/Dockerfile`.
- **Neue Abhängigkeiten (nur nach Frage 1 und 2):**
  - `react-router` 8.5.2: MIT; Peer react >=19.2.7; engines node >=22.22.0; an der npm-Registry geprüft. Zieht `cookie-es` ^3.1.1 (3.1.1: MIT, ohne Abhängigkeiten) und `@remix-run/route-pattern` ^0.22.1 (0.22.1: MIT, ohne Abhängigkeiten; es gibt keine neuere 0.22.x).
  - `@tanstack/react-query` 5.108.2: MIT; Peer react ^18 || ^19. Zieht `@tanstack/query-core` 5.108.2 (MIT, ohne Abhängigkeiten).
  - Optionale Peers (`@types/react`, `@types/react-dom`) wie in Auftrag 018 behandeln: Ausgabe von `npm ls --omit=dev --all --parseable` im Kurzbericht.
  - Im Kurzbericht die tatsächlich im Lock stehenden Versionen und Lizenzen nennen.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

1. **Routing der Oberfläche (neue Abhängigkeit)**
   - (a) `react-router` 8 (zwei kleine MIT-Abhängigkeiten).
   - (b) `@tanstack/react-router` (mehr mitgezogene Pakete, darunter `isbot` unter der Unlicense).
   - (c) Eigenes kleines Routing über die History-API, ohne Abhängigkeit.
   - Empfehlung: (a). Verbreitet und wenige Pakete; (c) wird mit Parametern, Links und „Zurück“ schnell eigener Code.
2. **Datenabruf der Oberfläche (neue Abhängigkeit)**
   - (a) `@tanstack/react-query` plus Plugin des vorhandenen Client-Generators (typisierte Abfragen, Zwischenspeicher, Neuladen nach Änderungen).
   - (b) Nur der generierte Client mit eigenen Hooks, wie heute auf der Selbsttest-Seite.
   - Empfehlung: (a). Viele Listen und Formulare in M1, weniger eigener Code für Laden, Fehler und Aktualisieren.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Kriterien 0–7 sind erfüllt; alle Läufe am 21.11.2026 im Container (Docker Engine 29.9.3, Compose v5.7.0). Keine offene Frage an a7.

### Was wurde gebaut?

- **Pakete** (`web/package.json`, `web/package-lock.json`, exakt festgelegt): `react-router` 8.5.2 und `@tanstack/react-query` 5.108.2. Mitgezogen laut Lock: `cookie-es` 3.1.1, `@remix-run/route-pattern` 0.22.1, `@tanstack/query-core` 5.108.2. Alle fünf MIT (Lock und `npm run licenses`), keine weiteren neuen Pakete. Im Lock wechselt `@types/react-dom` von `"dev": true` auf `"devOptional": true` (optionaler Peer von react-router).
- **Client:** `web/openapi-ts.config.ts` mit dem Plugin `@tanstack/react-query`; neu erzeugt `web/src/api/generated/@tanstack/react-query.gen.ts` (Query-Optionen und -Schlüssel je Endpunkt). Die übrigen erzeugten Dateien sind unverändert.
- **Routing** (`web/src/routes.tsx`): react-router im Daten-Modus (`createBrowserRouter`, `RouterProvider` aus `react-router/dom`), kein Framework-Modus, kein Node-Server. Adressen `/`, `/devices/:deviceId`, `/documents/:documentId`, `/import`, `/audit`, `/login`, `/selftest`, alles andere `NotFound`. Je Seite eine Datei unter `web/src/pages/` (Platzhalter mit Überschrift aus `nav.json`; Gerät und Datei zeigen den Adressparameter). Die Selbsttest-Seite ist nach `web/src/pages/SelftestPage.tsx` verschoben (mit ihrem Test), Inhalt und `data-testid` unverändert.
- **Navigation** `web/src/navigation.ts`: Liste mit Pfad, Text-Schlüssel (`nav.json`, typgeprüft) und `end`. Einträge: Struktur, Import, Änderungsprotokoll, Selbsttest. Seiten mit Parameter und `/login` stehen nicht in der Navigation (ihre Texte schon).
- **Rahmen** `web/src/components/Layout.tsx`: Kopf mit Namen (`<h1>`, Link auf `/`), Navigation (`<nav aria-label>`, `NavLink` mit `aria-current`), Sprachumschalter aus 018 und leerem Bereich `data-testid="user-area"` für 030; darunter `<main>` mit der Seite.
- **Komponenten:** `Loading`, `ErrorMessage` (HTTP-Status und Text der API, sonst „keine Antwort“, „unlesbare Antwort“ oder allgemeiner Fehler; `role="alert"`), `NotFound` (mit Link zur Struktur), dazu `PagePlaceholder` und `RouteError` (Renderfehler einer Seite erscheinen als `ErrorMessage` im Rahmen).
- **Datenabruf:** `web/src/App.tsx` legt `QueryClientProvider` um den Router. `web/src/api/errors.ts` macht über einen Fehler-Interceptor des erzeugten Clients aus jedem Fehlschlag ein `ApiError` (`kind` http/network/invalid-answer, `status`, `detail` aus DRF `detail` oder einer Klartext-Antwort, gekürzt auf 500 Zeichen; HTML-Seiten werden nicht gezeigt; Abbrüche bleiben unverändert). `web/src/api/queryClient.ts`: nur fehlende Antworten werden wiederholt (zweimal), HTTP-Fehler erscheinen sofort. `main.tsx` richtet beides ein.
- **Texte** in `common.json` und `nav.json`, Deutsch und Englisch (Laden, Fehler, Platzhalter, Seite nicht gefunden, alle Seitennamen, Name der Navigation).
- **Tests (Vitest):** neu `web/src/routes.test.tsx` (23 Fälle: Rahmen, jeder Navigationseintrag per Klick zur Seite mit `aria-current`, alle Adressen, Parameter, unbekannte Adressen zeigen `NotFound` im Rahmen, Rückweg, Deutsch, Renderfehler) und `web/src/api/errors.test.tsx` (12 Fälle: Umwandlung, Wiederholregel, erzeugte Query-Optionen mit `Loading` und `ErrorMessage` gegen einen gestubbten `fetch`). `web/src/App.test.tsx` rendert jetzt die ganze App unter `/selftest` (Hilfe `web/src/test/renderApp.tsx`).
- **Playwright:** `web/e2e/selftest.spec.ts` öffnet `/selftest` direkt; neu `web/e2e/navigation.spec.ts` (von `/` per Klick zu `/selftest` und zurück, direkter Aufruf von `/devices/plc-1`, unbekannte Adresse zeigt `NotFound` mit Rückweg; jeweils keine Konsolenfehler).
- **`backend/Dockerfile`, Stufe `web-build`:** erwartete Laufzeitliste und Hinweisschleife um die fünf Pakete ergänzt, Kommentar angepasst.
- **Doku:** neu `web/src/pages/README.md` (Adressen, Rahmen, Navigation, Datenabruf mit Beispiel); `web/openapi/README.md` um die Query-Optionen ergänzt.

### Wie wurde getestet?

`W` = `docker compose -p twox-023-web -f deploy/compose/compose.web.yaml`, `D` = `docker compose -p twox-023`; `.env` aus `.env.example` mit `TWOX_API_PORT=18023`.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version` (Server 29.9.3), `docker compose version` (v5.7.0): Exit 0 |
| 1 | erfüllt | `W --profile dev build web-dev`: Exit 0; `W run --rm web-dev npm ci`: Exit 0 (danach `npm install --save-exact` der zwei Pakete: „added 5 packages“) |
| 2 | erfüllt | `lint`, `typecheck`: Exit 0 ohne Meldung; `test`: „Test Files 6 passed (6), Tests 73 passed (73)“; `build`: `dist/assets/index-….js 417.64 kB` (gzip 131.16 kB); `licenses`: „402 packages … License check passed.“ – je Exit 0 |
| 3 | erfüllt | `npm run api:generate`: Exit 0; `git diff --exit-code -- web/openapi web/src/api`: Exit 0, `git status --porcelain --untracked-files=all` leer |
| 4 | erfüllt | `D --profile dev build migrate api worker web-dev`: Exit 0 (Prüfung der Laufzeitliste lief durch); `D up -d --wait …`: alle gesund; `…urlopen('http://localhost:8000/selftest').status` → `200` |
| 5 | erfüllt | siehe Befehl unten: `True True True True True` |
| 6 | erfüllt | `pull`, `npm ci`: Exit 0; `D --profile e2e run --rm e2e`: „5 passed (3.3s)“ (`i18n.spec.ts`, drei Fälle in `navigation.spec.ts`, `selftest.spec.ts`), Exit 0 |
| 7 | erfüllt | `D --profile dev --profile e2e down -v` und `W --profile dev down -v`: Exit 0; danach keine Container, Volumes oder Netze mit `twox-023` |

Prüfung zu Kriterium 5 (nach `D up …`):

```
D exec api python -c "import urllib.request as u; t=u.urlopen('http://localhost:8000/static/THIRD-PARTY-NOTICES.txt').read().decode(); print(chr(10)+'react-router 8.5.2 (MIT)' in t, chr(10)+'cookie-es 3.1.1 (MIT)' in t, chr(10)+'@remix-run/route-pattern 0.22.1 (MIT)' in t, chr(10)+'@tanstack/react-query 5.108.2 (MIT)' in t, chr(10)+'@tanstack/query-core 5.108.2 (MIT)' in t)"
```

Weil `backend/Dockerfile` geändert ist, zusätzlich die Backend-Prüfungen aus der CI mit `D` (nach `D --profile dev build backend-dev`): `ruff check` („All checks passed!“), `ruff format --check` („69 files already formatted“), `mypy` („no issues found in 69 source files“), `pytest` („184 passed, 4 deselected“), `pytest -m worker` („4 passed“), `makemigrations --check --dry-run` („No changes detected“), Lizenzprüfung Python („License check passed.“), OpenAPI-Schema neu erzeugt und `git diff --exit-code -- web/openapi web/src/api` ohne Unterschied. Alle Exit 0.

**Ausgabe von `npm ls --omit=dev --all --parseable`** (im Container `web-dev`):

```
/app
/app/node_modules/@tanstack/react-query
/app/node_modules/i18next
/app/node_modules/react-dom
/app/node_modules/react-i18next
/app/node_modules/react-router
/app/node_modules/react
/app/node_modules/@tanstack/query-core
/app/node_modules/@types/react
/app/node_modules/typescript
/app/node_modules/scheduler
/app/node_modules/html-parse-stringify
/app/node_modules/@remix-run/route-pattern
/app/node_modules/@types/react-dom
/app/node_modules/cookie-es
/app/node_modules/csstype
```

Neu als optionaler Peer erscheint `@types/react-dom` (von react-router); `@types/react` ist zusätzlich optionaler Peer von react-router und @tanstack/react-query. Die Laufzeitliste im Dockerfile ist genau diese Ausgabe; Hinweise bekommen nur Pakete mit ausgeliefertem Code. `npm run licenses` führt `@types/react-dom` (MIT) deshalb jetzt als `production`; die Regeln brauchten keine Änderung.

### Zweig und Arbeitsverzeichnis

Zweig `worktree-agent-aeff8cc079c3890b1`, Arbeitsverzeichnis `.claude/worktrees/agent-aeff8cc079c3890b1`. Nicht gepusht, nicht zusammengeführt.

### Abweichungen und Hinweise

- **`web/e2e/i18n.spec.ts` geändert** (nicht im Bereich genannt): öffnet jetzt `/selftest` statt `/`, weil die Selbsttest-Seite nicht mehr unter `/` liegt. Sonst unverändert.
- **`web/openapi/README.md` geändert** (nicht im Bereich genannt): Die Aussage „der erzeugte Code hat keine Laufzeitabhängigkeit“ stimmt mit dem Plugin nicht mehr; drei Zeilen angepasst.
- **Selbsttest-Seite** bleibt bei ihrem eigenen Ladecode aus M0 (`web/src/api/selftest.ts`), nur verschoben. Die erzeugten Query-Optionen sind in `errors.test.tsx` mit `Loading` und `ErrorMessage` geprüft; die erste echte Nutzung kommt mit den Fachseiten.
- **Bündel** wächst von 292,6 kB auf 417,6 kB (gzip 131,2 kB), vor allem durch react-router.
- **`docs/ARCHITECTURE.md`** nennt noch `web/src/SelftestPage.tsx` und die Seite unter `/`; außerhalb des Bereichs, Nachzug in Auftrag 038.
- Der Eintrag in `docs/DECISIONS.md` (Abhängigkeitstabelle) bleibt der Leitstelle.
