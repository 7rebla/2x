# Auftrag 150 – Teilstücke mit eigenen Vektoren

Meilenstein: M3 · Freigabestufe: C (freigegeben mit E-75) · Status: erledigt

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

### Was wurde gebaut?

**Datenmodell** (`backend/twox/ingest/models.py`, Migration `ingest.0004_sectionpiece`):

- Neue Tabelle `ingest_sectionpiece` (`SectionPiece`): `section` (FK, `CASCADE`), `ordinal`, `char_start`, `char_end` (Code-Points in `Section.text`), `embedding` (vector 1024, nicht leer), `embedding_model` (nicht leer).
- Constraints: eindeutig `(section, ordinal)`, `char_end >= char_start`, Modellname nicht leer. HNSW-Index `vector_cosine_ops` wie bei `Section`.
- Der Text wird nicht gespeichert: `Section.piece_text(piece)` schneidet ihn aus dem Abschnitt.
- Teilstücke gibt es nur mit Vektor. Der Einbettungsschritt schreibt alle Teilstücke eines Abschnitts in einer Transaktion.
- Die Migration legt nur die leere Tabelle an; `Section` bleibt unverändert.
- `CASCADE` ist in Django emuliert (die Datenbankvariante `DB_CASCADE` lehnt Django ab, weil `Section` Python-Varianten nutzt). Deshalb löscht `_finish` die alten Abschnitte jetzt mit `.only("pk")`, damit Django nicht alle Texte und Vektoren lädt.

**Teilen** (`backend/twox/ingest/pieces.py`, `split_pieces`): reine Funktion.

- Text ≤ Grenze ergibt genau ein Teilstück `(0, len)`, auch leer.
- Längere Texte werden an Leerraum geteilt, jedes Stück so lang wie möglich, ohne Überlappung. Leerraum zwischen Stücken gehört zu keinem.
- Ein Wort länger als die Grenze wird hart geteilt.
- Grenze: neue Einstellung `TWOX_PIECE_MAX_CHARS` (Standard 1 000) in `settings.py` und `.env.example`.

**Einbetten** (`pipeline.py`, `_embed`, `_SectionWork`, `_batch_work`, `_embed_batch`, `_copy_pieces`):

- Eingebettet wird `embedding_text(heading_text, teilstück)`.
- Ein Abschnitt aus einem Teilstück (ganzer Text) gibt dem Teilstück seinen eigenen Abschnittsvektor. Der eingebettete Text ist identisch, also gibt es keine zusätzliche Anfrage.
- Ein langer Abschnitt schickt den Abschnitt (falls nötig) und jedes Teilstück.
- Je Anfrage höchstens `TWOX_EMBED_BATCH_SIZE` Texte. Ein Abschnitt mit mehr Texten geht in mehreren Anfragen hinaus und wird erst geschrieben, wenn alle Vektoren da sind.
- Pausieren nach `should_pause` wie bisher, zwischen den Bündeln.
- `needs_embedding(model)` gilt, wenn der Abschnittsvektor des Modells fehlt, kein Teilstück des Modells existiert oder noch ein Teilstück eines anderen Modells da ist. Teilstücke anderer Modelle löscht der Schritt am Anfang.
- Teilstücke gleicher Inhalte (gleiche SHA-256, Ordnungszahl, Überschrift, Text) werden wie die Abschnittsvektoren übernommen (`_copy_pieces`, ein `INSERT … SELECT` mit Parametern).

**Neueinbettung bestehender Abschnitte:** Der Befehl `embed_sections` wurde erweitert.

- `--missing` (Standard) nimmt jetzt auch Abschnitte ohne Teilstücke des aktuellen Modells. Nach der Migration ist das jede Version.
- Die Abschnittsvektoren bleiben. Das Modell wird nur für die Teilstücke von Abschnitten über 1 000 Zeichen gefragt.
- `--all` löscht zusätzlich die Teilstücke.
- Docling wird nicht gebraucht, und es wird nicht neu eingelesen.

**Vektorsuche** (`backend/twox/search/postgres.py`, `vector_sql`):

- `indexed_pieces`: die `PIECE_CANDIDATES` (= 100) nächsten Teilstücke per HNSW.
- `indexed`: je Abschnitt der kleinste Abstand.
- `complete`, `nearest`, `contents` und `copies` wie nach 149. Der exakte Zweig (`every_piece`) misst alle Teilstücke im Bereich und gruppiert je Abschnitt.
- `semantic_distance` ist der kleinste Teilstück-Abstand.
- Eingrenzen und Ausschlüsse wirken auf den Abschnitt. Ein ausgeschlossenes Wort irgendwo im Abschnitt nimmt alle seine Teilstücke heraus.
- Kopien zählen nur mit Teilstücken des Modells.

