# Auftrag 018 – Oberfläche zweisprachig (Deutsch und Englisch)

Meilenstein: M1 · Freigabestufe: C · Status: zur Prüfung

## Ziel

Die Oberfläche zeigt alle Texte auf Deutsch oder Englisch (E-07). Die Sprache folgt dem Browser und lässt sich umschalten. Alle späteren Seiten von M1 legen ihre Texte nur noch in ihre eigene Katalogdatei, ohne zentrale Dateien zu ändern.

## Umfang

- Übersetzung nach Frage 1, Empfehlung `i18next` und `react-i18next`.
- Kataloge als JSON je Sprache und Namensraum unter `web/src/locales/<de|en>/<ns>.json`.
  - Alle Namensräume von M1 legt dieser Auftrag gleich an: `common`, `nav`, `selftest`, `auth`, `assets`, `audit`, `import`, `files`.
  - Die noch nicht genutzten Kataloge bleiben leer (`{}`).
- Registrierung und Typen nur hier:
  - `web/src/i18n.ts` bindet alle acht Namensräume ein.
  - Eine Typerweiterung von i18next (z. B. `web/src/i18next.d.ts`) leitet die Schlüssel aus den englischen Katalogen ab. TypeScript meldet dann einen unbekannten Schlüssel als Fehler.
  - Spätere Aufträge füllen nur ihre JSON-Datei; `i18n.ts` und die Typdatei ändern sie nicht.
- Die Texte aus `web/src/texts.ts` wandern in `common.json` und `selftest.json`; `texts.ts` entfällt. Die deutschen Texte sind neu, die englischen bleiben unverändert.
- Sprachwahl:
  - Erstwahl aus `navigator.languages` (de oder en, sonst en).
  - Umschalter im Kopf der Seite; die Wahl wird im `localStorage` gemerkt, Lesen und Schreiben in try/catch.
  - `document.documentElement.lang` folgt der Sprache; `index.html` startet weiter mit `lang=\"en\"`.
- Datums- und Zahlformate über `Intl` mit der gewählten Sprache, hier mindestens die Dauer im Selbsttest.
- Laufzeitpakete im Image: In `backend/Dockerfile`, Stufe `web-build`, die erwartete Liste der Produktionsabhängigkeiten und die Schleife für `THIRD-PARTY-NOTICES.txt` um die neuen Pakete ergänzen.
- Lizenzregeln `web/scripts/license-rules.txt` nur ändern, falls nötig (die neuen Pakete sind MIT).
- Tests (Vitest):
  - Umschalten ändert Texte und `lang`.
  - Die Erstwahl folgt der Browsersprache.
  - Je Namensraum haben beide Sprachen dieselben Schlüssel, und alle acht Namensräume sind in beiden Sprachen vorhanden.
- Playwright:
  - `web/e2e/selftest.spec.ts` bleibt grün.
  - Neue Datei `web/e2e/i18n.spec.ts`: Nach dem Umschalten auf Deutsch steht die Kartenüberschrift auf Deutsch, und `html[lang]` ist `de`.

## Nicht-Ziele

- Routing und Rahmen der Anwendung (023).
- Übersetzung von Backend-Meldungen (034).
- Sprache am Benutzerkonto speichern.
- Kein Spracherkennungs-Zusatzpaket; die Erstwahl ist eigener Code.

## Betroffene Bereiche (Ordner, Dateien)

