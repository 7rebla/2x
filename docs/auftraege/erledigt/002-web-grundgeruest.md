# Auftrag 002 – Oberfläche als Grundgerüst

Meilenstein: M0 · Freigabestufe: C · Status: erledigt (Frage 3)

## Ziel

Unter `web/` steht ein baubares, getestetes Grundgerüst der Oberfläche (React, TypeScript, Vite, Tailwind CSS). Lint, Typprüfung, Tests und Build laufen im Container.

## Umfang

- `web/package.json` und `web/package-lock.json` (npm), `tsconfig`, `vite.config.ts`, ESLint-Konfiguration.
- Tailwind CSS 4 über das Vite-Plugin (`@tailwindcss/vite`, `@import "tailwindcss"` in der CSS-Datei).
- Eine Startseite als Platzhalter (`src/main.tsx`, `src/App.tsx`): Überschrift „2x“ und ein kurzer Hinweistext. Kein Zugriff auf die API.
- Ein Vitest-Test, der die Startseite rendert und die Überschrift findet.
- npm-Skripte: `lint`, `typecheck` (`tsc --noEmit`), `test` (`vitest run`), `build`.
- `web/Dockerfile` (Stufe `dev` auf dem Node-Image nach Frage 2; darf als root laufen, nur Entwicklung und CI) und `deploy/compose/compose.web.yaml` mit dem Dienst `web-dev` (Profil `dev`): bindet `web/` ein, `node_modules` liegt in einem eigenen Volume (nicht im Windows-Ordner). Kein Host-Port. Pfade relativ zu `deploy/compose`.
- Vite-Einstellung `base: "/static/"`, damit Django die gebaute Oberfläche später ausliefern kann (Auftrag 013).

## Nicht-Ziele

- API-Client und Testseite (Auftrag 012), Auslieferung durch Django (Auftrag 013), Playwright (Auftrag 014).
- Routing, Übersetzungen (Deutsch/Englisch), Komponentenbibliothek, Zustandsverwaltung – jeweils neue Abhängigkeiten, nicht in M0.
- Ein Node-Server im Betrieb (Abschnitt 5.2: gibt es nicht).
- Regeln der Lizenzprüfung (Auftrag 006).

## Betroffene Bereiche (Ordner, Dateien)

- `web/**` (neu)
- `deploy/compose/compose.web.yaml` (neu)

## Akzeptanzkriterien (prüfbar)

Alle Befehle im Wurzelverzeichnis des Arbeitsverzeichnisses. `W` steht für `docker compose -p twox-002 -f deploy/compose/compose.web.yaml`.

0. Vorab: `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren oder ausführen; Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. `W build` endet mit Exit-Code 0; `W config` endet mit Exit-Code 0.
2. `W run --rm web-dev node --version` zeigt die nach Frage 2 gewählte Hauptversion.
3. `W run --rm web-dev npm ci` endet mit Exit-Code 0 und ohne `ERESOLVE`-Fehler.
4. `W run --rm web-dev npm run lint` endet mit Exit-Code 0 und 0 Meldungen.
5. `W run --rm web-dev npm run typecheck` endet mit Exit-Code 0.
6. `W run --rm web-dev npm run test` endet mit Exit-Code 0; mindestens 1 Test, 0 fehlgeschlagen.
7. `W run --rm web-dev npm run build` endet mit Exit-Code 0 und erzeugt `web/dist/index.html`; die eingebundenen Skripte und Stile beginnen mit `/static/`.
8. Kein Nachladen aus dem Internet (Leitplanke 6). Geprüft wird tatsächliches Nachladen; Lizenzkommentare mit einer Adresse zählen nicht:
   - `W run --rm web-dev sh -c "grep -rnoE '(url\(|@import)[^;)]*https?://' dist --include=*.css || echo kein-nachladen-css"` gibt `kein-nachladen-css` aus.
   - `W run --rm web-dev sh -c "grep -rnoE '(src|href)=.https?://' dist --include=*.html || echo kein-nachladen-html"` gibt `kein-nachladen-html` aus.
   - `W run --rm web-dev sh -c "grep -rlE 'fonts\.googleapis|fonts\.gstatic|unpkg\.com|jsdelivr|cdnjs' dist || echo kein-cdn"` gibt `kein-cdn` aus.
9. `git check-ignore -q web/dist web/node_modules` endet mit Exit-Code 0, und `git status --short` zeigt beide Ordner nicht. Fehlt der Eintrag in der `.gitignore`: nicht selbst ändern, im Kurzbericht melden.
10. `W run --rm web-dev npx license-checker-rseidelsohn --summary` läuft durch (Zusammenfassung in den Kurzbericht; einzeln alles, was nicht MIT, Apache-2.0 oder BSD ist).
11. Abräumen: `W down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