**Ohne Teilstück-Vektoren** (vor der Neueinbettung) verhält sich die Suche wie ohne Vektor: Diese Abschnitte findet nur die Stichwortsuche. Es gibt keinen Rückfall auf `Section.embedding`. Gründe:

- Eine Liste mit Abständen ganzer Abschnitte und von Teilstücken wäre nicht vergleichbar. Ein gemischter Bestand während der Neueinbettung würde Treffer verzerren.
- Die Abfrage bleibt einfach (ein Index).
- Die Übergangszeit ist kurz (siehe Neueinbettung unten).
- Risiko: Bis die Neueinbettung durch ist, gibt es in „2x“ keine Antworten aus dem Modell (Schwelle ohne Abstand). Deshalb direkt nach dem Zusammenführen neu einbetten.

**Aufrufer von `Section.embedding`** (bleibt bestehen und wird weiter befüllt):

| Aufrufer | umgestellt? |
| --- | --- |
| `twox/answers/context.py` (Sprachfassungen zusammenlegen, E-61, Abstand zweier Abschnitte) | nein, liest weiter den Abschnittsvektor; deshalb wird er weiter geschrieben |
| `twox/search/postgres.py` (Vektorsuche) | ja, liest nur noch Teilstücke |
| `twox/ingest/pipeline.py` (Einbetten, Übernehmen gleicher Inhalte) | schreibt weiter, zusätzlich Teilstücke |
| `twox/ingest/management/commands/embed_sections.py` (Auswahl, `--all` leert) | erweitert um Teilstücke |
| `twox/ingest/admin.py` (Anzeige „hat Einbettung“, Filter) | nein, nur Anzeige |
| `twox/ingest/checks.py` (Länge der Vektorspalte) | nein; die Teilstück-Spalte hat dieselbe Länge |

**Doku:** `docs/ARCHITECTURE.md` (Datenmodell, Indizes, Einbetten, Suche, Einstellungstabelle, Betriebshinweise), README (Einstellung, Neueinbettung), Docstrings in `models.py`, `pieces.py`, `pipeline.py`, `embed_sections.py`, `postgres.py`, Migration.

### Wie wurde getestet?

Neue Tests:

- `tests/ingest/test_pieces.py`: Grenzen, Leerraum, lange Wörter, kurze und leere Abschnitte, Unicode (Umlaute, Zeichen außerhalb BMP, geschütztes Leerzeichen), 2 000 Zeichen ergeben 3 Stücke ohne Wortverlust, Standardwert.
- `tests/ingest/test_embed_pieces.py`:
  - Teilstücke entstehen; ein kurzer Abschnitt bekommt den Abschnittsvektor.
  - Bündelgrößen; ein Abschnitt verteilt auf mehrere Anfragen.
  - Überschriftenpfad vor jedem Teilstück.
  - Abschnitte von vor 150: nur lange Abschnitte fragen das Modell.
  - `needs_embedding`.
  - Modellwechsel; alte Teilstücke bei aktuellem Abschnittsvektor.
  - Pausieren lässt nur ganze Abschnitte zurück.
  - Ein Fehler hinterlässt keinen halb geschriebenen Abschnitt.
  - Gleicher Inhalt übernimmt Teilstücke; ein anderes Modell nicht.
  - Löschen der Abschnitte löscht die Teilstücke.
- `tests/ingest/test_migration_sectionpiece.py` (Kriterium 3): Migration 0003 → 0004 → 0003 auf einer Datenbank mit Abschnitten (mit und ohne Vektor). Alle Spalten von `ingest_section` (inkl. `search_vector`, `embedding` als Text) sind vorher, nachher und nach dem Zurückgehen gleich; HNSW-Index vorhanden; Tabelle danach wieder weg.
- `tests/ingest/test_embed_sections_command.py`: `--missing` nimmt Abschnitte ohne Teilstücke und bettet nur lange ein; `--all` löscht Teilstücke.
- `tests/search/test_vector_pieces.py`:
  - Ein Abschnitt mit einem nahen Teilstück (5°) schlägt einen mit mittlerem Gesamtvektor (20°), obwohl sein Abschnittsvektor bei 30° liegt.
  - Treffer mit kleinstem Teilstück-Abstand und ganzem Abschnittstext (Kontext und Zitat bleiben am Abschnitt).
  - Kopien: gleicher Rang und Abstand, alle Fundorte.
  - 60 Inhalte × 3 Teilstücke ergeben genau 50 Inhalte (Zählung wie 149).
  - Geräte- und Anlagenfilter; Ausschluss eines Worts im ersten Teilstück nimmt den Abschnitt heraus.
  - Teilstücke eines anderen Modells zählen nicht.
  - Ohne Teilstücke findet nur die Stichwortsuche.
  - Viele Teilstücke weniger Inhalte führen in den exakten Zweig.

