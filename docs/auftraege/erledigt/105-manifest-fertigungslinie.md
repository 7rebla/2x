# Auftrag 105 – Manifest-Einträge der Fertigungslinie

Meilenstein: T1 · Freigabestufe: C · Status: erledigt

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

**Was wurde gebaut?**

- `testfactory/manifest.yaml`: 19 Einträge der Fertigungslinie, in kanonischer Form (über `parse_manifest`/`write_manifest` im Dienst `fetch` geschrieben). Alle Prüfsummen sind `null`.
  - 2 × `git-archive`, `fetch: auto`: `aps-repository` (`main` @ `b8082e16…`) und `aps-repository-dev` (`release` @ `24568073…`), `repository` als volle `https://github.com/...`-Adresse, `size_bytes` = Summe der Dateigrößen aus Auftrag 102.
  - 16 × `file`, `fetch: auto`: je Deutsch und Englisch Quick-Start, Dokumentation 02/2025, Belegungspläne, Kalibrierung (ZIP), Fehlersuche, IP-Adresse eines Moduls ändern, Software-Versionen, Software-Update. IDs `aps-<thema>-de` / `-en`. `size_bytes` aus der Quellen-Datei.
  - 1 × `reference`, `fetch: none`: `aps-rpi-image` (Kurzadresse des Herstellers als `url`, Weiterleitungsziel, Größe und „keine Prüfsumme, Dritt-Hoster“ in `notes`).
  - Ziele: `fischertechnik/aps-24v/repositories/<name>` und `fischertechnik/aps-24v/documents/<de|en>/<Dateiname>`; nichts ineinander verschachtelt.
  - `terms` überall `license: none-stated`, `redistribution: false`, `checked_on: 2026-11-21`.
- `testfactory/tests/test_manifest_aps.py`: 12 Tests (erwartete IDs; `terms.note`, `terms.holder`, `software_version`, `assigned_to`; 40-stellige, festgelegte Commits; kein `redistribution: true`; Kennungen nur aus der Liste des Auftrags; Ziele nicht verschachtelt; nicht aufgenommenes Material fehlt; jede Adresse steht in der Quellen-Datei, Kurzform `P` ausgeschrieben).

**Nicht aufgenommen (wie entschieden)**

- Add-on-Dokumentation FTS/AGV (Deutsch und Englisch): Auftrag 102 hat belegt, dass sie nicht zum Grundprodukt gehört; nach der Entscheidung der Leitstelle wird sie nicht geladen.
- Add-on Brennofen (Deutsch und Englisch): Zusatzmodul nicht Teil der Testfabrik (Frage 3 in Auftrag 102, Antwort A).
- Altstände A1 bis A3.

**Was vorerst in `notes` steht (nachziehen nach Auftrag 104)**

- `aps-rpi-image`: Größe 8.869.171.712 Byte steht in `notes`, weil das Format `size_bytes` bei `kind: reference` noch ablehnt. Nach 104 in `size_bytes` übernehmen und den Satz in `notes` kürzen.
- `file` + `manual` ohne `url` kommt bei der Fertigungslinie nicht vor; hier ist nichts nachzuziehen.
- Vergleichs-Prüfsummen der beiden Handbücher aus Auftrag 102 stehen in `notes` (nicht in `sha256`); Auftrag 109 kann sie mit dem Erstabruf vergleichen.

**Wie wurde getestet?** (alles im Container, Compose-Projekt `twox-105`, am Ende mit `down -v` entfernt)

- `docker version` (Engine 29.9.3) und `docker compose version` (v5.7.0): Exit 0.
- `TF run --rm fetch python -m testfactory.manifest_tools check`: `testfactory/manifest.yaml: OK (19 entries)`, Exit 0.
- `TF run --rm check python -m unittest discover -s testfactory/tests -t . -v`: `Ran 65 tests`, `OK`; die 12 Tests aus `test_manifest_aps` sind dabei. Dasselbe im Dienst `check-offline`: `OK`.
- `TF run --rm check mypy --config-file testfactory/mypy.ini testfactory`: `Success: no issues found in 5 source files`.
- `git grep -n -i -E "passw|kennwort" -- testfactory/manifest.yaml testfactory/tests/test_manifest_aps.py`: kein Treffer.
- Adressen wortgleich mit der Quellen-Datei: durch den Test `test_every_address_is_taken_from_the_source_file` für alle 19 Einträge geprüft (`url`, `landing_page`, `repository`).
- `git diff --stat main...HEAD`: nur `testfactory/manifest.yaml`, `testfactory/tests/test_manifest_aps.py` und diese Auftragsdatei. `git status --porcelain`: nichts unter `testfactory/extern/`.
- Nicht ausgeführt: `check --complete` (schlägt erwartungsgemäß fehl, solange die Prüfsummen offen sind – Auftrag 109). Es wurde nichts heruntergeladen und keine Adresse abgerufen.

