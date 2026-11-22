# Auftrag 050 – Vektorsuche und Kombination mit der Stichwortsuche

Meilenstein: M2 · Freigabestufe: B · Status: zur Prüfung

## Ziel

Die PostgreSQL-Suche findet auch sinngemäß gestellte Fragen: Die Anfrage wird über die Modell-Schnittstelle eingebettet, per Kosinus-Abstand mit den Abschnitten verglichen und mit der Stichwortsuche in einer Rangliste zusammengeführt (Reciprocal Rank Fusion). Ist das Modell nicht erreichbar, sucht sie nur nach Stichworten und sagt das im Ergebnis.

## Umfang

- `backend/twox/search/postgres.py`:
  - Anfrage mit `embed_query` einbetten (Vorsatz `TWOX_EMBED_QUERY_PREFIX`).
  - Die 50 nächsten Abschnitte nach `CosineDistance`, mit denselben Regeln wie in 047 (Versionsregel, Art `document`, Gerät, Anlage) und nur Abschnitte, deren `embedding_model` dem aktuellen Modell entspricht.
  - Für gefilterte Abfragen `SET LOCAL hnsw.iterative_scan = relaxed_order` und ein passender Wert für `hnsw.ef_search` in derselben Transaktion; Werte im Kurzbericht.
  - Zusammenführung: je Liste der Rang (Stichwort nach `ts_rank`, Vektor nach Abstand); Wert je Abschnitt ist die Summe aus `1/(k + Rang)` mit `k = 60`; exakte Kennungs-Treffer aus 047 bleiben vorne; `match_kinds` nennt `semantic` bei Herkunft aus der Vektorliste. Das Zusammenfassen gleicher Inhalte (047) gilt nach der Zusammenführung.
  - `EmbeddingUnavailableError`, `EmbeddingRejectedError` oder `EmbeddingRemoteModelError`: nur Stichwort, `semantic_used = False`, Eintrag im Server-Protokoll ohne Anfragetext.
- **Tests** (`backend/tests/search/test_vector_search.py`, `test_fusion.py`) mit einer Attrappe von `Embedder`, die selbst gebaute Vektoren mit 1 024 Werten liefert:
  - Eine Frage ohne gemeinsame Wörter findet den passenden Abschnitt nur über den Vektor.
  - Die Reihenfolge der Zusammenführung stimmt an einem kleinen, im Test von Hand gerechneten Beispiel.
  - Exakte Treffer bleiben oben.
  - Ausfall des Modells ergibt nur Stichwort-Treffer und `semantic_used = False`.
  - Abschnitte ohne Einbettung oder mit anderem Modell kommen nur über das Stichwort.
  - Filter und Versionsregel wirken in beiden Listen; gleicher Inhalt bei zwei Geräten bleibt ein Treffer.

## Nicht-Ziele

- Keine API (052), keine Gewichtung über einen Schalter, kein Reranker, keine Antwort mit Sprachmodell (M3).
- Kein Lauf mit echten Handbüchern (057).

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/search/postgres.py`
- neu: `backend/tests/search/test_vector_search.py`, `backend/tests/search/test_fusion.py`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-050`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18050` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Tests:
   - `D run --rm backend-dev pytest tests/search -v` endet mit Exit-Code 0.
   - `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen.
   - `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
3. `D run --rm backend-dev ruff check .` meldet `All checks passed!`, `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0, `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
4. Weitere Prüfungen wie in `ci.yml`, jeweils ohne Unterschied zum eingecheckten Stand:
   - `D run --rm backend-dev python manage.py makemessages -l de --add-location=file`, danach `git diff --exit-code -I '^"POT-Creation-Date:' -- backend/locale`;
   - `D run --rm backend-dev python manage.py makemigrations --check --dry-run` endet mit Exit-Code 0;
   - `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0;
   - `D run --rm -v "$PWD/web/openapi:/out" backend-dev python manage.py spectacular --file /out/schema.yml` (unter Git Bash mit vorangestelltem `MSYS_NO_PATHCONV=1`), danach `git diff --exit-code -- web/openapi`.
