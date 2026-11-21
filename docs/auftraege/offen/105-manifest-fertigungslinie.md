# Auftrag 105 – Manifest-Einträge der Fertigungslinie

Meilenstein: T1 · Freigabestufe: C · Status: offen

## Ziel

`testfactory/manifest.yaml` enthält alle Unterlagen und Dateien der fischertechnik APS 24V: Quelle, Softwarestand, Nutzungshinweis und zugeordnete Anlage oder Gerät. Die Prüfsummen bleiben leer; sie trägt der Erstabruf (Auftrag 109) ein.

## Umfang

1. Einträge nach dem Format aus Auftrag 101, Inhalt ausschließlich aus `docs/testfabrik/quellen-fertigungslinie.md` (Auftrag 102) und a7s Antworten dort:
   - zwei Einträge `git-archive`, `fetch: auto`: Repository `Agile-Production-Simulation-24V` und `Agile-Production-Simulation-24V-Dev`, jeweils mit `repository`, `branch` und vollem `commit` wie von a7 entschieden (Vorschlag: `main` @ `b8082e16282a69f7d219a39d993bf7d34cb9d349` und `release` @ `24568073f7f70d0d31dcaa83bcfcd7b595baba1f`).
   - je ein Eintrag `file`, `fetch: auto` für die Unterlagen in Deutsch und Englisch: Quick-Start, Dokumentation 02/2025, Belegungspläne, Kalibrierung (ZIP), Fehlersuche, IP-Adresse eines Moduls ändern, dazu vom Update-Blog Software-Versionen und Software-Update.
   - Add-on-Dokumentation FTS (Deutsch und Englisch): aufnehmen. Hat Auftrag 102 belegt, dass sie zum Grundprodukt gehört, normal; ist der Punkt dort „ungeprüft“, mit `verified: false` und Vermerk in `notes`; hat 102 belegt, dass sie nicht zum Grundprodukt gehört, nicht aufnehmen und im Kurzbericht nennen.
   - Add-on Brennofen nur, wenn a7 das Zusatzmodul aufgenommen hat (Frage 3 in Auftrag 102).
   - ein Eintrag `reference`, `fetch: none` für das Raspberry-Pi-Abbild (Adresse, Größe, Hinweis „keine Prüfsumme veröffentlicht, Dritt-Hoster“), sofern a7 nichts anderes entschieden hat (Frage 4 in Auftrag 102).
   - Altstände (Dokumentation 04/2024 und andere) werden nicht aufgenommen.
2. `software_version` je Eintrag: Softwarestand der Anlage (Vorschlag „APS 1.3.0“), `document_version` aus dem Dateinamen, `version_source` ehrlich angeben („Dateiname“, „Titelblatt laut Recherche“, „ungeprüft“). Die Titelblätter liest erst Auftrag 110.
3. `terms` je Eintrag aus dem Befund von Auftrag 102, zum Beispiel für die Repositories: `license: none-stated`, `redistribution: false`, `note`: laden ja, weitergeben nein, nichts einchecken. `verified` nur dann `true`, wenn Auftrag 102 den Punkt am Original bestätigt hat.
4. `assigned_to` mit den Kennungen der Geräteliste (Auftrag 106). Verwendet werden diese festen Kennungen; Auftrag 106 ist maßgeblich, Abweichungen gleicht die Leitstelle beim Zusammenführen ab:
   - Anlagen: `aps-dps`, `aps-hbw`, `aps-drill`, `aps-mill`, `aps-aiqs`, `aps-agv`, `aps-charging`, `aps-core`
   - Geräte: `dps-plc`, `dps-txt`, `hbw-plc`, `drill-plc`, `mill-plc`, `aiqs-plc`, `aiqs-txt`, `agv-txt`, `cgw-txt`, `ccu-rpi`, `aps-router`
   - Unterlagen, die die ganze Linie betreffen (Handbuch, Quick-Start), werden allen acht Anlagen zugeordnet.
   - Hat a7 bei Frage 5 in Auftrag 102 „bei vier bleiben“ gewählt, entfällt `dps-plc`.
