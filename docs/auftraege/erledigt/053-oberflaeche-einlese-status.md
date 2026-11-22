# Auftrag 053 – Oberfläche: Einlese-Status auf Datei- und Geräteseite

Meilenstein: M2 · Freigabestufe: B · Status: erledigt

## Ziel

In der Oberfläche ist je Dateiversion sichtbar, ob sie eingelesen ist: in der Warteschlange, läuft, fertig, gescheitert oder übersprungen. Fehler erscheinen mit verständlicher Meldung; Verwalter können das Einlesen erneut anstoßen. Das erfüllt „Fehler sind sichtbar“ der Abnahme M2 und „Statusanzeige, neuer Versuch“ aus Startunterlage 4.

## Umfang

- **Dateiseite** (`web/src/pages/DocumentPage.tsx`, `web/src/components/files/`):
  - Je Version ein Status-Abzeichen: „In Warteschlange“, „Wird eingelesen“ (mit Schritt), „Eingelesen“ (Seiten- und Abschnittszahl), „Fehler“, „Übersprungen“.
  - Bei Fehler oder Überspringen die übersetzte Meldung zur Fehlerart, der technische Text aufklappbar.
  - Schaltfläche „Erneut einlesen“ nur für `manage`, nur ohne laufenden Auftrag; ruft `POST /api/v1/document-versions/{id}/ingest/` über den erzeugten Client; 409 wird als Meldung angezeigt.
  - Solange ein Auftrag `queued` oder `running` ist, fragt die Seite alle 5 Sekunden neu ab (TanStack Query `refetchInterval`), sonst nicht.
- **Geräteseite** (`web/src/components/DeviceFiles.tsx`): kleines Abzeichen für die neueste Version jeder Datei.
- Bausteine `IngestStatusBadge` und `IngestError` als eigene Komponenten in `web/src/components/files/IngestStatus.tsx`, damit 055 sie wiederverwendet.
- Texte in `web/src/locales/de/files.json` und `en/files.json`: eine Meldung je Fehlerart aus 042, dazu ein Text für unbekannte Fehlerarten.
- **Tests:**
  - Vitest: alle Zustände, Schaltfläche je Rolle (`manager` und `reader` aus `test/fakeApi.ts`), 409, Abfragen nur bei laufendem Auftrag, unbekannte Fehlerart, `error_detail` nur als Text.
  - Playwright `web/e2e/ingest-status.spec.ts` (als `e2e-manager`):
    - Eine im Test erzeugte `.txt`-Datei hochladen: erscheint als „Übersprungen“ mit Begründung (Formatprüfung aus 049, ohne Docling).
    - Eine im Test erzeugte kleine Markdown-Datei hochladen: zeigt einen der Zustände „In Warteschlange“, „Wird eingelesen“ oder „Fehler“ (in der CI fehlt Docling).
    - Zustand „Fehler“ mit Schaltfläche: Antwort über `page.route` mit einer selbst geschriebenen Antwort hergestellt, nicht durch Warten auf die Wiederholungen.

## Nicht-Ziele

