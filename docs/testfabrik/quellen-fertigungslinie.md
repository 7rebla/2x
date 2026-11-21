# Quellen und Lizenzlage – Fertigungslinie (fischertechnik Agile Production Simulation 24V)

Stand der Prüfung: 21.11.2026 · Auftrag 102 · maßgebliche Grundlage für die Manifest-Einträge (Auftrag 105) und die Geräteliste (Auftrag 106).

Diese Datei hält Befunde und eine vorsichtige Folgerung fest. Sie ist keine Rechtsberatung; die Entscheidung trifft a7.

## Lesehilfe

- **geprüft am 21.11.2026** heißt: am genannten Tag an der Originalquelle nachgesehen, nur lesend und ohne Anmeldung. Die Art der Prüfung steht jeweils dabei.
- **ungeprüft** heißt: nicht oder nicht an der Originalquelle nachgesehen. Alle solchen Stellen stehen gesammelt im Abschnitt „Offen gebliebene Punkte“.
- „Zeile“ ist die Zeile der Rohdatei am genannten Commit. „PDF-S.“ ist der Seitenindex der Datei (Zählung ab 1), „gedr. S.“ die aufgedruckte Seitenzahl. In den drei gelesenen Dokumenten gilt: gedr. S. = PDF-S. − 1.
- Größen in Byte. Bei den Unterlagen ist es der Wert `Content-Length` einer HEAD-Anfrage, bei Repository-Dateien die Blob-Größe.
- Kurzform **P** = `https://www.fischertechnik.de/-/media/fischertechnik/rebrush/industrie-und-hochschulen/technische-dokumente/agile-production-simulation`
- Zugangsdaten, die in den Quellen stehen (Auslieferungsstand), werden hier nicht wiedergegeben. Es steht nur, wo sie vorkommen.

## Zusammenfassung

| Quelle | Lizenzbefund in einem Satz | Folgerung |
| --- | --- | --- |
| Repository 1 (Programme, Flows) | Keine Lizenz: keine Lizenzdatei, kein Hinweis im README. | laden ja · weitergeben nein · einchecken nein |
| Repository 2 (Zentralsteuerung) | Keine Lizenz: README verweist auf eine fehlende LICENSE-Datei, die Zentralsteuerung trägt das Lizenzfeld `UNLICENSED`. | laden ja · weitergeben nein · einchecken nein |
| Unterlagen-Seite (PDF, ZIP) | Frei abrufbar, aber ohne Nutzungsbedingungen für Downloads und ohne Lizenzvermerk. | laden ja · weitergeben nein · einchecken nein |
| Raspberry-Pi-Abbild | Keine Lizenzangabe, keine Prüfsumme, Dritt-Hoster; Inhalt ungeprüft. | nur Verweis · nicht laden · nicht weitergeben |

Damit bleibt die Regel aus Abschnitt 10.2 der Startunterlage bestehen: laden ja, weitergeben nein. Eine Anfrage beim Hersteller liegt als Entwurf in `anfrage-fischertechnik-entwurf.md` (nicht versendet).

## Quelle 1 – Repository „Agile-Production-Simulation-24V“

- **Adresse:** https://github.com/fischertechnik/Agile-Production-Simulation-24V
- **Stand:** Standardzweig `main`, Commit `b8082e16282a69f7d219a39d993bf7d34cb9d349` vom 02.03.2026 („Update README.md“). Festgelegt nach Frage 2 des Auftrags (Antwort A); im Manifest als Softwarestand „APS 1.3.0 (main, 02.03.2026)“.
- **Weitere Stände:**
  - Tag v1.3.0 = `37e70666cee4ad08ea26840055b692988714bc40` (25.10.2024)
  - Tag v1.2.1 = `f08585d6591a5856c41c26bcaff04f7f8fdc63eb` (08.07.2024)
  - Tag v1.0.1 = `4174bc42d9792304c59e2794a21e14022f224309` (13.03.2024; annotierter Tag, Tag-Objekt `92e6c43088854b584db0f54ddf3c5364fe7b7d83`)
  - Tag v1.0.0 = `5b317470e74f0c7f263039b98dcb07bc3a002cd4` (20.02.2024)
  - Zweiter Zweig `bugfix/change-timings`, zeigt auf denselben Commit wie v1.0.1.
  - Nach v1.3.0 vier Commits: `d2c4464` „OPCUA APS1.3.0“ (09.01.2025), `eab61f2` „Update APS 1.3.0“ (09.01.2025), `1d75426` „Update ROBO PRo Coding 6.4.0“ (03.07.2025), `b8082e1` (02.03.2026).
  - Der Update-Blog des Herstellers verlinkt als aktuelle Software den Tag v1.3.0, nicht `main`.
