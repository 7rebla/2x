# Auftrag 036 – Oberfläche: Dateien je Gerät hochladen, Versionen, herunterladen

Meilenstein: M1 · Freigabestufe: B · Status: zur Prüfung

## Ziel

Auf der Geräteseite sieht man die Dateien des Geräts mit ihren Versionen und kann sie herunterladen. Als „Verwalten“ lädt man neue Dateien und neue Versionen hoch. Dubletten und abgewiesene Uploads werden verständlich gemeldet.

## Umfang

- Bereich „Dateien“ auf der Geräteseite (Platzhalter-Komponente aus 032 ersetzen):
  - Liste mit Titel, Art und neuester Version (Nummer, Datum, Größe, Benutzer).
  - Die Prüfsumme gekürzt, beim Aufklappen vollständig.
- Dateiseite `/documents/:documentId` (Platzhalter aus 023 ersetzen):
  - Alle Versionen mit Download-Link je Version.
  - Das Protokoll des Dokuments über `AuditTrail` aus 033.
- Hochladen (nur `manage`):
  - Neue Datei (Datei, Titel, Art) und neue Version.
  - 409 zeigt „Inhalt gleicht Version N“.
  - Der Dubletten-Hinweis aus der Antwort nennt die anderen Fundstellen mit Link.
  - 413 zeigt die Obergrenze.
  - Die Ablehnung von Konfigurationsdateien (Antwort zu Auftrag 024, Frage 2) wird verständlich angezeigt; das Formular weist darauf hin.
- Texte in `files.json` (seit 018 angelegt), Deutsch und Englisch; Größen und Daten über `Intl`.
- Vitest: Liste, Upload-Ablauf mit nachgebildetem Client, Anzeige von 409, Dubletten und 413, Sichtbarkeit je Rolle.
- Playwright, neue Datei `web/e2e/files.spec.ts`:
  - Anmelden über `fixtures.ts` als `manage`.
  - Über die API Standort, Bereich, Anlage und Gerät mit `uniqueSuffix()` anlegen.
  - Eine im Test erzeugte Textdatei mit Inhalt je Lauf hochladen (Version 1), dann geänderten Inhalt als Version 2; beide Versionen sind sichtbar.
  - Version 1 herunterladen und den Inhalt prüfen.
  - Dieselbe Datei erneut hochladen zeigt die 409-Meldung.

## Nicht-Ziele

- Vorschau von Dateien im Browser, Löschen, Änderungsvergleich (M8), Einlese-Status (M2). Fortschrittsanzeige ist kein Muss.
- Änderungen am Backend, an `routes.tsx`, `navigation.ts`, `Layout.tsx`, `package.json`.

## Betroffene Bereiche (Ordner, Dateien)

