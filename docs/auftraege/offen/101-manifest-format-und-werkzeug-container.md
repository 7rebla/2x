# Auftrag 101 – Manifest-Format und Werkzeug-Container der Testfabrik

Meilenstein: T1 · Freigabestufe: C · Status: offen

## Ziel

Das Format der Manifest-Dateien steht fest, ist beschrieben und wird von einem kleinen Prüfwerkzeug maschinell geprüft. Es passt für beide Verwendungen: `testfactory/manifest.yaml` (geladene Herstellerunterlagen) und `testdata/klein/manifest.yaml` (eingecheckte freie Unterlagen, Auftrag 108). Dazu gibt es einen kleinen Container-Rahmen, in dem alle Werkzeuge, Tests und die Typprüfung der Testfabrik laufen, und eine einzige, in allen T1-Aufträgen wortgleich benutzte Aufrufform.

## Umfang

1. `deploy/compose/testfactory.yaml` (Projektname `twox-testfactory`, keine Host-Ports) mit drei Diensten. Das Repository wird als `/work` eingebunden, Arbeitsverzeichnis `/work`.
   - `fetch`: unverändertes offizielles Python-Image, ohne jede Nachinstallation. Darin laufen `manifest_tools.py` und später `fetch.py`.
   - `check`: Image aus `deploy/compose/testfactory.Dockerfile` = dasselbe Python-Image plus mypy (fest angegebene Version). Darin laufen Tests und Typprüfung.
   - `check-offline`: wie `check`, aber mit `network_mode: none` (Beleg, dass Tests kein Netz brauchen).
2. Paketform und Aufrufe (verbindlich für alle T1-Aufträge):
   - `testfactory/__init__.py` und `testfactory/tests/__init__.py` anlegen; Importe als `from testfactory import manifest_tools`.
   - Werkzeug: `python -m testfactory.manifest_tools …`
   - Tests: `python -m unittest discover -s testfactory/tests -t . -v`
   - Typprüfung: `mypy --config-file testfactory/mypy.ini testfactory`
3. `testfactory/mypy.ini`: `strict = True`; `testfactory/extern/` und `testfactory/generated/` sind ausgeschlossen (dort können fremde Python-Dateien liegen).
4. `testfactory/manifest.yaml`: Grundgerüst mit `schema_version`, `root` (hier `extern`) und leerer Liste `entries`. Die Einträge kommen in den Aufträgen 105 und 107.
5. `testfactory/manifest_tools.py` (nur Python-Standardbibliothek, vollständig typisiert): Laden und Prüfen, Datenklassen für Einträge, Zurückschreiben in stabiler Form (gleiche Eingabe ergibt byte-gleiche Ausgabe).
   - `python -m testfactory.manifest_tools check [PFAD]` prüft das Format (Standardpfad `testfactory/manifest.yaml`); Exit 0 bei gültig, sonst Exit 1 mit Eintrags-ID und Feldname.
   - `check --complete [PFAD]` schlägt zusätzlich fehl, wenn ein Eintrag mit `fetch: auto` oder `kind: local` keine Prüfsumme hat.
   - Die Adressprüfung steht an genau einer Stelle (eine Funktion). Erlaubt ist nur `https://`. `load_manifest(path, *, allow_insecure_loopback=False)` hat einen nur im Code setzbaren Parameter, der für Tests zusätzlich `http://127.0.0.1` und `http://localhost` zulässt. Die Befehlszeile kann ihn nicht setzen.