- **Rechteinhaber:** fischertechnik GmbH (Inhaber des GitHub-Kontos; im Repository steht kein Rechtevermerk). Ob einzelne Teile einem Dienstleister gehören, ist ungeprüft.
- **Größe:** 28 Dateien, zusammen 8.067.956 Byte; 34 Baumeinträge einschließlich 6 Ordnern.
- **Lizenzbefund:** keine Lizenz.
  - Im Baum des Commits gibt es keine Datei mit „license“, „notice“ oder „copying“ im Namen (Dateiliste unten).
  - `README.md` (49 Zeilen) enthält kein Wort zu Lizenz oder Urheberrecht.
  - Das Lizenzfeld der GitHub-API ließ sich am Prüftag nicht abrufen (Anfragegrenze ohne Anmeldung erreicht): ungeprüft. Der Befund stützt sich auf den Dateibaum.
  - Eingebettete Lizenztexte in den `.zap18`- und `.ft`-Archiven: ungeprüft (Auftrag 110 sucht nach dem Abruf).
- **Folgerung:** laden ja (öffentlich abrufbar, zum Ansehen und Verwenden mit dem Produkt bereitgestellt) · weitergeben nein · einchecken nein. Ohne Lizenz bleiben alle Rechte beim Rechteinhaber. Eigene Dateien dürfen Adressen, Commit-Kennungen, Prüfsummen und selbst formulierte Beschreibungen enthalten, aber keine Dateien oder längeren Auszüge.
- **geprüft am:** 21.11.2026 – `git ls-remote`, Commit-Verlauf und Baum über einen Abruf ohne Dateiinhalte; `README.md`, `OPC-UA.md` und `RPI_Image.md` vollständig gelesen; Größen der übrigen Dateien über HEAD-Anfragen an die Rohdateien des Commits.

### Dateien am festgelegten Commit

| Pfad | Größe | Bemerkung |
| --- | ---: | --- |
| `README.md` | 3.193 | Links auf Unterlagen (teils veraltet), Hinweise zu Abbild, TXT, Node-RED, SPS |
| `OPC-UA.md` | 800 | nur Überschriften und 12 Bildverweise, kein maschinenlesbarer Signaltext |
| `RPI_Image.md` | 2.692 | Anleitung zum Schreiben des Abbilds auf eine Speicherkarte |
| `Node-RED/flows.json` | 1.378.744 | Blob `5ee9d96a21155b791bf395d3770486133ae2f5f3`, 33.823 Zeilen |
| `PLC-programs/S7_1200_TIAv18/AIQSv1_3_0.zap18` | 556.993 | TIA-Portal-Archiv V18 |
| `PLC-programs/S7_1200_TIAv18/DPSv1_6_0.zap18` | 602.243 | TIA-Portal-Archiv V18 |
| `PLC-programs/S7_1200_TIAv18/DRILLv1_3_0.zap18` | 493.122 | TIA-Portal-Archiv V18 |
| `PLC-programs/S7_1200_TIAv18/HBWv1_3_0.zap18` | 866.133 | TIA-Portal-Archiv V18 |
| `PLC-programs/S7_1200_TIAv18/MILLv1_3_0.zap18` | 482.660 | TIA-Portal-Archiv V18 |
| `PLC-programs/S7_1200_TIAv18/OVENv1_3_0.zap18` | 475.148 | Zusatzmodul Brennofen; nach Frage 3 nicht Teil der Testfabrik |
| `PLC-programs/S7_1200_TIAv18/exercises/MILLv1_3_0_Solution.zap18` | 498.451 | Übungslösung |
| `TXT4.0-programs/FF_AI_24V.ft` | 60.135 | TXT-Programm (AIQS) |
| `TXT4.0-programs/FF_CGW.ft` | 35.094 | TXT-Programm (Cloud-Gateway) |
| `TXT4.0-programs/FF_DPS_24V.ft` | 272.626 | TXT-Programm (DPS) |
| `TXT4.0-programs/fts_main.ft` | 147.249 | TXT-Programm (Transportfahrzeug) |
| `TXT4.0-programs/ServoCalib_DPS.ft` | 13.023 | Kalibrierhilfe |
| `doc/` (12 Bilder) | 2.179.650 | eine Übersichtsgrafik, ein Verbindungsbild, zehn Bildschirmfotos der OPC-UA-Signale |

