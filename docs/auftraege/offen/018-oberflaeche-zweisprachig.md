# Auftrag 018 – Oberfläche zweisprachig (Deutsch und Englisch)

Meilenstein: M1 · Freigabestufe: C · Status: offen

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

1. **Übersetzungsmechanismus der Oberfläche (neue Abhängigkeit, Stufe C)**
   - (a) `i18next` und `react-i18next` (MIT, eine mitgezogene Abhängigkeit, kein Übersetzungsschritt im Build, JSON-Kataloge).
   - (b) Eigener kleiner Mechanismus ohne Abhängigkeit (typisierte Objekte, React-Kontext, `Intl`). Plural und Platzhalter müssen selbst gebaut werden.
   - (c) Lingui oder react-intl. Lingui braucht ein Makro-Plugin im Build, die Verträglichkeit mit `@vitejs/plugin-react` 6 ist ungeprüft; react-intl zieht drei Pakete.
   - Empfehlung: (a). Verbreiteter Standard mit wenigen Paketen.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
