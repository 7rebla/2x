# Beschreibung der Testfabrik

Stand: 21.11.2026 · Auftrag 106 · selbst verfasst.

## Was die Testfabrik darstellt

Die Testfabrik ist der Betrieb, an dem 2x entwickelt und geprüft wird: ein kleiner Standort mit einer Fertigungslinie, einer Roboterzelle und einem Übergang zwischen Anlagennetz und Büronetz. Sie besteht nur aus Geräten, die es wirklich gibt, mit öffentlicher Dokumentation des Herstellers und echter Konfiguration.

Die Testfabrik ist kein Aufbau aus Hardware. Sie ist eine Sammlung von Unterlagen und Konfigurationen echter Produkte, dazu diese Beschreibung, die Geräteliste und der Netzplan.

| Datei | Inhalt |
| --- | --- |
| `devices.csv` | Geräteliste: Standort, Bereich, Anlage, Gerät, Modell, Softwarestand, Adresse mit Fundstelle, Protokolle |
| `network-plan.md` | Netze, Adressen, Dienste und Ports mit Fundstelle je Zeile; Widersprüche in den Quellen |
| `description.md` | diese Beschreibung |

## Aufbau

Standort **Testfabrik** mit drei Bereichen:

| Bereich | Anlage (Kennung) | Geräte (Kennung) |
| --- | --- | --- |
| Fertigungslinie | Wareneingang und -ausgang (`aps-dps`) | `dps-plc`, `dps-txt` |
| Fertigungslinie | Hochregallager (`aps-hbw`) | `hbw-plc` |
| Fertigungslinie | Bohrstation (`aps-drill`) | `drill-plc` |
| Fertigungslinie | Frässtation (`aps-mill`) | `mill-plc` |
| Fertigungslinie | Qualitätssicherung (`aps-aiqs`) | `aiqs-plc`, `aiqs-txt` |
| Fertigungslinie | Transportfahrzeug (`aps-agv`) | `agv-txt` |
| Fertigungslinie | Ladestation (`aps-charging`) | keines belegt |
| Fertigungslinie | Zentralsteuerung und Netz (`aps-core`) | `ccu-rpi`, `aps-router`, `cgw-txt` |
| Roboterzelle | Roboterzelle UR5e (`ur5e-cell`) | `ur5e` |
| Netzübergang | Firewall zwischen Büronetz und Anlagennetz (`it-ot-firewall`) | `opnsense-fw` |

Das sind zehn Anlagen und dreizehn Geräte.

- **Fertigungslinie:** die Lernfabrik „Agile Production Simulation 24V“ von fischertechnik (Art.-Nr. 569289). Fünf Module haben eine Siemens-SPS mit OPC-UA-Server, zwei davon zusätzlich einen TXT-4.0-Controller. Das Transportfahrzeug und das Cloud-Gateway laufen auf je einem TXT 4.0. Ein Raspberry Pi 4B ist die Zentralsteuerung mit MQTT-Broker und Node-RED; ein Router von TP-Link baut das Netz auf.
- **Roboterzelle:** ein Universal Robots UR5e (e-Series, PolyScope 5), Softwarestand 5.25.1. Lauffähig ist er über den Simulator URSim des Herstellers.
- **Netzübergang:** eine Firewall OPNsense als virtuelle Maschine. Sie trennt das Anlagennetz (Fertigungslinie, Roboterzelle) vom Büronetz.

## Was erdacht ist

Nur die Zusammenstellung:

- dass diese Anlagen gemeinsam an einem Standort „Testfabrik“ stehen,
- die Einteilung in Bereiche und Anlagen und die Kennungen in der Geräteliste,
- dass eine OPNsense das Anlagennetz vom Büronetz trennt,
- die Zuordnung von Zentralsteuerung, Router und Cloud-Gateway zur Sammel-Anlage „Zentralsteuerung und Netz“. Laut Handbuch stehen alle drei auf der Grundplatte des Wareneingangs und -ausgangs (PDF-S. 3, 17 und 32); die Sammel-Anlage fasst sie nach ihrer Aufgabe zusammen.

## Was echt ist

