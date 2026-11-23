# Auftrag 148 – Prompt: Widerspruch nur bei unvereinbaren Angaben

Meilenstein: M3 · Freigabestufe: B (Richtung entschieden in E-74) · Status: fertig, zur Prüfung

## Ziel

Messlauf 144, Befund B5: Das Modell meldet fälschlich einen Widerspruch.
- Prüffrage 10 (`yaml`): in 3 von 3 Läufen Status `contradiction` zwischen der Belegstelle (S. 84) und einem Warnhinweis; die Antwort nennt den Ablauf nicht.
- Prüffrage 6 (`yaml`): `contradiction` zwischen zwei Quellen ohne Bezug zur Belegstelle.

Regel 4 des Systemprompts (`backend/twox/answers/prompt.py:69-70`) lautet heute: „Widersprechen sich Abschnitte in der gefragten Sache, beginne die Antwort genau mit „{contradiction}:“ …“. Ergänzende Angaben, Warnhinweise oder Angaben zu verschiedenen Geräten oder Versionen werden als Widerspruch gelesen.

Nach diesem Auftrag meldet das Modell einen Widerspruch nur, wenn zwei Abschnitte zum selben Gegenstand unvereinbare Angaben machen (z. B. zwei verschiedene Werte für dieselbe Einstellung desselben Geräts); sonst beantwortet es die Frage mit Belegen.

## Umfang

1. **Regel 4 schärfen** in `SYSTEM_TEMPLATE` (`prompt.py`). Vorschlag (der Bearbeiter darf den Wortlaut verbessern, Sinn bleibt):
   - Ein Widerspruch liegt nur vor, wenn zwei Abschnitte zum selben Gegenstand (dasselbe Gerät, dieselbe Version, dieselbe Einstellung oder derselbe Schritt) Angaben machen, die nicht beide zutreffen können.
   - Ergänzungen, Warnhinweise, Voraussetzungen und Angaben zu anderen Geräten oder Versionen sind kein Widerspruch; nutze sie für die Antwort.
   - Bei echtem Widerspruch bleibt das Verhalten wie heute (Antwort beginnt genau mit der festen Phrase, beide Stellen mit Nummern).
   - Die feste Phrase (`CONTRADICTION_PHRASE`, `types.py`) und die Zitatprüfung bleiben unverändert.
2. **`prompt_version()`** ändert sich dadurch. Die CI-Aufzeichnungen (`backend/tests/answers/recorded/ci_questions.json`) werden neu aufgenommen nach `backend/tests/answers/recorded/README.md` („Recording again“) mit `gemma4:31b-it-qat` (vorher `/api/ps` am Host leer, Ollama nicht stoppen). Scheitert eine Frage an einer Prüfung des CI-Tests: nichts aufweichen, Befund in den Kurzbericht, Status „wartet auf a7“.
3. **Prüfung am echten Modell (lokal, Kurzbericht):** Mit selbst geschriebenen Testabschnitten (keine Handbuchtexte) je 3 Läufe `manage.py ask … --json` im eigenen Compose-Projekt:
   - (a) echter Widerspruch (zwei Werte für dieselbe Einstellung desselben Geräts) → Status `contradiction`;
   - (b) Belegstelle plus Warnhinweis zum selben Ablauf → `answered` mit Ablauf;
   - (c) zwei Geräte mit verschiedenen Werten, Frage nach einem → `answered`, kein Widerspruch;
   - (d) Kontrolle: Frage ohne Beleg → feste Absage.
   Ergebnis je Fall vorher (Prompt von `main`) und nachher.
4. **Tests:** bestehende Prompt-Tests anpassen, soweit sie den Wortlaut von Regel 4 prüfen; ein Test, dass Regel 4 die neuen Kernaussagen enthält und die feste Phrase weiter einsetzt.
5. **Doku:** `docs/ARCHITECTURE.md`, falls dort Regel 4 beschrieben ist.

## Nicht-Ziele