5. Der Kurzbericht enthält den Abfrageplan (`EXPLAIN ANALYZE`) einer Vektorsuche mit Gerätefilter über 10 000 Testabschnitte nach `ANALYZE`, ohne Erzwingen über `enable_seqscan=off`. Nutzt der Planer den HNSW-Index nicht, gilt der Plan mit Begründung ebenfalls als Ergebnis.
6. Abräumen: `D --profile dev down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

- **Nachtrag der Leitstelle (E-59, KI optional):** Einbettungen, Vektorsuche und alles, was ein Modell braucht, sind eine aktivierbare Zusatzfunktion. Schalter `TWOX_AI_ENABLED` (Einstellung in `settings.py`, Standard `False`; `.env.example` mit Kommentar). Bei „aus“: kein Aufruf von Ollama, keine Einbettungs-Aufgaben, Einlesen endet nach den Abschnitten erfolgreich, die Suche arbeitet nur mit der Stichwortsuche, Selbsttest und Oberfläche zeigen „KI nicht aktiviert“ als neutralen Zustand (kein Fehler, kein Warnsymbol). Jede KI-abhängige Stelle braucht einen Test für beide Zustände; die CI läuft mit „aus“ und mit „an“ plus Attrappe.

Voraussetzung: 044 und 047 sind nach `main` zusammengeführt.

- Welle 4, parallel zu 046.
- **Keine neue Abhängigkeit.**
- `k = 60` ist der übliche Wert (Cormack u. a. 2009; nicht an der Quelle geprüft). Der Messlauf 057 prüft ihn mit.
- `hnsw.iterative_scan` (seit pgvector 0.8.0) und `hnsw.ef_search` (Vorgabe 40): Namen und Werte an der laufenden Version 0.8.7 prüfen.
- Anfragetexte nicht ins Protokoll schreiben.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Läufe am 22.11.2026 im Container, Projekt `twox-050`, Port 18050, Docker Engine 29.9.3, Compose v5.7.0, pgvector 0.8.7. Kriterien 0 bis 6 erfüllt. Keine neue Abhängigkeit, keine Migration, `interface.py` (auch `HitLocation`), `settings.py`, `compose.yaml` und `.env.example` unverändert. Keine offene Frage an a7.

### Was wurde gebaut?

- `backend/twox/search/postgres.py`:
  - **Einbetten der Anfrage** (`embed_query`): nur bei `TWOX_AI_ENABLED`; sonst wird `get_embedder()` gar nicht aufgerufen. Über `twox.answers.embeddings.get_embedder().embed_query(...)`, also mit `TWOX_EMBED_QUERY_PREFIX` (setzt der Client aus 044). Das Einbetten läuft außerhalb eines Datenbank-Cursors.
  - **Vektorliste** (`vector_sql`, `nearest_sections`): dieselben CTEs `latest`/`searchable` wie die Stichwortsuche (jetzt gemeinsam in `_scope_sql`), also Art `document`, Versionsregel, Gerät, Anlage. Bedingung `embedding_model = <Modell des Embedders>` und `embedding IS NOT NULL`. `ORDER BY s.embedding <=> %(embedding)s::vector LIMIT 50` als `MATERIALIZED`-CTE, danach erneut nach Abstand sortiert (wegen `relaxed_order`). Rang per `DENSE_RANK()` nach Abstand. Der Operator `<=>` ist der, den `CosineDistance` von pgvector erzeugt; die Suche ist durchgehend SQL (wie in 047), deshalb kein ORM-Ausdruck.
  - **HNSW-Einstellungen:** in einer eigenen Transaktion (`transaction.atomic()`, in einer äußeren Transaktion ein Savepoint) vor der Vektorabfrage `set_config('hnsw.iterative_scan', 'relaxed_order', true)` und `set_config('hnsw.ef_search', '100', true)`. `set_config(…, true)` ist die Funktionsform von `SET LOCAL` und nimmt Parameter. Werte: `iterative_scan = relaxed_order`, `ef_search = 100` (Vorgabe 40 liegt unter der Listenlänge 50; Faustwert 2 × 50). An der laufenden Version geprüft (`pg_settings`): `hnsw.ef_search` (40), `hnsw.iterative_scan` (`off`, Werte `off`, `relaxed_order`, `strict_order`), `hnsw.max_scan_tuples` (20 000), `hnsw.scan_mem_multiplier` (1). Nach dem Ende der Transaktion gelten wieder 40 und `off` (Test).
  - **Zusammenführung (RRF):** `score = Zahl der exakten Kennungen + 1/(60 + Rang Stichwort) + 1/(60 + Rang Vektor)`; fehlt ein Abschnitt in einer Liste, fällt der Teil weg. Stichwortrang nach `ts_rank` (wie 047, Normierung 32), Vektorrang nach Abstand. Der RRF-Teil ist höchstens 2/61 < 1, exakte Treffer bleiben also vorne. Das Zusammenfassen gleicher Inhalte (047) kommt nach der Zusammenführung (Gruppe bekommt den besten Wert, `match_kinds` aus allen Abschnitten der Gruppe). Die Abschnitts-IDs und Ränge der Vektorliste gehen als Arrays in die Suchabfrage; die Bedingung `s.id = ANY(…)` steht mit im `OR`, damit der Planer weiter Index-Bedingungen verknüpfen kann.
  - **`match_kinds`** in der Reihenfolge `exact`, `keyword`, `semantic`; `semantic` bei Herkunft aus der Vektorliste.
  - **Ausfall:** jede `EmbeddingError` außer `EmbeddingDisabledError` (also Unavailable, Rejected, RemoteModel und zusätzlich Dimension) sowie ein Vektor mit anderer Länge als die Spalte (1024) → nur Stichwort und exakt, `semantic_used = False`, eine Zeile WARNING im Logger `twox.search.postgres` mit Fehlerart und Meldung des Clients (ohne Anfragetext, ohne Adresse, siehe 044). `semantic_used = True`, sobald die Vektorabfrage lief, auch wenn sie nichts fand.
  - Bei KI aus: genau wie 047 (drei Abfragen), kein Aufruf des Embedders, keine Protokollzeile.
- Tests (alle Texte selbst geschrieben):
  - `backend/tests/search/fake_embedder.py` (neu): Attrappe `FakeEmbedder` mit Vektoren aus 1 024 Werten. Die Anfrage zeigt entlang der ersten Achse, ein Abschnitt im Winkel θ hat den Kosinus-Abstand 1 − cos θ; die Reihenfolge der Vektorliste steht damit fest.
  - `backend/tests/search/conftest.py` (neu): schaltet in allen Suchtests KI aus und setzt `TWOX_LLM_BASE_URL` auf einen geschlossenen Port im Container (`127.0.0.1:9`). Grund: In den Containern ist `TWOX_AI_ENABLED=true` aus `.env.example`; jeder Test setzt seinen Zustand selbst. So erreicht kein Test ein echtes Ollama.
  - `backend/tests/search/test_fusion.py` (neu, 7 Fälle): Rechenbeispiel von Hand (siehe unten), exakte Treffer oben, Zusammenfassen nach der Zusammenführung mit gleichem Rang für gleiche Werte, nur Vektorrang, Schalter an/aus.
  - `backend/tests/search/test_vector_search.py` (neu, 21 Fälle): Frage ohne gemeinsame Wörter nur über den Vektor (mit KI aus: kein Treffer); 50 nächste Abschnitte; der echte Client aus 044 gegen die HTTP-Attrappe aus 044 (Vorsatz `query: ` kommt an, Modell `bge-m3`); Ausfall je Fehlerart (Unavailable, Rejected, RemoteModel, Dimension) mit Protokollzeile ohne Anfragetext; echter Client gegen geschlossenen Port (Verbindung abgelehnt); falsche Vektorlänge; KI aus ruft `get_embedder` nie auf und protokolliert nichts; Abschnitte ohne Einbettung bzw. mit anderem Modell nur über Stichwort; Gerät, Anlage, beide; Art `configuration`; Versionsregel (neuere Version mit Abschnitten ohne Einbettung verdrängt die ältere auch aus der Vektorliste; ältere Version über den Vektor mit `is_latest_version = false`, wenn die neuere keine Abschnitte hat); gleicher Inhalt bei zwei Geräten ein Treffer, mit Gerätefilter ein Fundort; HNSW-Einstellungen vor der Vektorabfrage und nach der Transaktion zurück; Kosinus-Abstand; Textform des Vektors; Zahl der Abfragen mit KI an.
  - `backend/tests/search/test_keyword_search.py`: der Test „mit und ohne KI“ nutzt für „an“ jetzt die Attrappe und erwartet `semantic_used = True` (vorher fest `False`, weil 047 keine Vektorsuche hatte).

**Rechenbeispiel (Test `test_fusion_order_worked_out_by_hand`), k = 60:** Stichwortränge A 1, B 2, C 3 (D enthält das Wort nicht); Vektorränge C 1, D 2, B 3, A 4.

| Abschnitt | Rechnung | Wert |
| --- | --- | --- |
| C | 1/63 + 1/61 | 0,032266 |
| A | 1/61 + 1/64 | 0,032018 |
| B | 1/62 + 1/63 | 0,032002 |
| D | 1/62 | 0,016129 |

Erwartete und gefundene Reihenfolge: C, A, B, D. Mit KI aus bleibt A, B, C (Werte 1/61, 1/62, 1/63).

### Wie wurde getestet?

`D` = `docker compose -p twox-050`, `.env` aus `.env.example` (ohne BOM, mit dem Write-Werkzeug) mit `TWOX_API_PORT=18050`. Kriterien 1 bis 4 auf dem committeten Code-Stand. „2x“ und „twox-leit“ nicht angefasst.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | Engine 29.9.3, Compose v5.7.0, Exit 0 |
| 1 | erfüllt | Bau Exit 0; `up -d --wait …` Exit 0, db, valkey, api, worker Healthy |
| 2 | erfüllt | `pytest tests/search -v`: `199 passed`; `pytest -rs`: `1712 passed, 4 deselected`, nichts übersprungen; `pytest -m worker`: `4 passed, 1712 deselected` |
| 3 | erfüllt | `All checks passed!`; `161 files already formatted`; `Success: no issues found in 160 source files` |
| 4 | erfüllt | `makemessages` ohne Unterschied in `backend/locale` (`git status` leer); `No changes detected`; `License check passed.`; `spectacular` Exit 0, ohne Unterschied in `web/openapi` |
| 5 | erfüllt (Planer nutzt HNSW bei 10 000 Abschnitten nicht, Begründung unten) | Plan unten |
| 6 | erfüllt | `D --profile dev down -v` Exit 0; keine Container und Volumes `twox-050*` mehr |

**Abfrageplan (Kriterium 5).** 10 000 Abschnitte (100 Geräte mit je einem Dokument, je 100 Abschnitte mit 60 zufälligen Wörtern und einem zufälligen Einheitsvektor aus 1 024 Werten, `embedding_model = bge-m3`) per Skript außerhalb des Repositorys in die Entwicklungsdatenbank geschrieben, danach `ANALYZE`. Abfrage ist `vector_sql` des Backends mit Gerätefilter (ein Gerät), in derselben Transaktion nach `set_config` (`relaxed_order`, `ef_search` 100), `enable_seqscan = on`, `EXPLAIN (ANALYZE, BUFFERS)`. Gekürzt (Anfragevektor durch `<v>` ersetzt, Unterbaum von `searchable` zusammengefasst):

```
Incremental Sort  (cost=211.68..215.61 rows=50) (actual time=0.880..0.895 rows=50.00 loops=1)
  Sort Key: nearest.distance, nearest.id
  CTE nearest
    ->  Limit  (cost=211.48..211.61 rows=50) (actual time=0.850..0.857 rows=50.00 loops=1)
          ->  Sort  (cost=211.48..211.73 rows=100) (actual time=0.850..0.854 rows=50.00 loops=1)
                Sort Key: ((s.embedding <=> '<v>'::vector))
                Sort Method: quicksort  Memory: 28kB
                ->  Nested Loop  (cost=18.15..208.16 rows=100) (actual time=0.114..0.837 rows=100.00 loops=1)
                      ->  HashAggregate  (rows=1)  Group Key: v.id   -- searchable: 1 Version
                            ->  … Seq Scan on files_document d  Filter: ((device_id = ANY ('{43}'::smallint[])) AND ((kind)::text = 'document'::text))
                      ->  Index Scan using ingest_section_version_ordinal_unique on ingest_section s  (cost=0.29..189.03 rows=100) (actual time=0.003..0.033 rows=100.00 loops=1)
                            Index Cond: (document_version_id = v.id)
                            Filter: ((embedding IS NOT NULL) AND ((embedding_model)::text = 'bge-m3'::text))
  ->  WindowAgg  (actual time=0.854..0.880 rows=50.00 loops=1)
        Window: w1 AS (ORDER BY nearest.distance ROWS UNBOUNDED PRECEDING)
        ->  CTE Scan on nearest  (rows=50.00)