6. Felder der Datei: `schema_version`, `root` (Verzeichnis, auf das sich `target` bezieht, relativ zum Ordner der Manifest-Datei; `extern` für die Testfabrik, `.` für `testdata/klein`), `entries`.
7. Felder je Eintrag (Abschnitt 10.3 der Startunterlage: Quelle, Softwarestand, Prüfsumme, Nutzungshinweis, zugeordnetes Gerät; Repositories auf festen Commit):
   - `id` (eindeutig, klein, mit Bindestrichen), `title`, `language` (`de`, `en` oder leer)
   - `kind`: `file` (einzelne Datei per HTTPS) · `git-archive` (Repository-Stand auf festem Commit) · `container-image` (nur Name, Tag, Digest – wird nicht geladen) · `reference` (nur Verweis, wird nicht geladen) · `local` (Datei liegt im Repository unter `root`; nur für ausdrücklich freie Unterlagen)
   - `fetch`: `auto` · `manual` (Abruf von Hand, Datei wird nur geprüft) · `none`
   - Quelle: `url` (Pflicht bei `file`; bei `reference` und `local` die Herkunftsadresse), `landing_page`; `repository`, `branch`, `commit` (volle 40 Zeichen) – Pflicht bei `git-archive`, erlaubt bei `reference` und `local`; bei `container-image` `image`, `tag`, `digest`
   - `derived_from` (ID des Eintrags, aus dem die Datei erzeugt wurde) und `generated_by` (genauer Erzeugungsbefehl) – nur bei `local`, beide optional
   - `software_version` (Softwarestand der Anlage, zu dem die Unterlage gehört), `document_version` (Ausgabe/Datum der Unterlage), `version_source` (woher die Angabe stammt: Titelblatt, Dateiname, Tag …)
   - `sha256` (bei `file` und `local`), `tree_sha256` (bei `git-archive`), `size_bytes`. Bei `local` ist `sha256` Pflicht; bei `file` und `git-archive` dürfen die Werte bis zum Erstabruf (Auftrag 109) `null` sein
   - `target` (relativer Pfad unter `root`)
   - `terms`: `holder` (Rechteinhaber), `license` (SPDX-Kennung oder `proprietary`, `none-stated`, `public-domain`), `redistribution` (true/false), `terms_url`, `note` (Nutzungshinweis in einem Satz), `checked_on` (Datum), `verified` (true = am Original geprüft, false = ungeprüft)
   - `assigned_to`: Liste von `plant_id` oder `device_id` aus `testfactory/layout/devices.csv` (Auftrag 106); darf leer sein
   - `retrieved_on`, `notes`
8. `tree_sha256` in der README festlegen und in `manifest_tools.py` als Funktion bereitstellen: SHA-256 über die nach Pfad sortierte Liste aus relativem Pfad (POSIX-Schreibweise, UTF-8) und SHA-256 jeder Datei; Verzeichnisse, Zeitstempel und Rechte gehen nicht ein. So hängt die Prüfsumme nicht davon ab, wie GitHub das Archiv packt.
9. `testfactory/README.md` (Englisch, Entwicklerdoku): Zweck der Ordner nach Abschnitt 10.3, Feldbeschreibung, die Regeln aus Abschnitt 10.4, die Aufrufe aus Punkt 2.
10. Tests in `testfactory/tests/test_manifest_tools.py` (Standardbibliothek `unittest`): gültiges Beispiel je `kind` · fehlendes Pflichtfeld · doppelte `id` · falsche Commit-Länge · `http://`-Adresse wird abgelehnt · `allow_insecure_loopback` lässt nur Loopback zu · die Befehlszeile lehnt `http://` immer ab · `--complete` mit fehlender Prüfsumme · `local` ohne `sha256` wird abgelehnt · `reference` mit `repository` und `commit` ist gültig · stabile Ausgabe beim Zurückschreiben · `tree_sha256` an einem kleinen Verzeichnis.

## Nicht-Ziele

- Kein Herunterladen (Auftrag 104). Keine Manifest-Einträge (105, 107, 108). Keine Geräteliste (106).
- Keine Änderung an `.gitignore`, `.gitattributes`, `CLAUDE.md`, `docs/DECISIONS.md`, `docs/STATUS.md` oder an Dateien aus M0 (`backend/`, `web/`, andere Dateien unter `deploy/`).
- Kein CI-Workflow und kein Ruff; das übernimmt Auftrag 114, sobald M0 steht.

