# Auftrag 107 – Manifest-Einträge: Standardgeräte, UR5e, URSim, OPNsense-Dokumentation

Meilenstein: T1 · Freigabestufe: C · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
