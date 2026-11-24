# Auftrag 153 – Kontextauswahl: kurze Abschnitte und inhaltsreichere Sprachfassung

Meilenstein: M3 · Freigabestufe: C (freigegeben mit E-76, Teil A) · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
