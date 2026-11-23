# Auftrag 143 – Suche: Überschriften stärker gewichten und Fragen weicher suchen (D12 b)

Meilenstein: M3 · Freigabestufe: C · Status: zurückgenommen (E-73; Revert auf main, Code und Bericht bleiben im Verlauf)

Stufe C nach E-70 und D12: Die Stichwortsuche ändert ihr Verhalten für alle Aufrufer (Suchseite und Auskunft), und falls der Ausdruck des Stichwortindex (`Section.search_vector`) geändert wird, ändert sich das Datenmodell der Suche (Migration). Zusammenführen und Neuaufbau des Stichwortindex in der Testumgebung „2x“ erst nach Freigabe durch a7; die Leitstelle führt Migration und Messung dort aus.

## Ziel

Der Messlauf 128 (gemma4 4/10, qwen 2/10) und die Suchgrundlinie 120 zeigen für die Prüffragen 3, 4, 6 und 7 denselben Befund B1: Mit dem Wortlaut aus `testfactory/questions.yaml` liegt die Belegstelle nicht unter den k Quellen. Die Stichwortsuche trägt dazu nichts bei: Bei ganzen Fragen liefert sie keinen einzigen Treffer (alle Werte 0, Bericht 120, Messung vom 22.11.2026), alles kommt aus der Vektorsuche.

Nach diesem Auftrag liefert die Stichwortsuche auch für Fragen in Satzform eine Trefferliste, in der Abschnitte mit den Inhaltswörtern der Frage in der Überschrift deutlich vorne stehen. Exakte Suche nach Kennungen (063, 067, E-61) und die Messwerte der M2-Probe bleiben mindestens so gut wie heute.

## Umfang

### 1. Analyse am Code (Ergebnis in den Kurzbericht)

Am Code bestätigen oder widerlegen, mit Datei:Zeile:

- **Warum ganze Fragen keine Stichworttreffer liefern.** Vermutung der Leitstelle: `websearch_to_tsquery` verknüpft alle Wörter mit UND (`&`). Die Anfrage wird je Konfiguration `simple`, `german`, `english` geparst (`backend/twox/search/postgres.py:334-345`), die drei Anfragen werden nur untereinander mit ODER verbunden (`_Queries.combined`, `postgres.py:190-193`), und die Bedingung ist `s.search_vector @@ tsquery` (`postgres.py:359`). Innerhalb jeder Konfiguration muss also jedes Wort der Frage im Abschnitt stehen. In `simple` gehören dazu auch Stoppwörter wie „mit“, „welchem“, „der“; in `german` und `english` alle Inhaltswörter einer langen Frage. Mit SQL-Beispielen aus selbst geschriebenen Texten belegen (Ausgabe von `websearch_to_tsquery` für eine Frage wie Prüffrage 3 in allen drei Konfigurationen).
- **Wie Überschriften heute gewichtet sind.** `search_vector` ist eine gespeicherte generierte Spalte (`backend/twox/ingest/models.py:282-287`) mit `setweight(..., 'A')` für `heading_text` und `'B'` für `text`, je Konfiguration (`models.py:222-238`). `heading_text` ist der Überschriftenpfad, verbunden mit „ > “ (`models.py:49`, `models.py:241-243`, gefüllt in `save()` `models.py:348-352` und `section_rows` `models.py:405`). Gerankt wird mit `ts_rank(s.search_vector, tsquery, 32)` ohne eigene Gewichte (`postgres.py:495-499`, `RANK_NORMALIZATION` `postgres.py:146`), also mit den PostgreSQL-Standardgewichten D 0,1 · C 0,2 · B 0,4 · A 1,0 (Docstring `postgres.py:46-47`). Überschriften haben damit **schon** Gewicht A. Bestehender Test: `backend/tests/search/test_keyword_search.py:281` (`test_heading_matches_rank_above_text_matches`).
- Folgerung festhalten: Das Gewicht A allein hilft nicht, solange die UND-Bedingung bei Fragen nichts durchlässt. Die Änderung muss vor allem an der Anfrage ansetzen; eine stärkere Gewichtung der Überschriften wirkt erst danach.

### 2. Umsetzung (nach Wahl, mit Begründung im Kurzbericht)

**a) Weichere Stichwortanfrage für Fragen.** Für eine Anfrage in Satzform (Vorschlag: dieselbe Regel wie E-61, also mehr als `EXACT_FIRST_MAX_OTHER_WORDS` andere Wörter neben den Kennungen, `other_words` `postgres.py:283-299`, `EXACT_FIRST_MAX_OTHER_WORDS` `postgres.py:153`) werden die Inhaltswörter mit ODER verknüpft statt mit UND:

- **Stoppwörter fallen weg**, auch in `simple`: Ein Wort, das `german` **oder** `english` als Stoppwort verwirft, kommt in der weichen Anfrage nicht vor (sonst trifft „der“ fast jeden Abschnitt; „der“, „mit“, „welchem“ sind nur deutsche, „the“ nur ein englisches Stoppwort). Kennungen (`twox.search.identifiers.find_identifiers`) bleiben immer erhalten. Den Grenzfall „englisches Stoppwort, das im Deutschen ein Inhaltswort ist“ (und umgekehrt) im Kurzbericht prüfen und mit Beispiel festhalten.
- **Rangfolge:** Abschnitte, die alle Inhaltswörter enthalten (der heutige UND-Treffer), stehen in der Stichwortliste vor Teiltreffern; innerhalb davon nach `ts_rank` (bzw. Abdeckung und Rang, nach Wahl). So bleibt die Suchseite für Mehrwortanfragen mindestens so genau wie heute; die Fragen bekommen überhaupt eine Liste.
- **Ausschlüsse** (`-wort`, `-"zwei wörter"`) gelten unverändert: Sie werden heute schon getrennt geprüft (`_Queries.exclusions` `postgres.py:200-207`, `_exclusion_condition` `postgres.py:375-383`, angewandt in `postgres.py:492` und `postgres.py:545`) und dürfen in der weichen Anfrage nicht zu positiven Wörtern werden.
- **Phrasen** (`"…"`, auch `PLC-01`) bleiben als Einheit (`<->`) erhalten; die Nachprüfung über die Naht der Konfigurationen (`_keyword_condition` `postgres.py:352-372`, `_GAP_LEXEME` `postgres.py:167`) muss für die weiche Anfrage weiter stimmen.
- **Hervorhebungen** (`_keyword_spans` `postgres.py:861-885`) nutzen die weiche Anfrage, markieren also keine Stoppwörter.
- Möglichst ohne zusätzliche Datenbankabfrage: `test_search_needs_three_queries` (`test_keyword_search.py:771`) soll grün bleiben. Lässt sich das nicht halten, Begründung unter „Abweichungen“.
- Anfragen aus Kennungen (`192.168.0.100`, `E1234`, `Fehler E1234`, `PLC-01 Adresse`) und Anfragen mit höchstens einem anderen Wort laufen **unverändert** (gleiche SQL, gleiche Treffer, gleiche Reihenfolge). `exact_hits_first` (`postgres.py:302-323`) und die Fusion (`postgres.py:517-559`) bleiben unverändert.

**b) Überschriften stärker gewichten.** Zwei Wege, einer davon oder beide, mit Begründung:

- (b1) **nur im Ranking:** `ts_rank` mit eigenem Gewichtsvektor (z. B. `'{0.1, 0.2, 0.2, 1.0}'`) statt der Standardgewichte, als benannte Konstante neben `RANK_NORMALIZATION`. Kein Neuaufbau nötig.
- (b2) **im Index:** Änderung des Ausdrucks in `search_vector_expression` (`models.py:222-238`), z. B. Überschriften zusätzlich in eine weitere Gewichtsstufe. Dann gilt Punkt 3.

Empfehlung der Leitstelle: zuerst (a) mit (b1); (b2) nur, wenn die Tests mit selbst geschriebenen Texten zeigen, dass (b1) nicht reicht.

### 3. Neuberechnung des Stichwortindex ohne neues Einlesen

- Wird der Ausdruck von `search_vector` geändert (b2): eine Migration in `backend/twox/ingest/migrations/` (nächste Nummer nach `0003_ingestjob_conversion_error_count.py`), die die generierte Spalte in der Datenbank neu berechnet – **ohne** Docling, **ohne** neue Einbettungen. Prüfen, wie Django die Änderung eines `GeneratedField` umsetzt (ggf. Feld entfernen und neu anlegen statt `AlterField`); der GIN-Index `ingest_section_search_gin` (`models.py:329`) muss danach wieder bestehen. `embedding` und `embedding_model` aller Abschnitte bleiben unverändert (Test). Die Laufzeit für ca. 5 000 Abschnitte (Stand „2x“ laut 120) grob abschätzen und im Kurzbericht nennen (Sperre auf `ingest_section` während der Migration).
- Bleibt der Ausdruck unverändert (nur a und b1): Es ist kein Neuaufbau nötig, weil die Änderung nur die Anfrage betrifft. Das steht mit Begründung im Kurzbericht; Punkt 3 entfällt dann.
- Kein eigener Verwaltungsbefehl, solange die Migration (bzw. die generierte Spalte) die Neuberechnung leistet.

### 4. Tests (`backend/tests/search/`)

Alle Texte selbst geschrieben, Embedder nur als Attrappe (`backend/tests/search/fake_embedder.py`), nie echtes Ollama. Neue Tests bevorzugt in einer eigenen Datei (z. B. `backend/tests/search/test_question_keywords.py`):