## Betroffene Bereiche (Ordner, Dateien)

- `deploy/compose/testfactory.yaml`, `deploy/compose/testfactory.Dockerfile`
- `testfactory/__init__.py`, `testfactory/mypy.ini`, `testfactory/manifest.yaml`, `testfactory/manifest_tools.py`, `testfactory/README.md`
- `testfactory/tests/__init__.py`, `testfactory/tests/test_manifest_tools.py`

## Akzeptanzkriterien (prüfbar)

In den Befehlen steht `TF` für `docker compose -f deploy/compose/testfactory.yaml`.

- `docker version` und `docker compose version` enden mit Exit 0 (sonst siehe Hinweise).
- `TF build check` endet mit Exit 0.
- `TF run --rm fetch python -m testfactory.manifest_tools check` gibt eine Erfolgsmeldung aus, Exit 0 – im unveränderten Python-Image (Beleg: nur Standardbibliothek).
- `TF run --rm check python -m unittest discover -s testfactory/tests -t . -v` endet mit `OK`.
- `TF run --rm check-offline python -m unittest discover -s testfactory/tests -t . -v` endet mit `OK`.
- `TF run --rm check mypy --config-file testfactory/mypy.ini testfactory` endet mit `Success: no issues found`.
- `TF config --services` listet genau `fetch`, `check`, `check-offline`; `git grep -n "ports:" -- deploy/compose/testfactory.yaml` findet nichts.
- `git diff --stat main...HEAD` zeigt nur die unter „Betroffene Bereiche“ genannten Dateien sowie die eigene Auftragsdatei unter `docs/auftraege/offen/`.
- `testfactory/README.md` beschreibt jedes Feld aus den Punkten 6 und 7 und die Definition von `tree_sha256`.

## Vorgaben und Hinweise

- Voraussetzung: keine. Das Grundgerüst der Leitstelle ist vorhanden (`.gitignore` schließt `testfactory/extern/` aus).
- Kein Push. Der Bearbeiter committet nur auf seinem Auftragszweig; die Leitstelle pusht auf a7s Freigabe (Vorgabe vom 21.11.2026, weicht von Abschnitt 8.2 Stufe A ab).
- Fehlt Docker (`docker version` endet nicht mit Exit 0): nichts unter Windows installieren oder ausführen, Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
- Mit der Freigabe der Auftragsliste genehmigt a7 genau diese zwei Abhängigkeiten; weitere sind nicht erlaubt:
  - offizielles Docker-Image `python` (Docker Hub, `library/python`). Python-Version: die in M0 (Auftrag 001, Frage zur Python-Version) festgelegte; von der Leitstelle am 21.11.2026 eingetragen: **Python 3.14** (Image `python:3.14-slim` mit festem Patch-Tag und Digest, an der Quelle zu prüfen; dieselbe Version wie in Auftrag 001). Geprüft am 21.11.2026: Tag `3.13-slim` existiert (zuletzt neu gebaut 08.11.2026). Genauen Patch-Tag und Digest an der Quelle prüfen und in Compose-Datei und Dockerfile fest angeben. Lizenz des Images und seiner Debian-Pakete: ungeprüft – am Original prüfen und im Kurzbericht nennen (siehe Frage 4).
  - `mypy` nur in den Diensten `check` und `check-offline`. Geprüft am 21.11.2026 an PyPI: Version 2.4.1, Lizenz MIT, verlangt Python 3.10 oder neuer. Mitgezogene Pakete laut PyPI: `typing_extensions`, `mypy_extensions`, `pathspec`, `librt`, `ast-serialize` – deren Lizenzen sind ungeprüft; am Original prüfen und im Kurzbericht auflisten. Alle Versionen fest angeben.
