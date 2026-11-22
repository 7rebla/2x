# Auftrag 120 – Suchgrundlinie für die Prüffragen

Meilenstein: M3 · Freigabestufe: B · Status: zur Prüfung (Messung in „2x“ durch die Leitstelle nach dem Zusammenführen)

Voraussetzung: keine. Läuft in Welle 1 parallel zu 121, 122 und 123 (siehe „Abgrenzung“).

## Ziel

Bevor es eine Antwortlogik gibt, wird gemessen, ob die Belegstelle jeder Prüffrage unter den ersten k Treffern der Suche liegt. Das ist die Obergrenze für M3: Was die Suche nicht liefert, kann keine Antwort belegen („Antworten nur mit Quelle“, Leitplanke 3). Das Ergebnis ist die Grundlage für die Startwerte der Kontextauswahl (Auftrag 125: k, Zeichenbudget) und für die offenen Entscheidungen D12 (Suchgüte) und D2 (Prüffrage 8).

Heutige Lage:

- `backend/twox/search/probes/m2.json` enthält nur Proben für die Prüffragen 1, 3, 7, 9 und 10 (dazu zwei Adressproben). Für die Fragen 2, 4, 5, 6 und 8 gibt es keine Probe, für die Kontrollfrage 11 ebenfalls nicht.
- Prüffrage 3 fand die Suche im Abnahmelauf 060 in keiner Liste (`docs/auftraege/erledigt/060-m2-abnahmelauf.md:82` und `:108`, Nachmessung nach 067 in `docs/auftraege/erledigt/067-abnahme-sprachfassungen-und-fragen.md:134`).
- Prüffrage 10 steht je nach Wortwahl auf Rang 1 oder Rang 10 (`docs/ARCHITECTURE.md:653`, E-67, `060-m2-abnahmelauf.md:106`).
- `evaluate_search` misst nur Recall@5 und Recall@10 (`backend/twox/search/evaluation.py:67`) und liest die Probenliste nur von der Standardeingabe (`backend/twox/search/management/commands/evaluate_search.py:71`).
- Die Messwerte mit allen Handbüchern nach 067 sind in der Doku als „still open“ vermerkt (`docs/ARCHITECTURE.md:652`).

## Umfang

### 1. Neue Probenliste `backend/twox/search/probes/m3.json`

- `m2.json` bleibt **byte-gleich** unverändert (der M2-Abnahmetest und `test_probes.py` hängen daran).
- Gleiches Format wie `m2.json` (`schema_version`, `notes`, `probes`; je Probe nur `id`, `query`, `expected`, `basis`, `notes`), Erweiterungen siehe Abschnitt 2.
- Proben, alle Anfragen **in eigenen Worten** (nie wörtlich die Frage aus `testfactory/questions.yaml` und nie ein Satz aus einem Handbuch):

  | Probe | Prüffrage | erwartete Fundstellen (aus `testfactory/questions.yaml`) |
  | --- | --- | --- |
  | `question-1` | 1 | `aps-documentation-de` S. 18, 31, 38 (`questions.yaml:15-30`) |
  | `question-2` | 2 | `aps-documentation-de` S. 38 (`questions.yaml:49-54`) |
  | `question-3`, `question-3b` | 3 | `aps-documentation-de` S. 36, 38 (`questions.yaml:88-98`) |
  | `question-4` | 4 | `aps-documentation-de` S. 36, 38 (`questions.yaml:119-129`) |
  | `question-5` | 5 | `aps-documentation-de` S. 34 (`questions.yaml:158-163`) |
  | `question-6` | 6 | `aps-documentation-de` S. 34, 36, 38 (`questions.yaml:188-203`) |
  | `question-7`, `question-7b` | 7 | `aps-documentation-de` S. 22, 27 (`questions.yaml:223-233`) |
  | `question-9` | 9 | `ur5e-user-manual-de` S. 16, 101, 102 (`questions.yaml:285-300`) |
  | `question-10`, `question-10b` | 10 | `ur5e-user-manual-de` S. 81, 84, 86, 252; `ur5e-software-handbook-en` S. 46 (`questions.yaml:316-345`) |
  | `control-11` | 11 (Kontrollfrage) | keine (leere Liste `expected`, siehe Abschnitt 2) |

