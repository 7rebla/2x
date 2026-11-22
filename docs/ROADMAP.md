# Meilensteine

Quelle: STARTUNTERLAGE.md, Abschnitt 9 (Entwurf 2 vom 21.11.2026).

Die Wochen sind Richtwerte. Mit dem Betrieb ohne a7 kann es schneller gehen; maßgeblich bleibt seine Abnahme je Meilenstein.

| Nr. | Inhalt | Abnahme | Wochen | Stand |
| --- | --- | --- | --- | --- |
| M0 | Gerüst: Repository, Werkzeuge, Django-Projekt, Celery-Worker, Compose mit allen Containern, Oberfläche als Grundgerüst, CI, `.claude`-Einrichtung, eine Testseite durch alle Schichten | `docker compose up` startet alles; die Testseite zeigt einen Wert aus der Datenbank und ein Ergebnis aus dem Worker; CI ist grün | 1 | abgenommen 21.11.2026 (E-35) |
| M1 | Geräte und Dateien: Struktur, Geräte, CSV-Import, Upload mit Versionen, Anmeldung und Rollen, Protokoll | Geräteliste der Testfabrik per CSV geladen; eine Datei mit zwei Versionen; das Protokoll zeigt die Änderungen | 2–3 | abgenommen 22.11.2026 (E-49) |
| T1 | Testfabrik Teil 1 (parallel zu M1): Manifest, Lade-Skript, Geräteliste und Netzplan, Unterlagen der Fertigungslinie geladen, Nutzungsbedingungen je Quelle vermerkt | das Lade-Skript holt alles mit passender Prüfsumme; jede Anlage hat den Nachweis der drei Bedingungen aus Abschnitt 10 | 2–3 | abgenommen 21.11.2026 mit Lücke O-1 (E-36) |
| M2 | Einlesen und Suche: Einlese-Aufträge, Docling-Anbindung, Abschnitte, Stichwort- und Vektorsuche | Handbücher der Fertigungslinie und des Roboters eingelesen; die Suche findet eine IP-Adresse und eine sinngemäß gestellte Frage; Fehler sind sichtbar | 4–5 | abgenommen 22.11.2026 (E-67) |
| M3 | Auskunft mit Quellen: Frage und Antwort, Quellenanzeige, Eingrenzen auf Gerät | mindestens 8 von 10 Prüffragen richtig; Kontrollfrage ohne erfundene Antwort | 6–7 | offen |
| T2 | Testfabrik Teil 2 (parallel zu M3 und M4): URSim und OPNsense laufen; ihre Konfigurationen sind exportiert | Softwarestand von Handbuch und laufender Software stimmt überein | 6–8 | offen |
| M4 | Steckbrief: Feldvorschläge mit Herkunft, bestätigen und korrigieren | Steckbrief für fünf Geräte der Testfabrik; jede Angabe führt zur Quelle | 8 | offen |
| M5 | Konfigurationen: Einlese-Module 2–4, Schwärzen von Zugangsdaten, Anzeige mit Zeilenbezug | kein Kennwort in Datenbank oder Index; Fragen zu Konfigurationen werden belegt beantwortet | 9–10 | offen |
| M6 | Version 0.1: Installationsanleitung, Testfabrik in einem Befehl ladbar, Prüffragen in der CI | ein fremder Rechner startet in 10 Minuten; erste Tester haben Zugang | 11–12 | offen |
| M1b | Landkarte als interaktive Vorschau (vorgezogen, E-48): Struktur, Geräte und IP-Netze, ohne abgeleitete Verbindungen | Auftrag 039 | – | abgenommen mit M1 (E-49) |
| M7 | Landkarte: Beziehungen aus Konfigurationen, Darstellung | | danach | offen |
| M8 | Änderungsvergleich zwischen Versionen | | danach | offen |
| M9 | Was-wäre-wenn im Kleinen: Netzänderungen prüfen, Daten abspielen | | danach | offen |
| M10 | Verwaltungsschale-Export und MCP-Schnittstelle | | danach | offen |
| M11 | IT-Anbindung (NetBox) | | danach | offen |

**Parallel möglich ab M2:** weitere Einlese-Module, Oberfläche, Testfabrik. M7 kann beginnen, sobald M5 steht.

Die Reihenfolge von M7–M11 untereinander ist noch offen (E-12).

## Einlese-Module in dieser Reihenfolge (Abschnitt 10.5)

1. Dokumente (PDF, Office, Markdown) über Docling
2. Dienste der Zentralsteuerung: Node-RED-Flows, Mosquitto-Konfiguration, Docker Compose, Systemdienste
3. OPNsense `config.xml`
4. Universal Robots: Installationsdatei, Programme, URScript
5. SPS-Projekte in offenen Textformaten (PLCopen XML, TwinCAT, Structured Text)
6. Exporte aus Siemens-Projekten
7. Weitere Formate, sobald die Testfabrik wächst

Die genauen Formate prüft jeder Auftrag gegen die Herstellerdoku, bevor er sie umsetzt.