- Keine Änderung an Zitatprüfung, Kontextauswahl, Suche, Startwerten oder `types.py`.
- Keine Messung in der Testumgebung „2x“ (macht Messlauf 3).
- Keine neue Abhängigkeit.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/answers/prompt.py` (nur `SYSTEM_TEMPLATE`, Regel 4, und Docstring)
- `backend/tests/answers/` (Prompt-Tests), `backend/tests/answers/recorded/ci_questions.json`
- ggf. `docs/ARCHITECTURE.md` (nur die Stelle zu Regel 4)
- diese Auftragsdatei

## Akzeptanzkriterien (prüfbar)

1. Regel 4 ist geschärft wie in Umfang 1; `CONTRADICTION_PHRASE` und die Zitatprüfung sind unverändert.
2. Lokale Prüfung (Umfang 3): (a) `contradiction` in mindestens 2 von 3 Läufen, (b) und (c) `answered` in 3 von 3, (d) Absage in 3 von 3 – jeweils mit gemma4; Ergebnis vorher/nachher im Bericht. Wird ein Kriterium nicht erreicht: Wortlaut nachbessern; bleibt es verfehlt, Befund und Status „wartet auf a7“.
3. CI wie `ci.yml` grün (backend inkl. `pytest -m worker` mit laufendem `worker`, web, testfactory, e2e); CI-Aufzeichnungen neu mit gemma4, Kopfdaten wie in README, nur Modellausgabe.
4. Diff nur in den genannten Bereichen, keine neue Abhängigkeit; Compose-Projekte mit `down -v` entfernt.

## Vorgaben und Hinweise

- Compose-Projekt `twox-148`, `TWOX_API_PORT=18148` in der ignorierten `.env` des Arbeitsverzeichnisses. `docker` liegt nicht im PATH: `%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin`.
- Die Testabschnitte für Umfang 3 sind selbst geschrieben und erfinden keine echten Anlagen (Leitplanke 9: neutrale Platzhalter wie „Gerät A“, „Einstellung X“).
- Prompt bleibt deutsch und knapp; Injektionsschutz (Regel 5) unverändert.
- Nicht pushen.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine. Richtung entschieden in E-74.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Was wurde gebaut?**

- Regel 4 in `SYSTEM_TEMPLATE` (`backend/twox/answers/prompt.py`) neu: „Ein Widerspruch liegt nur vor, wenn zwei Abschnitte zum selben Gegenstand (dasselbe Gerät, dieselbe Version, dieselbe Einstellung oder derselbe Schritt) Angaben machen, die nicht beide zutreffen können. Nur dann beginne die Antwort genau mit „{contradiction}:“ und nenne beide Stellen mit ihren Nummern. Ergänzungen, Warnhinweise, Voraussetzungen und Angaben zu anderen Geräten oder Versionen sind kein Widerspruch; nutze sie für die Antwort.“ Dazu ein Absatz im Modul-Docstring. `CONTRADICTION_PHRASE` (`types.py`) und Zitatprüfung unverändert.
- `prompt_version()` jetzt `4dc455ce4239` (vorher `64267b8d166e`).
- Tests: Snapshot `tests/answers/snapshots/prompt_system.txt` nachgezogen; neuer Test `test_rule_4_reports_a_contradiction_only_for_incompatible_statements` (Kernaussagen von Regel 4, feste Phrase weiter über `types.CONTRADICTION_PHRASE`). Die übrigen Prompt-Tests prüften den alten Wortlaut nicht und blieben unverändert.
- CI-Aufzeichnung `backend/tests/answers/recorded/ci_questions.json` neu mit `gemma4:31b-it-qat` (Digest `e0812a55…`, unverändert), `/api/ps` vorher leer. Geändert haben sich nur `prompt_version` und die Schlüssel; die Modellausgaben (`chunks`) sind wortgleich. Alle Prüfungen des CI-Tests bestanden (18 bestanden, 5 nur für Wiedergabe übersprungen).
- `docs/ARCHITECTURE.md`: Beschreibung des Systemprompts (Regel 4) angepasst.

**Wie wurde getestet?**

Lokale Prüfung am echten Modell (Umfang 3), Compose-Projekt `twox-148`, `gemma4:31b-it-qat`, Einbettung `bge-m3`, Startwerte aus `.env.example` (u. a. `TWOX_ANSWER_MAX_DISTANCE` 0,55), je 3 Läufe `manage.py ask … --device <id> --json` ohne `--seed`. Testabschnitte selbst geschrieben (neutrale Platzhalter „Gerät A“, „Einstellung X“ …), per `manage.py shell` als Abschnitte mit `bge-m3`-Einbettung angelegt; nichts davon im Repository. Vor jeder Lauf-Serie und vor der Aufnahme `/api/ps` geprüft.

| Fall | Abschnitte | Frage | vorher (`main`) | nachher |
| --- | --- | --- | --- | --- |
| (a) echter Widerspruch | ein Dokument, „Einstellung X auf 40“ und „Sollwerte: Einstellung X = 60“, beides Normalbetrieb Gerät A | Wert von X bei Gerät A? | `contradiction` 3/3 | `contradiction` 3/3 (beide Stellen [1], [2]) |
| (b) Ablauf + Warnhinweis (Lüfter-Nachlauf, Handschuhe) | Filterwechsel Gerät B + Sicherheitshinweis | Wie wechsle ich den Filter? | `answered` 3/3 | `answered` 3/3, Ablauf mit Warnung |
| (b2) Ablauf + Warnhinweis „Hauptschalter trennt nicht alle Stromkreise, Netzstecker ziehen“ (bildet Befund B5 nach) | Filterwechsel Gerät B2 + allgemeiner Warnhinweis | Wie wechsle ich den Filter? | **`contradiction` 3/3** (Ablauf vs. Warnhinweis) | `answered` 3/3, Ablauf mit Netzstecker-Schritt [2] |
| (c) zwei Geräte, verschiedene Werte | Baureihe C: C1 Y = 12, C2 Y = 18 | Wert von Y bei C1? | `answered` 3/3 (12) | `answered` 3/3 (12) |
| (c2) zwei Versionen, verschiedene Werte | Gerät C Version 1: Y = 12, Version 2: Y = 18 | Wert von Y in Version 2? | `answered` 3/3 (18) | `answered` 3/3 (18) |
| (d) Kontrolle ohne Beleg | Gerät B (2 Abschnitte im Kontext, Modell gefragt) | Schutzart von Gerät B? | Absage 3/3 (ein erster Lauf brach mit `model_unavailable` ab: Einbettung beim Kaltstart nicht erreichbar; wiederholt) | Absage 3/3 |

Akzeptanzkriterium 2 erfüllt: (a) 3/3, (b) und (c) 3/3 `answered`, (d) 3/3 Absage. Der Prompt von `main` scheitert an (b2) in 3 von 3 Läufen, der neue besteht ihn in 3 von 3.

CI wie `ci.yml`, Compose-Projekt `twox-148` (Web, Testfabrik als `twox-148-tf`):
- backend: `ruff check` „All checks passed!“, `ruff format --check` ohne Befund, `mypy` „Success: no issues found in 229 source files“, `pytest` und `pytest -m worker` (Ergebnis siehe unten), `makemessages` ohne Unterschied, `makemigrations --check` „No changes detected“, Lizenzprüfung bestanden, OpenAPI-Schema unverändert;
- web: `npm ci`, `lint`, `typecheck`, `test`, `build`, `licenses`, `api:generate` jeweils Exit-Code 0, `web/` ohne Unterschied;
- testfactory: ruff, format, mypy, `unittest` (OK, 1 übersprungen wie in CI), Manifest-Prüfungen beider Manifeste OK, kein `testfactory/extern`;
- e2e: Playwright 83 bestanden, 1 übersprungen, Exit-Code 0.

`pytest`: 3521 bestanden, 6 abgewählt (`worker`), 0 fehlgeschlagen, 0 übersprungen; `pytest -m worker` mit laufendem `worker`: 6 bestanden.

**Zweig und Arbeitsverzeichnis**

Zweig `worktree-agent-ab5a2e3ed3ce7963b`, Arbeitsverzeichnis `.claude/worktrees/agent-ab5a2e3ed3ce7963b`, Basis `main` 9809570. Nicht gepusht. Compose-Projekte `twox-148` und `twox-148-tf` mit `down -v` entfernt.

**Abweichungen**

- Keine im Code. Zusätzlich zu (a)–(d) die Varianten (b2) und (c2), weil (b) und (c) schon mit dem alten Prompt bestanden und den Befund B5 nicht nachbildeten.
- Befund außerhalb des Auftrags (keine Änderung): Ein erster Versuch für (a) mit dem Widerspruch in **zwei Dokumenten desselben Geräts** (Betriebsanleitung „X = 40“, Kurzanleitung „X = 60“, ähnlich formuliert) brachte nur einen Abschnitt in den Kontext; die Antwort nannte 40 ohne Widerspruch (3/3, alter Prompt). Ursache vermutlich die Sprachfassungs-Regel der Kontextauswahl (E-61, `TWOX_ANSWER_TRANSLATION_DISTANCE` 0,15, `context.py` Schritt 6): ein sehr ähnlicher Abschnitt aus einem anderen Dokument desselben Geräts gilt als Übersetzung und fällt weg. Ein echter Widerspruch zwischen zwei Dokumenten eines Geräts kann so unsichtbar werden. Für (a) wurde deshalb ein Dokument mit zwei Abschnitten verwendet. Vorschlag an a7: im Messlauf 3 oder einem eigenen Auftrag prüfen.
