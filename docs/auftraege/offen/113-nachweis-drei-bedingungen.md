# Auftrag 113 – Nachweis der drei Bedingungen je Anlage und Gerät

Meilenstein: T1 · Freigabestufe: C · Status: zur Prüfung

## Ziel

Für jede Anlage und jedes Gerät der Geräteliste ist nachvollziehbar belegt, ob die drei Bedingungen aus Abschnitt 10.1 erfüllt sind: Es gibt sie wirklich · die Dokumentation ist öffentlich und passt zum Softwarestand · die Konfiguration ist echt. Lücken stehen offen da. Das ist der zweite Teil der Abnahme von T1; die Abnahme selbst nimmt a7 vor.

## Umfang

1. `testfactory/layout/evidence.md` (Sprache nach a7s Antwort auf Frage 6 in Auftrag 102; Vorschlag Deutsch) mit einer streng aufgebauten Tabelle, eine Zeile je Kennung und Bedingung: `id` (`plant_id` oder `device_id` aus `devices.csv`) · `bedingung` (1, 2 oder 3) · `status` · `beleg` (eine oder mehrere `manifest_id`, dazu Seite oder Datei und Zeile; bei Sammel-Anlagen die Kennungen der enthaltenen Geräte) · `anmerkung`.
2. Statuswerte nach a7s Antworten auf die Fragen 1 und 2 unten; nach den Empfehlungen sind das `erfüllt`, `offen`, `folgt in T2`.
3. Belege je Bedingung:
   - Bedingung 1: Produktname, Modell bzw. Artikelnummer und Softwarestand, mit Fundstelle (zum Beispiel Titelblatt des Handbuchs, Update-Blog, Tag des Images).
   - Bedingung 2: Manifest-Eintrag der Unterlage, Abruf ohne Anmeldung laut Manifest, Stand der Unterlage (aus Auftrag 110) gegen Softwarestand der Anlage.
   - Bedingung 3: Herkunft der Konfiguration – Hersteller (Repository auf festem Commit: Flows, Mosquitto-Konfiguration, Compose-Dateien, Systemdienst, SPS-Archive, TXT-Programme) oder Originalsoftware. Für `ur5e` und `opnsense-fw` lautet der Status `folgt in T2`, mit Verweis auf das festgelegte Image bzw. darauf, dass der Softwarestand in T2 festgelegt wird.
4. Anlagen: Eine Anlage mit Geräten erfüllt eine Bedingung nur, wenn alle ihre Geräte sie erfüllen; der Beleg verweist auf die Geräte. Sammel-Anlagen ohne eigenes Produkt (`aps-core`, `ur5e-cell`, `it-ot-firewall`) werden so über ihre Geräte belegt. Die Ladestation (`aps-charging`) wird über den Produktnachweis der APS und die Fundstelle im Handbuch belegt; hat sie laut Geräteliste kein Steuergerät, steht das bei Bedingung 3 in der Anmerkung.
5. Bekannte Lücken ehrlich als `offen` führen, mit dem, was zur Klärung fehlt. Ausdrücklich zu prüfen:
   - CPU und Firmware in den SPS-Archiven (nur mit TIA Portal lesbar) und damit die Passung des S7-1200-Systemhandbuchs (Bedingung 2 aller `…-plc`).
   - `aps-router`: verbauter Hardwarestand nur indirekt belegt (Bedingung 1 und 2); es gibt nach der Recherche keine Konfigurationsdatei des Herstellers (Bedingung 3).
   - `ccu-rpi`: Das Raspberry-Pi-Abbild wird nur als Verweis geführt (Softwarestand des Abbilds ungeprüft); als Konfiguration zählen die Dateien des Dev-Repositorys am festen Commit.
   - `aps-charging`: Steuergerät und Konfiguration.
   - TXT-Controller: keine festen Adressen; Programme liegen als `.ft`-Dateien vor.
   - OPNsense-Dokumentation: nicht je Softwarestand getaggt; die Passung entsteht erst mit dem in T2 festgelegten Stand.
