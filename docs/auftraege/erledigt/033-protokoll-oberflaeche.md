# Auftrag 033 – Oberfläche: Protokoll anzeigen

Meilenstein: M1 · Freigabestufe: B · Status: zur Prüfung

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

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

Keine eigenen; es gilt die Antwort zu Auftrag 028, Frage 3.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Kriterien 0–5 erfüllt; alle Läufe am 21.11.2026 im Container (Docker Engine 29.9.3, Compose v5.7.0). Keine offene Frage an a7. Keine neue Abhängigkeit, Schema und Client unverändert.

### Was wurde gebaut?

- `web/src/components/AuditTrail.tsx` (neu): Tabelle über `auditLogListOptions` aus dem erzeugten TanStack-Query-Client.
  - Spalten Zeitpunkt, Benutzer, Aktion, Objektart, Objekt, Änderungen.
  - Zeitpunkt über `Intl.DateTimeFormat` mit der gezeigten Sprache und der Zeitzone des Browsers (`<time datetime>` mit ISO-Wert). Zeiten in `changes` (UTC ohne Zone, Hinweis aus 028) werden ebenso umgerechnet, der Rohwert steht im `title`.
  - Aktion und Objektart übersetzt (alle drei Aktionen, alle sieben protokollierten Modelle aus E-43); Unbekanntes erscheint unverändert als Text.
  - Objekt: `object_repr` und „ID n“. Fehlender Benutzer: „System (kein angemeldeter Benutzer)“.
  - Änderungen je Feld „feld: alt → neu“, leere Werte als „(leer)“; Rollenwechsel (`m2m`) als „groups: hinzugefügt/entfernt manage“; unbekannte Formen als JSON-Text.
  - Seitenweise wie die API (50 je Seite, „Vorherige/Nächste Seite“, „Seite x von y“, Gesamtzahl). Während die nächste Seite lädt, bleibt die gezeigte stehen (`keepPreviousData`, `aria-busy`, Knöpfe gesperrt).
  - Props `objectType`, `objectId`, `actor`, `label`; ein geänderter Filter beginnt wieder auf Seite 1. Einbindung in Geräte- und Dateiseite: `<AuditTrail objectType="assets.device" objectId={id} />` (036).
  - Fehler über `ErrorMessage`: 403 erscheint als „keine Berechtigung“, ohne Umleitung.
  - Alle Werte aus dem Protokoll werden von React als Text gerendert, nie als HTML und nie über die Interpolation von i18next.
- `web/src/pages/AuditPage.tsx`: Platzhalter ersetzt. Überschrift, Kurztext, Filterformular (Objektart als Auswahl, Benutzer als Textfeld mit genauem Namen, höchstens 150 Zeichen, getrimmt), „Filter anwenden“ und „Filter zurücksetzen“; darunter `AuditTrail`. Gefragt wird erst beim Anwenden.
- `web/src/locales/{de,en}/audit.json`: alle Texte der Seite und der Komponente.
- Tests (Vitest):
  - neu `web/src/components/AuditTrail.test.tsx` (14 Fälle): Darstellung aller Spalten; alle Aktionen und Objektarten übersetzt; Anlegen, Löschen, Rollenwechsel, fehlender Benutzer, Zeiten in `changes`; Unbekanntes als Text; HTML in Benutzername, Objektname, Feldname und Werten erscheint als Text, kein Element entsteht; Deutsch; leere Liste; Seitenwechsel vor und zurück über drei Seiten (Abfrageparameter `page`); gezeigte Seite bleibt während des Ladens; Filter `object_type`/`object_id` und `actor` in der Anfrage; Filterwechsel zurück auf Seite 1; 403 als „keine Berechtigung“; andere HTTP-Fehler mit Status.
  - neu `web/src/pages/AuditPage.test.tsx` (6 Fälle, ganze App über `renderApp`): Überschrift und Einträge; Filter nach Objektart und Benutzer mit Zurücksetzen; Auswahlliste der Objektarten; 403 der API bei gültiger Sitzung: Meldung, `me` erneut gefragt, Adresse bleibt `/audit`, keine Umleitung; Leser fragt die API gar nicht; Deutsch.
