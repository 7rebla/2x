# Auftrag 139 – Startwerte und Relevanzfilter der Auskunft

Meilenstein: M3 · Freigabestufe: B · Status: offen

Voraussetzungen: E-70 (`docs/DECISIONS.md:80`) ist entschieden. 125 (Kontextauswahl), 128 (Messlauf) und 135 (Prüffragen in der CI mit Aufzeichnungen) liegen auf `main`.

Stufe B: Der Auftrag setzt nur um, was a7 in E-70 entschieden hat. Er ändert weder Architektur noch Datenmodell und bringt keine neue Abhängigkeit. Die Modellgewichte stehen schon in der Abhängigkeitstabelle (`docs/DECISIONS.md:226-227`).

## Ziel

E-70 legt Chat-Modell, Reasoning, Temperatur und Startwerte der Auskunft fest: Schwelle 0.55 **mit Filter auf relevante Treffer nach geöffneter Sperre**, k = 8, 16 000 Zeichen. Grundlage ist der Messlauf 128 (Kurzbericht, Abschnitte „Filter nach geöffneter Sperre“ und „Empfehlung und Optionen für a7“).

Heute ist die Schwelle nur ein Tor. Liegt **ein** Treffer unter der Schwelle, kommen alle Treffer der Suche in den Kontext, auch weit entfernte (`backend/twox/answers/context.py:18-23` und `:195-202`). Nach diesem Auftrag kommen nach geöffneter Sperre nur noch relevante Treffer in den Kontext. Die Standardwerte in Code, Vorlage und Doku entsprechen dann E-70, und die Aufzeichnungen der CI-Prüffragen passen zur neuen Kontextauswahl.

## Umfang

1. **Relevanzfilter in `backend/twox/answers/context.py`:**
   - Nach geöffneter Sperre kommen nur Treffer weiter, für die `_is_relevant(hit, threshold)` gilt (`context.py:224-227`): Abstand ≤ Schwelle oder exakter Treffer (`MatchKind.EXACT`). Stichworttreffer ohne Abstand und ohne exakten Treffer fallen damit aus dem Kontext. Das ist gewollt und entspricht dem Filterversuch aus 128.
   - **Ort des Filters:** vor `_candidates(...)` in `select_context` (`context.py:202`), also auf der Trefferliste. 128 nennt „eine Zeile in `_select_mains`“. `_Candidate` (`context.py:101-117`) trägt aber keinen Abstand, und der Filterversuch aus 128 hat auf Trefferebene gefiltert (Laufzeit-Ersatz von `context._candidates`, Kurzbericht 128, Abschnitt „Was wurde gemacht?“). Gefiltert wird daher die Trefferliste. `_select_mains` bleibt unverändert.
   - `best_distance` und `hit_count` beziehen sich weiter auf **alle** Treffer der Suche (`context.py:84-90`, `:193-194`). Messwerkzeuge (127, 142) lesen diese Felder, ihre Bedeutung bleibt.
   - Nachbarabschnitte (`TWOX_ANSWER_NEIGHBOURS`, `context.py:347-403`) folgen weiter ihrer Hauptquelle und werden nicht gefiltert. Sie haben keinen eigenen Treffer und damit keinen Abstand.
   - Kopien derselben Datei an mehreren Geräten (`_merge_copies`, `context.py:289-305`) haben denselben Abstand und fallen gemeinsam heraus oder bleiben gemeinsam. Das deckt ein Test ab.
   - Die Abfrage `limit=min(MAX_LIMIT, 2 * k)` (`context.py:185`) bleibt.
   - Modul-Docstring Schritt 5 (`context.py:18-23`, „The threshold is a gate: once it is passed, the hits are taken in the order of the search“) auf das neue Verhalten umschreiben.