Geänderte Erwartungen bestehender Tests, jede begründet:

- `tests/search/fake_embedder.py`, `embed()`: schreibt jetzt zusätzlich die Teilstücke (alle mit dem Abschnittsvektor), wie der Einbettungsschritt. Damit gelten die bisherigen Abstände in allen Such- und Antworttests unverändert. Neu ist `embed_pieces()`.
- `test_vector_contents.py` (2 Stellen) und `test_vector_search.py` (1 Stelle): Die Parameterlisten für direkt ausgeführtes `vector_sql` brauchen `piece_limit`. Im Test „ohne Einbettung bleibt draußen“ werden auch die Teilstücke gelöscht, weil die Suche jetzt Teilstücke liest.
- `test_embed.py` (2 Tests), `test_tasks_worker.py` (1 Test): Die Zahl der eingebetteten Texte ist jetzt Abschnitte plus Teilstücke langer Abschnitte (Helfer `texts_to_embed` in `fake_converter.py`). Vorher war sie gleich der Zahl der Abschnitte.
- `test_embed_sections_command.py`: Die Testdaten „eingebettet“ schreiben jetzt auch Teilstücke. Sonst zählen sie als fehlend.
- `tests/acceptance/test_m2.py` (außerhalb der genannten Bereiche, siehe Abweichungen): Der Ersatz-Einbetter legt die Frage jetzt auf das Teilstück mit den gesuchten Worten statt auf den Abschnittsvektor. Bei einem langen Abschnitt hat der Abschnittsvektor keinen Teilstück-Partner mehr.

### CI wie `ci.yml` (Compose-Projekt `twox-150`)

- backend:
  - ruff check, ruff format, mypy: ohne Befund.
  - `pytest` (voller Lauf, `-v`): 3592 bestanden, 1 übersprungen, darunter `tests/answers/test_ci_questions.py`.
  - Nach der letzten Änderung (`PIECE_CANDIDATES` 50 → 100) liefen `tests/search`, `tests/answers`, `tests/acceptance` und `tests/ingest` noch einmal: 2238 bestanden. Der eine Fehlschlag ist der reihenfolgeabhängige Test unter „Abweichungen“; er besteht in CI-Reihenfolge.
  - `pytest -m worker` mit laufendem `worker`: 6 bestanden.
  - `makemigrations --check`: „No changes detected“.
  - Übersetzungskatalog unverändert (keine neuen übersetzbaren Texte: das Modell ist nirgends sichtbar, deshalb ohne `gettext`).
  - Lizenzen „passed“; OpenAPI-Schema unverändert.
- **web: grün.** lint, typecheck, test, build, licenses; API-Client ohne Abweichung.
- **testfactory: grün.** ruff, format, mypy, Tests ohne Netz, Manifestprüfungen; `testfactory/extern` existiert nicht.
- **e2e: grün.** 102 bestanden, 2 übersprungen. Gelaufen mit `--env-file .env.example` wie in CI (ohne Chat-Modell) und dem Testkonto aus `.env.example`.
- **CI-Aufzeichnungen:** blieben grün. `ci_questions.json` wurde nicht neu aufgenommen, Ollama nicht benutzt (kein Aufruf, `/api/ps` deshalb nicht nötig).

### Laufzeit und EXPLAIN (Kriterium 4)

Selbst erzeugte Daten in der Entwicklungsdatenbank von `twox-150`, in einer Transaktion, die danach zurückgerollt wurde:

- 1024-dimensionale Zufallsvektoren; 5 000 Abschnitte, davon 30 % lang mit 2 Teilstücken.
- Gemessen wurden 5 Anfragen × 10 Wiederholungen; angegeben ist der Median von `nearest_sections_with_distance`.

