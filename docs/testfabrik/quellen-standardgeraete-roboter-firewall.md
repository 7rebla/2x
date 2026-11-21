# Quellen und Nutzungsbedingungen: Standardgeräte, Roboterzelle, Firewall-Dokumentation

Ergebnis von Auftrag 103 (Meilenstein T1). Grundlage für die Aufträge 107 (Manifest) und 108 (Testdaten).

**Abrufdatum aller Angaben: 21.11.2026**, soweit nicht anders vermerkt.

## Lesehilfe

- **Wie geprüft wurde:** Kopfzeilen-Abfragen (HTTP HEAD) ohne Anmeldung, Lesen der Lizenz- und Nutzungstexte an der Originaladresse, Metadaten-Abfragen bei Docker Hub, der Docker-Registry und GitHub. Für Siemens zusätzlich ein Abruf im Browser ohne Anmeldung. Es wurde kein Konto angelegt, nichts in den Projektordner geladen und keine Anfrage an einen Hersteller gesendet.
- **Größe** in Byte laut Kopfzeile `Content-Length`; **Stand** ist, wo nichts anderes steht, die Kopfzeile `Last-Modified`.
- **Lade-Art** für das Lade-Skript (Auftrag 104): `auto` = das Skript kann die Datei ohne Anmeldung per Direktadresse holen · `manual` = Abruf von Hand im Browser, das Skript prüft nur die Prüfsumme · `none` = nur Verweis, wird nicht geladen.
- **Folgerung** nennt immer drei Dinge: laden (in `testfactory/extern/`, ungetrackt) · weitergeben (an Dritte, in Bildern, Videos, Archiven) · einchecken (ins Repository).
- **Offene Punkte** tragen eine Nummer `U-nn` und stehen jeweils in genau einer Zeile. Die Suche aus dem Akzeptanzkriterium des Auftrags zeigt genau diese Zeilen.
- Die Befunde sind Lesebefunde, keine Rechtsberatung.

## Übersicht

| Quelle | Rechteinhaber | Lizenzlage in einem Satz | Abruf ohne Anmeldung | Lade-Art |
| --- | --- | --- | --- | --- |
| Siemens S7-1200 Systemhandbuch | Siemens | Herstellerunterlage; Nutzung nur für eigene Zwecke, Weitergabe untersagt, Klausel gegen Text- und Data-Mining | ja | V4.6: `auto` möglich · V4.7: `manual` |
| Raspberry Pi 4B – Online-Dokumentation | Raspberry Pi Ltd | CC BY-SA 4.0 (Werkzeuge BSD-3-Clause), Marken ausgenommen | ja | `none` (Verweis mit festem Commit) |
| Raspberry Pi 4B – Datenblatt, Product Brief, Schaltplan | Raspberry Pi Ltd | Herstellerunterlage, „All rights reserved“ bzw. kein Lizenzvermerk | ja | `auto` |
| TP-Link TL-WR902AC Anleitung V3 | TP-Link | Herstellerunterlage; nur persönlicher Gebrauch, Weitergabe nur mit Zustimmung | ja | `auto` |
| UR5e-Handbücher | Universal Robots A/S | Herstellerunterlage; Vervielfältigung nur mit schriftlicher Genehmigung | ja | `auto` |
| URSim-Image | Universal Robots A/S | keine Lizenzangabe am Image; die UR-EULA nennt URSim nicht | ja (Docker Hub, anonym) | `none` (Tag und Digest) |
| OPNsense-Dokumentation | Deciso B.V. und Mitwirkende | BSD-2-Clause; einige Bilder CC0; Logos ausgenommen | ja | `auto` (`git-archive` auf festem Commit) |

---

## 1. Siemens S7-1200 (Systemhandbuch)

**Rechteinhaber:** Siemens (Betreiber laut Impressum des jeweiligen Angebots).

### Unterlagen

| Ausgabe | Beitrag im Industry Online Support | Direktadresse der PDF-Datei | Größe (Byte) | Stand | Lade-Art |
| --- | --- | --- | --- | --- | --- |
| V4.7, 12/2024, A5E02486681-AQ (aktuell) | https://support.industry.siemens.com/cs/document/109977302/s7-1200-automatisierungssystem?lc=de-DE (Beitragsdatum 12.02.2026) | https://support.industry.siemens.com/cs/attachments/109977302/s71200_system_manual_de-DE.pdf | laut Seite 32.770 KB | 13.02.2026 | `manual` |
| V4.6, 11/2022, A5E02486681-AP | https://support.industry.siemens.com/cs/ww/de/view/109814829 (Beitragsdatum 13.10.2022) | https://cache.industry.siemens.com/dl/files/829/109814829/att_1120872/v1/s71200_system_manual_de-DE_de-DE.pdf | 36.472.132 | 15.11.2022 | `auto` möglich |
| Ausgabe 11/2019 | Beitrag 109772940 | https://cache.industry.siemens.com/dl/files/940/109772940/att_1002388/v1/s71200_system_manual_de-DE_de-DE.pdf | 23.264.287 | 12.11.2019 | `none` (Altstand) |
| Ausgabe 04/2012 (laut Vorbefund) | Beitrag 36932465 | https://cache.industry.siemens.com/dl/files/465/36932465/att_106116/v1/s71200_system_manual_de-DE_de-DE.pdf | 26.655.703 | 24.01.2015 | `none` (Altstand) |