Planning Time: 0.945 ms
Execution Time: 0.954 ms
```

Ergebnis: 50 Zeilen, Trefferquote gegen die exakte Suche (Sortierung ohne Index) 50/50.

**Begründung, warum der HNSW-Index hier nicht genutzt wird:**

- Mit Gerätefilter grenzt der Planer über den B-Baum `(document_version_id, ordinal)` auf die 100 Abschnitte des Geräts ein und sortiert sie. Das ist exakt (keine Näherung) und dauert unter 1 ms; HNSW wäre hier schlechter.
- Ohne Filter (gleiche Daten) wählt der Planer `Seq Scan` + `top-N heapsort` über 10 000 Abschnitte: 64 ms, Trefferquote 50/50. Schon die nackte Abfrage `SELECT id FROM ingest_section ORDER BY embedding <=> '<v>' LIMIT 50` läuft als Seq Scan (37 ms): pgvector schätzt den HNSW-Scan auf Startkosten 4 373 gegen 2 124 für Seq Scan + Sortierung. Bei 10 000 Zeilen ist das die Kostenschätzung von pgvector, nicht die Form der Abfrage. Mit wachsender Tabelle steigen die Kosten des Seq Scan linear, die des HNSW-Scans kaum.
- Nur zur Diagnose (nicht als Ergebnis) mit `enable_seqscan = off`: Die Abfrage ohne Filter läuft dann als `Nested Loop Semi Join` über `Index Scan using ingest_section_embedding_hnsw … Order By: (embedding <=> '<v>')` in 10,7 ms; die Form `IN (SELECT version_id FROM searchable)` lässt den HNSW-Weg also zu. Eine Variante mit `= ANY(ARRAY(SELECT …))` habe ich verworfen: Dort wählt der Planer auch ohne Seq Scan den B-Baum über alle Versionen (36 ms) statt HNSW.
- In dieser Diagnose fand HNSW nur 26 der 50 exakten Nachbarn. Zufällige Vektoren mit 1 024 Werten sind für HNSW der ungünstigste Fall (alle Abstände fast gleich); für echte Einbettungen misst 057 die Trefferquote. Falls sie dort schwach ist, sind `HNSW_EF_SEARCH` und die Indexparameter die Stellschrauben.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-acd1d0dbf1b9d377a`
- Arbeitsverzeichnis: `.claude/worktrees/agent-acd1d0dbf1b9d377a` (relativ zum Projektordner)
- Commits: `Add the vector search and fuse it with the keyword search (RRF)`, `Test the vector search and the fusion with a stand-in embedder`, dazu dieser Kurzbericht. Nicht gepusht, nichts zusammengeführt.

