# Auftrag 155 – Prompt: verschiedene Typangaben für dasselbe Bauteil sind ein Widerspruch

Meilenstein: M3 · Freigabestufe: B (Teil C von E-76) · Status: zur Prüfung

Voraussetzung: 154 (Werte hinter einem Wort) liegt auf `main`.

## Ziel

Diagnose 152: Bei Prüffrage 6 nennt gemma4 beide Typangaben und zitiert beide Gruppen, meldet aber keinen Widerspruch. Mit einem Zusatz zu Regel 4 (Variante C2) und nur den beiden Gruppenabschnitten meldete es 6/6 den Widerspruch mit beiden Gruppen; die Kontrollfrage sagte mit C2 in allen Varianten ab.

Nach diesem Auftrag nennt Regel 4 ausdrücklich: Verschiedene Typ- oder Bestellangaben für dasselbe Bauteil desselben Geräts sind ein Widerspruch, auch innerhalb eines Dokuments.

## Umfang

1. **Regel 4 ergänzen** in `SYSTEM_TEMPLATE` (`backend/twox/answers/prompt.py`), Wortlaut nach C2 aus dem Bericht 152 (der Bearbeiter darf ihn verbessern). Die Schärfung aus 148 (Ergänzungen, Warnhinweise, andere Geräte/Versionen sind kein Widerspruch) bleibt. Feste Phrase und Zitatprüfung unverändert.
2. **Prüfung am echten Modell, lokal** wie in 148 (Umfang 3) mit selbst geschriebenen Testabschnitten und neutralen Platzhaltern, je 3 Läufe: die Fälle (a)–(d) und (b2), (c2) aus 148 bleiben wie dort; neu (e) zwei Abschnitte nennen für dasselbe Bauteil von Gerät A verschiedene Typangaben → `contradiction`; (f) zwei verschiedene Bauteile mit verschiedenen Typangaben → kein Widerspruch.
3. **Prüfung in „2x“, nur lesend:** Prüffrage 6 und Kontrollfrage 11 (beide Wortlaute) je 3 Seeds über das Hilfsskript aus 152 (`Claude outputs/152/scripts/`), Prompt von `main` gegen den neuen, mit dem jeweils aktuellen Kontext von `main`. Kein Neubau von „2x“.
4. **Tests:** Snapshot `prompt_system.txt`, Test für die Kernaussagen der ergänzten Regel 4 (wie in 148).
5. **CI-Aufzeichnungen** neu aufnehmen mit gemma4 (`prompt_version` ändert sich; `/api/ps` vorher leer); scheitert eine Frage an einer Prüfung, nichts aufweichen, Status „wartet auf a7“.
6. **Doku:** Satz zu Regel 4 in `docs/ARCHITECTURE.md`, Modul-Docstring.

## Nicht-Ziele

