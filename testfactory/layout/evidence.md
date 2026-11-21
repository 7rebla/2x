# Nachweis der drei Bedingungen je Anlage und Gerät

Stand: 21.11.2026 · Auftrag 113 · selbst verfasst. Grundlage für a7s Abnahme von T1; die Abnahme selbst nimmt a7 vor.

Die drei Bedingungen (Startunterlage Abschnitt 10.1, hier in eigenen Worten):

1. **Es gibt sie wirklich:** Hersteller, Produkt bzw. Modell und ein Softwarestand sind mit Fundstelle benannt.
2. **Die Dokumentation ist öffentlich und passt:** Die Unterlage des Herstellers ist ohne Anmeldung abrufbar, und ihr Stand passt nachweislich zum Softwarestand.
3. **Die Konfiguration ist echt:** Sie stammt als Datei vom Hersteller oder entsteht in der Originalsoftware; nichts ist von Hand ausgedacht.

Statuswerte (Auftrag 113, Fragen 1 bis 3, entschieden nach E-23):

- `erfüllt` – mit Beleg nachgewiesen.
- `offen` – nicht oder nicht vollständig belegt; die Anmerkung sagt, was zur Klärung fehlt.
- `folgt in T2` – entsteht erst mit der Originalsoftware in T2 (nur `ur5e`, `opnsense-fw` und ihre Anlagen).

## Zusammenfassung

Zeilen je Bereich und Status (je Kennung drei Zeilen, Anlagen und Geräte zusammen):

| Bereich | Zeilen | erfüllt | offen | folgt in T2 |
| --- | ---: | ---: | ---: | ---: |
| Fertigungslinie | 57 | 33 | 24 | 0 |
| Roboterzelle | 6 | 4 | 0 | 2 |
| Netzübergang | 6 | 0 | 0 | 6 |
| Gesamt | 69 | 37 | 24 | 8 |

Kurz: Die Roboterzelle ist bis auf die Konfiguration (T2) nachgewiesen. Die Fertigungslinie erfüllt Bedingung 1 bis auf den Router und Bedingung 3 bis auf Router und Ladestation; Bedingung 2 ist für keine ihrer Anlagen und keines ihrer Geräte nachgewiesen. Die Firewall folgt vollständig in T2.

### Offene Punkte (Entscheidungsvorlage für a7)

| Nr. | Punkt | betroffene Zeilen | was zur Klärung fehlt |
| ---: | --- | --- | --- |
| O-1 | Die Unterlagen von fischertechnik nennen keinen APS-Softwarestand. Ihre Passung zu APS 1.3.0 ist ungeprüft (Manifest, `version_source` aller 16 Einträge). Handbuch (02/2025) und Fehlersuche (03.02.2025) sind jünger als der Eintrag zu 1.3.0 im Update-Blog (09.01.2025); das ist nur ein zeitlicher Hinweis, kein Beleg. | Bedingung 2 aller Anlagen der Fertigungslinie; mittelbar aller ihrer Geräte | eine Angabe des Herstellers, zu welchem Softwarestand die Unterlagen gehören (Anfrage, siehe `docs/testfabrik/anfrage-fischertechnik-entwurf.md`), oder a7s Entscheidung, den zeitlichen Hinweis gelten zu lassen |
| O-2 | CPU-Typ und Firmware der fünf SPS sind unbekannt (Projektarchive nur mit TIA Portal V18 lesbar; Handbuch nennt S7-1200 und an einer Stelle zugleich CPU 1512SP). Damit ist offen, ob das S7-1200-Systemhandbuch V4.6 passt; es ist zudem nicht geladen (E-27). | Bedingung 2 von `dps-plc`, `hbw-plc`, `drill-plc`, `mill-plc`, `aiqs-plc` | Archive mit TIA Portal V18 öffnen (U-01), Zuordnung TIA V18 zu Firmware V4.6 an einer Siemens-Quelle prüfen (U-02), Handbuch von Hand laden (E-23, Frage 1 Antwort A) |
| O-3 | Firmware der vier TXT 4.0 unbekannt; im Manifest gibt es keine Unterlage des Herstellers zum TXT 4.0 selbst. | Bedingung 2 von `dps-txt`, `aiqs-txt`, `agv-txt`, `cgw-txt` | Firmware des Release-Stands 1.3.0 (laut Software-Versionen-PDF im Update-Blog-Eintrag genannt; der Blog ist nicht geladen) und eine Unterlage zum TXT 4.0 dieses Stands |
| O-4 | Raspberry-Pi-Abbild nur als Verweis, nie geladen: Betriebssystem und gebaute Zentralsteuerung ungeprüft; die Datei (25.09.2024) ist älter als Tag v1.3.0 (25.10.2024). | Bedingung 2 von `ccu-rpi` | Abbild prüfen (Stand von Betriebssystem und Zentralsteuerung) oder a7s Festlegung, dass die Zentralsteuerung nur über das Dev-Repository geführt wird |
| O-5 | Router: Hardwarestand nur indirekt (Handbuch verweist auf die Anleitung V3), Firmware unbekannt, keine Konfigurationsdatei des Herstellers. | alle drei Bedingungen von `aps-router`; dadurch Bedingung 1 bis 3 von `aps-core` | Typenschild des verbauten Geräts (Hardwarestand, Firmware); Bedingung 3 bleibt nach E-23 (Frage 3 Antwort A) offen, die Konfiguration gibt es nur am echten Gerät |
| O-6 | Ladestation: kein eigenes Steuergerät belegt, keine Konfigurationsdatei. | Bedingung 3 von `aps-charging` (Bedingung 2 über O-1) | nach E-23 (Frage 3 Antwort A) offen; Klärung nur am echten Gerät |
| T-1 | UR5e: Installationsdatei, Programme und URScript entstehen erst in URSim. | Bedingung 3 von `ur5e` und `ur5e-cell` | T2: URSim `ursim-e-series` (Tag 5.25.1, festgelegter Digest) starten und die Konfiguration erzeugen |
| T-2 | OPNsense: Softwarestand, Passung der Dokumentation und `config.xml` entstehen erst in T2. | alle drei Bedingungen von `opnsense-fw` und `it-ot-firewall` | T2: Softwarestand festlegen, Firewall als virtuelle Maschine aufsetzen, `config.xml` erzeugen |

