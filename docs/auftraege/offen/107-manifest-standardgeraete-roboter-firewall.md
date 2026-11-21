# Auftrag 107 – Manifest-Einträge: Standardgeräte, UR5e, URSim, OPNsense-Dokumentation

Meilenstein: T1 · Freigabestufe: C · Status: zur Prüfung

## Ziel

`testfactory/manifest.yaml` enthält auch die Unterlagen der Standardgeräte, der Roboterzelle und der Firewall, jeweils mit Softwarestand, Nutzungshinweis und Zuordnung. URSim steht als Verweis mit festem Tag und Digest im Manifest (Nutzungsbedingungen nach Abschnitt 10.4); gezogen und gestartet wird es erst in T2.

## Umfang

1. Einträge nach dem Format aus Auftrag 101, Inhalt ausschließlich aus `docs/testfabrik/quellen-standardgeraete-roboter-firewall.md` (Auftrag 103) und a7s Antworten dort:
   - Siemens S7-1200 Systemhandbuch: nach a7s Antwort auf Frage 2 in Auftrag 103 als `file`/`auto` (Ausgabe 04/2012) und/oder als `file`/`manual` (aktuelle Ausgabe, mit `landing_page`). Zuordnung: alle `…-plc`-Geräte der Geräteliste.
   - Raspberry Pi 4B: Datenblatt und Product Brief als `file`/`auto`. Die Dokumentation (`raspberrypi/documentation`) nach a7s Antwort auf Frage 4 in Auftrag 103: bei A oder C als `reference`, `fetch: none`, mit `repository` und `commit`; bei B als `git-archive`. Zuordnung: `ccu-rpi`.
   - TP-Link TL-WR902AC: Benutzerhandbuch V3 (PDF) als `file`/`auto`. Zuordnung: `aps-router`. In `notes`: verbauter Hardwarestand nur indirekt belegt.
   - UR5e: Benutzerhandbuch im von a7 gewählten Softwarestand (Vorschlag: Deutsch 5.25.1), Service-Handbuch e-Series (Englisch), Script-Verzeichnis und Software-Handbuch PolyScope 5 (Englisch; Stand wie in Auftrag 103 geklärt), alle `file`/`auto`. Zuordnung: `ur5e`. Weicht der Stand einer Unterlage vom gewählten Softwarestand ab, steht das in `notes`.
   - URSim: ein Eintrag `container-image`, `fetch: none`, mit `image: universalrobots/ursim_e-series`, Patch-Tag und Digest aus Auftrag 103. Zuordnung: `ur5e`. `terms` nach dem Befund aus 103 (EULA, keine Weitergabe, jeder Nutzer zieht selbst).
   - OPNsense-Dokumentation: ein Eintrag mit `repository: opnsense/docs` und dem festen `commit` aus Auftrag 103 – nach a7s Antwort auf Frage 4 in Auftrag 103 bei A oder B als `git-archive`, `fetch: auto`; bei C als `reference`, `fetch: none`. `license: BSD-2-Clause` von Hand eintragen (Fundstelle der LICENSE-Datei in `terms_url`), `redistribution: true`. `software_version` bleibt leer mit Vermerk „Softwarestand der Firewall wird in T2 festgelegt“. Zuordnung: `opnsense-fw`.
2. `software_version`, `document_version`, `version_source` und `terms` wie in Auftrag 105 beschrieben; `verified: true` nur für am Original bestätigte Punkte.
3. `target` je Eintrag: `<hersteller>/…` (relativ zu `root`).
4. Test `testfactory/tests/test_manifest_other.py` (`unittest`): Die erwarteten IDs sind vorhanden; der URSim-Eintrag hat einen Patch-Tag (kein `latest`, kein Minor-Tag) und einen Digest der Form `sha256:` plus 64 Hex-Zeichen; die Einträge von UR5e-Benutzerhandbuch und URSim nennen denselben Softwarestand; jeder Eintrag hat `terms.note`; `redistribution: true` haben nur Einträge mit `license` aus der Liste `BSD-2-Clause`, `public-domain` (`CC-BY-SA-4.0` nur, wenn a7 bei Frage 3 in Auftrag 108 Option B gewählt hat); kein Eintrag enthält eine bewegliche Adresse (`/latest/`) oder einen beweglichen Tag.

