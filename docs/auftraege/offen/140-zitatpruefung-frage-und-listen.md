# Auftrag 140 – Zitatprüfung: Werte aus der Frage und Listenpunkte

Meilenstein: M3 · Freigabestufe: B · Status: zur Prüfung

Voraussetzung: 123 (`citations.verify`), 126 (Antwortdienst) und 127 (`evaluate_answers`) sind auf `main`. Folgeauftrag zu den Befunden B2 und B3 des Messlaufs 128 (`docs/auftraege/erledigt/128-messlauf-chat-modell.md`, Kurzbericht, Tabelle „Frage × Modell“ und Abschnitt Befunde) und zu E-70 (`docs/DECISIONS.md:80`, „Zitatprüfung (Werte aus der Frage, Listenpunkte)“).

## Ziel

Die Zitatprüfung verwirft keine belegten Antworten mehr aus zwei formalen Gründen, die der Messlauf 128 gezeigt hat:

- **Frage 9 (B2):** „Welche Nutzlast hat der UR5e?“ (`testfactory/questions.yaml:278`). Das Modell nennt die Typbezeichnung aus der Frage im Antwortsatz und zitiert gültig die Belegstelle (Rang 1). Die Typbezeichnung steht aber nicht im zitierten Abschnitt. Der Satz wird als `unsupported_value` verworfen, und die Antwort wird zur Absage (beide Modelle 0/3).
- **Frage 8 (B3, qwen):** Die Antwort ist eine Liste unter einem Einleitungssatz mit Quellennummer. Die Listenpunkte ohne eigene Nummer gelten als `no_citation` und werden verworfen; übrig bleibt nur der Einleitungssatz (0/3, 7 Sätze verworfen). Dasselbe zeigte die Injection-Probe.

Die Prüfung bleibt dabei ein Schutz gegen erfundene Werte. Eine falsche Prämisse in der Frage (z. B. eine falsche Zahl) darf sich nicht selbst bestätigen.

## Umfang

**Ist-Stand (geprüft am Code):**
- `verify(answer_text, sources, *, drop_unsupported)` kennt die Frage nicht (`backend/twox/answers/citations.py:666-671`).
- Prüfwerte entstehen in `_check_values` (`citations.py:498-565`). Typbezeichnungen sind Werte der Art `IdentifierKind.GENERIC` (`backend/twox/search/identifiers.py:54-60`, `_is_generic` Z. 117-122: Buchstaben/Ziffern mit `-_./`, mindestens eine Ziffer und ein anderes Zeichen). Sie werden in `citations.py:541-564` hinzugefügt, ohne dass `_Value` (`citations.py:310-318`) ihre Art kennt. Bereits vorhandene Schlüssel werden nicht überschrieben (`add`, Z. 504-507): Zahlen mit Einheit, Ports und Versionen kommen vor den Tokens und behalten ihre Kennzeichen.
- Jeder Listenpunkt ist ein eigener Satz (`_LIST_MARKER` Z. 208, `_split_sentences` Z. 437-464). `_Sentence` (Z. 300-307) merkt sich nicht, ob ein Satz in einer Listenzeile steht.
- Ein Satz ohne Nummer wird sofort `no_citation` (Z. 701-709).
- Der Dienst ruft `verify` ohne Frage auf (`backend/twox/answers/service.py:290-294`); `question` ist dort im Gültigkeitsbereich (Z. 221, genutzt Z. 241).
- `evaluate_answers` ruft `verify` nicht selbst auf, sondern den Dienst (`backend/twox/answers/evaluation.py:844`, `answer(text, device_ids=(), plant_ids=())`). Es braucht deshalb **keine Änderung** in `evaluation.py`.

**Zu bauen:**

