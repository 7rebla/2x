# Status

Stand: 21.11.2026 · gepflegt von der Leitstelle

## Freigegeben

Alle Aufträge für M0 und T1 (E-21). Die Fragen in den Aufträgen sind nach Empfehlung entschieden (E-23).
Höchstens fünf Bearbeiter gleichzeitig (E-24), M0 und T1 zusammen gezählt. Eine Welle startet erst, wenn ihre Voraussetzungen nach `main` zusammengeführt sind. M0 hat Vorrang, damit früh etwas zum Ansehen da ist; T1-Aufträge füllen freie Plätze.

### M0 – Gerüst

| Nr. | Auftrag | Stufe | Welle | Hängt ab von | Status |
| --- | --- | --- | --- | --- | --- |
| 001 | Backend: Werkzeuge und Container | C | 1 | – | erledigt |
| 002 | Oberfläche als Grundgerüst | C | 1 | – | erledigt |
| 003 | Suche nach Geheimnissen | C | 1 | – | erledigt (CI grün) |
| 004 | Messung Dateizugriff | B | 2 | 001, 002 | offen |
| 005 | API-Grundlage | C | 3 | 001 | erledigt |
| 006 | Lizenzprüfung | C | 3 | 001, 002 | erledigt |
| 007 | Prüfung der Erreichbarkeit von Ollama | B | 3 | 001 | erledigt |
| 008 | Celery-Worker mit Valkey | C | 4 | 005 | erledigt |
| 009 | docling-serve als Container | C | 5 | 008 | in Arbeit |
| 010 | Testseite, Teil API | C | 5 | 005, 008 | erledigt |
| 011 | CI-Hauptworkflow | C | 5 | 002, 005, 006, 008 | offen |
| 012 | Testseite, Teil Oberfläche | C | 6 | 002, 010 | in Arbeit |
| 013 | Auslieferung der Oberfläche durch Django | C | 6 | 002, 009, 010 | offen |
| 014 | Playwright-Test der Testseite | C | 7 | 011, 012, 013 | offen |
| 015 | ARCHITECTURE.md und README | B | 8 | 006, 007, 009, 013, 014 | offen |

### T1 – Testfabrik Teil 1

| Nr. | Auftrag | Stufe | Welle | Hängt ab von | Status |
| --- | --- | --- | --- | --- | --- |
| 101 | Manifest-Format und Werkzeug-Container | C | 1 | – (Python-Version aus 001 eintragen) | erledigt |
| 102 | Quellen und Lizenzlage der Fertigungslinie | C | 1 | – | erledigt |
| 103 | Quellen und Nutzungsbedingungen: Standardgeräte, UR5e, URSim, OPNsense-Doku | C | 1 | – | erledigt |
| 104 | Lade-Skript `fetch.py` | B | 2 | 101 | erledigt |
| 105 | Manifest-Einträge der Fertigungslinie | C | 2 | 101, 102 | erledigt |
| 106 | Aufbau der Testfabrik: Geräteliste, Netzplan, Beschreibung | C | 2 | 101, 102 | erledigt |
| 107 | Manifest-Einträge: Standardgeräte, UR5e, URSim, OPNsense-Doku | C | 3 | 103, 105 | erledigt |
| 108 | Frei lizenzierte Testunterlagen in `testdata/klein` | C | 3 | 101, 103 | erledigt |
| 109 | Erstabruf: Unterlagen laden und Prüfsummen eintragen | B | 4 | 104, 105, 106, 107 | erledigt |
| 110 | Stände und Nutzungsvermerke nachtragen | C | 5 | 109 | in Arbeit |
| 111 | Prüffragen der Fertigungslinie mit Fundstelle | C | 5 | 109 | erledigt |
| 112 | Prüffragen des Roboters (Fragen 9 und 10) | C | 6 | 110, 111 | in Arbeit |
| 113 | Nachweis der drei Bedingungen je Anlage und Gerät | C | 6 | 106, 110 | offen |
| 114 | Testfabrik-Prüfungen in CI und Werkzeugkette | B | 7 | 101, 112, 113, 011 | offen |

## In Arbeit

- 009 (Netz abriegeln), 012 (Nacharbeit), 110, 112 als Subagenten.

## Wartet auf a7

Nichts davon hält die laufende Arbeit auf.

