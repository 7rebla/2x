# Auftrag 149 – Vektorliste: 50 verschiedene Inhalte statt 50 Zeilen

Meilenstein: M3 · Freigabestufe: B (Fehlerbehebung, Diagnose 147) · Status: erledigt

## Ziel

Diagnose 147 (`docs/auftraege/erledigt/147-diagnose-vektorsuche.md`): `VECTOR_CANDIDATES = 50` (`backend/twox/search/postgres.py:155`) begrenzt in der Vektorabfrage (`postgres.py:452-465`, CTE `nearest`, `LIMIT %(vector_limit)s`) **Abschnittszeilen**. Dasselbe Handbuch hängt an vielen Geräten (APS-Handbücher an 11, Quick-Start an 22); jede Kopie ist eine eigene Zeile. Die Suche fasst Kopien erst nach der Fusion zu einem Treffer zusammen. 50 Zeilen ergeben deshalb oft nur 5 bis 10 verschiedene Inhalte, und die Auskunft bekommt 4 bis 7 statt 8 Quellen.

Nach diesem Auftrag liefert die Vektorsuche bis zu `VECTOR_CANDIDATES` **verschiedene Inhalte** (Kopien zählen einmal), mit allen ihren Abschnittszeilen, damit Gerät, Anlage und Fundorte wie heute erhalten bleiben. Messung 147 (Variante V5): Recall@8 kombiniert 8/13 → 9/13, Prüffrage 4 (`probe`) Rang – → 8, Kontrollfrage unverändert.

## Umfang

1. **Vektorabfrage**: Kopien vor dem Limit zusammenfassen. Inhalt = derselbe Schlüssel, mit dem die Suche Kopien heute zusammenfasst (`content_key` in `_search_sql`: Prüfsumme der Version, Seiten, ggf. Überschrift, Text), oder ein gleichwertiger, im Bericht begründeter Schlüssel. Die Liste enthält die nächsten `VECTOR_CANDIDATES` Inhalte; jede Zeile eines Inhalts trägt Rang und Abstand ihres Inhalts.
   - Die HNSW-Nutzung (Index-Scan mit `ef_search`, `iterative_scan`) soll erhalten bleiben oder es ist begründet, warum nicht (Laufzeit mit ca. 5 000 Abschnitten; Messung im Bericht). Möglich z. B.: Index-Scan mit größerer Zeilenzahl und danach Gruppierung, oder iterative Erweiterung, bis `VECTOR_CANDIDATES` Inhalte erreicht sind.
   - Eingrenzen auf Gerät/Anlage und Ausschlüsse gelten wie heute vor der Zählung.
2. **Tests** in `backend/tests/search/`: Mit vielen Kopien eines Inhalts (z. B. 20 Geräte) und 60 verschiedenen Inhalten liefert die Vektorliste genau `VECTOR_CANDIDATES` verschiedene Inhalte; Kopien tragen denselben Rang; Fundorte aller Kopien bleiben im Treffer; Eingrenzen und Ausschlüsse wirken vor der Zählung; ohne Kopien unverändertes Ergebnis.
3. **CI-Aufzeichnungen** (`backend/tests/answers/test_ci_questions.py`): bleiben sie grün, nichts tun. Werden sie rot, neu aufnehmen nach `backend/tests/answers/recorded/README.md` mit `gemma4:31b-it-qat` (vorher `/api/ps` leer, Ollama nicht stoppen); nichts aufweichen.
4. **Doku:** Docstrings in `postgres.py` und `docs/ARCHITECTURE.md` (Abschnitt Search) an der Stelle zur Vektorliste.

## Nicht-Ziele