1. **Werte aus der Frage.**
   - `verify` bekommt den optionalen, nur benannten Parameter `question: str | None = None`. Ohne Frage (`None` oder leer) verhält sich `verify` genau wie bisher; alle bestehenden Tests bleiben unverändert grün.
   - Die Prüfwerte der Frage werden **einmal je Aufruf** mit denselben Regeln wie bei Antwortsätzen ermittelt (`_check_values`, gleiche Vereinheitlichung über `_compact`).
   - Freigestellt werden können nur **Typbezeichnungen und Kennungen**: Werte der Art `GENERIC` (auch zusammengesetzte wie `S7 1500`), die mindestens einen Buchstaben und eine Ziffer enthalten. `_Value` bekommt dafür ein Kennzeichen (z. B. `designation: bool`), das nur im GENERIC-Zweig gesetzt wird.
   - **Zusatzbedingung (eng gefasst):** Eine solche Bezeichnung aus der Frage gilt nur dann als belegt, wenn derselbe Satz **mindestens einen weiteren geprüften Wert** trägt, der nicht freigestellt ist und in einer seiner gültig zitierten Quellen steht (Frage 9: „5 kg“). Ein Satz, dessen einziger Prüfwert die Bezeichnung aus der Frage ist, bleibt `unsupported_value`, wenn die Quelle sie nicht enthält. Grund: Unter `GENERIC` fallen auch Fehlercodes (`E1234`), Betriebsmittelkennzeichen (`PLC-01`), Schutzarten (`IP67`) und Teilenummern; eine falsche Prämisse wie „Was bedeutet Fehler E1234?“ mit einer Quelle zu `E1235` darf den Satz „E1234 bedeutet … [1]“ nicht belegen (Leitplanke 3).
   - **Nicht** aus der Frage belegt sind:
     - Zahlen mit Einheit (`10 kg`, `24 V`), auch als ein Token geschrieben (`10kg`, `24VDC`, `230VAC`);
     - IPv4-, IPv6- und MAC-Adressen;
     - Ports;
     - Versionen (`V18`, `Firmware 5.12`, auch `5.12` ohne Wort, wenn es in der Frage als Version erkannt wurde);
     - reine Zahlen mit Punkt ohne Buchstaben (`1.5`).
     Ein solcher Wert muss im Antwortsatz weiterhin in einer gültig zitierten Quelle stehen. Sonst würde eine falsche Prämisse sich selbst bestätigen.
   - Ein Wert des Antwortsatzes, dessen Schlüssel einem freigestellten Schlüssel der Frage gleicht, zählt nicht als fehlend. Der Satz braucht trotzdem eine gültige Quellennummer; ohne Nummer bleibt er `no_citation`. Alle übrigen Werte des Satzes werden wie bisher geprüft.
   - Der Vergleich nutzt nur Schlüssel und `str`-Vergleiche. Aus der Frage wird kein regulärer Ausdruck gebaut (Leitplanke 4, `citations.py:8-9`).
2. **Listenpunkte erben die Nummern ihres Einleitungssatzes.**
   - `_Sentence` merkt sich, ob der Satz in einer Listenzeile steht (Zeile mit `_LIST_MARKER`: `-`, `*`, `•`, `1.`, `1)`).
   - **Einleitungssatz** ist der letzte Satz der letzten Nicht-Listenzeile mit Inhalt vor einem Listenblock. Er muss mit `:` enden; Quellennummern dürfen vor oder nach dem Doppelpunkt stehen: `Die Station nutzt folgende Topics [1]:` und `Die Station nutzt folgende Topics: [1]`. Außerdem muss er mindestens eine gültige Nummer tragen und selbst belegt sein, also nicht verworfen.
   - Der **Listenblock** reicht über aufeinanderfolgende Listenzeilen; Leerzeilen dazwischen beenden ihn nicht, auch eingerückte (verschachtelte) Punkte gehören dazu. Eine Nicht-Listenzeile mit Inhalt beendet ihn.
   - Ein Satz in einem Listenblock **ohne eigene Nummer** erbt die gültigen Nummern des Einleitungssatzes. Seine Prüfwerte werden gegen diese Quellen geprüft. Gibt es keinen Einleitungssatz nach dieser Regel, bleibt er `no_citation`.
   - Ein Listenpunkt **mit eigener Nummer** wird nur gegen seine eigenen Nummern geprüft; es wird nichts gemischt. Trägt er nur ungültige Nummern, bleibt er `unknown_citation`.
   - Ein verworfener Einleitungssatz vererbt nichts. Seine Listenpunkte ohne Nummer bleiben dann `no_citation`.
   - Geerbte Nummern zählen für `cited` und für die Statusregel (`contradiction` braucht zwei verschiedene gültige Nummern, Z. 759) wie eigene. Weil es dieselben Nummern wie die des Einleitungssatzes sind, ändert sich dadurch nichts.
