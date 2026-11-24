# Auftrag 153 – Kontextauswahl: kurze Abschnitte und inhaltsreichere Sprachfassung

Meilenstein: M3 · Freigabestufe: C (freigegeben mit E-76, Teil A) · Status: zur Prüfung

## Ziel

Diagnose 152 (`docs/auftraege/erledigt/152-diagnose-modellantworten.md`): Die Prüffragen 4 und 10 scheitern an der Kontextauswahl (`backend/twox/answers/context.py`, Schritt 6). Mit den Abschnitten, die die key_facts enthalten, antwortet gemma4 3/3 richtig. Sie fehlen, weil

1. **sehr kurze Abschnitte** (gemessen: 2, 100, 363 Zeichen, ohne Inhalt zur Frage, oft nur eine Überschrift oder ein Seitenrest) einen der `max_sources` = 8 Plätze belegen – der „Rang 1“ von Frage 10 in 151 war so ein Abschnitt;
2. die **Sprachfassungs-Regel** (E-61, `TWOX_ANSWER_TRANSLATION_DISTANCE` 0,15) von zwei Fassungen derselben Stelle die zuerst gefundene behält, auch wenn die andere anders zugeschnitten ist und mehr Inhalt hat (Frage 4 mit `probe`: die englische S. 36 mit der ganzen Kette fällt weg, die deutsche ohne Node-RED bleibt).

Nach diesem Auftrag belegen sehr kurze Abschnitte keinen eigenen Quellenplatz, und von zwei Sprachfassungen bleibt die inhaltsreichere.

## Umfang

1. **Kurze Abschnitte:** Ein Hauptquellen-Kandidat mit weniger als `TWOX_ANSWER_MIN_SOURCE_CHARS` Zeichen Text (neue Einstellung; Startwert vom Bearbeiter an den Daten in „2x“ begründet, Vorschlag 200) zählt nicht als eigene Quelle. Der Bearbeiter wählt und begründet eine der Formen:
   - (a) überspringen (außer bei einem exakten Treffer, `MatchKind.EXACT`), oder
   - (b) durch den nächsten Abschnitt derselben Version ersetzen bzw. mit ihm zusammen ausgeben, ohne die Regel „jede `(version_id, ordinal)` einmal“ und die Zitierbarkeit je Abschnitt zu brechen.
   Bevorzugt (a), wenn die Messung (Umfang 3) gleich gut ist – einfacher und ohne Folgen für Nummerierung und Zitatprüfung.
2. **Sprachfassungen:** Wird ein Treffer als andere Sprachfassung einer schon genommenen Quelle erkannt, bleibt die Fassung mit **mehr Text** (oder: beide, wenn die spätere deutlich mehr enthält – begründet; Grenze als Konstante). Die Reihenfolge der Quellen bleibt die der Suche (die behaltene Fassung nimmt den Platz der früheren ein). Kopien (gleiche Datei an mehreren Geräten) bleiben unverändert eine Quelle.
3. **Messung in „2x“, nur lesend** (`docker compose exec -T api python manage.py shell -c …` mit dem Code des Zweigs – dazu das Hilfsskript den Code aus dem Arbeitsverzeichnis laden lassen oder `select_context` mit einer Ersatzfunktion im Skript nachbilden; **kein Neubau von „2x“**): Für alle M3-Prüffragen (Wortlaut `yaml` und `probe`, `testfactory/questions.yaml`, `backend/twox/search/probes/m3.json`) vorher/nachher die Quellen (Kennzeichnung, Länge), und ob die Abschnitte mit den key_facts im Kontext sind (Maßstab „ideal“ aus 152). Für die Kontrollfrage (11, beide Wortlaute) Zahl der Quellen und bester Abstand – sie darf nicht mehr Quellen bekommen als vorher, ohne dass das im Bericht begründet ist.
4. **Tests** in `backend/tests/answers/`: kurze Abschnitte (unter/über der Grenze, exakter Treffer, alle Kandidaten kurz), Sprachfassung (spätere länger → ersetzt, spätere kürzer → bleibt draußen, Kopien unverändert), Nummerierung und Budget unverändert korrekt.
5. **CI-Aufzeichnungen:** werden sie rot, neu aufnehmen nach `backend/tests/answers/recorded/README.md` mit `gemma4:31b-it-qat` (vorher `/api/ps` leer); nichts aufweichen.
6. **Doku:** Modul-Docstring von `context.py` (Schritt 6), `docs/ARCHITECTURE.md`, `.env.example`, README (neue Einstellung).