Als geklärt vermerkt (mit Beleg in der Tabelle): `ccu-rpi` Bedingung 3 (Dateien des Dev-Repositorys am festen Commit) und die TXT-Controller Bedingung 3 (Programme als `.ft`-Dateien des Herstellers; die fehlende feste Adresse betrifft die Geräteliste, nicht die Herkunft der Konfiguration).

## Regeln der Bewertung

- **Bedingung 1** ist `erfüllt`, wenn Hersteller, Produkt bzw. Modell und ein Softwarestand mit Fundstelle belegt sind. Für die Fertigungslinie gilt als Softwarestand der Release-Stand APS 1.3.0 mit der Version des jeweiligen Programms im Repository: Der Hersteller fasst die Stände von Zentralsteuerung, SPS-Programmen und TXT-Controllern zu einem Release-Stand zusammen (`aps-software-versions-de` PDF-S. 1). Unbekannte Einzelwerte (Firmware, Abbild) stehen in der Anmerkung und wirken bei Bedingung 2.
- **Bedingung 2** ist `erfüllt`, wenn (a) die Unterlage im Manifest steht, ohne Anmeldung abrufbar ist (`fetch: auto`, Nutzungshinweis im Manifest) und `fetch --verify` sie am 21.11.2026 bestätigt hat, und (b) ihr Stand nachweislich zum Softwarestand passt: gleicher Versionsvermerk in der Unterlage oder derselbe feste Commit wie die Software; bei reinen Hardware-Unterlagen dasselbe Modell. Hängt die Passung an einem unbekannten Wert (Firmware, CPU, Abbild, Hardwarestand), ist sie `offen`.
- **Bedingung 3** ist `erfüllt`, wenn die Konfiguration als Datei des Herstellers auf einem festen Commit im Manifest steht und dem Gerät zugeordnet ist. Die Zuordnung der SPS-Archive und TXT-Programme folgt den Dateinamen (Manifest `aps-repository`, `notes`); ihr Inhalt ist nicht geprüft.
- **Anlagen** mit Geräten: `erfüllt` nur, wenn alle Geräte die Bedingung erfüllen; sonst `offen`, wenn ein Gerät `offen` ist, sonst `folgt in T2`. Der Beleg nennt die Geräte.
- **Fundstellen:** „PDF-S.“ ist der Seitenindex der Datei (ab 1), „Zeile“ die Zeile der Datei am festen Commit des Manifest-Eintrags. Alle genannten Seiten und Zeilen wurden am 21.11.2026 an den geladenen Dateien nachgesehen (Auftrag 113), soweit die Anmerkung nichts anderes sagt. Kein Text der Hersteller ist übernommen.