## Nicht-Ziele

- Nichts herunterladen, kein Image ziehen, keine Prüfsummen von Dateien eintragen (Auftrag 109). Der Digest des Images ist eine Angabe der Quelle und wird übernommen.
- Kein Eintrag für OPNsense-Software oder -Installationsabbild: gehört zu T2.
- Keine Änderung an den Einträgen der Fertigungslinie (Auftrag 105), am Format oder an `manifest_tools.py`.
- Keine eigene Lizenzbewertung: Es gilt der Befund aus Auftrag 103.

## Betroffene Bereiche (Ordner, Dateien)

- `testfactory/manifest.yaml` (nur neue Einträge)
- `testfactory/tests/test_manifest_other.py`

## Akzeptanzkriterien (prüfbar)

In den Befehlen steht `TF` für `docker compose -f deploy/compose/testfactory.yaml`.

- `docker version` und `docker compose version` enden mit Exit 0 (sonst siehe Hinweise).
- `TF run --rm fetch python -m testfactory.manifest_tools check` endet mit Exit 0.
- `TF run --rm check python -m unittest discover -s testfactory/tests -t . -v` endet mit `OK`; `test_manifest_other` ist dabei.
- `TF run --rm check mypy --config-file testfactory/mypy.ini testfactory` endet mit `Success: no issues found`.
- `git diff main...HEAD -- testfactory/manifest.yaml` zeigt nur hinzugefügte Einträge, keine Änderung an bestehenden.
- Jede Adresse im Manifest steht wortgleich in der Quellen-Datei aus Auftrag 103 (Stichprobe der Leitstelle: fünf Einträge).
- `git diff --stat main...HEAD` zeigt nur die zwei genannten Dateien sowie die eigene Auftragsdatei unter `docs/auftraege/offen/`.

## Vorgaben und Hinweise

**Nachtrag der Leitstelle (21.11.2026, aus Auftrag 103):** Maßgebliche Quelle ist `docs/testfabrik/quellen-standardgeraete-roboter-firewall.md`. Entschieden mit E-27 (a7, 21.11.2026): Systemhandbuch S7-1200 V4.6 (11/2022) als maßgebliche Ausgabe, V4.7 (12/2024) als Verweis; **kein automatischer Abruf von Siemens-Adressen** (Lade-Art `manual` bzw. `none`), wegen der Klausel gegen Text- und Data-Mining in den Siemens-Nutzungsbedingungen. Die Ausgabe 04/2012 entfällt. URSim immer mit Digest festlegen (Patch-Tags sind beweglich). Raspberry-Pi-Datenblatt und Product Brief wie Herstellerunterlagen behandeln.

**Nachtrag der Leitstelle (21.11.2026, aus der Prüfung von Auftrag 101):** `repository` immer als volle `https://github.com/...`-Adresse. Ziele (`target`) nicht ineinander verschachteln; Archive bekommen getrennte Unterordner. `size_bytes` bei `kind: reference` und `file`+`manual` ohne `url` lässt das Werkzeug erst nach Auftrag 104 zu – ist 104 noch nicht zusammengeführt, die Größe vorerst in `notes` führen und das im Kurzbericht nennen. Vor dem Commit die Datei in die kanonische Form bringen (`load_manifest`/`write_manifest` im Dienst `fetch`, nach Auftrag 104 der dortige Unterbefehl) und `check` laufen lassen. Maßgebliche Quelle ist `docs/testfabrik/quellen-fertigungslinie.md` bzw. die Quellen-Datei aus Auftrag 103.

