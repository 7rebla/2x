# Auftrag 148 – Prompt: Widerspruch nur bei unvereinbaren Angaben

Meilenstein: M3 · Freigabestufe: B (Richtung entschieden in E-74) · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