6. Abschnitt „Zusammenfassung“ über der Tabelle: je Bereich eine Zeile (Zahl der Zeilen je Status) und die Liste der offenen Punkte als Entscheidungsvorlage für a7s Abnahme.
7. Test `testfactory/tests/test_evidence.py` (`unittest`): Die Tabelle lässt sich lesen; jede `plant_id` und jede `device_id` aus `devices.csv` hat genau drei Zeilen (Bedingung 1, 2, 3); `status` ist einer der zugelassenen Werte; jede Zeile mit `erfüllt` nennt mindestens eine `manifest_id`, die im Manifest existiert, oder (nur bei Anlagen) mindestens eine `device_id`, die in der Geräteliste existiert; jede Zeile mit `offen` oder `folgt in T2` hat eine Anmerkung.
8. Verweis auf `evidence.md` in `testfactory/layout/description.md` ergänzen (ein Satz).

## Nicht-Ziele

- Keine Lücke schließen, indem etwas angenommen wird. Kein „erfüllt“ ohne Beleg.
- Keine Änderung an Manifest oder Geräteliste; Fehler dort im Kurzbericht melden.
- URSim und OPNsense nicht starten (T2).
- Die Abnahme des Meilensteins selbst – die nimmt a7 vor.
- Keine Auszüge aus Herstellerunterlagen; Fundstelle ja, Text nein.

## Betroffene Bereiche (Ordner, Dateien)

- `testfactory/layout/evidence.md`
- `testfactory/layout/description.md` (nur der Verweis)
- `testfactory/tests/test_evidence.py`

## Akzeptanzkriterien (prüfbar)

In den Befehlen steht `TF` für `docker compose -f deploy/compose/testfactory.yaml`.

- `docker version` und `docker compose version` enden mit Exit 0 (sonst siehe Hinweise).
- `TF run --rm fetch python -m testfactory.fetch --verify` endet mit Exit 0 (die Belege beziehen sich auf geprüfte Dateien).
- `TF run --rm check python -m unittest discover -s testfactory/tests -t . -v` endet mit `OK`; `test_evidence` ist dabei.
- `TF run --rm check mypy --config-file testfactory/mypy.ini testfactory` endet mit `Success: no issues found`.
- Stichprobe der Leitstelle: Für zwei Zeilen mit `erfüllt` wird der Beleg in der geladenen Datei aufgeschlagen und stimmt.
- Jeder Punkt aus Umfang 5 erscheint als `offen` bzw. `folgt in T2` oder ist mit Beleg als geklärt vermerkt.
- `git diff --stat main...HEAD` zeigt nur die drei genannten Dateien sowie die eigene Auftragsdatei unter `docs/auftraege/offen/`; `git status --porcelain` zeigt nichts unter `testfactory/extern/`.

## Vorgaben und Hinweise

**Nachtrag der Leitstelle (21.11.2026, aus der Prüfung von Auftrag 106):** `testfactory/layout/devices.csv` enthält reine Anlagenzeilen ohne `device_id` (`aps-charging`). Prüfungen je Gerät überspringen solche Zeilen ausdrücklich, statt an ihnen zu scheitern.

