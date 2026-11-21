# Auftrag 032 – Oberfläche: Struktur und Geräte anzeigen, anlegen, bearbeiten

Meilenstein: M1 · Freigabestufe: B · Status: zur Prüfung

## Ziel

In der Oberfläche sind Standorte, Bereiche, Anlagen und Geräte sichtbar. „Verwalten“ kann sie anlegen und bearbeiten, „Lesen“ nur ansehen.

## Umfang

- Seite Struktur (`/`, Platzhalter aus 023 ersetzen):
  - Baum oder verschachtelte Liste Standort > Bereich > Anlage > Gerät, mit Anzahl der Geräte.
  - Suche nach Name, Kennung oder IP-Adresse; bei der Größe genügt eine Suche im Browser.
- Geräteseite `/devices/:deviceId` (Platzhalter aus 023 ersetzen):
  - Alle Felder; die Kette als Brotkrumen.
  - Ein Bereich „Dateien“ als Platzhalter für 036, als eigene Komponente, die 036 ersetzt.
  - Lange Freitexte (Notizen, Adressherkunft) werden vollständig und mit Zeilenumbruch angezeigt.
- Formulare für Anlegen und Bearbeiten aller vier Ebenen:
  - React-19-Formulare, keine Formular-Bibliothek.
  - Feldfehler aus der 400-Antwort der API am Feld anzeigen.
  - Nach dem Speichern die Daten neu laden.
- Schaltflächen zum Anlegen und Bearbeiten nur für die Rolle `manage` (`useRole()` aus 030); die API prüft ohnehin.
- Texte in `assets.json` (seit 018 angelegt), Deutsch und Englisch, mit übersetzten Feldbezeichnungen.
- Vitest: Darstellung, Sichtbarkeit je Rolle, Feldfehler.
- Playwright, neue Datei `web/e2e/assets.spec.ts`:
  - Anmelden über `fixtures.ts` (027) als `manage`.
  - Standort, Bereich, Anlage und Gerät anlegen; Namen und Kennungen mit `uniqueSuffix()`, IP-Adresse aus `testIp()`.
  - Das Gerät bearbeiten (z. B. den Softwarestand); die Änderung ist sichtbar.
  - Eine ungültige IP zeigt den Feldfehler.

## Nicht-Ziele

