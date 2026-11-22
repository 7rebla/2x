# Auftrag 050 – Vektorsuche und Kombination mit der Stichwortsuche

Meilenstein: M2 · Freigabestufe: B · Status: offen

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

Voraussetzung: 044 und 047 sind nach `main` zusammengeführt.

- Welle 4, parallel zu 046.
- **Keine neue Abhängigkeit.**
- `k = 60` ist der übliche Wert (Cormack u. a. 2009; nicht an der Quelle geprüft). Der Messlauf 057 prüft ihn mit.
- `hnsw.iterative_scan` (seit pgvector 0.8.0) und `hnsw.ef_search` (Vorgabe 40): Namen und Werte an der laufenden Version 0.8.7 prüfen.
- Anfragetexte nicht ins Protokoll schreiben.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