- **Voraussetzung:** keine. Das Grundgerüst der Leitstelle ist vorhanden.
- **Abhängigkeiten.** Mit der Freigabe der Auftragsliste genehmigt a7 diese direkten Abhängigkeiten:
  - Laufzeit: react, react-dom.
  - Entwicklung: typescript, vite, @vitejs/plugin-react, tailwindcss, @tailwindcss/vite, vitest, @testing-library/react, @testing-library/dom (Pflicht-Peer von @testing-library/react), jsdom, @types/react, @types/react-dom, eslint, typescript-eslint, eslint-plugin-react-hooks, license-checker-rseidelsohn (wird in Auftrag 006 gebraucht).
  - Image: `node:24-slim` (oder nach Frage 2).
  - Mitgezogene Pakete sind mitgenehmigt, soweit ihre Lizenz MIT, Apache-2.0 oder BSD ist. Jede weitere direkte Abhängigkeit ist nicht genehmigt.
  - Ergibt die Prüfung für eine genannte oder mitgezogene Abhängigkeit eine andere Lizenz oder ist sie nicht feststellbar: im Kurzbericht einzeln aufführen. Bekannte Fälle, über die a7 in Auftrag 006 entscheidet: ISC, 0BSD und ähnliche freizügige Lizenzen sowie lightningcss (MPL-2.0, Build-Werkzeug, kommt über Tailwind und Vite). Jeder weitere Fall (GPL, AGPL, Nutzungsbeschränkung, unbekannt): nicht einbauen, Frage in den Auftrag, Status „wartet auf a7“.
