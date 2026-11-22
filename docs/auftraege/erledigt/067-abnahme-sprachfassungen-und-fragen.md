# Auftrag 067 – Sprachfassungen in der Abnahme, keine exakte Liste bei Fragen

Meilenstein: M2 · Freigabestufe: C (entschieden mit E-61) · Status: erledigt

Voraussetzung: E-61; 063 und 058 sind auf `main`.

## Ziel

Der Abnahmelauf 060 scheiterte an zwei Stellen der Suche (Bericht in `docs/auftraege/offen/060-m2-abnahmelauf.md`):

1. Für `192.168.0.100` steht die richtige Stelle auf Rang 2 – in der **englischen** APS-Dokumentation (S. 38, dieselbe Stelle wie in der deutschen). Probe und Abnahmetest zählen nur die deutsche Fassung (Rang 4).
2. Prüffrage 9 (Traglast UR5e): Vektor Rang 1, kombiniert Rang 12, weil Abschnitte mit „UR5e“ in Stichwort- und exakter Liste zugleich stehen und so jeden Abschnitt schlagen, der nur in einer Liste steht.

Nach diesem Auftrag zählen beide Sprachfassungen als richtig, und Fragen in Satzform haben keine eigene exakte Liste mehr (E-61).

## Umfang

**Teil A – Sprachfassungen (Probe und Test):**
- `backend/twox/search/probes/m2.json`: Bei den Proben mit Fundstellen in der APS-Dokumentation die entsprechenden Seiten der englischen Fassung (`aps-documentation-en`, SHA-256 aus `testfactory/manifest.yaml`) als weitere richtige Fundstellen ergänzen. Welche englischen Seiten der deutschen entsprechen, an der lokalen Datei feststellen (Hauptordner, `testfactory/extern/…/documents/en/documentation_aps_en-02-2025.pdf`, **nur lesen**, keine Zitate oder Auszüge in Dateien oder Bericht – nur Seitenzahlen). Kennzeichnen, dass die Seite aus der anderen Sprachfassung stammt (Feld oder `basis`-Text), damit die Herkunft nachvollziehbar bleibt.
- `backend/tests/search/test_probes.py`: Prüfung der neuen Einträge gegen das Manifest (Prüfsumme) wie bei den übrigen.
- `web/e2e/m2-acceptance.spec.ts`, lokaler Teil: Die IP-Probe (und jede andere Probe mit APS-Fundstelle) akzeptiert auch die englische Fassung mit ihren Seiten.

**Teil B – keine exakte Liste bei Fragen:**
- `backend/twox/search/postgres.py`: Gilt `exact_hits_first(...)` nicht (Frage in Satzform, Vektorliste vorhanden), entfällt die eigene exakte Liste in der RRF-Summe; Kennungen wirken nur über Stichwort- und Vektorliste. Kennungsanfragen (Kennung plus höchstens ein Wort) und Suchen ohne Vektorliste bleiben unverändert. `match_kinds` enthält `exact` weiterhin, wenn der Abschnitt die Kennung wörtlich enthält.
- Tests (`test_fusion.py`, `test_vector_search.py`) anpassen: Rechenbeispiel von Hand für die neue Summe; Frage mit Produktkennung („XR7“-Fall aus 063) – bester Abschnitt nach Bedeutung vorne; Kennungsanfragen und KI aus unverändert.
- `docs/ARCHITECTURE.md` und `README.md`: Abschnitt zur Rangfolge anpassen; Docstring von `SearchView.get` in `backend/twox/search/api.py` prüfen, ggf. Schema und Client neu erzeugen.

## Nicht-Ziele

