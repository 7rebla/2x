# Auftrag 143 – Suche: Überschriften stärker gewichten und Fragen weicher suchen (D12 b)

Meilenstein: M3 · Freigabestufe: C · Status: offen

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

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