5. `target` je Eintrag: sprechender Pfad `fischertechnik/…` (relativ zu `root`, also unter `testfactory/extern/`).
6. Test `testfactory/tests/test_manifest_aps.py` (`unittest`): Die Einträge der Fertigungslinie sind vorhanden (erwartete IDs); jeder hat `terms.note`, `terms.holder`, `software_version` und mindestens einen Eintrag in `assigned_to`; beide Repositories haben einen 40-stelligen Commit; kein Eintrag hat `redistribution: true`.

## Nicht-Ziele

- Nichts herunterladen, keine Prüfsummen eintragen (Auftrag 109).
- Keine Einträge für Standardgeräte, UR5e, URSim oder OPNsense (Auftrag 107).
- Keine Änderung am Format oder an `manifest_tools.py`.
- Keine eigene Lizenzbewertung: Es gilt der Befund aus Auftrag 102.

## Betroffene Bereiche (Ordner, Dateien)

- `testfactory/manifest.yaml`
- `testfactory/tests/test_manifest_aps.py`

## Akzeptanzkriterien (prüfbar)

In den Befehlen steht `TF` für `docker compose -f deploy/compose/testfactory.yaml`.

- `docker version` und `docker compose version` enden mit Exit 0 (sonst siehe Hinweise).
- `TF run --rm fetch python -m testfactory.manifest_tools check` endet mit Exit 0.
- `TF run --rm check python -m unittest discover -s testfactory/tests -t . -v` endet mit `OK`; `test_manifest_aps` ist dabei.
- `TF run --rm check mypy --config-file testfactory/mypy.ini testfactory` endet mit `Success: no issues found`.
- Jede Adresse im Manifest steht wortgleich in `docs/testfabrik/quellen-fertigungslinie.md` (Stichprobe der Leitstelle: fünf Einträge).
- `git grep -n -i -E "passw|kennwort" -- testfactory/manifest.yaml testfactory/tests/test_manifest_aps.py` findet nichts (keine Liefer-Zugangsdaten übernommen).
- `git diff --stat main...HEAD` zeigt nur die zwei genannten Dateien sowie die eigene Auftragsdatei unter `docs/auftraege/offen/`; `git status --porcelain` zeigt nichts unter `testfactory/extern/`.

## Vorgaben und Hinweise

**Nachtrag der Leitstelle (21.11.2026, aus der Prüfung von Auftrag 101):** `repository` immer als volle `https://github.com/...`-Adresse. Ziele (`target`) nicht ineinander verschachteln; Archive bekommen getrennte Unterordner. `size_bytes` bei `kind: reference` und `file`+`manual` ohne `url` lässt das Werkzeug erst nach Auftrag 104 zu – ist 104 noch nicht zusammengeführt, die Größe vorerst in `notes` führen und das im Kurzbericht nennen. Vor dem Commit die Datei in die kanonische Form bringen (`load_manifest`/`write_manifest` im Dienst `fetch`, nach Auftrag 104 der dortige Unterbefehl) und `check` laufen lassen. Maßgebliche Quelle ist `docs/testfabrik/quellen-fertigungslinie.md` bzw. die Quellen-Datei aus Auftrag 103.

- Voraussetzung: Die Aufträge 101 und 102 sind zusammengeführt, und a7s Antworten zu den Fragen 2 bis 5 in Auftrag 102 liegen vor. Fehlt eine Antwort, gilt die dortige Empfehlung nur, wenn a7 die Liste ohne Änderung freigegeben hat; sonst Frage und Status „wartet auf a7“.
- Kein Push. Der Bearbeiter committet nur auf seinem Auftragszweig; die Leitstelle pusht auf a7s Freigabe (Vorgabe vom 21.11.2026, weicht von Abschnitt 8.2 Stufe A ab).
- Fehlt Docker: nichts unter Windows installieren oder ausführen, Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
- Nichts erfinden: Was die Quellen-Datei als „ungeprüft“ führt, bleibt im Manifest `verified: false`, mit kurzem Grund in `notes`.
- Dateien ohne Datum im Namen können sich still ändern (kein `Last-Modified`, kein `ETag`); das in `notes` vermerken.
- Die Liefer-Zugangsdaten, die in den Repositories offen stehen, werden nirgends ins Manifest oder in Tests übernommen.
- Läuft gleichzeitig mit 104 und 106; `fetch.py` wird hier nicht benutzt.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

Keine eigenen; maßgeblich sind die Antworten zu den Fragen 2 bis 5 in Auftrag 102.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