- `web/package.json`, `web/package-lock.json`, ggf. `web/scripts/license-rules.txt`
- `web/src/` (`main.tsx`, `App.tsx`, `SelftestPage.tsx`, `texts.ts` entfällt, neu `i18n.ts`, Typdatei, `locales/**`) und die zugehörigen Tests
- `web/e2e/selftest.spec.ts` (nur falls nötig), neu `web/e2e/i18n.spec.ts`
- `backend/Dockerfile` (nur Stufe `web-build`)

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `W` steht für `docker compose -p twox-018-web -f deploy/compose/compose.web.yaml`, `D` für `docker compose -p twox-018`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18018` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `W --profile dev build web-dev` und `W run --rm web-dev npm ci` enden mit Exit-Code 0.
2. `W run --rm web-dev npm run lint`, `… npm run typecheck`, `… npm run test`, `… npm run build` und `… npm run licenses` enden jeweils mit Exit-Code 0.
3. `W run --rm web-dev npm run api:generate`, danach zeigt `git diff --exit-code -- web/openapi web/src/api` keinen Unterschied.
4. `D --profile dev build migrate api worker web-dev` endet mit Exit-Code 0; die Prüfung der Laufzeitpakete in `web-build` läuft also durch.
5. Nach `D up -d --wait --wait-timeout 300 db valkey worker api` gibt `D exec api python -c \"import urllib.request as u; t=u.urlopen('http://localhost:8000/static/THIRD-PARTY-NOTICES.txt').read().decode(); print(chr(10)+'i18next 27.2.3 (MIT)' in t, chr(10)+'react-i18next 18.0.3 (MIT)' in t, chr(10)+'html-parse-stringify 4.0.1 (MIT)' in t)\"` `True True True` aus. Weichen die Versionen im Lock ab, mit den tatsächlichen Versionen.
6. Browser-Test:
   - `D --profile e2e pull e2e`
   - `D --profile dev run --rm web-dev npm ci`
   - `D --profile e2e run --rm e2e` meldet `2 passed`.
7. Abräumen: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); Antwort von a7 auf Frage 1 (neue Abhängigkeiten).

- Welle 1. Einziger Auftrag der Welle mit `web/package.json` und `backend/Dockerfile`.
- **Neue Abhängigkeiten nur nach Frage 1:**
  - `i18next` 27.2.3 (MIT, ohne Abhängigkeiten).
  - `react-i18next` 18.0.3 (MIT). Es zieht `html-parse-stringify` 4.0.1 (MIT, ohne Abhängigkeiten) nach.
  - Versionen exakt festlegen.
- Beide Pakete haben optionale Peer-Abhängigkeiten (`typescript`, bei react-i18next auch `@types/react`), die im Projekt als Entwicklungspakete installiert sind. Ungeprüft ist, ob `npm ls --omit=dev --all --parseable` sie als Laufzeitpakete meldet.
  - Im Kurzbericht die tatsächliche Ausgabe dieses Befehls nennen.
  - Die Liste im Dockerfile so festlegen, dass sie nur ausgelieferten Code enthält. Was abweicht, begründen.
- Im Kurzbericht außerdem die tatsächlich installierten Versionen und Lizenzen aus dem Lock nennen. Den Eintrag in `docs/DECISIONS.md` macht die Leitstelle.
- Die Kataloge werden mit dem Build gebündelt; nichts wird über das Netz nachgeladen (Betrieb ohne Internet).
- Hinweis aus 012: `texts.ts` sammelt heute alle Texte für genau diesen Schritt.
- Sobald die Anmeldung gilt (Auftrag 027), stellt 027 `i18n.spec.ts` auf den gemeinsamen Anmelde-Schritt um.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

1. **Übersetzungsmechanismus der Oberfläche (neue Abhängigkeit, Stufe C)**
   - (a) `i18next` und `react-i18next` (MIT, eine mitgezogene Abhängigkeit, kein Übersetzungsschritt im Build, JSON-Kataloge).
   - (b) Eigener kleiner Mechanismus ohne Abhängigkeit (typisierte Objekte, React-Kontext, `Intl`). Plural und Platzhalter müssen selbst gebaut werden.
   - (c) Lingui oder react-intl. Lingui braucht ein Makro-Plugin im Build, die Verträglichkeit mit `@vitejs/plugin-react` 6 ist ungeprüft; react-intl zieht drei Pakete.
   - Empfehlung: (a). Verbreiteter Standard mit wenigen Paketen.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Kriterien 0–7 sind erfüllt; alle Läufe am 21.11.2026 im Container (Docker Engine 29.9.3, Compose v5.7.0). Keine offene Frage an a7.

### Was wurde gebaut?

