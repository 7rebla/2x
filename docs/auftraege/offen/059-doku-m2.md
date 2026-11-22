# Auftrag 059 – README und ARCHITECTURE für M2

Meilenstein: M2 · Freigabestufe: B · Status: zur Prüfung

## Ziel

`README.md` und `docs/ARCHITECTURE.md` beschreiben den Stand nach M2: Einlesen, Docling, Abschnitte, Einbettungen, Suche, neue Seiten, Einstellungen, Befehle und Grenzen. Ein Mitentwickler kann danach das Einlesen lokal mit Docling und Ollama in Gang bringen.

## Umfang

- `README.md`:
  - Docling lokal starten (`docker compose up -d --wait docling`; die erste Umwandlung lädt die Modelle);
  - Einbettungsmodell in Ollama laden (`ollama pull <modell>`);
  - `check_docling --convert -` und `check_llm --embed`;
  - Einlesen anstoßen und nachholen (`ingest_versions`, `embed_sections`, je mit `--user` und `--commit`);
  - Suchprobe (`evaluate_search`);
  - lokaler Teil des Abnahmetests (`TWOX_M2_LOCAL`, `TWOX_M2_REQUIRED`, `TWOX_M2_FAILED_FILE`) und die Schrittfolge zur Abnahme von Hand aus 058.
- `docs/ARCHITECTURE.md`:
  - Tabelle der Django-Apps: `ingest` und `search` gefüllt, `answers` mit Einbettungen; Zeile `importers` nach Frage 2 in 049.
  - ER-Diagramm mit `IngestJob` und `Section`.
  - Sequenzdiagramm: Upload → `on_commit` → `ingest` → Wiederverwendung oder Docling (asynchron, Abfrage mit Neuplanung) → Antwort speichern → Abschnitte → `embed` (in Teilen) → `done`.
  - Warteschlangen, Routen, Concurrency, Zeitlimits (Tabelle aus 045).
  - Suche: Schnittstelle, Volltext mit `simple`, `german`, `english`, exakte Kennungen, Vektor, Zusammenführung, Versionsregel, Zusammenfassen gleicher Inhalte, Fallback ohne Modell.
  - Rechte der neuen Endpunkte, Sichtbarkeit von `requested_by` und `error_detail`.
  - Konfigurationstabelle mit allen neuen `TWOX_*`-Variablen.
  - „What CI runs / does not run“ ergänzen.
  - Grenzen: Formatliste und Restrisiko (Konfiguration als PDF oder Markdown, Markdown nur nach Endung); Standard-Zugangsdaten in Herstellerhandbüchern durchsuchbar (Frage 3 in 049); kein Abbrechen, Docling rechnet nach `timeout` weiter; Versionsregel; keine Rechte je Gerät (5.6, E-40); keine Zeilenangabe bei Markdown (Frage 3 in 042); Modellwechsel braucht `embed_sections --all`; Aufträge nach einem Abbruch (`--stuck`); gespeicherte Docling-Antworten ohne Löschen und mögliche Antworten ohne Verweis; `load_result` hält eine Antwort im Speicher; Suchtexte im Zugriffsprotokoll nach Frage 1 in 052; gemessene Laufzeiten aus 057.
  - Abschnitt „Configuration files“ nach Frage 1 in 049 anpassen.
- `web/src/pages/README.md`, soweit 054 und 055 es nicht schon nachgezogen haben.

## Nicht-Ziele

- Kein Code.
- `docs/DECISIONS.md`, `docs/STATUS.md` und `docs/ROADMAP.md` ändert nur die Leitstelle.

## Betroffene Bereiche (Ordner, Dateien)