2. **Standardwerte nach E-70.** Namen und heutige Werte sind geprüft:

   | Variable | heute `settings.py` | heute `.env.example` | neu |
   | --- | --- | --- | --- |
   | `TWOX_ANSWER_MAX_DISTANCE` | `0.60` (`settings.py:562`) | `0.60` (`.env.example:73`) | `0.55` |
   | `TWOX_ANSWER_CONTEXT_CHARS` | `20000` (`settings.py:554`) | `20000` (`.env.example:69`) | `16000` |
   | `TWOX_ANSWER_MAX_SOURCES` | `8` (`settings.py:551`) | `8` (`.env.example:67`) | unverändert |
   | `TWOX_CHAT_TEMPERATURE` | `0.0` (`settings.py:543`) | `0` (`.env.example:60`) | unverändert |
   | `TWOX_CHAT_MAX_TOKENS` | `1024` (`settings.py:542`) | `1024` (`.env.example:58`) | unverändert |
   | `TWOX_CHAT_REASONING_EFFORT` | `none` (`settings.py:546`) | `none` (`.env.example:63`) | unverändert |

   - Die Kommentare in `settings.py:533-536` (Chat-Modell; Zeile 532 ist `TWOX_SEARCH_EMBED_TIMEOUT_SECONDS` und bleibt unberührt „chosen after the measurement run of work order 128“), `:548-549` („Starting values, calibrated in work order 128“), `:552-553` (Begründung der 20 000 Zeichen: neu 8 × 2 000 = k × `TWOX_SECTION_MAX_CHARS`, Kurzbericht 128) und `:557-561` (Schwelle) auf E-70 nachziehen. Der Kommentar zur Schwelle nennt dabei den Filter.
   - `.env.example:50-52` (Kommentar zum Chat-Modell) und `:65-73` ebenso.
   - `TWOX_ANSWER_TRANSLATION_DISTANCE` 0.15 bleibt kleiner als die neue Schwelle; die Startprüfung (`settings.py:575-587`) greift also nicht.
   - `deploy/compose/compose.yaml:24-35` reicht die Variablen nur als `${VAR:-}` durch. Leer heißt dort Standardwert aus `settings.py` (`settings.py:49-51`, `:81-83`). **Es gibt dort keine Werte zu ändern.** Die Datei bleibt unberührt; der Kurzbericht bestätigt das.
3. **`TWOX_CHAT_MODEL`: empfohlenes Modell nennen, Vorlage bleibt leer.**
   - `README.md`, Abschnitt „Chat model for answers“ (`README.md:189-213`): Empfohlen ist `gemma4:31b-it-qat`, Rückfall `qwen3.8:27b-q4_K_M` (E-70). Den Satz „Which one becomes the default is decided after the measurement run (work order 128)“ (`:191`) ersetzen. Bei Punkt 1 `ollama pull gemma4:31b-it-qat` als Beispiel nennen. Bei Punkt 3 (`:201`, „concrete values are set after the model decision“) `OLLAMA_CONTEXT_LENGTH=16384` nach E-70 nennen. Nie `:latest` oder ein Tag ohne Quantisierung empfehlen (`docs/DECISIONS.md:226`).
   - `docs/ARCHITECTURE.md`, Zeile der Einstellungstabelle zu `TWOX_CHAT_MODEL` (`:594`): empfohlenes Modell und E-70 nennen. Standard und Wert in `.env.example` bleiben „empty“.
   - **`.env.example` bleibt bei `TWOX_CHAT_MODEL=` (leer).** Nur der Kommentar (`.env.example:50-52`) nennt das empfohlene Modell und den Rückfall. Er sagt auch, dass man den Wert nach `ollama pull` in der eigenen `.env` setzt. Begründung am Code:
     - Die CI kopiert `.env.example` nach `.env` (`.github/workflows/ci.yml:40`, `:112`, `:217`). Ein gesetztes Modell gilt also in allen Jobs.
     - Mit gesetztem Modell fragt `GET /api/v1/answers/status/` über `chat_model_ready()` das Modell an (`backend/twox/answers/api.py:530-538`, `:558-561`, Selbsttest mit `GET /api/tags`). `api`, `worker` und `backend-dev` erreichen den Host über `host.docker.internal` (`deploy/compose/compose.yaml:121-122`, `:179-180`, `:305-306`; `.env.example:26`).
     - In der GitHub-CI ohne Ollama ergäbe das wohl weiter „nicht verfügbar“. **Lokal** mit laufendem Ollama und geladenem Modell meldet der Status aber `available: true`. Dann bricht `web/e2e/answer-page.spec.ts`, der ausdrücklich ein leeres `TWOX_CHAT_MODEL` und den Hinweis „nicht verfügbar“ erwartet (`answer-page.spec.ts:5-9`).
     - Außerdem entfiele in CI und lokal die Warnung `twox.answers.W001` (`backend/twox/answers/checks.py:36-44`), die heute auf das fehlende Modell hinweist.
     - Ergebnis: Leer lassen ist die sichere Wahl, das Modell steht im Kommentar. Will der Bearbeiter davon abweichen, gilt das als Frage an a7 (Status „wartet auf a7“), nicht als eigene Entscheidung.
