# Auftrag 154 – Werte wie „1512SP“ auch direkt hinter einem Wort erkennen

Meilenstein: M3 · Freigabestufe: B (Teil B von E-76) · Status: erledigt

## Ziel

Diagnose 152: Das key_fact „1512SP“ von Prüffrage 6 wird nie gefunden, weil es in Abschnitt und Antwort direkt an ein Wort angehängt steht (z. B. „CPU“ ohne Leerzeichen). Die Grenzregel in `backend/twox/answers/citations.py` (`_bounded`, `_occurs`, `value_occurs`) lässt eine Fundstelle mit einem Buchstaben direkt davor nicht zu. Folgen: Die Bewertung (`evaluation.py`, `value_occurs`) findet das key_fact nicht, und die Zitatprüfung (`verify`) hat einmal einen belegten Satz mit `unsupported_value` entfernt.

Nach diesem Auftrag gilt ein Wert, der mit einer Ziffer beginnt und einen Buchstaben enthält (eine Typbezeichnung wie „1512SP“, „1500“ nicht), auch dann als vorhanden, wenn direkt davor Buchstaben stehen (Übergang Buchstabe → Ziffer als Grenze). Alle anderen Grenzregeln bleiben.

## Umfang

1. **Grenzregel** in `citations.py` erweitern, eng gefasst:
   - gilt nur für Werte, die mit einer Ziffer beginnen und mindestens einen Buchstaben enthalten;
   - links ist ein Buchstabe direkt davor erlaubt (z. B. „CPU1512SP“ enthält „1512SP“); eine Ziffer direkt davor bleibt verboten („21512SP“ enthält „1512SP“ nicht);
   - rechts bleiben die Regeln wie heute („1512SPX“ oder „1512SP0“ enthalten „1512SP“ nicht; Trennzeichen wie „-1 PN“ nach den bestehenden Regeln für Verbindungszeichen).
   - Zahlen mit Einheit, Versionen, Adressen, Ports und reine Zahlen bleiben unverändert (keine Lockerung für „5 kg“, „V18“, „24V“ usw.).
2. **Wirkung** gilt für `value_occurs` (Bewertung) und `verify` (Zitatprüfung) gleich, weil beide `_occurs` nutzen. Im Bericht für beide je ein Beispiel.
3. **Tests** in `backend/tests/answers/test_citations.py`: Positivfälle (Buchstaben davor, auch nach Groß-/Kleinschreibung und Bindestrich-Varianten nach den bestehenden Normalisierungsregeln), Negativfälle (Ziffer davor, Zeichen danach, Einheiten, Versionen, „V18“ in „V180“, „5 kg“ in „25 kg“ unverändert), Laufzeittest unverändert grün.
4. **Bewertung:** ein Test in `backend/tests/answers/test_evaluation.py`, dass ein key_fact dieser Form in einer Antwort mit vorangestelltem Wort gefunden wird.
5. **CI-Aufzeichnungen:** werden sie rot, neu aufnehmen (gemma4, `/api/ps` vorher leer); nichts aufweichen.
6. **Doku:** Modul-Docstring von `citations.py` (Abschnitt zu Grenzen), Docstring von `value_occurs`.

## Nicht-Ziele