3. **Dienst.** `service.py` übergibt die Frage an `verify` (`question=question`), nur im Aufruf Z. 290-294. Der Modul-Docstring, Schritt 8 (`service.py:31-34`), nennt die Übergabe.
4. **Doku im Code.** Der Modul-Docstring von `citations.py` wird nachgezogen:
   - Abschnitt „Sentences“: Listenblock und Einleitungssatz;
   - Abschnitt „Sentence verdict“: geerbte Nummern;
   - ein kurzer Absatz zu den Werten aus der Frage (welche Arten freigestellt sind, welche nicht, und warum);
   - Abschnitt „Limits“ (Z. 129-142), neue Punkte:
     - Ein Wert aus der Frage gilt ungeprüft, wenn er eine Typbezeichnung ist und der Satz einen weiteren belegten Wert trägt. Ob die Quelle von diesem Gerät handelt, prüft `verify` nicht. Das gilt auch für Fehlercodes und Kennzeichen: „E1234 tritt ab 80 °C auf [1]“ gilt als belegt, wenn die Quelle „80 °C“ nur zu `E1235` nennt.
     - Ein Listenpunkt ist nur so gut belegt wie die Quellen des Einleitungssatzes.
   Der Docstring von `verify` nennt den neuen Parameter.
5. **Linear bleiben.** Die Frage wird einmal zerlegt, die Vererbung läuft in einem Durchgang über die Sätze. Keine verschachtelten Quantoren, keine neuen Muster aus Eingabetext.

## Nicht-Ziele

- Keine Änderung am Prompt (`prompt.py`), an der Kontextauswahl (`context.py`), an Einstellungen (`settings.py`, `.env.example`), an der Bewertung (`evaluation.py`), an `identifiers.py`, `types.py` oder `testfactory/questions.yaml`.
- Keine neuen Einheiten, Abkürzungen oder Satzende-Regeln. Keine Änderung an der Grenzprüfung (`_bounded`, `_occurs`) und an `value_occurs`.
- Keine Prüfung von Wörtern, Bedeutung oder Bezug eines Werts. Die Grenzen unter „Limits“ bleiben.
- Kein Neuaufzeichnen der CI-Antworten (`backend/tests/answers/recorded/`, `manage.py record_answers`); das braucht das Modell am Host.
- Kein Messlauf auf der Testumgebung „2x“ (siehe Vorgaben).

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/answers/citations.py`: `verify`, `_Value`, `_Sentence`, `_check_values`, `_split_sentences`, Modul-Docstring
- `backend/twox/answers/service.py`: nur der Aufruf von `citations.verify` (Z. 290-294) und Schritt 8 im Modul-Docstring (Z. 31-34)
- `backend/tests/answers/test_citations.py`: neue Tests
- `backend/tests/answers/test_service_question.py` (**neue Datei**): der Test, dass die Frage ankommt. `backend/tests/answers/test_service.py` wird **nicht** geändert; die Hilfen `use_context`, `StandInContext` und `source` (`test_service.py:96-146`) werden von dort importiert (Muster: `test_service.py:27-33` importiert aus `tests.search.test_keyword_search`). Fixtures aus `test_service.py` (z. B. `ai_on`, Z. 204) nicht importieren, sondern bei Bedarf in der neuen Datei nachbilden.
- `docs/ARCHITECTURE.md`: nur im Absatz „Answer service“ (Z. 167) der Aufruf `citations.verify(..., question=..., drop_unsupported=True)`

Abgrenzung zu den parallelen Aufträgen:
- 142 ändert ebenfalls `service.py`, aber andere Hunks (Signaturen und Docstring von `answer()`/`_events()`, Schritt 3 des Moduldocstrings, eine Zeile nach der Kontextauswahl). Dieser Auftrag ändert in `service.py` nur den `verify`-Aufruf und Schritt 8; keine Umformatierung. 142 legt seine Diensttests in einer eigenen neuen Datei an; `test_service.py` bleibt für beide unverändert.
- 142 ergänzt die Signatur von `answer()` um `on_context`; den Nachtrag in `docs/ARCHITECTURE.md:167` macht die Leitstelle nach dem Zusammenführen beider Aufträge. Dieser Auftrag ändert in Z. 167 nur den `verify`-Aufruf.
- 139 ändert `context.py`, Einstellungen und ggf. Testaufbau in `test_service.py` und `test_ci_questions.py` sowie andere Zeilen von `docs/ARCHITECTURE.md` (:134, :594, :600, :602); 141 nur `testfactory/`; 143 nur die Suche. Keiner davon ändert `citations.py`, `test_citations.py` oder `test_service_question.py`.
- Umgekehrt berührt dieser Auftrag weder `context.py`, `settings.py`, `.env.example` noch `evaluation.py`, `prompt.py`, `test_service.py`, `test_ci_questions.py`, `testfactory/` und keine anderen Absätze von `docs/ARCHITECTURE.md`. `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle.