4. **Aufzeichnungen aus 135 (`backend/tests/answers/recorded/ci_questions.json`) neu erzeugen.**
   - Der Schlüssel jeder Aufzeichnung hängt an den Nachrichten an das Modell, also am Kontext (`backend/tests/answers/recorded/README.md`, Abschnitt „Format“; `docs/ARCHITECTURE.md:175`).
   - Der CI-Test legt die Kontextwerte fest: `TWOX_ANSWER_MAX_DISTANCE` 0.6, k = 3, 8 000 Zeichen (`backend/tests/answers/test_ci_questions.py:133-141`). Damit ändern die neuen Standardwerte allein nichts. **Der Filter ändert den Kontext aber:**
     - Bei den Fragen `ci-fact-1`, `ci-fact-2` und `ci-injection` liegt die Belegstelle bei etwa 0,06, alle anderen Abschnitte bei 1,0 (orthogonal, `test_ci_questions.py:142-148`, `:440-463`).
     - Heute sieht das Modell je 3 Quellen (alle vier Einträge der Aufzeichnung haben 3 `sources`). Mit Filter bleibt bei diesen drei Fragen nur die Belegstelle, plus ggf. exakte Treffer.
     - Die Kontrollfrage mit `THRESHOLD_OFF` = 2.0 (`:732-745`, `:877`, `:901`) bleibt unverändert.
     - Ohne Neuaufnahme scheitert `pytest` mit `RecordingMissingError`.
   - Darum: Neuaufnahme mit `manage.py record_answers` nach `backend/tests/answers/recorded/README.md` („Recording again“), mit dem Standardmodell aus E-70: `docker compose -p twox-139 run --rm -e TWOX_CHAT_MODEL=gemma4:31b-it-qat backend-dev python manage.py record_answers`.
   - Vorher am lokalen Ollama über `/api/tags` prüfen, dass der Digest von `gemma4:31b-it-qat` mit `docs/DECISIONS.md:227` übereinstimmt (Lizenz und Digest an der Quelle sind dort schon geprüft, D1).
   - Das Beispiel mit `qwen3.8:27b-q4_K_M` in `backend/tests/answers/recorded/README.md` („Recording again“) und in `README.md:447` auf `gemma4:31b-it-qat` umstellen.
   - `ANSWER_SETTINGS` im CI-Test (`test_ci_questions.py:134-141`) bleibt unverändert: feste Testwerte, unabhängig von den Standardwerten.
   - Besteht eine Frage mit gemma4 eine Prüfung des CI-Tests nicht, wird die Aufnahme nicht geschrieben (`record_answers`, Verhalten aus 135). Dann **nicht** den Test aufweichen und nicht auf eigene Faust mit dem Rückfallmodell aufnehmen. Befund mit Frage und Prüfung in den Kurzbericht, Status „wartet auf a7“. Die Leitstelle legt die Optionen vor (Aufnahme mit `qwen3.8:27b-q4_K_M` oder Folgeauftrag).