- `README.md`
- `docs/ARCHITECTURE.md`
- gegebenenfalls `web/src/pages/README.md`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-059`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18059` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. Jeder neue Befehl im README läuft, wie er dasteht (mit `D` bzw. dem Projektnamen dieses Arbeitsverzeichnisses), und endet mit Exit-Code 0 bzw. der beschriebenen Ausgabe. Liste mit Ergebnis je Befehl im Kurzbericht; Befehle mit Docling oder Ollama lokal geprüft.
2. Jeder Dateipfad, jede Umgebungsvariable und jeder Endpunkt in den geänderten Abschnitten existiert, geprüft mit `git grep` bzw. `web/openapi/schema.yml`; Liste im Kurzbericht.
3. Die Mermaid-Diagramme sind syntaktisch geprüft (Sichtprüfung; Ansicht auf GitHub geht nicht, weil nicht gepusht wird); Vorgehen im Kurzbericht.
4. Geheimnissuche: `docker compose -f deploy/compose/compose.tools.yaml run --rm gitleaks-dir` endet mit Exit-Code 0.
5. Kein Personenname, kein lokaler Pfad mit Benutzernamen und kein Zitat aus Herstellerunterlagen in den geänderten Dateien (`git diff main -- README.md docs/ARCHITECTURE.md web/src/pages/README.md` durchgesehen).
6. Abräumen: `D --profile dev down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

- **Nachtrag der Leitstelle (E-59, KI optional):** Einbettungen, Vektorsuche und alles, was ein Modell braucht, sind eine aktivierbare Zusatzfunktion. Schalter `TWOX_AI_ENABLED` (Einstellung in `settings.py`, Standard `False`; `.env.example` mit Kommentar). Bei „aus“: kein Aufruf von Ollama, keine Einbettungs-Aufgaben, Einlesen endet nach den Abschnitten erfolgreich, die Suche arbeitet nur mit der Stichwortsuche, Selbsttest und Oberfläche zeigen „KI nicht aktiviert“ als neutralen Zustand (kein Fehler, kein Warnsymbol). Jede KI-abhängige Stelle braucht einen Test für beide Zustände; die CI läuft mit „aus“ und mit „an“ plus Attrappe.

Voraussetzung: 055, 056 und 058 sind nach `main` zusammengeführt. Messwerte aus 057 werden übernommen, sobald dessen Kurzbericht vorliegt; sonst steht die Lücke im Kurzbericht und die Leitstelle trägt sie nach.

- Welle 11.
- Englisch (Entwicklerdoku).
- **Keine neue Abhängigkeit.**
- Kein Push (E-14).

- **Nachtrag der Leitstelle (Prüfung 045):** README (Abschnitt zu den Warteschlangen) und `docs/ARCHITECTURE.md` (Abschnitt „Task queues“) nennen noch drei feste Warteschlangen und die `--queues`-Liste. Seit 045: Worker ohne `--queues`, `embed` nur bei eingeschalteter KI, `--concurrency 4`, Prefetch 1, weiches Herunterfahren 60 s über `REMAP_SIGTERM=SIGQUIT` und `stop_grace_period: 90s`, die sieben Einlese-Variablen und die Startprüfung `check_ingest_timing`.

- **Nachtrag der Leitstelle (Prüfung 049):** In der Betriebsdoku das Restrisiko zu Leitplanke 5 nennen: Markdown wird über Endung und Textprüfung erkannt, PDF über die Signatur; eine Konfiguration, die als `.md` oder PDF hochgeladen wird, wird eingelesen. Office-Dateien werden nur am ZIP-Inhaltsverzeichnis erkannt. Dazu `ingest_versions` mit allen Optionen und der Hinweis, dass `--stuck` für laufende Umwandlungen mehr als `TWOX_INGEST_TIMEOUT_SECONDS` braucht.

- **Nachtrag der Leitstelle (Prüfung 052):** Neuer Endpunkt `GET /api/v1/search/` (Parameter, Grenzen, Antwortform mit `semantic` used/disabled/unavailable), neue Variable `TWOX_SEARCH_EMBED_TIMEOUT_SECONDS` (Vorgabe 20), Logfilter in `config/logging.py`: Suchtexte stehen nicht im Zugriffsprotokoll (nicht mehr als Grenze führen). `uvicorn --no-access-log` wirkt wegen der Django-Konfiguration nicht – erwähnen.

- **Nachtrag der Leitstelle (Prüfungen 053, 055, 062, 063):** In `web/src/pages/README.md` die Adressentabelle angleichen: alle Seiten außer Anmeldung und Struktur werden über `lazyPage()` nachgeladen (062); Abschnitte zu Suche, Einlese-Übersicht und Landkarte sagen noch `lazy()`. In `docs/ARCHITECTURE.md` den veralteten Satz zur Bündelgröße („just below the 500 kB warning threshold“) durch die Messwerte aus 062 ersetzen. Kopfzeile unter 1280 px nur Icons (055). Statuswechsel des Einlesens werden Screenreadern nicht angesagt (053) – als bekannte Grenze nennen. Such-Rangfolge nach 063 (exakte Treffer nur bei Kennungsanfragen absolut vorne) beschreiben. Neue Seiten `/search` und `/ingest`.
## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Läufe am 22.11.2026 im Container, Projekte `twox-059`, `twox-059-web` und `twox-059-tools`, Port 18059, Docker Engine 29.9.3, Compose v5.7.0, Ollama am Host mit `bge-m3`. Kriterien 0 bis 6 erfüllt, alle Nachträge umgesetzt. Nur Doku geändert, kein Code, keine Abhängigkeit.

### Was wurde gebaut?

- **`README.md`:** Status M2; Anforderungen mit Speicherbedarf von Docling (Grenze offen bei a7); Schnellstart mit Hinweis auf `TWOX_AI_ENABLED` in der Vorlage, Upload startet das Einlesen, Selbsttest mit KI-Karte; Tabelle der Seiten mit `/map`, `/search`, `/ingest`, `/settings`; neuer Abschnitt „Ingestion and search“ (Formate, Zustände, Wiederverwendung; Docling starten, `check_docling --convert -` mit `--page-range`/`--suffix`/`--json-out`, Messwerte 057; `ollama pull bge-m3`, `check_llm --embed`, Modell als Vorgabe bis zur Entscheidung; `ingest_versions` mit allen Optionen als Tabelle, `--stuck` mit Hinweis auf `TWOX_INGEST_TIMEOUT_SECONDS`; `embed_sections`; Suche mit Rangfolge nach 063; `evaluate_search`; Abnahme von Hand aus 058 auf Englisch, lokaler Teil mit `TWOX_M2_LOCAL`, `TWOX_M2_REQUIRED`, `TWOX_M2_FAILED_FILE`); Konfigurationstabelle M2 mit `check_ingest_timing` und E001/W001; Dienste (Worker ohne feste Warteschlangenliste, weiches Herunterfahren); Prüfbefehle mit `DISABLED:`, `WARNING:` und den `--embed`-Fehlern; Wartung mit `--stuck`; Tests mit Attrappen; „What the CI does not run“; Sicherheitshinweise (Restrisiko Leitplanke 5, Standard-Zugangsdaten in Handbüchern, Bereinigung von `error_detail`, `requested_by` nur `manage`, Suchtexte nicht im Zugriffsprotokoll, Modellserver).
- **`docs/ARCHITECTURE.md`:** Stand nach M2; Container-Diagramm und -Tabelle; Docling-Grenzen (200 MB, 2 000 Seiten, 2 h an drei Stellen, ein Worker, Speicher ohne Grenze als Vorgabe bis zur Entscheidung); App-Tabelle (`ingest`, `search` gefüllt, `answers` mit Einbettungen, `importers` nach Frage 2 in 049); ER-Diagramm mit `IngestJob` und `Section` samt Erläuterungen und Indizes; neuer Abschnitt „Ingestion“ mit Sequenzdiagramm (Upload → `on_commit` → Formatprüfung → `convert` → Wiederverwendung oder Docling mit Abfrage und Neuplanung → Antwort speichern → Abschnitte → `embed` in Teilen → `done`), Fehlerarten, Wiederholungen, Befehle, Systemprüfung und Messwerte aus 057; neuer Abschnitt „Search“ (Schnittstelle, `simple`/`german`/`english`, exakte Kennungen, Vektor mit HNSW-Einstellungen, RRF und Regel aus 063, Ausschlüsse, Versionsregel, Zusammenfassen, Rückfall ohne Modell, Messung); Endpunkt-Tabelle mit `/api/v1/search/` und `latest`/`is_latest`; Selbsttest mit Teil `ai`; „Task queues“ neu nach 045 (Tabelle der Zeitwerte, Startprüfung); neuer Abschnitt „Logging“ (Logfilter, `--no-access-log` wirkt nicht); Konfigurationstabelle mit allen neuen Variablen; „What CI runs / does not run“; Grenzen neu gegliedert (Betrieb, Konfigurationsdateien nach Frage 1 und 3 in 049, Einlesen, Suche, Oberfläche mit Bündelgröße aus 062, Kopfzeile unter 1280 px, keine Ansage für Screenreader).
- **`web/src/pages/README.md`:** Adressentabelle mit Spalte „Loaded“ (alle Seiten außer Anmeldung und Struktur über `lazyPage()`), `lazy()` in Suche, Einlese-Übersicht und Landkarte ersetzt, Hinweis zu Screenreadern (053).

### Wie wurde getestet?

`D` = `docker compose -p twox-059`, `.env` aus `.env.example` (mit dem Write-Werkzeug, ohne BOM) mit `TWOX_API_PORT=18059`, also KI an.

| Nr. | Ergebnis | Nachweis |
| --- | --- | --- |
| 0 | erfüllt | `docker version` 29.9.3, `docker compose version` v5.7.0, beide Exit 0 |
| 1 | erfüllt | Liste unten |
| 2 | erfüllt | alle 40 `TWOX_*`-Namen der drei Dateien kommen in `backend/`, `deploy/`, `.env.example` oder `web/e2e/` vor; alle Dateipfade in Backticks geprüft (Rest sind Teilpfade, URL-Teile, Bildnamen oder Medientypen); Endpunkte `/api/v1/search/`, `/api/v1/ingest-jobs/` (mit `latest`, `is_latest`) und `/api/v1/document-versions/{version_id}/ingest/` in `web/openapi/schema.yml`; alle Anker-Links innerhalb und zwischen README und ARCHITECTURE per Skript gegen die Überschriften geprüft (21 Links, keiner kaputt) |
| 3 | erfüllt | Sichtprüfung der vier Mermaid-Diagramme (Containers, ER, Ingestion, Self-test): nur bekannte Schlüsselwörter (`flowchart`, `erDiagram`, `sequenceDiagram`, `alt/else/end`, `loop/end`, `opt/end`, `Note over`), Attributtypen nur aus Wortzeichen (`string_list` statt `text[]`, `vector` ohne Klammern), keine `;` oder `#` in Nachrichten, jede Beziehung mit Kardinalität und Beschriftung in Anführungszeichen. Ein Prüfwerkzeug für Mermaid gibt es im Projekt nicht (wäre eine neue Abhängigkeit); Ansicht auf GitHub erst nach dem Push |
| 4 | erfüllt | `gitleaks-dir`: `no leaks found`, Exit 0 |
| 5 | erfüllt | `git diff main` der drei Dateien durchgesehen und nach Namen und Benutzerpfaden durchsucht: kein Personenname, kein lokaler Pfad, kein Zitat aus Herstellerunterlagen (Handbücher nur über Manifest-ID, Seite und eigene Worte) |
| 6 | erfüllt | `D --profile dev --profile e2e down -v`, `twox-059-web` und `twox-059-tools` `down -v`, je Exit 0 (siehe unten) |