- **Versionen (Stand 21.11.2026, an der npm-Registry belegt):** react / react-dom 19.3.1 · TypeScript 6.0.3 (siehe Frage 1) · vite 8.3.8 · @vitejs/plugin-react 6.3.0 · tailwindcss / @tailwindcss/vite 4.3.5 · vitest 5.1.1 · eslint 10.15.0 · typescript-eslint 8.73.0 (Peer: typescript >=4.8.4 <6.1.0) · license-checker-rseidelsohn 5.0.1 (verlangt Node >=24, npm >=11). Laut Prüfbefund vom 21.11.2026 ebenfalls an der Registry belegt: @testing-library/react 16.3.3 · @testing-library/dom 10.4.2 · jsdom 31.0.1 (Node ^22.22.2, ^24.15.0 oder >=26) · eslint-plugin-react-hooks 7.1.1 (Peer eslint bis ^10). Die direkten Pakete sind MIT, außer TypeScript (Apache-2.0) und license-checker-rseidelsohn (BSD-3-Clause).
- **Ungeprüft und hier an der npm-Registry zu prüfen:** Version und Lizenz von @types/react und @types/react-dom; ob typescript-eslint 8.73.0 ESLint 10 als Peer zulässt; Lizenz des Node-Images. Passt etwas nicht zusammen: nicht mit `--force` oder `--legacy-peer-deps` installieren, sondern Frage in den Auftrag.
- **TypeScript 7 nicht verwenden**, solange Frage 1 nicht anders entschieden ist: npm `latest` ist 7.0.2, aber typescript-eslint und openapi-typescript schließen 7 per Peer-Abhängigkeit aus. TypeScript mit exakter Version eintragen.
- Versionen exakt festschreiben (keine `^`-Bereiche bei 0.x-Paketen); `package-lock.json` wird eingecheckt.
- Ungeprüft: geänderte tsconfig-Standards in TypeScript 6 (`types: []`, `baseUrl` entfernt) – an der TypeScript-Doku prüfen. Vite 8 baut mit Rolldown statt Rollup – keine Rollup-Plugins voraussetzen.
- Der Dienst `web-dev` darf nicht von Diensten anderer Compose-Dateien abhängen; `compose.web.yaml` muss allein gültig bleiben.
- Keine Telemetrie, keine externen Schriften oder Skripte.
- Sprache: Code, Bezeichner und Commit-Nachrichten Englisch.
- `.gitignore`, `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Im Kurzbericht je Abhängigkeit Name, festgeschriebene Version, Lizenz und Quelle nennen.
- Kein Push. Die Leitstelle committet nach `main` und pusht auf a7s Freigabe.
- Die Fragen unten beantwortet a7 mit der Freigabe der Liste; die Leitstelle trägt die Antworten vor dem Start ein. Fehlt eine Antwort: nicht raten, Status „wartet auf a7“.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

1. **TypeScript-Version und Werkzeuge.** TypeScript 7 (native Neufassung) wird von typescript-eslint (`<6.1.0`) und openapi-typescript (`^5.x`) nicht zugelassen.
   - (a) TypeScript 6.0.3, ESLint mit typescript-eslint, API-Client später mit `@hey-api/openapi-ts`.
   - (b) TypeScript 5.9.3, ESLint mit typescript-eslint, API-Client später mit openapi-typescript und openapi-fetch.
   - (c) TypeScript 7.0.2 mit Biome statt ESLint und `@hey-api/openapi-ts` – die Kombination ist nicht getestet (ungeprüft).
   - Empfehlung: (a). Diese Antwort legt zugleich den Client-Generator für Auftrag 012 fest.
2. **Node-Version** (nur für Build und Tests, nicht im Betrieb).
   - (a) Node 24 (Maintenance LTS, Ende April 2028).
   - (b) Node 26 (Active LTS seit 28.10.2026, Ende April 2029).
   - Empfehlung: (a) Node 24 als vorsichtige Wahl; alle Werkzeuge laufen auf beiden, ein Wechsel ist eine Zeile.

3. **Neu vom Auftragsbearbeiter (21.11.2026): weitere Lizenzen bei mitgezogenen Entwicklungswerkzeugen.** Die Lizenzprüfung zeigt neben den bekannten Fällen (ISC, 0BSD, lightningcss MPL-2.0) Lizenzen, die der Auftrag nicht nennt. Keine davon ist GPL/AGPL, keine hat eine Nutzungsbeschränkung, keine ist unbekannt. Alle betreffen nur Entwicklungswerkzeuge; im gebauten `dist` stecken nur react, react-dom und scheduler (MIT).
   - BlueOak-1.0.0 (freizügig, 14 Pakete: glob, minimatch, minipass, lru-cache, tar, graceful-fs, path-scurry, chownr, isexe, yallist u. a.) – fast alle über license-checker-rseidelsohn (npm-Bibliotheken), graceful-fs auch über @tailwindcss/node.
   - CC-BY-4.0: caniuse-lite (Datenbestand; über eslint-plugin-react-hooks → @babel/core → browserslist).
   - CC-BY-3.0, CC0-1.0, (MIT AND CC-BY-3.0): spdx-exceptions, spdx-license-ids, spdx-ranges (Lizenzlisten als Daten; über license-checker-rseidelsohn).
   - Optionen: (a) als gleichwertig freizügig bzw. als reine Datenbestände in Entwicklungswerkzeugen zulassen und im Entscheidungsprotokoll benennen; (b) license-checker-rseidelsohn und/oder eslint-plugin-react-hooks wieder entfernen (dann fehlt das Werkzeug für Auftrag 006 bzw. die Hooks-Regeln); (c) Entscheidung in Auftrag 006 treffen und den Zweig bis dahin stehen lassen.
   - Empfehlung: (a). Die Pakete kommen zwingend mit den von a7 genehmigten direkten Abhängigkeiten, werden unverändert genutzt und nicht ausgeliefert.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: erledigt** (Frage 3, Lizenzen mitgezogener Entwicklungswerkzeuge). Technisch ist der Auftrag fertig; alle Prüfungen liefen am 21.11.2026 im Container.

### Was wurde gebaut?

- `web/`: `package.json` und `package-lock.json` (npm, alle Versionen exakt, `.npmrc` mit `save-exact`), `tsconfig.json` (strict), `vite.config.ts` (`base: "/static/"`, React- und Tailwind-Plugin, Vitest mit jsdom), `eslint.config.js` (typescript-eslint `strictTypeChecked`, React-Hooks-Regeln), `index.html`, `src/main.tsx`, `src/App.tsx` (Überschrift „2x“ und Hinweistext, kein API-Zugriff), `src/index.css` (`@import "tailwindcss"`), `src/App.test.tsx` (2 Tests).
- `web/Dockerfile` (Stufe `dev`, `node:24-slim`) und `web/.dockerignore`.
- `deploy/compose/compose.web.yaml`: Dienst `web-dev` (Profil `dev`), bindet `web/` ein, `node_modules` im Volume `web_node_modules`, kein Host-Port, allein gültig.

### Wie wurde getestet?

`W` = `docker compose -p twox-002 -f deploy/compose/compose.web.yaml`, Docker Engine 29.9.3, Compose v5.7.0.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version` und `docker compose version`: Exit 0 |
| 1 | erfüllt, mit Hinweis | `W build`: Exit 0, meldet aber „No services to build“, weil der Dienst im Profil `dev` liegt. Tatsächlich gebaut mit `W build web-dev` (Exit 0, „Image twox-002-web-dev Built“). `W config`: Exit 0 |
| 2 | erfüllt | `v24.22.3` (npm 11.19.1) |
| 3 | erfüllt | `npm ci`: „added 371 packages“, Exit 0, kein `ERESOLVE` |
| 4 | erfüllt | `eslint . --max-warnings 0`: keine Meldung, Exit 0. Gegenprobe: `--print-config` enthält die Regeln der Typprüfung und der React-Hooks |
| 5 | erfüllt | `tsc --noEmit`: Exit 0 |
| 6 | erfüllt | Vitest 5.1.1: „Test Files 1 passed (1), Tests 2 passed (2)“, Exit 0 |
| 7 | erfüllt | `dist/index.html` erzeugt; eingebunden: `/static/assets/index-….js` und `/static/assets/index-….css` |
| 8 | erfüllt | `kein-nachladen-css`, `kein-nachladen-html`, `kein-cdn` |
| 9 | teilweise | Der Befehl aus dem Auftrag scheitert wörtlich: `git check-ignore -q web/dist web/node_modules` → „fatal: --quiet is only valid with a single pathname“, Exit 128. Einzeln je Ordner: Exit 0; ohne `-q` mit beiden: Exit 0. `git status --short` zeigt beide Ordner nicht. Die `.gitignore` ist in Ordnung |
| 10 | erfüllt | läuft durch, Zusammenfassung unten |
| 11 | erfüllt, mit Hinweis | `W down -v`: Exit 0, räumt aber nichts ab („No resource found to remove“), das Volume bleibt stehen (Profil). Tatsächlich abgeräumt mit `W --profile dev down -v` (Volume und Netz entfernt, geprüft mit `docker volume ls`). Das lokale Image `twox-002-web-dev` bleibt liegen |