- Seitenzahlen sind wie in `m2.json` PDF-Seiten ab 1 („PDF-S.“) und werden aus den `locator`-Angaben von `questions.yaml` übernommen. Quellen in den Git-Repositorys der Testfabrik (`aps-repository`, `aps-repository-dev`) haben keine Seiten und keine Prüfsumme und bleiben weg, wie in `m2.json` (Vorgabe D3, Empfehlung (a)).
- **Andere Sprachfassung (E-61):** Jede Probe mit `aps-documentation-de` erwartet zusätzlich `aps-documentation-en` mit denselben Seiten, gekennzeichnet über `basis.other_language_edition` wie in `m2.json:8`. Für S. 18, 22, 27, 31, 36 und 38 ist die Gleichheit der Seiten in 067 belegt (`067-…md:67-75`). **S. 34 ist dort nicht geprüft:** vor dem Eintrag nach dem Muster von 067 an den Dateien unter `testfactory/extern/` des Projektordners nur lesend prüfen (nur Kennzahlen wie Zählung von „V18“ oder „1512SP“ je Seite, kein Text in Datei, Bericht oder Terminal-Ausgabe, die ins Repository gelangt). Bestätigt sich die Seite nicht, `aps-documentation-en` für S. 34 weglassen und im Kurzbericht nennen.
- Prüfsummen (`sha256`) kommen aus `testfactory/manifest.yaml`; `ur5e-software-handbook-en` hat keine andere Sprachfassung in der Testfabrik (Einträge `manifest.yaml:1080-1134`).
- **Zweite Formulierungen** für die Fragen 3, 7 und 10 (`question-3b`, `question-7b`, `question-10b`): andere Wortwahl als die erste Probe, ohne den Fachbegriff, der die erste Probe trägt. Für Frage 10 entspricht `question-10b` dem Fall aus 060 ohne den englischen Begriff (Rang 10), aber nicht wörtlich dessen Satz.
- **Prüffrage 8** bekommt in diesem Auftrag **keine** Probe: Alle vier Quellen sind Markdown in `aps-repository-dev` und nicht eingelesen (`questions.yaml:251-271`). Sie wird in `notes` von `m3.json` und im Bericht als „nicht messbar“ ausgewiesen. Die Probe folgt mit Auftrag 136, falls a7 D2 (a) wählt.
- **Kontrollprobe `control-11`:** eigene Formulierung der Frage nach dem letzten Wartungstermin der Frässtation; `basis` `{"question": 11}`; `expected` ist eine leere Liste.

### 2. Format der Probenliste (`backend/twox/search/evaluation.py`)

- `schema_version` bleibt 1; jede Erweiterung ist optional, sodass `m2.json` unverändert gültig bleibt.
- **Kontrollprobe:** `expected` darf eine leere Liste sein. Eine solche Probe wird gesucht, aber nicht bewertet (kein Rang, zählt nicht in Recall und MRR); ausgegeben werden die ersten 10 Einträge der kombinierten und der Vektorliste, **nur mit Kennungen**: Rang, `section_id`, `version_id`, `sha256`, Seiten, Geräteschlüssel. Kein Titel aus dem Dokument, kein Abschnittstext, kein Ausschnitt.
- **Fundstelle über den Überschriftenpfad** (Vorbereitung für 136, Markdown ohne Seiten, E-55): `ExpectedPlace` bekommt das optionale Feld `heading_path` (Liste von Überschriften). Genau eines von `pages` oder `heading_path` muss gesetzt sein, sonst `ProbeFormatError`. Ein Eintrag passt, wenn die Prüfsumme stimmt und der erwartete Pfad ein Präfix des Überschriftenpfads des Abschnitts ist (Vergleich nach Vereinheitlichung von Leerraum und Groß-/Kleinschreibung). `Place` trägt dazu den Überschriftenpfad (`SearchHit.heading_path`, `interface.py:133`; `Section.heading_path`, `ingest/models.py:271`). Grenzen im Parser: höchstens 8 Ebenen, je Überschrift höchstens 120 Zeichen (damit dort keine Textauszüge landen). `matching_place` (`evaluation.py:298`) bleibt eine reine Funktion mit derselben Signatur, weil 127 sie wiederverwenden soll.
- **Dateipfad bei Repository-Quellen:** `ExpectedPlace` bekommt zusätzlich das optionale Feld `path` (Pfad der Datei im Archiv, z. B. `docs/…/datei.md`; relativ, ohne `..`, höchstens 200 Zeichen). `path` ist genau dann Pflicht, wenn `heading_path` gesetzt ist, und bei `pages` verboten; sonst `ProbeFormatError`. Für den Treffer zählt weiter nur die Prüfsumme der hochgeladenen Datei mit dem Überschriftenpfad; `path` dient der Prüfung gegen `questions.yaml` (siehe Akzeptanzkriterium 5). Hintergrund: Repository-Einträge im Manifest (`kind: git-archive`) haben keine Prüfsumme je Datei, nur `tree_sha256` (`testfactory/manifest.yaml:56`, `:71-72`); die Prüfsumme der Probe gehört dann zur einzelnen Datei am festen Commit (136).
- Unbekannte Schlüssel bleiben ein Fehler (`evaluation.py:206-212`).

### 3. Messung (`evaluation.py`, `evaluate_search`)