Weitere Fundstellen, nur als Verweis (`none`):

- S7-1200 **G2** Systemhandbuch V4.1, 12/2025, A5E52923937-AC, Beitrag 109997791. Das ist eine andere Gerätereihe; die Projektarchive der Fertigungslinie (TIA Portal V18) betreffen die klassische S7-1200.
- Originalbetriebsanleitung S7-1200, 03/2024, A5E51784853-AD, Beitrag 109972031.

### Befund zum Abruf

- **Beitragsseiten** (`support.industry.siemens.com/cs/…`) antworten auf Abrufe ohne Browser mit HTTP 403. Im Browser öffnen sie sich **ohne Anmeldung**; die Schaltfläche „Anmelden“ bleibt ungenutzt.
- **V4.7 (aktuell):** Der PDF-Link der Seite lässt sich im Browser ohne Anmeldung abrufen (geprüft mit einem Teilabruf der ersten 1024 Byte, Antwort beginnt mit `%PDF`). Er löst auf `https://support.industry.siemens.com/dl/files/302/109977302/att_1307439/v2/s71200_system_manual_de-DE.pdf` auf. Diese Adresse antwortet ohne Browser mit HTTP 403; unter `cache.industry.siemens.com` gibt es sie nicht (HTTP 404). Folge: `manual`.
- **Siemens veröffentlicht für V4.7 selbst eine SHA-256-Prüfsumme** (Link „SHA-256“ neben dem Download): `51c1ec7508182ce4de6a1a715514702239fd5e1e21c8734f23202676d19a3ba2`. Auftrag 109 kann die von Hand geladene Datei dagegen prüfen.
- **V4.6 (11/2022):** Die Beitragsseite vermerkt, dass eine neuere Ausgabe verfügbar ist. Der PDF-Link löst im Browser auf die oben genannte Adresse unter `cache.industry.siemens.com` auf. Diese Adresse antwortet **auch ohne Browser** mit HTTP 200 (`application/pdf`). Folge: `auto` ist technisch möglich.
- Die Seite zu V4.7 bietet zusätzlich ein „Multimedia-Dokument“ als ZIP (29 MB) und eine Ansicht mit Kapitelstruktur an; beides wird nicht benötigt.

### Abweichungen vom Vorbefund

- Beitrag 109814829 ist die Ausgabe **V4.6 (11/2022)**, nicht V4.5. Beitrag 109772940 ist die Ausgabe 11/2019. Aktuell ist **V4.7 (12/2024)** unter Beitrag 109977302; dieser Beitrag fehlte im Vorbefund.
- Eine neuere Ausgabe als 04/2012 ist per Direktadresse ohne Anmeldung abrufbar (V4.6).

### Lizenzbefund

Fundstelle: https://www.siemens.com/global/en/general/terms-of-use.html , Abschnitt A „General Terms of Use“, Vermerk „Last updated: 29 October 2026“.

- **A.4.3:** einfaches, nicht übertragbares Nutzungsrecht an Informationen, Software und Dokumentation, nur für eigene geschäftliche Zwecke und im Rahmen des Zwecks, zu dem Siemens sie bereitstellt.
- **A.4.5:** Informationen, Software und Dokumentation dürfen nicht an Dritte weitergegeben, vermietet oder sonst zugänglich gemacht werden; die Dokumentation darf nicht verändert werden.
- **A.4.6:** Urheberrechtsschutz; Vermerke dürfen nicht entfernt werden.
- **A.5.1:** Inhalte dürfen ohne vorherige schriftliche Zustimmung nicht kopiert, vervielfältigt oder anderweitig verwendet werden.
- **A.6.2:** untersagt „text or data mining“, ausdrücklich auch automatisiertes Auslesen, Vervielfältigen oder Extrahieren von Inhalten zum Zweck der Analyse und für Entwicklung, Training oder Verbesserung von KI-Systemen. **Dieser Punkt ist neu gegenüber dem Vorbefund und betrifft den Zweck der Testfabrik** (Einlesen und Durchsuchen der Unterlage durch die Anwendung). Siehe neue Frage 2 im Auftrag.

### Folgerung

- **laden:** ja, für den eigenen Gebrauch; wegen A.6.2 vorerst **von Hand** (`manual`), bis a7 über die neue Frage 2 entschieden hat.
- **weitergeben:** nein (A.4.5).
- **einchecken:** nein. Auch keine Auszüge in Testdaten, Bildern oder Videos.

**Abruf ohne Anmeldung:** ja (V4.7 nur im Browser; V4.6 auch per Direktadresse).
**geprüft am:** 21.11.2026.

### Offene Punkte