Kriterium 1, Befehle wie im README (mit `D`), lokal geprüft:

| Befehl | Ergebnis |
| --- | --- |
| `D up -d --wait docling` | Exit 0 |
| `D exec api python manage.py check_docling` | `OK: docling-serve 1.38.2 at http://docling:5001`, Exit 0 |
| `D exec -T api python manage.py check_docling --convert - --page-range 1 2 < testdata/klein/recht/BetrSichV.pdf` | `OK: converted 2 pages, 25 texts, 2 tables in 6.1s (docling: 3.4s)`, Exit 0 |
| dasselbe mit `--suffix .md` und einer OPNsense-Markdown-Datei | `OK: converted 0 pages, 28 texts, 0 tables …`, Exit 0 |
| `ollama pull bge-m3` | nicht ausgeführt (Befehl am Host, außerhalb des Projektordners; E-56 erlaubt ihn nur der Leitstelle). Das Modell liegt vor: `check_llm` meldet 2 Modelle |
| `D exec api python manage.py check_llm` / `check_llm --embed` | `OK: … 2 model(s) reported` / `OK: embedded a test sentence with bge-m3 at …: 1024 dimensions in 0.04s`, je Exit 0 |
| Einlesen nach Upload (zwei Markdown-Dateien und eine `.txt` über `create_document` im `api`-Container, Gerätliste vorher mit `import_devices … --commit`) | 2 × `done`, Schritt `embed`, je 4 Abschnitte; `.txt` sofort `skipped`/`unsupported_format` |
| `ingest_versions --missing --user admin` (Probelauf und `--commit`), `--all` (Probelauf), `--failed --stuck 180` (Probelauf), `--stuck 180 --commit`, `--version 1 --commit` | Ausgabe mit den sechs Zählzeilen und `Dry run: …` bzw. `Saved.`, je Exit 0; `--version 1` legte einen Auftrag an, der die gespeicherte Antwort wiederverwendete (`reused_from`) |
| `embed_sections --user admin` / `embed_sections --all --user admin --commit` | `Dry run: …` / `versions: 2 jobs created …`, `Saved; the worker embeds the sections.`, danach beide `done`, je Exit 0 |
| `D exec -T api python manage.py evaluate_search < backend/twox/search/probes/m2.json` (auch `--json`) | `Not ingested: 7 of 7 probes`, Exit 0 |
| Browser-Test-Schritte aus dem README (`pull e2e`, `npm ci`, „Create test account“) | je Exit 0 |
| `D --profile e2e run --rm e2e npx playwright test e2e/m2-acceptance.spec.ts -g "local part"` ohne `TWOX_M2_LOCAL` | `1 skipped`, Exit 0 |
| dasselbe mit `TWOX_M2_LOCAL=1`, ohne die beiden anderen Variablen | scheitert mit der Meldung „TWOX_M2_REQUIRED lists the file names of the required manuals“, Exit 1 – wie im README beschrieben. Der vollständige lokale Teil braucht die Handbücher und ist Teil von 060 |

