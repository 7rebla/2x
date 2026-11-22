# Auftrag 125 – Kontextauswahl für Antworten

Meilenstein: M3 · Freigabestufe: B · Status: offen

Voraussetzung: 121 (Schnittstelle Sprachmodell), 122 (Antworttypen und Prompt, insbesondere `ContextSource` in `backend/twox/answers/types.py`) und 124 (Abstand und Volltext im Suchtreffer: `SearchRequest.include_text`, `SearchHit.semantic_distance`, `SearchHit.text`) sind auf `main`. 124 ist Stufe C (D11) – ohne dessen Zusammenführung startet dieser Auftrag nicht.

## Ziel

Aus einer Frage und der optionalen Eingrenzung auf Gerät oder Anlage entsteht die nummerierte Quellenliste, die der Prompt (122) erhält. Fragen mit zwei Belegstellen sollen beide Stellen im Kontext haben (Prüffrage 6: S. 34 und S. 36/38; Prüffrage 7: S. 22 und S. 27). Liegt kein Treffer unter der Relevanzschwelle, wird das Sprachmodell gar nicht gefragt; das deckt die Kontrollfrage (Prüffrage 11) ab, bevor ein Modell eine Antwort erfinden kann (Leitplanke 3, D8 Vorgabe (a)).

Das Modul ist rein serverseitig und kennt weder HTTP noch das Sprachmodell. Es wird von 126 (Antwortdienst) aufgerufen und von 128 kalibriert.

## Umfang

### 1. Modul `backend/twox/answers/context.py` (neu)

Öffentliche Schnittstelle (Namen verbindlich, weil 126 und 128 darauf aufbauen):

```python
@dataclass(frozen=True, slots=True)
class ContextSelection:
    sources: list[ContextSource]        # aus types.py (122), Nummern n = 1..len(sources), lückenlos
    below_threshold: bool               # True: kein Treffer relevant genug, Modell nicht fragen
    best_distance: float | None         # kleinster semantic_distance aller Treffer (für Messung/Log), sonst None
    hit_count: int                      # Zahl der Suchtreffer vor Auswahl (nur Zahl, für Log/Messung)

class ContextDisabledError(Exception): ...     # KI aus (E-59)
class ContextUnavailableError(Exception): ...  # Vektorsuche hat nicht teilgenommen (SemanticState.UNAVAILABLE)

def select_context(
    question: str,
    *,
    device_ids: Sequence[int] = (),
    plant_ids: Sequence[int] = (),
    max_sources: int | None = None,      # None: settings.TWOX_ANSWER_MAX_SOURCES
    context_chars: int | None = None,    # None: settings.TWOX_ANSWER_CONTEXT_CHARS
    max_distance: float | None = None,   # None: settings.TWOX_ANSWER_MAX_DISTANCE
    neighbours: bool | None = None,      # None: settings.TWOX_ANSWER_NEIGHBOURS
) -> ContextSelection: ...
```

Die Parameter mit `None`-Standard sind für die Kalibrierung in 128 gedacht (ohne Umgebungsvariablen zu ändern).

Ablauf, in dieser Reihenfolge:

1. **KI aus:** Ist `settings.TWOX_AI_ENABLED` falsch, wirft `select_context` sofort `ContextDisabledError` – ohne Suche, ohne Einbettung, ohne Verbindung (E-59, D10 Vorgabe (a)). 126 macht daraus `error(ai_disabled)`.
2. **Leere Frage** (nach `strip()`): `ContextSelection(sources=[], below_threshold=True, best_distance=None, hit_count=0)`, ohne Suche.
3. **Suche** ausschließlich über `get_search_backend().search(SearchRequest(query=question, device_ids=…, plant_ids=…, limit=…, include_text=True))` (`backend/twox/search/interface.py:161-166`). `limit` ist `min(MAX_LIMIT, 2 * max_sources)`, damit nach Zusammenlegen der Sprachfassungen und nach dem Zeichenbudget noch genug Kandidaten übrig sind. Kein direkter SQL-Zugriff auf die Suche, keine eigene Vektorabfrage, kein Import aus `twox.search.postgres`.
4. **Vektorsuche nicht beteiligt:** Ist `result.semantic` gleich `SemanticState.UNAVAILABLE`, wirft die Funktion `ContextUnavailableError` (126 macht daraus `error(model_unavailable)`). Eine Antwort „Dazu finde ich nichts“ wäre in diesem Fall irreführend. `SemanticState.DISABLED` kann bei eingeschalteter KI nicht auftreten, weil `keyword_only` nicht gesetzt wird; tritt es doch auf, gilt dasselbe wie bei `UNAVAILABLE`.
5. **Schwelle** (vor jeder weiteren Arbeit): Relevant ist ein Treffer, wenn `hit.semantic_distance is not None and hit.semantic_distance <= max_distance` oder wenn `MatchKind.EXACT` in `hit.match_kinds` steht (ein Bezeichner wie eine IP-Adresse oder Teilenummer wurde wörtlich gefunden). Gibt es keinen relevanten Treffer, ist das Ergebnis `sources=[]`, `below_threshold=True`, `best_distance` gesetzt. Reine Stichworttreffer ohne Abstand gelten allein nicht als relevant – genau sie würden bei der Kontrollfrage sonst Kontext liefern.
6. **Auswahl** (nur wenn die Schwelle überschritten ist), in Rangfolge der Suche:
   - Je Dokument sind mehrere Abschnitte zugelassen (keine Begrenzung je Dokument), damit Prüffrage 6 und 7 beide Stellen bekommen.
   - **Sprachfassungen zusammenlegen** (E-61): siehe Abschnitt 2.
   - **Zeichenbudget:** Die Summe von `len(source.text)` über alle Quellen überschreitet nie `context_chars`. Passt ein Abschnitt nicht mehr ins Restbudget, wird er übersprungen und der nächste Kandidat geprüft; Abschnittstexte werden **nie gekürzt**, weil die Zitatprüfung (123) Prüfkennzeichen im vollständigen zitierten Abschnitt sucht.
   - Höchstens `max_sources` Hauptquellen (Nachbarn zählen nicht gegen `max_sources`, wohl aber gegen das Zeichenbudget).
   - **Nachbarabschnitte** (nur wenn `neighbours` wahr): Zu jeder Hauptquelle werden die Abschnitte mit `ordinal - 1` und `ordinal + 1` derselben `DocumentVersion` aus `twox.ingest.models.Section` nachgeladen (eine Abfrage für alle, nicht je Quelle; Eindeutigkeit über `ingest_section_version_ordinal_unique`, `backend/twox/ingest/models.py:307-310`). Ein Nachbar wird eine eigene Quelle direkt hinter seiner Hauptquelle (erst `-1`, dann `+1`), nur wenn er noch nicht in der Liste ist und ins Budget passt. Seine `locations` sind die Fundorte der Hauptquelle mit derselben `version_id`, mit der `section_id` des Nachbarn (`dataclasses.replace`). Nachbarn erweitern nie die Schwellenprüfung.
7. **Nummerierung:** `n` läuft 1..len(sources) lückenlos in der Endreihenfolge. Jede Quelle ist eindeutig auf `(version_id, ordinal)` abgebildet; doppelte Paare kommen nicht vor.

Felder der `ContextSource` (Definition aus 122): `section_id` = `hit.section_id`; `version_id` und `sha256` aus dem Fundort, zu dem `hit.section_id` gehört (`HitLocation.section_id == hit.section_id`; `sha256` über `DocumentVersion.sha256` in einer gesammelten Abfrage, falls 122/124 ihn nicht schon liefern); `ordinal` aus `Section`; `page_start`, `page_end`, `heading_path`, `text` aus dem Treffer; `locations` = alle `hit.locations` unverändert (E-55: Fundorte mehrerer Geräte bleiben erhalten). Weicht die Definition in 122 von dieser Liste ab, gilt 122; die Abweichung steht im Kurzbericht.

Datenbankzugriffe: höchstens eine Abfrage für `ordinal`/`sha256` aller Kandidaten und eine für alle Nachbarn – keine Abfrage je Treffer (Test mit `django_assert_max_num_queries`).