- Voraussetzung: Die Aufträge 103 und 105 sind zusammengeführt; a7s Antworten zu den Fragen 1, 2 und 4 in Auftrag 103 liegen vor. Ohne Antwort auf Frage 1 (Softwarestand UR5e/URSim): Status „wartet auf a7“. Läuft gleichzeitig mit 108, das andere Dateien schreibt.
- Kein Push. Der Bearbeiter committet nur auf seinem Auftragszweig; die Leitstelle pusht auf a7s Freigabe (Vorgabe vom 21.11.2026, weicht von Abschnitt 8.2 Stufe A ab).
- Fehlt Docker: nichts unter Windows installieren oder ausführen, Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
- Bewegliche Adressen (zum Beispiel `…/manuals/latest/…`) und bewegliche Tags (`latest`, `5.26`) sind im Manifest nicht erlaubt.
- Die GitHub-API meldet für die OPNsense-Doku keine erkannte Lizenz; deshalb der Handeintrag mit Fundstelle.
- Die Kennungen in `assigned_to` müssen in `testfactory/layout/devices.csv` (Auftrag 106) vorkommen; den Abgleich prüft der Test aus Auftrag 109.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

Keine eigenen; maßgeblich sind die Antworten zu den Fragen 1, 2 und 4 in Auftrag 103.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Stand 21.11.2026 – Status: zur Prüfung**

**Was wurde gebaut?**

- `testfactory/manifest.yaml`: 12 neue Einträge hinter den 19 bestehenden (diese unverändert), in kanonischer Form (`load_manifest`/`write_manifest` im Dienst `fetch`). Alle Prüfsummen `null`, nichts geladen.
  - Siemens: `siemens-s7-1200-system-manual-v4-6-de` (`file`/`manual`, maßgeblich nach E-27, mit `url` und `landing_page`, `size_bytes` 36.472.132) und `siemens-s7-1200-system-manual-v4-7-de` (`reference`/`none`, Verweis). Beide `license: proprietary`, Zuordnung zu den fünf `…-plc`. Restrisiko der Klausel A.6.2 (Text- und Data-Mining) in `notes` beider Einträge vermerkt; Ausgabe 04/2012 nicht aufgenommen.
  - Raspberry Pi: `rpi4b-datasheet-en` und `rpi4b-product-brief-en` (`file`/`auto`, wie Herstellerunterlagen, `redistribution: false`), `rpi-documentation` (`reference`/`none`, `repository`, `branch` `master`, `commit` `97485d97…`, `license: CC-BY-SA-4.0`, `redistribution: false` wegen Frage 3 in Auftrag 108 Antwort A). Zuordnung `ccu-rpi`.
  - TP-Link: `tl-wr902ac-user-guide-v3-en` (`file`/`auto`), Zuordnung `aps-router`; Hardwarestand nur indirekt belegt (U-05) in `notes`.
  - UR5e: `ur5e-user-manual-de`, `ur5e-software-handbook-en`, `ur5e-script-directory-en`, `ur5e-service-manual-en` (alle `file`/`auto`, Ordner `SW5_25_1`, `software_version` „PolyScope 5.25.1“). Zuordnung `ur5e`.
  - URSim: `ursim-e-series` (`container-image`/`none`, `universalrobots/ursim_e-series`, Tag `5.25.1`, Digest `sha256:36c80afd…2210`, `terms_url` = UR-EULA, `license: none-stated`). Zuordnung `ur5e`.
  - OPNsense: `opnsense-docs` (`git-archive`/`auto`, `https://github.com/opnsense/docs`, `master` @ `953dd3d1…aff6`, `size_bytes` 108.160.157, `license: BSD-2-Clause` von Hand, `terms_url` = LICENSE am festen Commit, `redistribution: true`, `verified: true`). `software_version` leer, Vermerk „set in T2“ in `version_source` und `notes`. Zuordnung `opnsense-fw`.
  - Ziele: `siemens/…`, `raspberry-pi/…`, `tp-link/…`, `universal-robots/ur5e/documents/<de|en>/…`, `opnsense/repositories/docs`; nichts ineinander verschachtelt.
  - `verified: true` nur, wo 103 am Original gelesen hat: Datenblatt, Product Brief, Script-Verzeichnis, Raspberry-Pi-Dokumentation, OPNsense. Alle anderen `false` mit Grund in `notes`.