- Löschen. Import (035). Dateien (036). Protokoll (033).
- Änderungen am Backend, an `routes.tsx`, `navigation.ts`, `Layout.tsx`, `package.json`.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/pages/` (Struktur- und Geräteseite, Formulare)
- `web/src/components/` (nur neue Komponenten)
- `web/src/locales/*/assets.json` und Tests
- neu: `web/e2e/assets.spec.ts`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-032`, `W` für `docker compose -p twox-032-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18032` setzen.

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

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); 026 und 030 sind nach `main` zusammengeführt.

- Welle 6, parallel zu 031 (Backend) und 033 (Protokollseite). Nur die eigenen Dateien. Ist eine Änderung an gemeinsamen Dateien unvermeidlich, vorher Rückfrage an die Leitstelle.
- **Keine neue Abhängigkeit.**
- Testdaten (CLAUDE.md, Leitplanke 9): keine erfundenen Anlagen, die echt wirken. Nur Namen nach dem Muster `e2e-<art>-<suffix>` und IP-Adressen aus 192.0.2.0/24, über die Hilfen in `web/e2e/fixtures.ts`. Kein Test verlässt sich auf Daten anderer Spezifikationen.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Kriterien 0–5 erfüllt; alle Läufe am 21.11.2026 im Container (Docker Engine 29.9.3, Compose v5.7.0). Keine neue Abhängigkeit, keine offene Frage an a7.

### Was wurde gebaut?

- **Strukturseite** `web/src/pages/StructurePage.tsx` (`/`): lädt die vier Listen über die erzeugten Query-Optionen und zeigt den Baum Standort > Bereich > Anlage > Gerät (verschachtelte Listen) mit der Geräteanzahl auf jeder Ebene (Plural über i18next). Geräte verlinken auf `/devices/<id>` und zeigen Kennung und IP. Suche im Browser nach Name, Kennung oder IP-Adresse (ohne weitere Anfrage); passt ein Standort, Bereich oder eine Anlage, erscheint alles darunter. Hinweise für „noch kein Standort“ und „nichts gefunden“.
- **Baum und Suche** `web/src/pages/structure/tree.ts` (rein, getestet): Sortierung natürlich nach Name bzw. Kennung; Einträge ohne Eltern fallen weg; die Anzahl bleibt die der ganzen Struktur, auch bei aktiver Suche.
- **Geräteseite** `web/src/pages/DevicePage.tsx` (`/devices/:deviceId`): Brotkrumen (Struktur › Standort › Bereich › Anlage (Kennung) › Gerät, `aria-current`), Überschrift mit dem Gerätenamen, alle Felder mit übersetzten Bezeichnungen (Standort, Bereich, Anlage, Kennung, Name, Hersteller, Modell, Softwarestand, IP-Adresse, Herkunft der Adresse, Protokolle, Notizen, Angelegt, Zuletzt geändert). Freitexte mit `whitespace-pre-wrap` und `break-words`, also vollständig und mit Zeilenumbrüchen; leere Felder „–“. Eine Adresse, die keine Geräte-ID sein kann (z. B. `plc-1`), und eine 404 der API zeigen `NotFound`; andere Fehler `ErrorMessage` unter der Überschrift „Gerät“.
- **Dateien-Platzhalter** `web/src/components/DeviceFiles.tsx` (`DeviceFiles({ deviceId })`), eigene Komponente für 036.
- **Formulare** `web/src/pages/structure/forms.tsx`: `SiteForm`, `AreaForm`, `PlantForm`, `DeviceForm` zum Anlegen und Bearbeiten, React-19-Formularaktionen mit `useActionState`, keine Formular-Bibliothek, Schreiben über die erzeugten Mutation-Optionen (`useMutation`). Eltern als Auswahlfeld (beim Bearbeiten verschiebbar, beim Anlegen vorbelegt). Leere IP-Adresse wird als `null` gesendet. Formulare öffnen sich unter der zugehörigen Zeile (neuer Standort oben); Schaltflächen mit eindeutigem Namen („New area in …“, „Edit device …“) nur für `manage` (`useRole()`).
- **Feldfehler** `web/src/pages/structure/save.ts`: Der Schreibaufruf bekommt über die Option `fetch` des erzeugten Clients eine eigene fetch-Hülle, die eine Kopie einer 400-Antwort behält; daraus werden DRFs Meldungen je Feld gelesen und am Feld gezeigt (`aria-invalid`, `aria-describedby`). Schlüssel ohne Feld (`non_field_errors`, `detail`) erscheinen über den Feldern; die Eingaben bleiben erhalten. Andere Fehler (403, keine Antwort) zeigt `ErrorMessage`. Nach dem Speichern werden alle Abfragen außer der Sitzung neu geladen (`reloadAfterSave`), dann schließt das Formular.
- **Texte** `web/src/locales/{de,en}/assets.json`, gleiche Schlüssel.
- **Doku** `web/src/pages/README.md`, Abschnitt „Structure and devices“.
- **Vitest:** `structure/tree.test.ts` (10), `structure/save.test.ts` (12), `StructurePage.test.tsx` (16: Baum und Anzahl, Deutsch, leer, API-Fehler, Suche nach Name/Kennung/IP ohne Anfrage, Schaltflächen je Rolle, Anlegen Standort/Bereich/Anlage mit Neuladen, Bearbeiten Bereich, Feldfehler an IP und Kennung mit erhaltener Eingabe, Fehler ohne Feld, 403, Abbrechen, deutsche Feldbezeichnungen), `DevicePage.test.tsx` (24: ID-Prüfung, alle Felder und Brotkrumen, lange Freitexte, leere Felder, Deutsch, Rolle, Bearbeiten mit PUT und Neuladen, leere IP als `null`, ungültige IP am Feld, 404, ungültige ID ohne Anfrage, 500). Testhilfe `structure/testData.ts` (gefälschte Struktur-API, Namen `Test …`, IPs aus 192.0.2.0/24).
- **Playwright** `web/e2e/assets.spec.ts` (2 Fälle): als `manage` (fixtures.ts) Standort, Bereich, Anlage und Gerät über die Formulare anlegen (Namen und Kennungen mit `testName()`, IP mit `testIp()`), Anzahl im Baum, Suche nach Kennung und IP, Geräteseite mit Brotkrumen und Feldern, Softwarestand bearbeiten, Änderung sichtbar (auch nach Neuladen); zweiter Fall legt Standort/Bereich/Anlage per API an und prüft, dass `192.0.2.256` den Feldfehler der API an der IP zeigt und nichts gespeichert wird. Keine Konsolenfehler (außer der erwarteten 400-Meldung im zweiten Fall).

### Wie wurde getestet?

`D` = `docker compose -p twox-032`, `W` = `docker compose -p twox-032-web -f deploy/compose/compose.web.yaml`; `.env` aus `.env.example` (ohne BOM) mit `TWOX_API_PORT=18032`. Die Umgebungen „2x“ und „twox-leit“ wurden nicht berührt.

| AK | Ergebnis |
| --- | --- |
| 0 | erfüllt: `docker version` (Server 29.9.3), `docker compose version` (v5.7.0), Exit 0 |
| 1 | erfüllt: `W --profile dev build web-dev`, `npm ci` („added 425 packages“); `lint`, `typecheck` ohne Meldung; `test`: 13 Dateien, 235 Fälle bestanden; `build`: `index-….js 468.45 kB` (gzip 144.48 kB); `licenses`: „License check passed.“ – je Exit 0 |
| 2 | erfüllt: `npm run api:generate` Exit 0; `git diff --exit-code -- web/openapi web/src/api` Exit 0, `git status --porcelain --untracked-files=all` dazu leer |
| 3 | erfüllt: Bau, `pull e2e`, `npm ci`, `up -d --wait` (alle healthy), „Create test account“ wie in `ci.yml` („Created account 'e2e-manager' …“), `D --profile e2e run --rm e2e`: „14 passed“, Exit 0 |
| 4 | erfüllt: erneut `up -d --wait`, „Create test account“ („Updated …“), e2e: „14 passed“, Exit 0 |
| 5 | erfüllt: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` Exit 0; danach kein Container, Volume oder Netz mit `twox-032` |

### Zweig und Arbeitsverzeichnis

Zweig `worktree-agent-ab470f35db19e5455`, Arbeitsverzeichnis `.claude/worktrees/agent-ab470f35db19e5455`. Nicht gepusht, nicht zusammengeführt.

### Abweichungen und Hinweise

1. **Zwei bestehende Tests angepasst**, weil die Platzhalter ersetzt sind:
   - `web/src/routes.test.tsx`: `/` prüft jetzt den Baum statt des Platzhalters; `/devices/plc-1` gehört jetzt zu den Adressen mit `NotFound` (keine Geräte-ID); der Parametertest öffnet `/devices/1001` mit gefälschter API.
   - `web/e2e/navigation.spec.ts`: Der Test „an address with a parameter opens directly“ öffnet `/documents/7` statt `/devices/plc-1`, denn die Geräteseite braucht ein echtes Gerät. Den direkten Aufruf einer Geräteseite (Neuladen) prüft `assets.spec.ts`. 036 muss diesen Test ändern, wenn die Dateiseite den Platzhalter ersetzt.
2. **Feldfehler ohne Änderung an `api/errors.ts`:** `ApiError` behält nur Status und `detail`, nicht den Rumpf einer 400. Statt die gemeinsame Datei zu ändern, liest `structure/save.ts` den Rumpf über eine eigene fetch-Hülle (Option `fetch` des erzeugten Clients). Falls weitere Seiten (035, 036) Feldfehler brauchen, wäre ein Feld `body` in `ApiError` einfacher; das wäre ein eigener kleiner Auftrag.
3. **Anzahl der Geräte** bleibt bei aktiver Suche die der ganzen Struktur (nicht die Zahl der Treffer).
4. **Bearbeiten sendet `PUT`** mit allen Feldern des Formulars; Löschen gibt es nicht (Nicht-Ziel).
5. **Testdaten:** Vitest nutzt erkennbare Testnamen („Test site A“, „test-plc-1“) und IPs aus 192.0.2.0/24; Playwright nur `testName()`/`testIp()`.
6. Der Auftrag nennt `uniqueSuffix()`; verwendet ist `testName()`, das intern `uniqueSuffix()` nutzt und das Muster `e2e-<art>-<suffix>` liefert (Vorgabe der Leitstelle).