- Keine Übersicht aller Aufträge (055), keine Suchseite (054).
- Keine Änderung an API und erzeugtem Client.
- Keine Änderung an `web/src/test/fakeApi.ts` (054 läuft gleichzeitig); Testdaten in `web/src/components/files/testData.ts`.
- Kein Zusammenlegen der Feldfehler-Hilfen (bekannte M1-Grenze).

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/pages/DocumentPage.tsx`, `web/src/pages/DocumentPage.test.tsx`
- neu: `web/src/components/files/IngestStatus.tsx`, `web/src/components/files/IngestStatus.test.tsx`; `web/src/components/files/testData.ts`
- `web/src/components/DeviceFiles.tsx`, `web/src/components/DeviceFiles.test.tsx`
- `web/src/locales/de/files.json`, `web/src/locales/en/files.json`
- neu: `web/e2e/ingest-status.spec.ts`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-053`, `W` für `docker compose -p twox-053-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18053` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. Oberfläche wie im CI-Job `web`: `W --profile dev build web-dev` und `W run --rm web-dev npm ci`, danach `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build` und `npm run licenses`, je über `W run --rm web-dev …`, mit Exit-Code 0. Vite meldet keine Warnung zur Bündelgröße über 500 kB; die Größe des Hauptbündels steht im Kurzbericht.
2. `W run --rm web-dev npm run api:generate`, danach `git diff --exit-code -- web/openapi web/src/api` ohne Unterschied.
3. Browser-Test wie im CI-Job `e2e`: `D --profile dev build migrate api worker web-dev`, `D --profile e2e pull e2e`, `D --profile dev run --rm web-dev npm ci`, `D up -d --wait --wait-timeout 300 db valkey worker api`; dann der Schritt „Create test account“ aus `ci.yml` wörtlich, nur mit `D` statt `docker compose` (Kennwort nur über den Variablennamen `TWOX_ACCOUNT_PASSWORD`); dann `D --profile e2e run --rm e2e`: alle Fälle bestanden, darunter `ingest-status.spec.ts`, Exit-Code 0.
4. Ein zweiter Lauf von Kriterium 3 ohne `down -v` bleibt grün.
5. Lokal, mit Docling und Modell: Eine PDF-Datei aus `testdata/klein/` hochladen. Die Dateiseite zeigt ohne Neuladen nacheinander „In Warteschlange“ oder „Wird eingelesen“ und dann „Eingelesen“ mit Seitenzahl. Beschreibung im Kurzbericht.
6. Abräumen: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

- **Nachtrag der Leitstelle (E-59, KI optional):** Einbettungen, Vektorsuche und alles, was ein Modell braucht, sind eine aktivierbare Zusatzfunktion. Schalter `TWOX_AI_ENABLED` (Einstellung in `settings.py`, Standard `False`; `.env.example` mit Kommentar). Bei „aus“: kein Aufruf von Ollama, keine Einbettungs-Aufgaben, Einlesen endet nach den Abschnitten erfolgreich, die Suche arbeitet nur mit der Stichwortsuche, Selbsttest und Oberfläche zeigen „KI nicht aktiviert“ als neutralen Zustand (kein Fehler, kein Warnsymbol). Jede KI-abhängige Stelle braucht einen Test für beide Zustände; die CI läuft mit „aus“ und mit „an“ plus Attrappe.

Voraussetzung: 051 ist nach `main` zusammengeführt (Feld `ingest` und Endpunkte im erzeugten Client).

- Welle 7, parallel zu 052 und danach zu 054.
- **Keine neue Abhängigkeit.**
- Texte aus der API (`error_detail`) nur als Text darstellen, nie als HTML.
- Bezeichnungen in beiden Sprachen; Englisch ist der Schlüsselkatalog (TypeScript prüft die Schlüssel).
- In der CI läuft kein Docling. Kein Test wartet auf `done` oder auf das Ende der Wiederholungen.
- Die CI hat nur das Testkonto `e2e-manager` (Rolle `manage`); Verhalten der Rolle `read` deshalb in Vitest.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Läufe am 22.11.2026 im Container, Projekte `twox-053` und `twox-053-web`, Port 18053, Docker Engine 29.9.3, Compose v5.7.0. Kriterien 0, 2, 3, 4, 5 und 6 erfüllt; Kriterium 1 bis auf die Bündelgröße erfüllt (Warnung über 500 kB bestand schon auf `main`, siehe Abweichung 1). Keine neue Abhängigkeit, kein Eingriff in API, erzeugten Client oder `test/fakeApi.ts`.

### Was wurde gebaut?

