# Auftrag 155 – Prompt: verschiedene Typangaben für dasselbe Bauteil sind ein Widerspruch

Meilenstein: M3 · Freigabestufe: B (Teil C von E-76) · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