5. **Tests** (`backend/tests/answers/test_context.py`):
   - Neue Tests:
     - Ein weit entfernter Treffer (Abstand > Schwelle, kein exakter Treffer) neben einem nahen erscheint nicht unter den Quellen.
     - Ein exakter Treffer jenseits der Schwelle bleibt Quelle.
     - Ein Stichworttreffer ohne Abstand neben einem nahen Treffer erscheint nicht.
     - `best_distance` und `hit_count` zählen weiter alle Treffer.
     - Nachbarn einer relevanten Hauptquelle bleiben (mit `neighbours=True`).
     - Zwei Kopien eines nahen Abschnitts an zwei Geräten bleiben eine Quelle mit beiden Orten.
     - Die Grenze ist eingeschlossen (Abstand = Schwelle bleibt).
   - Bestehende Tests anpassen:
     - `test_answer_settings_have_their_starting_values` (`test_context.py:722-726`) erwartet `["8", "16000", "False", "0.55", "0.15"]`.
     - `test_translation_distance_must_be_below_the_threshold` (`:767-775`) nennt in der Meldung die neue Schwelle (`0.55`).
   - **Erwartete Nebenwirkung:** Viele bestehende Tests in `test_context.py` (Budget, Nachbarn, Kopien, Übersetzungen) legen Abschnitte in Winkeln ab, deren Abstand über 0,55 liegt (z. B. 80° und 85° in `:464-476`). Sie erwarten diese Abschnitte trotzdem als Quellen und laufen mit Standardschwelle. Solche Tests, die nicht die Schwelle prüfen, bekommen eine ausdrücklich passende Schwelle (z. B. `max_distance=2.0` als benannte Konstante oder ein `settings`-Override in einer Fixture) oder nähere Winkel. **Zusicherungen werden dabei nicht abgeschwächt.** Dasselbe gilt für Tests in `test_ask.py` und `test_api.py`, falls sie über die echte Kontextauswahl laufen. Für `test_service.py` und `test_evaluation.py` gilt die Sperre unter „Betroffene Bereiche“ (nur Befund im Kurzbericht). Jede angepasste Datei steht im Kurzbericht.
6. **Doku:**
   - `docs/ARCHITECTURE.md`:
     - Einstellungstabelle, Zeilen `TWOX_CHAT_MODEL` (`:594`), `TWOX_ANSWER_CONTEXT_CHARS` (`:600`) und `TWOX_ANSWER_MAX_DISTANCE` (`:602`: Standard und Wert in `.env.example` `0.55`, Beschreibung mit Filter).
     - In der Zeile des Pakets `answers` (`:134`) nur der Teilsatz zur Schwelle der Kontextauswahl („a relevance threshold before any model call …“): danach nur relevante Treffer im Kontext.
   - `README.md`: Abschnitt „Chat model for answers“ und die Zeile zur Neuaufnahme (`:447`).
   - `backend/tests/answers/recorded/README.md`.

## Nicht-Ziele

