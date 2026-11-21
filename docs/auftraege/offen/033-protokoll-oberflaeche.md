# Auftrag 033 – Oberfläche: Protokoll anzeigen

Meilenstein: M1 · Freigabestufe: B · Status: offen

## Ziel

Die Oberfläche zeigt, wer was wann geändert hat: als Liste aller Änderungen und gefiltert für ein Objekt.

## Umfang

- Seite `/audit` (Platzhalter aus 023 ersetzen):
  - Tabelle mit Zeitpunkt (in der gewählten Sprache und der Ortszeit des Browsers), Benutzer, Aktion, Objektart (übersetzt), Objekt und geänderten Feldern mit alt → neu.
  - Seitenweise wie die API; Filter nach Objektart und Benutzer.
- Wiederverwendbare Komponente `AuditTrail` (Filter `object_type` und `object_id`), die die Geräte- und die Dateiseite einbinden können. Hier nur die Komponente und ihre Tests; eingebunden wird sie in 036.
- Sichtbarkeit: Die Navigation regelt seit 030 `navigation.ts`. Die Seite zeigt ein 403 der API verständlich an, ohne Umleitung (Regel aus 030).
- Texte in `audit.json` (seit 018 angelegt), Deutsch und Englisch.
- Vitest: Darstellung von Änderungen, Seitenwechsel, Filter, Anzeige bei 403.
- Playwright, neue Datei `web/e2e/audit.spec.ts`:
  - Anmelden über `fixtures.ts` als `manage`.
  - Über die API ein Gerät anlegen und ändern, mit Anfragen im Test mit Sitzung und `X-CSRFToken`. Namen mit `uniqueSuffix()`, IP aus `testIp()`.
  - Die Protokollseite zeigt beide Einträge mit Benutzernamen.

## Nicht-Ziele

- Export des Protokolls. Änderungen am Backend.
- Änderungen an `routes.tsx`, `navigation.ts`, `Layout.tsx`, `package.json`.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/pages/AuditPage.tsx`, neu `web/src/components/AuditTrail.tsx`, `web/src/locales/*/audit.json`, Tests
- neu: `web/e2e/audit.spec.ts`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-033`, `W` für `docker compose -p twox-033-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18033` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. Oberfläche:
   - `W --profile dev build web-dev`, `W run --rm web-dev npm ci`.
   - Dann `… npm run lint`, `… npm run typecheck`, `… npm run test`, `… npm run build` und `… npm run licenses`, je Exit-Code 0.
2. `W run --rm web-dev npm run api:generate`, danach zeigt `git diff --exit-code -- web/openapi web/src/api` keinen Unterschied.
3. Browser-Test wie in `ci.yml`, Job `e2e`:
   - `D --profile dev build migrate api worker web-dev`
   - `D --profile e2e pull e2e`
   - `D --profile dev run --rm web-dev npm ci`
   - `D up -d --wait --wait-timeout 300 db valkey worker api`
   - Schritt „Create test account“ wie in `ci.yml`
   - `D --profile e2e run --rm e2e` meldet alle Fälle bestanden, Exit-Code 0.
4. Kriterium 3 noch einmal ohne `down -v`: bleibt grün.
5. Abräumen: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); 028 und 030 sind nach `main` zusammengeführt.

- Welle 6, parallel zu 031 und 032. Nur die eigenen Dateien.
- **Keine neue Abhängigkeit.**
- Testdaten (CLAUDE.md, Leitplanke 9): keine erfundenen Anlagen, die echt wirken. Nur Namen nach dem Muster `e2e-<art>-<suffix>` und IP-Adressen aus 192.0.2.0/24, über `web/e2e/fixtures.ts`.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine eigenen; es gilt die Antwort zu Auftrag 028, Frage 3.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