- **U-01 (ungeprüft):** CPU-Typ und Firmware in den SPS-Projektarchiven der Fertigungslinie – nur mit TIA Portal lesbar; davon hängt ab, welche Handbuchausgabe passt.
- **U-02 (ungeprüft):** Zuordnung „TIA Portal V18 gehört zu Firmware V4.6“ – naheliegend, aber nicht an einer Siemens-Quelle nachgelesen.
- **U-03 (ungeprüft):** Titelblätter der Ausgaben 11/2019 und 04/2012 – Ausgabestand nur aus Vorbefund und Dateidatum, die Dateien wurden nicht geöffnet.
- **U-04 (ungeprüft):** Ob A.6.2 der Siemens-Nutzungsbedingungen das lokale Einlesen einer von Hand geladenen Unterlage erfasst – Rechtsfrage, Entscheidung bei a7.

---

## 2. Raspberry Pi 4B

**Rechteinhaber:** Raspberry Pi Ltd (in den PDFs: Raspberry Pi (Trading) Ltd.).

### 2.1 Online-Dokumentation

- **Adresse:** https://www.raspberrypi.com/documentation/computers/raspberry-pi.html
- **Quelle:** https://github.com/raspberrypi/documentation , Zweig `master`
- **Stand:** Commit `97485d9742bcd15765f208d8c01735d74d542650` vom 18.11.2026 (11:33 UTC); am 21.11.2026 weiterhin Spitze von `master` (`git ls-remote`).
- **Größe:** 988 Dateien, zusammen 148.169.882 Byte unkomprimiert am festen Commit (GitHub-API, Verzeichnisbaum; davon rund 137 MB Bilder, 1,9 MB AsciiDoc-Text). Das Repository mit Verlauf ist laut API rund 1,1 GB groß.
- **Lade-Art:** `none` – nur Verweis mit festem Commit (Entscheidung zu Frage 4, Option A).

**Lizenzbefund** (Fundstellen am festen Commit: `LICENSE.md` und `README.md`, Abschnitt „Licence“):

- Dokumentation: Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0). Der vollständige Lizenztext in `LICENSE.md` ist der von CC BY-SA 4.0.
- Unstimmigkeit im Original: Der erste Satz von `LICENSE.md` nennt die Lizenz „Attribution 4.0“ ohne „ShareAlike“, verlinkt aber auf `by-sa/4.0`. `README.md` und der Volltext sagen eindeutig CC BY-SA. Maßgeblich ist CC BY-SA 4.0.
- Werkzeuge außerhalb des Unterordners `documentation/`: BSD-3-Clause (laut `README.md`).
- Marken sind nicht mitlizenziert (CC BY-SA 4.0, Abschnitt 2(b)(2)).

**Folgerung:** laden ja · weitergeben ja, mit Namensnennung und unter gleicher Lizenz · einchecken rechtlich möglich, aber nicht vorgesehen (ShareAlike passt nicht zu den bevorzugten Lizenzen des eigenen Codes; für die CI-Testdaten ist die OPNsense-Dokumentation die bessere Wahl).

**Abruf ohne Anmeldung:** ja. **geprüft am:** 21.11.2026.

### 2.2 Datenblätter (PDF)

Die Adressen unter `datasheets.raspberrypi.com` leiten zweimal weiter (301 nach `pip.raspberrypi.com/documents/…`, dann 302 nach `pip-assets.raspberrypi.com/…`). Das Lade-Skript muss Weiterleitungen folgen. Der Dateiname am Ziel trägt eine laufende Nummer; der Inhalt hinter der festen Adresse kann sich also ändern – die Prüfsumme im Manifest fängt das ab.

| Unterlage | Adresse | Größe (Byte) | Stand | Vermerk in der Datei | Lade-Art |
| --- | --- | --- | --- | --- | --- |
| Datenblatt Raspberry Pi 4 Model B, Release 1.1, März 2024 | https://datasheets.raspberrypi.com/rpi4/raspberry-pi-4-datasheet.pdf | 413.147 | 06.10.2025 | Titelblatt: Copyright 2024 Raspberry Pi (Trading) Ltd., „All rights reserved“ | `auto` |
| Product Brief | https://datasheets.raspberrypi.com/rpi4/raspberry-pi-4-product-brief.pdf | 21.375.446 | 01.10.2026 | kein Copyright- oder Lizenzvermerk im Text; nur Markenhinweis auf Raspberry Pi Ltd | `auto` |
| Schaltplan (gekürzt) | https://datasheets.raspberrypi.com/rpi4/raspberry-pi-4-reduced-schematics.pdf | 337.685 | 06.10.2025 | „© Raspberry Pi 2018“ | `auto` |

**Lizenzbefund:** Keine der drei Dateien nennt eine freie Lizenz. Das Datenblatt behält ausdrücklich alle Rechte vor. Die CC-Lizenz der Online-Dokumentation gilt für das Dokumentations-Repository, nicht für diese PDFs. Zum Lesen der Vermerke wurden die drei Dateien vorübergehend außerhalb des Projektordners geöffnet und danach gelöscht.

**Folgerung:** laden ja · weitergeben nein · einchecken nein (wie Herstellerunterlage).

**Abruf ohne Anmeldung:** ja. **geprüft am:** 21.11.2026.

---

## 3. TP-Link TL-WR902AC

**Rechteinhaber:** TP-Link (Seitenfuß: TP-Link Systems Inc. und verbundene Unternehmen; die deutsch ausgelieferten Nutzungsbedingungen nennen TP-Link Deutschland GmbH als Anbieter).