- Keine Änderung an der Suche (`backend/twox/search/*`, Auftrag 143), an der Zitatprüfung (`backend/twox/answers/citations.py`, Auftrag 140), an den Prüffragen (`testfactory/questions.yaml`, Auftrag 141) und am Messwerkzeug (`backend/twox/answers/evaluation.py`, `evaluate_answers.py`, Auftrag 142).
- Keine Änderung am Prompt (`backend/twox/answers/prompt.py`) und damit an `prompt_version()`.
- Kein Schalter für den Filter. Er gilt immer, wie in E-70 entschieden.
- Keine neue Einstellung, keine Änderung an `TWOX_ANSWER_NEIGHBOURS`, `TWOX_ANSWER_TRANSLATION_DISTANCE`, `TWOX_ANSWER_RATE`, `TWOX_ANSWER_TOTAL_TIMEOUT`.
- Kein Wert für `TWOX_CHAT_MODEL` in `.env.example` (Begründung Umfang 3); die lokale `.env` des Hauptordners bleibt unberührt.
- Kein Messlauf auf der Testumgebung 2x. Den wiederholten Messlauf nach E-70 führt die Leitstelle nach dem Zusammenführen dieses Auftrags und der Aufträge 140–143 aus.
- Keine Änderung an `docs/DECISIONS.md`, `docs/STATUS.md`, `docs/ROADMAP.md` (pflegt die Leitstelle).
- Keine Änderung an `web/` (auch nicht an `web/e2e/answer-page.spec.ts`).

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/answers/context.py` (Filter, Docstring)
- `backend/twox/config/settings.py` (nur die Zeilen der Chat- und Antwortwerte, `:533-562`)
- `.env.example` (nur `:50-52` und `:65-73`)
- `backend/tests/answers/test_context.py`
- `backend/tests/answers/recorded/ci_questions.json`, `backend/tests/answers/recorded/README.md`
- nur falls durch den Filter nötig (Umfang 5): `backend/tests/answers/test_ask.py`, `test_api.py`, `test_ci_questions.py` (dort nur Testaufbau; **nicht** `ANSWER_SETTINGS` und **nicht** `World.answer_function`, `test_ci_questions.py:343-363`, das 142 ändert).
- **Nicht** `backend/tests/answers/test_service.py` (140 und 142 legen dort Hilfen ab bzw. importieren sie, E-66: gleichzeitige Aufträge berühren verschiedene Dateien), **nicht** `test_citations.py` (140) und **nicht** `test_evaluation.py` (142). Ist in einer dieser Dateien oder in `World.answer_function` eine Anpassung unvermeidlich, wird sie nicht vorgenommen: Befund mit Test und Grund in den Kurzbericht, die Leitstelle legt die Reihenfolge fest.
- `README.md`: nur Abschnitt „Chat model for answers“ und die Zeile zur Neuaufnahme im Testabschnitt (`:447`)
- `docs/ARCHITECTURE.md`: nur die Tabellenzeilen `:594`, `:600`, `:602` und der Teilsatz zur Schwelle in `:134`
- **Nicht berührt:** `deploy/compose/compose.yaml` (keine Werte, siehe Umfang 2), `backend/twox/answers/citations.py`, `prompt.py`, `evaluation.py`, `backend/twox/search/*`, `testfactory/*`, `web/*`.
- **Parallele Aufträge:**
  - 140 ändert `citations.py`. Ändert 140 den Prompt oder die Zitatprüfung so, dass die Aufzeichnungen nicht mehr passen, braucht es nach beiden Aufträgen eine weitere Neuaufnahme. Die Leitstelle führt dann 139 zuerst zusammen und lässt neu aufnehmen.
  - 143 ändert die Suche (Gewichtung der Überschriften, weichere Stichwortanfrage). `test_ci_questions.py` läuft über die echte Postgres-Suche (`get_search_backend`, `test_ci_questions.py:112`, `:666`); geänderte Menge oder Reihenfolge der Treffer ändert die Nachrichten an das Modell und damit die Schlüssel der Aufzeichnungen (`docs/ARCHITECTURE.md:175`), besonders bei der Kontrollfrage mit `THRESHOLD_OFF`. Weil 143 Stufe C ist und voraussichtlich nach 139 zusammengeführt wird, folgt nach 143 eine weitere Neuaufnahme mit `gemma4:31b-it-qat` (durch die Leitstelle oder einen kleinen Folgeauftrag). Dieser Auftrag nimmt nur gegen die Suche auf `main` auf.
  - 142 und 140 können die Zeile `answers` in `docs/ARCHITECTURE.md:134` ebenfalls berühren. Konflikte löst die Leitstelle beim Zusammenführen; dieser Auftrag ändert dort nur den Teilsatz zur Schwelle.

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit-Code 0.
1. Alle Prüfungen aus `.github/workflows/ci.yml` sind grün, jeweils mit `cp .env.example .env` im Arbeitsverzeichnis und über `docker compose`:
   - Job `backend`: `ruff check .`, `ruff format --check .`, `mypy .`, `pytest`, `pytest -m worker`, Übersetzungskatalog unverändert, `makemigrations --check --dry-run`, Lizenzprüfung, OpenAPI-Schema unverändert.
   - Job `web`: Lint, Typprüfung, Tests, Build, Lizenzprüfung, API-Client unverändert.
   - Job `testfactory`: alle Schritte.
   - Job `e2e`: Playwright grün, insbesondere `answer-page.spec.ts`.
2. `pytest backend/tests/answers/test_ci_questions.py` ist **ohne Ollama** grün (Ollama am Host gestoppt oder nicht erreichbar), mit der neu aufgenommenen `ci_questions.json`.
3. Mit Standardwerten gilt in einem Test: Liegt ein Treffer mit Abstand ≤ 0,55 vor, enthält die Auswahl keinen Treffer mit Abstand > 0,55, außer exakten Treffern. `best_distance` und `hit_count` beziehen sich auf alle Treffer.
4. Die neuen Tests aus Umfang 5 sind vorhanden und grün; keine bestehende Zusicherung ist entfernt oder abgeschwächt (Diff von `test_context.py` zeigt nur Schwelle/Winkel im Aufbau und die neuen Erwartungen der Startwerte).
5. `python -c` mit `django.setup()` ohne gesetzte Variablen ergibt `TWOX_ANSWER_MAX_DISTANCE` 0.55, `TWOX_ANSWER_CONTEXT_CHARS` 16000, `TWOX_ANSWER_MAX_SOURCES` 8, `TWOX_CHAT_TEMPERATURE` 0.0, `TWOX_CHAT_MAX_TOKENS` 1024, `TWOX_CHAT_REASONING_EFFORT` `none` (Test aus Umfang 5 deckt die Antwortwerte ab; die Chat-Werte sind unverändert und nur zu bestätigen).
6. `.env.example` und `settings.py` nennen dieselben Werte; `TWOX_CHAT_MODEL=` ist leer und der Kommentar nennt `gemma4:31b-it-qat` und `qwen3.8:27b-q4_K_M`. `deploy/compose/compose.yaml` ist unverändert.
7. `ci_questions.json` trägt `model` `gemma4:31b-it-qat` und den Digest aus `docs/DECISIONS.md:227`, `prompt_version` unverändert gegenüber `main`. Die Datei enthält nur Modellausgabe, keine fremden Links, keine Personennamen, keine Pfade (Durchsicht durch den Bearbeiter, Diff vollständig geprüft durch die Leitstelle). Der Kurzbericht nennt Modell, Digest, Datum und Dauer des Aufnahmelaufs.
8. `README.md`, `docs/ARCHITECTURE.md` und `backend/tests/answers/recorded/README.md` sind wie in Umfang 6 nachgezogen; keine andere Stelle dieser Dateien ist geändert.
9. Keine neue Abhängigkeit: `backend/pyproject.toml`, Lock-Datei, `web/package.json` und `web/package-lock.json` sind unverändert.
10. Keine Logzeile enthält Frage oder Abschnittstext (bestehender Test `test_logs_hold_neither_question_nor_text_nor_headings`, `test_context.py:684`, bleibt grün).
11. Der Kurzbericht enthält die Prüfanleitung für den Filter (siehe Vorgaben) als lauffähiges Snippet; der Bearbeiter hat es in seinem eigenen Compose-Projekt (`-p twox-139`) einmal fehlerfrei ausgeführt (eine kleine eigene Datenbasis ohne Herstellertexte genügt) und nennt das Ergebnis (nur Zahlen).

## Vorgaben und Hinweise

- **Leitplanken:**
  - 3 (Antworten nur mit Quelle): Der Filter darf die Absage „Dazu finde ich nichts in den Unterlagen.“ nicht umgehen. Ohne relevanten Treffer bleibt `below_threshold` wahr, und das Modell wird nicht gefragt.
  - 4 (Dokumentinhalte sind Daten): An Prompt und Spotlighting ändert sich nichts.
  - 6 (ohne Internet): Tests ohne Netz, Socket-Sperre wie in 135.
  - 7 (Lizenzen): keine neue Abhängigkeit.
  - E-19/E-20: Das Repository ist öffentlich; keine Herstellertexte, keine Auszüge aus Handbüchern, keine Modellantworten zu Herstellerunterlagen im Kurzbericht.
- **Entscheidungen:** E-70 (`docs/DECISIONS.md:80`) ist der Auftrag. E-59 (`:69`): Bei KI aus bleibt alles unverändert (`ContextDisabledError` vor jeder Suche). E-61 (`:71`): Die Übersetzungserkennung bleibt. E-69 D1 (`:79`): nur Modelle mit an der Quelle geprüfter Lizenz und geprüftem Digest.
- **Warum Filter auf Trefferebene:** Siehe Umfang 1. Die Messung aus 128 (0.55 mit Filter: `yaml` 4/10, Kontrollfrage 7 statt 8 Quellen; `probe` 3/10, Kontrollfrage 3 Quellen) wurde genau so erzeugt. Eine andere Stelle könnte andere Ergebnisse liefern als gemessen.
- **Typen:** Jede Funktion hat Typangaben; `mypy .` ohne Fehler. Bezeichner, Docstrings, Kommentare und Meldungen auf Englisch.
- **Neuaufnahme:**
  - Eigenes Compose-Projekt (`-p twox-139`), danach `down -v`.
  - Nicht aufnehmen, während ein anderer Lauf (Messlauf, anderer Auftrag) dasselbe Modell am Host nutzt (Befund B7 aus 128). Vorher über `/api/ps` lesend prüfen.
  - Keine Einstellung am Host ändern; `OLLAMA_CONTEXT_LENGTH=16384` ist schon gesetzt (E-70).
- **Messungen auf der Testumgebung 2x** (Hauptordner, eingelesene Handbücher) führt die Leitstelle nach dem Zusammenführen aus. Dieser Auftrag misst dort nichts und ändert die `.env` des Hauptordners nicht.
- **Prüfanleitung für den Filter auf 2x (für die Leitstelle, Messlauf 144 Schritt 3).** `SourceRef` und `ContextSource` (`backend/twox/answers/types.py:71-95`) tragen keinen Abstand; der Nachweis läuft daher über die Suche selbst. Der Bearbeiter liefert im Kurzbericht ein kurzes, lauffähiges Snippet für `docker compose run --rm backend-dev python manage.py shell -c "…"` (nicht im Repository abgelegt), das für eine Frage:
  - `select_context(question)` mit Standardwerten aufruft (`context.py:148`, ohne Nachbarn),
  - dieselbe Suche wie die Kontextauswahl ausführt (`SearchRequest` mit `limit=min(MAX_LIMIT, 2 * k)`, `context.py:180-187`) und je Treffer `section_id`, `semantic_distance` und `MatchKind.EXACT in match_kinds` bereitstellt (`backend/twox/search/interface.py:118-149`),
  - je Quelle (`section_id` bzw. die Abschnitte ihrer `locations`) den zugehörigen Treffer findet und prüft: Abstand ≤ 0,55 oder exakter Treffer,
  - nur Zahlen und Kennungen ausgibt (Quellnummer, `section_id`, Abstand, exakt ja/nein, `best_distance`, `hit_count`), keine Frage, keinen Abschnittstext, keine Überschriften.
  Die Leitstelle wendet es auf die Kontrollfrage und Frage 8 an; 144 übernimmt es in Schritt 3.
- **Ablauf:** Commits klein und nur auf dem Auftragszweig; kein Push (E-14). Kurzbericht in diese Datei.
- **Herkunft:** Kurzbericht 128 (Empfehlung Startwerte, Option (a)), E-70, Vorgabe der Leitstelle.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine. Die Werte und der Filter sind in E-70 entschieden. Kommt beim Aufnahmelauf mit gemma4 eine Prüfung nicht durch, gilt Umfang 4 (Status „wartet auf a7“, Optionen durch die Leitstelle).

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