- Jedes Gerät ist ein benennbares Produkt. Modell, Adresse, Port und Protokoll stehen so in den Unterlagen des Herstellers; die Fundstelle steht in der Geräteliste und im Netzplan.
- Die Unterlagen sind beim Hersteller öffentlich abrufbar. Quelle, Stand und Prüfsumme je Unterlage führt das Manifest.
- Die Konfigurationen stammen vom Hersteller (Node-RED-Flows, Mosquitto-Konfiguration, Compose-Dateien, SPS-Projektarchive, Programme der TXT-Controller) oder entstehen in T2 in der Originalsoftware (URSim, OPNsense). Keine Konfiguration wird von Hand ausgedacht.

## Was offen ist

Was die Quellen nicht hergeben, bleibt leer oder „offen“:

- Adressen der Roboterzelle, der Firewall und des Büronetzes (kommen in T2 aus den echten Konfigurationen), ebenso der Softwarestand der Firewall,
- Adressen der vier TXT 4.0 (keine feste Adresse in den Unterlagen),
- genaue CPU und Firmware der SPS, Firmware der TXT 4.0, Betriebssystem der Zentralsteuerung, Hardware-Version und Firmware des Routers,
- ein Steuergerät der Ladestation: Die Unterlagen belegen keines, deshalb führt die Geräteliste die Ladestation als Anlage ohne Gerät.

## Grenzen

- **Lernmodell.** Die Fertigungslinie ist eine Lernfabrik, keine Produktionsanlage. Steuerungen, Protokolle und Unterlagen sind aber die echten.
- **SPS-Projekte.** Die Projektarchive sind nur mit TIA Portal V18 lesbar (Handbuch PDF-S. 34; Repository 1 `README.md` Zeile 47). Ohne TIA Portal werden sie nur als Datei geführt; ihr Inhalt ist nicht geprüft.
- **Keine Simulation der Module.** Die Zentralsteuerung lässt sich ohne Hardware lokal starten; die Module werden dabei nicht simuliert, ihre MQTT-Nachrichten müssten von Hand eingespielt werden (Dev `README.md` Zeile 334). Die Testfabrik startet die Zentralsteuerung in T1 und T2 nicht.
- **Widersprüche in den Unterlagen.** Die Unterlagen widersprechen sich an zwei Stellen (Adressen der SPS, CPU der Modulsteuerungen). Der Netzplan nennt beide Fundstellen und löst nichts auf.
- **Lizenzlage.** Die Quellen von fischertechnik tragen keine Lizenz. Es gilt: laden ja, weitergeben nein. Im Repository stehen deshalb nur eigene Beschreibungen und Fundstellen, keine Herstellerdateien. Einzelheiten: `docs/testfabrik/quellen-fertigungslinie.md`.
- **Zugangsdaten.** Die Unterlagen nennen Standard-Zugangsdaten des Auslieferungsstands. Sie stehen in keiner Datei der Testfabrik.

## Nicht aufgenommen

- **Zusatzmodul Brennofen (OVEN):** nicht Teil der Art.-Nr. 569289. Sein Adressblock und sein OPC-UA-Endpunkt kommen in den Quellen vor (Handbuch PDF-S. 38; `flows.json` Zeile 1369), das Modul steht aber nicht in der Testfabrik.
- **Zusatzpaket weiteres Transportfahrzeug (Add-on FTS):** Die Testfabrik hat ein Fahrzeug.
- **fischertechnik Cloud:** ein Dienst außerhalb der Testfabrik, kein Gerät. Das Cloud-Gateway `cgw-txt` ist als Gerät aufgenommen.
- **Raspberry-Pi-Abbild der Zentralsteuerung:** wird nur als Verweis geführt und nicht geladen.

## Verweise

- Manifest der Unterlagen: `testfactory/manifest.yaml` (Quelle, Softwarestand, Prüfsumme, Nutzungshinweis, zugeordnetes Gerät; die Zuordnung verwendet die Kennungen der Geräteliste).
- Quellen und Lizenzlage der Fertigungslinie: `docs/testfabrik/quellen-fertigungslinie.md`.
- Die Spalten von `devices.csv` sind ein Vorschlag aus Sicht der Testfabrik. Sie legen kein Datenmodell der Anwendung fest.