Protokollierung: Das Modul protokolliert weder Frage noch Abschnittstext noch Überschriften. Erlaubt ist auf DEBUG nur: Zahl der Treffer, Zahl der Quellen, `best_distance`, `below_threshold`.

### 2. Sprachfassungen zusammenlegen (E-61)

Das Datenmodell kennt keine Sprache und keine Verknüpfung zwischen de- und en-Handbuch (`backend/twox/files/models.py`, `Document`/`DocumentVersion` ohne Sprachfeld). Die Erkennung geschieht deshalb über die gespeicherten Einbettungen:

- Zwei Kandidaten gelten als inhaltsgleiche Sprachfassung, wenn sie aus **verschiedenen Dokumenten** stammen, mindestens ein **gemeinsames Gerät** in ihren Fundorten haben und der **Kosinusabstand ihrer gespeicherten Einbettungen** (`Section.embedding`, nur mit `embedding_model == settings.TWOX_EMBED_MODEL`) höchstens `TWOX_ANSWER_TRANSLATION_DISTANCE` beträgt. bge-m3 ist mehrsprachig (E-56), deshalb liegen Übersetzungen derselben Stelle eng beieinander.
- Die Einbettungen werden mit der Abfrage aus Schritt 6 gelesen (eine Abfrage) und in Python verglichen (höchstens `2 * max_sources` Kandidaten, also vernachlässigbar). Es gibt keine neue Vektorabfrage gegen den Index und keine Änderung unter `backend/twox/search/`.
- Behalten wird der besser platzierte Kandidat; der andere entfällt ganz. Die Bewertung in 127 erkennt die andere Sprachfassung ohnehin über die erwarteten Fundstellen (E-61, `backend/twox/search/evaluation.py:298`).
- Abschnitte ohne passende Einbettung werden nie zusammengelegt.
- Ein und dasselbe Dokument wird nie mit sich selbst zusammengelegt (zwei benachbarte, ähnliche Abschnitte eines Handbuchs bleiben beide).

### 3. Einstellungen

In `backend/twox/config/settings.py`, direkt unter dem KI-Block (`settings.py:426-448`), mit den vorhandenen Hilfsfunktionen (`env_positive_int`, `env_bool`; für Gleitkommazahlen eine kleine typisierte Hilfsfunktion `env_positive_float` im selben Stil, falls nicht vorhanden):

| Variable | Typ | Startwert | Bedeutung |
| --- | --- | --- | --- |
| `TWOX_ANSWER_MAX_SOURCES` | int ≥ 1 | 8 | Höchstzahl Hauptquellen (k) |
| `TWOX_ANSWER_CONTEXT_CHARS` | int ≥ 1 | 20000 | Zeichenbudget aller Quellentexte zusammen |
| `TWOX_ANSWER_NEIGHBOURS` | bool | false | Nachbarabschnitte nachladen |
| `TWOX_ANSWER_MAX_DISTANCE` | float 0 < x ≤ 2 | Wert aus Kurzbericht 124 (siehe Hinweise), sonst 0.5 | Relevanzschwelle (Kosinusabstand) |
| `TWOX_ANSWER_TRANSLATION_DISTANCE` | float 0 < x ≤ 2 | 0.15 | Höchstabstand für „gleiche Stelle in anderer Sprache“ |

Begründung Zeichenbudget: 8 Abschnitte à höchstens 2 000 Zeichen (`TWOX_SECTION_MAX_CHARS`, `settings.py:481`, E-60) sind 16 000 Zeichen; 20 000 lassen Platz für zwei Nachbarn. Bei der in D1 vorgeschlagenen Kontextlänge von 16 384 Tokens bleibt damit genug Raum für Systemprompt und Antwort. Alle Startwerte sind vorläufig und werden in 128 kalibriert.

`TWOX_ANSWER_TRANSLATION_DISTANCE` muss kleiner als `TWOX_ANSWER_MAX_DISTANCE` sein; sonst bricht der Start mit einer klaren Meldung ab (wie `check_ingest_timing`, `settings.py:500-560`, oder als Systemprüfung).