| Datensatz | Teilstücke | `PIECE_CANDIDATES` = 50 | = 100 (gewählt) |
| --- | --- | --- | --- |
| Viele Kopien: 4 Handbücher × 50 Abschnitte × 20 Geräte + 10 × 100 Einzelabschnitte | ≈ 6 240–6 660 | 46 ms, exakter Zweig, 50 Inhalte | 54 ms, exakter Zweig, 50 Inhalte |
| Ohne Kopien: 10 × 500 Einzelabschnitte | ≈ 6 470–6 530 | 134 ms, exakter Zweig (50 Teilstücke < 50 Abschnitte), 50 Inhalte | **12 ms, nur HNSW**, 50 Inhalte |

`EXPLAIN (ANALYZE)` der gewählten Fassung:

- Ohne Kopien: `Index Scan using ingest_sectionpiece_hnsw` (100 Zeilen, ≈ 4 ms). Der exakte Zweig (`Seq Scan on ingest_sectionpiece`) steht als „never executed“ hinter dem One-Time Filter. Ausführung ≈ 9 ms.
- Mit Kopien: erst derselbe HNSW-Scan, dann `Seq Scan on ingest_sectionpiece` über alle ≈ 6 660 Teilstücke im exakten Zweig. Ausführung ≈ 53 ms.
- Deshalb `PIECE_CANDIDATES = 2 × VECTOR_CANDIDATES = 100` (= `HNSW_EF_SEARCH`, das unverändert bleibt).
- Vergleich 149 (Abschnittsvektoren, 5 000 Abschnitte): 7,6 ms ohne und 28,8 ms mit Kopien.

Messskript nur im Scratchpad, nicht im Repository.

### Neueinbettung in „2x“ (Kriterium 5, macht die Leitstelle)

Nach dem Zusammenführen und dem Neubau, sodass `migrate` die Migration `ingest.0004` ausführt:

```sh
docker compose -p 2x exec api python manage.py embed_sections --user <Konto mit Rolle manage>            # Trockenlauf
docker compose -p 2x exec api python manage.py embed_sections --user <Konto mit Rolle manage> --commit
```

- **Erwartete Dauer:** etwa 1 bis 3 Minuten, höchstens die ≈ 5 Minuten aus E-75. Herleitung:
  - Die Abschnittsvektoren bleiben. Das Modell wird nur für die Teilstücke von Abschnitten über 1 000 Zeichen gefragt.
  - 147 zählte 3 513 Teilstücke für 2 737 verschiedene Inhalte, also grob 800 bis 1 600 Texte.
  - 147 maß ≈ 22 Texte/s.
  - Kopien übernehmen die Teilstücke, sobald die erste Version fertig ist.
- **Prüfen, dass alle Teilstücke einen Vektor haben:**
  - Trockenlauf wiederholen. Er muss `versions: 0 jobs to create, 0 skipped` melden; eine noch laufende Version zählt als „skipped“.
  - Direkt zählen; Ergebnis muss `0` sein:
    ```sh
    docker compose -p 2x exec api python manage.py shell -c "from django.conf import settings; from twox.ingest.models import Section; from twox.ingest.pipeline import needs_embedding; print(Section.objects.filter(needs_embedding(settings.TWOX_EMBED_MODEL)).count())"
    ```
  - Teilstücke ohne Vektor kann es nicht geben (`embedding` ist NOT NULL).

### Zweig und Arbeitsverzeichnis

- Zweig `worktree-agent-a16523c3aea1585ef`
- Arbeitsverzeichnis `.claude/worktrees/agent-a16523c3aea1585ef`
- Basis `main` 12a43a0. Nicht gepusht.

### Abweichungen

- **`tests/acceptance/test_m2.py`** liegt außerhalb der genannten Bereiche. Geändert wurden drei Zeilen im Test „Frage in anderen Worten“: Der Ersatz-Einbetter legt die Frage jetzt auf das Teilstück mit den gesuchten Worten. Sonst wäre die CI rot, weil der Abschnittsvektor eines langen Abschnitts nicht mehr gesucht wird.
- **Teilstücke sind nicht übersetzt** (`verbose_name` ohne `gettext`), damit der Übersetzungskatalog unverändert bleibt. Das Modell ist weder in Admin noch API sichtbar.
- **`PIECE_CANDIDATES` = 100** statt 50, nach Messung (siehe oben). `HNSW_EF_SEARCH`, Schwelle, k und Zeichenbudget sind unverändert.
- **Kein Rückfall auf `Section.embedding`** (begründet oben).
- **Neueinbettung über `embed_sections --missing`.** Es gibt keinen neuen Befehl und keine Datenmigration mit Einbettungsaufträgen.
- **Eine geänderte `TWOX_PIECE_MAX_CHARS` erkennt `--missing` nicht**, weil die Größe nicht mit den Teilstücken gespeichert wird. Dafür gibt es `--all`; das ist in ARCHITECTURE und README beschrieben.
- **Beobachtungen, nicht eingegrenzt:**
  - Zwei Läufe mit `pytest -q`, Ausgabe durch eine Pipe, blieben in einem Test mit lokalem Ersatz-Server hängen (Prozess wartet in `futex`, keine DB-Verbindung offen).
  - Ein dritter Lauf derselben Verzeichnisse mit `-o faulthandler_timeout=90` lief ohne Hänger durch. Der volle Lauf mit `-v` in CI-Reihenfolge lief ebenfalls durch (3592 bestanden).
  - Der Test ließ sich deshalb nicht benennen. Ein Zusammenhang mit 150 ist nicht erkennbar; betroffen waren Läufe mit `tests/answers`.