- Keine Änderung an Zitatprüfung, `types.py`, Kontextauswahl, Suche, Startwerten.
- Kein Messlauf über alle Fragen.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/answers/prompt.py`
- `backend/tests/answers/` (Prompt-Tests, Snapshot), `backend/tests/answers/recorded/ci_questions.json`
- `docs/ARCHITECTURE.md` (nur Regel 4)
- diese Auftragsdatei

## Akzeptanzkriterien (prüfbar)

1. Regel 4 ergänzt; Phrase, Zitatprüfung, übrige Regeln unverändert.
2. Lokale Fälle: (a), (e) `contradiction` in mindestens 2/3; (b), (b2), (c), (c2), (f) `answered` 3/3; (d) Absage 3/3 – vorher/nachher im Bericht.
3. „2x“: Kontrollfrage 3/3 Absage in beiden Wortlauten; Frage 6: Status und genannte Gruppen je Seed vorher/nachher.
4. CI wie `ci.yml` grün; Aufzeichnungen neu, nur Modellausgabe, Digest wie DECISIONS.
5. Diff nur in den genannten Bereichen, keine neue Abhängigkeit, Compose-Projekte mit `down -v` entfernt.

## Vorgaben und Hinweise

- Compose-Projekt `twox-155`, `TWOX_API_PORT=18155`. `docker` liegt nicht im PATH: `%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin`.
- Testabschnitte selbst geschrieben, keine echten Anlagen erfinden (Leitplanke 9).
- Nicht pushen.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine (E-76).

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Akzeptanzkriterien erfüllt. Frage 6 bleibt in „2x“ mit dem jetzigen Kontext falsch (siehe unten); mit beiden Gruppen allein ist sie jetzt 6/6 richtig.

### Was wurde gebaut?

- Regel 4 in `SYSTEM_TEMPLATE` (`backend/twox/answers/prompt.py`) bekommt am Ende den Satz aus Variante C2 (Bericht 152), wörtlich: „Nennen zwei Abschnitte für dasselbe Bauteil verschiedene Typen, ist das ein Widerspruch, auch wenn beide aus demselben Dokument stammen.“ Die Schärfung aus 148 bleibt unverändert davor. Feste Phrase, Zitatprüfung, `types.py` und die übrigen Regeln sind unverändert.
- `prompt_version()` jetzt `50193e143663` (vorher `4dc455ce4239`).
- Modul-Docstring und `docs/ARCHITECTURE.md` (Beschreibung des Systemprompts, nur Regel 4): je ein Satz.
- Tests: Snapshot `tests/answers/snapshots/prompt_system.txt` nachgezogen; neuer Test `test_rule_4_counts_different_type_designations_for_one_component_as_contradiction` (Kernaussagen des Zusatzes, Zusatz steht hinter der Schärfung aus 148, feste Phrase weiter aus `types`). Der Test aus 148 bleibt unverändert grün.
- CI-Aufzeichnung `backend/tests/answers/recorded/ci_questions.json` neu mit `gemma4:31b-it-qat` (Digest `e0812a55…`, unverändert, wie in DECISIONS), `/api/ps` unmittelbar vorher leer (`{"models":[]}`). Geändert sind nur `prompt_version`, `recorded_on` und die vier Schlüssel; die Modellausgaben (`chunks`) sind wortgleich. 18 Prüfungen bestanden, 5 nur für die Wiedergabe übersprungen.

Ein erster, längerer Wortlaut („für dasselbe Bauteil desselben Geräts verschiedene Typ- oder Bestellangaben“, Commit `94d184c`) war schlechter: Frage 6 mit nur den beiden Gruppenabschnitten (`idealmin`) 1/6 Widerspruch statt 6/6 mit C2 wörtlich. Er ist durch C2 ersetzt (Commit `f1fc07f`). Die lokalen Fälle bestand er ebenfalls.

### Wie wurde getestet?

**Lokale Fälle** (Compose-Projekt `twox-155`, gemma4:31b-it-qat, Einbettung bge-m3, Startwerte aus `.env.example`, je 3 Läufe über `service.answer` mit `--device`-Bereich wie `manage.py ask`, ohne Seed). Testabschnitte selbst geschrieben mit neutralen Platzhaltern (Gerät A, Einstellung X, Typ ST-100 …), per `manage.py shell` mit Einbettung und Teilstück angelegt; nichts davon im Repository. „vorher“ = Prompt von `main` (Regel 4 ohne Zusatz, im Speicher ersetzt), „nachher“ = neuer Prompt. `/api/ps` vor jedem Fall protokolliert.

| Fall | Abschnitte | Frage | vorher (`main`) | nachher |
| --- | --- | --- | --- | --- |
| (a) echter Widerspruch | ein Dokument: X = 40 und Sollwert X = 60, Normalbetrieb Gerät A | Wert von X? | `contradiction` 3/3 | `contradiction` 3/3 ([1], [2]) |
| (b) Ablauf + Warnhinweis | Filterwechsel Gerät B + Sicherheitshinweis | Wie wechsle ich den Filter? | `answered` 3/3 | `answered` 3/3 |
| (b2) Ablauf + Warnhinweis (Befund B5) | Filterwechsel B2 + „Hauptschalter trennt nicht alle Stromkreise“ | wie (b) | `answered` 3/3 | `answered` 3/3 |
| (c) zwei Geräte | C1: Y = 12, C2: Y = 18 | Y bei C1? | `answered` 3/3 (12) | `answered` 3/3 (12) |
| (c2) zwei Versionen | Version 1: Y = 12, Version 2: Y = 18 | Y in Version 2? | `answered` 3/3 (18) | `answered` 3/3 (18) |
| (d) Kontrolle | Gerät B | Schutzart von Gerät B? | Absage 3/3 | Absage 3/3 |
| (e) neu: dasselbe Bauteil, zwei Typen | ein Dokument: Steuereinheit von Gerät A „Typ ST-100“ (Projektierung) und „Typ ST-250“ (Technische Daten) | Typ der Steuereinheit? | `contradiction` 3/3 | `contradiction` 3/3 ([1], [2]) |
| (f) neu: zwei Bauteile, zwei Typen | Steuereinheit ST-100, Netzteil NT-250 | Typen von Steuereinheit und Netzteil? | `answered` 3/3 | `answered` 3/3 |
| zusätzlich (f2) zwei Bauteile gleicher Art | Hauptsteuerung ST-100, Zusatzsteuerung ST-250 | Welche Steuereinheiten? | `answered` 3/3 | `answered` 3/3 |
| zusätzlich (f3) Typ + Bestellnummer | Steuereinheit ST-100; Ersatzteil ST-100 mit Bestellnummer | Steuereinheit und Bestellnummer? | `answered` 3/3 | `answered` 3/3 |
| zusätzlich (e2) wie Frage 6 | Typ beiläufig in einer Programmieraufgabe, ohne Leerzeichen angehängt („SteuereinheitST100X“); Komponentenliste „ST-250“ | Welche Steuereinheit? | Absage 3/3 | Absage 3/3 |

Kriterium 2 erfüllt: (a), (e) 3/3 `contradiction`; (b), (b2), (c), (c2), (f) 3/3 `answered`; (d) 3/3 Absage. Der einfache Fall (e) besteht schon der Prompt von `main`; der Zusatz wirkt erst bei schwierigeren Abschnitten wie in Frage 6 (unten). (e2) scheitert mit beiden Prompts: Die Zitatprüfung entfernt je Lauf einen Satz (`removed_sentences` = 1), danach bleibt die Absage. Ursache vermutlich die selbst gebaute Schreibweise „ST100X“; nicht weiter untersucht (Zitatprüfung ist Nicht-Ziel).

**Prüfung in „2x“** (nur lesend, kein Neubau, Container `api` des Hauptordners, `manage.py shell` über stdin). Hilfsskript abgeleitet aus `Claude outputs/152/scripts/diag152.py`: Kontext je Frage und Wortlaut mit `select_context` von `main` (Prüfsummen `context.py`, `prompt.py`, `evaluation.py`, `search/postgres.py`, `service.py` im Container = `main`). Nur `citations.py` war im Container älter (vor 154); das Skript lädt die Fassung von `main` nur im Speicher. Prompt im Speicher ersetzt, Kennung je Seed und Frage fest, Seeds 151–153, Bewertung mit `judge_run`. Zusätzlich für Frage 6 `idealmin` (nur die beiden Gruppenabschnitte, wie 152). Hilfsdateien in `/tmp` des Containers danach gelöscht.

Frage 6, jetziger Kontext (`base`):

| Wortlaut | Seed | vorher (`main`) | nachher |
| --- | --- | --- | --- |
| `yaml` | 151 | Absage | `answered`, nur Gruppe B |
| `yaml` | 152 | Absage | `answered`, nur Gruppe B |
| `yaml` | 153 | Absage | `answered`, nur Gruppe B |
| `probe` | 151 | `answered`, nur Gruppe B (+ fremde Quellen 1, 8) | `contradiction`, Gruppe A gegen fremde Quellen 1, 8 (andere CPU) |
| `probe` | 152 | ebenso | ebenso |
| `probe` | 153 | ebenso | ebenso |

Urteil in allen 12 Läufen „falsch“ (vorher und nachher). Mit `yaml` steht Gruppe A nicht im Kontext (Befund 152, Suche); mit `probe` stehen beide Gruppen im Kontext, das Modell stellt aber Gruppe A einer fremden Quelle gegenüber statt Gruppe B. Ein Wiederholungslauf mit demselben Prompt ergab bei `yaml`, Seed 151, einmal die Absage statt `answered` (Streuung wie in 151/152).

Frage 6, nur die beiden Gruppenabschnitte (`idealmin`, zusätzlich):
- vorher: `yaml` 3/3 `answered` mit A und B; `probe` 3/3 `answered` nur mit A.
- nachher: **6/6 `contradiction` mit beiden Gruppen, Urteil „richtig“** (mit der Schreibweisen-Regel aus 154); im Wiederholungslauf ebenso 6/6.
- erster, längerer Wortlaut: 1/6.

Kontrollfrage 11: vorher und nachher je 3/3 Absage in beiden Wortlauten (auch mit dem ersten Wortlaut).

**CI wie `ci.yml`** (Compose-Projekte `twox-155` und `twox-155-tf`):
- backend: `ruff check` „All checks passed!“, `ruff format --check` ohne Befund, `mypy` „Success: no issues found in 238 source files“; `pytest` (Ergebnis unten), `pytest -m worker` mit laufendem `worker`: 6 bestanden; `makemessages` ohne Unterschied, `makemigrations --check` „No changes detected“, Lizenzprüfung bestanden, OpenAPI-Schema unverändert.
- web: `npm ci`, `lint`, `typecheck`, `test`, `build`, `licenses`, `api:generate` jeweils Exit-Code 0, `web/` ohne Unterschied.
- testfactory: ruff, format, mypy, `unittest` (OK, 1 übersprungen wie in CI), Manifest-Prüfungen beider Manifeste OK, kein `testfactory/extern`.
- e2e: Playwright 97 bestanden, Exit-Code 0.
- `pytest`: 3631 bestanden, 1 übersprungen (lokaler Teil der M3-Abnahme, wie in CI), 6 abgewählt (`worker`), 0 fehlgeschlagen.

### Zweig und Arbeitsverzeichnis

- Zweig `worktree-agent-ac9afb036f661af4a`, Arbeitsverzeichnis `.claude/worktrees/agent-ac9afb036f661af4a`, Basis `main` `e6a089a`. Nicht gepusht, nichts zusammengeführt.
- Compose-Projekte `twox-155` und `twox-155-tf` mit `down -v` entfernt.

### Abweichungen

1. Wortlaut: Der Auftrag nennt „Typ- oder Bestellangaben … desselben Geräts“. Dieser Wortlaut war in „2x“ messbar schlechter (1/6 statt 6/6 bei `idealmin`). Übernommen ist deshalb C2 wörtlich. Bestellangaben und „desselben Geräts“ stehen nicht im Text; (c) und (f)–(f3) zeigen, dass andere Geräte, andere Bauteile und Typ plus Bestellnummer trotzdem nicht als Widerspruch gelten.
2. Zusätzliche lokale Fälle (f2), (f3), (e2) als Gegenproben (siehe Tabelle).
3. Lokale Läufe über `service.answer` im Container statt über die Kommandozeile `manage.py ask` (gleicher Weg, ohne Prozessstart je Lauf). Die Testabschnitte bekamen je ein Teilstück (seit 150 sucht die Vektorsuche über Teilstücke).
4. In „2x“ lief die Zitatprüfung von `main` (154) nur im Speicher, weil der Container noch die Fassung davor hat (kein Neubau erlaubt).
5. Befund für a7 (keine Änderung): Mit dem neuen Satz meldet das Modell bei Frage 6 `probe` einen Widerspruch zwischen Gruppe A und fremden Quellen (andere CPU-Angabe). Das war in 152 bei C2 schon so beobachtet. Ob die fremden Quellen dasselbe Bauteil betreffen, ist nicht geprüft. Frage 6 wird erst richtig, wenn die Kontextauswahl Gruppe A und B gemeinsam bringt und Fremdquellen mit anderen CPU-Angaben nicht dazwischenstehen (Optionen (a)/(d) aus 152).
