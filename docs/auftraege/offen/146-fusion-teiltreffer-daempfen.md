# Auftrag 146 – Fusion: Teiltreffer der Stichwortsuche dämpfen

Meilenstein: M3 · Freigabestufe: B (Richtung entschieden in E-72) · Status: offen

## Ziel

Seit 143 (E-71) trifft eine Frage in der Stichwortsuche mit jedem Inhaltswort. Abschnitte mit allen Inhaltswörtern stehen in der Stichwortliste vorn, danach die Teiltreffer. Die Messung der Leitstelle in der Testumgebung (Suchproben M3, `evaluate_search --probes m3 --cutoffs 5,8,10,12 --distance`) zeigt:

| | vor 143 | nach 143 |
| --- | --- | --- |
| keyword R@8 | 0,000 | 0,231 |
| combined R@8 / R@10 / MRR | 0,615 / 0,692 / 0,396 | 0,538 / 0,538 / 0,320 |
| mittlere Zeit keyword / combined | 5 / 54 ms | 125 / 184 ms |

Erster Rang combined vor → nach 143: Q3 – → 12, Q4 – → 38, Q6 4 → 3, Q7 7 → 2, aber Q8 9 → 20, Q9 1 → 3, Q10b 7 → 21, Q5 2 → 4.

Ursache: Jeder Teiltreffer bekommt in der Fusion `1/(RRF_K + keyword_rank)` (`backend/twox/search/postgres.py`, CTE `matched` in `_search_sql`) und überholt Abschnitte, die nur über die Vektorsuche gefunden werden. Die Auskunft liest `2k = 16` Treffer (`backend/twox/answers/context.py`), und nach E-70/139 fallen Treffer ohne Abstand ohnehin aus dem Kontext. Ein Teiltreffer ohne Abstand verdrängt also Belege, ohne selbst in den Kontext zu kommen.

Nach diesem Auftrag hilft die Stichwortsuche bei Fragen, ohne Abschnitte zu verdrängen, die nur nach Bedeutung gefunden werden.

## Umfang

1. **Fusion für Fragen ändern** (nur wenn `question is not None`; für Nicht-Fragen bleibt das SQL byte-gleich, der SHA-256-Test aus 143 belegt das weiter):
   - Abschnitte mit **allen** Inhaltswörtern (`keyword_every`) zählen in der Fusion wie bisher.
   - **Teiltreffer** (`keyword_match AND NOT keyword_every`) zählen in der Fusion **nur, wenn derselbe Abschnitt auch in der Vektorliste steht** (`semantic_rank IS NOT NULL`). Ohne Vektorsuche (KI aus, E-59) gilt die Stichwortliste allein wie bisher, also zählen dort auch Teiltreffer.
   - Der Rang für die Fusion wird innerhalb der zählenden Stichworttreffer vergeben (kein Loch in den Rängen durch ausgeblendete Teiltreffer).
   - Teiltreffer ohne Vektorrang bleiben Kandidaten mit Trefferart `keyword` (Suchseite, Hervorhebung), stehen aber hinter allen fusionierten Treffern.
2. **Laufzeit ansehen:** Die mittlere Zeit der Stichwortsuche ist mit 143 von 5 auf 125 ms gestiegen. Mit `EXPLAIN (ANALYZE, BUFFERS)` an selbst erzeugten Daten feststellen, woher das kommt, und im Kurzbericht festhalten. Eine Verbesserung nur, wenn sie klein ist und im selben Bereich bleibt (kein neuer Index, keine Migration); sonst nur der Befund.
3. **Tests** in `backend/tests/search/`:
   - Teiltreffer mit Vektorrang bekommen einen Fusionsanteil, Teiltreffer ohne Vektorrang nicht und stehen hinter einem reinen Vektortreffer.
   - Treffer mit allen Inhaltswörtern bekommen ihren Anteil auch ohne Vektorrang.
   - Ohne Vektorsuche: Reihenfolge wie nach 143.
   - Ein von Hand nachgerechneter Fall für die Punktzahl.
   - Nicht-Fragen: SQL und Treffer unverändert (bestehender Test bleibt grün).
4. **Doku:** Modul-Docstring von `postgres.py` und `docs/ARCHITECTURE.md` (Abschnitt Search, „Ranking“) an der Stelle, die 143 geändert hat.

## Nicht-Ziele

- Keine Änderung an `context.py`, an Schwelle, `k` oder an der Vektorsuche.
- Keine Migration, kein neuer Index, keine neue Abhängigkeit.
- Keine Messung in der Testumgebung „2x“ – die macht die Leitstelle vor dem Zusammenführen.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/search/postgres.py`
- `backend/tests/search/` (neue oder erweiterte Testdatei)
- `docs/ARCHITECTURE.md` (nur die Stelle zum Ranking aus 143)
- diese Auftragsdatei

## Akzeptanzkriterien (prüfbar)

1. Die Tests aus Umfang 3 sind vorhanden und grün; `test_keyword_search.py`, `test_fusion.py`, `test_question_keywords.py` grün (Erwartungen nur ändern, wo sie an der alten Fusion von Teiltreffern hängen – jede Änderung im Kurzbericht begründet).
2. CI wie `ci.yml` grün: ruff, Formatprüfung, mypy, `pytest`, `pytest -m worker` (mit laufendem Dienst `worker`, wie in der CI), Katalog, Migrationen, Lizenzen, Schema, e2e.
3. Die CI-Aufzeichnungen (`backend/tests/answers/test_ci_questions.py`) bleiben grün. Werden sie rot, weil sich der Kontext ändert: neu aufnehmen nach `backend/tests/answers/recorded/README.md` mit `gemma4:31b-it-qat` (vorher `/api/ps` am Host leer, Ollama nicht stoppen), sonst nichts aufweichen.
4. Kurzbericht mit dem Laufzeitbefund (Umfang 2) und einer Beschreibung der neuen Punktzahl in einer Zeile.
5. Diff nur in den genannten Bereichen (plus ggf. `ci_questions.json`), keine neue Abhängigkeit.
6. Compose-Projekte des Auftrags mit `down -v` entfernt.

## Vorgaben und Hinweise

- Compose-Projekt `twox-146`, `TWOX_API_PORT=18146` in der ignorierten `.env` des Arbeitsverzeichnisses. `docker` steht nicht im PATH: `%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin`.
- Nutzereingaben nur als Parameter ins SQL.
- Basis ist `main` mit 143 und 145.
- Nicht pushen.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine. Richtung entschieden in E-72. Bringt die Messung der Leitstelle das Ziel (combined R@8 über 0,615, keine M3-Probe deutlich schlechter als vor 143) nicht, legt die Leitstelle a7 neue Optionen vor.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