Die Zuordnung der `.ft`-Programme zu Modulen folgt den Dateinamen; der Inhalt der Archive ist ungeprüft.

### Einzelbefunde

- `OPC-UA.md` besteht nur aus Bildern (Zeilen 4–26). Die OPC-UA-Signale liegen damit nicht als Text vor.
- `README.md` Zeile 29 verweist für das Raspberry-Pi-Abbild auf eine Kurzadresse außerhalb von GitHub (siehe Quelle 4). Das Abbild liegt nicht im Repository.
- `README.md` Zeile 33 nennt Standard-Zugangsdaten des Abbilds (Auslieferungsstand). Sie werden nirgends übernommen.
- `README.md` Zeile 23 spricht von vier verschiedenen TXT-Controllern; Zeile 47 nennt TIA Portal V18 als Voraussetzung; Zeile 43 nennt die Adresse von Node-RED auf der Zentralsteuerung.
- `README.md` Zeilen 8, 9 und 15 verlinken Altstände der Unterlagen (siehe Tabelle unten). Zeile 2 nennt eine Kontaktadresse des Herstellers für Fragen.

## Quelle 2 – Repository „Agile-Production-Simulation-24V-Dev“

- **Adresse:** https://github.com/fischertechnik/Agile-Production-Simulation-24V-Dev
- **Stand:** Standardzweig `release` (nicht `main`), Commit `24568073f7f70d0d31dcaa83bcfcd7b595baba1f` vom 02.03.2026 („Update README.md“). Version laut `package.json` Zeile 3: 1.3.0. Keine Tags.
- **Verlauf:** fünf Commits; erster Commit 09.02.2026, öffentliche Freigabe der Zentralsteuerung 16.02.2026 (`897c727`). Zweiter Zweig `docs` = `a270dcd3f968d41f3a328c7178cc8a2f4dd1f02a` (09.02.2026); sein Inhalt wurde nicht gesondert verglichen: ungeprüft.
- **Rechteinhaber:** fischertechnik GmbH als Inhaber des GitHub-Kontos; als Autor der Zentralsteuerung nennt `central-control/package.json` Zeile 19 einen Dienstleister (OMM Solutions GmbH). Wer welche Rechte hält, ist ungeprüft.
- **Größe:** 540 Dateien, zusammen 13.628.940 Byte; 673 Baumeinträge.
- **Inhalt:** `central-control/` (Node.js/TypeScript), `common/`, `frontend/` (Angular), `nodeRed/`, `mosquitto/config/` (`mosquitto.conf` 176 B, `password.txt` 120 B), `raspberrypi/fischer-techik.service` (494 B), `docs/` (MQTT-Protokollbeschreibung: `01-introduction.md` bis `11-appendices.md`, `06-modules/` mit acht Dateien, `README.md`), `examples/`, `scripts/`, `docker-compose.yml` (1.687 B), `docker-compose-prod.yml` (1.845 B), `DEPLOYMENT.md`, zwei Einrichtungsskripte.
- **Lizenzbefund:** keine Lizenz, mit ausdrücklichem Vorbehalt für die Zentralsteuerung.
  - `README.md` Zeilen 319–321: Abschnitt „License“ mit dem Verweis „See LICENSE file for details.“ – eine solche Datei gibt es im Baum nicht.
  - `README.md` Zeile 317 verweist auf `CONTRIBUTING.md` – fehlt ebenfalls.
  - `central-control/package.json` Zeile 20: Lizenzfeld `UNLICENSED` (in npm die Angabe für „keine Nutzungsrechte eingeräumt“); Zeile 21 und Wurzel-`package.json` Zeile 4: `private`.
  - `nodeRed/package.json` Zeile 5 nennt Apache-2.0. Die Datei trägt Name, Version und Beschreibung der Vorlage node-red-docker 3.0.2 (mit deren `package.json` am Original verglichen). Die Angabe stammt aus der Vorlage und deckt die Flows des Herstellers nicht.
  - Eine Volltextsuche nach „license“, „copyright“ und „SPDX“ über alle Dateien außer den Lock-Dateien ergab sonst nur: Hinweise zur Lizenz von Docker Desktop (README Zeilen 40–42), Texte der Bedienoberfläche zu einem Lizenzschlüssel, einen Schalter der Angular-Konfiguration und Farbprofil-Vermerke in vier Bildern. Nichts davon ist eine Lizenz für das Repository.
  - Das Lizenzfeld der GitHub-API: ungeprüft (wie bei Quelle 1).
