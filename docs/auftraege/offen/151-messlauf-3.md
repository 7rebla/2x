# Auftrag 151 – Messlauf 3 nach 148, 149 und 150

Meilenstein: M3 · Freigabestufe: C · Status: offen

## Ziel

Messlauf 144 ergab 5/10 (Kontrollfrage stabil). Danach kamen nach E-74 und E-75:
- 148: Prompt-Regel 4 – Widerspruch nur bei unvereinbaren Angaben (Befund B5, Prüffrage 10).
- 149: Vektorliste zählt Inhalte statt Zeilen (Diagnose 147, Variante V5).
- 150: Teilstücke ≤ 1 000 Zeichen mit eigenen Vektoren (Variante V4a).

Gemessen wird, ob die Auskunft jetzt mindestens 8/10 erreicht und die Kontrollfrage in jedem Lauf absagt. Das Ergebnis ist die Vorlage für a7: bei ≥ 8/10 Empfehlung, den Abnahmelauf 138 zu starten; sonst Befunde je Frage mit Ursache und Vorschlag.

## Umfang

Ablauf, Befehle, Prüfungen und Berichtsform **wie Auftrag 144** (`docs/auftraege/erledigt/144-messlauf-2-chat-modell.md`, Schritte 1–12 und Akzeptanzkriterien), mit diesen Abweichungen:

1. **Voraussetzungen:** 148, 149 und 150 liegen auf `main` (Commit-Kennungen im Bericht). Die Leitstelle hat „2x“ auf diesem Stand gebaut, migriert (0004) und neu eingebettet; die Prüfung „0 Abschnitte brauchen eine Einbettung“ und die Suchmessung der Leitstelle stehen in `docs/STATUS.md` (Notiz zu 150). Vor Beginn selbst prüfen, dass im Container `api` der Code von `main` läuft (Prüfsumme von `backend/twox/search/postgres.py` und `backend/twox/answers/prompt.py` im Container gegen `main`) und dass `needs_embedding` 0 Abschnitte meldet. Ist das nicht so, nicht messen, Status „wartet“.
2. **Kein Neubau und keine Migration** durch den Bearbeiter, wenn Schritt 1 stimmt (sonst nur Neubau/Migration wie 144, aber keine Neueinbettung – die macht die Leitstelle).
3. **Seed 151.** Sonst dieselben Läufe wie 144: 3 Läufe Mehrheit (streng in Klammern), `--literal` 1 Lauf, `--wording probe` 1 Lauf, Injection-Probe in `-p twox-inj`, qwen-Gegenprobe nur wenn Zeit bleibt.
4. **Vergleich** je Frage zu 128 **und** 144, je Befund B1–B5 aus 128 ein Urteil.
5. **Zusätzlich:** Zahl der Quellen je Frage gegen 144 (149 soll mehr verschiedene Quellen bringen); kleinster Abstand der Kontrollfrage und von Frage 8 gegen 144 (150 ändert die Abstände – Lage zur Schwelle 0,55 berichten).
6. **Befund aus 148 beobachten:** Meldet eine Frage einen Widerspruch oder fehlt einer, prüfen, ob die Sprachfassungs-Regel (E-61, `TWOX_ANSWER_TRANSLATION_DISTANCE`, `context.py` Schritt 6) eine Quelle weggelassen hat. Nur berichten.

## Nicht-Ziele

Wie 144: keine Code- oder Datenänderung, keine Änderung an Startwerten, Prompt, `questions.yaml`; kein Abnahmelauf (138); keine Neueinbettung; kein Push. Einzige getrackte Änderung ist der Kurzbericht in dieser Datei, auf dem eigenen Zweig.

## Betroffene Bereiche (Ordner, Dateien)

Wie 144: diese Auftragsdatei (Kurzbericht); Testumgebung „2x“ im Hauptordner nur lesend bzw. Neustart; eigenes Projekt `twox-inj`, am Ende entfernt; ungetrackt `Claude outputs/151/` und Scratchpad.

## Akzeptanzkriterien (prüfbar)

Wie 144, Kriterien 0–11, mit den Abweichungen aus „Umfang“. Zusätzlich: Tabelle Frage × (128, 144, 151) mit Urteil, Rang der Belegstelle und Zahl der Quellen.

## Vorgaben und Hinweise

Wie 144. `docker` liegt nicht im PATH: `%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin`. Vor jedem Lauf `/api/ps` prüfen. Keine Handbuchauszüge, keine Antworttexte im Bericht.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine vor dem Start. Optionen und Empfehlung nach dem Messlauf im Kurzbericht.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