- **Recall bei mehreren k:** neue Option `--cutoffs` (z. B. `--cutoffs 5,8,10,12`), Standard bleibt `5,10`. Ohne die Option sind Text- und JSON-Ausgabe für `m2.json` unverändert (bestehende Tests in `backend/tests/search/test_evaluation.py` bleiben ohne Änderung grün). Erlaubt sind ganze Zahlen von 1 bis `DEPTH` (`evaluation.py:65`, 50), aufsteigend, ohne Doppelte; sonst Abbruch mit Meldung und Exit 1. Die Zusammenfassung je Art enthält Recall@k für jedes k und MRR.
- **Rang je Probe:** wie bisher der Rang der besten (ersten richtigen) Fundstelle je Art (Stichwort, Vektor, kombiniert). Neu: bei Proben mit mehreren erwarteten Seiten zusätzlich in JSON der erste Rang **je erwarteter Fundstelle** (Handbuch und Seite bzw. Überschriftenpfad), damit für Frage 6 (S. 34 gegenüber S. 36/38) und Frage 7 (S. 22 und 27) sichtbar ist, ob beide Stellen unter den ersten k liegen. Die andere Sprachfassung zählt dabei für dieselbe Seite (E-61).
- **Probenliste nach Namen:** neue Option `--probes NAME` liest `twox/search/probes/NAME.json` aus dem Paket (Name nur `^[a-z0-9-]+$`, sonst Fehler); ohne die Option wird wie bisher von der Standardeingabe gelesen. (124 baut darauf mit `evaluate_search --probes m3 --distance` auf.)
- Die Ausgabe enthält weiter nur Ränge, Seiten, Prüfsummen und Kennungen, nie Abschnittstexte oder Ausschnitte (`evaluation.py:36-37`).
- Bei ausgeschalteter KI (E-59) misst der Befehl wie bisher nur die Stichwortsuche und baut keine Verbindung zum Modelldienst auf; das gilt auch für die Kontrollprobe.

### 4. Messlauf in der Testumgebung „2x“

- Gemessen wird in der laufenden Testumgebung „2x“ mit allen eingelesenen Handbüchern, `TWOX_AI_ENABLED=1`, bge-m3 und 2 000 Zeichen je Abschnitt (E-60), **nur lesend**: kein Einlesen, kein Upload, keine Migration, kein `down`, kein Neustart von Diensten. Weg: aus dem eigenen Arbeitsverzeichnis ein Einmal-Container mit dem Code des Zweigs gegen die Datenbank der Testumgebung, z. B. `docker compose -p 2x --env-file <.env des Projektordners> --profile dev run --rm --no-deps backend-dev python manage.py evaluate_search --probes m3 --cutoffs 5,8,10,12` (Text und `--json`). Vorher mit `docker compose -p 2x ps` prüfen, dass `db` und `api` laufen und Ollama erreichbar ist (`check_llm`).
- Läuft die Testumgebung nicht, fehlt die KI oder verweigert die Berechtigungsprüfung der Sitzung den Lauf: nicht auf anderem Weg versuchen, im Kurzbericht unter „Abweichungen“ vermerken. Dann misst die Leitstelle nach dem Muster von 067 (`067-…md:132-134`) und trägt die Tabelle nach.
- Zusätzlich ein Lauf im eigenen Compose-Projekt mit `testdata/klein/` (zeigt „not ingested“ – erwartbar) als Nachweis, dass Befehl und Format ohne Handbücher funktionieren.

### 5. Doku

- `docs/ARCHITECTURE.md`, Abschnitt „Search“ unter „Limits and known gaps“ (Z. 649-659): Messwerte nach 067 und dieses Auftrags nachtragen (Recall@k, MRR, Ränge der Prüffragen, Abhängigkeit von der Wortwahl mit den Zahlen aus 3/3b, 7/7b, 10/10b); Satz „measurements with all manuals after 067 are still open“ (Z. 652) ersetzen.
- `docs/ARCHITECTURE.md` Z. 585 (Tabelle der Prüfungen) und Z. 604 („What CI does not run“): Probenliste `m3.json` und die neuen Optionen nennen.
- `README.md` Z. 229-232 (Abschnitt zu `evaluate_search`): `--probes`, `--cutoffs`, Kontrollprobe und Überschriftenpfad kurz beschreiben.
- Modul-Docstrings von `evaluation.py` und `evaluate_search.py` nachziehen.

## Nicht-Ziele