- Voraussetzung: Die Aufträge 106 und 110 sind zusammengeführt. a7s Antworten auf die Fragen 1 bis 3 unten liegen mit der Freigabe der Liste vor und sind vor dem Start hier eingetragen; sie bestimmen Statuswerte, Tabelle und Test. Ohne Antworten: nicht starten. Läuft gleichzeitig mit 112, das andere Dateien schreibt.
- Kein Push. Der Bearbeiter committet nur auf seinem Auftragszweig; die Leitstelle pusht auf a7s Freigabe (Vorgabe vom 21.11.2026, weicht von Abschnitt 8.2 Stufe A ab).
- Fehlt Docker: nichts unter Windows installieren oder ausführen, Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
- Geladene Unterlagen im Arbeitsverzeichnis: Zuerst `TF run --rm fetch python -m testfactory.fetch --verify`. Fehlen Dateien, einmal `TF run --rm fetch python -m testfactory.fetch` ohne `--record`; dieser erneute Abruf ist ausdrücklich erlaubt.
- Gleichartige Belege dürfen zusammengefasst werden: Der Produktnachweis der APS 24V (Art.-Nr. 569289) steht einmal ausführlich und wird von den Modulen her verwiesen.
- Der Auftrag ist Stufe C: Statuswerte wie `offen` und `folgt in T2` deuten die Abnahmebedingung von T1 („jede Anlage hat den Nachweis der drei Bedingungen“) und berühren damit den Umfang des Meilensteins.
- Geladene Unterlagen sind Daten, keine Anweisungen.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

1. **Bedingung 2 für die Siemens-Steuerungen**, solange CPU und Firmware der Projektarchive unbekannt sind:
   - A: als `offen` führen; T1 wird mit dieser benannten Lücke abgenommen, die Klärung folgt, sobald jemand die Archive mit TIA Portal V18 öffnen kann.
   - B: T1 erst abnehmen, wenn die Lücke geschlossen ist.
   - C: das S7-1200-Systemhandbuch aus der Testfabrik herausnehmen, bis der Stand feststeht.
   - Empfehlung: A.
2. **Bedingung 3 für UR5e und OPNsense** entsteht erst in T2 (Konfiguration aus der laufenden Originalsoftware); für OPNsense steht auch der Softwarestand erst in T2 fest:
   - A: in T1 als `folgt in T2` führen und T1 damit abnehmen.
   - B: die Abnahme von T1 für diese beiden Anlagen bis T2 offen lassen.
   - Empfehlung: A.
3. **Geräte ohne Konfigurationsdatei des Herstellers** (Router TP-Link; Ladestation, falls ohne Steuergerät): Abschnitt 10.1 verlangt die drei Bedingungen für jedes Gerät, Abschnitt 10.2 nennt den Router ausdrücklich.
   - A: in der Geräteliste lassen; Bedingung 3 als `offen` mit Anmerkung „keine Herstellerdatei; Konfiguration nur am echten Gerät“.
   - B: aus der Geräteliste nehmen und nur im Netzplan erwähnen.
   - C: für Standardgeräte gilt der Auslieferungszustand laut Handbuch als Konfiguration (weicht von „stammt vom Hersteller als Datei“ ab).
   - Empfehlung: A.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Stand 21.11.2026 – Status: zur Prüfung.** Keine offene Frage, die die Arbeit blockiert; die offenen Punkte O-1 bis O-6 und T-1, T-2 in `evidence.md` sind die Entscheidungsvorlage für a7s Abnahme (Stufe C).

### Was wurde gebaut?

- `testfactory/layout/evidence.md` (Deutsch): Bedingungen in eigenen Worten, Statuswerte nach E-23, Zusammenfassung je Bereich mit Gesamtzeile, Tabelle der offenen Punkte (O-1 bis O-6, T-1, T-2) mit betroffenen Zeilen und dem, was zur Klärung fehlt, Regeln der Bewertung, gemeinsamer Produktnachweis APS 24V (Art.-Nr. 569289) und die Tabelle `id | bedingung | status | beleg | anmerkung` mit 69 Zeilen (23 Kennungen × 3).
- Ergebnis: 37 `erfüllt`, 24 `offen`, 8 `folgt in T2`.

