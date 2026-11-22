# Auftrag 059 – README und ARCHITECTURE für M2

Meilenstein: M2 · Freigabestufe: B · Status: offen

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

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