- **Folgerung:** laden ja · weitergeben nein · einchecken nein. Wegen `UNLICENSED` und des toten Lizenzverweises ist die Lage hier strenger als bei Quelle 1: Der Quelltext ist einsehbar, eine Erlaubnis zum Verändern oder Weitergeben ist nicht erkennbar. Die Testfabrik liest die Dateien nur ein; sie startet die Zentralsteuerung in T1 und T2 nicht.
- **geprüft am:** 21.11.2026 – `git ls-remote`, vollständiger Verlauf, Stand des Zweigs `release` in einem Arbeitsordner außerhalb des Projekts ausgecheckt und dort durchsucht.

### Einzelbefunde

- `nodeRed/flows.json` ist bytegleich mit `Node-RED/flows.json` aus Quelle 1: gleiche Blob-Kennung `5ee9d96a21155b791bf395d3770486133ae2f5f3`, 1.378.744 Byte.
- Lokaler Betrieb ohne Hardware: `README.md` Zeilen 323–338. Die Module werden nicht simuliert; ihre MQTT-Nachrichten müssen von Hand eingespielt werden (Zeile 334).
- `mosquitto/config/password.txt` enthält einen Eintrag mit Kennwort-Hash (Mosquitto-Format). Er wird nicht wiedergegeben und ist Material für die Schwärzungsprüfung.
- `README.md` Zeile 312 verlinkt den Altstand 04/2024 des Handbuchs.

## Quelle 3 – Unterlagen-Seite des Herstellers

- **Adresse:**
  - Englisch: https://www.fischertechnik.de/en/industry-and-universities/technical-documents/simulate/agile-production-simulation
  - Deutsch: https://www.fischertechnik.de/de-de/industrie-und-hochschulen/technische-dokumente/simulieren/agile-production-simulation
  - Update-Blog (Deutsch): https://www.fischertechnik.de/de-de/industrie-und-hochschulen/technische-dokumente/simulieren/agile-production-simulation/update-blog
  - Update-Blog (Englisch): https://www.fischertechnik.de/en/industry-and-universities/technical-documents/simulate/agile-production-simulation/update-blog