- **Reihenfolgeabhängiger Test (bestehend):** Ruft man `tests/search` vor `tests/answers` auf, scheitert `tests/answers/test_api.py::test_no_database_connection_stays_open_after_the_stream` mit `Group.DoesNotExist`. Ursache ist ein Test mit `transaction=True` in `test_vector_search.py`, der die Gruppen leert. Die CI-Reihenfolge ist nicht betroffen; nicht Teil dieses Auftrags.

### Nacharbeit nach der Prüfung der Leitstelle

1. **`TWOX_PIECE_MAX_CHARS` in Compose:** Die Zeile `TWOX_PIECE_MAX_CHARS: ${TWOX_PIECE_MAX_CHARS:-}` steht jetzt neben `TWOX_SECTION_MAX_CHARS` in `deploy/compose/compose.yaml` (`x-backend-environment`); nur diese Zeile wurde geändert. `test_default_size_is_the_measured_one` prüft nur noch `DEFAULT_PIECE_MAX_CHARS == 1000`, damit ein abweichender `.env`-Wert ihn nicht rot macht.
2. **`docs/ARCHITECTURE.md`:**
   - „Deleting“ nennt `SectionPiece.section` als Ausnahme (`CASCADE`).
   - Im erDiagram stehen jetzt `SectionPiece` mit seinen Feldern und die Beziehung `Section ||--o{ SectionPiece`.
3. **Zwei gleichzeitige embed-Aufgaben:**
   - `_embed_batch` sperrt die Abschnitte des Bündels mit `select_for_update()` (in der Reihenfolge der IDs), bevor es Teilstücke löscht und einfügt. Ein zweiter Schreiber wartet und ersetzt danach den Satz des ersten als Ganzes.
   - `_copy_pieces` sperrt die Abschnitte der Version ebenso und hat zusätzlich `ON CONFLICT (section_id, ordinal) DO NOTHING`.
   - Tests in `tests/ingest/test_embed_pieces.py`:
     - Mit `transaction=True` hält ein erster Schreiber die Zeilensperre und schreibt Teilstücke; ein zweiter `embed` in einem eigenen Thread wartet nachweislich, endet `done` und hinterlässt genau einen gültigen Satz (Ordnungszahlen 0–2, richtige Spannen, aktuelles Modell).
     - Kopieren überspringt Abschnitte, die schon Teilstücke haben.
4. **Kontextauswahl:** neue Datei `tests/answers/test_context_pieces.py` (die Leitstelle hat sie angefordert; `tests/answers` lag nicht im ursprünglichen Bereich).
   - Ein langer Abschnitt mit nahem Teilstück (8°) und fernem Abschnittsvektor (80°) kommt als ganzer Abschnitt mit vollem Text in den Kontext; `best_distance` ist der Abstand des Teilstücks.
   - Umgekehrt (naher Abschnittsvektor, alle Teilstücke fern) greift die Schwelle: `below_threshold`.
   - Das Zusammenlegen der Sprachfassungen (E-61) folgt dem Abschnittsvektor: gleiche Abschnittsvektoren werden zusammengelegt, gleiche Teilstücke allein nicht.
5. **Prüfung:**
   - ruff, ruff format, mypy: ohne Befund.
   - `pytest` voll (`-v`): 3599 bestanden, 1 übersprungen.
   - `pytest -m worker` mit laufendem `worker`: 6 bestanden.
   - `makemigrations --check`: ohne Änderung; Übersetzungskatalog unverändert.
   - Compose-Projekt `twox-150` mit `down -v` entfernt.
