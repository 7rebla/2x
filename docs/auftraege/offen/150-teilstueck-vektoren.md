# Auftrag 150 – Teilstücke mit eigenen Vektoren

Meilenstein: M3 · Freigabestufe: C (freigegeben mit E-75) · Status: offen

Voraussetzung: 149 (Vektorliste zählt Inhalte statt Zeilen) liegt auf `main`.

## Ziel

Diagnose 147 (`docs/auftraege/erledigt/147-diagnose-vektorsuche.md`, Variante V4a): Lange Abschnitte (bis `TWOX_SECTION_MAX_CHARS` = 2 000 Zeichen) verwässern den Vektor. Wird jeder Abschnitt in Teilstücke ≤ 1 000 Zeichen geteilt (an Leerzeichen, ohne Überlappung, vor jedem Teilstück der Überschriftenpfad wie in `embedding_text`, `backend/twox/ingest/pipeline.py:752`) und bekommt ein Abschnitt den kleinsten Abstand seiner Teilstücke, steigt Recall@8 kombiniert von 8/13 auf 11/13; die Kontrollfrage bleibt bei 0,510.

Nach diesem Auftrag sucht die Vektorsuche über Teilstück-Vektoren. Quelle, Kontext- und Zitiereinheit bleibt der Abschnitt (E-75).

## Umfang

1. **Datenmodell** (`backend/twox/ingest/models.py`, neue Migration): neue Tabelle für Teilstücke eines Abschnitts – Verweis auf den Abschnitt (Löschen mit dem Abschnitt), Ordnungszahl, Beginn und Ende im Abschnittstext (Zeichen), `embedding` (vector, Dimension wie `Section.embedding`), `embedding_model`; HNSW-Index wie bei `Section`. Der Text wird nicht doppelt gespeichert, sondern aus dem Abschnitt geschnitten. `Section.embedding` bleibt bestehen und wird weiter befüllt, solange es noch einen Aufrufer gibt (z. B. Zusammenlegen von Sprachfassungen); der Bericht nennt alle Aufrufer und ob sie umgestellt werden.
2. **Teilen:** eine reine Funktion, die einen Abschnittstext in Teilstücke ≤ `TWOX_PIECE_MAX_CHARS` (neue Einstellung, Standard 1 000, in `settings.py` und `.env.example`) teilt – an Leerzeichen, ohne Überlappung, ein Wort länger als die Grenze wird hart geteilt; kurze Abschnitte ergeben genau ein Teilstück. Eingebettet wird `embedding_text(heading_text, teilstück)`.
3. **Einbetten im Worker:** Der Schritt `embed` (`pipeline.py`, `_embed`, `_embed_batch`) bettet die Teilstücke ein (Bündel wie heute, Pausieren nach `should_pause`). „Braucht Einbettung“ gilt, solange ein Teilstück ohne Vektor des aktuellen Modells fehlt. Bestehende Abschnitte: ein Weg, alles neu einzubetten, ohne neu einzulesen und ohne Docling (vorhandenen Befehl/Ablauf erweitern, z. B. `embed_sections`, oder Migration + Einbettungsaufträge); der Bericht nennt den genauen Befehl für die Leitstelle in „2x“.
4. **Vektorsuche** (`backend/twox/search/postgres.py`): nächste Teilstücke per HNSW, je Abschnitt kleinster Abstand, dann wie nach 149 Kopien zusammenfassen und auf `VECTOR_CANDIDATES` Inhalte begrenzen. `semantic_distance` eines Treffers ist der kleinste Teilstück-Abstand. Eingrenzen und Ausschlüsse wie heute. Ohne Teilstück-Vektoren (z. B. vor der Neueinbettung) verhält sich die Suche wie ohne Vektor – oder fällt auf `Section.embedding` zurück; begründet im Bericht.
5. **Tests:** Teilen (Grenzen, lange Wörter, kurzer Abschnitt, Unicode); Einbetten (Teilstücke entstehen, Pausieren, Modellwechsel); Migration; Vektorsuche (Abschnitt mit einem nahen Teilstück gewinnt gegen einen mit mittlerem Gesamtvektor; Kopien; Eingrenzen; Ausschlüsse; Zählung der Inhalte wie in 149); Kontextauswahl unverändert über den Abschnitt; Neueinbettung bestehender Abschnitte.
6. **CI-Aufzeichnungen:** werden sie rot, neu aufnehmen mit `gemma4:31b-it-qat` nach `backend/tests/answers/recorded/README.md` (vorher `/api/ps` leer); nichts aufweichen.
7. **Doku:** `docs/ARCHITECTURE.md` (Datenmodell, Einlesen, Suche), README (neue Einstellung, Neueinbettung), Docstrings.

## Nicht-Ziele

- Keine Änderung an Schwelle, k, Zeichenbudget, Prompt, Zitatprüfung, Stichwortsuche oder Fusion.
- Keine Übersetzung der Frage (E-75: erst nach Messlauf).
- Kein neues Modell, keine neue Abhängigkeit.
- Keine Neueinbettung in „2x“ (macht die Leitstelle nach dem Zusammenführen).

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/ingest/` (models, Migration, pipeline, ggf. Befehl), `backend/twox/search/postgres.py`, `backend/twox/config/settings.py`, `.env.example`
- `backend/tests/ingest/`, `backend/tests/search/`, ggf. `backend/tests/answers/recorded/ci_questions.json`
- `docs/ARCHITECTURE.md`, `README.md`
- diese Auftragsdatei

## Akzeptanzkriterien (prüfbar)

1. Tests aus Umfang 5 vorhanden und grün; bestehende Tests grün (geänderte Erwartungen einzeln begründet).
2. CI wie `ci.yml` grün: backend (inkl. `pytest -m worker` mit laufendem `worker`, `makemigrations --check`), web, testfactory, e2e.
3. Migration läuft auf einer Datenbank mit vorhandenen Abschnitten ohne Datenverlust; `Section`-Daten unverändert.
4. Laufzeit der Vektorabfrage an selbst erzeugten Daten (≈ 6 500 Teilstücke, viele Kopien) und `EXPLAIN` (HNSW genutzt) im Bericht.
5. Der Bericht nennt den Befehl zur Neueinbettung in „2x“, die erwartete Dauer und wie man prüft, dass alle Teilstücke einen Vektor haben.
6. Diff nur in den genannten Bereichen, keine neue Abhängigkeit, Compose-Projekte mit `down -v` entfernt.

## Vorgaben und Hinweise

- Compose-Projekt `twox-150`, `TWOX_API_PORT=18150`. `docker` liegt nicht im PATH: `%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin`.
- Für Tests mit Vektoren die vorhandenen Ersatz-Einbetter der Tests verwenden; Ollama nur für die Neuaufnahme der CI-Aufzeichnungen.
- Nutzereingaben nur als Parameter ins SQL.
- Nicht pushen.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine vor dem Start (E-75). Ergibt sich eine Abweichung vom Datenmodell oben, Frage hier eintragen und Status „wartet auf a7“.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