- Eine Frage in Satzform (Muster der Prüffrage 3, eigene Wörter und eigener Text) findet per Stichwort einen Abschnitt, der nur einen Teil der Inhaltswörter enthält; heute (UND) fände sie ihn nicht.
- Ein Abschnitt mit allen Inhaltswörtern steht vor einem Teiltreffer; ein Abschnitt mit Inhaltswörtern in der Überschrift steht vor einem mit denselben Wörtern nur im Text.
- Ein Abschnitt, der nur Stoppwörter der Frage enthält („mit“, „der“, „welchem“, „the“), wird per Stichwort nicht gefunden und nicht hervorgehoben.
- Kennungsanfragen und Anfragen mit höchstens einem anderen Wort: gleiche Treffer und gleiche Reihenfolge wie vor der Änderung (Vergleich mit festgehaltener Erwartung, Muster `test_keyword_search.py:159-250` und `test_fusion.py:316`).
- Ausschluss und ausgeschlossene Phrase gelten auch bei einer Frage in Satzform; Phrasen in einer Frage bleiben Phrasen.
- Fusion mit Vektorliste: eine Frage, deren Belegstelle in der Stichwortliste jetzt einen Rang hat, steigt im kombinierten Ergebnis gegenüber nur Vektor (von Hand nachgerechnet wie `test_fusion.py:94` und `test_fusion.py:250`).
- Bei (b2): Migrationstest – nach der Migration hat jeder bestehende Abschnitt einen neu berechneten `search_vector`, `embedding`/`embedding_model` unverändert, GIN-Index vorhanden.
- Bestehende Tests in `backend/tests/search/` werden nur geändert, wenn sie nachweislich an der UND-Semantik für Fragen hängen; jede solche Änderung steht unter „Abweichungen“.
- **Tests außerhalb von `backend/tests/search/` werden nicht angepasst.** Insbesondere `backend/tests/answers/test_ci_questions.py` nutzt die echte Postgres-Suche (`get_search_backend`, `test_ci_questions.py:112`, `:666`; `service.answer` `:332`), und der Schlüssel jeder CI-Aufzeichnung hängt an den Nachrichten an das Modell, also an Quellen und Reihenfolge (`docs/ARCHITECTURE.md:175`). Mit `THRESHOLD_OFF = 2.0` (`test_ci_questions.py:143`) gehen alle Treffer der Fusion in den Kontext; ändert die weiche Anfrage Menge oder Reihenfolge, folgt `RecordingMissingError`. Auch `backend/tests/answers/test_context.py` (Auftrag 139) kann betroffen sein. Bricht dort oder in einem anderen Test außerhalb von `backend/tests/search/` etwas: nichts anpassen, nichts neu aufnehmen, betroffene Tests mit Fehlermeldung in den Kurzbericht, Status „wartet auf a7“. Die Neuaufnahme der CI-Antworten nach dem Zusammenführen von 143 übernimmt die Leitstelle bzw. ein kleiner Folgeauftrag.

### 5. Messung

- Im eigenen Arbeitsverzeichnis nur mit Testdaten (Tests oben). Kein Lauf gegen die Datenbank der Testumgebung „2x“, keine Migration dort.
- Für die Leitstelle im Kurzbericht die genauen Befehle für den Vorher-nachher-Vergleich nach dem Zusammenführen: `evaluate_search --probes m2` und `evaluate_search --probes m3 --cutoffs 5,8,10,12` (Text und `--json`), dazu bei (b2) `migrate` vorher. Die Stichwortart misst `evaluation.py:895` über `keyword_only=True`; ihre Werte sollen für Fragen nicht mehr alle 0 sein.

### 6. Doku

- Modul-Docstring von `postgres.py` (Abschnitt „keyword“, `postgres.py:12-16`, und Score `postgres.py:45-50`): weiche Anfrage für Fragen, Stoppwörter, Rangfolge, ggf. Gewichte.
- Docstring von `search_vector_expression` nur bei (b2).
- `docs/ARCHITECTURE.md`, nur der Punkt „Keyword“ im Abschnitt Suche (Z. 378) und ein Satz in „Ranking“ (Z. 713); keine anderen Abschnitte.

## Nicht-Ziele