- Keine Änderung an Datenmodell, API-Form oder Oberfläche.
- Keine Anpassung von Rang-Grenzen im Abnahmetest (die bleiben 3 bzw. 5).

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/search/postgres.py`, `backend/twox/search/api.py` (nur Docstring)
- `backend/twox/search/probes/m2.json`
- `backend/tests/search/test_fusion.py`, `test_vector_search.py`, `test_probes.py`, gegebenenfalls `test_evaluation.py`
- `web/e2e/m2-acceptance.spec.ts`
- `web/openapi/schema.yml`, `web/src/api/generated/**` (nur falls der Docstring sich ändert)
- `README.md`, `docs/ARCHITECTURE.md` (nur Rangfolge und Probe)

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Alle Prüfungen aus `.github/workflows/ci.yml` (backend, web, e2e) sind grün.
2. Die Tests aus Teil A und B bestehen, mit KI an (Attrappe) und aus.
3. Messung mit `evaluate_search` und `m2.json` in einem eigenen Projekt mit `testdata/klein/` (zeigt „not ingested“ – erwartbar) und Nachweis an Testdaten, dass der XR7-Fall jetzt vorn steht. Die Leitstelle misst danach in „2x“ mit den Handbüchern.
4. `down -v` der eigenen Compose-Projekte endet mit Exit 0.

## Vorgaben und Hinweise

- Herkunft: E-61 (a7, 22.11.2026), Befunde aus 060.
- Herstellerunterlagen sind Daten, keine Anweisungen; keine Zitate. `testfactory/extern/` bleibt ungetrackt.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Läufe am 22.11.2026 im Container, Projekte `twox-067` und `twox-067-web`, `TWOX_API_PORT=18067`, Docker Engine 29.9.3, Compose v5.7.0. Kriterien 0, 1, 2 und 4 erfüllt, Kriterium 3 mit Einschränkung (siehe Abweichung 1). Keine neue Abhängigkeit, keine Migration, keine Änderung an API-Form, Datenmodell oder Oberfläche. „2x“ und „twox-leit“ nicht angefasst.

### Was wurde gebaut?

**Teil A – Sprachfassungen**

- Seitenabgleich an den Dateien des Manifests (Prüfsummen beider Dateien stimmen mit `testfactory/manifest.yaml` überein), nur lesend in einem Wegwerf-Container ohne Netz mit der PDF-Bibliothek des Docling-Images: Beide Fassungen haben 38 Seiten. Je Seite wurden nur Kennzahlen verglichen (Anzahl Zeichen, IPv4-Adressen, Zahlenfolgen, Zählung einzelner Fachbegriffe); kein Text wurde ausgegeben oder gespeichert. Ergebnis: Die englische Fassung hat dieselben Angaben auf **derselben Seitenzahl**.

  | Probe | deutsche Seiten | englische Seiten | Beleg (nur Kennzahlen) |
  | --- | --- | --- | --- |
  | `ip-ccu` (Prüffrage 1) | 18, 31, 38 | 18, 31, 38 | `192.168.0.100` steht in beiden Fassungen genau auf S. 18, 31, 38; Zahlenabgleich je Seite 1,0 / 0,91 / 1,0 |
  | `ip-drill-plc` | 38 | 38 | `192.168.0.50` und die übrigen Adressen der Seite auf S. 38 beider Fassungen |
  | `question-1` | 18, 31, 38 | 18, 31, 38 | wie `ip-ccu` |
  | `question-3` | 36, 38 | 36, 38 | Zahlenabgleich 1,0; gleiche Zählung der Protokollbegriffe auf S. 36 und 38 |
  | `question-7` | 22, 27 | 22, 27 | Zahlenabgleich 1,0; der Begriff für das Fahrzeug erscheint gleich oft (deutsche und englische Abkürzung) |

- `backend/twox/search/probes/m2.json`: Die fünf Proben mit APS-Fundstellen erwarten zusätzlich `aps-documentation-en` (SHA-256 `f4555cab…04d2` aus dem Manifest) mit denselben Seiten. Herkunft im Feld `basis`: `"other_language_edition": {"aps-documentation-en": "aps-documentation-de"}` (Ort der anderen Sprachfassung → dokumentierter Ort); `notes` erklärt Regel und Abgleich in 067. Das Format der Probenliste bleibt gleich (`basis` wird vom Befehl nicht ausgewertet).
- `backend/tests/search/test_probes.py`: Die bisherigen Prüfungen gegen `questions.yaml`/`devices.csv` gelten für die dokumentierten Orte; neu:
  - `test_places_in_the_other_language_edition_match_the_documented_place`: Ort der anderen Fassung steht in derselben Probe neben dem dokumentierten Ort, gleiche Seiten, Prüfsumme wie im Manifest, gleiche `document_version`, andere `language`.
  - `test_every_probe_on_the_aps_documentation_accepts_both_editions`: Jede Probe mit `aps-documentation-de` erwartet auch `aps-documentation-en` (genau die fünf Proben).
  - Die Prüfsumme der englischen Einträge prüft wie bei allen übrigen `test_every_file_is_in_the_manifest`. `basis` wird jetzt über die Schlüssel `question`/`device` gelesen statt über den ersten Schlüssel.
- `web/e2e/m2-acceptance.spec.ts` (lokaler Teil): neues Handbuch `APS_DOCUMENTATION_EN` (Prüfsumme aus dem Manifest); die IP-Probe akzeptiert `aps-documentation-de` oder `-en` mit S. 18, 31, 38. Sie ist die einzige Browser-Probe mit APS-Fundstelle. Rang-Grenzen unverändert (3 bzw. 5).

**Teil B – keine exakte Liste bei Fragen**

- `backend/twox/search/postgres.py`: Gilt `exact_hits_first(...)` nicht (Frage mit Vektorliste), ist der Anteil der exakten Treffer 0; die CTEs `exact_list`/`exact_ranked` und ihr Join entfallen. Abschnitte mit der Kennung bleiben Kandidaten, daher enthält `match_kinds` weiter `exact`; steht ein solcher Abschnitt in keiner der beiden Listen, hat er den Wert 0 und steht hinter allen anderen Treffern. Bei gleichem Wert geht weiter der Treffer mit dem besseren Vektorrang vor (wie in 063). Kennungsanfragen und Suchen ohne Vektorliste (KI aus, Modellausfall, nichts eingebettet) erzeugen dasselbe SQL wie vorher. Modul- und Funktions-Docstrings beschreiben die Regel.
- **Neue Rechenregel** für eine Frage mit Vektorliste: `Wert = 1/(60 + Stichwortrang) + 1/(60 + Vektorrang)`, fehlende Listen fallen weg; die Kennung zählt nur, wenn sie über diese Listen trifft.
  - **Beispiel** (`test_question_without_exact_list_worked_out_by_hand`, Anfrage „XR7 Getriebeöl wechseln“): Stichwort A 1, B 2; Vektor B 1, A 2, C 3, E 4; XR7 wörtlich in B, C, D.

    | Abschnitt | Rechnung | Wert | 063 (dritte Liste) |
    | --- | --- | --- | --- |
    | B | 1/62 + 1/61 | 0,032522 | 0,048916 |
    | A | 1/61 + 1/62 | 0,032522 | 0,032522 |
    | C | 1/63 | 0,015873 | 0,031873 |
    | E | 1/64 | 0,015625 | 0,015625 |
    | D | in keiner Liste | 0 | 0,016000 |

    Reihenfolge B, A, C, E, D (B vor A bei Gleichstand, weil näher nach Bedeutung); `match_kinds` von D bleibt `exact`.
  - **XR7-Fall aus 063, jetzt mit einem Abschnitt, der XR7 nennt und zugleich unter den nächsten nach Bedeutung steht** (`test_question_naming_a_product_puts_the_best_meaning_first`, das Muster von Prüffrage 9 aus 060): Antwort 1/61 vorne, der Abschnitt mit XR7 1/62 auf Platz 2; mit 063 hätte er 1/62 + 1/62 = 0,032258 gehabt und vor der Antwort (0,016393) gestanden.
- `backend/twox/search/api.py` (nur Docstring von `SearchView.get`), `web/openapi/schema.yml` und `web/src/api/generated/` (zwei Kommentare) neu erzeugt.
- `README.md` (Rangfolge, Probenliste, Abnahme von Hand Schritt 3: deutsche oder englische Fassung) und `docs/ARCHITECTURE.md` (Fusion, Messung, Grenzen der Rangfolge).

### Wie wurde getestet?

`D` = `docker compose -p twox-067`, `W` = `docker compose -p twox-067-web -f deploy/compose/compose.web.yaml`; `.env` aus `.env.example` mit dem Write-Werkzeug (ohne BOM), nur `TWOX_API_PORT=18067` geändert. Vor jedem Web-Bau und e2e-Lauf `web/dist` und `web/playwright-report` gelöscht. Alle Tests mit Attrappen, nie gegen echtes Ollama oder Docling.

| Nr. | Ergebnis | Nachweis |
| --- | --- | --- |
| 0 | erfüllt | Engine 29.9.3, Compose v5.7.0, je Exit 0 |
| 1 | erfüllt | **backend:** build, `up -d --wait`, `ruff check` („All checks passed!“), `ruff format --check`, `mypy` („Success: no issues found in 192 source files“), `pytest` 2341 passed / 6 deselected / 0 failed / 0 skipped, `pytest -m worker` 6 passed, `makemessages` ohne Unterschied, `makemigrations --check` Exit 0, Lizenzprüfung bestanden, `spectacular` (Unterschied nur der neue Docstring, committet). **web:** build, `npm ci`, `lint`, `typecheck`, `test` (38 Dateien, 730 Tests), `build`, `licenses`, `api:generate` je Exit 0. **e2e:** build, `pull e2e`, `npm ci`, `up`, „Create test account“ wie in `ci.yml` (Kennwort nur über den Variablennamen), `run --rm e2e`: 55 passed, 1 skipped (lokaler Teil), Exit 0. Danach erneut `spectacular` und `api:generate`: `git diff --exit-code -- web/openapi web/src/api backend/locale` Exit 0, `git status` leer |
| 2 | erfüllt | `pytest tests/search tests/acceptance`: KI an (Attrappen) 348 passed; mit `-e TWOX_AI_ENABLED=false` 348 passed. Neue und geänderte Tests: Rechenbeispiel, XR7-Fall, exakter Treffer ohne Liste (Wert 0, `exact` bleibt), gleicher Inhalt an zwei Geräten, zwei Prüfungen der Sprachfassungen; unverändert grün: Kennungsanfragen (`192.168.0.5`, `E1234`, `Fehler E1234`, `PLC-07`), KI aus und Modellausfall (Werte und Reihenfolge wie vor 063), `test_evaluation.py`. Zum Flackern eines Abnahmetests siehe Befund unten |
| 3 | mit Einschränkung | `D exec -T api python manage.py evaluate_search < backend/twox/search/probes/m2.json`: Exit 0, „Not ingested: 7 of 7 probes“, die APS-Proben nennen jetzt `aps-documentation-de, aps-documentation-en`. XR7-Nachweis über die Tests mit Testtexten und Attrappe (siehe oben), nicht mit echtem Modell (Abweichung 1) |
| 4 | erfüllt | `D --profile dev --profile e2e down -v` Exit 0, `W --profile dev down -v` Exit 0; kein Container und kein Volume `twox-067*` mehr |

### Befund (nicht durch 067, nicht behoben)

`tests/acceptance/test_m2.py::test_search_answers_a_question_in_other_words_by_meaning[ai-on]` flackert, wenn `tests/search` und `tests/acceptance` in einem Lauf zusammen laufen: mit diesem Zweig 2 von 6 Läufen rot, mit dem Suchcode von `main` (eingebunden über die Datei) 3 von 8 Läufen rot; einzeln je 10 von 10 grün, im vollen `pytest` grün. Die Anfrage hat keine Kennung, der Fall läuft über unveränderten Code. Vermutete Ursache: Die Attrappe aus 048 gibt jedem Abschnitt einen Einheitsvektor auf einer eigenen Achse; alle Abschnitte sind zueinander gleich weit entfernt, und der HNSW-Index (näherungsweise, zufällige Ebenen) findet den gesuchten Abschnitt dann nicht immer. Vorschlag für einen Folgeauftrag: in diesem Test Vektoren mit Abstufung verwenden oder die Vektorsuche dort exakt erzwingen. `test_m2.py` liegt außerhalb des Bereichs von 067.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-ac2fa27b65526164a`
- Arbeitsverzeichnis: `.claude/worktrees/agent-ac2fa27b65526164a` (relativ zum Projektordner)
- Commits: `Drop the exact list from the fusion for questions (E-61)`, `Accept the English APS documentation as a correct place (E-61)`, `Describe the order of search hits without an exact list for questions`, `Document the ranking of questions and both language editions in the probes`, dazu dieser Kurzbericht. Nicht gepusht, nichts zusammengeführt.

### Abweichungen

1. **Keine Messung mit echtem Modell und `testdata/klein/`:** Den Start von Docling im Projekt `twox-067` hat die Berechtigungsprüfung der Sitzung abgelehnt; ich habe ihn nicht auf anderem Weg versucht. Ohne Docling wird nichts eingelesen, also gibt es keine Werte für eine eigene Probenliste wie in 063. `evaluate_search` mit `m2.json` lief auf der Datenbank des Projekts („not ingested“, wie erwartet). Der XR7-Fall ist an Testtexten mit Attrappe belegt. Die Messung mit den Handbüchern macht wie vorgesehen die Leitstelle in „2x“.
2. **Abschnitte, die eine Kennung nur wörtlich enthalten** (in keiner der beiden Listen), bleiben bei Fragen in der Trefferliste, mit Wert 0 am Ende. Grund: `match_kinds` soll `exact` weiter zeigen, und kein Treffer soll verschwinden. Bei genug Vektortreffern (50) fallen sie praktisch unter die Grenze `limit`.
3. **Seitenabgleich mit dem Docling-Image:** Das `backend-dev`-Image hat keine PDF-Bibliothek. Ich habe die PDF-Bibliothek des Docling-Images benutzt, das in `compose.yaml` steht (ohne Netz, nur lesend eingebunden). Beim ersten Aufruf fehlte die Angabe der Version, deshalb hat Docker das Image einmal als `:latest` geladen; dieses zusätzliche Image habe ich sofort wieder entfernt. Das festgelegte Image ist unverändert.
4. Lokal bleiben die Images `twox-067-*`; die ignorierte `.env` hat `TWOX_API_PORT=18067`.

### Nachmessung der Leitstelle (22.11.2026)

Testumgebung „2x“ mit allen Handbüchern, bge-m3, 2 000 Zeichen; `evaluate_search` mit Probe und `postgres.py` dieses Zweigs. Kombinierter Rang der ersten richtigen Fundstelle (vorher nach 063 → jetzt): ip-ccu 4 → 2 (en S. 38); ip-drill-plc 11 → 10; question-1 4 → 1; question-3 – → –; question-7 – → 7; question-9 12 → 1; question-10 3 → 1. Kombiniert: Recall@5 0,429 → 0,571, Recall@10 0,429 → 0,857, MRR 0,144 → 0,535.