- Keine Änderung an `questions.yaml` (keine neue Alternative), am Prompt, an der Kontextauswahl (läuft parallel in 153) oder an der Suche.
- Keine weitere Lockerung der Grenzen.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/answers/citations.py`
- `backend/tests/answers/test_citations.py`, `backend/tests/answers/test_evaluation.py`, ggf. `backend/tests/answers/recorded/ci_questions.json`
- diese Auftragsdatei

## Akzeptanzkriterien (prüfbar)

1. Tests aus Umfang 3 und 4 vorhanden und grün; alle bestehenden Tests in `tests/answers` unverändert grün.
2. CI wie `ci.yml` grün: backend (inkl. `pytest -m worker` mit laufendem `worker`), web, testfactory, e2e.
3. Diff nur in den genannten Bereichen, keine neue Abhängigkeit, Compose-Projekte mit `down -v` entfernt.

## Vorgaben und Hinweise

- Compose-Projekt `twox-154`, `TWOX_API_PORT=18154`. `docker` liegt nicht im PATH: `%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin`.
- Parallel läuft 153 (`context.py`, Einstellungen); deren Dateien nicht anfassen.
- Muster aus selbst geschriebenen Werten; keine Handbuchtexte in Tests.
- Nicht pushen.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine (E-76).

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- **Was wurde gebaut?** In `citations.py` gibt es die neue Hilfsfunktion `_letter_may_precede`. `_bounded` lässt einen Buchstaben direkt vor einer Fundstelle jetzt zu, wenn alle diese Bedingungen gelten: Der Schlüssel des Werts beginnt mit einer Ziffer, besteht nur aus Buchstaben und Ziffern und ist nach `_is_designation` eine Typbezeichnung. Damit fallen Zahlen mit Einheit wie „24VDC“, „5kg“ oder „2x10kg“ heraus. Der Wert ist außerdem weder Einheit noch Version noch IPv6-/MAC-Adresse. Eine Ziffer, ein `_`, ein verbindender `.` oder ein Minuszeichen direkt davor bleiben verboten. Die Regeln für das Ende der Fundstelle sind unverändert. Modul-Docstring (Abschnitt „Normalisation“, Grenzen) und Docstring von `value_occurs` sind nachgezogen.
  - Beispiel Bewertung: `value_occurs("1512SP", "Die CPU1512SP hat …")` ergibt jetzt True. `missing_key_facts` meldet das key_fact „1512SP“ für „… eine CPU1512SP [1].“ nicht mehr als fehlend, für „CPU1512SP0“ weiterhin.
  - Beispiel Zitatprüfung: `verify("Die Steuerung 1512SP wird mit 24 V versorgt [1].", {1: "Die Steuerung CPU1512SP hat eine Versorgung von 24 V DC."})` ergibt `answered` ohne entfernten Satz. Vorher wurde der Satz als `unsupported_value` entfernt.
- **Wie wurde getestet?** In `test_citations.py` gibt es neue Tests. Ein parametrisierter Test prüft jeden Fall mit `value_occurs` und mit `verify`:
  - Positivfälle: Groß- und Kleinschreibung, „1512-SP“ und „1512SP-1 PN“, geschütztes Bindestrich-Zeichen.
  - Negativfälle: Ziffer davor, „SPX“ oder „SP0“ danach, `_`, `.` und Minuszeichen davor, „5 kg“ in „25 kg“ und „X5kg“, „24 V“ in „DC24V“, „V18“ in „V180“ und „XV18“, Port 502 in 5020.

  Dazu kommen ein Satztest für `verify` und ein Test, dass `value_occurs` die Regel nicht auf „1500“, „24V“, „24VDC“, „2x10kg“, „V18“, „V2.1a“, IPv4 und Port anwendet. In `test_evaluation.py` stehen vier neue Fälle in `test_key_facts_are_whole_values` und ein neuer Test `test_key_fact_of_a_designation_right_after_a_word_is_found`. Den CI-Ablauf nach `ci.yml` habe ich lokal nachgestellt, Compose-Projekt `twox-154`:
  - Backend: ruff, Formatprüfung, mypy, `pytest` (3630 bestanden, 1 übersprungen), `pytest -m worker` mit laufendem worker (6 bestanden). Übersetzungskatalog, Migrationen, Lizenzen und OpenAPI-Schema ohne Änderung.
  - Web: Lint, Typprüfung, 1132 Tests, Build, Lizenzen, API-Client ohne Änderung.
  - testfactory: alle Schritte grün.
  - e2e: 102 bestanden, 2 übersprungen.

  Die CI-Aufzeichnungen (`test_ci_questions`) blieben grün. Eine Neuaufnahme war nicht nötig.
- **Zweig und Arbeitsverzeichnis:** Zweig `worktree-agent-a38449252bf12742b`, Arbeitsverzeichnis `.claude/worktrees/agent-a38449252bf12742b`.
- **Abweichungen:** keine. Hinweis: Wenn die Antwort „CPU1512SP-1PN“ ohne Leerzeichen vor „PN“ enthält, prüft `verify` weiterhin den Wert „1512SP-1“. Dieser Wert gilt in „…-1PN“ als verlängert. Das war schon vor diesem Auftrag so und gehört nicht zum Umfang. `value_occurs("1512SP-1 PN", "CPU1512SP-1PN")` findet den Wert.