- **`web/src/components/files/IngestStatus.tsx`** (neu, für 055 wiederverwendbar):
  - `IngestStatusBadge`: Abzeichen mit Icon und Text für den neuesten Auftrag einer Version (Feld `ingest`): „In Warteschlange“ (neutral, Uhr), „Wird eingelesen: <Schritt>“ (Info-Farbe, drehendes Lade-Icon; Schritte „Umwandeln“, „Abschnitte bilden“, „Einbettungen berechnen“), „Eingelesen“ (Erfolg, daneben „60 Seiten, 140 Abschnitte“ mit Pluralformen; fehlende Seitenzahl wird weggelassen), „Fehler“ (Gefahr-Farbe), „Übersprungen“ (neutral, kein Fehler), „Nicht eingelesen“ (Version ohne Auftrag, neutral). `compact` zeigt nur den Zustand (Geräteseite).
  - `IngestError`: übersetzte Meldung je Fehlerart (alle zehn Codes aus 042, dazu ein Text für unbekannte Fehlerarten mit dem Code als reinem Text und einer für leeren Code); `error_detail` aufklappbar unter „Technische Angaben“ (`<details>`, nur als Text). Bei `done` mit `partly_converted` der Hinweis „Nur teilweise umgewandelt …“ (Warnfarbe) mit dem Text aufklappbar.
  - `IngestRetryButton`: „Erneut einlesen“ (bzw. „Einlesen“ ohne bisherigen Auftrag) über `documentVersionIngestMutation` des erzeugten Clients; verborgen bei `queued`/`running`; 409 → „Diese Version wird bereits eingelesen.“, 400 → „Konfigurationsdateien werden nicht eingelesen.“, andere Fehler über `ErrorMessage`. Danach werden die Daten neu geladen (`reloadAfterSave`).
  - `isIngestActive`, `ingestPollInterval`, `INGEST_POLL_INTERVAL_MS = 5000` für `refetchInterval`.
- **Dateiseite** (`DocumentPage.tsx`): Spalte „Einlesen“ je Version mit Abzeichen, Meldung und Schaltfläche (nur `manage` und nur für Dokumente, nicht für Konfigurationen). Die Seite fragt alle 5 s neu ab, solange eine Version einen Auftrag `queued` oder `running` hat, sonst nicht.
- **Geräteseite** (`DeviceFiles.tsx`): Spalte „Einlesen“ mit kompaktem Abzeichen der neuesten Version; dieselbe Abfrage-Regel (siehe Abweichung 3).
- **Texte** in `locales/{en,de}/files.json` (Spalte, Zustände, Schritte, Zählungen, zehn Fehlerarten, unbekannt, Schaltfläche, 409, 400).
- **Icons** (`icons/names.ts`, `icons/README.md`): `queued` (Clock, STA-08), `skipped` (CircleMinus), `notIngested` (CircleDashed). `lucide-react` wird weiter nur in `names.ts` importiert.
- **Testdaten** (`components/files/testData.ts`): `ingestJob()` und ein falscher Endpunkt `POST …/ingest/` (202, 409 bei aktivem Auftrag, 400 für Konfigurationen, `rejectNextIngest`, `ingestRequests`).
- **Doku:** Abschnitt „Files“ in `web/src/pages/README.md`.
- E-59: Bei KI aus gibt es keinen Schritt `embed` und keinen Hinweis auf fehlende Einbettungen; „Übersprungen“, „In Warteschlange“ und „Nicht eingelesen“ sind neutral gestaltet. Die Meldungen zu `embedding_*` (nur bei KI an möglich) sagen, dass die Abschnitte gespeichert sind und nur die Einbettungen fehlen.

### Wie wurde getestet?

`D` = `docker compose -p twox-053`, `W` = `docker compose -p twox-053-web -f deploy/compose/compose.web.yaml`; `.env` aus `.env.example` (ohne BOM) mit `TWOX_API_PORT=18053` (KI an). Vor jedem Build `web/dist` gelöscht. Die Umgebungen „2x“ und „twox-leit“ wurden nicht berührt.

