# Auftrag 154 – Werte wie „1512SP“ auch direkt hinter einem Wort erkennen

Meilenstein: M3 · Freigabestufe: B (Teil B von E-76) · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