## Produktnachweis APS 24V (gemeinsamer Beleg der Fertigungslinie)

Die Zeilen der Fertigungslinie verweisen hierher („Produktnachweis APS“).

- **Produkt:** fischertechnik Agile Production Simulation 24V, Art.-Nr. 569289 – `aps-software-versions-de` PDF-S. 1 und `aps-software-update-de` PDF-S. 1 (Überschrift mit Artikelnummer); Produktseite mit der Nummer in der Adresse: `aps-repository` `README.md` Zeile 5, `aps-repository-dev` `docs/README.md` Zeile 9.
- **Handbuch:** `aps-documentation-de` PDF-S. 1 (Titelblatt: Version 4, Model revision 1.x, 02/2025). Lieferumfang mit sechs Modulen, darunter die Ladestation, sowie Raspberry Pi 4B und WLAN-Router am Wareneingang und -ausgang: PDF-S. 3–4. Steuerungen (TXT 4.0, SPS S7-1200, Raspberry Pi mit MQTT-Broker und Node-RED, Router von TP-Link): PDF-S. 36. Vier TXT 4.0: PDF-S. 15.
- **Softwarestand APS 1.3.0:** `aps-repository-dev` am Commit `24568073…` – `package.json` Zeile 3 und `central-control/package.json` Zeile 3 nennen 1.3.0. `aps-repository` am Commit `b8082e16…`, vier Commits nach Tag v1.3.0 (Manifest `version_source`). Eintrag „APS-24V v1.3.0“ vom 09.01.2025 im Update-Blog laut Manifest (`software_version` der Unterlagen; der Blog ist nicht geladen).
- **Release-Stand:** `aps-software-versions-de` PDF-S. 1 beschreibt, dass zu einem Softwarestand die passenden Versionen von Zentralsteuerung, SPS-Programmen und TXT-Controllern (Firmware und Programme) gehören.
- **Abruf ohne Anmeldung:** alle 16 Unterlagen und beide Repositories mit `fetch: auto`; Nutzungshinweis im Manifest (`terms.note`: frei abrufbar ohne Anmeldung); `fetch --verify` am 21.11.2026: 26 ok.
- **Passung der Unterlagen:** ungeprüft, siehe O-1. Die Dateien der beiden Repositories gehören dagegen zum selben festen Commit wie die Software; die MQTT-Beschreibung im Dev-Repository trägt die Dokumentversion 1.0 vom Dezember 2025 (`docs/11-appendices.md` Zeile 332).

## Nachweis

