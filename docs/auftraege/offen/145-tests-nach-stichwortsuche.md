# Auftrag 145 – Tests nach der weichen Stichwortsuche nachziehen

Meilenstein: M3 · Freigabestufe: B (Inhalt entschieden in E-71) · Status: offen

## Ziel

Seit Auftrag 143 (E-71) treffen Fragen in der Stichwortsuche mit jedem Inhaltswort. Dadurch sind auf `main` 9 Tests rot, alle wie in 143 vorhergesehen:

- 7 Tests in `backend/tests/answers/test_ci_questions.py`: `RecordingMissingError` bei `ci-fact-1` und `ci-fact-2`, weil sich Quellen und Reihenfolge im Kontext und damit die Schlüssel der Aufzeichnungen ändern.
- 2 Tests `backend/tests/acceptance/test_m2.py::test_search_answers_a_question_in_other_words_by_meaning` (ai-off und ai-on): Der Test verlangt, dass die Frage per Stichwort nichts findet (`test_m2.py:373`). Ohne KI kommen jetzt Treffer, mit KI trägt der erste Treffer `['keyword', 'semantic']` statt `['semantic']`.

Nach diesem Auftrag sind alle Tests grün, ohne dass eine Zusicherung ihren Zweck verliert.

## Umfang

1. **Abnahmetest M2 anpassen.** Zweck des Tests: Eine Frage in anderen Worten wird über die Bedeutung gefunden, nicht über gemeinsame Wörter.
   - **Bevorzugt (Option 1):** Die Frage `QUESTION` (`test_m2.py:65`) so umformulieren, dass keines ihrer Inhaltswörter (nach Stoppwörtern in `german`/`english`/`simple`) im Testdokument vorkommt. Sinn und Ziel (`QUESTION_TARGET`) bleiben gleich. Dann bleiben alle Zusicherungen unverändert, auch `match_kinds == ["semantic"]` und `hits == []` ohne KI.
   - Der Text muss selbst geschrieben sein; keine Auszüge aus fremden Unterlagen.
   - **Nur wenn Option 1 nicht geht** (begründet im Kurzbericht): Die Zusicherungen so ändern, dass der Zweck erhalten bleibt – mit KI ist der Zielabschnitt der erste Treffer und trägt `semantic`; ohne KI ist der Zielabschnitt nicht der erste Treffer oder es gibt keinen. Kein bloßes Entfernen von Zusicherungen.
2. **CI-Aufzeichnungen neu aufnehmen** (`backend/tests/answers/recorded/ci_questions.json`) nach `backend/tests/answers/recorded/README.md` („Recording again“), mit dem Standardmodell aus E-70:
   `docker compose -p twox-145 run --rm -e TWOX_CHAT_MODEL=gemma4:31b-it-qat backend-dev python manage.py record_answers`
   - Vorher mit `/api/ps` am Host prüfen, dass kein anderes Modell geladen ist. Ollama nicht stoppen.
   - Besteht eine Frage mit gemma4 eine Prüfung des CI-Tests nicht, wird nicht aufgeweicht und nicht mit dem Rückfallmodell aufgenommen: Befund in den Kurzbericht, Status „wartet auf a7“.
   - Durchsicht: nur Modellausgabe, keine fremden Links, keine Personennamen, keine Pfade.

## Nicht-Ziele

- Keine Änderung an `backend/twox/` (Suche, Antworten, Prompt). Ist eine Codeänderung nötig, Frage an a7.
- Keine Änderung an `test_ci_questions.py`, an den Fixtures oder an anderen Tests.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/tests/acceptance/test_m2.py` (nur `QUESTION`, ggf. `QUESTION_TARGET` und dieser eine Test)
- `backend/tests/answers/recorded/ci_questions.json`
- diese Auftragsdatei

## Akzeptanzkriterien (prüfbar)

1. `pytest` (alle) und `pytest -m worker` grün; ruff, Formatprüfung, mypy grün.
2. `test_search_answers_a_question_in_other_words_by_meaning` grün in ai-off und ai-on; der Kurzbericht nennt die gewählte Option und zeigt bei Option 1, dass kein Inhaltswort der neuen Frage im Testdokument steht (z. B. per `websearch_to_tsquery` und `@@` gegen die Abschnitte).
3. `ci_questions.json` trägt `model` `gemma4:31b-it-qat` und den Digest aus `docs/DECISIONS.md` (Abhängigkeitstabelle), `prompt_version` unverändert. Der Kurzbericht nennt Datum, Dauer und Ergebnis des Aufnahmelaufs und je Frage die Zahl der Quellen.
4. `test_ci_questions.py` grün mit unerreichbarer Modelladresse (`TWOX_LLM_BASE_URL=http://127.0.0.1:9/v1`).
5. e2e-Lauf wie in der CI grün (die Suchseite ist von 143 betroffen).
6. Diff nur in den genannten Dateien, keine neue Abhängigkeit.
7. Compose-Projekte des Auftrags mit `down -v` entfernt.

## Vorgaben und Hinweise

- Compose-Projekt `twox-145`, eigener `TWOX_API_PORT` (z. B. 18145) in der ignorierten `.env` des Arbeitsverzeichnisses.
- Basis ist `main` mit 143 (E-71).
- Nicht pushen.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine. Inhalt entschieden in E-71.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
