# Auftrag 062 – Seiten bei Bedarf nachladen

Meilenstein: M2 · Freigabestufe: B · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
