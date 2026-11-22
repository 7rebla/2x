# Auftrag 062 – Seiten bei Bedarf nachladen

Meilenstein: M2 · Freigabestufe: B · Status: erledigt

Voraussetzung: 054 und 055 sind nach `main` zusammengeführt (beide ändern `web/src/routes.tsx`).

## Ziel

`npm run build` warnt, weil das Hauptbündel über 500 kB groß ist (551 kB vor 053, 561 kB danach; gzip etwa 170 kB). Die Warnung bestand schon vor M2. Nach diesem Auftrag lädt die Oberfläche große Seiten erst, wenn sie geöffnet werden, und der Bau läuft ohne Warnung.

## Umfang

- Seiten in `web/src/routes.tsx` mit `React.lazy()` und `Suspense` laden, mindestens die Landkarte (React Flow) und alle anderen Seiten außer Anmeldung und Startseite; ein gemeinsamer, ruhiger Ladezustand (Theme-Tokens aus 070, Animationen dezent nach E-52, respektiert `prefers-reduced-motion`).
- Fehler beim Nachladen eines Teils (z. B. nach einem neuen Bau, während die Seite offen ist) zeigen eine verständliche Meldung mit „Neu laden“ statt einer leeren Seite.
- Seit 054 lädt Rolldown den erzeugten API-Client als eigenes Stück (`react-query.gen-…js`, 218 kB) per `modulepreload` beim Start mit; die Startlast ist damit nicht gesunken (zusammen 565 kB). Ziel ist eine echte Verringerung der Startlast, nicht nur das Verschwinden der Warnung.
- Wackeliger Test `web/src/session.test.tsx` › „signs out … leads to /login“ (2 von 10 Läufen: `/login?next=%2Fselftest` statt `/login`; vermutlich Wettlauf zwischen `RequireSession` und `navigate("/login")` in `UserMenu.tsx`) beheben; `session.test.tsx` und `UserMenu.tsx` gehören dafür zu den betroffenen Bereichen.
- Bündelgrößen vor und nach dem Auftrag im Kurzbericht (Hauptbündel und größte Teile, jeweils roh und gzip).
- Tests: Vitest für Ladezustand und Fehler beim Nachladen; die bestehenden e2e-Tests laufen unverändert grün.

## Nicht-Ziele