- **Stand:** Seiten ohne Datum. Der Update-Blog nennt als aktuelle Software „APS-24V v1.3.0“ mit Datum 09.01.2025. Stand je Datei: siehe Tabelle.
- **Rechteinhaber:** fischertechnik GmbH (Impressum der Seite).
- **Größe:** 20 verlinkte Dateien, zusammen 71.335.908 Byte; dazu 3 Altstände mit 5.161.500 Byte.
- **Lizenzbefund:** frei abrufbar, keine Nutzungsbedingungen für die Downloads, kein Lizenzvermerk.
  - Unterlagen-Seite (DE und EN) und Update-Blog (DE und EN): im Quelltext der Seiten kein Treffer für „Copyright“, „©“, „Urheber“, „Nutzungsbedingungen“, „terms of use“, „Lizenz“ oder „license“.
  - Seitenfuß: nur AGB des Onlineshops, Widerrufsbelehrung, B2B-AGB (PDF), Impressum, Datenschutz, Cookie-Erklärung, Hinweisgebersystem. Eigene Nutzungsbedingungen für die Website gibt es dort nicht. Die AGB-Texte selbst wurden nicht gelesen: ungeprüft (sie betreffen Käufe).
  - Impressum (https://www.fischertechnik.de/de-de/rechtliches/impressum, im Browser mit ausgeführtem Skript gelesen): drei Abschnitte – Anbieterangaben, Geschäftsführung, Verpackungsregister. Keine Aussage zum Urheberrecht oder zur Nutzung von Inhalten.
  - Handbuch Deutsch und Englisch (Stand 02/2025) sowie Add-on-Dokumentation FTS Deutsch: Textsuche nach „Copyright“, „©“, „Urheber“, „alle Rechte“, „all rights“, „Lizenz“, „license“, „Nachdruck“, „Vervielf…“ ohne Treffer. Die übrigen Dateien wurden nicht geöffnet: ungeprüft.
- **Folgerung:** laden ja (ohne Anmeldung, vom Hersteller zum Herunterladen angeboten) · weitergeben nein · einchecken nein. Ohne ausdrückliche Erlaubnis gilt das Urheberrecht des Herstellers. In eigenen Dateien stehen nur Adresse, Größe, Prüfsumme, Stand und selbst formulierte Angaben; Zitate bleiben kurz und tragen eine Fundstelle.
- **geprüft am:** 21.11.2026 – jede Adresse der Tabelle mit einer HEAD-Anfrage (alle HTTP 200, ohne Anmeldung); Verlinkung im Quelltext der vier Seiten nachgesehen; drei Dateien außerhalb des Projektordners geladen und als Text durchsucht.

### Unterlagen

Spalte „Vermerk“: **geprüft** = Adresse, Erreichbarkeit und Größe am 21.11.2026 bestätigt. Der Stand ist nur dort geprüft, wo es dabeisteht.

| Nr. | Unterlage | Sprache | Adresse | Größe | Stand | Vermerk |
| ---: | --- | --- | --- | ---: | --- | --- |
| 1 | Quick Start Guide | DE | `P/de/quick-start-guide-agile-production-simulation_de.pdf` | 640.769 | Stand ungeprüft (kein Datum im Namen) | geprüft |
| 2 | Dokumentation (Handbuch) | DE | `P/de/dokumentation_aps_de-02-2025.pdf` | 2.531.482 | Version 4, Model revision 1.x, 02/2025, 38 Seiten (Titelblatt gelesen) | geprüft |
| 3 | Belegungspläne | DE | `P/de/belegungsplaene_de-09-2024.pdf` | 1.175.306 | 09/2024 laut Dateiname | geprüft |
| 4 | Kalibrierung | DE | `P/de/kalibrierung-de.zip` | 13.329.798 | Stand ungeprüft (kein Datum im Namen) | geprüft |
| 5 | Fehlersuche | DE | `P/de/troubleshooting-aps_2025-02-03_de.pdf` | 168.049 | 03.02.2025 laut Dateiname | geprüft |
| 6 | IP-Adresse eines Moduls ändern | DE | `P/de/anleitung-ip-adresse-eines-moduls-ndern-ber-tia.pdf` | 10.089.795 | Stand ungeprüft (kein Datum im Namen) | geprüft |
| 7 | Add-on Brennofen | DE | `P/dokumentationen-brennofen/dokumentation_aps_addon_brennofen_de-09-2024.pdf` | 1.997.963 | 09/2024 laut Dateiname | geprüft; nach Frage 3 nicht Teil der Testfabrik |
| 8 | Add-on FTS | DE | `P/dokumentationen-fts/dokumentation_aps_addon_fts_de-09-2024.pdf` | 1.097.574 | Version 1, Model revision 1.x, 09/2024, 10 Seiten (Titelblatt gelesen) | geprüft; Zusatzpaket, siehe unten |
| 9 | Quick Start Guide | EN | `P/en/quick-start-guide-agile-production-simulation_en.pdf` | 639.540 | Stand ungeprüft (kein Datum im Namen) | geprüft |
| 10 | Documentation (Handbuch) | EN | `P/en/documentation_aps_en-02-2025.pdf` | 2.650.705 | 02/2025 laut Dateiname, 38 Seiten | geprüft |
| 11 | Assignment Plans | EN | `P/en/assignmentplans_aps_en-09-2024.pdf` | 1.178.112 | 09/2024 laut Dateiname | geprüft |
| 12 | Calibration | EN | `P/en/calibration-en.zip` | 23.223.044 | Stand ungeprüft (kein Datum im Namen) | geprüft |
| 13 | Troubleshooting | EN | `P/en/troubleshooting_aps_2025-02-03_en.pdf` | 121.035 | 03.02.2025 laut Dateiname | geprüft |
| 14 | Changing the IP Address of a module | EN | `P/en/changing-the-ip-address-of-a-module-via-tia-en.pdf` | 2.222.861 | Stand ungeprüft (kein Datum im Namen) | geprüft |
| 15 | Add-on Annealing Furnace | EN | `P/dokumentationen-brennofen/documentation_aps_addon_annealingfurnace_en-09-2024-en.pdf` | 1.991.292 | 09/2024 laut Dateiname | geprüft; nach Frage 3 nicht Teil der Testfabrik |
| 16 | Add-on AGV | EN | `P/dokumentationen-fts/documentation_aps_addon_agv_en-09-2024-en.pdf` | 1.152.423 | 09/2024 laut Dateiname | geprüft; Zusatzpaket, siehe unten |
| 17 | Software-Versionen („Welche Software Version habe ich?“, Update-Blog) | DE | `P/de/software-info-aps_de.pdf` | 249.791 | Stand ungeprüft (kein Datum im Namen) | geprüft |
| 18 | Software-Versionen (Update-Blog) | EN | `P/en/software-info-aps-en.pdf` | 212.679 | Stand ungeprüft (kein Datum im Namen) | geprüft |
| 19 | Anleitung Software-Update (Update-Blog) | DE | `P/de/software-update-aps_de.pdf` | 3.344.210 | Stand ungeprüft (kein Datum im Namen) | geprüft |
| 20 | Anleitung Software-Update (Update-Blog) | EN | `P/en/software-update-aps_en.pdf` | 3.319.480 | Stand ungeprüft (kein Datum im Namen) | geprüft |

Prüfsummen (SHA-256) der drei am 21.11.2026 gelesenen Dateien, als Vergleichswert für Auftrag 105:

- Nr. 2: `662ae19b00945aab2b014c72d6a6bd966403bf0f2cc2b939f6b97a4658350d55`
- Nr. 10: `f4555cab6cdc25d39769d7388b848622d23c1c4180ccb519c2965a4db19304d2`
- Nr. 8: `9c683020c8cbd0317acf682ba122b580501a2aedc3cf8e2d4874d58f06419886`

### Reine Verweise (werden nicht geladen)

| Nr. | Verweis | Sprache | Adresse | Größe | Stand | Vermerk |
| ---: | --- | --- | --- | ---: | --- | --- |
| A1 | Altstand Handbuch | EN | `P/en/documentation_aps_en-0424.pdf` | 4.499.304 | 04/2024 laut Dateiname | geprüft; auf der Seite nicht mehr verlinkt, aber in beiden GitHub-READMEs |
| A2 | Altstand Belegungspläne | EN | `P/en/assignmentplans_aps_en.pdf` | 548.353 | Stand ungeprüft | geprüft; nur noch im README von Quelle 1 verlinkt |
| A3 | Altstand Fehlersuche | DE | `P/de/fehlersuche_aps_de.pdf` | 113.843 | Stand ungeprüft | geprüft; nur noch im README von Quelle 1 verlinkt |
| A4 | Raspberry-Pi-Abbild | – | https://short.omm.cloud/rpi-v130 → https://omm-apc-releases.s3-eu-central-1.ionoscloud.com/20240925.dd | 8.869.171.712 | Datei vom 25.09.2024 laut Server | geprüft (nur HEAD); siehe Quelle 4 |

### Einzelbefunde

- Der Server der Unterlagen liefert weder `Last-Modified` noch `ETag` (bei allen 23 Adressen). Dateien ohne Datum im Namen können sich unbemerkt ändern; das Manifest braucht deshalb eigene Prüfsummen.
- Die Seite nennt die Artikelnummer 569289 nicht. Sie steht auf der Produktseite, auf die `README.md` Zeile 5 von Quelle 1 verweist.
- Das Handbuch nennt Standard-Zugangsdaten in einer Tabelle (PDF-S. 38). Sie werden nicht wiedergegeben.
- Fundstück aus der Startunterlage bestätigt: Das Handbuch nennt auf PDF-S. 34 (gedr. S. 33), deutsch und englisch, die S7-1200 und im selben Satz eine CPU 1512SP.

### Prüfpunkt: Gehört die Add-on-Dokumentation FTS zum Grundprodukt Art.-Nr. 569289?

**Nein. Sie gehört zu einem Zusatzpaket: einem weiteren Transportfahrzeug.** Geprüft am 21.11.2026.

- Unterlagen-Seite (DE), Abschnitt „Add Ons“: Der Download steht dort neben dem Brennofen unter der Beschreibung „Das zusätzliche Fahrerlose Transportsystem (FTS)“. Das Fahrzeug der Grundausstattung wird getrennt davon unter „Die Fabrikmodule im Überblick“ beschrieben.
- Add-on-Dokumentation FTS (DE), PDF-S. 3 (gedr. S. 2): „dass es sich hier um ein Add On handelt“; die Anleitung führt bis zum Betrieb mehrerer Fahrzeuge. Das Inhaltsverzeichnis (PDF-S. 2) nennt das Aufstellen eines weiteren Fahrzeugs und die Anpassung der Konfiguration für mehrere Fahrzeuge.
- Folgerung: Für das eine Fahrzeug der Testfabrik ist das Handbuch (Nr. 2 und 10) die maßgebliche Unterlage. Die Add-on-Dokumentation beschreibt den Ausbau auf mehrere Fahrzeuge. Ob sie trotzdem als Unterlage geladen wird, entscheidet Auftrag 105 mit a7; sie beschreibt kein Gerät, das in der Testfabrik steht.
- Die Artikelnummern der beiden Add-ons stehen weder auf der Seite noch im gelesenen Dokument: ungeprüft.

## Quelle 4 – Raspberry-Pi-Abbild der Zentralsteuerung

- **Adresse:** https://short.omm.cloud/rpi-v130 (aus `README.md` Zeile 29 von Quelle 1), Weiterleitung (HTTP 301) auf https://omm-apc-releases.s3-eu-central-1.ionoscloud.com/20240925.dd
- **Stand:** Dateiname und `Last-Modified` nennen den 25.09.2024. Das liegt vor dem Tag v1.3.0 (25.10.2024). Die Kurzadresse trägt „v130“ im Namen; ob das Abbild den Softwarestand 1.3.0 enthält, ist ungeprüft.
- **Rechteinhaber:** ungeprüft. Kurzadresse und Speicherort gehören zum Dienstleister, nicht zum Hersteller; das Abbild enthält neben der Software der Zentralsteuerung ein Betriebssystem mit Bestandteilen Dritter.
- **Größe:** 8.869.171.712 Byte.
- **Lizenzbefund:** keine Angabe – weder im README noch in `RPI_Image.md` (58 Zeilen, nur Schreibanleitung) noch an der Adresse. Der Hersteller veröffentlicht keine Prüfsumme. Der Server liefert ein `ETag`; es stammt aus einem mehrteiligen Hochladen und ist keine Prüfsumme des Inhalts. Inhalt und Lizenzen des Abbilds: ungeprüft.
- **Folgerung:** nur als Verweis führen · nicht laden · nicht weitergeben · nicht einchecken (Frage 4 des Auftrags, Antwort A; benannte Ausnahme von Abschnitt 10.3 der Startunterlage). Das Abbild enthält laut README Standard-Zugangsdaten.
- **geprüft am:** 21.11.2026 – nur HEAD-Anfragen (Weiterleitung, Größe, Datum); die Datei wurde nicht geladen.

## Korrekturbedarf an der Startunterlage (Abschnitt 10.2)

| Punkt | Abweichung | Fundstelle | Vermerk |
| --- | --- | --- | --- |
| a | Sechs SPS-Projekte, davon fünf in Modulen der Grundausstattung mit S7-1200 und OPC UA: MILL, DRILL, AIQS, HBW und DPS – nicht vier. OVEN ist Zusatzmodul. DPS und AIQS haben SPS und TXT-Controller. | Handbuch DE PDF-S. 38 (Tabelle, Zeile zur SPS); `DPSv1_6_0.zap18` in Quelle 1; `flows.json` Zeile 1423 (OPC-UA-Endpunkt DPS); Quelle 2 `docs/04-opcua-relationship.md` Zeile 317 | bestätigt |
| b | Das Handbuch nennt vier TXT 4.0. Programme: `FF_DPS_24V`, `FF_AI_24V`, `FF_CGW`, `fts_main`, dazu `ServoCalib_DPS`. | Handbuch DE und EN PDF-S. 15; Quelle 1 `README.md` Zeile 23 und Ordner `TXT4.0-programs/` | bestätigt |
| c | Modulliste stimmt mit der Startunterlage überein; OVEN ist ein Add-on. | Handbuch DE PDF-S. 3–4 (Lieferumfang); Unterlagen-Seite, Abschnitt „Add Ons“ | bestätigt |
| d | Adressplan der SPS: MILL .40–45, DRILL .50–55, OVEN .60–65, AIQS .70–75, HBW .80–83, DPS .90. Die Entwicklungsumgebung von Quelle 2 setzt abweichend MILL .135, DRILL .130, OVEN .125, AIQS .120, DPS .150, HBW .140. Für die TXT-Controller gibt es keine festen Adressen (DHCP; Startadresse soll auf .101 gestellt werden). | Handbuch DE und EN PDF-S. 38; `flows.json` Zeilen 1315, 1342, 1369, 1396, 1423, 1450; Quelle 2 `docker-compose.yml` Zeilen 53–58; Handbuch DE PDF-S. 31 | bestätigt |
| e | Die „OPC-UA-Beschreibung“ ist eine Bildersammlung. | Quelle 1 `OPC-UA.md` Zeilen 4–26 | bestätigt |
| f | Das Raspberry-Pi-Abbild liegt nicht im Repository, sondern bei einem Dritt-Hoster: 8,9 GB, ohne Prüfsumme. | Quelle 1 `README.md` Zeile 29; HEAD-Anfrage (Quelle 4) | bestätigt |
| g | „Software-Update“ und „Software-Versionen“ liegen auf dem Update-Blog, nicht auf der Unterlagen-Seite. Zusätzlich gibt es „IP-Adresse eines Moduls ändern“ und zwei Add-on-Dokumentationen. | Unterlagen-Seite und Update-Blog (Tabelle oben, Nr. 6–8, 14–20) | bestätigt |
| h | „Keine Lizenz zu finden“ trifft zu und ist schärfer: Lizenzfeld `UNLICENSED`, Verweis auf eine fehlende LICENSE-Datei. | Quelle 2 `central-control/package.json` Zeile 20; `README.md` Zeilen 319–321 | bestätigt |

Seitenangaben wurden am Seitenindex des aus dem PDF gewonnenen Texts geprüft; die Tabellen auf PDF-S. 38 sind dabei nur als Textzeilen lesbar. Die Zuordnung der Tabellenspalten prüft Auftrag 106 an der geladenen Datei erneut.

Weitere Beobachtung für die Leitstelle: Die Startunterlage nennt als öffentliche Datei eine „OPC-UA-Beschreibung“ und das „Raspberry-Pi-Abbild“ unter den GitHub-Dateien; beides ist nach e und f zu berichtigen.

## Offen gebliebene Punkte

1. Lizenzfeld der GitHub-API für beide Repositories: ungeprüft (Anfragegrenze ohne Anmeldung). Der Befund „keine Lizenz“ stützt sich auf Dateibaum und Volltextsuche.
2. Eingebettete Lizenztexte in `.zap18` und `.ft` (Quelle 1): ungeprüft, folgt in Auftrag 110.
3. Inhalt der `.ft`-Archive und ihre Zuordnung zu Modulen: ungeprüft (nur nach Dateinamen).
4. Aufteilung der Rechte zwischen Hersteller und Dienstleister (Quellen 1, 2 und 4): ungeprüft; Gegenstand der Anfrage.
5. Zweig `docs` von Quelle 2: ungeprüft.
6. Stand der Dateien ohne Datum im Namen (Tabelle Nr. 1, 4, 6, 9, 12, 14, 17–20, A2, A3): ungeprüft, bis Auftrag 110 die Titelblätter liest.
7. Urheber- oder Lizenzvermerke in den nicht geöffneten Dateien (alle außer Nr. 2, 8, 10): ungeprüft.
8. Texte der Shop-AGB und der B2B-AGB: ungeprüft.
9. Artikelnummern der Add-ons FTS und Brennofen: ungeprüft.
10. Raspberry-Pi-Abbild: Softwarestand, Inhalt, Lizenzen und Rechteinhaber ungeprüft; keine Prüfsumme des Herstellers.
11. Nutzungsbedingungen von GitHub (was bei öffentlichen Repositories ohne Lizenz gilt): hier nicht am Original nachgelesen, ungeprüft.
