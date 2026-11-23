# Auftrag 149 – Vektorliste: 50 verschiedene Inhalte statt 50 Zeilen

Meilenstein: M3 · Freigabestufe: B (Fehlerbehebung, Diagnose 147) · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