## Akzeptanzkriterien (prüfbar)

1. **Signatur:** `verify(answer_text, sources, *, drop_unsupported, question=None)` mit Typangaben. Alle bisherigen Tests in `test_citations.py` bleiben ohne Änderung grün, insbesondere die Laufzeittests `test_verify_grows_linearly_for_unfavourable_input` (`test_citations.py:659`) und `test_space_runs_in_checked_sentences_stay_linear` (Z. 700).
2. **Werte aus der Frage, positiv** (eigene Testtexte, Quelle ohne die Typbezeichnung, z. B. `{1: "Die Nutzlast beträgt 5 kg."}`):
   - Frage `Welche Nutzlast hat der Greifer G-12?` mit Antwort `Der G-12 hat eine Nutzlast von 5 kg [1].` ergibt `answered` mit `cited == (1,)`.
   - Derselbe Fall ohne `question` ergibt `no_evidence` mit `unsupported_value` und `values == ("G-12",)`; das bisherige Verhalten bleibt.
   - Je ein Fall für eine zusammengesetzte Bezeichnung (`S7 1500` in Frage und Antwort) und eine Bezeichnung mit angehängtem Wortteil in der Antwort (`G-12-Greifer`), jeweils mit einem weiteren Wert im Satz, der in der Quelle steht (z. B. `5 kg`).
3. **Werte aus der Frage, negativ** (je ein Test; die Quelle enthält den Wert nicht, der Satz bleibt `unsupported_value`):
   - Frage `Ist die Nutzlast 10 kg?`, Antwort `Die Nutzlast ist 10 kg [1].`;
   - Einheit als ein Token: `24VDC` in Frage und Antwort;
   - IPv4-Adresse, MAC-Adresse, `Port 502`, Version (`Firmware 5.12` und `V18`), `1.5`;
   - eine Typbezeichnung, die nur in der Frage steht, macht einen *anderen* Wert der Antwort nicht belegt (Frage `G-12`, Antwort `G-14 [1]`);
   - Bezeichnung aus der Frage als einziger Prüfwert des Satzes: Frage `Welche Nutzlast hat der Greifer G-12?`, Antwort `Der G-12 ist ein Greifer [1].`, Quelle ohne `G-12` → `unsupported_value`;
   - falsche Prämisse mit Fehlercode: Frage `Was bedeutet Fehler E1234?`, Antwort `E1234 bedeutet Übertemperatur [1].`, Quelle `{1: "Fehler E1235 bedeutet Übertemperatur."}` → `unsupported_value`.
   - Ein Antwortsatz mit dem Wert aus der Frage, aber ohne Nummer, bleibt `no_citation`.
4. **Listenpunkte, positiv:**
   - Einleitung `Die Station nutzt diese Ports [1]:` mit Punkten `- Port 502` und `- Port 1883`, die Quelle enthält beide. Ergebnis: `answered`, keine `removed_sentences`, der Text bleibt unverändert.
   - Dasselbe mit Nummer nach dem Doppelpunkt (`… Ports: [1]`), mit nummerierter Liste (`1.` und `1)`), mit Leerzeile zwischen den Punkten und mit einem eingerückten Unterpunkt.
5. **Listenpunkte, negativ** (je ein Test):
   - Ein Punkt mit einem Wert, der nicht in der Quelle der Einleitung steht, ergibt `unsupported_value` und wird entfernt; die anderen Punkte bleiben.
   - Einleitung ohne `:` → Punkte `no_citation`.
   - Einleitung mit `:`, aber ohne Nummer oder nur mit ungültiger Nummer → Punkte `no_citation`.
   - Verworfene Einleitung (unbelegter Wert) → Punkte `no_citation`.
   - Eine Nicht-Listenzeile mit Inhalt zwischen Einleitung und Liste → keine Vererbung.
   - Ein Punkt mit eigener gültiger Nummer wird nur gegen diese Quelle geprüft (Wert nur in der Quelle der Einleitung → `unsupported_value`).
   - Eine Liste ohne Einleitung (Antwort beginnt mit `- …`) → `no_citation`.