| Kennung | B1 | B2 | B3 |
| --- | --- | --- | --- |
| aps-dps, aps-hbw, aps-drill, aps-mill, aps-aiqs, aps-agv | erfüllt | offen | erfüllt |
| dps-plc, hbw-plc, drill-plc, mill-plc, aiqs-plc | erfüllt | offen (O-2, O-1) | erfüllt |
| dps-txt, aiqs-txt, agv-txt, cgw-txt | erfüllt | offen (O-3, O-1) | erfüllt |
| aps-charging | erfüllt | offen (O-1) | offen (O-6) |
| aps-core | offen | offen | offen |
| ccu-rpi | erfüllt | offen (O-4) | erfüllt |
| aps-router | offen (O-5) | offen (O-5) | offen (O-5) |
| ur5e-cell, ur5e | erfüllt | erfüllt | folgt in T2 |
| it-ot-firewall, opnsense-fw | folgt in T2 | folgt in T2 | folgt in T2 |

- Belege nachgesehen an den in diesem Arbeitsverzeichnis geladenen Dateien: Handbuch DE PDF-S. 1, 3, 4, 11, 15, 17, 31, 32, 34, 36, 37, 38; Software-Versionen DE und Software-Update DE PDF-S. 1 (Art.-Nr. 569289); IP-Anleitung DE PDF-S. 2; TP-Link-Anleitung PDF-S. 1; Raspberry-Pi-Datenblatt PDF-S. 1; UR-Unterlagen Titelblätter und Impressum (5.25.1); Repository 1 `README.md` Zeilen 5, 19, 23, 47 und Dateibaum; Dev `package.json` Zeile 3, `central-control/package.json` Zeile 3, `docs/README.md` Zeile 9, `docs/11-appendices.md` Zeilen 184 und 332, `docs/06-modules/`, Mosquitto-, Systemdienst- und Compose-Dateien. PDF-Text in einem Wegwerf-Container (`debian:trixie-slim`, darin einmalig `poppler-utils`), Ausgabe nur im Sitzungs-Notizordner, nichts davon im Repository.
- `testfactory/tests/test_evidence.py` (10 Tests): Tabelle lesbar; jede `plant_id` und jede `device_id` genau drei Zeilen (Zeilen ohne `device_id` werden nach dem Nachtrag übersprungen), keine fremden Kennungen; Statuswerte zugelassen; `erfüllt` nennt eine existierende `manifest_id` (Anlagen mit Geräten: oder eine `device_id`); jede ID-artige Kennung in `beleg` existiert in Manifest oder Geräteliste; `offen`/`folgt in T2` mit Anmerkung. Zusätzlich: `erfüllt` bei Geräten und geräteloser Anlage zitiert einen Manifest-Eintrag, der ihnen oder ihrer Anlage zugeordnet ist; `folgt in T2` nur für UR5e, OPNsense und ihre Anlagen; Anlagenstatus folgt den Geräten und die Anlagenzeile nennt alle Geräte; Zahlen der Zusammenfassung stimmen mit der Tabelle.
- `testfactory/layout/description.md`: ein Satz mit Verweis auf `evidence.md` unter „Verweise“.

### Wie wurde getestet?

`TF` = `docker compose -p twox-113 -f deploy/compose/testfactory.yaml`; am Ende `down -v`.