### Abweichungen und Hinweise

1. **Dateien außerhalb der genannten:** `backend/tests/search/conftest.py` und `backend/tests/search/fake_embedder.py` (neu, gemeinsame Attrappe und Grundzustand „KI aus“) sowie ein Test in `test_keyword_search.py` (siehe oben). Die neuen Tests holen die Hilfsfunktionen (`add_sections`, `make_document` …) aus `test_keyword_search.py`, statt sie zu kopieren.
2. **Gleicher Wert, gleicher Rang (`DENSE_RANK`)** in beiden Listen, nicht fortlaufend nummeriert. Sonst belegt gleicher Inhalt bei mehreren Geräten mehrere Ränge und schiebt andere Abschnitte nach hinten (Test `test_same_content_is_merged_after_the_fusion`). Die Vektorliste zählt trotzdem 50 Abschnitte, nicht 50 verschiedene Inhalte.
3. **Auch `EmbeddingDimensionError` und eine falsche Vektorlänge** führen zur Stichwortsuche (statt zu einem Fehler 500); der Auftrag nennt nur drei Fehlerarten.
4. **`set_config(…, true)` statt `SET LOCAL`**: gleiche Wirkung, aber als eine parametrisierte Abfrage.
5. **Keine Hervorhebungen bei reinen Vektortreffern.** `ts_headline` markiert sonst einzelne Wörter der Frage wie „the“; der Ausschnitt beginnt dann am Textanfang. Die Abfrage für die Hervorhebungen läuft nur für Stichworttreffer (gibt es keine, entfällt sie).
6. **Anfrage ohne Wort und ohne Kennung** (nur Stoppwörter oder Sonderzeichen) ergibt wie in 047 ein leeres Ergebnis, ohne das Modell zu fragen.
7. **Zahl der Abfragen** mit KI an: fünf (Anfrage zerlegen, HNSW-Einstellungen, Vektorliste, Suche, Hervorhebungen) plus Savepoint/Release; mit KI aus unverändert drei.
8. **Zeitgrenze:** Das Einbetten der Anfrage nutzt `TWOX_EMBED_TIMEOUT_SECONDS` (Vorgabe 120 s, für das Einlesen gedacht). Antwortet Ollama gar nicht, wartet eine Suche so lange, bevor sie auf Stichworte zurückfällt; eine abgelehnte Verbindung fällt sofort zurück. Vorschlag für 052 oder später: eigene, kurze Zeitgrenze für Suchanfragen (Einstellung in `settings.py`, hier gesperrt).
9. **Für 052:** Ausschlüsse (`-pumpe`) wirken nur auf die Stichwortliste; ein Abschnitt mit dem ausgeschlossenen Wort kann über den Vektor kommen. Gehört zu den Ausschlüssen, die 052 ohnehin anfasst.
10. **Für 056:** Die Auswertung „Stichwort, Vektor, zusammen“ braucht einen Weg, nur eine Liste zu befragen. `vector_sql`/`nearest_sections` und `embed_query` sind dafür öffentlich; eine Umschaltung im Backend gibt es nicht (Nicht-Ziel „keine Gewichtung über einen Schalter“).
11. `README.md` und `docs/ARCHITECTURE.md` sind nicht nachgezogen; die Regeln stehen im Modul-Docstring, die Doku folgt mit 059.
12. Lokal bleiben die Images `twox-050-*`; die ignorierte `.env` hat `TWOX_API_PORT=18050`.