6. **Laufzeit:** Ein neuer Laufzeittest nach dem Muster von `test_citations.py:659-673` (t(20000)/t(5000) < 8, t(20000) < 1 s) für eine lange Liste unter einer Einleitung und für eine lange Frage (20 000 Zeichen) besteht.
7. **Dienst:** Ein Test in der neuen Datei `tests/answers/test_service_question.py` zeigt, dass `answer()` die Frage an `verify` übergibt. Zum Beispiel ersetzt er `citations.verify` mit `monkeypatch` und prüft das Argument `question`, oder er prüft Ende-zu-Ende mit `FakeChatModel` eine Typbezeichnung aus der Frage, die nicht im Abschnitt steht (mit einem weiteren belegten Wert im Satz). `test_service.py` ist unverändert; seine Tests und `tests/answers/test_ci_questions.py` bleiben grün, und zwar gegen die Aufzeichnungen unter `backend/tests/answers/recorded/`, wie sie zum Zeitpunkt der Prüfung auf `main` liegen (nach dem Zusammenführen von 139 die Neuaufnahme mit gemma4), ohne sie zu ändern.
8. **Doku:** Der Modul-Docstring von `citations.py` (Sentences, Sentence verdict, Werte aus der Frage, Limits) und der Docstring von `verify` beschreiben das neue Verhalten. Schritt 8 in `service.py` und `docs/ARCHITECTURE.md:167` nennen die Übergabe der Frage.
9. **CI:** Alle Prüfungen aus `.github/workflows/ci.yml` sind im eigenen Compose-Projekt grün und werden mit Exit-Code im Kurzbericht genannt: `ruff check .`, `ruff format --check .`, `mypy .`, `pytest`, `pytest -m worker`, Übersetzungskatalog (`makemessages` ohne Unterschied unter `backend/locale`), `makemigrations --check --dry-run`, `scripts/check-licenses.sh`, Schema-Prüfung (`spectacular` ohne Unterschied unter `web/openapi`) sowie die Jobs `web`, `testfactory` und `e2e` (unverändert grün; dieser Auftrag berührt ihre Dateien nicht, ein lokaler Lauf der Jobs `web` und `testfactory` genügt, `e2e` laut CI-Lauf oder mit Begründung).
10. `git diff main --stat` zeigt nur Dateien aus „Betroffene Bereiche“. Keine neue Abhängigkeit (`backend/pyproject.toml` und Lock-Datei unverändert).
11. Abräumen: `docker compose -p twox-140 --profile dev down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

- **Leitplanke 3 (Antworten nur mit Quelle):** Jeder belegte Satz trägt weiterhin eine gültige Nummer, eigen oder geerbt. Die Freistellung aus der Frage ersetzt keine Nummer. Sie gilt nur für Typbezeichnungen, die das Modell aus der Frage wiederholt, und nur neben einem weiteren Wert, den die Quelle belegt. Messwerte, Adressen, Ports und Versionen müssen in der Quelle stehen. Darum sind die Tests „Frage `Ist die Nutzlast 10 kg?`, Antwort `10 kg [1]` ohne Beleg bleibt unbelegt“ und „Fehlercode `E1234` nur aus der Frage, Quelle zu `E1235` bleibt unbelegt“ Pflicht.
- **Leitplanke 4 (Dokumentinhalte sind Daten):** Frage, Antwort und Abschnittstexte werden nur verglichen, nie ausgewertet. Kein Muster wird aus diesen Texten gebaut. `verify` protokolliert nichts, auch nicht die Frage, und Ausnahmen enthalten keinen Text.
- **Keine Herstellertexte im Repository:** Testtexte selbst schreiben, mit neutralen Werten wie in 123 (`Greifer G-12`, `24 V`, `10.0.0.7`, `S7 1500`). Keine Sätze aus Handbüchern der Testfabrik, auch nicht aus dem UR5e-Handbuch oder dem APS-Repository.
- **Keine neue Abhängigkeit.**
- **Linearität:** Siehe Kurzbericht 123, Nachbesserung 2: possessive Quantoren, Suche mit `str.find`. Die Prüfwerte der Frage werden einmal ermittelt, nicht je Satz.
- **Kompatibilität:** `question` ist optional und nur benannt. `replay.py`, `api.py` und die Messung rufen `verify` nicht direkt auf (Aufrufer laut `grep`: nur `service.py:290`). Bestehende Aufrufe bleiben gültig.
- **CI-Aufzeichnungen:** Ändert die neue Regel das Urteil einer aufgezeichneten CI-Antwort (`backend/tests/answers/recorded/ci_questions.json`), wird nicht neu aufgezeichnet und kein Test angepasst. Der Bearbeiter beschreibt den Fall im Kurzbericht und setzt den Status „wartet auf a7“.
- **Messungen:** Die Wirkung auf die Prüffragen 8 und 9 misst die Leitstelle nach dem Zusammenführen auf der Testumgebung „2x“ (Wiederholung des Messlaufs nach E-70). Der Bearbeiter startet die Testumgebung „2x“ nicht und ändert sie nicht. Er arbeitet im eigenen Compose-Projekt `twox-140`.
- **Tests im Container** aus dem Verzeichnis `backend` (`tests/answers/...` im Befehl, siehe 123).
- Commits klein auf dem eigenen Zweig, nicht auf `main`. Kein Push (E-14). Keine Personen- oder Produktnamen außer 2x, keine lokalen Pfade mit Benutzernamen.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine. Die Vorgabe der Leitstelle setzt E-70 um; die Freistellung ist eng gefasst (nur Typbezeichnungen, nur neben einem weiteren belegten Wert, Nummer bleibt Pflicht). E-70 legt die Breite der Freistellung nicht fest; die engere Fassung deckt Frage 9 („5 kg“) ab.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- **Was wurde gebaut?**
  - `citations.verify(answer_text, sources, *, drop_unsupported, question=None)`. Die Prüfwerte der Frage werden einmal je Aufruf mit `_check_values` ermittelt. Nur Schlüssel mit `designation=True` zählen.
  - `_Value.designation` wird nur im GENERIC-Zweig gesetzt (`_is_designation`): mindestens ein Buchstabe und eine Ziffer, und kein Ein-Token-Wert aus Zahl und Einheit, auch mit `AC`/`DC` (`10kg`, `24VDC`, `230VAC`; neues festes Muster `_UNIT_TOKEN` aus der Einheitenliste).
  - `_missing_values` stellt einen Bezeichnungswert aus der Frage nur dann frei, wenn derselbe Satz einen weiteren Wert trägt, der nicht aus der Frage stammt und in einer gültig zitierten Quelle steht. Verglichen werden nur Schlüssel (`in` auf `frozenset`). Aus der Frage wird kein Muster gebaut.
  - `_Sentence.in_list`. `_list_intros` geht einmal über die Zeilen und bestimmt den Einleitungssatz eines Listenblocks: letzter Satz der letzten Nicht-Listenzeile mit Inhalt; endet nach Entfernen der Nummern mit `:`. Leerzeilen erhalten den Block, eine andere Zeile mit Inhalt beendet ihn.
  - In `verify` erbt ein Listenpunkt ohne eigene Nummer die gültigen Nummern eines belegten Einleitungssatzes (`supported_numbers`). Sonst bleibt er `no_citation`.
  - Nachgezogen sind:
    - der Modul-Docstring: Sentences, neuer Abschnitt „Values from the question“, Sentence verdict und zwei neue Punkte unter „Limits“;
    - der Docstring von `verify`;
    - in `service.py` der Aufruf mit `question=question` und Schritt 8;
    - `docs/ARCHITECTURE.md:167`, dort nur der `verify`-Aufruf.
- **Wie wurde getestet?** Compose-Projekt `twox-140`, API-Port 18140.
  - Neu in `test_citations.py` (Abschnitte 13–15):
    - positive Fälle: `G-12`, `S7 1500` (auch Frage `S7-1500`), `G-12-Greifer`, `**G-12**`;
    - ohne Frage (`None` und `""`) bleibt `unsupported_value` mit `("G-12",)`;
    - 15 Negativfälle: `10 kg`, `10kg`, `24VDC`, `230VAC`, IPv4, MAC, `Port 502`, `Firmware 5.12`, `5.12` ohne Wort, `V18`, `1.5`, `G-12`→`G-14`, Bezeichnung als einziger Wert, `E1234` gegen `E1235`, zweite Bezeichnung aus der Frage als „Anker“;
    - ohne Nummer bleibt der Satz `no_citation`; keine Freistellung in einem anderen Satz; Regex-Zeichen in der Frage;
    - Listen positiv: Nummer vor oder nach `:`, `1.`, `1)`, Leerzeile, eingerückter Unterpunkt;
    - Listen negativ: unbelegter Punkt wird entfernt, ohne `:`, `:` mit Text danach, ohne Nummer, nur `[9]`, verworfene Einleitung, Zwischenzeile, Liste ohne Einleitung, Listenpunkt als Einleitung, eigene Nummer nur ungültig, eigene gültige Nummer;
    - `contradiction` mit geerbten Nummern, `in_list`-Kennzeichen;
    - Laufzeit: 7 Fälle (lange Liste, lange Frage mit 20 000 Zeichen), Wachstum < 8 und t(20000) < 1 s.
  - Neu `tests/answers/test_service_question.py`: `verify` mit `monkeypatch` ersetzt; das Argument `question` kommt an. Dazu zwei Fälle Ende-zu-Ende mit `FakeChatModel` (positiv und Bezeichnung allein).
  - `test_citations.py` und `test_service_question.py` zusammen: 230 bestanden. Bestehende Tests unverändert.
  - Prüfungen aus `ci.yml`, je mit Exit-Code:
    - `ruff check .` 0, `ruff format --check .` 0, `mypy .` 0 (228 Dateien);
    - `pytest` 0 (3475 bestanden), `pytest -m worker` 0 (6 bestanden);
    - `makemessages` 0 ohne Unterschied, `makemigrations --check --dry-run` 0 („No changes detected“), `check-licenses.sh` 0, `spectacular` 0 ohne Unterschied.
  - Job `web` (`twox-140-web`): `npm ci`, `lint`, `typecheck`, `test`, `build`, `licenses` und `api:generate` je 0, ohne Unterschied.
  - Job `testfactory` (`twox-140-tf`): Build, `ruff`, `format`, `mypy`, `unittest` und vier Manifestprüfungen je 0.
  - `e2e` lokal nicht gelaufen. Begründung: Der Auftrag berührt weder Web noch API-Schema; im Schema gibt es keinen Unterschied.
  - `docker compose -p twox-140 --profile dev down -v` Exit 0, ebenso für `-web` und `-tf`.
- **CI-Aufzeichnungen:** Die vier Antworten in `recorded/ci_questions.json` (Stand dieses Zweigs, qwen) sind Einzelsätze ohne Liste. Keine trägt neben einer Bezeichnung aus der Frage einen weiteren belegten Wert. Ihr Urteil ändert sich nicht, `test_ci_questions.py` ist grün. Gegen die Neuaufnahme aus 139 (gemma4) konnte ich nicht prüfen, sie liegt noch nicht auf `main`.
- **Zweig und Arbeitsverzeichnis:** `worktree-agent-a4eba25db25722898`, `.claude/worktrees/agent-a4eba25db25722898`.
- **Abweichungen und Auslegungen:**
  1. Freigestellt wird nur, wenn auch der Antwortwert eine Bezeichnung ist (`designation`) und nicht nur sein Schlüssel einem Fragewert gleicht. Das ist enger als der Wortlaut des Auftrags.
  2. „Weiterer Wert, der nicht freigestellt ist“: Eine zweite Bezeichnung aus der Frage zählt nicht als weiterer Wert, auch wenn sie in der Quelle steht. `Der G-12 passt zur S7-1200 [1]` mit Quelle nur zu `S7-1200` bleibt `unsupported_value`. Dafür gibt es einen Test.
  3. Eine Einleitung, deren Doppelpunkt nur innerhalb von Markdown steht (`**Ports [1]:**`), endet nicht mit `:`. Ihre Punkte erben nichts; die Regel ist so eng wie vorgegeben.
  4. Als „Zeile mit Inhalt“ gilt jede Zeile, die nach `strip()` nicht leer ist, auch `---`. Eine solche Zeile beendet einen Listenblock.
  5. Keine neue Abhängigkeit, keine offene Frage an a7.

Status: zur Prüfung
