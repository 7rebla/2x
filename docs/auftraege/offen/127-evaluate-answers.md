# Auftrag 127 – Messwerkzeug evaluate_answers

Meilenstein: M3 · Freigabestufe: B · Status: offen

Voraussetzung: 120 (Probe-Liste `m3.json`, Recall@k, Fundstelle über Überschriftenpfad) und 126 (Antwortdienst `answer()`, Befehl `ask`) sind auf `main`. Mittelbar damit auch 121 (`FakeChatModel`), 122 (`ContextSource`, `AnswerEvent`, `prompt_version()`), 123 (`citations.verify`) und 125 (Kontextauswahl).

## Ziel

Die Abnahme von M3 lautet „mindestens 8 von 10 Prüffragen richtig; Kontrollfrage ohne erfundene Antwort“ (`docs/ROADMAP.md:13`, Startunterlage Abschnitt 9). Dieser Auftrag macht sie wiederholbar messbar: ein Werkzeug `evaluate_answers` als Gegenstück zu `evaluate_search` (056), mit einer im Code festgelegten, getesteten Definition von „richtig“. Es stellt die Prüffragen aus `testfactory/questions.yaml` über den Antwortdienst aus 126, bewertet jede Antwort automatisch und gibt das Ergebnis als Text und als JSON aus, ohne Antwort- oder Abschnittstext. Messlauf 128, Abnahmetest 137 und Abnahmelauf 138 bauen darauf auf.

## Umfang

### 1. Modul `backend/twox/answers/evaluation.py` (neu)

Aufbau nach dem Muster von `backend/twox/search/evaluation.py` (frozen dataclasses mit `slots=True`, `StrEnum`, Fehlerklasse für Eingabefehler, reine Urteilsfunktionen getrennt vom Lauf, `format_table` und `format_json`).

**Eingaben**

- **Prüffragen:** `testfactory/questions.yaml` (JSON-Notation trotz Endung, `schema_version` 1). Gezählt werden nur die Einträge unter `questions` mit den Kennungen 1 bis 11; `candidates` (`c1`, `c2`, …) zählen nicht für M3 (`testfactory/questions.yaml:4`) und werden ignoriert. Gelesen werden `id`, `question`, `kind` (`fact` | `contradiction` | `no-evidence`), `key_facts`, `sources` und, falls vorhanden, das optionale Feld `key_fact_alternatives` (siehe Urteil). Unbekannte `kind` oder fehlende Pflichtfelder ergeben einen Eingabefehler mit Ortsangabe wie `ProbeFormatError` (`backend/twox/search/evaluation.py:79`).
- **Erwartete Fundstellen:** aus der Probe-Liste `backend/twox/search/probes/m3.json` (Auftrag 120), geladen mit `twox.search.evaluation.load_probes`. Für die Frage N gilt die Vereinigung der `expected`-Fundstellen aller Proben mit `basis.question == N`. Die Fundstellen der anderen Sprachfassung stehen dort bereits mit `other_language_edition` (E-61, `backend/tests/search/test_probes.py:9-13`) und zählen deshalb ohne eigene Logik. Eine Frage ohne Probe (heute Frage 8, bis Auftrag 136) bekommt das Urteil `no_probe` und zählt als nicht richtig.
- **Gestellter Fragetext:** Das Feld `question` enthält bei Frage 6 und 11 Hinweise für Menschen, bei 11 sogar die erwartete Absage (`testfactory/questions.yaml:180`, `:352`). Diese Hinweise dürfen nie an das Modell gehen. Eine kleine, dokumentierte und getestete Funktion `asked_text(question)` entfernt: eine führende Kennzeichnung bis zum ersten Doppelpunkt, wenn sie mit „Kontrollfrage“ beginnt; jede Klammerbemerkung „(…)“; jeden Satz, der mit „Erwartet wird“ beginnt. Das Ergebnis darf weder die feste Absage noch die Wörter „erwartet“ oder „widersprechen“ enthalten (Test für alle elf Fragen). Option `--wording probe` stellt statt dessen die `query` der ersten Probe zu Frage N (eigene Worte aus 120), zum Vergleich mit der Suchgrundlinie.

**Lauf**