| Unterlage | Adresse | Größe (Byte) | Stand | Lade-Art |
| --- | --- | --- | --- | --- |
| Anleitung V3 als PDF (REV3.0.0 laut Dateiname) | https://static.tp-link.com/2019/201906/20190624/1910012191_TL-WR902AC%203.0_UG_REV3.0.0.pdf | 8.504.388 | 24.06.2019 | `auto` |
| Anleitung V3 online (HTML) | https://www.tp-link.com/us/user-guides/tl-wr902ac_v3/ | – | abgerufen 21.11.2026 | `none` |
| Übersicht aller Hardwarestände | https://www.tp-link.com/us/support/download/tl-wr902ac/ | – | abgerufen 21.11.2026 | `none` |

Die Übersichtsseite führt die Hardwarestände V4.60, V4.46, V4.40, V4, V3.80, V3.60, V3 und V1.

**Lizenzbefund:**

- Seitenfuß von tp-link.com: „©2026 TP-Link Systems Inc. … All rights reserved.“
- Nutzungsbedingungen der Website, Fundstelle https://privacy.tp-link.com/web/official/terms-of-use (deutsch ausgeliefert), Abschnitt „Geistiges Eigentum“: begrenzte, nicht übertragbare Lizenz zum Herunterladen und Verwenden auf dem eigenen Gerät für den persönlichen Gebrauch; keine öffentliche oder kommerzielle Nutzung der Inhalte; kein Kopieren in ein anderes Werk ohne vorherige schriftliche Zustimmung; Weiterverteilen nur mit eigener Lizenz. Der Abschnitt „Nutzung“ beschränkt die Dienste auf den persönlichen, nicht-kommerziellen Gebrauch.

**Folgerung:** laden ja (eigener Gebrauch) · weitergeben nein · einchecken nein.

**Abruf ohne Anmeldung:** ja. **geprüft am:** 21.11.2026.

### Offene Punkte

- **U-05 (ungeprüft):** Hardwarestand des in der Fertigungslinie verbauten Routers – steht nur indirekt fest (das Handbuch der Fertigungslinie verweist auf die Anleitung V3).
- **U-06 (ungeprüft):** Datum und Fassung der TP-Link-Nutzungsbedingungen sowie die Frage, ob sie auch für Dateien unter `static.tp-link.com` gelten – auf der Seite kein Datum gefunden, die US-Seite verlinkt im Fuß nur die Datenschutzerklärung.
- **U-07 (ungeprüft):** Revisionsvermerk und Copyright-Vermerk im PDF selbst – die Datei wurde nicht geöffnet (Auftrag 110).

---

## 4. UR5e-Handbücher (Universal Robots, e-Series, PolyScope 5)

**Rechteinhaber:** Universal Robots A/S.

Alle Adressen liefern ohne Anmeldung HTTP 200, soweit nicht anders vermerkt. Basis der Adressen: `https://www.universal-robots.com/manuals`.

### Stand 5.25.1 (gewählter Stand, Frage 1 Option A)

| Unterlage | Sprache | Adresse | Größe (Byte) | Stand | Lade-Art |
| --- | --- | --- | --- | --- | --- |
| Benutzerhandbuch UR5e | de | https://www.universal-robots.com/manuals/de/PDF/SW5_25_1/user-manual-UR5e-PDF_online/710-966-00_UR5e_User_Manual_de_Global.pdf | 21.703.593 | 30.09.2026 | `auto` |
| Benutzerhandbuch UR5e | en | https://www.universal-robots.com/manuals/EN/PDF/SW5_25_1/user-manual-UR5e-PDF_online/710-965-00_UR5e_User_Manual_en_Global.pdf | 21.443.808 | 30.09.2026 | `none` (Verweis) |
| Software-Handbuch PolyScope 5 | en | https://www.universal-robots.com/manuals/EN/PDF/SW5_25_1/Poly5_handbook_online/e-Series_Software_Handbook_en_Global.pdf | 11.470.539 | 30.09.2026 | `auto` |
| Script-Verzeichnis | en | https://www.universal-robots.com/manuals/EN/PDF/SW5_25_1/scriptmanualG5/script_directory_Poly5.pdf | 2.089.986 | 30.09.2026 | `auto` |
| Service-Handbuch e-Series | en | https://www.universal-robots.com/manuals/EN/PDF/SW5_25_1/service-manual_e-series/e-Series_Service_Manual_en.pdf | 23.785.655 | 30.09.2026 | `auto` |

Befunde dazu:

- **Script-Verzeichnis und Software-Handbuch im Stand 5.25.1 sind vorhanden** (offener Punkt des Auftrags: ja, Adressen oben). Das Titelblatt des Script-Verzeichnisses nennt „5.25.1“ (Datei vorübergehend außerhalb des Projektordners geöffnet, danach gelöscht).
- **Software-Handbuch auf Deutsch als PDF: nicht gefunden.** Zwei naheliegende Adressen (`…/de/PDF/SW5_25_1/Poly5_handbook_online/e-Series_Software_Handbook_de_Global.pdf`, ebenso mit `DE`) liefern HTTP 404. Deutsch gibt es das Software-Handbuch als HTML: https://www.universal-robots.com/manuals/de/HTML/SW5_25_1/Content/Landingpages/Web/SWHandbook.htm (HTTP 200).
- **Deutsch 5.25.1 ist der neueste deutsche Stand.** Die „permanente Adresse“ des Herstellers für das jeweils neueste deutsche UR5e-Handbuch, `…/manuals/latest/de/pdf/ps5/ur5e/`, führt auf die Datei unter `SW5_25_1`. (Diese Adressen beantworten HEAD mit 404 und leiten nur bei GET weiter.) Die englische Entsprechung führt auf `SW5_26`.
- **Die englische PDF-Übersicht des Stands 5.25.1 verlinkt auf den Ordner `SW5_25`,** nicht auf `SW5_25_1`. Unter `SW5_25` liegen ältere Dateien (11.09.2026, deutsches Handbuch 12.01.2026). Für das Manifest gelten die Adressen unter `SW5_25_1`.
- **Das Service-Handbuch gibt es in drei Fassungen** unterschiedlicher Größe: `Shared` (22.830.834 Byte, 29.09.2026), `SW5_25_1` (23.785.655 Byte, 30.09.2026) und `SW5_25` (23.243.459 Byte, 11.09.2026). Es ist also nicht einfach „an keinen Softwarestand gebunden“. Für den Stand 5.25.1 wird die Fassung unter `SW5_25_1` vorgeschlagen.

### Andere Stände (nur Verweis, `none`)

| Unterlage | Adresse | Größe (Byte) | Stand |
| --- | --- | --- | --- |
| Benutzerhandbuch UR5e, de, 5.24 | https://s3-eu-west-1.amazonaws.com/ur-support-site/262293/UR5e_User_Manual_de_PolyScope_5.24.pdf | 20.749.530 | 03.11.2025 |
| Benutzerhandbuch UR5e, de, 5.24 (zweite Fundstelle) | https://www.universal-robots.com/manuals/de/PDF/SW5_24/user-manual-UR5e-PDF_online/710-966-00_UR5e_User_Manual_de_Global.pdf | 20.758.560 | 12.11.2025 |
| Benutzerhandbuch UR5e, de, 5.25 | https://www.universal-robots.com/manuals/de/PDF/SW5_25/user-manual-UR5e-PDF_online/710-966-00_UR5e_User_Manual_de_Global.pdf | 20.982.204 | 12.01.2026 |
| Benutzerhandbuch UR5e, de, 5.26 | `…/de/PDF/SW5_26/…/710-966-00_UR5e_User_Manual_de_Global.pdf` | **HTTP 404** | – |
| Benutzerhandbuch UR5e, en, 5.26 | https://www.universal-robots.com/manuals/EN/PDF/SW5_26/user-manual-UR5e-PDF_online/710-965-00_UR5e_User_Manual_en_Global.pdf | 20.985.870 | 14.09.2026 |
| Software-Handbuch, en, 5.26 | https://www.universal-robots.com/manuals/EN/PDF/SW5_26/Poly5_handbook_online/e-Series_Software_Handbook_en_Global.pdf | 13.361.031 | 14.09.2026 |
| Script-Verzeichnis, en, 5.26 | https://www.universal-robots.com/manuals/EN/PDF/SW5_26/scriptmanualG5/script_directory_Poly5.pdf | 1.592.959 | 14.09.2026 |
| Service-Handbuch e-Series, en, `Shared` | https://www.universal-robots.com/manuals/EN/PDF/Shared/service-manual_e-series/e-Series_Service_Manual_en.pdf | 22.830.834 | 29.09.2026 |

Die deutsche PDF-Übersicht des Stands 5.25.1 verlinkt bereits auf ein deutsches Handbuch unter `SW5_26`; die Datei gibt es noch nicht (404). Auch eine deutsche HTML-Fassung des Stands 5.26 fehlt (404). Übersicht aller Stände: https://www.universal-robots.com/manuals/EN/HTML/MainLanding/Content/Landingpages/mainlanding.htm

### Lizenzbefund

- **Vermerk im Script-Verzeichnis 5.25.1** (Seite nach dem Titelblatt, am Original gelesen): Der Inhalt ist Eigentum von Universal Robots A/S und „shall not be reproduced in whole or in part without prior written approval“; Copyright 2009–2025, in der Fußzeile „All rights reserved“. Das klärt den im Vorbefund als widersprüchlich bezeichneten Befund für dieses Teilhandbuch.
- **Website:** Im Seitenfuß von universal-robots.com sind nur Cookie- und Datenschutzhinweise verlinkt; aktuelle allgemeine Nutzungsbedingungen für Downloads wurden nicht gefunden. Unter https://www.universal-robots.com/media/876344/tou_universalrobots_ukversion_markup_28082015-final.pdf liegt ein Dokument „Terms of Use“ vom September 2015 (125.445 Byte).
- **Keine freie Lizenz** an irgendeiner der Unterlagen.

### Folgerung

- **laden:** ja, für den eigenen Gebrauch.
- **weitergeben:** nein.
- **einchecken:** nein. Prüffragen und erwartete Antworten (Aufträge 111, 112) nennen nur Fundstellen und höchstens kurze Zitate.