- `chunkSizeWarningLimit` wird nicht angehoben.
- Keine neue Abhängigkeit, kein Austausch von Bibliotheken.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/routes.tsx`, `web/src/routes.test.tsx`
- neu: `web/src/components/PageLoading.tsx` und Test (Name frei wählbar)
- `web/src/locales/de/common.json`, `web/src/locales/en/common.json` (nur neue Texte)
- gegebenenfalls `web/vite.config.ts` (nur `build.rollupOptions.output.manualChunks`, falls nötig)

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Web-Job aus `.github/workflows/ci.yml` grün: npm ci, lint, typecheck, test, build, licenses; `npm run build` gibt **keine** Warnung zur Bündelgröße aus.
2. `api:generate` ohne Unterschied.
3. e2e wie in `ci.yml` (Testkonto anlegen, `TWOX_E2E_USERNAME`/`TWOX_E2E_PASSWORD` aus `.env.example`) grün.
4. `down -v` der eigenen Compose-Projekte endet mit Exit 0.

## Vorgaben und Hinweise

- Herkunft: Kurzbericht von 053 (Abweichung 1), Entscheidung der Leitstelle.
- Betrieb ohne Internet (Leitplanke 6): alle Teile kommen vom eigenen Server.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Läufe am 22.11.2026 im Container, Projekte `twox-062` und `twox-062-web`, Port 18062, Docker Engine 29.9.3, Compose v5.7.0. Alle Kriterien erfüllt. Keine neue Abhängigkeit, erzeugter Client unverändert, `vite.config.ts` unverändert (kein `manualChunks` nötig).

### Was wurde gebaut?

- **Seiten nachladen (`web/src/routes.tsx`):** Nur Anmeldung und Startseite (Struktur) liegen im Hauptbündel. Landkarte, Suche, Einlese-Übersicht, Gerät, Datei, Import, Änderungsprotokoll, Selbsttest und Einstellungen werden beim Öffnen geladen (Tabelle `pages`, je `lazyPage(...)`). `preloadPages()` lädt den Code aller dieser Seiten vorab (nur für Tests).
- **Neu `web/src/components/PageLoading.tsx`:**
  - `PageLoading`: ruhiger Ladezustand; hält Platz frei und zeigt erst nach 300 ms den gemeinsamen Ladezustand („Seite wird geladen…“, drehendes Icon und Schimmer nach Muster D, Theme-Tokens aus 070). Bei „Bewegung reduzieren“ steht beides still (E-52).
  - `PageLoadFailed`: Meldung „Diese Seite konnte nicht geladen werden.“ mit Erklärung (Anwendung aktualisiert oder Verbindung unterbrochen) und Knopf „Neu laden“ (`window.location.reload()`).
  - `lazyPage()`: `React.lazy` + `Suspense` + `PageLoadBoundary`. Ein Ladefehler des Teils wird zu `PageLoadError` und zeigt `PageLoadFailed`; jeder andere Fehler der Seite geht wie bisher an das Fehlerelement der Route (`RouteError`).
- **Texte:** `common.json` (de, en) nur neuer Block `pageLoad`.
- **Wackeliger Test (`session.test.tsx` › „signs out … leads to /login“):** Ursache gefunden. `forgetSession` meldet den Komponenten die Abmeldung über einen Timer (TanStack Query, `setTimeout(0)`); React Router rendert die neue Adresse in einer Transition. Kam der Timer vor dem Abschluss der Transition, sah `RequireSession` auf der alten Seite „abgemeldet“ und leitete auf `/login?next=%2Fselftest` um. Korrektur in `UserMenu.tsx`: `navigate("/login", { replace: true, flushSync: true })` – die Anmeldeseite steht damit fest, sobald der Router dort ist (der Router schließt ohne Loader nur über Microtasks ab, also vor dem Timer). Neuer Regressionstest erzwingt genau diese Reihenfolge (Timer feuert, sobald der Router `/login` erreicht): ohne die Korrektur schlägt er jedes Mal mit `/login?next=%2Fselftest` fehl, mit ihr besteht er.
- **Doku:** `web/src/pages/README.md`, neuer Abschnitt „Loading on demand“.

### Bündelgröße

Beides auf demselben Stand gemessen (Ausgangsstand `0787005` = `main` nach 055, Endstand dieses Zweigs), `npm run build` im Container, vorher `web/dist` und `web/playwright-report` gelöscht.

| Teil | vorher | nachher |
| --- | --- | --- |
| `index-….js` (Einstieg) | 348,46 kB (gzip 102,69) | 387,52 kB (gzip 119,28) |
| `react-query.gen-….js` (modulepreload) | 219,12 kB (gzip 70,38) | – |
| `rolldown-runtime-….js` (modulepreload) | 0,59 kB (gzip 0,36) | – |
| `TextMotion-….js` (modulepreload) | – | 67,51 kB (gzip 22,33) |
| `i18n-….js` (modulepreload) | – | 35,57 kB (gzip 11,77) |
| `Icon-….js` (modulepreload) | – | 28,41 kB (gzip 9,43) |
| **beim Start geladenes JS zusammen** | **568,17 kB (gzip 173,43)** | **519,01 kB (gzip 162,81)** |
| `index-….css` | 29,23 kB (gzip 6,82) | 29,26 kB (gzip 6,82) |
| `MapPage-….js` (nur `/map`) | 261,39 kB (gzip 89,58) | 261,36 kB (gzip 89,58) |
| `SearchPage` / `IngestPage` | 8,83 / 8,40 kB | 8,76 / 8,32 kB |
| neu nachgeladen | – | `DevicePage` 7,99, `ImportPage` 7,94, `UploadForm` 8,53, `AuditTrail` 6,20, `parts` 5,64, `SelftestPage` 5,62, `DocumentPage` 5,44, `SettingsPage` 4,24, `AuditPage` 2,16, `format` 0,92 kB |

Startlast: **−49,16 kB JS (−8,7 %), gzip −10,62 kB (−6,1 %)**. Keine Warnung zur Bündelgröße.

**Zum Stück `react-query.gen-…`:** Der Name täuscht. Ich habe die Teile mit einer vorübergehenden, nicht eingecheckten Vite-Konfiguration nach Modulen aufgeschlüsselt. Das Stück enthielt nicht vor allem den Client, sondern die gemeinsam genutzten Bibliotheken: react-router (≈ 215 kB vor dem Verkleinern), i18next (≈ 87 kB), Teile von TanStack Query, React, lucide und den erzeugten Client (≈ 31 kB). Rolldown benennt ein gemeinsames Stück nach einem seiner Module. Alles davon braucht schon die erste Seite (Router, Übersetzungen, Sitzung über `meRetrieve`, Icons der Navigation), das `modulepreload` war also richtig. Nach der Änderung verteilt Rolldown diese Bibliotheken anders (`TextMotion-…`, `i18n-…`, `Icon-…`, Rest im Einstieg). Die Einsparung kommt aus den Seiten selbst. Der erzeugte Client ist ein einziges Modul (`sdk.gen.ts`), deshalb lässt er sich ohne Änderung am erzeugten Code nicht weiter aufteilen.

### Wie wurde getestet?

`D` = `docker compose -p twox-062`, `W` = `docker compose -p twox-062-web -f deploy/compose/compose.web.yaml`; `.env` aus `.env.example` (ohne BOM) mit `TWOX_API_PORT=18062`. „2x“ und „twox-leit“ nicht berührt.

| Nr. | Ergebnis | Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version` (Engine 29.9.3) Exit 0, `docker compose version` v5.7.0 Exit 0 |
| 1 | erfüllt | Auf dem Endstand: `W --profile dev build web-dev`, `npm ci`, `lint`, `typecheck`, `test` (38 Dateien, 724 Tests), `build`, `licenses` („License check passed.“) je Exit 0. Keine Warnung zur Bündelgröße (siehe Hinweis 3) |
| 2 | erfüllt | `npm run api:generate` Exit 0; `git diff --exit-code -- web/openapi web/src/api` ohne Ausgabe, `git status --porcelain` dazu leer |
| 3 | erfüllt | `D --profile dev build migrate api worker web-dev`, `pull e2e`, `npm ci`, `up -d --wait …` je Exit 0; „Create test account“ wie in `ci.yml`, Exit 0; Playwright **53 passed**, Exit 0. Die ausgelieferte Seite verwies auf dieselben Teile wie der lokale Bau (`index-9tkR3Pid.js` und drei modulepreload) |
| 4 | erfüllt | `D --profile dev --profile e2e down -v` und `W --profile dev down -v` je Exit 0; danach kein Container und kein Volume mit `twox-062` |