- Komponenten unter `web/src/components/files/`, die Dateien-Komponente der Geräteseite, `web/src/pages/DocumentPage.tsx`
- `web/src/locales/*/files.json`, Tests
- neu: `web/e2e/files.spec.ts`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-036`, `W` für `docker compose -p twox-036-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18036` setzen.

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

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); 029, 032 und 033 sind nach `main` zusammengeführt.

- Welle 7, parallel zu 034 und 035. Nur die eigenen Dateien.
- **Keine neue Abhängigkeit.** Upload über den generierten Client (`multipart`); meldet er keinen Fortschritt, dann ohne Fortschrittsanzeige.
- Der Download läuft über die API mit Sitzung; es gibt keinen öffentlichen Medien-Pfad.
- Testdaten (CLAUDE.md, Leitplanke 9): keine erfundenen Anlagen, die echt wirken. Nur Namen nach dem Muster `e2e-<art>-<suffix>` und IP-Adressen aus 192.0.2.0/24, über `web/e2e/fixtures.ts`. Keine Herstellerunterlagen als Testdatei.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Kriterien 0–5 erfüllt; alle Läufe am 22.11.2026 im Container (Docker Engine 29.9.3, Compose v5.7.0) auf dem committeten Stand. Keine neue Abhängigkeit, Schema und Client unverändert, Backend unverändert. Keine offene Frage an a7.

### Was wurde gebaut?

- **Dateien auf der Geräteseite** `web/src/components/DeviceFiles.tsx` (Platzhalter aus 032 ersetzt, gleicher Name und gleiche Props): Tabelle mit Titel (Link auf `/documents/<id>`), Art (übersetzt), neuester Version mit Nummer, Datum, Größe, Benutzer („System“ bei `null`), Prüfsumme gekürzt (12 Zeichen, `<details>`: ein Klick zeigt sie vollständig) und Download-Link. Hinweis bei leerer Liste; Fehler der API im Dateibereich über `ErrorMessage`. Für `manage` darunter das Formular „Neue Datei hochladen“.
- **Dateiseite** `web/src/pages/DocumentPage.tsx` (`/documents/:documentId`, Platzhalter ersetzt): Titel als Überschrift, Gerät als Link (Name und Kennung, nachgeladen), Art, angelegt am/von; alle Versionen **neueste zuerst** mit Nummer, Datum, Größe, Benutzer, Original-Dateiname, Prüfsumme und Download-Link je Version; für `manage` das Formular „Neue Version hochladen“ und das Protokoll der Datei über `<AuditTrail objectType="files.document" objectId={id} />`. Ungültige Id (ohne Anfrage) und 404 zeigen `NotFound`, andere Fehler `ErrorMessage` unter der Überschrift „Datei“.
- **Bausteine** unter `web/src/components/files/`:
  - `format.ts`: Größe über `Intl.NumberFormat` mit Einheiten (dezimal, 1 kB = 1000 Byte, passend zur Grenze 200 000 000 Byte = 200 MB), Datum über `Intl.DateTimeFormat`, gekürzte Prüfsumme, Adressen, Id-Prüfung, Grenze aus der 413-Meldung.
  - `parts.tsx`: Prüfsumme, Größe, Zeitpunkt, Benutzer, Art, Download-Link (normaler Link auf `/api/v1/document-versions/<id>/download/`, die API setzt `Content-Disposition: attachment`).
  - `upload.ts`: Upload über den erzeugten Client (`deviceDocumentsCreate`, `documentVersionCreate`, `multipart/form-data`, CSRF über `api/client.ts`) mit eigener fetch-Hülle wie in `pages/structure/save.ts`, die eine Kopie von 400, 409 und 413 behält. Ergebnis als Union: hochgeladen (mit `duplicates`), 409 mit `existing_version`, 413 mit Grenze, 400 mit Feldfehlern (`parseFieldErrors` aus `save.ts` wiederverwendet), sonst Fehler. Leerer Titel wird nicht gesendet (die API nimmt den Dateinamen).
  - `UploadForm.tsx`: `NewDocumentForm` (Datei, Titel, Art) und `NewVersionForm` (Datei), React-19-Formularaktionen ohne Formular-Bibliothek. Meldungen: „Als Version N hochgeladen.“ mit Dubletten-Hinweis („Derselbe Inhalt liegt bereits an anderer Stelle:“, je Fundstelle Link auf Gerät und Datei, Versionsnummer); 409 „Inhalt gleicht Version N. Es wurde keine neue Version angelegt.“ mit Datum und Download-Link der Version; 413 „Die Datei ist größer als die Obergrenze von 200 MB.“ (Grenze aus der Meldung der API, sonst Text ohne Zahl); 400 mit Feldfehlern am Feld und übrigen Meldungen oben; fehlende Datei wird vor dem Senden gemeldet. Der Titel bleibt nach einem Fehler stehen, nach Erfolg sind die Felder leer und die Daten neu geladen (`reloadAfterSave`). Während des Hochladens „Wird hochgeladen …“, Knopf gesperrt; keine Fortschrittsanzeige (der Client meldet keinen Fortschritt).
  - **Konfigurationen (E-37/E-42):** Das Auswahlfeld „Art“ zeigt „Konfiguration (noch nicht möglich)“ gesperrt; darunter der Hinweis, dass Konfigurationen Zugangsdaten enthalten können, erst ab M5 geschwärzt werden und auch nicht als Dokument hochgeladen werden sollen. Weist die API eine Konfiguration ab (400 an `kind`, bei einer neuen Version eines Konfigurations-Dokuments unter `non_field_errors`), erscheint zusätzlich „Konfigurationsdateien werden noch nicht angenommen (das Schwärzen von Zugangsdaten folgt mit Meilenstein M5).“
- Dateinamen, Titel, Gerätenamen und Benutzernamen werden nur als Text gerendert, nie über die Interpolation von i18next (getestet mit HTML im Titel).
- **Texte** `web/src/locales/{de,en}/files.json`, gleiche Schlüssel.
- **Doku** `web/src/pages/README.md`: Abschnitt „Files“, Verweis auf der Geräteseite aktualisiert.

### Wie wurde getestet?

`D` = `docker compose -p twox-036`, `W` = `docker compose -p twox-036-web -f deploy/compose/compose.web.yaml`; `.env` aus `.env.example` (ohne BOM) mit `TWOX_API_PORT=18036`. Die Umgebungen „2x“ und „twox-leit“ wurden nicht berührt.

- **Vitest (neu, 66 Fälle):**
  - `components/files/format.test.ts` (29): Größen in Englisch und Deutsch, Prüfsumme, Adressen, Id-Prüfung, Grenze aus der Meldung.
  - `components/files/upload.test.ts` (10): Multipart mit Datei, Titel, Art und `X-CSRFToken`; leerer Titel entfällt; 400, 413 mit und ohne lesbare Meldung, 403, keine Antwort; neue Version nur mit Datei; 409 mit `existing_version`, 409 ohne.
  - `components/DeviceFiles.test.tsx` (15): Liste mit allen Spalten, Prüfsumme gekürzt und aufgeklappt, leere Liste, HTML im Titel als Text, API-Fehler, Deutsch; Leser ohne Formular, Verwalter mit gesperrter Konfiguration und Hinweis; Upload-Ablauf mit Neuladen und gesendetem Formular, Dubletten mit Links, 413 mit Grenze (Titel bleibt), abgewiesene Konfiguration, Fehler ohne Feld, fehlende Datei ohne Anfrage, 403.
  - `pages/DocumentPage.test.tsx` (12): Versionen neueste zuerst mit Download-Links, Gerät als Link, 404, ungültige Id ohne Anfrage, 500, Deutsch; Leser ohne Formular und ohne Protokoll-Anfrage, Verwalter mit `AuditTrail` (`object_type=files.document`, `object_id`); neue Version, 409 (Englisch und Deutsch), 413, abgewiesene neue Version einer Konfiguration.
  - Testhilfe `components/files/testData.ts`: gefälschte Datei-API mit Speicher und 409 bei gleichem Inhalt, Namen `Test …`.
- **Playwright** `web/e2e/files.spec.ts` (1 Fall, als `manage` über `fixtures.ts`): Standort, Bereich, Anlage, Gerät per API (`testName()`, `testIp(30)`); Geräteseite leer; Textdatei mit Inhalt je Lauf (`uniqueSuffix()`) als Version 1 über das Formular, Zeile mit Titel, Art, Version, Benutzer und Prüfsumme; Dateiseite über den Link; geänderter Inhalt als Version 2; beide Versionen sichtbar (2, 1); Version 1 per Klick heruntergeladen (Download-Ereignis, Dateiname, kein Fehler) und der Inhalt über dieselbe Adresse mit Sitzung geprüft (200, `attachment`, gleicher Text); dieselbe Datei erneut → 409-Meldung, weiter zwei Versionen; Neuladen der Dateiseite (Direktaufruf) und ein Protokolleintrag „Created“; keine Konsolenfehler außer der erwarteten 409.

| AK | Ergebnis |
| --- | --- |
| 0 | erfüllt: `docker version` (Server 29.9.3), `docker compose version` (v5.7.0), Exit 0 |
| 1 | erfüllt: `W --profile dev build web-dev`, `npm ci` („added 425 packages“); `lint`, `typecheck` ohne Meldung; `test`: 19 Dateien, 322 Fälle bestanden; `build`: `index-….js 499.84 kB` (gzip 151.61 kB); `licenses`: „License check passed.“ – je Exit 0 |
| 2 | erfüllt: `npm run api:generate` Exit 0; `git diff --exit-code -- web/openapi web/src/api` Exit 0, `git status --porcelain --untracked-files=all` leer |
| 3 | erfüllt: Bau, `pull e2e`, `npm ci`, `up -d --wait` (alle healthy), „Create test account“ wie in `ci.yml` („Created account …“), `D --profile e2e run --rm e2e`: „16 passed“, Exit 0 |
| 4 | erfüllt: dieselbe Folge ohne `down -v`: „Updated account …“, „16 passed“, Exit 0 |
| 5 | erfüllt: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` Exit 0; danach kein Container, Volume oder Netz mit `twox-036` |