1. ~~Freigabe für den Push~~ – entschieden mit E-26: `main` wird nach jedem geprüften Zusammenführen gepusht.
2. **Durchsicht der Entscheidungen nach E-23** in `docs/DECISIONS.md`, vor allem die Lizenz-Ausnahmen (psycopg LGPL, pathspec und lightningcss MPL-2.0, pandoc GPL als Einmalwerkzeug) und das Zusammenführen von Stufe-C-Aufträgen ohne Einzelfreigabe.
3. **Lizenzlage fischertechnik (Auftrag 102, Frage 1):** Beide Repositories haben keine Lizenz, die Zentralsteuerung ist ausdrücklich „UNLICENSED". Soll a7 beim Hersteller anfragen? Den Entwurf der Anfrage liefert Auftrag 102. Bis dahin gilt: laden ja, weitergeben nein.
4. **URSim (Auftrag 103, Frage 3):** Die Nutzungsbedingungen erlauben nur eigene interne Nutzung. Anfrage bei Universal Robots vor T2? Arbeitsstand bis dahin: nur selbst erzeugte Dateien einchecken.
5. **GitHub Secret Scanning mit Push Protection** am Repository einschalten (Auftrag 003, Frage 1) – Einstellung am Konto, nimmt a7 selbst vor.
6. **Prüffragen in der CI (Auftrag 011, Frage 1):** Empfehlung: aufgezeichnete Antworten in der CI, dazu der echte Lauf lokal vor jedem Zusammenführen. Entscheidung spätestens zu M3.
7. **Startunterlage berichtigen (Auftrag 102, Frage 5):** Laut Recherche haben fünf statt vier Module eine S7-1200 (zusätzlich DPS). Die Leitstelle ändert die Startunterlage nicht ohne a7.
8. ~~Gebündelte Bibliotheken in psycopg-binary~~ – bestätigt mit E-28.
9. ~~Siemens: Klausel gegen Text- und Data-Mining~~ – entschieden mit E-27: nur lokal, von Hand geladen.
10. **Siemens: welche Ausgabe (Auftrag 103, Frage 6).** Aktuell ist V4.7 (12/2024, nur im Browser abrufbar); V4.6 (11/2022) passt vermutlich besser zu TIA Portal V18, das ist nicht bestätigt. Empfehlung und Arbeitsstand: beide führen, V4.6 maßgeblich, V4.7 als Verweis; beides ohne automatischen Abruf.

## Offene Abnahmebedingungen M0

1. ~~`check_llm` gegen das echte Ollama~~ – erfüllt am 21.11.2026: `OK:` aus dem Container über `host.docker.internal`, Ollama mit Standardbindung, keine Einstellung nötig.
2. ~~Eigenes Arbeitsverzeichnis je Auftragsbearbeiter~~ – erfüllt: Zweig und Ordner unter `.claude/worktrees/` bei jedem Start belegt.
3. Entscheidung zur Messung aus 004 (im Windows-Ordner bleiben oder ins WSL-2-Dateisystem umziehen).
4. CI-Läufe grün nach freigegebenem Push.
5. Sichtprüfung der Testseite unter `http://localhost:8000/` nach dem Zusammenführen von 012 und 013.
6. Abnahme durch a7.

## Erledigt seit dem letzten Bericht

- Rechner geprüft: Git 2.55, GitHub CLI, WSL 2, Docker Desktop (Engine 29.9.3, Compose 5.7.0), Ollama 0.40.17 (noch kein Modell geladen; Modellwahl in M2/M3).
- Grundgerüst angelegt und auf `main` committet.
- Entscheidungen E-14 bis E-23 protokolliert.
- 29 Aufträge für M0 und T1 recherchiert, entworfen, von drei Prüfern gegengelesen (64 Befunde) und überarbeitet.

## Als Nächstes

- Welle 1 prüfen und zusammenführen, dann 004 (Messung) und danach 005, 006, 007.
- Freie Plätze mit T1 füllen: zuerst 102 und 103 (reine Recherche), dann 101.
- Folgeaufträge vorgemerkt: Selbsttest-Endpunkt in M1 auf angemeldete Benutzer beschränken; Zeitlimit für den Fall „Broker erreichbar, Ergebnisspeicher nicht" (Vorschläge im Kurzbericht von 010).
- Siemens-Systemhandbuch V4.6 lädt a7 bei Gelegenheit selbst (E-27): Quelle und Ablage stehen im Kurzbericht von 109; danach `fetch --record --only siemens-s7-1200-system-manual-v4-6-de`.