**Zweig und Arbeitsverzeichnis**

Zweig `worktree-agent-a40a68a2b16a0d25e`, Arbeitsverzeichnis `.claude/worktrees/agent-a40a68a2b16a0d25e`. Nicht gepusht, nicht zusammengeführt.

**Abweichungen und eigene Festlegungen (bitte prüfen)**

1. `terms.verified`: `true` nur bei den drei Quellen, deren Inhalt Auftrag 102 selbst geöffnet und durchsucht hat – Handbuch Deutsch, Handbuch Englisch, Repository 2 (ausgecheckt, Volltextsuche). `false` mit Grund in `notes` bei den 14 nicht geöffneten Unterlagen, bei Repository 1 (nur Dateibaum und drei Markdown-Dateien gelesen; Lizenzfeld der GitHub-API und eingebettete Lizenztexte der Archive ungeprüft) und beim Abbild. Das ist die strengere Lesart von „Was die Quellen-Datei als ungeprüft führt, bleibt `verified: false`“; die Leitstelle kann Repository 1 auf `true` setzen, wenn ihr der Dateibaum-Befund genügt.
2. `software_version`: Unterlagen „APS 1.3.0“ (aktueller Softwarestand laut Update-Blog; dass die einzelne Unterlage zu diesem Stand gehört, ist ungeprüft und so in `version_source` vermerkt). Repository 1 „APS 1.3.0 (main, 02.03.2026)“ wie in der Quellen-Datei; Repository 2 entsprechend „APS 1.3.0 (release, 02.03.2026)“; Abbild „APS 1.3.0 (unverified)“, weil die Datei älter ist als der Tag v1.3.0.
3. `document_version`: nur wo belegt („Version 4, 02/2025“ vom Titelblatt des deutschen Handbuchs laut 102; sonst Datum aus dem Dateinamen). Bei den zehn Dateien ohne Datum im Namen `null`, mit Vermerk „kann sich still ändern“ in `notes`.
4. `assigned_to`:
   - Handbuch und Quick-Start: alle acht Anlagen (Vorgabe).
   - Belegungspläne, Kalibrierung, Fehlersuche, Software-Versionen, Software-Update: alle acht Anlagen, aber nur nach Titel – der Inhalt ist nicht geöffnet; als „assignment unverified“ vermerkt.
   - „IP-Adresse eines Moduls ändern“: die fünf SPS (`dps-plc`, `hbw-plc`, `drill-plc`, `mill-plc`, `aiqs-plc`), ebenfalls nur nach Titel.
   - Repository 1: die fünf SPS, `dps-txt`, `aiqs-txt`, `agv-txt`, `cgw-txt` und `ccu-rpi` (Zuordnung nach Dateinamen, Inhalt der Archive ungeprüft). Repository 2: `aps-core` und `ccu-rpi`. Abbild: `ccu-rpi`.
   - `aps-router` ist keinem Eintrag zugeordnet; seine Unterlagen gehören zu Auftrag 107.
5. `terms.holder` beim Abbild ist ein Text mit „unverified …“, weil der Rechteinhaber laut Quellen-Datei ungeprüft ist und das Feld Pflicht ist.
6. `retrieved_on` ist bei allen Einträgen der 21.11.2026 (letzte Prüfung der Quelle in Auftrag 102, nicht ein Abruf). Auftrag 109 überschreibt das Feld beim Erstabruf.
7. Sprache der Freitexte im Manifest (`notes`, `terms.note`, `version_source`): Englisch, wie README und Code der Testfabrik. Titel in der Sprache der Unterlage.
8. Der Test geht über Punkt 6 des Umfangs hinaus (Adressabgleich mit der Quellen-Datei, Kennungen, Ziele). Er liest dafür `docs/testfabrik/quellen-fertigungslinie.md`; wird die Datei verschoben, muss der Pfad im Test mitziehen.
9. Zugangsdaten: nichts übernommen. Die `notes` sagen nur, dass Handbuch, README und Abbild Standard-Zugangsdaten enthalten und Repository 2 eine Datei mit Hash des Broker-Geheimnisses; Werte und Dateiname stehen nicht im Manifest.
10. Das Manifest wurde mit einem Wegwerf-Skript außerhalb des Repositorys erzeugt (im Dienst `fetch` ausgeführt, nicht eingecheckt).

**Offene Fragen**

Keine, die blockiert. Zur Kenntnis für die Leitstelle: Punkt 1 (Lesart von `verified`) und Punkt 4 (Zuordnung nach Titel) sind Auslegungen des Bearbeiters.