- `evaluate(questions, places, *, runs=1, answer=service.answer, clock=time.perf_counter) -> Report`. Jede Frage wird `runs`-mal über den Antwortdienst gestellt, ohne Eingrenzung auf Gerät oder Anlage (`device_ids` und `plant_ids` leer). `answer` ist injizierbar, damit Urteils- und Lauftests ohne Datenbank und ohne Modell auskommen.
- Je Lauf werden aus dem Ereignisstrom (Vertrag aus 122) gelesen: `SourcesEvent` (Quellen mit Nummer n, `sha256`, Seiten, Überschriftenpfad, Fundorten), die Zeit bis zum ersten `DeltaEvent`, die Gesamtzeit bis `DoneEvent` oder `ErrorEvent`, aus `DoneEvent` `status`, `cited`, `removed_sentences` und `final_text`. Bewertet wird immer `final_text` (die bereinigte Fassung), nie der gestreamte Rohtext.
- Ein `ErrorEvent` ergibt das Urteil `error` mit dem Fehlercode und zählt als nicht richtig. Ist die KI aus (`TWOX_AI_ENABLED=0`, E-59), wird keine Frage gestellt; der Bericht sagt „AI features not enabled: not measured“ und meldet kein x/10. Ein Modell wird dabei nie angesprochen.
- Eine Frage, von deren erwarteten Dateien keine eingelesen ist, wird wie bei `evaluate_search` als `not_ingested` ausgewiesen (`ingested_checksums` aus `backend/twox/search/evaluation.py:375` wiederverwenden), nicht gestellt und zählt als nicht richtig.

**Urteil je Lauf (reine Funktion `judge_run`)**

Eine zitierte Quelle ist eine Quelle aus `SourcesEvent`, deren Nummer in `DoneEvent.cited` steht. Aus ihr wird je Fundort ein `twox.search.evaluation.Place` gebildet (`sha256`, `page_start`, `page_end`, `device_key`) und mit `matching_place` (`backend/twox/search/evaluation.py:298`) gegen die erwarteten Fundstellen geprüft. Für Markdown-Fundstellen über den Überschriftenpfad wird der Abgleich aus Auftrag 120 verwendet, nicht neu geschrieben.

- **`fact`:** richtig, wenn `status == answered`, jedes `key_fact` nach Vereinheitlichung in `final_text` vorkommt (oder eine seiner Alternativen, siehe unten) und mindestens ein gültiges Zitat auf eine erwartete Fundstelle zeigt. Für die Fragen mit zusätzlichen Repository-Quellen genügt eine Fundstelle aus der eingelesenen Dokumentation (Vorgabe nach D3, siehe Fragen).
- **`contradiction`:** richtig, wenn `status == contradiction`, beide `key_facts` vorkommen und die gültigen Zitate beide Aussagengruppen treffen. Die Gruppen werden aus `questions.yaml` abgeleitet, nicht im Code fest verdrahtet: Quellen, deren `supports` mit „Statement A:“ bzw. „Statement B:“ beginnt, bilden Gruppe A bzw. B; die Seite kommt aus dem `locator` („PDF-S. n“, Muster wie `PDF_PAGE` in `backend/tests/search/test_probes.py:37`), Datei und `sha256` aus der Probe zu derselben `manifest_id`. Die andere Sprachfassung zählt nach E-61. Für Frage 6 ergibt das Gruppe A = S. 34, Gruppe B = S. 36 oder 38 (`testfactory/questions.yaml:188-208`); Quellen ohne PDF-Seite (Ordnername im Repository) entfallen bis M5.
- **`no-evidence`:** richtig nur, wenn `status == no_evidence` und `cited` leer ist. Jedes Zitat, jede andere Statusangabe und jeder Fehler ist ein Fehlschlag. Scheitert die Kontrollfrage, ist M3 nicht bestanden, unabhängig von x/10.
- **Vereinheitlichung:** dieselbe wie in der Zitatprüfung aus 123 (Leerraum, Groß- und Kleinschreibung, Bindestriche; „5 kg“ = „5kg“). Die Funktion wird aus `twox.answers.citations` importiert, nicht kopiert. Ist sie dort nicht öffentlich, darf sie ohne Verhaltensänderung öffentlich gemacht werden (einzige erlaubte Änderung an `citations.py`, unter „Abweichungen“ nennen).
- **`key_fact_alternatives`:** optionales Objekt in einer Frage, Schlüssel ist ein `key_fact`, Wert eine Liste gleichwertiger Schreibweisen. Fehlt das Feld, gilt der Wortlaut. Option `--literal` ignoriert vorhandene Alternativen. Dieser Auftrag ändert `questions.yaml` nicht (D5).
- Ergebnis je Lauf: Urteil (`correct` | `wrong` | `error` | `no_probe` | `not_ingested`), fehlende `key_facts` (nur die Kennwerte aus `questions.yaml`, kein Antworttext), getroffene und fehlende erwartete Fundstellen (`manifest_id` und Seiten bzw. Überschriftenpfad), Rang der Belegstelle (kleinste Quellennummer n einer passenden Quelle im Kontext, sonst `None`), ob sie zitiert wurde, Zahl der Quellen, Zahl der gültigen Zitate, Zahl der verworfenen Sätze, Status, Fehlercode, Zeit bis zum ersten Token, Gesamtzeit.