- Playwright, neu `web/e2e/audit.spec.ts`: angemeldet über `fixtures.ts` als `manage`; legt über die API Standort, Bereich, Anlage und Gerät an (Namen mit `testName()`, IP aus `testIp()`) und ändert Name und IP des Geräts, jeweils per `fetch` in der Seite mit Sitzung und `X-CSRFToken`. Auf `/audit` wird nach Objektart „Gerät“ und dem Testkonto gefiltert; geprüft werden genau zwei Zeilen dieses Geräts (neueste zuerst): „Changed“ mit `name` und `ip_address` alt → neu, „Created“ mit `name` und `key`, beide mit dem Benutzernamen; keine Konsolenfehler.

### Wie wurde getestet?

`D` = `docker compose -p twox-033`, `W` = `docker compose -p twox-033-web -f deploy/compose/compose.web.yaml`; `.env` aus `.env.example` mit `TWOX_API_PORT=18033`. Die Umgebungen „2x“ und „twox-leit“ wurden nicht berührt.

| Nr. | Ergebnis | Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version` (Server 29.9.3), `docker compose version` (v5.7.0): Exit 0 |
| 1 | erfüllt | `W --profile dev build web-dev`, `npm ci`: Exit 0; `lint`, `typecheck`: Exit 0 ohne Meldung; `test`: „Test Files 11 passed (11), Tests 192 passed (192)“; `build`: `index-….js 449.21 kB` (gzip 140.47 kB); `licenses`: „402 packages … License check passed.“ – je Exit 0 |
| 2 | erfüllt | `api:generate` Exit 0; `git diff --exit-code -- web/openapi web/src/api` Exit 0, `git status --porcelain --untracked-files=all` leer |
| 3 | erfüllt | Bau `migrate api worker web-dev`, `pull e2e`, `npm ci`, `up -d --wait` je Exit 0; „Create test account“ wie in `ci.yml` (Kennwort nur als Variablenname): „Created account …“; `D --profile e2e run --rm e2e`: „13 passed“, Exit 0 |
| 4 | erfüllt | dieselbe Folge ohne `down -v`: „Updated account …“, „13 passed“, Exit 0 |
| 5 | erfüllt | `D --profile dev --profile e2e down -v` und `W --profile dev down -v`: Exit 0; danach kein Container, Volume oder Netz mit `twox-033` |

### Zweig und Arbeitsverzeichnis

Zweig `worktree-agent-adaccf6ee05c7fcdd`, Arbeitsverzeichnis `.claude/worktrees/agent-adaccf6ee05c7fcdd`. Nicht gepusht, nicht zusammengeführt.

### Abweichungen und Hinweise

1. **`web/src/routes.test.tsx` geändert** (nicht im Bereich genannt): Die Zeile `["/audit", "Change log"]` in der Tabelle „addresses“ ist entfernt, weil der Test dort den Platzhalter erwartet. Die Seite selbst prüfen jetzt `AuditPage.test.tsx` und die übrigen Fälle in `routes.test.tsx` (Klick in der Navigation, Rückweg über den Namen). 032 ändert dieselbe Tabelle vermutlich auch (Zeilen `/` und `/devices/plc-1`); beim Zusammenführen kann dort ein kleiner Konflikt entstehen.
2. **Leere Feldpaare ausgeblendet:** Beim Anlegen protokolliert auditlog jedes Feld, auch leer gelassene (`[null, ""]`). Paare, die auf beiden Seiten leer sind (`null` oder `""`), zeigt die Tabelle nicht; bleibt nichts übrig, steht dort „Keine Feldwerte“. Ein Wechsel von leer auf Wert und umgekehrt erscheint immer.
3. **Feldnamen unübersetzt** (z. B. `ip_address`, `groups`): Sie kommen so aus dem Protokoll und sind für alle Modelle gleich gut lesbar. Eine Übersetzung je Modell wäre ein eigener Auftrag.
4. **Filter nicht in der Adresse:** Filter und Seite stehen im Zustand der Seite; ein Neuladen beginnt ohne Filter auf Seite 1. Der Auftrag verlangt das nicht.
5. **Benutzerfilter als Textfeld** mit genauem Benutzernamen, weil es keinen Endpunkt mit einer Liste der Benutzer gibt.
6. **Doku:** `web/src/pages/README.md` nennt `AuditPage.tsx` bereits mit 033; die Einbindung der Komponente ist im Kopfkommentar von `AuditTrail.tsx` beschrieben. README und ARCHITECTURE nicht geändert (038).
7. Geheimnissuche (`gitleaks`) nicht ausgeführt; keine Werte außer den öffentlichen Testmustern hinzugefügt.