### Zweig und Arbeitsverzeichnis

Zweig `worktree-agent-a58f626d1ceee5865`, Arbeitsverzeichnis `.claude/worktrees/agent-a58f626d1ceee5865`. Nicht gepusht, nicht zusammengeführt.

### Abweichungen und Hinweise

1. **Zwei bestehende Tests angepasst**, weil der Platzhalter der Dateiseite ersetzt ist:
   - `web/src/routes.test.tsx`: `/documents/42` aus der Platzhalter-Tabelle entfernt; der Parametertest öffnet `/documents/7` mit gefälschter Datei-API und prüft den Titel.
   - `web/e2e/navigation.spec.ts`: „an address with a parameter opens directly“ öffnet jetzt `/documents/2147483647` (eine Datei, die kein Test anlegt): Django liefert die Seite (200), die Seite fragt die API (404) und zeigt `NotFound` im Rahmen. Den Direktaufruf einer echten Dateiseite prüft `files.spec.ts` (Neuladen), den einer Geräteseite `assets.spec.ts`. Die erwartete 404-Meldung der Konsole wird dort herausgefiltert.
2. **`api/errors.ts` nicht geändert.** Statt eines Felds `body` in `ApiError` liest `files/upload.ts` die Antworten 400/409/413 über eine eigene fetch-Hülle (Muster aus `save.ts`). `parseFieldErrors` und `reloadAfterSave` werden aus `pages/structure/save.ts` importiert (Komponente importiert aus `pages/`; bei einem späteren Umbau wäre ein gemeinsamer Ort wie `api/` besser).
3. **Die Grenze der 413** steht nicht in einer Einstellung der Oberfläche; sie wird aus der Meldung der API gelesen (einzige Zahl darin, `%d` ohne Tausendertrennung). Fehlt sie, erscheint der Text ohne Zahl.
4. **Protokoll auf der Dateiseite** zeigt nur die Einträge des Dokuments (`files.document`). Neue Versionen sind eigene Objekte (`files.documentversion`) und erscheinen dort nicht; `AuditTrail` filtert auf genau eine Objektart. Das Protokoll sehen nur Verwalter (die API erlaubt es nur ihnen, E-43); Leser bekommen den Bereich gar nicht, statt eines „keine Berechtigung“.
5. **Neue Versionen** lädt man auf der Dateiseite hoch, nicht in der Liste der Geräteseite.
6. **Test-Technik:** Unter jsdom sendet Nodes `Request` eine jsdom-Datei als leeren Teil „blob“. Die Vitest-Fälle nutzen deshalb `textFile()` und `fakeUploadApi()` (in `files/testData.ts`), die Formulare als Multipart-Text senden; der Code der Anwendung ist derselbe wie im Browser. Aus demselben Grund merkt sich das Formular die gewählte Datei zusätzlich aus dem `change`-Ereignis (Rückfall, wenn `FormData` sie nicht enthält). `web/src/test/fakeApi.ts` ist unverändert.
7. **Ungenutzte Schlüssel:** `assets.json` enthält weiter `files.heading` und `files.placeholder` aus 032; die Texte des Bereichs kommen jetzt aus `files.json`. `assets.json` gehört nicht zu diesem Auftrag und blieb unverändert; die Schlüssel können bei Gelegenheit entfallen.
8. **Bündelgröße:** `index-….js` liegt mit 499.84 kB knapp unter der Warnschwelle von Vite (500 kB); der nächste Auftrag mit Oberfläche wird sie vermutlich überschreiten (nur eine Warnung, kein Fehler).
9. Der Auftrag nennt `uniqueSuffix()` für die Namen; verwendet ist `testName()` (nutzt `uniqueSuffix()`, Muster `e2e-<art>-<suffix>`), `uniqueSuffix()` direkt für den Dateiinhalt je Lauf.