In `.env.example` kommen die fünf Variablen mit Startwert und einem englischen Einzeiler als Kommentar dazu (nur diese Zeilen). In `deploy/compose/compose.yaml` kommen im Block `x-backend-environment` (`compose.yaml:4-34`) verbindlich die fünf Zeilen `TWOX_ANSWER_…: ${TWOX_ANSWER_…:-}` dazu, im Muster der vorhandenen Zeilen (nur diese Zeilen). Der Block zählt jede Variable einzeln auf; ohne diese Zeilen kämen die Werte aus `.env` nicht in `api`, `worker` und `backend-dev` an, und die Kalibrierung in 128 sowie die Werte für 138 blieben wirkungslos. `settings.py` (121, 130) und `compose.yaml` (121) werden nacheinander geändert, nicht parallel.

### 4. Tests `backend/tests/answers/test_context.py` (neu)

Mit Datenbank (`pytest.mark.django_db`) und dem `FakeEmbedder` aus `backend/tests/search/fake_embedder.py` (Abstände über `at_angle`, `fake_embedder.py:36`). Anlagen, Geräte, Versionen und Abschnitte entstehen wie in `backend/tests/search/test_vector_search.py:68-91`. Abschnittstexte sind selbst geschrieben oder stammen aus `testdata/klein` (OPNsense-Doku BSD-2, BetrSichV); keine Herstellertexte. Eine `conftest.py` in `backend/tests/answers/` übernimmt das Muster von `backend/tests/search/conftest.py:12-31` (KI aus, geschlossener Port), falls 121 sie nicht schon anlegt; existiert sie, wird sie nur ergänzt.

## Nicht-Ziele