- `testfactory/tests/test_manifest_other.py`: 13 Tests (erwartete IDs; URSim mit Patch-Tag und Digest; gleicher Softwarestand Handbuch/URSim; `terms.note` bei allen 31 Einträgen; `redistribution: true` nur bei `BSD-2-Clause`/`public-domain`; keine Adresse mit `/latest/`, kein beweglicher Tag; Siemens nie `auto`; OPNsense-Archiv; Raspberry-Pi-Doku nur Verweis; `assigned_to` gegen `devices.csv`; Begründung bei `verified: false`; Ziele nicht verschachtelt; jede Adresse inkl. `terms_url` wortgleich in der Quellen-Datei aus 103).

**Vorerst in `notes` statt in eigenen Feldern** (Format vor Auftrag 104):

- Größe der Verweise: V4.7 „laut Seite 32.770 KB“, Raspberry-Pi-Dokumentation 148.169.882 Byte.
- Von Siemens veröffentlichte SHA-256 der V4.7 (`reference` hat kein Prüfsummenfeld).
- Komprimierte Größe des URSim-Images (961.067.605 Byte; `size_bytes` ist bei `container-image` nicht erlaubt).
- SHA-256 der OPNsense-LICENSE-Datei und die Archiv-Adresse `codeload.github.com/…`.

**Wie wurde getestet?** (Container, Projektname `twox-107`, danach `down -v`)

- `docker version` / `docker compose version`: Exit 0 (Server 29.9.3, Compose v5.7.0).
- `TF run --rm fetch python -m testfactory.manifest_tools check`: `testfactory/manifest.yaml: OK (31 entries)`, Exit 0.
- `TF run --rm check python -m unittest discover -s testfactory/tests -t . -v`: `Ran 97 tests`, `OK`, `test_manifest_other` dabei; ebenso `check-offline`: `OK`.
- `TF run --rm check mypy --config-file testfactory/mypy.ini testfactory`: `Success: no issues found in 7 source files`.
- `git diff main...HEAD -- testfactory/manifest.yaml`: nur hinzugefügte Zeilen (0 entfernte).
- `git diff --stat main...HEAD`: nur `testfactory/manifest.yaml`, `testfactory/tests/test_manifest_other.py` und diese Auftragsdatei.

**Zweig und Arbeitsverzeichnis:** Zweig `worktree-agent-a3df18e8661be55a1`, Arbeitsverzeichnis `.claude/worktrees/agent-a3df18e8661be55a1`. Nicht gepusht.

**Abweichungen und Hinweise**

- `software_version` ist `null` bei Siemens (CPU/Firmware offen, U-01/U-02), Raspberry-Pi-Unterlagen (an keinen Softwarestand gebunden), TP-Link (Firmware offen) und OPNsense (T2). Der Auftrag verlangt „jeweils mit Softwarestand“; einen Stand zu erfinden wäre gegen die Vorgaben, der Grund steht jeweils in `version_source`.
- Siemens V4.6 hat `verified: false`, obwohl 103 die Siemens-Nutzungsbedingungen am Original gelesen hat: Die Datei selbst wurde nicht geöffnet (gleiche Regel wie in 105).
- Raspberry-Pi-Dokumentation: `redistribution: false`, obwohl CC BY-SA 4.0 die Weitergabe erlaubt – das Projekt gibt sie nach Frage 3 in 108 (Antwort A) nicht weiter, und die Testvorgabe lässt `true` nur für `BSD-2-Clause`/`public-domain` zu. Begründung in `terms.note`.
- Sprache der TP-Link-Anleitung als `en` angenommen (englische Herstellerseiten, Datei nicht geöffnet); vermerkt in `version_source`.
- Nicht aufgenommen, obwohl in der Quellen-Datei als Verweis geführt: englisches UR5e-Benutzerhandbuch 5.25.1, deutsches Software-Handbuch als HTML, ältere UR-Stände, Siemens-Ausgabe 11/2019, G2-Handbuch, Raspberry-Pi-Schaltplan, TP-Link-HTML-Anleitung. Der Auftrag nennt sie nicht. Das deutsche Software-Handbuch (HTML) könnte für Auftrag 112 als Verweis nützlich sein.
- Keine offenen Fragen an a7.
