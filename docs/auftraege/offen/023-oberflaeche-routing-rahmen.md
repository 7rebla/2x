# Auftrag 023 – Oberfläche: Routing, Rahmen und Datenabruf

Meilenstein: M1 · Freigabestufe: C · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