**Zusammenfassung über mehrere Läufe**

- `--runs N` (Standard 1) und `--mode majority|strict` (Standard `majority`): Mehrheit heißt mehr als die Hälfte der Läufe richtig, streng heißt alle Läufe richtig.
- Die Kontrollfrage wird unabhängig von `--mode` streng bewertet (alle Läufe ohne Zitat und mit `no_evidence`); `--control-mode majority` ist für Vergleiche möglich, der Bericht nennt dann den Modus deutlich.
- Je Frage: Endurteil, Zahl der richtigen Läufe von N als Streuung, Rang der Belegstelle (kleinster, größter), Zeit bis zum ersten Token und Gesamtzeit (Median, kleinster, größter Wert).
- Je Lauf (für 128 und 138, die eine Zeile x/10 je Lauf verlangen): `per_run: [{run, correct_count, control_ok}]` in Text und JSON. `correct_count` zählt die Fragen 1–10, die in diesem Lauf richtig sind; `control_ok` gilt für diesen Lauf.
- Gesamt: zwei Abnahmeregeln, beide immer berechnet und ausgegeben, weil sie verschieden ausgehen können (bei 3 Läufen kann jede Frage in 2 von 3 Läufen richtig sein, ohne dass ein einzelner Lauf 8/10 erreicht):
  - **je Frage** (`per_question`): Endurteil je Frage nach `--mode`, daraus „x/10 richtig“; `passed_per_question = x >= 8 and control_ok`.
  - **je Lauf** (`per_run`): Ein Lauf besteht, wenn `correct_count >= 8` und `control_ok`; `passed_per_run` ist wahr, wenn nach `--mode` die Mehrheit (bzw. bei `strict` alle) der Läufe besteht.
  - `--rule per-question|per-run` (Standard `per-question`) legt fest, welche der beiden Regeln `passed` bestimmt; der Bericht nennt die Regel im Kopf. Die verbindliche Regel legt a7 mit D5 fest; 128, 137 und 138 übernehmen sie wortgleich.
  - Dazu: „x/10 richtig, Kontrollfrage ok | nicht ok“, Quote gültiger Zitate über alle Läufe, Zahl `no_probe` und `not_ingested`.
- Kopf des Berichts: Chat-Modell, Einbettungsmodell, `prompt_version()`, Temperatur und `max_tokens` aus den Einstellungen von 121, die `TWOX_ANSWER_*`-Werte aus 125, Läufe, Modus, Fragetext-Quelle (`yaml` | `probe`), KI an oder aus.
- Je Frage eine leere Spalte bzw. ein Feld `verdict_a7` (`null`), die a7 im Bericht von 128/138 ausfüllt (D5).

**Ausgabe**

- `format_table(report)` mit einer Zeile je Frage und einer Zusammenfassung, `format_json(report)` mit `ensure_ascii=False`, wie `backend/twox/search/evaluation.py:531-638`.
- Weder Text noch JSON enthalten Fragetext, Antworttext, `final_text`, verworfene Sätze, Abschnittstext oder Snippets, nur Kennungen, Seiten, Überschriftenpfade (aus den Proben), Zahlen, Status und Codes.

### 2. Befehl `backend/twox/answers/management/commands/evaluate_answers.py` (neu)

- Aufbau wie `backend/twox/search/management/commands/evaluate_search.py`.
- Optionen: `--questions PATH` (Standard `/testfactory/questions.yaml`, so in `backend-dev` eingehängt, `deploy/compose/compose.yaml:288-289`; `-` liest von der Standardeingabe, für den Lauf im Container `api`, der die Datei nicht eingehängt hat), `--probes NAME|PATH` (Standard `m3`, also `twox/search/probes/m3.json`; Namensauflösung wie in 120, falls 120 sie für `evaluate_search` anlegt), `--runs N`, `--mode majority|strict`, `--rule per-question|per-run`, `--control-mode strict|majority`, `--wording yaml|probe`, `--literal`, `--only ID[,ID…]` (Teilmenge, z. B. für 128), `--json`.
- Ungültige Eingaben enden mit kurzer englischer Meldung und Exit 1 (`CommandError`). Eine abgeschlossene Messung endet mit Exit 0, auch wenn M3 nicht bestanden ist; das Urteil steht in `passed`.
- Die Ausgabe ist englisch wie die der übrigen Befehle (`docs/ARCHITECTURE.md:689`).