| Nr. | Ergebnis | Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | Engine 29.9.3, Compose v5.7.0, je Exit 0 |
| 1 | teilweise | `build web-dev`, `npm ci`, `lint`, `typecheck`, `test` (34 Dateien, 636 Tests), `build`, `licenses` („423 packages … License check passed.“) je Exit 0. **Vite warnt über 500 kB:** Hauptbündel `index-….js` 560,93 kB (gzip 169,61 kB); auf dem Ausgangsstand `9af50bc` gemessen 550,77 kB (gzip 166,79 kB), Warnung dort ebenfalls. Zuwachs durch 053: 10,16 kB |
| 2 | erfüllt | `npm run api:generate` Exit 0; `git diff --exit-code -- web/openapi web/src/api` Exit 0, `git status --porcelain` dazu leer |
| 3 | erfüllt | `build migrate api worker web-dev`, `pull e2e`, `npm ci`, `up -d --wait …` je Exit 0; „Create test account“ wörtlich mit `D`: „Created account 'e2e-manager' …“. Erster Lauf: 43 bestanden, 1 fehlgeschlagen (eigener Test, siehe Abweichung 4); nach der Korrektur: **44 passed**, Exit 0, darunter die drei Fälle aus `ingest-status.spec.ts` |
| 4 | erfüllt | dritter Lauf ohne `down -v` nach dem letzten Code-Commit: „Updated account …“, **44 passed**, Exit 0 |
| 5 | erfüllt (mit Abweichung 2) | siehe unten |
| 6 | erfüllt | siehe Schlussantwort an die Leitstelle (Abräumen nach dem Commit dieses Berichts) |

**Vitest neu oder erweitert:** `IngestStatus.test.tsx` (alle Zustände englisch und deutsch, Schritte, Zählungen mit Plural, `compact`, Farben neutral/Erfolg/Fehler/Info, eigene Meldung je Fehlerart in beiden Sprachen und alle verschieden, unbekannte und leere Fehlerart, `error_detail` mit `<img onerror>`, `<script>` und `<b>` nur als Text, Teilumwandlung, Abfrage-Regel, Schaltfläche: POST, versteckt bei `queued`/`running`, 409 englisch und deutsch, 400, 500). `DocumentPage.test.tsx` (Zustände je Version, deutsch, `reader` ohne Schaltfläche, `manager` mit Schaltfläche nur ohne aktiven Auftrag, Konfiguration ohne Schaltfläche, Anstoßen → „In Warteschlange“, 409 → Meldung und danach aktiver Auftrag; mit künstlicher Uhr: Abfrage alle 5 s bei `queued`/`running`, Ende der Abfragen nach `done`, keine Abfrage ohne aktiven Auftrag). `DeviceFiles.test.tsx` (kompaktes Abzeichen der neuesten Version, deutsch, Abfrage nur bei aktivem Auftrag).

**Playwright `web/e2e/ingest-status.spec.ts`** (als `e2e-manager`): `.txt` hochgeladen → Dateiseite „Skipped“ mit Begründung, technischer Text aufklappbar, Schaltfläche sichtbar; Geräteseite „Skipped“. `.md` hochgeladen → Zustand `queued`, `running` oder `failed`. Zustand „Fehler“: Antwort der Datei-API über `page.route` mit selbst geschriebenem Auftrag (`failed`, `docling_unavailable`) → Meldung und Text; Klick auf „Erneut einlesen“ schickt den echten POST (202), danach zeigt die Seite den neuen echten Auftrag (`skipped`). Kein Test wartet auf Docling.