Lizenz-Zusammenfassung (`license-checker-rseidelsohn --summary`, 348 Pakete einschließlich Entwicklungswerkzeuge): MIT 220 · ISC 65 · Apache-2.0 27 · BlueOak-1.0.0 14 · BSD-2-Clause 10 · BSD-3-Clause 4 · MPL-2.0 2 · CC-BY-4.0 1 · CC-BY-3.0 1 · CC0-1.0 1 · (MIT AND CC-BY-3.0) 1 · 0BSD 1 · UNLICENSED 1. Nur Laufzeit (`--production`): MIT 3 und UNLICENSED 1.

Alles außerhalb MIT, Apache-2.0, BSD:

- **ISC (65):** vor allem npm-Bibliotheken unter license-checker-rseidelsohn (`@npmcli/*`, pacote, cacache, semver, nopt, which, ssri u. a.), dazu picocolors, electron-to-chromium, flatted, glob-parent, saxes, signal-exit, lru-cache 5, yallist 3/4.
- **BlueOak-1.0.0 (14):** @isaacs/nonrecursive-glob-match, chownr, common-ancestor-path, glob 13, graceful-fs, isexe 4, lru-cache 11, minimatch 10 und 11, minipass 7, minipass-flush, path-scurry, tar, yallist 5.
- **MPL-2.0 (2):** lightningcss 1.33.0 und lightningcss-linux-x64-gnu 1.33.0 (über Vite und Tailwind; in E-23 benannt).
- **0BSD (1):** tslib 2.8.1.
- **CC-BY-4.0 (1):** caniuse-lite. **CC-BY-3.0 (1):** spdx-exceptions. **CC0-1.0 (1):** spdx-license-ids. **(MIT AND CC-BY-3.0) (1):** spdx-ranges.
- **UNLICENSED (1):** das eigene Paket `twox-web`. Das Werkzeug meldet jedes Paket mit `"private": true` so; in `package.json` steht `Apache-2.0`. Kein Fremdpaket ohne Lizenz.