### 3. Tests `backend/tests/answers/test_evaluation.py` (neu)

- Urteilstests ohne Datenbank: selbst geschriebene Ereignisfolgen mit erfundenen Kennungen und `sha256`-Werten, selbst geschriebene Antworttexte; keine Herstellertexte.
- Lauf- und Befehlstest mit `FakeChatModel` aus 121 über den echten Antwortdienst aus 126, auf einer kleinen Datenbank nach dem Muster von `backend/tests/search/conftest.py` und `backend/tests/search/fake_embedder.py`, mit einer selbst geschriebenen kleinen Fragen- und Probe-Datei aus `tmp_path` (nicht mit den echten Handbüchern).

### 4. Doku

- `docs/ARCHITECTURE.md`: Modulzeile `answers` (`:134`) um `evaluation.py` und `evaluate_answers` ergänzen; Werkzeugtabelle (`:585`) um eine Zeile „Answer quality“; Abschnitt „What CI does not run“ (`:605`) so ändern, dass `evaluate_answers` mit den echten Prüffragen nur lokal läuft (Definition von „richtig“ in einem Satz je `kind`, Verweis auf das Modul). Den CI-Teil der Prüffragen (E-10) beschreibt erst 135.

## Nicht-Ziele

- Keine Änderung an Suche, Kontextauswahl, Prompt, Zitatprüfung oder Antwortdienst (außer dem oben genannten öffentlichen Export der Vereinheitlichung in `citations.py`).
- Keine Änderung an `testfactory/questions.yaml` (auch kein `key_fact_alternatives`), an `m3.json` oder an `m2.json`.
- Kein Messlauf mit echtem Modell; den führt 128 nach D1 aus. Kein `ollama pull`.
- Kein Abnahmetest (`test_m3.py`, Schalter `TWOX_M3_LOCAL`), das ist 137. Keine CI-Aufzeichnungen und kein Replay-Modell, das ist 135.
- Keine Eingrenzung auf Gerät oder Anlage beim Messen; die prüft 137.
- Keine Speicherung von Fragen, Antworten oder Messergebnissen in der Datenbank (D7).
- Keine Änderung an Compose-Dateien.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/answers/evaluation.py` (neu)
- `backend/twox/answers/management/commands/evaluate_answers.py` (neu; der Ordner besteht mit `check_llm.py`)
- `backend/tests/answers/test_evaluation.py` (neu; `backend/tests/answers/` besteht)
- `backend/twox/answers/citations.py` (aus 123; nur falls nötig: Vereinheitlichung öffentlich machen, ohne Verhaltensänderung)
- `docs/ARCHITECTURE.md` (nur die drei unter „Doku“ genannten Stellen)

Nur lesend genutzt: `backend/twox/search/evaluation.py`, `backend/twox/search/probes/m3.json`, `backend/twox/answers/service.py`, `types.py`, `chat.py`, `prompt.py`, `testfactory/questions.yaml`.

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Die Urteilsregeln sind mit selbst geschriebenen Antwortbeispielen für alle drei Arten getestet, mindestens: Treffer (`fact` richtig); fehlendes `key_fact`; `key_fact` nur über `key_fact_alternatives` getroffen (mit und ohne `--literal`); richtige Datei, falsche Seite; Zitat auf die andere Sprachfassung zählt (E-61); Zitat mit einer Nummer, die nicht in `cited` steht, zählt nicht; Widerspruch mit nur einer Gruppe ist falsch, mit beiden Gruppen und Status `contradiction` richtig; Widerspruch mit beiden Gruppen, aber Status `answered` ist falsch; Kontrollfrage mit `no_evidence` und ohne Zitat richtig; Kontrollfrage mit einem Zitat ist Fehlschlag, und `passed` ist dann `false`, auch bei 10/10; `ErrorEvent` ergibt `error`; Frage ohne Probe ergibt `no_probe`.
2. Mehrheit und streng sind getestet (z. B. 2 von 3 richtig: Mehrheit richtig, streng falsch); die Kontrollfrage ist ohne `--control-mode` streng (1 von 3 Läufen mit Zitat ergibt „nicht ok“). Die beiden Regeln `per-question` und `per-run` sind getestet: 3 Läufe mit 9/7/8 richtigen Fragen ergeben `per_run` mit diesen drei Werten, `passed_per_run` wahr (2 von 3 Läufen ≥ 8); ein Fall, in dem jede Frage in 2 von 3 Läufen richtig ist, aber kein Lauf 8/10 erreicht, ergibt `passed_per_question` wahr und `passed_per_run` falsch; `passed` folgt `--rule`.
3. `asked_text` ist für alle elf Fragen aus `questions.yaml` getestet: Das Ergebnis enthält weder die feste Absage „Dazu finde ich nichts in den Unterlagen“ noch „erwartet“ oder „widersprechen“ und ist nicht leer.
4. Die Gruppen der Widerspruchsfrage werden aus `questions.yaml` abgeleitet; ein Test liest die echte Datei und erhält für Frage 6 Gruppe A = {34} und Gruppe B = {36, 38} (Seiten, keine Texte).
5. Ein Test zeigt, dass Bericht und JSON keine Antwort-, Frage- oder Abschnittstexte enthalten: Eingeschleuste Markertexte in `final_text`, in den verworfenen Sätzen, in `ContextSource.text` und im Fragetext kommen in keiner Ausgabe vor.
6. Ein Test zeigt: Bei `TWOX_AI_ENABLED=0` wird keine Frage gestellt, `answer` wird nie gerufen, der Bericht sagt „not measured“.
7. `manage.py evaluate_answers --runs 1` (und `--json`) läuft mit `FakeChatModel` über den echten Antwortdienst durch und meldet das erwartete x/n (Test mit `call_command`). Ungültige Fragen- oder Probe-Datei endet mit `CommandError` (Test).
8. Ein Log-Test mit `caplog` auf allen Loggern zeigt, dass weder Frage noch Antwort noch Abschnittstext in einer Logzeile steht.
9. `docker compose run --rm backend-dev pytest tests/answers` ist grün (Arbeitsverzeichnis im Container ist `/app` = `backend/`, `backend/Dockerfile:26`, `deploy/compose/compose.yaml:281`, `testpaths = ["tests"]` in `backend/pyproject.toml:84`; daher `tests/...` statt `backend/tests/...`).
10. Alle Prüfungen des Jobs `backend` aus `.github/workflows/ci.yml` sind grün: `ruff check .`, `ruff format --check .`, `mypy .`, `pytest`, `pytest -m worker`, Übersetzungskatalog, `makemigrations --check --dry-run` (keine Migration), Lizenzprüfung, OpenAPI-Schema unverändert. Die Jobs `web`, `testfactory` und `e2e` bleiben grün (keine Datei dort berührt).
11. Keine neue Abhängigkeit (`backend/pyproject.toml` und Lock unverändert).
12. `down -v` der eigenen Compose-Projekte endet mit Exit 0.

Den Lauf gegen die echten Handbücher mit echtem Modell führt die Leitstelle in 128 aus.

## Vorgaben und Hinweise

- **Leitplanke 3 und Abnahme:** „Richtig“ heißt richtig mit Quelle; eine Antwort ohne gültiges Zitat auf eine erwartete Fundstelle ist nie richtig, auch wenn die `key_facts` stimmen.
- **Leitplanke 4:** Das Werkzeug wertet nur strukturierte Ereignisse aus, nie Anweisungen im Antworttext. Die Hinweise in `questions.yaml` gehen nicht ans Modell (siehe `asked_text`).
- **Keine Textauszüge (Leitplanke Testfabrik, E-10, CLAUDE.md „Keine längeren Auszüge“):** Bericht und JSON enthalten nur Kennungen, Seiten und Zahlen, wie `evaluate_search` (`backend/twox/search/evaluation.py:36-37`). Testtexte sind selbst geschrieben.
- **Protokollieren:** Wie im Antwortdienst (126, D7) nur Fehlerart, Modellname, Dauer und Zahl der Quellen.
- **E-59:** Bei ausgeschalteter KI keine Verbindung zum Modell. Die Abnahme gilt mit `TWOX_AI_ENABLED=1` (D5).
- **E-61:** Die andere Sprachfassung zählt; sie ist über die Proben in `m3.json` abgebildet.
- **E-55:** Ein Abschnitt kann mehrere Fundorte (Geräte) haben; jeder Fundort einer zitierten Quelle wird geprüft.
- **E-60 und 057:** Messwerkzeug und Bericht folgen dem Muster des Messlaufs 057; 128 nutzt dieses Werkzeug für die Modellwahl.
- **Schnittstellen:** Fragen nur über `twox.answers.service.answer`, Suche nur über die Funktionen von `twox.search.evaluation` bzw. `get_search_backend()`, Modell nur über `get_chat_model()` (im Test über das injizierte `FakeChatModel`).
- **Laufbefehl in der Testumgebung** (für den Kurzbericht nur als Beispiel, kein Lauf mit echtem Modell nötig): `docker compose run --rm backend-dev python manage.py evaluate_answers --runs 3 --json` oder im Container `api` mit `--questions -` und Umleitung der Datei auf die Standardeingabe.
- **Abgrenzung:** 128 (Messlauf) und 137 (Abnahmetest) rufen dieses Werkzeug, ändern es aber nicht. 135 baut für die CI einen eigenen kleinen Fragensatz auf `testdata/klein` und darf die Urteilsfunktionen dieses Moduls wiederverwenden; die Schnittstelle von `judge_run` und `evaluate` deshalb klein und dokumentiert halten. Parallel laufen 130 (API) und ggf. 135; 130 ändert in `docs/ARCHITECTURE.md` nur API und Logging, dieser Auftrag nur die drei genannten Stellen.
- Typangaben an jeder Funktion; Code, Bezeichner, Docstrings und Meldungen englisch; keine Personennamen, keine lokalen Pfade.
- Auf dem eigenen Zweig klein committen; kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

Der Auftrag ist ohne Entscheidung startbar; das Werkzeug unterstützt alle Varianten, die Entscheidungen legen nur die Vorgaben für 128, 137 und 138 fest.

- **D5 Abnahmeregeln: Läufe, Urteil, key_facts.** Läufe je Frage: (a) 3 Läufe, Mehrheit; (b) 3 Läufe, alle richtig; (c) 1 Lauf mit Temperatur 0 und festem Seed. Urteil: (d) automatisch vorgeschlagen und von a7 in der Spalte „Urteil a7“ bestätigt; (e) rein automatisch. key_facts: (f) Feld `key_fact_alternatives` in `questions.yaml`, damit Umschreibungen (Fragen 7, 10, englische Quelle zu Frage 10) nicht wörtlich scheitern, als Datenänderung mit Prüfung durch a7; (g) wörtlich lassen. Mehrheitsregel: (k) je Frage (eine Frage ist richtig, wenn mehr als die Hälfte ihrer Läufe richtig ist; daraus x/10) oder (l) je Lauf (mindestens 8/10 und Kontrollfrage ok in der Mehrheit der Läufe). **Empfehlung:** (a), (d), (f) und (k); die Kontrollfrage muss in allen Läufen bestanden werden, die Streuung und die Werte je Lauf stehen im Bericht. Die gewählte Regel wird in 128, 137 und 138 wortgleich übernommen. Vorgabe im Werkzeug bis zur Entscheidung: `--runs 1`, `--mode majority`, `--rule per-question`, Kontrollfrage streng, `key_fact_alternatives` werden gelesen, wenn vorhanden.
  - **Ausführung von (f):** Dieser Auftrag ändert `questions.yaml` nicht. Wählt a7 (f), braucht es einen eigenen kleinen Auftrag (Stufe C, Testfabrik-Daten): `key_fact_alternatives` für die Fragen 7 und 10 in `testfactory/questions.yaml` eintragen, Prüfung durch a7, Testfabrik-Tests und CI-Job `testfactory` grün. Die Leitstelle legt ihn nach der Entscheidung an und plant ihn vor 128 ein; heute nennt keiner der Aufträge 120–138 `questions.yaml` als Bereich. Ohne ihn messen 128 und 138 wörtlich.
- **D3 Belegumfang ohne M5-Daten.** (a) Für M3 genügt eine Fundstelle aus der eingelesenen Dokumentation; Repository-Quellen werden mit M5 nachgeprüft. (b) Volle Quellenlage erst mit M5. **Empfehlung:** (a); so umgesetzt, weil das Werkzeug die erwarteten Fundstellen aus `m3.json` nimmt, die nur eingelesene Dateien kennt.
- **D4 Prüffragen beibehalten oder eigene.** (a) Die 11 Fragen aus `questions.yaml` bleiben Abnahmegrundlage; (b) Ersatz durch eigene Fragen; (c) beide Sätze, eigene nur informativ. **Empfehlung:** (a) mit (c); das Werkzeug liest jede Datei im selben Format über `--questions`.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