Web-Job wie in `ci.yml` (`twox-059-web`, vorher `web/dist` und `web/playwright-report` gelöscht): build, `npm ci`, lint, typecheck, test (38 Dateien bestanden), build (keine Größenwarnung; Startlast 387,52 + 67,51 + 35,71 + 28,41 = 519,15 kB), licenses, `api:generate` und `git diff --exit-code -- web/openapi web/src/api` je Exit 0. `git diff --check` ohne Befund. Der Backend-Job lief nicht, weil kein Backend-Code geändert ist (es gibt keine Tests, die README oder ARCHITECTURE lesen; eine Markdown-Linkprüfung steht nicht in `ci.yml`).

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-acbb14d2409b1fca8`
- Arbeitsverzeichnis: `.claude/worktrees/agent-acbb14d2409b1fca8`
- Commits: `Describe ingestion, search and the M2 commands in the README`, `Describe the architecture after M2 in ARCHITECTURE.md`, `Mark every page except sign-in and structure as loaded with lazyPage`, dazu dieser Kurzbericht. Nicht gepusht, nichts zusammengeführt.

### Abweichungen und Hinweise

1. **Messwerte 057 übernommen** (Docling 0,65–1,7 s/Seite, BetrSichV 4,3 s/Seite, Spitze 6,6 GiB, ~1,25 s je 100 Abschnitte, 49 MB bei 2 623 Abschnitten). Modellwahl und Docling-Speichergrenze stehen als „Vorgabe bis zur Entscheidung durch a7“, nicht als entschieden.
2. **Bündelgröße:** die Werte aus 062 (519,01 kB) plus eigene Nachmessung auf `main` nach 064 (519,15 kB; `i18n` +0,14 kB durch die Texte aus 064).
3. **Abnahme von Hand (058)** ins Englische übertragen, mit den englischen Beschriftungen der Oberfläche; Schritt 8 an 064 angepasst (ältere Versuche nur mit „Also show older attempts“). Der Befehl für den lokalen Teil hat zusätzlich `-g "local part"`, wie im Hinweis 3 von 058 empfohlen; ohne die Option läuft auch der CI-Teil.
4. **Ungereimtheit Code/Doku (nicht geändert):** Der Docstring und die Hilfe von `ingest_versions --stuck` (`backend/twox/ingest/management/commands/ingest_versions.py`, Zeilen 17–19) sagen „A running job is not updated while Docling converts“. Seit 048 schreibt `poll` aber bei jeder Abfrage `updated_at` (`pipeline.py`, Zeile 571 ff.). Die Empfehlung „mehr als `TWOX_INGEST_TIMEOUT_SECONDS`“ ist damit vorsichtiger als nötig, aber nicht falsch; das README nennt beides. Vorschlag: Docstring in einem späteren Auftrag anpassen.
5. **Ungereimtheit im Bericht 057 (nicht im Code):** 057 nennt ein leeres `docling_started_at` „schadlos, weil `TWOX_INGEST_TIMEOUT_SECONDS` als äußere Grenze bleibt“. Laut `_deadline_passed` (`pipeline.py`, Zeile 265 ff.) gibt es ohne `docling_started_at` gar keine Frist. Schadlos ist der Fall trotzdem, weil Docling dann schon fertig war. Als Grenze dokumentiert ist der andere Fall: Bleibt eine Docling-Aufgabe dauerhaft `pending`, hat der Auftrag keine Frist, und `--stuck` greift auch nicht, weil jede Abfrage `updated_at` schreibt.
6. **Zusätzlich dokumentiert** (über die Liste hinaus, weil sonst falsch): Routenliste und Favicon-Pfade in „Serving the web UI“, Teil `ai` im Selbsttest-Diagramm, `device_class` im ER-Diagramm, Speicher der Docling-Antworten unter „File storage“, `backend-dev`-Mounts von `manifest.yaml`/`questions.yaml`, Erweiterung `vector` braucht einen Superuser (040).
7. Für die lokalen Läufe lagen im `api`-Container kurz zwei Markdown-Dateien aus `testdata/klein/`, eine selbst geschriebene Textdatei und ein Hilfsskript unter `/tmp`; mit `down -v` entfernt. Ins Repository kam nichts davon. „2x“ und „twox-leit“ nicht berührt.

Keine offene Frage an a7.

### Nachbesserung aus der Prüfung der Leitstelle

1. **Client-Adresse im Zugriffsprotokoll:** Der Formatter `uvicorn_access` in `settings.py` schreibt `%(client_addr)s`. ARCHITECTURE („Logging“) sagt jetzt: Der Query-String wird entfernt, Methode, Pfad, Status und Client-Adresse (mit Port) bleiben, auch bei fehlgeschlagener Anmeldung. Ob die Adresse entfernt wird, ist offen bei a7 (Stufe C). Im README sagt „Rate limit of the sign-in“ nur noch, dass die Meldung des Anmelde-Adapters keine Adresse enthält, und nennt die Adresse im Zugriffsprotokoll als bekannte Grenze, offen bei a7. Unter „Search texts“ steht dazu ein Halbsatz.
2. **Kleinere Ungenauigkeiten:**
   - Wartezeit bei gestopptem Docling: 10 + 20 + 40 + 60 + 60 = 190 s statt „etwa 2,5 min“.
   - BetrSichV: 258 s in Docling, 292 s für den ganzen Auftrag (046/057) statt „about 5 minutes“.
   - `embed_sections` im Fließtext von README und ARCHITECTURE mit `--user`; `ingest_versions --failed` dort ebenfalls mit `--user` und `--commit`.
3. **Prüfungen:** `git diff --check` ohne Befund, `gitleaks-dir` ohne Fund (Exit 0). Nur Doku geändert.
