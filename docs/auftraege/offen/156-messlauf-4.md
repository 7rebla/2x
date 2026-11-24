# Auftrag 156 – Messlauf 4 nach 153, 154 und 155

Meilenstein: M3 · Freigabestufe: C · Status: offen

## Ziel

Messlauf 151 ergab 6/10 (Kontrollfrage stabil). Danach kamen nach E-76:
- 153: kurze Abschnitte (< 200 Zeichen) keine eigene Quelle; von zwei Sprachfassungen bleibt die längere.
- 154: Typbezeichnungen wie „1512SP“ werden auch direkt hinter einem Wort erkannt (Bewertung und Zitatprüfung).
- 155: Regel 4 – verschiedene Typen für dasselbe Bauteil sind ein Widerspruch.

Gemessen wird, ob die Auskunft jetzt mindestens 8/10 erreicht und die Kontrollfrage in jedem Lauf absagt. Bei ≥ 8/10: Empfehlung, den Abnahmelauf 138 zu starten; sonst Befunde je Frage mit Ursache und Vorschlag.

## Umfang

Ablauf, Befehle, Prüfungen und Berichtsform **wie Auftrag 151** (`docs/auftraege/erledigt/151-messlauf-3.md`), mit diesen Abweichungen:

1. **Voraussetzungen:** 153, 154 und 155 liegen auf `main`; die Leitstelle hat „2x“ auf diesem Stand gebaut. Vor Beginn selbst prüfen: Prüfsummen von `search/postgres.py`, `answers/prompt.py`, `answers/context.py`, `answers/citations.py`, `config/settings.py` im Container `api` gleich `main`; `needs_embedding` = 0. Stimmt das nicht: nicht messen, Status „wartet“.
2. **Seed 156.** Läufe wie 151 (3 Läufe Mehrheit, `--literal`, `--wording probe`, Injection-Probe in `-p twox-inj`, qwen-Gegenprobe wenn Zeit bleibt).
3. **Vergleich** je Frage zu 128, 144 und 151; je Befund B1–B5 und N1 ein Urteil.
4. **Falsche Widersprüche (Risiko aus 155):** Für jede Frage und jeden Lauf mit Status `contradiction` angeben, welche Quellen genannt sind, ob sie dasselbe Gerät/Bauteil betreffen und ob der Widerspruch echt ist (nur Kennzeichnungen, keine Texte). Jede Frage, die gegenüber 151 wegen eines Widerspruchs falsch wird, ist ein eigener Befund.
5. **Kurze Abschnitte (153):** Zahl der Quellen je Frage gegen 151; ob eine Frage eine Quelle mit key_facts verliert, weil sie < 200 Zeichen hat (bekannt aus 153: Frage 8 hat einen key_fact-Abschnitt mit 105 Zeichen, Frage 9 mit 96 und 133).
6. **Trefferzahl:** Für Fragen, deren Belegstelle nicht im Kontext ist, Rang der Belegstelle in der kombinierten Liste (2k = 16 Treffer heute). Daraus die erwartete Wirkung von 3k = 24 Treffern berichten (Vorschlag aus 153; nur Diagnose, keine Änderung).

## Nicht-Ziele

Wie 151: keine Code- oder Datenänderung, keine Änderung an Startwerten, Prompt, `questions.yaml`; kein Abnahmelauf (138); keine Neueinbettung; kein Push. Einzige getrackte Änderung ist der Kurzbericht in dieser Datei, auf dem eigenen Zweig.

## Betroffene Bereiche (Ordner, Dateien)

Wie 151.

## Akzeptanzkriterien (prüfbar)

Wie 151, dazu: Tabelle Frage × (128, 144, 151, 156) mit Urteil, Rang der Belegstelle und Zahl der Quellen; Tabelle der Widersprüche (Umfang 4).

## Vorgaben und Hinweise

Wie 151. `docker` liegt nicht im PATH: `%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin`. Vor jedem Lauf `/api/ps` prüfen. Keine Handbuchauszüge, keine Antworttexte im Bericht.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine vor dem Start. Optionen und Empfehlung nach dem Messlauf im Kurzbericht.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