- Keine Änderung an der Suche selbst (`backend/twox/search/postgres.py`, `interface.py`, `api.py`), an Rangfolge, Gewichtung oder Datenmodell. Ein Abstand (`semantic_distance`) oder Volltext im Treffer ist Auftrag 124 (wartet auf D11).
- Keine Antwortlogik, kein Chat-Modell, nichts unter `backend/twox/answers/` (121, 122, 123).
- Keine Probe für Prüffrage 8 und kein Upload von Markdown-Dateien (136, wartet auf D2).
- Keine Änderung an `m2.json`, `backend/tests/search/test_probes.py` (außer, falls nötig, dem Auslagern gemeinsamer Hilfsfunktionen ohne Änderung der Prüfungen), `testfactory/questions.yaml` oder `backend/tests/acceptance/test_m2.py`.
- Keine Verbesserung der Suchgüte (D12); dieser Auftrag misst nur.
- Keine Änderung an `docs/STATUS.md`, `docs/ROADMAP.md` oder `docs/DECISIONS.md` (pflegt die Leitstelle).

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/search/probes/m3.json` (neu)
- `backend/twox/search/evaluation.py`
- `backend/twox/search/management/commands/evaluate_search.py`
- `backend/tests/search/test_evaluation.py` (nur neue Tests; bestehende unverändert)
- `backend/tests/search/test_probes_m3.py` (neu; Prüfungen von `m3.json` gegen Manifest und `questions.yaml`, Hilfsfunktionen aus `test_probes.py` dürfen wiederverwendet werden)
- `docs/ARCHITECTURE.md` (nur Z. 585, Z. 604 und Abschnitt „Search“ Z. 649-659)
- `README.md` (nur Abschnitt `evaluate_search`, Z. 229-232)

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Alle Prüfungen aus `.github/workflows/ci.yml` sind grün, mindestens der Job `backend` vollständig: `ruff check .`, `ruff format --check .`, `mypy .`, `pytest`, `pytest -m worker`, Übersetzungskatalog, `makemigrations --check --dry-run` (keine Migration), Lizenzprüfung, OpenAPI-Schema unverändert. Die Jobs `web`, `testfactory` und `e2e` bleiben grün (keine Änderung dort erwartet).
2. `docker compose run --rm backend-dev pytest tests/search` ist grün, mit neuen Tests für:
   - Recall@k bei frei gewählten k (z. B. 5, 8, 10, 12) mit einem von Hand nachgerechneten Beispiel, und ungültige `--cutoffs` (0, über `DEPTH`, doppelt, absteigend, keine Zahl) mit Meldung und Exit 1;
   - den Rang je Probe und den ersten Rang je erwarteter Fundstelle bei einer Probe mit zwei Seiten;
   - eine Markdown-Fundstelle über den Überschriftenpfad (Treffer bei Präfix, kein Treffer bei anderem Pfad oder anderer Prüfsumme, Formatfehler bei `pages` und `heading_path` zugleich, bei keinem von beiden, bei zu langer Überschrift, bei `heading_path` ohne `path` und bei `pages` mit `path`); alle Testtexte selbst geschrieben;
   - die Kontrollprobe mit leerer `expected`-Liste: nicht in Recall und MRR gezählt, Ausgabe der ersten 10 Einträge nur mit Kennungen (Test: kein Abschnittstext und kein Ausschnitt in Text- und JSON-Ausgabe);
   - `--probes m3` und `--probes` mit ungültigem oder unbekanntem Namen;
   - KI aus: keine Verbindung zum Modelldienst, auch mit Kontrollprobe (wie die bestehenden Tests mit Attrappe).
3. Die bestehenden Tests in `backend/tests/search/` (insbesondere `test_evaluation.py`, `test_probes.py`) und `backend/tests/acceptance/` laufen **unverändert** grün; die Ausgabe ohne `--cutoffs` für `m2.json` ist unverändert (Test).
4. `docker compose run --rm backend-dev mypy .` läuft ohne Fehler; jede neue Funktion hat Typangaben.
5. Ein Formattest prüft, dass `m3.json` nur Verweise enthält: je Probe nur die Felder `id`/`query`/`expected`/`basis`/`notes`; jede `manifest_id` steht in `testfactory/manifest.yaml`; bei Fundstellen mit `pages` ist der Eintrag `kind: file` und die Prüfsumme gleich der des Manifests (wie `test_probes.py:120-128`); bei Fundstellen mit `heading_path` ist der Eintrag `kind: git-archive`, die Prüfsumme nur auf das Format geprüft (64 Zeichen hex, klein) und `path` gleich dem Dateipfad einer Quelle derselben `manifest_id` in der Prüffrage (Teil des `locator` vor dem Komma, `questions.yaml:252-271`) – mit eigenem Test, der eine selbst geschriebene Probe dieser Art als gültig und eine mit fremdem `path` oder `kind: file` als ungültig erkennt, damit 136 die Probe für Frage 8 ohne Code- oder Teständerung ergänzen kann; jede Seite steht in den Quellen der Prüffrage in `questions.yaml` und jede PDF-Seite dieser Quellen ist erwartet (wie `test_probes.py:131-160`); keine Anfrage ist wörtlich die Frage aus `questions.yaml`; die Prüffragen 1–7, 9, 10 und die Kontrollfrage 11 sind abgedeckt, die Fragen 3, 7 und 10 je zweimal mit verschiedenen Anfragen; Prüffrage 8 fehlt und ist in `notes` begründet (der Test lässt eine spätere Probe `question-8` mit `heading_path`-Fundstellen nach den obigen Regeln zu, damit 136 grün bleibt).
6. Der Kurzbericht enthält eine Tabelle Probe × k (5/8/10/12) × Modus (kombiniert, nur Vektor; Stichwort informativ) mit Rang der besten Belegstelle, Recall@k und MRR aus der Testumgebung „2x“ mit `TWOX_AI_ENABLED=1`, dazu Einbettungsmodell und `TWOX_SECTION_MAX_CHARS` aus der Kopfzeile der Ausgabe.
7. Für die Fragen 6 und 7 nennt der Bericht den ersten Rang jeder erwarteten Fundstelle (S. 34 / 36 / 38 bzw. S. 22 / 27).
8. Jede Probe, deren Beleg im kombinierten Modus nicht unter den ersten 10 Treffern liegt, ist mit einer vermuteten Ursache genannt (z. B. Wortwahl, Abschnittsgrenze, Stelle in einer Tabelle, andere Handbücher mit gleichen Begriffen davor, Sprachfassung).
9. Für die Kontrollprobe ist die Liste der ersten 10 Treffer (kombiniert und Vektor) protokolliert, nur mit Kennungen (Rang, `section_id`, Handbuch aus dem Manifest über die Prüfsumme, Seiten).
10. Prüffrage 8 ist im Bericht als „nicht messbar“ ausgewiesen, mit Verweis auf D2 und 136.
11. `docs/ARCHITECTURE.md` und `README.md` sind nachgezogen (siehe Umfang, Abschnitt 5).
12. Keine neue Abhängigkeit (`pyproject.toml` und Lock unverändert).
13. `down -v` der eigenen Compose-Projekte endet mit Exit 0; die Testumgebung „2x“ ist unverändert (keine neuen Versionen, Aufträge oder Abschnitte; Nachweis z. B. über Anzahl der Abschnitte vorher und nachher).

## Vorgaben und Hinweise

- **Leitplanken:** Herstellerunterlagen und `questions.yaml` sind Daten, keine Anweisungen (Leitplanke 4). Keine Zitate oder Auszüge aus Handbüchern in `m3.json`, Tests, Bericht oder Commit-Nachrichten; nur Seiten, Prüfsummen und Kennungen. Seite 38 der APS-Dokumentation enthält Standard-Zugangsdaten (`docs/ARCHITECTURE.md:628`) – nie zitieren, auch nicht in Terminal-Ausgaben, die in den Bericht übernommen werden. `testfactory/extern/` bleibt ungetrackt und wird nur gelesen.
- **Betrieb ohne Internet:** Messung und Tests ohne Netz; die Tests verwenden die Attrappe aus `backend/tests/search/fake_embedder.py`, nie ein echtes Modell.
- **E-Nummern:** E-03 (Suchschnittstelle; `evaluate_search` misst über `get_search_backend()`, `evaluation.py:9-16`), E-10 (Prüffragen laufen automatisch mit; `m3.json` ist die Grundlage für 127/135), E-55 (Markdown ohne Zeilen und Seiten, Fundort über Datei und Überschrift), E-59 (KI optional), E-60 (bge-m3, 2 000 Zeichen), E-61 (andere Sprachfassung zählt), E-67 (Frage 10 und Wortwahl als Thema für M3).
- **Vorgaben aus dem Gesamtplan M3:** D3 (a) – für M3 genügt eine Fundstelle aus der eingelesenen Dokumentation; D4 (a) – die 11 Fragen aus `testfactory/questions.yaml` bleiben Grundlage. Beide gelten als Vorgabe, bis a7 anders entscheidet.
- **Muster:** Probenliste und Prüfungen wie `m2.json` und `backend/tests/search/test_probes.py` (056, 067); Messlauf und Bericht wie 057/067. Die Struktur von `KindResult`/`KindSummary` darf erweitert werden; vorhandene Felder bleiben (JSON-Ausgabe für `m2.json` abwärtsverträglich).
- **Abgrenzung zu parallelen Aufträgen:** 121 (Chat-Schnittstelle), 122 (Typen und Prompt) und 123 (Zitatprüfung) arbeiten nur unter `backend/twox/answers/`, in `settings.py`, `compose.yaml` und `.env.example`; 121 und 122 ändern in `docs/ARCHITECTURE.md` den Abschnitt `answers` (Z. 134). Dieser Auftrag ändert `ARCHITECTURE.md` nur an den oben genannten Stellen und nicht die Modultabelle (Z. 134-135); Konflikte löst die Leitstelle beim Zusammenführen. 124 ändert nach diesem Auftrag ebenfalls `evaluation.py` und `evaluate_search.py` (Ausgabe des Abstands) – deshalb die Messung so aufbauen, dass eine weitere Spalte ohne Umbau hinzukommen kann. 136 ergänzt später nur die Probe für Frage 8 in `m3.json` mit `heading_path`.
- **Keine Personennamen, keine lokalen Pfade mit Benutzernamen** in Dateien, Bericht oder Commits (E-22). Kein Python oder npm unter Windows; alles über `docker compose`.
- **Commits:** klein, englisch, auf dem eigenen Zweig; nicht pushen (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

Keine, die den Auftrag aufhalten. Das Ergebnis fließt in die Vorlagen D12 (Suchgüte: zuerst mehr Kontext in 125, danach ggf. Überschriften stärker gewichten als Folgeauftrag) und D2 (Prüffrage 8: (a) zwei Markdown-Dateien in der Testumgebung hochladen, (b) Frage 8 erst mit M5, (c) mit 8 von 9 antreten; Empfehlung (a)) ein; beide legt die Leitstelle a7 gesondert vor.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Code, Probenliste, Tests und Doku fertig; die Messung mit allen Handbüchern (Kriterien 6–9, 13 für „2x“) ist **von der Leitstelle nach dem Zusammenführen auszuführen** (Vorgabe der Leitstelle für diesen Lauf, siehe Abweichung 1). Eigenes Compose-Projekt `twox-120`, `TWOX_API_PORT=18120`, Docker Engine 29.9.3, Compose v5.7.0. „2x“ und „twox-leit“ nicht angefasst. Keine neue Abhängigkeit, keine Migration, keine Änderung an Suche, API oder Datenmodell.

### Was wurde gebaut?

- **`backend/twox/search/probes/m3.json`** (neu, `m2.json` byte-gleich): 13 Proben – `question-1`, `-2`, `-3`, `-3b`, `-4`, `-5`, `-6`, `-7`, `-7b`, `-9`, `-10`, `-10b` und `control-11`. Fundstellen und Seiten wie in der Tabelle des Auftrags, Prüfsummen aus dem Manifest, APS-Proben zusätzlich mit `aps-documentation-en` (E-61). `question-1/-3/-7/-9/-10` verwenden die Anfragen aus `m2.json` (vergleichbar mit 060/067); `-3b` ohne „TXT“/„Kommunikationsprotokoll“, `-7b` ohne „fahrerlos“/„Fahrlinie“, `-10b` ohne „Safeguard Stop“ und nicht wörtlich der Satz aus 060. Prüffrage 8 fehlt, in `notes` als „not measurable yet“ mit Verweis auf D2/136 begründet.
- **Seite 34 der englischen Fassung geprüft** (nach dem Muster von 067): Wegwerf-Container ohne Netz mit der PDF-Bibliothek des festgelegten Docling-Images (Digest aus `deploy/compose/compose.yaml`), Dateien nur lesend eingebunden, Prüfsummen beider Dateien gleich denen des Manifests, beide 38 Seiten. Nur Kennzahlen ausgegeben: S. 34 hat in beiden Fassungen je 1× „V18“, 1× „1512SP“, 1× „S7-1200“, 3× „TIA“, Zahlenabgleich 1,0 (8/8 Zahlen); Nachbarseiten 33/35 ohne diese Begriffe. → `aps-documentation-en` S. 34 ist eingetragen. Kein Text gespeichert oder ausgegeben; Prüfskript lag nur im Scratchpad.
- **`evaluation.py`:**
  - `ExpectedPlace` mit optionalem `heading_path` und `path`; genau eines von `pages`/`heading_path`, `path` genau bei `heading_path`; höchstens 8 Ebenen, je 120 Zeichen, `path` relativ, ohne `..`, `.`, `\`, höchstens 200 Zeichen. Treffer bei gleicher Prüfsumme und Präfix des Überschriftenpfads (Leerraum vereinheitlicht, `casefold`). `Place` trägt `heading_path`, `section_id`, `version_id` (mit Vorgaben, alte Aufrufe gültig). `matching_place` bleibt rein mit derselben Signatur.
  - Kontrollprobe: `expected: []` ist nur erlaubt, wenn die Kennung mit `control-` beginnt (und umgekehrt), siehe Abweichung 2. Status `control`, kein Rang, zählt nicht in Recall/MRR; je Art (Stichwort, Vektor, kombiniert) die ersten 10 Einträge nur mit Rang, `section_id`, `version_id`, `sha256`, Seiten, Geräteschlüssel.
  - `judge`/`summarise` mit frei wählbaren Grenzen (`correct_in_top`, `recall_at` je k) und erstem Rang je erwarteter Fundstelle (`place_ranks`; die andere Sprachfassung zählt über `basis.other_language_edition` für dieselbe Seite). Felder von 056 (`correct_in_top_5/10`, `recall_at_5/10`) bleiben.
  - `parse_cutoffs` (1…50, aufsteigend, ohne Doppelte, nur ganze Zahlen) und `probe_list_text` (Name `^[a-z0-9-]+$`, Datei unter `twox/search/probes/`).
  - Ausgabe: Spalten `top k`/`Recall@k` je Grenze; mit `--cutoffs` zusätzlich Tabelle „First rank per expected place“ und in JSON `cutoffs`, `recall_at`, `correct_in_top`, `place_ranks`. **Ohne `--cutoffs` sind Text und JSON für Listen ohne Kontrollprobe Byte für Byte wie vorher** (die neuen JSON-Schlüssel entfallen dann; `controls` erscheint nur bei Kontrollproben). Für 124 ist eine weitere Spalte je Art ohne Umbau möglich (`KindResult`-Feld plus Zelle in `_probe_rows`).
- **`evaluate_search.py`:** Optionen `--probes NAME` und `--cutoffs K,K,…`; ungültige Werte enden mit `CommandError` („Invalid --cutoffs: …“, „Invalid --probes: …“), Exit 1. Docstring nachgezogen.
- **Tests:** `test_evaluation.py` nur ergänzt (Importliste erweitert, bestehende Tests unverändert): Golden-Test der Ausgabe ohne `--cutoffs` (Text exakt und JSON mit Schlüsselreihenfolge, erzeugt vor der Änderung mit dem alten Code, KI an und aus), `--probes m2` gleich Standardeingabe, Recall@5/8/10/12 und MRR von Hand (49/180), gültige/ungültige Grenzen (0, 51, doppelt, absteigend, keine Zahl, leer; Meldung und `returncode == 1`), Rang je Fundstelle mit zwei Seiten und anderer Sprachfassung, Seitenbereich, Überschriftenpfad (Präfix, anderer Pfad, längerer Pfad, andere Prüfsumme, alle Formatfehler, Grenzwerte 8/120 gültig, Markdown-Abschnitt in der Datenbank gefunden), Kontrollprobe (nicht gezählt, Liste nur mit Kennungen in Text und JSON, kein Abschnittstext, kein Titel, höchstens 10 Einträge, Modellausfall), KI aus ohne Modellaufruf auch mit Kontrollprobe, `--probes m3` und ungültige Namen (`M3`, `../m2`, `m2.json`, leer, `m9`). Neu `test_probes_m3.py`: Prüfungen als Funktionen, die Probleme zurückgeben; `m3.json` ohne Probleme; Schlüssel je Probe; Abdeckung 1–7, 9, 10, 11, Fragen 3/7/10 je zweimal verschieden; keine Anfrage gleich der Prüffrage; Frage 8 fehlt mit Begründung oder nur mit `heading_path`; Sprachfassungen; eigene Proben mit `heading_path` (gültig; ungültig bei fremdem `path`, fremdem Repository, `kind: file`, Prüfsumme in Großbuchstaben) und mit Seiten (falsche Seite, falsche Prüfsumme, Anfrage = Frage, Kontrollprobe zu Frage mit Belegen). Hilfsfunktionen aus `test_probes.py` wiederverwendet, `test_probes.py` unverändert.
- **Doku:** `docs/ARCHITECTURE.md` Z. 585 (Tabelle), Z. 604 („What CI does not run“), Abschnitt „Search“: Satz „still open“ durch die Werte der Nachmessung nach 067 ersetzt, neuer Punkt „Baseline of M3“ (Werte mit allen Handbüchern trägt die Leitstelle nach der Messung nach). `README.md` Abschnitt `evaluate_search`: `--probes`, `--cutoffs`, Kontrollprobe, Überschriftenpfad. Modultabelle (Z. 134–135) nicht berührt.

### Wie wurde getestet?

`D` = `docker compose -p twox-120`; `.env` aus `.env.example`, nur `TWOX_API_PORT=18120`.

| Nr. | Ergebnis | Nachweis |
| --- | --- | --- |
| 0 | erfüllt | `docker version` 29.9.3, `docker compose version` v5.7.0, je Exit 0 |
| 1 | erfüllt (backend) | siehe Prüfliste unten; Jobs `web`, `testfactory`, `e2e` nicht berührt (keine Datei dort geändert) und nicht lokal gelaufen |
| 2 | erfüllt | `D run --rm backend-dev pytest tests/search` grün, neue Tests siehe oben |
| 3 | erfüllt | bestehende Tests in `tests/search` und `tests/acceptance` unverändert grün; Golden-Test der Ausgabe ohne `--cutoffs` |
| 4 | erfüllt | `mypy .` ohne Fehler |
| 5 | erfüllt | `test_probes_m3.py` |
| 6–9 | offen | Messung in „2x“ durch die Leitstelle, Befehle unten |
| 10 | erfüllt | Prüffrage 8 „nicht messbar“ (Markdown aus `aps-repository-dev` nicht eingelesen), Verweis D2 und 136, auch in `m3.json`/`notes` |
| 11 | erfüllt | ARCHITECTURE.md und README.md nachgezogen |
| 12 | erfüllt | `pyproject.toml` und Lock unverändert |
| 13 | eigener Teil erfüllt | `D --profile dev down -v` Exit 0, danach kein Container und kein Volume `twox-120*`; „2x“ nicht benutzt (Zählung vorher/nachher gehört zur Messung der Leitstelle) |

**Prüfliste backend** (wie `ci.yml`, je Exit 0): `ruff check .` („All checks passed!“), `ruff format --check .`, `mypy .` („Success: no issues found in 196 source files“), `pytest` 2459 passed / 6 deselected / 0 failed, `pytest -m worker` 6 passed, `makemessages -l de --add-location=file` ohne Unterschied in `backend/locale`, `makemigrations --check --dry-run` („No changes detected“), `sh scripts/check-licenses.sh`, `spectacular --file` ohne Unterschied in `web/openapi`. Nach der letzten kleinen Änderung (Zeile „no entries“ bei leerer Kontrollliste) erneut `ruff check`, `ruff format --check`, `mypy` und `pytest tests/search tests/acceptance` (415 passed).

Lauf im eigenen Projekt ohne Handbücher: `D run --rm -T backend-dev python manage.py evaluate_search --probes m3 --cutoffs 5,8,10,12` Exit 0, 13 Proben, Spalten `top 5/8/10/12`, `Recall@5/8/10/12`, „Not ingested: 12 of 13 probes“, `control-11` als „control, not judged“; `--json` mit `cutoffs` und `recall_at`; `--cutoffs 10,5` Exit 1.

### Messung in „2x“ – von der Leitstelle nach dem Zusammenführen auszuführen

1. Vorher: `docker compose -p 2x ps` (`db`, `api` laufen); `docker compose -p 2x exec -T api python manage.py check_llm`; Zählung `docker compose -p 2x exec -T db psql -U twox -d twox -Atc "select (select count(*) from ingest_section), (select count(*) from files_documentversion), (select count(*) from ingest_ingestjob)"`.
2. Messung (Code des Zweigs bzw. `main` nach dem Zusammenführen; über einen Einmal-Container mit `--no-deps` oder nach Neubau von `api`):
   `docker compose -p 2x --env-file <.env des Projektordners> --profile dev run --rm --no-deps backend-dev python manage.py evaluate_search --probes m3 --cutoffs 5,8,10,12` und dasselbe mit `--json`.
3. Nachher dieselbe Zählung wie in 1 (muss gleich sein).
4. Eintragen: Tabelle Probe × k (5/8/10/12) × Modus (kombiniert, Vektor; Stichwort informativ) mit Rang, Recall@k, MRR und Kopfzeile (Modell, `TWOX_SECTION_MAX_CHARS`); für `question-6` und `question-7`/`-7b` die Zeilen „First rank per expected place“ (S. 34/36/38 bzw. 22/27); für jede Probe ohne Beleg unter den ersten 10 (kombiniert) eine vermutete Ursache; für `control-11` die Liste der ersten 10 (Rang, `section_id`, Handbuch über die Prüfsumme, Seiten). Die Ausgabe enthält keine Texte; Seite 38 der APS-Dokumentation trotzdem nicht zitieren.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a6485d5523b62fca7`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a6485d5523b62fca7` (relativ zum Projektordner)
- Nicht gepusht, nichts zusammengeführt.

### Abweichungen

1. **Keine Messung in „2x“:** Nach der Vorgabe der Leitstelle für diesen Lauf nur beschrieben (oben); Kriterien 6–9 und der „2x“-Teil von 13 sind daher offen.
2. **Kennzeichnung der Kontrollprobe über die Kennung `control-…`:** Der bestehende, unveränderte Test verlangt für `expected: []` weiter den Fehler „expected a non-empty list“. Damit beides gilt, ist eine leere Liste nur bei einer Kennung mit `control-` erlaubt (und eine solche Probe darf keine Fundstelle haben). Ein eigener Schlüssel wäre nach Kriterium 5 nicht zulässig.
3. **Neue JSON-Felder nur mit `--cutoffs`:** Damit die Ausgabe ohne `--cutoffs` für `m2.json` unverändert bleibt, erscheinen `cutoffs`, `recall_at`, `correct_in_top` und `place_ranks` (und die Tabelle der Ränge je Fundstelle) nur mit `--cutoffs`. Für die Messung ist `--cutoffs` ohnehin gesetzt.
4. **Eigenes Projekt mit KI an:** `.env.example` schaltet die KI ein; beim Lauf mit `--probes m3` im eigenen Projekt wurde die Kontrollanfrage einmal an Ollama auf dem Host eingebettet (nur lesend, keine Abschnitte vorhanden, Listen leer). Die Tests selbst nutzen nur die Attrappe.
5. `testdata/klein/` wurde nicht eingelesen (ohne Docling kein Einlesen); der Nachweis ohne Handbücher läuft auf der leeren Datenbank von `twox-120` („not ingested“, wie erwartet).
6. Lokal bleiben die Images `twox-120-*`; die ignorierte `.env` hat `TWOX_API_PORT=18120`.