**Vitest neu:** `components/PageLoading.test.tsx` (11 Fälle): Ladezustand erst nach 300 ms (künstliche Uhr), Text englisch und deutsch, Animationsklassen, ohne Schimmer bei „Bewegung reduzieren“; Meldung mit „Neu laden“ (en, de, Klick ruft das Neuladen); `lazyPage` zeigt den Ladezustand bis zur Ankunft, dann die Seite; Ladefehler → Meldung statt leerer Seite, ohne Dateinamen; anderer Fehler → `RouteError`; `preload`; Boundary fängt nur `PageLoadError`. `routes.test.tsx`: welche Routen nachgeladen werden (alle außer Anmeldung und Struktur), Ladefehler im Rahmen mit Navigation. `session.test.tsx`: Regressionstest zur Abmeldung (siehe oben).

**Wackeliger Test:** Vor der Korrektur auf diesem Rechner 30 volle Läufe ohne Fehler; der Fehler war hier nicht zufällig reproduzierbar, der Regressionstest reproduziert ihn aber zuverlässig. Nach der Korrektur **20 volle Vitest-Läufe, alle 724 Tests grün**. Laufzeit der Suite unverändert (etwa 6,6 s).

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a5608beb3672ac549`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a5608beb3672ac549` (relativ zum Projektordner)
- Commits: `Fix sign-out race between session guard and navigation`, `Add loading state and load-failure notice for lazy pages`, `Load every page except sign-in and structure on demand`, `Describe loading pages on demand in the pages README`, dazu dieser Kurzbericht. Nicht gepusht, nichts zusammengeführt.

### Abweichungen und Hinweise

1. **`web/src/test/renderApp.tsx` geändert (außerhalb der Liste):** eine Zeile `await preloadPages()` auf oberster Ebene. Sonst müssten etwa zehn Testdateien, die `renderApp` auf jetzt nachgeladenen Seiten aufrufen (App, Audit, Device, Document, Import, Settings, DeviceFiles, Layout …), einzeln vorladen. Ohne Vorladen droht ein neuer wackeliger Test (erste Umwandlung im Test über 1 s). Den `beforeAll` in `routes.test.tsx` habe ich dafür entfernt; die eigenen `beforeAll` in `SearchPage.test.tsx` und `IngestPage.test.tsx` blieben unberührt (Dateien von 064).
2. **`web/src/pages/README.md` ergänzt** (Doku). Die Adressentabelle dort habe ich nicht angefasst, um Konflikte mit 064 zu vermeiden; die Markierung „(loaded lazily)“ fehlt daher bei den neu nachgeladenen Seiten, der neue Abschnitt nennt sie. **Für 059:** `docs/ARCHITECTURE.md` Zeile „The JavaScript bundle is just below the 500 kB warning threshold of Vite.“ ist veraltet.
3. **Weitere Build-Warnung (nicht zur Größe):** `[MODULE_LEVEL_DIRECTIVE] … "use no memo" in react-compiler-runtime` erscheint vorher wie nachher (kommt mit React Flow). Nicht Gegenstand dieses Auftrags.
4. **Weiteres Sparpotenzial beim Start (außerhalb des Bereichs, nur als Hinweis):** Beide Sprachen werden beim Start geladen (`i18n-…`, 35,57 kB, gzip 11,77). Nur die aktive Sprache zu laden spart etwa die Hälfte, ändert aber `i18n.ts` und das Umschalten. Den Rest der Startlast brauchen React DOM, React Router, TanStack Query und i18next.
5. Für die Aufschlüsselung lagen kurz zwei Hilfsdateien in `web/` (`*.tmp.*`); sie wurden vor dem Lint entfernt und nie gestaged.