- `web/package.json`, `web/package-lock.json`: `i18next` 27.2.3 und `react-i18next` 18.0.3 als Laufzeitpakete, exakt festgelegt; mitgezogen `html-parse-stringify` 4.0.1. Laut Lock alle drei MIT, keine weiteren neuen Pakete.
- `web/src/locales/<de|en>/<ns>.json` für alle acht Namensräume (`common`, `nav`, `selftest`, `auth`, `assets`, `audit`, `import`, `files`); gefüllt sind `common` und `selftest`, die übrigen enthalten `{}`. Die englischen Texte sind wörtlich die aus `texts.ts`; `texts.ts` ist entfernt.
- `web/src/i18n.ts`: eigene i18next-Instanz mit allen acht Namensräumen, Kataloge statisch importiert (im Build gebündelt, kein Nachladen), synchrone Initialisierung. Erstwahl: gespeicherte Wahl (`localStorage`, Schlüssel `twox.language`), sonst die erste deutsche oder englische Sprache aus `navigator.languages` (Vergleich über das Hauptkürzel, `de-AT` → `de`), sonst Englisch. `localStorage` wird nur in try/catch gelesen und geschrieben. `document.documentElement.lang` folgt jedem Sprachwechsel; `index.html` startet unverändert mit `lang="en"`.
- `web/src/i18next.d.ts`: `CustomTypeOptions` mit den Schlüsseln aus den englischen Katalogen. Gegenprobe mit einer Wegwerfdatei: unbekannter Schlüssel, Tippfehler im Standard-Namensraum, Schlüssel im leeren Namensraum `assets` und unbekannter Namensraum ergeben je einen Fehler TS2345; ein gültiger Schlüssel nicht.
- `web/src/LanguageSwitch.tsx` (neu): Auswahlfeld „Language“/„Sprache“ im Kopf der Seite; `App.tsx` hat dafür einen `<header>`. `main.tsx` lädt `i18n.ts` vor dem ersten Rendern.
- `web/src/SelftestPage.tsx`: Texte über `useTranslation("selftest")`. Die Dauer läuft über das Zahlformat von i18next (`{{duration, number}} ms`, intern `Intl.NumberFormat` mit der gezeigten Sprache). Die Kartenüberschrift steht in einem eigenen `<span data-testid="…-heading">`.
- `web/src/locales/README.md`: Entwicklerdoku, wie spätere Seiten Texte anlegen.
- Tests: `web/src/i18n.test.ts` (neu, 25 Tests: Erstwahl aus Browsersprache, gespeicherte Wahl, ungültiger Wert, blockierter Speicher beim Lesen und Schreiben, Start der App in Deutsch mit `lang="de"`, alle 16 Katalogdateien vorhanden und keine weiteren, gleiche Schlüssel je Namensraum, nur nicht-leere Zeichenketten, alle Namensräume bei i18next registriert). `web/src/App.test.tsx`: drei neue Tests (Umschalten ändert Texte, Zahlformat, `lang` und Speicher und zurück; deutsche Fehlermeldung mit HTTP-Status; ungültiger Wert wird ignoriert); bestehende Tests vergleichen jetzt mit den englischen Texten im Wortlaut. `web/e2e/i18n.spec.ts` (neu): Start auf Englisch (`locale: "en-US"`), Umschalten auf Deutsch → Kartenüberschrift „Datenbank“, `html[lang]` = `de`, Wahl übersteht ein Neuladen, keine Konsolenfehler. `web/e2e/selftest.spec.ts` unverändert.
- `backend/Dockerfile`, nur Stufe `web-build`: erwartete Laufzeitliste und Hinweisschleife um die drei Pakete ergänzt (Begründung unten). `web/scripts/license-rules.txt` unverändert (nicht nötig).

### Wie wurde getestet?