- Kein Reranker, kein Umformulieren der Frage durch das Modell (D12 c, d).
- Keine Änderung an Vektorsuche, Einbettungen, Abschnittsgröße, Einbettungsmodell (E-60) oder HNSW-Einstellungen.
- Keine Änderung an `exact_hits_first`, an der Fusion (RRF, `RRF_K`) und an E-61.
- Keine Änderung an Auskunft, Kontextauswahl, Prompt, Zitatprüfung (`backend/twox/answers/`).
- Keine Änderung an den Proben `backend/twox/search/probes/m2.json`, `m3.json` und an `testfactory/questions.yaml`.
- Kein neues Einlesen mit Docling, keine neuen Einbettungen, keine Änderung an `docling-serve`.
- Keine Änderung an öffentlicher Such-API, OpenAPI-Schema oder Oberfläche (`web/`).

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/search/postgres.py` (Anfrage, Ranking, Docstring)
- bei Bedarf `backend/twox/search/identifiers.py` nur lesend nutzen, nicht ändern
- nur bei (b2): `backend/twox/ingest/models.py` (ausschließlich `search_vector_expression` und Docstring) und eine neue Migration in `backend/twox/ingest/migrations/`
- `backend/tests/search/` (neue Testdatei; bestehende nur wie unter 4. beschrieben)
- `docs/ARCHITECTURE.md`, nur die unter 6. genannten Punkte
- Kurzbericht in dieser Datei

**Nicht anfassen** (parallele Aufträge 139–142): `backend/twox/answers/` (insbesondere `context.py`, Auftrag 139), `backend/tests/answers/` einschließlich `test_ci_questions.py`, `test_context.py` und der Aufzeichnungen unter `recorded/` (keine Neuaufnahme), `backend/twox/search/evaluation.py`, `backend/twox/search/management/commands/evaluate_search.py`, `backend/twox/search/interface.py`, `backend/twox/search/api.py`, Proben, `testfactory/`, `web/`, `docs/STATUS.md`, `docs/DECISIONS.md`.

## Akzeptanzkriterien (prüfbar)

1. Der Kurzbericht enthält die Analyse aus 1. mit Datei:Zeile und SQL-Beispiel (selbst geschriebener Text): Ursache der fehlenden Stichworttreffer und heutige Gewichtung der Überschriften.
2. Eine Frage in Satzform liefert per Stichwort Treffer, auch wenn kein Abschnitt alle Inhaltswörter enthält; Abschnitte mit allen Inhaltswörtern und mit Treffern in der Überschrift stehen vorne (Tests aus 4.).
3. Stoppwörter allein führen zu keinem Stichworttreffer und keiner Hervorhebung (Test).
4. Kennungsanfragen und Anfragen mit höchstens einem anderen Wort liefern dieselben Treffer in derselben Reihenfolge wie vorher; alle bestehenden Tests in `test_keyword_search.py` und `test_fusion.py` sind grün, Änderungen daran nur wie unter 4. begründet.
5. Ausschlüsse und Phrasen verhalten sich wie vorher, auch in Fragen (Tests).
6. Bei (b2): Migration rechnet `search_vector` für alle Abschnitte neu, ohne Docling und ohne Einbettungen; Migrationstest grün; `makemigrations --check` sauber. Ohne (b2): Begründung im Kurzbericht, warum kein Neuaufbau nötig ist.
7. Alle Prüfungen aus `.github/workflows/ci.yml` sind grün: `ruff check`, `ruff format --check`, `mypy`, `pytest`, `pytest -m worker`, Übersetzungskatalog aktuell, `makemigrations --check --dry-run`, Lizenzprüfung, OpenAPI-Schema aktuell, sowie die Jobs `web`, `testfactory` und `e2e` (`ci.yml:201-244`; `web/e2e/search.spec.ts` und `m2-acceptance.spec.ts` prüfen die Suchseite, deren Mehrwortanfragen sich ändern). Bricht ein Test außerhalb von `backend/tests/search/`, gilt die Regel aus 4. (nicht anpassen, Kurzbericht, „wartet auf a7“).
8. Keine neue Abhängigkeit.
9. Messung durch die Leitstelle in „2x“ nach dem Zusammenführen (nicht Teil der Abnahme des Zweigs, aber Voraussetzung für das Abschließen des Auftrags):
   - `--probes m2` nicht schlechter als nach 067/090 (`docs/ARCHITECTURE.md:713`, Bericht 067 Z. 134): kombiniert Recall@5 ≥ 0,571, Recall@10 ≥ 0,857, MRR ≥ 0,535; Ränge ip-ccu ≤ 2, ip-drill-plc ≤ 10, question-1, question-9, question-10 je Rang 1, question-7 ≤ 7.
   - `--probes m3 --cutoffs 5,8,10,12`: Recall@10 der Fragen 3, 4, 6, 7 (einschließlich 3b, 7b) besser als in 120 (3, 3b, 4, 7b nicht in Top 10; 6 Rang 4; 7 Rang 7), oder für jede nicht verbesserte Frage eine Begründung (z. B. Fachbegriff nur in Tabelle oder Abbildungsunterschrift, nicht in Überschrift oder Fließtext). Die Stichwortspalte ist für Fragen nicht mehr durchweg 0.
   - Kontrollprobe (control-11, `m3.json:225-228`, ohne erwartete Fundstellen): mit `--distance` kleinster Abstand unter den ersten 10 Einträgen der kombinierten Suche und Rang des ersten Eintrags ohne Abstand im Bericht, vorher und nachher; der Abstand zur Schwelle 0,55 (E-70) wird nicht kleiner. Auffälligkeiten (viele Teiltreffer) im Bericht.

## Vorgaben und Hinweise

- **Antworten nur mit Quelle (Leitplanke 3):** Die Änderung betrifft nur, welche Abschnitte gefunden werden; jeder Treffer behält seine Fundstelle (Dokument, Version, Seite, Überschriftenpfad).
- **Dokumentinhalte sind Daten, keine Anweisungen (Leitplanke 4):** Texte aus Handbüchern werden nie als Anweisung gelesen; Testtexte selbst schreiben.
- **Keine Herstellertexte im Repository:** keine Auszüge aus den Handbüchern der Testfabrik in Tests, Doku oder Kurzbericht; Fundstellen nur mit Kennung, Seite und Prüfsummenpräfix.
- **Keine neue Abhängigkeit**; alles mit PostgreSQL-Bordmitteln (`websearch_to_tsquery`, `to_tsquery`, `ts_rank`/`ts_rank_cd`, `ts_lexize` o. Ä.).
- SQL nur mit benannten Parametern; Konfigurationsnamen nur über `_configs()` (`postgres.py:326-331`) in SQL.
- Zugriffe nur über die Suchschnittstelle; `SearchRequest`/`SearchHit` bleiben unverändert.
- Typangaben für jede Funktion; Bezeichner, Docstrings, Commit-Nachrichten auf Englisch.
- Alles über `docker compose` im eigenen Arbeitsverzeichnis; nichts global installieren.
- **Messungen auf der Testumgebung „2x“ führt die Leitstelle nach dem Zusammenführen aus**, ebenso eine etwaige Migration dort. Der Auftragsbearbeiter greift nicht auf die Datenbank der Testumgebung zu.
- Nicht pushen (E-14). Commits klein und nachvollziehbar auf dem eigenen Zweig.
- Bei Widerspruch zwischen Analyse und Annahmen dieses Auftrags: im Kurzbericht festhalten, nicht raten; bei Bedarf Frage an a7 ergänzen und Status „wartet auf a7“.

## Fragen an a7 (mit Optionen und Empfehlung)

1. **Wirkung auf die Suchseite.** Die weichere Anfrage gilt für alle Aufrufer der Suche, also auch für Mehrwortanfragen auf der Suchseite.
   - (a) Weiche Anfrage für Anfragen mit mehr als einem anderen Wort (Regel wie E-61), UND-Treffer stehen in der Stichwortliste vor Teiltreffern. Suchseite bleibt oben gleich genau, zeigt darunter mehr Treffer.
   - (b) Weiche Anfrage nur als Rückfall, wenn die UND-Anfrage nichts findet.
   - (c) Weiche Anfrage nur für die Auskunft über ein neues Feld in `SearchRequest`; ändert die Schnittstelle und berührt `backend/twox/answers/` (Konflikt mit 139).
   - Empfehlung: (a). (b) hilft bei Fragen, bei denen die UND-Anfrage einen einzigen schwachen Treffer findet, nicht; (c) widerspricht der Trennung der parallelen Aufträge.
   - Bis zur Antwort von a7 setzt der Auftragsbearbeiter die Empfehlung (a) um; entscheidet a7 anders, folgt Nacharbeit.
   - **Umgesetzt: (a)** (Auftragsbearbeiter, 23.11.2026).

2. **Rote Tests außerhalb von `backend/tests/search/`** (vom Auftragsbearbeiter ergänzt). Nach Regel 4 nicht angepasst und nicht neu aufgenommen:
   - `tests/answers/test_ci_questions.py` (7 Tests: `test_fact_question[ai-on-ci-fact-1]`, `[ai-on-ci-fact-2]`, `test_evaluate_with_the_small_question_set`, `test_control_question_without_threshold_plays_the_refusal`, `test_cancelling_closes_the_stream_of_the_replay`, `test_no_log_line_holds_a_question_an_answer_or_a_section_text`, `test_recording_file`): `RecordingMissingError: no recording for this prompt (prompt_version=64267b8d166e, model=qwen3.8:27b-q4_K_M, question=ci-fact-1)` (bzw. `ci-fact-2`). Erwartet: Die CI-Fragen sind Fragen in Satzform, die Stichwortliste enthält jetzt Teiltreffer, Quellen und Reihenfolge im Kontext ändern sich, damit der Schlüssel der Aufzeichnung.
   - `tests/acceptance/test_m2.py::test_search_answers_a_question_in_other_words_by_meaning[ai-off]`: `assert {'semantic': ... 'hits': [...]} == {'semantic': 'disabled', 'hits': []}`; `[ai-on]`: `assert ['keyword', 'semantic'] == ['semantic']`. Der Test setzt voraus, dass die Frage „Wer ist sachverständig genug für eine Aufgabe nach dieser Regel?“ per Stichwort nichts findet („none of the words matches“, `test_m2.py:373`); mit der weichen Anfrage trifft jetzt ein Inhaltswort der Frage. Hängt nachweislich an der UND-Semantik, liegt aber außerhalb meines Bereichs.
   - Optionen: (a) Folgeauftrag nach dem Zusammenführen: CI-Antworten neu aufnehmen (`record_answers`) und in `test_m2.py` die Erwartung anpassen (KI aus: Stichworttreffer erlaubt, Belegstelle nicht verlangt; KI an: erster Treffer bleibt die Belegstelle, Art `keyword`+`semantic` zulassen) bzw. eine Frage ohne gemeinsames Inhaltswort wählen. (b) 143 verwerfen bzw. auf Option (b) aus Frage 1 (nur Rückfall) umbauen. **Empfehlung: (a)**; die Leitstelle hatte die Neuaufnahme für `test_ci_questions.py` bereits vorgesehen, `test_m2.py` kommt dazu.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: wartet auf a7** (Frage 2: 9 Tests außerhalb von `backend/tests/search/` rot, wie im Auftrag vorhergesehen). Läufe am 23.11.2026 im Container, Compose-Projekt `twox-143`, `TWOX_API_PORT=18143`. Umgesetzt: (a) weiche Anfrage für Fragen + (b1) Gewichte nur im Ranking. Kein (b2), keine Migration, keine neue Abhängigkeit. „2x“ und „twox-leit“ nicht angefasst.

### 1. Analyse am Code (Stand `main` vor 143)

**Warum ganze Fragen keine Stichworttreffer liefern – bestätigt.**
- `_parse_queries` (`backend/twox/search/postgres.py:334-345`) parst die ganze Anfrage je Konfiguration mit `websearch_to_tsquery`. Diese Funktion verbindet alle Wörter außerhalb von `or` mit `&`. `_Queries.combined` (`postgres.py:190-193`) verbindet nur die drei Konfigurationen mit `|`; die Bedingung ist `s.search_vector @@ %(tsquery)s::tsquery` (`postgres.py:359`). In einer Konfiguration muss also jedes Wort stehen.
- SQL-Beleg mit Prüffrage 3 (Wortlaut aus `testfactory/questions.yaml`, eigener Text des Projekts) – `SELECT websearch_to_tsquery(c, '<Frage>')::text`:
  - `simple`: `'über' & 'welches' & 'protokoll' & 'tauschen' & 'die' & 'txt-controller' <-> 'txt' <-> 'controller' & 'daten' & 'mit' & 'der' & 'zentralsteuerung' & 'aus'` – auch die Stoppwörter „über“, „welches“, „die“, „mit“, „der“, „aus“ müssen im Abschnitt stehen.
  - `german`: `'protokoll' & 'tausch' & 'txt-controll' <-> 'txt' <-> 'controll' & 'dat' & 'zentralsteuer'` – Stoppwörter fallen weg, aber alle fünf Inhaltswörter (eins als Phrase) sind Pflicht.
  - `english`: wie `simple`, nur gestemmt (`'welch'`, `'protokol'` …); deutsche Stoppwörter bleiben Pflicht.
  - Selbst geschriebener Abschnitt, Überschrift „Kommunikation > Protokolle“, Text „Die Steuerungen senden ihre Daten per MQTT an den Broker.“ (`search_vector` wie in `models.py` gebaut): `@@` alte Anfrage = **false** in allen drei Konfigurationen, obwohl „Protokolle“ in der Überschrift und „Daten“ im Text stehen. Mit der neuen Anfrage: `matching` = **true**, `every` = false, `ts_rank` mit Fragegewichten 0,064.
- **Überschriften sind heute schon Gewicht A – bestätigt.** `search_vector` ist eine gespeicherte generierte Spalte (`backend/twox/ingest/models.py:282-287`) aus `search_vector_expression` (`models.py:222-238`): `setweight(..., 'A')` für `heading_text`, `'B'` für `text`, je Konfiguration. `heading_text` ist der Pfad mit „ > “ (`models.py:48`, `join_headings` `models.py:241-243`, gesetzt in `save()` `models.py:350`, in `section_rows` `models.py:405`); GIN-Index `models.py:329`. Gerankt wurde mit `ts_rank(s.search_vector, tsquery, 32)` (`postgres.py:495-499`, `RANK_NORMALIZATION` `postgres.py:146`), also D 0,1 · C 0,2 · B 0,4 · A 1,0. Test `test_keyword_search.py:281` belegt Überschrift vor Text.
- **Folgerung:** Gewicht A hilft nicht, solange die UND-Bedingung bei Fragen nichts durchlässt. Die Änderung setzt an der Anfrage an; die stärkere Gewichtung (b1) wirkt erst danach, innerhalb der Teiltreffer.

### Was wurde gebaut?

`backend/twox/search/postgres.py`:
- `is_question(query)`: dieselbe Regel wie E-61, `len(other_words(query)) > EXACT_FIRST_MAX_OTHER_WORDS`. Für alle anderen Anfragen bleibt der Code-Pfad unverändert (`_parse_queries`, gleiches SQL – per Test mit SHA-256 des SQL vor 143 belegt).
- `query_units(query)`: Wörter und Phrasen der Anfrage wie eingegeben; Phrasen (`"…"`, auch offen am Ende) bleiben eine Einheit; Ausschlüsse (`-wort`, `-"zwei wörter"`) und Teile ohne Buchstabe/Ziffer fallen weg.
- `_parse_question`: **eine** Abfrage statt zwei – die ganze Anfrage je Konfiguration (wie bisher, für die Ausschlüsse) und zusätzlich jede Einheit einzeln je Konfiguration (`ARRAY(SELECT websearch_to_tsquery('<config>', u.unit) FROM unnest(%(units)s::text[]) WITH ORDINALITY …)`). Benannte Parameter, Konfigurationsnamen nur über `_configs()`.
- `_build_question` → `_Question` mit drei `_Queries`:
  - **Stoppwörter:** Eine Einheit, die `german` oder `english` leer parst, fällt in allen drei Konfigurationen weg (auch in `simple`). Kennungen (`find_identifiers`) bleiben immer. Eine Einheit mit Negation (`!`) ist nie ein positives Wort.
  - `matching` (wer trifft): ODER über die Inhaltswörter **ohne** Kennungen; nur wenn die Frage außer Kennungen kein Inhaltswort hat („Was ist E1234?“), die Kennungen. Begründung siehe Abweichung 1.
  - `every` (wer zuerst kommt): UND über alle Inhaltswörter und Kennungen.
  - `ranking`: ODER über alle Inhaltswörter und Kennungen, für `ts_rank` und Hervorhebungen.
- `_search_sql(..., question=…)`: Bei einer Frage `keyword_match` = `matching` (mit der Nachprüfung über die Naht wie bisher, `_keyword_condition`), zusätzliche Spalte `keyword_every` (Parameter mit Präfix `every_`), Stichwortrang `DENSE_RANK() OVER (… ORDER BY c.keyword_every DESC, c.rank DESC)`, `rank` = `ts_rank('{0.1, 0.2, 0.2, 1.0}'::float4[], s.search_vector, %(rank_tsquery)s, 32)`. Ohne Frage entsteht byte-gleich das bisherige SQL. Ausschlüsse kommen weiter aus der ganzen Anfrage (`queries.exclusions()`), Vektorsuche, `exact_hits_first` und Fusion unverändert.
- (b1) `QUESTION_RANK_WEIGHTS = (0.1, 0.2, 0.2, 1.0)` neben `RANK_NORMALIZATION`, nur für Fragen (andere Anfragen behalten die Standardgewichte, damit ihr SQL gleich bleibt). Wirkung (SQL-Messung mit selbst geschriebenen Texten): Ein Fragewort in der Überschrift gegen drei Fragewörter im Text – Standardgewichte 0,120 gegen 0,141 (Text vorn), Fragegewichte 0,120 gegen 0,076 (Überschrift vorn). Test `test_heading_word_outranks_more_words_in_the_text`.
- Hervorhebungen nutzen bei Fragen `ranking`, also keine Stoppwörter.
- Modul-Docstring (Abschnitt „keyword“ und „Score“), Docstrings der neuen Funktionen und von `_search_sql`.
- `docs/ARCHITECTURE.md`: nur Punkt „Keyword“ im Abschnitt Search und ein Satz unter „Ranking“ (Grenzen).

**Grenzfall Stoppwörter (geprüft mit `websearch_to_tsquery` je Konfiguration):** Englische Stoppwörter, die im Deutschen Inhaltswörter sind, fallen weg: „Not“ (Not-Fall; `english` leer, `german` `'not'`), „most“ (Most), „once“, „over“. Deutsche Stoppwörter, die im Englischen Inhaltswörter sind: „man“, „war“, „hat“, „bin“, „die“ (engl. Matrize), „will“. Eine Frage, die nur über ein solches Wort trifft, findet per Stichwort nichts mehr; sie bleibt der Vektorsuche überlassen. Test `test_english_stop_word_that_is_a_german_word_is_left_out` („Was tun bei Not am Schaltschrank?“ findet den Abschnitt mit „Not“ nicht). Bindestrich-Wörter wie „Not-Halt“ bleiben erhalten (`english` liefert `'not-halt' <-> …`). „beim“ ist in PostgreSQL kein deutsches Stoppwort und bleibt ein Wort.

**Punkt 3 entfällt:** Ausdruck von `search_vector` unverändert (kein b2). Die Änderung betrifft nur die Anfrage und das Ranking zur Abfragezeit; `search_vector`, GIN-Index, Einbettungen bleiben, daher kein Neuaufbau, keine Migration, kein Neueinlesen. `makemigrations --check` sauber.

### Wie wurde getestet?

Neu `backend/tests/search/test_question_keywords.py` (21 Testfunktionen, alle Texte selbst geschrieben, Embedder nur `FakeEmbedder`):
- Regel `is_question`, `query_units`, `_build_question` (Stoppwörter, Negation, Kennung, Frage nur aus Kennung und Stoppwörtern).
- Teiltreffer: Frage nach Muster Prüffrage 3 findet einen Abschnitt mit nur „Roboter“; Nachweis per SQL, dass die alte UND-Anfrage ihn nicht trifft.
- Alle Inhaltswörter vor Teiltreffer (auch wenn der Teiltreffer die Wörter in der Überschrift hat); Überschrift vor gleichen Wörtern im Text; Überschriftswort vor drei Textwörtern (b1, gegen Standardgewichte).
- Stoppwörter allein: kein Treffer, keine Hervorhebung („Der“ wird nicht markiert); Frage nur aus Stoppwörtern findet per Stichwort nichts; Grenzfall „Not“.
- Ausschluss und ausgeschlossene Phrase in Fragen; Phrase bleibt Phrase; Naht der Konfigurationen in einer Frage.
- Unverändert: für `192.168.0.100`, `E1234`, `Fehler E1234`, `PLC-01 Adresse`, `Pumpe`, `pump -valve` Treffer und Reihenfolge auf einem festen Korpus **und** SHA-256 des SQL (Parse- und Suchabfrage, Parameter eingesetzt) – beides vorher mit dem Code von `main` aufgezeichnet (Datei vorübergehend getauscht, danach wiederhergestellt).
- Drei Abfragen auch für eine Frage (`test_question_needs_three_queries`; `test_search_needs_three_queries` mit „chi belt“, jetzt eine Frage, bleibt grün).
- Fusion von Hand: Belegstelle Vektorrang 3, Stichwortrang 1 über die Überschrift → 1/61 + 1/63 = 0,032266, steigt von Platz 3 auf 1; E-61-Fall: Abschnitt, der nur „XR7“ nennt, bekommt keinen Stichwortrang und überholt die Antwort nicht.

Prüfungen (je im Container, Projekt `twox-143`):

| Prüfung | Ergebnis |
| --- | --- |
| `ruff check .` | All checks passed |
| `ruff format --check .` | 232 files already formatted |
| `mypy .` | Success: no issues found in 228 source files |
| `pytest tests/search` | 471 passed |
| `pytest` (alle) | **9 failed**, 3451 passed, 6 deselected – alle 9 außerhalb von `tests/search`, siehe Frage 2 |
| `pytest -m worker` | nicht separat gelaufen (keine Worker-Datei berührt; im vollen Lauf deselektiert) |
| `makemessages -l de` | Exit 0, kein Unterschied |
| `makemigrations --check --dry-run` | No changes detected |
| Lizenzprüfung | Exit 0 |
| `spectacular` | Exit 0, kein Unterschied in `web/openapi` |
| e2e (`--profile e2e run e2e`, Schritte wie `ci.yml`) | 88 passed, 1 skipped, Exit 0 |
| Jobs `web`, `testfactory` | nicht gelaufen: keine Datei unter `web/` oder `testfactory/` geändert, Schema unverändert |

Danach `docker compose -p twox-143 --profile dev --profile e2e down -v` Exit 0, kein Container und kein Volume `twox-143*`.

### Akzeptanzkriterien

1. erfüllt (Analyse oben). 2. erfüllt (Tests). 3. erfüllt. 4. erfüllt: Kennungsanfragen und Anfragen mit höchstens einem anderen Wort gleiche Treffer, Reihenfolge und SQL; `test_keyword_search.py` und `test_fusion.py` unverändert grün. 5. erfüllt. 6. ohne (b2), Begründung oben. 7. **nicht erfüllt**: 9 Tests außerhalb von `tests/search` rot (Frage 2), sonst grün. 8. erfüllt. 9. offen, Messung der Leitstelle.

### Messung in „2x“ – für die Leitstelle nach dem Zusammenführen

Keine Migration nötig. Vorher (Code von `main` vor 143) und nachher (nach dem Zusammenführen, `api` neu gebaut oder Einmal-Container `--no-deps`), jeweils Text und `--json`:

```
docker compose -p 2x --env-file <.env des Projektordners> --profile dev run --rm --no-deps backend-dev python manage.py evaluate_search --probes m2
docker compose -p 2x --env-file <.env des Projektordners> --profile dev run --rm --no-deps backend-dev python manage.py evaluate_search --probes m2 --json
docker compose -p 2x --env-file <.env des Projektordners> --profile dev run --rm --no-deps backend-dev python manage.py evaluate_search --probes m3 --cutoffs 5,8,10,12 --distance
docker compose -p 2x --env-file <.env des Projektordners> --profile dev run --rm --no-deps backend-dev python manage.py evaluate_search --probes m3 --cutoffs 5,8,10,12 --distance --json
```

Darauf achten: Stichwortspalte für Fragen nicht mehr 0; `question-9` Rang 1 (E-61-Risiko, siehe Abweichung 1); `control-11` kleinster Abstand unter den ersten 10 und Rang des ersten Eintrags ohne Abstand. Erwartbar: deutlich mehr Stichworttreffer je Frage; in der Fusion zählt jeder Teiltreffer `1/(60 + Rang)` und kann Abschnitte nur nach Bedeutung überholen.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a478417578a56fa8f`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a478417578a56fa8f` (relativ zum Projektordner)
- Nicht gepusht, nichts zusammengeführt.

### Abweichungen

1. **Kennungen machen allein keinen Stichworttreffer einer Frage.** Der Auftrag sagt „Kennungen bleiben immer erhalten“; sie bleiben in der Anfrage (für „alle Wörter zuerst“, Rang, Hervorhebung), aber ein Abschnitt, der nur die Kennung enthält, ist kein Teiltreffer (außer die Frage hat kein anderes Inhaltswort). Grund: Mit reinem ODER bekäme jeder Abschnitt, der das Produkt nennt („UR5e“), einen Stichwortrang und könnte – zusammen mit einem Vektorrang – die Antwort überholen; genau der Fehler aus 060 (Prüffrage 9), den E-61 behoben hat, und `--probes m2` verlangt `question-9` auf Rang 1. Ein Schalter in `_build_question` (`words or identifiers` → `words + identifiers`) stellt reines ODER her, falls a7 das will.
2. **„Alle Inhaltswörter“ statt „heutiger UND-Treffer“** als erste Gruppe: UND über die Einheiten ohne Stoppwörter (der heutige UND-Treffer verlangt in `simple`/`english` auch deutsche Stoppwörter). Innerhalb jeder Gruppe nach `ts_rank` (ODER-Anfrage, wirkt wie Abdeckung plus Überschriftengewicht); keine eigene Abdeckungsspalte.
3. **Geänderte bestehende Tests in `tests/search/test_vector_search.py`** (hängen nachweislich an der UND-Semantik): `test_question_naming_a_product_puts_the_best_meaning_first` – die Antwort enthält „Getriebeöls“ und ist jetzt zusätzlich Stichworttreffer (Wert 1/61 + 1/61 statt 1/61, Art `keyword`+`semantic`; Reihenfolge gleich, die XR7-Abschnitte weiter ohne Stichwortrang). `test_vector_list_holds_the_50_nearest_sections` und `test_excluded_sections_do_not_shorten_the_vector_list` – Anfrage „which spare is nearest“ → „which item is nearest“ (sonst wären alle 60 Abschnitte mit „spare“ Stichworttreffer; der Test prüft die Vektorliste). `test_version_rule_works_in_the_vector_list` – der neue, noch nicht eingebettete Abschnitt wird jetzt über „change“ per Stichwort gefunden; die Prüfung, dass die alte Version nicht mehr gesucht wird, bleibt. `test_keyword_search.py` und `test_fusion.py` unverändert.
4. **Suchseite:** Mehrwortanfragen ohne Kennung (z. B. „safety valve“) gelten jetzt als Frage und zeigen unter den Treffern mit allen Wörtern auch Teiltreffer (Option a aus Frage 1). Die e2e-Tests bleiben grün.
5. `pytest -m worker` nicht einzeln gelaufen; keine Datei mit Worker-Bezug geändert.
6. Die ignorierte `.env` des Arbeitsverzeichnisses wurde aus `.env.example` neu geschrieben (`TWOX_API_PORT=18143`); lokal bleiben Images `twox-143-*`.