**Abruf ohne Anmeldung:** ja. **geprüft am:** 21.11.2026.

### Offene Punkte

- **U-08 (ungeprüft):** Welchen Softwarestand das Titelblatt des deutschen UR5e-Benutzerhandbuchs unter `SW5_25_1` nennt, und der Copyright-Vermerk in dieser Datei – die Datei wurde nicht geladen (Auftrag 110 liest beides nach dem Abruf).
- **U-09 (ungeprüft):** Inhalt und Gültigkeit der „Terms of Use“ von 2015 – nur Vorhandensein und Datum geprüft, Text nicht gelesen.
- **U-10 (ungeprüft):** Welche der drei Fassungen des Service-Handbuchs inhaltlich zum Stand 5.25.1 gehört – nur Größe und Datum verglichen.

---

## 5. URSim-Image (`universalrobots/ursim_e-series`)

**Rechteinhaber:** Universal Robots A/S (Docker-Hub-Konto `universalrobots`).

- **Adresse:** https://hub.docker.com/r/universalrobots/ursim_e-series
- **Beschreibung laut Docker Hub:** Simulator für die e-Series mit Oberfläche über VNC; Hauptzweck sind CI-Tests der quelloffenen ROS-Treiber des Herstellers, andere Nutzung wird ausdrücklich als möglich genannt.
- **Architektur:** nur `linux/amd64`. 52 Tags (5.4 bis 5.26.3 und `latest`).

### Tags und Digests

Abgefragt am **21.11.2026** über die Docker-Hub-API (`/v2/repositories/universalrobots/ursim_e-series/tags/<tag>`); jeder Digest zusätzlich an der Registry bestätigt (Kopfzeile `Docker-Content-Digest` von `registry-1.docker.io`, anonymes Lesetoken). Es wurde kein Image gezogen.

| Tag | Digest (Manifest) | zuletzt gepusht (UTC) | Größe komprimiert (Byte) | Abrufdatum |
| --- | --- | --- | --- | --- |
| `5.25.1` | `sha256:36c80afd904f748486c31b38331ef8b0edbaf234432714d3f3d1dc8fe0102210` | 28.10.2026 13:16 | 961.067.605 | 21.11.2026 |
| `5.26.3` | `sha256:c80dfb4ec6b554db6d20ba45fb90d0ec056d0303bd3c7a7040a4e8b503eaaf87` | 28.10.2026 13:18 | 973.012.100 | 21.11.2026 |
| `5.24.0` | `sha256:0910c578445c4337c4faea25eed57c813c3c3569633658e03f56a46a453461ad` | 28.10.2026 13:16 | 960.598.912 | 21.11.2026 |

Weitere Befunde:

- `latest` und `5.26` zeigen am 21.11.2026 auf denselben Digest wie `5.26.3`. `5.25` zeigt auf `sha256:444b4b360b312a07aad7453fd2435d6c41c9244f3f06f2070cb7601cf03c3117`, also **nicht** auf `5.25.1`.
- **Auch Patch-Tags sind beweglich:** Alle drei Tags wurden am 28.10.2026 neu gepusht, auch das alte `5.24.0`. Das Manifest (Auftrag 107) muss deshalb den Digest festhalten, nicht nur den Tag; T2 zieht mit `@sha256:…`.
- Das Image `5.25.1` trägt die Kennzeichnung `build_version: URSim Version: 5.25.1` und die Umgebungsvariable `VERSION=5.25.1` (aus der Image-Konfiguration gelesen, erzeugt am 28.10.2026). Tag und enthaltener Softwarestand stimmen überein.
- **5.26 ist der LTS-Stand:** Die Produktmitteilung des Herstellers sagt, PolyScope 5.26 LTS werde bis Ende 2027 unterstützt (https://www.universal-robots.com/articles/ur/documentation/product-notice-introduction-of-polyscope-526-long-term-support-lts/). Der Punkt aus dem Vorbefund ist damit bestätigt.

### Lizenzbefund

- **Docker Hub:** Die Beschreibung nennt keine Lizenz. Die Image-Konfiguration trägt keine Lizenz-Kennzeichnung (nur `build_version` und `description`).
- **Quell-Repository:** Unter https://github.com/UniversalRobots wurde kein Repository für das URSim-Image gefunden (Suche nach „sim“ in der Organisation: nur Gazebo-Simulationen für ROS 2 und zwei Beispiel-URCaps; `UniversalRobots/ursim_docker` gibt es nicht, HTTP 404). Das Repository https://github.com/urrsk/ursim_docker (Stand `8de3a6d7fdb61502679be2cd25e18b52ed40e682`) ist nicht die Quelle des Images, sondern baut auf dem fertigen Image auf und ergänzt ein URCap; es enthält keine Lizenzdatei (`LICENSE`, `LICENSE.md`, `LICENSE.txt`: 404).
- **UR-EULA:** https://www.universal-robots.com/articles/ur/documentation/end-user-software-license-agreement-eula/ (Fassung „Ver 1.5, May 2024“ laut verlinkter PDF-Datei). Abschnitt 2.1: Nutzung der Software nur zusammen mit dem UR-Produkt, in das sie eingebettet ist, und nur für eigene interne Geschäftszwecke; keine Überlassung an Dritte und keine abgeleiteten Werke ohne vorherige schriftliche Zustimmung. **Das Wort „URSim“ oder „Simulator“ kommt auf der Seite nicht vor.** Ob die EULA für den Simulator gilt, bleibt offen; sie ist auf eingebettete Robotersoftware zugeschnitten.

### Folgerung

- **laden:** ja – jeder Nutzer zieht das Image selbst von Docker Hub (T2).
- **weitergeben:** nein – das Image und Standarddateien daraus werden nicht weitergegeben.
- **einchecken:** nein. Ins Manifest kommen nur Name, Tag und Digest. Für selbst erzeugte Dateien aus URSim gilt der Arbeitsstand aus Frage 3 (Option B, Anfrage an den Hersteller durch a7 vor T2).

**Lade-Art:** `none` – das Lade-Skript holt das Image nicht.
**Abruf ohne Anmeldung:** ja (anonymer Zugriff auf Docker Hub). **geprüft am:** 21.11.2026.

### Offene Punkte

- **U-11 (ungeprüft):** Ob im Image selbst eine Lizenzdatei oder ein Lizenzhinweis liegt – dafür müsste das Image gezogen werden (T2).
- **U-12 (ungeprüft):** Ob die UR-EULA für URSim gilt und ob aus URSim erzeugte Dateien veröffentlicht werden dürfen – der Text nennt URSim nicht; Klärung nur durch Anfrage beim Hersteller (Frage 3, a7).
- **U-13 (ungeprüft):** Vollständigkeit der Suche nach einem offiziellen Quell-Repository – nur die erste Trefferseite der Organisation und zwei naheliegende Namen geprüft.

---

## 6. OPNsense-Dokumentation

**Rechteinhaber:** Deciso B.V. und namentlich genannte Mitwirkende (Copyright-Zeilen in der Lizenzdatei, 2015–2018).

- **Adresse:** https://github.com/opnsense/docs (gerendert: https://docs.opnsense.org/)
- **Geprüfter Commit:** `953dd3d1d1dd2739a18d0b6df5c936146153aff6` vom 20.11.2026 (19:44 +0100), Zweig `master`; am 21.11.2026 weiterhin Spitze von `master` (`git ls-remote`).
- **Format:** reStructuredText (Sphinx), nur Englisch.
- **Größe des Archivs am festen Commit:** 929 Dateien, zusammen **108.160.157 Byte unkomprimiert** (GitHub-API, Verzeichnisbaum des Commits, vollständig, nicht abgeschnitten); als unkomprimiertes tar rund 108,9 MB. Das liegt deutlich unter der Schwelle von 300 MB aus Frage 4. Das Repository mit Verlauf ist laut API rund 290 MB groß. Aufteilung nach Dateiendung: `.png` 28,3 MB · `.bz2` 26,5 MB · `.pdf` 18,2 MB · `.gz` 15,2 MB · `.jpg` 9,3 MB · **`.rst` 4,7 MB** · `.ai` 3,3 MB · `.zip` 1,1 MB.
- **Lade-Art:** `auto` – als `git-archive` auf dem festen Commit mit `tree_sha256` (Entscheidung zu Frage 4, Option A). Archiv-Adresse: `https://codeload.github.com/opnsense/docs/tar.gz/953dd3d1d1dd2739a18d0b6df5c936146153aff6` (HTTP 200).

### Lizenzbefund (Pflichtpunkt aus Abschnitt 10.2 der Startunterlage)

- **Adresse der LICENSE-Datei:** https://raw.githubusercontent.com/opnsense/docs/953dd3d1d1dd2739a18d0b6df5c936146153aff6/LICENSE (am festen Commit) – inhaltsgleich mit https://raw.githubusercontent.com/opnsense/docs/master/LICENSE . SHA-256 der Datei: `4ffb5112f4d0d9eb0fb07bbe8d5740420edc176bdf69037306c838b0ee48f153`.
- **Ergebnis der Prüfung am Original, 21.11.2026: BSD-2-Clause – ja.** Die Datei erklärt die Dokumentation zur 2-Klausel-BSD-Lizenz. Sie enthält genau die zwei Bedingungen (Quelltext-Weitergabe und Weitergabe in anderer Form jeweils mit Copyright-Vermerk, Bedingungen und Haftungsausschluss) und einen Haftungsausschluss; eine dritte Klausel (Werbeverbot mit Namen) fehlt.
- **Abweichung vom Standardtext:** Der Haftungsausschluss ist auf die Dokumentation umformuliert („this documentation“, „the OPNsense documentation project“ statt „software“ und „copyright holder“). Die GitHub-API meldet deshalb keine erkannte Standardlizenz. Inhaltlich ändert das nichts an den zwei Bedingungen.
- **Bilder:** Abschnitt „Pictures“ der LICENSE-Datei: einige Bilder stehen unter CC0. Welche, sagt die Datei nicht.
- **Logos:** Abschnitt „Logos“: Logos können zusätzlichen Urheber-, Eigentums- oder Markenrechten unterliegen; Deciso sichert dafür keine Rechte zu und räumt keine ein.

### Folgerung

- **laden:** ja.
- **weitergeben:** ja, wenn Copyright-Vermerk, die zwei Bedingungen und der Haftungsausschluss mitgegeben werden (die LICENSE-Datei unverändert beilegen).
- **einchecken:** ja für Textdateien (`.rst`) zusammen mit der unveränderten LICENSE-Datei und Angabe von Quelle und Commit. **Bilder und Logos nicht einchecken:** Die Lizenzdatei ordnet einzelne Bilder nicht zu und nimmt Logos aus. Für `testdata/klein/` (Auftrag 108) deshalb nur Textdateien auswählen.
- **Hinweis für das Einlesen:** Docling führt reStructuredText nicht unter den unterstützten Formaten (https://docling-project.github.io/docling/usage/supported_formats/ , abgerufen 21.11.2026; genannt sind unter anderem Markdown und AsciiDoc). Auftrag 108 muss das berücksichtigen.

**Abruf ohne Anmeldung:** ja. **geprüft am:** 21.11.2026.

### Offene Punkte

- **U-14 (ungeprüft):** Genaue Größe des komprimierten Archivs (`tar.gz`) am festen Commit – die Archiv-Adresse liefert keine `Content-Length`, und laden war nicht erlaubt; sie liegt höchstens bei der unkomprimierten Größe von rund 109 MB (Auftrag 109 misst sie beim Erstabruf).
- **U-15 (ungeprüft):** Herkunft und Rechte der im Repository enthaltenen PDF-Dateien und Archive (`.pdf`, `.bz2`, `.gz`, `.zip`, zusammen rund 61 MB) – nicht geöffnet; für `testdata/klein/` deshalb nur `.rst`-Dateien verwenden.
- **U-16 (ungeprüft):** Welche Bilder unter CC0 stehen – die LICENSE-Datei ordnet sie nicht zu.

---

## 7. Passung Handbuch und Softwarestand

### UR5e und URSim

Regel der Startunterlage (Abschnitt 10.2): Handbuch und Simulator haben denselben Softwarestand. Deutsch ist für die Prüffragen Pflicht.

| Paar | Handbuch | Simulator | Bewertung |
| --- | --- | --- | --- |
| **A (gewählt)** | Benutzerhandbuch UR5e deutsch unter `SW5_25_1`; dazu Software-Handbuch, Script-Verzeichnis und Service-Handbuch englisch unter `SW5_25_1` | `universalrobots/ursim_e-series:5.25.1`, Digest `sha256:36c80afd…2210` | Stände passen laut Ordnername, Titelblatt des Script-Verzeichnisses und Kennzeichnung des Images. Deutsch vorhanden. Nicht der LTS-Stand. Titelblatt des deutschen Handbuchs: siehe U-08. |
| B | Benutzerhandbuch UR5e englisch unter `SW5_26` | `…:5.26.3`, Digest `sha256:c80dfb4e…af87` | LTS bis Ende 2027. Kein deutsches Handbuch (404). Das Handbuch nennt den Stand 5.26 ohne Patch-Nummer. |
| C | Benutzerhandbuch UR5e deutsch 5.24 | `…:5.24.0`, Digest `sha256:0910c578…61ad` | Deutsch vorhanden; älterer Stand; Handbuch nennt nur „5.24“. |

Für die Prüffrage zum Schutzstopp (Startunterlage Abschnitt 11, Frage 10) ist das Software-Handbuch wichtig. Es liegt im Stand 5.25.1 als PDF nur englisch vor, deutsch nur als HTML. Auftrag 112 muss entscheiden, ob die deutsche Antwort aus dem Benutzerhandbuch belegbar ist.

### Siemens S7-1200

- Bedingung 2 aus Abschnitt 10.1 („Dokumentation passt zum Softwarestand“) bleibt für die S7-1200 **offen**, solange CPU und Firmware der Projektarchive unbekannt sind (U-01).
- Die Projektarchive setzen TIA Portal V18 voraus. Falls die Zuordnung in U-02 stimmt, passt die Ausgabe **V4.6 (11/2022)** besser als die aktuelle V4.7 (12/2024) – und gerade V4.6 ist per Direktadresse abrufbar.
- Das Handbuch der Fertigungslinie nennt neben der S7-1200 an einer Stelle eine CPU 1512SP (Startunterlage 10.2, „Fundstück für die Prüfung“). Eine CPU 1512SP gehört nicht zur Reihe S7-1200; das S7-1200-Systemhandbuch deckt sie nicht ab. Der Widerspruch bleibt Prüfstoff und wird hier nicht aufgelöst.

### Raspberry Pi 4B und TP-Link TL-WR902AC

- Raspberry Pi: Das Datenblatt beschreibt die Hardware (Release 1.1, März 2024) und ist an keinen Softwarestand gebunden. Der Softwarestand der Zentralsteuerung ergibt sich aus dem Abbild der Fertigungslinie (Auftrag 102).
- TP-Link: Die Anleitung gehört zum Hardwarestand V3. Ob dieser Stand verbaut ist, steht nur indirekt fest (U-05).