### Abhängigkeiten fürs Entscheidungsprotokoll

Quelle für Version, Lizenz und Peer-Angaben: npm-Registry (`npm view`, Abruf 21.11.2026 im Container).

| Name | Version | Lizenz | Art |
| --- | --- | --- | --- |
| react | 19.3.1 | MIT | Laufzeit |
| react-dom | 19.3.1 | MIT | Laufzeit |
| typescript | 6.0.3 | Apache-2.0 | Entwicklung |
| vite | 8.3.8 | MIT | Entwicklung |
| @vitejs/plugin-react | 6.3.0 | MIT | Entwicklung |
| tailwindcss | 4.3.5 | MIT | Entwicklung |
| @tailwindcss/vite | 4.3.5 | MIT | Entwicklung |
| vitest | 5.1.1 | MIT | Entwicklung |
| @testing-library/react | 16.3.3 | MIT | Entwicklung |
| @testing-library/dom | 10.4.2 | MIT | Entwicklung |
| jsdom | 31.0.1 | MIT | Entwicklung |
| @types/react | 19.3.0 | MIT | Entwicklung |
| @types/react-dom | 19.3.0 | MIT | Entwicklung |
| eslint | 10.15.0 | MIT | Entwicklung |
| typescript-eslint | 8.73.0 | MIT | Entwicklung |
| eslint-plugin-react-hooks | 7.1.1 | MIT | Entwicklung |
| license-checker-rseidelsohn | 5.0.1 | BSD-3-Clause | Entwicklung |
| Image `node:24-slim` | Node v24.22.3, npm 11.19.1 | Node.js: MIT; das Image enthält ein Debian-Grundsystem mit eigenen Lizenzen (auch GPL) | nur Build und Tests |

Die im Auftrag als ungeprüft genannten Punkte: @types/react und @types/react-dom sind 19.3.0, MIT. typescript-eslint 8.73.0 lässt ESLint 10 zu (Peer `^8.57.0 || ^9.0.0 || ^10.0.0`) und TypeScript `>=4.8.4 <6.1.0`. Die Lizenz des Node-Images wurde in dieser Sitzung nicht an einer Quelle nachgeschlagen; die Angabe oben ist ungeprüft.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a1667f7e4fc0d0e28`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a1667f7e4fc0d0e28`

### Abweichungen und Hinweise

- **Profil `dev` und die Befehle `W build` / `W down -v`:** Beide enden mit Exit 0, wirken aber ohne `--profile dev` bzw. ohne Dienstnamen nicht (siehe Nr. 1 und 11). Für CI und Aufräumen: `W build web-dev` und `W --profile dev down -v`. Vorschlag: Akzeptanzkriterien oder spätere Aufträge (011) entsprechend fassen.
- **Kriterium 9** ist im Wortlaut nicht ausführbar (`-q` nur mit einem Pfad); inhaltlich erfüllt.
- **Image nur per Tag festgelegt** (`node:24-slim`), nicht per Digest; die Nebenversion kann sich bei einem Neuaufbau ändern.
- **Kein `@eslint/js`:** Die üblichen ESLint-Grundregeln (`js.configs.recommended`) brauchen dieses Paket als direkte Abhängigkeit; es ist nicht genehmigt. Verwendet werden die Regeln von typescript-eslint und eslint-plugin-react-hooks. `eslint.config.js` selbst wird ohne Regeln geprüft.
- **Kein `@types/node`** (nicht genehmigt): `vite.config.ts` verwendet keine Node-Schnittstellen; `skipLibCheck` ist an.
- **Zusätzliche Dateien in `web/`**, im Umfang nicht einzeln genannt: `.npmrc`, `.dockerignore`, `index.html`, `src/index.css`. Zusätzliches npm-Skript `dev` (Vite-Entwicklungsserver; ohne Host-Port von außen nicht erreichbar).
- **Hinweistext auf Englisch** („This page is a placeholder …“), weil Übersetzungen ein Nicht-Ziel sind und Code auf Englisch steht.
- Nicht geprüft: Anzeige im Browser (kein Host-Port, Auslieferung kommt mit Auftrag 013).