- Keine Teilstücke/Neueinbettung (Stufe C, Entscheidung a7), keine Umformulierung der Frage, keine Änderung an Stichwortsuche, Fusion, `context.py`, Schwelle oder k.
- Keine Migration, kein neuer Index, keine neue Abhängigkeit.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/search/postgres.py`
- `backend/tests/search/`
- ggf. `backend/tests/answers/recorded/ci_questions.json`
- `docs/ARCHITECTURE.md` (nur die Stelle zur Vektorliste)
- diese Auftragsdatei

## Akzeptanzkriterien (prüfbar)

1. Tests aus Umfang 2 vorhanden und grün; bestehende Suchtests grün (Änderungen an Erwartungen nur, wo sie an der Zeilenzählung hängen, jede begründet).
2. CI wie `ci.yml` grün: backend (inkl. `pytest -m worker` mit laufendem `worker`), web, testfactory, e2e.
3. Laufzeit der Vektorabfrage an selbst erzeugten Daten (ca. 5 000 Abschnitte, viele Kopien) vorher/nachher im Bericht; `EXPLAIN` zeigt, ob der HNSW-Index genutzt wird.
4. Diff nur in den genannten Bereichen, keine neue Abhängigkeit, Compose-Projekte mit `down -v` entfernt.

## Vorgaben und Hinweise

- Compose-Projekt `twox-149`, `TWOX_API_PORT=18149`. `docker` liegt nicht im PATH: `%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin`.
- Nutzereingaben nur als Parameter ins SQL.
- Parallel läuft 148 (Prompt, CI-Aufzeichnungen) und 137 (Abnahmetests). Kommt es bei `ci_questions.json` zu einer Überschneidung mit 148, nimmt die Leitstelle nach dem Zusammenführen beider neu auf.
- Die Messung in „2x“ macht die Leitstelle vor dem Zusammenführen.
- Nicht pushen.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine (Fehlerbehebung, Stufe B).

## Kurzbericht (füllt der Auftragsbearbeiter aus)

### Was wurde gebaut?

`backend/twox/search/postgres.py`, `vector_sql` und `nearest_sections_with_distance`: Die Vektorliste enthält jetzt die Abschnitte der `VECTOR_CANDIDATES` (50) nächsten **Inhalte**. Alles läuft in **einer** Abfrage:

1. `indexed`: die 50 nächsten Abschnitte über den HNSW-Index, wie bisher (`ORDER BY embedding <=> q LIMIT 50`, `iterative_scan`, `ef_search` unverändert).
2. `complete`: Prüft, ob diese 50 Zeilen 50 verschiedene Inhalte sind.
3. `nearest`: Wenn ja, sind es diese Zeilen. Wenn nein (Kopien belegen Zeilen, der Bereich ist kleiner oder der Index lieferte zu wenig), nimmt die Abfrage alle Abschnitte im Bereich mit ihrem Abstand, also exakt. PostgreSQL führt per One-Time-Filter nur den nötigen Zweig aus. `EXPLAIN` zeigt den anderen Zweig als „never executed“.
4. `contents`: Gruppierung nach Inhalt, die 50 Inhalte mit dem kleinsten Abstand. Bei gleichem Abstand gewinnt die kleinere Abschnitts-ID.
5. `copies`: Alle Abschnitte dieser Inhalte im Bereich, auch Kopien, die der Index nicht gelesen hat. Jede Kopie trägt Rang (`DENSE_RANK`) und Abstand ihres Inhalts.

**Inhaltsschlüssel** ist derselbe wie in `_search_sql`: Prüfsumme, Seiten, ggf. Überschrift, `md5(text)`. Die Ausdrücke stehen jetzt einmal in `_SECTION_KEYS` und gelten für Suche und Vektorliste. Die Zeilen von `_search_sql` sind dadurch nur umgestellt, nicht verändert. Beim Nachladen der Kopien wird der Text direkt verglichen (`s.text = first.text`) statt über md5. Das ist gleichwertig, aber Texte anderer Länge werden dabei nicht gehasht.

**Eingrenzen und Ausschlüsse** wirken in allen Schritten vor der Zählung: über `searchable` und `{exclude}`, auch bei den Kopien. Es zählen nur Abschnitte mit dem aktuellen Modell.

Doku: Modul-Docstring und Docstrings in `postgres.py`, `docs/ARCHITECTURE.md` (Abschnitt Search, Punkte „Vector“ und „Exclusions“).

### Wie wurde getestet?

- **Neue Tests** in `backend/tests/search/test_vector_contents.py`, 13 Stück:
  - 20 Geräte × 12 geteilte Abschnitte plus 60 Einzelinhalte ergeben genau 50 Inhalte, Ränge 1–50.
  - Kopien tragen denselben Rang und Abstand.
  - Ein Treffer der Suche behält alle 20 Fundorte.
  - Kopien, die der Index nicht gelesen hat, kommen über den Schlüssel dazu.
  - Geräte- und Anlagenfilter sowie Ausschlüsse wirken vor der Zählung.
  - Kopien mit anderem Modell oder ohne Einbettung bleiben draußen.
  - Ohne Kopien ist das Ergebnis unverändert (die 50 nächsten Abschnitte, Ränge 1–50).
  - Ohne Einbettung gibt es kein Ergebnis.
  - Der exakte Zweig läuft nur bei Bedarf, und im Plan stehen One-Time-Filter.
- **Bestehende Tests:** Eine Erwartung wurde geändert. `test_vector_ranks_are_sorted_again_after_the_index` prüft jetzt den Sort auf `min(n.distance) + 0` in `contents` und auf `c.distance + 0` am Ende statt `nearest.distance + 0`. Grund: Die Liste wird jetzt nach Inhalten statt nach Zeilen sortiert. Sonst wurde nichts geändert.
- **Stabilität:** `pytest tests/search` lief sechsmal hintereinander grün (444 Tests).
  - Eine frühere Fassung erweiterte den Index-Scan schrittweise mit mehr Zeilen. Sie war unzuverlässig: Nach vielen zurückgerollten Testdaten und mit vielen identischen Vektoren lieferte HNSW teils 0 statt 50 Zeilen.
  - Ein Prüflauf mit 30 Runden zu je 300 zurückgerollten Abschnitten zeigt bei der Endfassung in jeder Runde 50 Inhalte. Vorher fiel dieselbe Prüfung auf 0 bis 4 Inhalte ab.
- **CI wie `ci.yml`:** Ergebnis siehe Abschnitt „CI-Lauf“.

### Laufzeit (Kriterium 3)

Selbst erzeugte Daten, ca. 5 000 Abschnitte, 1024-dimensionale Zufallsvektoren, im Container `backend-dev`. Gemessen wurden 5 Anfragen mit je 10 Wiederholungen; angegeben ist der Median der Zeit von `nearest_sections_with_distance`. `EXPLAIN (ANALYZE)` wurde auf die ausgeführte Abfrage angewendet.

| Datensatz | vorher (main) | nachher |
| --- | --- | --- |
| Viele Kopien: 4 Handbücher × 50 Abschnitte × 20 Geräte + 10 × 100 Einzelabschnitte | 3,6 ms, 50 Zeilen = **10–12 Inhalte**, HNSW | 28,8 ms, 183–278 Zeilen = **50 Inhalte**; HNSW für `indexed`, danach exakter Zweig (Seq Scan über 5 000 Abschnitte, ca. 27 ms) |
| Ohne Kopien: 10 × 500 Einzelabschnitte | 3,9 ms, 50 Inhalte, HNSW | 7,6 ms, 50 Inhalte, nur HNSW (exakter Zweig „never executed“) |

**Warum bei Kopien kein größerer Index-Scan?**

- Gemessen: Ab etwa 200 Zeilen wählt der Planer für `ORDER BY embedding <=> q LIMIT n` mit dem Bereichsfilter ohnehin Seq Scan und Top-N-Sort.
- HNSW findet identische Vektoren schlecht. Kopien haben identische Vektoren. Bei größeren Zeilenzahlen lieferte der Index deutlich weniger Zeilen als vorhanden, im Prüflauf 80 statt 800 und teils 0.
- Der exakte Zweig ist dagegen vollständig und deterministisch.
- Die Kosten wachsen linear mit der Zahl der Abschnitte. Bei 50 000 Abschnitten wären es grob geschätzt 300 ms je Suche mit Kopien; das ist nicht gemessen.
- Ohne Kopien unter den 50 nächsten bleibt es beim Index.

Rohdaten und Messskripte liegen nur im Scratchpad, nicht im Repository.

### CI-Lauf

Lokal mit den Befehlen aus `ci.yml`, Compose-Projekt `twox-149`; `worker` und `api` liefen dabei.

- **backend: grün.**
  - ruff check, ruff format, mypy: ohne Befund.
  - `pytest`: 3533 bestanden, darunter `tests/answers/test_ci_questions.py`.
  - `pytest -m worker`: 6 bestanden.
  - Übersetzungskatalog, Migrationen, Lizenzen und OpenAPI-Schema: ohne Abweichung.
- **web: grün.** lint, typecheck, test, build, licenses, API-Client ohne Abweichung.
- **testfactory: grün.** ruff, format, mypy, Tests ohne Netz, Manifestprüfungen; `testfactory/extern` existiert nicht.
- **e2e: grün.** 88 bestanden, 1 übersprungen.
  - Lief wie in CI ohne Chat-Modell (`TWOX_CHAT_MODEL=` leer wie in `.env.example`) und mit dem Testkonto aus `.env.example`.
  - Mit der lokalen `.env` des Arbeitsverzeichnisses (Chat-Modell gesetzt) scheitern die drei Tests „without a chat model“ erwartungsgemäß. Das liegt an der Umgebung, nicht am Auftrag.

**CI-Aufzeichnungen:** blieben grün. `ci_questions.json` wurde nicht neu aufgenommen, Ollama nicht benutzt.

### Zweig und Arbeitsverzeichnis

- Zweig `worktree-agent-a25912b141a61c9f3`
- Arbeitsverzeichnis `.claude/worktrees/agent-a25912b141a61c9f3`
- Basis `main` e34b95b. Nicht gepusht.

### Abweichungen

- **Kein reiner Index-Scan bei Kopien.** Statt eines größeren Index-Scans läuft ein exakter Zweig über alle Abschnitte im Bereich, mit Begründung und Messung oben. Der Auftrag lässt das mit Begründung zu.
- **Abstand der Kopien:** Jede Kopie trägt den kleinsten Abstand ihres Inhalts, wie im Auftrag verlangt. `SearchHit.semantic_distance` war schon vorher das Minimum über die Abschnitte desselben Inhalts und ändert sich dadurch praktisch nicht.
- `ci_questions.json`: unverändert (CI-Aufzeichnungen grün).
- Die Messung in „2x“ (Recall@8, Prüffrage 4, Kontrollfrage) macht laut Auftrag die Leitstelle; sie ist hier nicht gemacht.