**Kriterium 5 (lokal, Docling `twox-053-docling-1` gestartet, Ollama am Host mit Modell, KI an):** `testdata/klein/recht/BetrSichV.pdf` an „SPS Bohrstation“ hochgeladen, Dateiseite im eingebauten Browser geöffnet (Port 18053, Testkonto). Erster Zustand nach 4 s: „Wird eingelesen: Umwandeln“ (der Worker hatte den Auftrag schon übernommen, „In Warteschlange“ war deshalb nicht zu sehen). Die Seite fragte alle 5 s neu ab; nach 298 s Einlesedauer zeigte sie ohne Neuladen (eine einzige Navigation) „Eingelesen · 60 Seiten, 140 Abschnitte“ mit der Schaltfläche „Erneut einlesen“; danach keine weiteren Abfragen. API: `done`, Schritt `embed`, 60 Seiten, 140 Abschnitte.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-af54c4cba6fbdf170`
- Arbeitsverzeichnis: `.claude/worktrees/agent-af54c4cba6fbdf170` (relativ zum Projektordner)
- Commits: `Add ingest status badge, error message and retry button for versions`, `Show the ingest status on the file page and the device page`, `Add a browser test for the ingest status and document the building blocks`, dazu dieser Kurzbericht. Nicht gepusht, nichts zusammengeführt.

### Abweichungen und Hinweise

1. **Bündelgröße (Kriterium 1):** Vite warnt über 500 kB schon auf `main` (550,77 kB, seit 039 bekannt). Innerhalb der genannten Dateien lässt sich das nicht beheben; dafür müssten Seiten in `routes.tsx` per `lazy()` nachgeladen oder die Grenze in `vite.config.ts` geändert werden. Optionen: (a) eigener kleiner Auftrag „Seiten per `lazy()` nachladen“ (Empfehlung), (b) Kriterium für M2 auf „keine neue Warnung“ ändern, (c) `chunkSizeWarningLimit` anheben (nicht empfohlen, verdeckt das Wachstum).
2. **Kriterium 5:** Der Upload lief nicht über das Formular, sondern mit `curl` über dieselbe API (`POST /api/v1/devices/33/documents/`, angemeldet mit dem Testkonto): Der eingebaute Browser kann keine lokale Datei in ein Dateifeld legen. Die Anzeige auf der Dateiseite (Abfragen, Zustandswechsel ohne Neuladen) war davon unberührt. Die Formular-Strecke selbst ist im Browser-Test mit `.txt` und `.md` abgedeckt.
3. **Abfragen auch auf der Geräteseite:** Der Auftrag verlangt sie nur für die Dateiseite. Ohne sie bliebe nach dem Hochladen „In Warteschlange“ stehen, bis jemand neu lädt; dieselbe Regel (5 s nur bei aktivem Auftrag) ist ein Zweizeiler und getestet.
4. **Erster Browser-Lauf rot (eigener Test):** `route.fetch()` aus dem Test-Runner erreicht die API nicht, weil nur Chromium den Hostnamen umleitet (`playwright.config.ts`). Die Antwort wird jetzt in der Seite gelesen und per `page.route` fest ausgeliefert. Danach zweimal grün.
5. **Zusätzliche Dateien außerhalb der genannten Liste:** `web/src/icons/names.ts` und `web/src/icons/README.md` (drei Status-Icons, nach Vorgabe der Leitstelle), `web/src/pages/README.md` (Doku).
6. **Schaltfläche auch für `done` und für Versionen ohne Auftrag** („Einlesen“): „nur ohne laufenden Auftrag“ wörtlich umgesetzt; Versionen aus der Zeit vor M2 lassen sich so einzeln einlesen.
7. **Meldung 409 bleibt stehen**, solange der dann aktive Auftrag läuft, und verschwindet, wenn er endet. Die Schaltfläche hat wie der Download-Link einen Namen mit Versionsnummer („Version 2 erneut einlesen“).
8. Hinweis für 061: Nach 061 kann der neueste Auftrag ein reiner Einbettungsauftrag sein; die Anzeige nutzt nur `status`, `step`, `error_code`, `page_count`, `section_count` und `partly_converted` und passt damit ohne Änderung.