`W` = `docker compose -p twox-018-web -f deploy/compose/compose.web.yaml`, `D` = `docker compose -p twox-018`; `.env` aus `.env.example` mit `TWOX_API_PORT=18018`.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version`, `docker compose version`: Exit 0 |
| 1 | erfüllt | `W --profile dev build web-dev`: Exit 0; `W run --rm web-dev npm ci`: „added 417 packages“, Exit 0 (danach `npm install` der zwei Pakete: „added 3 packages“) |
| 2 | erfüllt | `lint`, `typecheck`: Exit 0 ohne Meldung; `test`: „Test Files 4 passed (4), Tests 38 passed (38)“; `build`: `dist/assets/index-….js 292.58 kB`; `licenses`: „397 packages … License check passed.“ – je Exit 0 |
| 3 | erfüllt | `npm run api:generate`: Exit 0; `git diff --exit-code -- web/openapi web/src/api`: Exit 0, `git status --porcelain` dazu leer |
| 4 | erfüllt | `D --profile dev build migrate api worker web-dev`: Exit 0, die Prüfung der Laufzeitpakete in `web-build` lief durch |
| 5 | erfüllt | Ausgabe: `True True True` (Versionen wie im Auftrag) |
| 6 | erfüllt | `pull` und `npm ci`: Exit 0; `D --profile e2e run --rm e2e`: „2 passed (2.2s)“ (`i18n.spec.ts`, `selftest.spec.ts`) |
| 7 | erfüllt | `D --profile dev --profile e2e down -v` und `W --profile dev down -v`: Exit 0; danach keine Container, Volumes oder Netze mit `twox-018` (die gebauten Images bleiben liegen) |

Weil `backend/Dockerfile` geändert ist, zusätzlich die Backend-Prüfungen aus der CI mit `D` (nach `D --profile dev build backend-dev`): `ruff check` („All checks passed!“), `ruff format --check` („52 files already formatted“), `mypy` („no issues found in 52 source files“), `pytest` („110 passed, 4 deselected“), `pytest -m worker` („4 passed“), `makemigrations --check --dry-run` („No changes detected“), Lizenzprüfung Python („License check passed.“), OpenAPI-Schema neu erzeugt und `git diff --exit-code -- web/openapi` ohne Unterschied. Alle Exit 0.

**Ausgabe von `npm ls --omit=dev --all --parseable`** (nach der Installation, im Container `web-dev`):

```
/app
/app/node_modules/i18next
/app/node_modules/react-dom
/app/node_modules/react-i18next
/app/node_modules/react
/app/node_modules/typescript
/app/node_modules/scheduler
/app/node_modules/@types/react
/app/node_modules/html-parse-stringify
/app/node_modules/csstype
```

Die optionalen Peer-Abhängigkeiten werden also als Laufzeitpakete gemeldet: `typescript` (von i18next und react-i18next), `@types/react` (von react-i18next) und darüber `csstype`. Im Lock tragen `typescript` und `@types/react` jetzt `"devOptional": true`.

### Abweichungen und Hinweise

- **Laufzeitliste im Dockerfile:** Die erwartete Liste ist die tatsächliche Ausgabe oben, also mit `typescript`, `@types/react` und `csstype`. So schlägt der Build weiterhin bei jeder Änderung fehl. Hinweise bekommen nur Pakete mit ausgeliefertem Code (zusätzlich `i18next`, `react-i18next`, `html-parse-stringify`); die drei Typ- bzw. Werkzeugpakete gelangen nicht ins Bündel und stehen nicht in `THIRD-PARTY-NOTICES.txt`. Der Kommentar im Dockerfile begründet das.
- **Lizenzprüfung:** Aus demselben Grund führt `npm run licenses` `typescript` (Apache-2.0), `@types/react` (MIT) und `csstype` (MIT) jetzt als `production` statt `dev`. Alle drei Lizenzen sind allgemein zugelassen; die Regeln brauchten keine Änderung.
- **Englische Dauer mit Tausendertrennzeichen:** Weil die Dauer jetzt über `Intl` formatiert wird, zeigt Englisch `5,019 ms` statt bisher `5019 ms` (Deutsch `5.019 ms`); Werte unter 1000 sind unverändert. Der Katalogtext selbst (`… ms`) ist gleich geblieben. Der bestehende Test ist darauf angepasst.
- **Neue Prüfkennungen** `database-heading` und `worker-heading` für die Kartenüberschrift, damit der Browser-Test sie ohne den Statustext prüfen kann.
- **Doku:** Die Entwicklerdoku steht in `web/src/locales/README.md`. `docs/ARCHITECTURE.md` und `README.md` habe ich nicht geändert (außerhalb des genannten Bereichs, Welle 1 läuft parallel); ein Verweis dort wäre beim Zusammenführen sinnvoll.
- Der Eintrag in `docs/DECISIONS.md` (Abhängigkeitstabelle) bleibt der Leitstelle.

### Zweig und Arbeitsverzeichnis

Zweig `worktree-agent-ab4573b94de72dd7a`, Arbeitsverzeichnis `.claude/worktrees/agent-ab4573b94de72dd7a`. Nicht gepusht, nicht zusammengeführt.