- Keine Änderung unter `backend/twox/search/` (Schnittstelle, PostgreSQL-Suche, Auswertung) – das ist 124.
- Kein Prompt, keine Typdefinitionen (122), keine Zitatprüfung (123), kein Aufruf des Sprachmodells, kein Ereignisstrom (126), keine API und keine Oberfläche.
- Keine Kalibrierung mit echten Handbüchern und echtem Modell (128). Die Startwerte werden nicht „optimiert“.
- Kein Reranker, kein Umformulieren der Frage, keine geänderte Gewichtung im Stichwortindex (D12 (b)–(d)).
- Keine Migration, kein Sprachfeld am Dokument.
- Keine neue Abhängigkeit.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/answers/context.py` (neu)
- `backend/twox/config/settings.py` (nur der neue Block `TWOX_ANSWER_*` und ggf. `env_positive_float`)
- `.env.example` (nur `TWOX_ANSWER_*`)
- `deploy/compose/compose.yaml` (nur die fünf Zeilen `TWOX_ANSWER_*` im Block `x-backend-environment`, siehe Umfang 3)
- `backend/tests/answers/test_context.py` (neu)
- `backend/tests/answers/conftest.py` (neu oder ergänzt, nur Fixtures für diesen Test)
- `docs/ARCHITECTURE.md`: Zeile zur App `answers` (`ARCHITECTURE.md:134`) um `context.py` ergänzen; im Abschnitt „Configuration“ (`ARCHITECTURE.md:519`) die fünf Variablen kurz nennen. Englisch.

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. **Eingrenzung:** Mit zwei Geräten (je ein passender Abschnitt) liefert `device_ids=[A]` nur Quellen, deren Fundorte Gerät A enthalten; ebenso `plant_ids=[P]` nur Quellen der Anlage P (Tests).
2. **Sprachfassungen:** Zwei Abschnitte aus verschiedenen Dokumenten desselben Geräts mit Einbettungsabstand unter `TWOX_ANSWER_TRANSLATION_DISTANCE` erscheinen einmal, und zwar der besser platzierte (Test). Zwei solche Abschnitte desselben Dokuments bleiben beide (Test). Abschnitte ohne Einbettung des aktuellen Modells werden nicht zusammengelegt (Test).
3. **Zeichenbudget:** Die Summe der Quellentexte überschreitet nie `context_chars`, auch mit Nachbarn; ein zu langer Abschnitt wird übersprungen, ein späterer kürzerer noch aufgenommen; kein Text ist gekürzt (`source.text == Section.text`) (Tests).
4. **Nachbarn:** Bei `neighbours=False` erscheinen keine Nachbarabschnitte; bei `True` erscheinen `ordinal ± 1` derselben Version direkt hinter der Hauptquelle, ohne Dubletten, wenn der Nachbar selbst schon Treffer ist (Tests).
5. **Schwelle:** Liegt kein Treffer unter `max_distance` und gibt es keinen exakten Treffer, ist `below_threshold` wahr und `sources` leer (Test). Ein exakter Treffer (IP-Adresse) hebt die Sperre auf (Test). Reine Stichworttreffer ohne Abstand heben sie nicht auf (Test).
6. **Nummern:** `n` ist 1..len lückenlos und eindeutig; `(version_id, ordinal)` ist eindeutig (Test, auch mit Nachbarn).
7. **Mehrere Abschnitte je Dokument:** Zwei relevante Abschnitte desselben Dokuments auf verschiedenen Seiten erscheinen beide (Test, Muster Prüffrage 6/7).
8. **Fundorte:** Ein Abschnittsinhalt an zwei Geräten (E-55) behält beide Fundorte in `locations` (Test).
9. **KI aus:** `ContextDisabledError`, ohne dass die Suche oder der Embedder gerufen wird (Test mit Spion auf `get_search_backend` bzw. Socket-Sperre). **Vektorsuche ausgefallen:** `ContextUnavailableError` (Test mit fehlschlagendem Fake, Muster `test_vector_search.py:212`).
10. **Abfragen:** Höchstens eine feste Zahl Datenbankabfragen unabhängig von der Trefferzahl (Test mit `django_assert_max_num_queries`).
11. **Logs:** Ein Test mit `caplog` auf allen Loggern (Stufe DEBUG) zeigt: weder Frage noch Abschnittstext noch Überschrift steht in einer Logzeile.
12. **Einstellungen:** Ungültige Werte (`0`, negativ, `TRANSLATION_DISTANCE >= MAX_DISTANCE`) führen zu einer klaren Fehlermeldung (Test).
12a. **Durchreichung:** `docker compose config` zeigt alle fünf `TWOX_ANSWER_*` in den Diensten `api` und `backend-dev`, und `docker compose run --rm -e TWOX_ANSWER_MAX_SOURCES=5 backend-dev python manage.py shell -c "from django.conf import settings; print(settings.TWOX_ANSWER_MAX_SOURCES)"` gibt `5` aus (Befehl und Ausgabe im Kurzbericht).
13. Keine Datei unter `backend/twox/search/` geändert: `git diff --stat main -- backend/twox/search` ist leer.
14. Keine Migration: `docker compose run --rm backend-dev python manage.py makemigrations --check --dry-run` endet mit Exit 0.
15. Alle Prüfungen des Backend-Jobs aus `.github/workflows/ci.yml` (Z. 48-60 ff.) sind grün: `ruff check .`, `ruff format --check .`, `mypy .`, `pytest`, Worker-Tests (`pytest -m worker`), jeweils über `docker compose run --rm backend-dev …`.
16. Keine neue Abhängigkeit (`backend/pyproject.toml` und Lock unverändert).
17. `down -v` der eigenen Compose-Projekte endet mit Exit 0.

## Vorgaben und Hinweise

- **Schnittstellen vor Umsetzung** (CLAUDE.md, E-03): Die Suche nur über `get_search_backend()` (`backend/twox/search/interface.py:161`). Lesender ORM-Zugriff auf `Section` und `DocumentVersion` für `ordinal`, `sha256`, Einbettungen und Nachbarn ist erlaubt (Speicher, nicht Suche).
- **Felder der Suche:** `SearchRequest` `interface.py:62-82`, `HitLocation` `:85-104`, `SearchHit` `:115-135`, `SemanticState` `:47-58`. `semantic_distance`, `text` und `include_text` kommen aus 124; vorher gibt es sie nicht.
- **Abschnitte:** `Section` in `backend/twox/ingest/models.py:246-336`; `ordinal` `:263`; `page_start`/`page_end` leer bei Markdown `:264-270`; Einbettung leer ohne KI `:288-298`. Ein Abschnitt ohne Seite bleibt Quelle (Fundstelle dann über `heading_path`; für Prüffrage 8 relevant, 136).
- **Versionsregel:** Die Suche liefert nur die neueste eingelesene Version (`ARCHITECTURE.md`, Abschnitt Search). Nachbarn werden deshalb immer aus derselben `DocumentVersion` wie die Hauptquelle geladen, nie aus einer anderen.
- **Startwert der Schwelle:** Steht im Kurzbericht von 124 die Abstandstabelle (Belegstellen der Prüffragen und kleinster Abstand der Kontrollprobe), nimmt der Bearbeiter als Startwert die Mitte zwischen dem größten Abstand einer Belegstelle unter den ersten 10 und dem kleinsten Abstand der Kontrollprobe, auf zwei Stellen gerundet, und nennt beide Ausgangswerte im Kurzbericht. Liegen die Werte überkreuz (Kontrollprobe näher als eine Belegstelle), gilt 0.5 und der Befund kommt als Frage in diesen Auftrag (Status „wartet auf a7“ nur für diese Zahl; der Code wird trotzdem fertig). Gemessen wird nicht in diesem Auftrag.
- **KI optional** (E-59, `DECISIONS.md:69`): Ohne KI gibt es keine Auskunft (D10 Vorgabe (a)); Tests laufen standardmäßig mit KI aus und geschlossenem Modellport (`backend/tests/search/conftest.py:12-31`). Kein Test spricht ein echtes Modell oder das Internet an (Leitplanke 6).
- **Sprachfassungen** (E-61, `DECISIONS.md:71`); **Fundorte mehrerer Geräte** (E-55, `DECISIONS.md:65`); **Einbettungsmodell bge-m3, Abschnittsgröße 2 000** (E-56, E-60, `DECISIONS.md:66, 70`).
- **Leitplanke 4:** Abschnittstexte sind Daten. Dieses Modul wertet sie nicht aus und verändert sie nicht; das Neutralisieren von Begrenzern geschieht im Prompt (122).
- **Leitplanke 3 / D8:** Die harte Schwelle hier ist der erste Schutz der Kontrollfrage; die Zitatprüfung (123) ist der zweite.
- **Protokoll:** wie E-62 und Abschnitt „Logging“ (`ARCHITECTURE.md:512`) – keine Inhalte in Logs.
- **Abgrenzung zu parallelen Aufträgen:** 126 (Antwortdienst) baut auf diesem Modul auf und startet erst danach; 129 (Selbsttest) und 127 berühren andere Dateien. `settings.py` und `.env.example` werden in M3 nacheinander geändert (121 → 125 → 130); vor Beginn auf den aktuellen `main` aufsetzen. `docs/ARCHITECTURE.md` nur in den genannten Stellen ändern.
- **Testdaten:** keine Herstellertexte, keine echten Betriebsdaten, keine Personennamen; selbst geschriebene Sätze oder Texte aus `testdata/klein` (Lizenzlage in `testdata/klein/manifest.yaml`).
- Code, Bezeichner, Kommentare und Doku in `docs/ARCHITECTURE.md` auf Englisch; jede Funktion mit Typangaben.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine, die den Auftrag aufhält.

- **D10 (Auskunft bei ausgeschalteter KI):** (a) keine Antwort, Hinweis mit Link zur Stichwortsuche, Formular gesperrt; (b) Fundstellen als Quellenliste ohne Antworttext. Empfehlung und Vorgabe dieses Auftrags: (a) – `select_context` wirft bei KI aus `ContextDisabledError`.
- **D12 (Suchgüte):** Dieser Auftrag setzt Option (a) um (mehr Kontext: k, mehrere Abschnitte je Dokument, Nachbarn, Sprachfassungen zusammenlegen). (b) stärkere Gewichtung der Überschriften, (c) Umformulieren durch das Modell und (d) Reranker sind nicht Teil dieses Auftrags. Empfehlung: zuerst (a) und in 128 messen.
- Die Startwerte k = 8 und 20 000 Zeichen legt die Leitstelle fest; die Kalibrierung folgt in 128.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
