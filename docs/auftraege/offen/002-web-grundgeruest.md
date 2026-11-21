# Auftrag 002 – Oberfläche als Grundgerüst

Meilenstein: M0 · Freigabestufe: C · Status: offen

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

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