## Nicht-Ziele

- Keine Änderung an Suche, Schwelle, k, Zeichenbudget, Prompt, Zitatprüfung, `value_occurs` (läuft parallel in 154).
- Kein Neu-Einlesen, keine Änderung an Abschnitten oder Teilstücken.
- Kein Messlauf mit dem Chat-Modell über alle Fragen (Messlauf 4 macht die Leitstelle).

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/answers/context.py`, `backend/twox/config/settings.py`, `.env.example`, `deploy/compose/compose.yaml` (nur die neue Variable unter `x-backend-environment`)
- `backend/tests/answers/` (Tests zur Kontextauswahl), ggf. `backend/tests/answers/recorded/ci_questions.json`
- `docs/ARCHITECTURE.md`, `README.md`
- diese Auftragsdatei

## Akzeptanzkriterien (prüfbar)

1. Tests aus Umfang 4 vorhanden und grün; bestehende Tests grün (geänderte Erwartungen einzeln begründet).
2. Messung Umfang 3 im Bericht: Für Frage 4 und 10 (beide Wortlaute) ist mindestens ein Abschnitt mit den key_facts im Kontext, oder es ist belegt, warum nicht. Keine andere Prüffrage verliert einen Abschnitt mit key_facts. Kontrollfrage: Zahl der Quellen und bester Abstand vorher/nachher.
3. CI wie `ci.yml` grün: backend (inkl. `pytest -m worker` mit laufendem `worker`), web, testfactory, e2e.
4. Diff nur in den genannten Bereichen, keine neue Abhängigkeit, Compose-Projekte mit `down -v` entfernt; „2x“ unverändert (`.env`, Zählung Abschnitte/Teilstücke).

## Vorgaben und Hinweise

- Compose-Projekt `twox-153`, `TWOX_API_PORT=18153`. `docker` liegt nicht im PATH: `%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin`.
- Parallel läuft 154 (`citations.py`, `value_occurs`); deren Dateien nicht anfassen. Vor einer Neuaufnahme und vor Läufen in „2x“ `/api/ps` prüfen.
- Rohdaten der Messung ungetrackt (`Claude outputs/153/`); im Bericht nur Kennzeichnungen und Zahlen.
- Nicht pushen.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine vor dem Start (E-76). Weicht die gewählte Form wesentlich ab (z. B. beide Sprachfassungen behalten), Begründung im Bericht.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Gewählte Form: **(a) überspringen**, Grenze **200** Zeichen; Sprachfassungen: **die längere ersetzt die frühere an deren Platz** (nicht „beide behalten“).

### Was wurde gebaut?

- `backend/twox/answers/context.py`, Schritt 6:
  - **Kurze Abschnitte:** Ein Hauptquellen-Kandidat mit weniger als `TWOX_ANSWER_MIN_SOURCE_CHARS` Zeichen (ohne Leerraum am Rand) wird übersprungen und belegt keinen der `max_sources` Plätze. Ausnahme: exakter Treffer (`MatchKind.EXACT`; bei zusammengeführten Kopien genügt eine exakte Kopie). Sind alle relevanten Treffer kurz, ist die Auswahl leer (`below_threshold` bleibt `False`; der Dienst antwortet wie bisher ohne Quellen mit `no_evidence`, ohne Modellaufruf). Nachbarn (`TWOX_ANSWER_NEIGHBOURS`) werden wie bisher nicht gefiltert. Neuer Parameter `select_context(..., min_source_chars=None)` wie die übrigen.
  - **Sprachfassungen (E-61):** Ist ein Treffer Sprachfassung einer schon genommenen Quelle, ersetzt er sie an ihrem Platz, wenn sein Text länger ist und er mit dem frei werdenden Budget hineinpasst; gleich lang oder kürzer → bleibt draußen. Ist er Fassung mehrerer genommener Quellen, nimmt er den Platz der ersten ein, die übrigen entfallen. Das Ersetzen fügt keine Quelle hinzu und wird deshalb auch geprüft, wenn `max_sources` schon erreicht ist. Kopien werden unverändert vorher zu einer Quelle zusammengeführt. Keine neue Konstante nötig (Form „ersetzen“, nicht „beide“).
- `settings.py`: `TWOX_ANSWER_MIN_SOURCE_CHARS` (ganze Zahl > 0, Standard 200; 1 nimmt jeden Abschnitt). `.env.example`, `deploy/compose/compose.yaml` (`x-backend-environment`), `docs/ARCHITECTURE.md` (Modulübersicht und Einstellungstabelle), `README.md` (Abschnitt Answers), Modul-Docstring von `context.py`.

**Begründung Form (a):** In der Messung ist (b) („durch den nächsten Abschnitt derselben Version ersetzen“, bis 3 Schritte) nirgends besser als (a): bei keiner Frage kommt ein zusätzlicher Abschnitt mit key_facts in den Kontext; bei Frage 3 `probe` bringt (a) einen weiteren key_fact-Abschnitt (dt. S. 38), (b) nicht. (a) ist einfacher und ohne Folgen für Nummerierung und Zitatprüfung.

**Begründung Grenze 200:** In den Kontexten vorher liegen unter 200 Zeichen nur Abschnitte ohne key_facts der Frage (2, 15, 51, 55, 100, 105, 140, 153, 190 Zeichen; Überschriften, Bildunterschriften, Seitenreste). Der kürzeste Abschnitt mit key_facts in einem Kontext hat 213 Zeichen (Frage 8, Abschn. 11025, alle fünf key_facts); 300 würde ihn verlieren (gemessen: Frage 8 beide Wortlaute ohne key_facts). 150 ergibt dieselben key_facts wie 200, lässt aber bei Frage 4 `yaml` einen 153-Zeichen-Abschnitt ohne Inhalt im Kontext. Über die ganze Sammlung haben 985 von 5 071 Abschnitten weniger als 200 Zeichen. Bekannte Grenze der Regel: In den Unterlagen gibt es vereinzelt kurze Abschnitte mit key_facts (Frage 8: 105 Zeichen mit 2 von 5; Frage 9: 96 und 133 Zeichen). Sie sind in keinem gemessenen Kontext vorher enthalten; ein exakter Treffer bleibt ohnehin.

### Messung (Umfang 3; „2x“ nur lesend)

Hilfsskripte `measure153.py` und `ranks153.py` im Container `api` über `manage.py shell -c`; der neue `context.py` des Zweigs wurde als eigenes Modul aus `/tmp` geladen, die Einstellung nur im Speicher gesetzt. Vergleich „vorher“ = Code des Containers (Prüfsumme `context.py` = `main`, `76fa5a38cc89132b`). Rohdaten ungetrackt in `Claude outputs/153/`. Kontext in „2x“: k = 8, Nachbarn aus, Übersetzungsabstand 0,15. Ollama `/api/ps` vor den Läufen: leer bzw. nur `bge-m3` (Suchanfragen); kein Chat-Modell.

Abschnitte mit key_facts im Kontext (Abschnitts-ID, Seite, Zeichen); „ideal“ = Abschnitte aus 152 mit allen key_facts (Frage 4: 8657, 8766; Frage 10: 6771, 7090, 7202):

| Frage | Wortlaut | vorher: key_facts im Kontext | nachher (a200) | ideal im Kontext nachher |
| --- | --- | --- | --- | --- |
| 1 | yaml | 8665, 8768, 8738 | gleich | – |
| 1 | probe | 8768 (engl. S. 38), 8738 | 8658 (dt. S. 38, längere Fassung), 8738 | – |
| 2 | beide | 8658 | gleich | – |
| 3 | yaml | 8656 (dt. S. 36) | 8766 (engl. S. 36, längere Fassung) | – |
| 3 | probe | 8656, 8657 | 8766, 8657, **+8658** | – |
| 4 | yaml | MQTT, Node-RED (8768, 8665); OPC UA fehlt | gleich; 3 kurze Abschnitte (105–153 Z.) ersetzt durch längere ohne key_facts | **nein**, s. u. |
| 4 | probe | 8656 (MQTT, OPC UA), 8658 | **8766 (alle drei)**, 8658 | **ja, 8766 auf Platz 1** |
| 5 | beide | 8653, 5981 | gleich | – |
| 6 | yaml | 8656 (Gruppe B) | 8766 (Gruppe B, engl.) | – |
| 6 | probe | 8656, 8771, 8700, 8653 (A) | 8766, 8664, 8700, 8653 (A) – je die längere Fassung | – |
| 7 | yaml / probe | – / 8744 | gleich | – |
| 8 | beide | 11025 (213 Z., alle key_facts) | gleich | – |
| 9 | beide | 6612 | gleich | – |
| 10 | yaml | keine | keine (2-Z.- und 100-Z.-Abschnitt weg, dafür 2 längere ohne key_facts) | **nein**, s. u. |
| 10 | probe | keine | keine (100-Z.-Abschnitt auf Platz 1 und 2-Z.-Abschnitt weg) | **nein**, s. u. |

- **Keine Prüffrage verliert einen key_fact-Abschnitt:** Wo eine ID wechselt (Fragen 1, 3, 6), ist es die andere, längere Sprachfassung derselben Stelle mit denselben key_facts; die abgedeckten key_facts sind je Frage und Wortlaut vorher ⊆ nachher.
- **Warum 4 `yaml` und 10 nicht (belegt):** Die ideal-Abschnitte stehen nicht unter den 2k = 16 Treffern der Suche, aus denen `select_context` wählt; keine Regel der Auswahl kann sie hereinholen. Ränge in der kombinierten Liste (Grenze 100): Frage 4 `yaml` 8766 Rang 29, 8657 nicht unter 50; Frage 10 `yaml` 7090 Rang 21 (Abstand 0,4906; Rang 16: 0,4849), 6771/7202 nicht unter 68; Frage 10 `probe` 7202 Rang 28 (0,4648; Rang 16: 0,4542), 6771/7090 nicht unter 72. Die frei gewordenen Plätze füllen Treffer 9–16 ohne key_facts. Form (b) hilft ebenfalls nicht (Folgeabschnitte 7205 und 7073 ohne key_facts).
- **Kontrollfrage 11:** `yaml` vorher 8 Quellen, nachher 8 (1-Zeichen-Abschnitt ersetzt durch einen mit 227 Zeichen), bester Abstand 0,4904 vorher und nachher; `probe` vorher 6, nachher **5**, bester Abstand 0,5095 vorher und nachher. Nicht mehr Quellen als vorher.
- Zählung Abschnitte / Versionen / Teilstücke / ohne Vektor vor und nach den Läufen: 5 071 / 158 / 6 815 / 0 = 5 071 / 158 / 6 815 / 0. `.env` des Hauptordners: SHA-256 vorher und nachher gleich. Hilfsdateien in `/tmp` des Containers gelöscht.

**Folgerung für die Leitstelle:** Ziel für Frage 4 `probe` erreicht. Für Frage 4 `yaml` und Frage 10 ist die Kontextauswahl nicht mehr die Ursache, sondern die Trefferzahl der Suche (2k = 16). Naheliegende Option für einen Folgeauftrag (Stufe C, Änderung der Suchanfrage in `context.py`, nicht Teil dieses Auftrags): mehr Treffer anfragen, als Plätze belegt werden (z. B. 3k = 24 → Frage 10 `yaml` mit 7090, 273 Zeichen, alle key_facts); dann wieder gegen die Kontrollfrage messen.

### Wie wurde getestet?

- Neue Tests in `backend/tests/answers/test_context.py`: kurze Abschnitte (unter/an/über der Grenze, Leerraum zählt nicht, Parameter und 1, exakter Treffer, kurze Kopie mit einer exakten Kopie, keine Platzbelegung unter `max_sources`, alle Kandidaten kurz → leer über der Schwelle, kurzer Abschnitt weiter als Nachbar), Sprachfassungen (spätere länger → ersetzt an ihrem Platz, kürzer bzw. gleich lang → bleibt draußen, Ersetzen bei vollen `max_sources`, nur mit passendem Budget, eine Fassung zweier Quellen, Kopien bleiben eine Quelle), Budget und Nummerierung mit kurzen Abschnitten, Fassungen und Nachbarn; Einstellung (Startwert 200, Variable, ungültige Werte, `min_source_chars=0`).
- **Geänderte Erwartungen/Aufbauten bestehender Tests:**
  - `test_same_place_in_another_document_of_the_device_appears_once`: deutscher Text gekürzt („Achse fetten.“), damit der Test weiter „die besser platzierte Fassung bleibt“ prüft; vorher war die spätere Fassung länger und würde nach der neuen Regel ersetzen (das prüfen die neuen Tests).
  - Tests mit absichtlich kurzen Texten (wenige Wörter), die anderes prüfen, nutzen die neue Fixture `every_text_a_source` (`conftest.py`, setzt die Grenze auf 1): ganz `test_context.py`, `test_context_pieces.py`, `test_ask.py` sowie je ein bzw. zwei Tests in `test_service.py`, `test_evaluation.py`, `test_api.py`. Ohne sie fielen 13 Tests, weil ihre einzigen Abschnitte kürzer als 200 Zeichen sind. Erwartungen selbst unverändert.
- CI-Aufzeichnungen (`test_ci_questions.py`) laufen mit dem Startwert 200 grün; keine Neuaufnahme nötig, `recorded/ci_questions.json` unverändert.
- CI wie `ci.yml` im Compose-Projekt `twox-153` (API-Port 18153): backend (ruff check, ruff format --check, mypy, pytest, `pytest -m worker` mit laufendem `worker`, Übersetzungskatalog, Migrationen, Lizenzen, OpenAPI), web (lint, typecheck, test, build, licenses, API-Client), testfactory (ruff, mypy, unittest offline, Manifestprüfungen, kein `extern/`), e2e (Playwright). Alle grün: pytest 3 618 bestanden, 1 übersprungen (lokaler Teil M3); worker 6 bestanden; Katalog, Migrationen, OpenAPI, API-Client ohne Unterschied; testfactory 223 Tests OK (1 übersprungen); e2e 102 bestanden, 2 übersprungen. Compose-Projekte danach mit `down -v` entfernt.

### Zweig und Arbeitsverzeichnis

- Zweig `worktree-agent-aab88ab1fc5eb13d6`, Arbeitsverzeichnis `.claude/worktrees/agent-aab88ab1fc5eb13d6` (relativ zum Projektordner), Basis `main` 8487444. Nicht gepusht, nichts zusammengeführt.

### Abweichungen

1. Akzeptanzkriterium 2 für Frage 4 `yaml` und Frage 10 (beide Wortlaute) nur über den Beleg „warum nicht“ erfüllt (Ränge > 16, s. o.); die Trefferzahl der Suche war ausdrücklich nicht Teil des Auftrags.
2. Alle relevanten Treffer kurz → leere Auswahl mit `below_threshold = False` (nicht „unter der Schwelle“): Die Schwelle beschreibt weiter nur die Suche; der Dienst behandelt „keine Quelle“ schon wie bisher als `no_evidence`.
3. Die Fixture `every_text_a_source` steht in `backend/tests/answers/conftest.py` (nicht autouse), damit `test_ci_questions.py` mit dem Startwert läuft.