| id | bedingung | status | beleg | anmerkung |
| --- | --- | --- | --- | --- |
| aps-dps | 1 | erfüllt | Geräte `dps-plc`, `dps-txt`; Produktnachweis APS; `aps-documentation-de` PDF-S. 3 (Modul 1 im Lieferumfang) | |
| aps-dps | 2 | offen | Geräte `dps-plc`, `dps-txt` | Beide Geräte offen (O-1, O-2, O-3). |
| aps-dps | 3 | erfüllt | Geräte `dps-plc`, `dps-txt` | |
| dps-plc | 1 | erfüllt | Produktnachweis APS; `aps-documentation-de` PDF-S. 36 (SPS S7-1200); `aps-repository` `PLC-programs/S7_1200_TIAv18/DPSv1_6_0.zap18` (Programmstand DPS 1.6.0 laut Dateiname) | Modell nur als Reihe S7-1200 belegt; PDF-S. 34 nennt zugleich eine CPU 1512SP (Widerspruch bleibt Prüfstoff). Genaue CPU und Firmware offen, siehe Bedingung 2. |
| dps-plc | 2 | offen | `siemens-s7-1200-system-manual-v4-6-de` (fetch manual, nicht geladen); `siemens-s7-1200-system-manual-v4-7-de` (nur Verweis); `aps-change-ip-address-de` PDF-S. 2 (TIA Portal V18) | O-2: CPU-Typ und Firmware unbekannt (U-01, U-02), Handbuch nach E-27 nicht geladen; E-23 Frage 1 Antwort A. Außerdem O-1. |
| dps-plc | 3 | erfüllt | `aps-repository` `PLC-programs/S7_1200_TIAv18/DPSv1_6_0.zap18`; `README.md` Zeile 19 (Projektarchive der Module) und Zeile 47 (TIA Portal V18) | Projektarchiv des Herstellers am festen Commit; Inhalt nur mit TIA Portal V18 lesbar und nicht geprüft; Zuordnung nach Dateiname. |
| dps-txt | 1 | erfüllt | Produktnachweis APS; `aps-documentation-de` PDF-S. 15 (vier TXT 4.0) und PDF-S. 36; `aps-repository` `TXT4.0-programs/FF_DPS_24V.ft` | Softwarestand: Programm des Release-Stands APS 1.3.0; Firmware des Controllers offen (O-3). |
| dps-txt | 2 | offen | `aps-documentation-de` (Passung zu 1.3.0 ungeprüft); `aps-repository-dev` `docs/06-modules/dps.md` (Modulschnittstelle, Stand 1.3.0) | O-3: Firmware unbekannt, keine Unterlage zum TXT 4.0 im Manifest. O-1. |
| dps-txt | 3 | erfüllt | `aps-repository` `TXT4.0-programs/FF_DPS_24V.ft`; `README.md` Zeile 23 (Projektdateien der vier TXT) | Geklärt: Konfiguration ist das Programm des Herstellers als `.ft`-Datei (ROBO-Pro-Coding-Projekt) am festen Commit; Zuordnung nach Dateiname. Keine feste Adresse (`aps-documentation-de` PDF-S. 38 nur 192.168.0.x); das betrifft die Geräteliste, nicht die Herkunft. |
| aps-hbw | 1 | erfüllt | Gerät `hbw-plc`; Produktnachweis APS; `aps-documentation-de` PDF-S. 3 (Modul 2) | |
| aps-hbw | 2 | offen | Gerät `hbw-plc` | Gerät offen (O-2, O-1). |
| aps-hbw | 3 | erfüllt | Gerät `hbw-plc` | |
| hbw-plc | 1 | erfüllt | Produktnachweis APS; `aps-documentation-de` PDF-S. 36; `aps-repository` `PLC-programs/S7_1200_TIAv18/HBWv1_3_0.zap18` | Wie `dps-plc`: Reihe S7-1200 belegt, CPU-Widerspruch PDF-S. 34, CPU und Firmware offen. |
| hbw-plc | 2 | offen | `siemens-s7-1200-system-manual-v4-6-de` (nicht geladen); `aps-change-ip-address-de` PDF-S. 2 | O-2 (U-01, U-02, E-27; E-23 Frage 1 Antwort A). O-1. |
| hbw-plc | 3 | erfüllt | `aps-repository` `PLC-programs/S7_1200_TIAv18/HBWv1_3_0.zap18`; `README.md` Zeile 19 und 47 | Wie `dps-plc`: Archiv des Herstellers, Inhalt ungeprüft, Zuordnung nach Dateiname. |
| aps-drill | 1 | erfüllt | Gerät `drill-plc`; Produktnachweis APS; `aps-documentation-de` PDF-S. 4 (Modul 3) | |
| aps-drill | 2 | offen | Gerät `drill-plc` | Gerät offen (O-2, O-1). |
| aps-drill | 3 | erfüllt | Gerät `drill-plc` | |
| drill-plc | 1 | erfüllt | Produktnachweis APS; `aps-documentation-de` PDF-S. 36; `aps-repository` `PLC-programs/S7_1200_TIAv18/DRILLv1_3_0.zap18` | Wie `dps-plc`: Reihe S7-1200 belegt, CPU-Widerspruch PDF-S. 34, CPU und Firmware offen. |
| drill-plc | 2 | offen | `siemens-s7-1200-system-manual-v4-6-de` (nicht geladen); `aps-change-ip-address-de` PDF-S. 2 | O-2 (U-01, U-02, E-27; E-23 Frage 1 Antwort A). O-1. |
| drill-plc | 3 | erfüllt | `aps-repository` `PLC-programs/S7_1200_TIAv18/DRILLv1_3_0.zap18`; `README.md` Zeile 19 und 47 | Wie `dps-plc`: Archiv des Herstellers, Inhalt ungeprüft, Zuordnung nach Dateiname. |
| aps-mill | 1 | erfüllt | Gerät `mill-plc`; Produktnachweis APS; `aps-documentation-de` PDF-S. 4 (Modul 4) | |
| aps-mill | 2 | offen | Gerät `mill-plc` | Gerät offen (O-2, O-1). |
| aps-mill | 3 | erfüllt | Gerät `mill-plc` | |
| mill-plc | 1 | erfüllt | Produktnachweis APS; `aps-documentation-de` PDF-S. 36; `aps-repository` `PLC-programs/S7_1200_TIAv18/MILLv1_3_0.zap18` | Wie `dps-plc`: Reihe S7-1200 belegt, CPU-Widerspruch PDF-S. 34, CPU und Firmware offen. Die Übungslösung im Ordner `exercises` ist nicht gemeint. |
| mill-plc | 2 | offen | `siemens-s7-1200-system-manual-v4-6-de` (nicht geladen); `aps-change-ip-address-de` PDF-S. 2 | O-2 (U-01, U-02, E-27; E-23 Frage 1 Antwort A). O-1. |
| mill-plc | 3 | erfüllt | `aps-repository` `PLC-programs/S7_1200_TIAv18/MILLv1_3_0.zap18`; `README.md` Zeile 19 und 47 | Wie `dps-plc`: Archiv des Herstellers, Inhalt ungeprüft, Zuordnung nach Dateiname. |
| aps-aiqs | 1 | erfüllt | Geräte `aiqs-plc`, `aiqs-txt`; Produktnachweis APS; `aps-documentation-de` PDF-S. 4 (Modul 5) | |
| aps-aiqs | 2 | offen | Geräte `aiqs-plc`, `aiqs-txt` | Beide Geräte offen (O-1, O-2, O-3). |
| aps-aiqs | 3 | erfüllt | Geräte `aiqs-plc`, `aiqs-txt` | |
| aiqs-plc | 1 | erfüllt | Produktnachweis APS; `aps-documentation-de` PDF-S. 36; `aps-repository` `PLC-programs/S7_1200_TIAv18/AIQSv1_3_0.zap18` | Wie `dps-plc`: Reihe S7-1200 belegt, CPU-Widerspruch PDF-S. 34, CPU und Firmware offen. |
| aiqs-plc | 2 | offen | `siemens-s7-1200-system-manual-v4-6-de` (nicht geladen); `aps-change-ip-address-de` PDF-S. 2 | O-2 (U-01, U-02, E-27; E-23 Frage 1 Antwort A). O-1. |
| aiqs-plc | 3 | erfüllt | `aps-repository` `PLC-programs/S7_1200_TIAv18/AIQSv1_3_0.zap18`; `README.md` Zeile 19 und 47 | Wie `dps-plc`: Archiv des Herstellers, Inhalt ungeprüft, Zuordnung nach Dateiname. |
| aiqs-txt | 1 | erfüllt | Produktnachweis APS; `aps-documentation-de` PDF-S. 15 und 36; `aps-repository` `TXT4.0-programs/FF_AI_24V.ft` | Softwarestand: Programm des Release-Stands APS 1.3.0; Firmware offen (O-3). |
| aiqs-txt | 2 | offen | `aps-documentation-de` (Passung ungeprüft); `aps-repository-dev` `docs/06-modules/aiqs.md` | O-3: Firmware unbekannt, keine Unterlage zum TXT 4.0 im Manifest. O-1. |
| aiqs-txt | 3 | erfüllt | `aps-repository` `TXT4.0-programs/FF_AI_24V.ft`; `README.md` Zeile 23 | Geklärt wie `dps-txt`: Programm des Herstellers als `.ft`-Datei; keine feste Adresse (betrifft die Geräteliste). |
| aps-agv | 1 | erfüllt | Gerät `agv-txt`; Produktnachweis APS; `aps-documentation-de` PDF-S. 3 (Fahrerloses Transportsystem) | |
| aps-agv | 2 | offen | Gerät `agv-txt` | Gerät offen (O-3, O-1). |
| aps-agv | 3 | erfüllt | Gerät `agv-txt` | |
| agv-txt | 1 | erfüllt | Produktnachweis APS; `aps-documentation-de` PDF-S. 15 und 17 (TXT 4.0 am Fahrzeug); `aps-repository` `TXT4.0-programs/fts_main.ft` | Softwarestand: Programm des Release-Stands APS 1.3.0; Firmware offen (O-3). |
| agv-txt | 2 | offen | `aps-documentation-de` (Passung ungeprüft); `aps-repository-dev` `docs/06-modules/agv.md` | O-3: Firmware unbekannt, keine Unterlage zum TXT 4.0 im Manifest. O-1. |
| agv-txt | 3 | erfüllt | `aps-repository` `TXT4.0-programs/fts_main.ft`; `README.md` Zeile 23 | Geklärt wie `dps-txt`: Programm des Herstellers als `.ft`-Datei; keine feste Adresse (betrifft die Geräteliste). |
| aps-charging | 1 | erfüllt | Produktnachweis APS; `aps-documentation-de` PDF-S. 4 (Modul 6 Ladestation), PDF-S. 11 und 17; `aps-repository-dev` `docs/11-appendices.md` Zeile 184 (Modultyp CHRG) | Anlage ohne Gerät: Belegt ist das Modul als Teil der APS 569289; ein eigenes Steuergerät ist nicht belegt, ein eigener Softwarestand daher nicht anwendbar (Stand der APS: 1.3.0). |
| aps-charging | 2 | offen | `aps-documentation-de` PDF-S. 4, 11 und 17; `aps-documentation-en` | O-1: Passung der Unterlagen zu APS 1.3.0 ungeprüft. |
| aps-charging | 3 | offen | Geräteliste `devices.csv` Zeile 10 (kein Gerät angelegt) | O-6: keine Herstellerdatei; Konfiguration nur am echten Gerät. Laut Geräteliste kein Steuergerät (Handbuch PDF-S. 11, 17, 36). E-23 Frage 3 Antwort A. |
| aps-core | 1 | offen | Geräte `ccu-rpi`, `aps-router`, `cgw-txt` | `aps-router` offen (O-5); `ccu-rpi` und `cgw-txt` erfüllt. |
| aps-core | 2 | offen | Geräte `ccu-rpi`, `aps-router`, `cgw-txt` | Alle drei Geräte offen (O-1, O-3, O-4, O-5). |
| aps-core | 3 | offen | Geräte `ccu-rpi`, `aps-router`, `cgw-txt` | `aps-router` offen (O-5); `ccu-rpi` und `cgw-txt` erfüllt. |
| cgw-txt | 1 | erfüllt | Produktnachweis APS; `aps-documentation-de` PDF-S. 32 (weiterer TXT 4.0 am Wareneingang und -ausgang); `aps-repository` `TXT4.0-programs/FF_CGW.ft` | Softwarestand: Programm des Release-Stands APS 1.3.0; Firmware offen (O-3). |
| cgw-txt | 2 | offen | `aps-documentation-de` PDF-S. 32 und 37 (Passung ungeprüft); `aps-repository-dev` `docs/06-modules/cgw.md` | O-3: Firmware unbekannt, keine Unterlage zum TXT 4.0 im Manifest. O-1. |
| cgw-txt | 3 | erfüllt | `aps-repository` `TXT4.0-programs/FF_CGW.ft`; `README.md` Zeile 23 | Geklärt wie `dps-txt`: Programm des Herstellers als `.ft`-Datei; keine feste Adresse (betrifft die Geräteliste). |
| ccu-rpi | 1 | erfüllt | `aps-documentation-de` PDF-S. 3 (Raspberry Pi 4B) und PDF-S. 36 (Zentralsteuerung); `rpi4b-datasheet-en` PDF-S. 1 (Raspberry Pi 4 Model B); `aps-repository-dev` `package.json` Zeile 3 und `central-control/package.json` Zeile 3 (1.3.0) | Softwarestand: Zentralsteuerung APS 1.3.0. Stand von Abbild und Betriebssystem ungeprüft, siehe Bedingung 2. |
| ccu-rpi | 2 | offen | `aps-repository-dev` `docs/README.md` und `docs/11-appendices.md` Zeile 332 (MQTT-Beschreibung 1.0, gleicher Commit wie 1.3.0); `rpi4b-datasheet-en` PDF-S. 1 (Release 1.1, Hardware); `aps-rpi-image` (nur Verweis); `rpi-documentation` (nur Verweis) | Belegt: Dev-Dokumentation am selben Commit wie die Zentralsteuerung 1.3.0, Datenblatt zum Modell 4B. Offen (O-4): Betriebssystem und Inhalt des Abbilds ungeprüft, Abbild älter als Tag v1.3.0; die Online-Dokumentation ist nur Verweis ohne Softwarestand. |
| ccu-rpi | 3 | erfüllt | `aps-repository-dev` am Commit `24568073…`: `nodeRed/flows.json`, `mosquitto/config/mosquitto.conf`, `raspberrypi/fischer-techik.service`, `docker-compose.yml`, `docker-compose-prod.yml`; `aps-repository` `Node-RED/flows.json` (bytegleich) | Geklärt: Als Konfiguration zählen die Dateien des Dev-Repositorys am festen Commit; das Abbild `aps-rpi-image` ist nur Verweis und wird nicht geladen. |
| aps-router | 1 | offen | `aps-documentation-de` PDF-S. 31 und 38 (TL-WR902AC); `tl-wr902ac-user-guide-v3-en` PDF-S. 1 (REV3.0.0) | O-5: Modell belegt; verbauter Hardwarestand nur indirekt (Handbuch PDF-S. 31 verweist auf die Anleitung V3, U-05); Firmware unbekannt, kein Softwarestand in der Geräteliste. |
| aps-router | 2 | offen | `tl-wr902ac-user-guide-v3-en` PDF-S. 1 (REV3.0.0, Hardwarestand V3) | O-5: Anleitung öffentlich ohne Anmeldung; Passung zum verbauten Gerät hängt am Hardwarestand und an der Firmware. |
| aps-router | 3 | offen | keine Herstellerdatei im Manifest | O-5: keine Herstellerdatei; Konfiguration nur am echten Gerät. E-23 Frage 3 Antwort A. |
| ur5e-cell | 1 | erfüllt | Gerät `ur5e` | |
| ur5e-cell | 2 | erfüllt | Gerät `ur5e` | |
| ur5e-cell | 3 | folgt in T2 | Gerät `ur5e` | T-1: Konfiguration entsteht in T2 in URSim. |
| ur5e | 1 | erfüllt | `ur5e-user-manual-de` PDF-S. 1 (UR5e, PolyScope 5) und PDF-S. 266 (Softwareversion 5.25.1); `ursim-e-series` (Tag 5.25.1, Digest im Manifest) | Universal Robots UR5e (e-Series), PolyScope 5.25.1 (E-23). |
| ur5e | 2 | erfüllt | `ur5e-user-manual-de` PDF-S. 266; `ur5e-software-handbook-en` PDF-S. 1 und 255; `ur5e-script-directory-en` PDF-S. 1 und 178; `ur5e-service-manual-en` PDF-S. 1 und 124 | Alle vier Unterlagen nennen 5.25.1, gleich dem Stand des Simulators; ohne Anmeldung abrufbar (`fetch: auto`), `--verify` ok. |
| ur5e | 3 | folgt in T2 | `ursim-e-series` (Tag 5.25.1, festgelegter Digest; nicht geladen) | T-1: Installationsdatei, Programme und URScript entstehen erst in URSim (T2). Für erzeugte Dateien gilt der Arbeitsstand zu Frage 3 aus Auftrag 103. |
| it-ot-firewall | 1 | folgt in T2 | Gerät `opnsense-fw` | T-2: Softwarestand der Firewall wird in T2 festgelegt. |
| it-ot-firewall | 2 | folgt in T2 | Gerät `opnsense-fw` | T-2. |
| it-ot-firewall | 3 | folgt in T2 | Gerät `opnsense-fw` | T-2. |
| opnsense-fw | 1 | folgt in T2 | `opnsense-docs` (Projekt OPNsense, Dokumentation am festen Commit) | T-2: Produkt benannt; Softwarestand wird erst in T2 festgelegt (E-23, Frage 2 Antwort A). |
| opnsense-fw | 2 | folgt in T2 | `opnsense-docs` am Commit `953dd3d1…` (BSD-2-Clause, `fetch: auto`) | T-2: Dokumentation öffentlich und geladen, aber nicht je Softwarestand getaggt; die Passung entsteht erst mit dem in T2 festgelegten Stand. |
| opnsense-fw | 3 | folgt in T2 | keine Datei in T1 | T-2: `config.xml` entsteht in T2 aus der laufenden Firewall. |