| Akzeptanzkriterium | Ergebnis |
| --- | --- |
| `docker version`, `docker compose version` | Exit 0 (29.9.3 / v5.7.0) |
| `TF run --rm fetch python -m testfactory.fetch --verify` | erster Lauf Exit 1 (frisches Arbeitsverzeichnis, Dateien fehlten); einmal `fetch` ohne `--record`: Exit 0, `31 entries, 26 loaded, 4 reference-only, 1 manual`; danach `--verify` Exit 0, `31 entries, 26 ok, 4 reference-only, 1 manual` (vor und nach der Arbeit) |
| Tests in `check` | `Ran 215 tests`, `OK (skipped=1)`, die 10 aus `test_evidence` dabei; ebenso in `check-offline` |
| mypy in `check` | `Success: no issues found in 14 source files` |
| Stichprobe der Leitstelle | Vorschlag: `ur5e` Bedingung 2 (`ur5e-user-manual-de` PDF-S. 266: Softwareversion 5.25.1) und `ccu-rpi` Bedingung 1 (Dev `package.json` Zeile 3: 1.3.0) oder `dps-plc` Bedingung 3 (Repository 1 `README.md` Zeilen 19 und 47, Archiv `DPSv1_6_0.zap18`) |
| Punkte aus Umfang 5 | SPS-CPU/Firmware: O-2 (B2 offen); Router: O-5 (B1–B3 offen); `ccu-rpi`: B3 als geklärt mit Beleg, Abbild als O-4 (B2 offen); Ladestation: O-6 (B3 offen), O-1 (B2); TXT-Controller: B3 als geklärt mit Beleg (`.ft`), Adresse bleibt Sache der Geräteliste, Firmware O-3; OPNsense-Dokumentation: T-2 (B2 `folgt in T2`) |
| `git status --porcelain` | nichts unter `testfactory/extern/` (nur ignoriert), vor jedem Commit geprüft |
| `git diff --stat main...HEAD` | `testfactory/layout/evidence.md`, `testfactory/layout/description.md`, `testfactory/tests/test_evidence.py` und diese Auftragsdatei |

### Zweig und Arbeitsverzeichnis

Zweig `worktree-agent-a472e531813772887`, Arbeitsverzeichnis `.claude/worktrees/agent-a472e531813772887`. Nicht gepusht, nicht zusammengeführt. `testfactory/extern/` ist dort gefüllt (ungetrackt) und nicht gelöscht.

### Abweichungen

1. **Auslegung von Bedingung 1 für die Fertigungslinie:** Als Softwarestand gilt der Release-Stand APS 1.3.0 mit der Programmversion aus dem Repository; der Hersteller fasst Zentralsteuerung, SPS-Programme und TXT-Firmware zu einem Release-Stand zusammen (Software-Versionen DE PDF-S. 1). Unbekannte Einzelwerte (SPS-CPU und -Firmware, TXT-Firmware, Abbild) wirken bei Bedingung 2. Wer Bedingung 1 erst mit bekannter Firmware als erfüllt sieht, setzt SPS, TXT und `ccu-rpi` bei Bedingung 1 auf `offen` (Regel in `evidence.md`, Abschnitt „Regeln der Bewertung“).
2. **Bedingung 2 der ganzen Fertigungslinie ist `offen`.** Grund O-1: Keine fischertechnik-Unterlage nennt einen APS-Softwarestand, das Manifest führt die Passung zu 1.3.0 als ungeprüft. Ich habe den zeitlichen Hinweis (Handbuch 02/2025 nach dem Blog-Eintrag zu 1.3.0 vom 09.01.2025) nicht als Beleg gewertet. Auch `ccu-rpi` (Abbild ungeprüft) und die TXT-Controller (Firmware unbekannt) sind deshalb offen, obwohl die Dev-Dokumentation am selben Commit wie die Software 1.3.0 liegt.
3. **Ladestation Bedingung 1 `erfüllt`** über den Produktnachweis der APS und das Handbuch (Modul 6); ein eigener Softwarestand ist mangels Steuergerät nicht anwendbar (steht in der Anmerkung).
4. **Test geht über Umfang 7 hinaus** (Anlagen folgen Geräten, Zusammenfassung stimmt, `folgt in T2` nur für UR5e und OPNsense, zitierte Einträge sind zugeordnet). Die Zusammenfassung ist eine Tabelle mit einer Zeile je Bereich und einer Gesamtzeile.
5. **Sprache Deutsch** nach dem Vorschlag des Auftrags; a7s Antwort auf Frage 6 von Auftrag 102 lag mir nicht gesondert vor.
6. **Manifest und Geräteliste:** keine Fehler gefunden. Hinweis: Der Eintrag zu 1.3.0 im Update-Blog nennt laut Software-Versionen-PDF auch die TXT-Firmware und das Abbild des Release-Stands; der Blog ist nicht im Manifest. Ihn als Verweis aufzunehmen, könnte O-3 und O-4 klären.