- Ergibt die Prüfung für ein Python-Paket eine Lizenz außerhalb von MIT, Apache-2.0, BSD, PostgreSQL-Lizenz (Leitplanke 7) oder ist sie nicht feststellbar: nicht einbauen, Frage in den Auftrag, Status „wartet auf a7“.
- Text für die Einträge im Entscheidungsprotokoll (je Abhängigkeit Name, Version, Lizenz, Zweck; dazu die Abweichungen aus den Fragen 1 und 3) im Kurzbericht vorschlagen. `docs/DECISIONS.md` pflegt die Leitstelle.
- Der Auftrag ist nach den Empfehlungen der Fragen unten geschrieben. Entscheidet a7 anders, passt die Leitstelle den Auftrag vor dem Start an.
- Tests laufen ohne Netz. Code, Bezeichner, Kommentare, README und Commit-Nachrichten auf Englisch. Jede Funktion mit Typangaben.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

1. **Eigener Rahmen für die Testfabrik?** Abschnitt 5.2 und 6 sehen Tests unter `backend/tests` mit pytest, uv und Ruff vor; nach Abschnitt 9 läuft T1 parallel zu M1, also nach M0.
   - A: eigener kleiner Rahmen wie oben (Compose-Datei unter `deploy/compose`, Tests unter `testfactory/tests` mit `unittest`, mypy per pip im Prüf-Image). Bewusste Abweichung von 5.2/6 mit Eintrag im Entscheidungsprotokoll. T1 hängt nicht am Django-Gerüst; `fetch.py` läuft in einem nackten Python-Image. Auftrag 114 hängt die Prüfungen nach M0 in CI und Ruff ein.
   - B: T1 erst nach M0 starten; Tests mit pytest unter `backend/tests`, Werkzeuge aus der M0-Kette. Die Aufträge 101 und 104 bis 114 werden dann vor dem Start umgeschrieben.
   - Empfehlung: A.
2. **Wie wird `manifest.yaml` gelesen?** Die Python-Standardbibliothek kann kein YAML lesen.
   - A: Bibliothek PyYAML (Lizenz ungeprüft) – normales YAML mit Kommentaren, aber eine neue Abhängigkeit, und `fetch.py` läuft nicht mehr im unveränderten Python-Image.
   - B: Die Datei bleibt `manifest.yaml`, wird aber in JSON-Schreibweise geführt (jedes JSON-Dokument ist gültiges YAML) und mit dem Modul `json` gelesen. Keine Abhängigkeit, automatisch zurückschreibbar; Nachteil: keine Kommentare, dafür das Feld `notes`.
   - C: Umbenennen in `manifest.toml` – weicht vom Dateinamen der Startunterlage ab.
   - Empfehlung: B.
3. **Erweiterung der Ordnerübersicht (Abschnitt 6) durch T1:** `deploy/compose/testfactory.yaml` und `.Dockerfile`, `testfactory/__init__.py`, `manifest_tools.py`, `mypy.ini`, `README.md`, `testfactory/tests/`, `testfactory/questions.yaml` (Auftrag 111), `testfactory/layout/evidence.md` (113), `testdata/klein/manifest.yaml` (108), `docs/testfabrik/` (102, 103).
   - A: so zustimmen; die Leitstelle ergänzt Abschnitt 6.
   - B: einzelne Orte anders festlegen (bitte nennen), zum Beispiel Compose-Datei und Dockerfile unter `testfactory/`.
   - Empfehlung: A.
4. **Basis-Image mit Debian-Paketen:** Das Python-Image enthält erwartbar auch GPL-lizenzierte Systemprogramme (ungeprüft). Es wird unverändert als Laufzeitumgebung benutzt und ist nicht Teil des eigenen Codes.
   - A: zulässig, mit Eintrag im Entscheidungsprotokoll (gleiche Regel wie für die Images in M0).
   - B: nicht zulässig – dann braucht T1 eine andere Laufzeit, Status „wartet auf a7“.
   - Empfehlung: A.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
