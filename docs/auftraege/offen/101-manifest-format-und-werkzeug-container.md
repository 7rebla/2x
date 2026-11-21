# Auftrag 101 – Manifest-Format und Werkzeug-Container der Testfabrik

Meilenstein: T1 · Freigabestufe: C · Status: zur Prüfung

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

5. **(neu, vom Auftragsbearbeiter, 21.11.2026) Zwei Pflicht-Abhängigkeiten von mypy liegen außerhalb der Lizenzliste des Auftrags.** Geprüft an den Lizenzdateien und Metadaten der von PyPI installierten Pakete (mypy 2.4.1 unter Python 3.14.10):

   | Paket | Version | Lizenz | in der Liste (MIT, Apache-2.0, BSD, PostgreSQL)? |
   | --- | --- | --- | --- |
   | mypy | 2.4.1 | MIT (enthält typeshed unter Apache-2.0) | ja |
   | mypy_extensions | 1.2.0 | MIT | ja |
   | librt | 0.17.0 | MIT | ja |
   | ast-serialize | 0.13.1 | MIT (enthält Ruff-Teile unter MIT) | ja |
   | typing_extensions | 4.16.0 | PSF-2.0 | **nein** |
   | pathspec | 1.1.1 | MPL-2.0 | **nein** |

   Nach der Vorgabe dieses Auftrags („Lizenz außerhalb von MIT, Apache-2.0, BSD, PostgreSQL-Lizenz: nicht einbauen, Frage in den Auftrag“) ist mypy deshalb **nicht** ins Prüf-Image eingebaut. Ohne `pathspec` startet mypy nicht (ausprobiert: `ModuleNotFoundError: No module named 'pathspec'`); `typing_extensions` ist ebenfalls Pflicht.
   Einordnung: PSF-2.0 ist die Lizenz von Python selbst (freizügig, kein Copyleft). MPL-2.0 erlaubt Leitplanke 7 „nur als unverändert eingebundene Bibliothek und mit Eintrag im Entscheidungsprotokoll“. Beide Pakete wären nur im Prüf-Image als unverändertes Werkzeug vorhanden, nicht im eigenen Code und nicht in einer Auslieferung.
   - A: beide zulassen (pathspec als unveränderte MPL-Bibliothek nach Leitplanke 7, typing_extensions unter PSF-2.0 wie Python selbst), je mit Eintrag im Entscheidungsprotokoll. Dann wird im Dockerfile der unten stehende Block eingefügt; damit ist das letzte Akzeptanzkriterium erfüllt (mit genau diesem Block in einem nicht eingecheckten Probe-Image geprüft: `Success: no issues found in 4 source files`).
   - **Entschieden nach E-23, Option A** (Mitteilung der Leitstelle vom 21.11.2026; Beleg: `docs/DECISIONS.md` auf `main`, E-23: PSF-2.0 gilt als gleichwertig freizügig, pathspec ist benannte Ausnahme, beide schon mit Auftrag 001 eingetragen). Der Block unten ist eingebaut.
   - B: mypy nicht verwenden; ein anderes Typprüfwerkzeug wählen (ungeprüft, neue Abhängigkeit, die Aufrufform der T1-Aufträge ändert sich).
   - C: Typprüfung der Testfabrik bis Auftrag 114 zurückstellen und dort mit der M0-Werkzeugkette lösen. Auftrag 001 verwendet nach Abschnitt 5.2 erwartbar ebenfalls mypy und hat dann dieselbe Frage (ungeprüft).
   - Empfehlung: A.

   Block für `deploy/compose/testfactory.Dockerfile` bei Option A (ersetzt den Platzhalter-Kommentar):

   ```dockerfile
   # mypy (MIT) with all dependencies pinned. pathspec is MPL-2.0 and
   # typing_extensions is PSF-2.0; both are used unmodified as tools only.
   RUN pip install --no-cache-dir --disable-pip-version-check --root-user-action=ignore \
           mypy==2.4.1 \
           typing_extensions==4.16.0 \
           mypy_extensions==1.2.0 \
           pathspec==1.1.1 \
           librt==0.17.0 \
           ast-serialize==0.13.1
   ```

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Frage 5 ist nach E-23 mit Option A entschieden; mypy ist eingebaut, alle Akzeptanzkriterien sind erfüllt.

### Was wurde gebaut?

- `deploy/compose/testfactory.yaml`: Projekt `twox-testfactory`, Dienste `fetch`, `check`, `check-offline`, keine Ports. Repository als `/work`; bei `fetch` beschreibbar (für `extern/`), bei `check` und `check-offline` nur lesend. `__pycache__` und mypy-Cache landen nicht im Repository.
- `deploy/compose/testfactory.Dockerfile`: dasselbe Python-Image wie `fetch` plus mypy 2.4.1 mit allen fünf mitgezogenen Paketen in fester Version.
- `testfactory/__init__.py`, `testfactory/tests/__init__.py`, `testfactory/mypy.ini` (`strict`, `extern/` und `generated/` ausgeschlossen), `testfactory/manifest.yaml` (Grundgerüst, keine Einträge).
- `testfactory/manifest_tools.py` (nur Standardbibliothek): `load_manifest`, `parse_manifest`, Datenklassen `Manifest`, `Entry`, `Terms`, `dump_manifest`/`write_manifest` (stabile Form), `find_incomplete`, `address_problem` (die eine Adressprüfung), `tree_sha256`, `file_sha256`, `target_path`, Befehl `check [--complete] [PFAD]`. Alle Befunde einer Datei werden gesammelt gemeldet, je mit Eintrags-ID und Feldname.
- `testfactory/README.md` (Englisch): Ordner, Regeln aus 10.4, Aufrufe, jedes Feld aus den Punkten 6 und 7, Definition von `tree_sha256`.
- `testfactory/tests/test_manifest_tools.py`: 53 Tests, alle zwölf im Auftrag genannten Fälle.

### Wie wurde getestet?

Docker Engine 29.9.3, Compose v5.7.0. Aufrufe mit `-p twox-101`; `TF` wie im Auftrag.

| Akzeptanzkriterium | Ergebnis |
| --- | --- |
| `docker version`, `docker compose version` | erfüllt, Exit 0 |
| `TF build check` | erfüllt, Exit 0 |
| `TF run --rm fetch python -m testfactory.manifest_tools check` | erfüllt: `testfactory/manifest.yaml: OK (0 entries)`, Exit 0; `pip list` im Image zeigt nur `pip` |
| Tests in `check` | erfüllt: `Ran 53 tests`, `OK` |
| Tests in `check-offline` | erfüllt: `Ran 53 tests`, `OK`, keiner übersprungen |
| mypy in `check` | erfüllt: `Success: no issues found in 4 source files`, Exit 0 |
| `TF config --services`; kein `ports:` | erfüllt: `fetch`, `check`, `check-offline`; `git grep` findet nichts |
| `git diff --stat main...HEAD` | erfüllt: nur die neun Dateien aus „Betroffene Bereiche“ und diese Auftragsdatei |
| README beschreibt Felder und `tree_sha256` | erfüllt |

Alle Kriterien wurden nach dem Einbau von mypy noch einmal vollständig ausgeführt. Im ersten Durchlauf (vor der Entscheidung zu Frage 5) fehlte mypy im Image; die Typprüfung lief damals nur in einem nicht eingecheckten Probe-Image, das wieder gelöscht ist. Aufgeräumt mit `down -v`.

### Zweig und Arbeitsverzeichnis

- Zweig `worktree-agent-ad0f9207ee1267aaf`
- Arbeitsverzeichnis `.claude/worktrees/agent-ad0f9207ee1267aaf` (relativ zum Projektordner)

### Festlegungen über den Auftragstext hinaus (bitte prüfen)

Der Auftrag lässt einige Einzelheiten offen. So umgesetzt und in der README beschrieben:

- Fehlendes Feld und `null` bedeuten dasselbe; leere Zeichenketten sind nicht erlaubt (Ausnahme `language`). Unbekannte Felder und doppelte Schlüssel sind Fehler.
- `fetch` je `kind`: `file` und `git-archive` nur `auto` oder `manual`; `container-image`, `reference`, `local` nur `none`.
- `url` ist bei `git-archive` und `container-image` nicht erlaubt (der Auftrag nennt es nur für `file`, `reference`, `local`). `landing_page` ist überall erlaubt. Braucht Auftrag 104 bei `git-archive` eine eigene Archiv-Adresse, ist das eine Zeile in `_KINDS_BY_FIELD`.
- `reference` braucht mindestens eines von `url`, `landing_page`, `repository`. `branch` und `commit` verlangen `repository`.
- `terms`: `holder`, `license`, `redistribution`, `note`, `verified` sind Pflicht; `checked_on` ist Pflicht, wenn `verified` true ist.
- `target` ist innerhalb einer Datei eindeutig; kein `..`, kein absoluter Pfad, kein `\` oder `:`.
- `derived_from`: geprüft wird nur die Form der ID, nicht ob der Eintrag existiert (er kann in der anderen Manifest-Datei stehen).
- `size_bytes` ist auch bei `git-archive` erlaubt (Summe aller Dateien).
- Adressen dürfen keinen Benutzernamen und kein Kennwort enthalten.
- `tree_sha256`: Datensatz je Datei = Pfad (UTF-8), NUL-Byte, SHA-256 in Hex, LF; sortiert nach den Bytes des Pfads. Symbolische Links werden nie verfolgt; ein Link zählt als Datei mit dem Linkziel als Inhalt. So ist das Ergebnis gleich, egal ob ein Entpacker echte Links anlegt oder kleine Textdateien schreibt.
- `check` prüft nur das Format. Ob die Datei eines `local`-Eintrags vorhanden ist und zur Prüfsumme passt, prüft der Befehl nicht (nicht Teil dieses Auftrags; passt zu 104/108/109).

### Abweichungen

- mypy wurde erst nach der Entscheidung zu Frage 5 eingebaut (eigener Commit).
- Image-Tag: `python:3.14.10-slim-trixie` statt des im Auftrag genannten `3.14-slim`; es ist dasselbe Image (gleicher Digest), nur mit festem Patch-Stand und fester Debian-Ausgabe.
- Die drei Dienste teilen sich über YAML-Anker dieselben Einstellungen; `check-offline` kann das Image selbst bauen, wenn es fehlt.

### Vorschlag für das Entscheidungsprotokoll

Abhängigkeiten (alle am 21.11.2026 am Original geprüft: Registry-Abfrage für das Image, Lizenzdateien im Image und in den installierten Paketen):

| Name, Version | Lizenz | Zweck | Quelle |
| --- | --- | --- | --- |
| Docker-Image `python:3.14.10-slim-trixie`, Digest `sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f` (am Prüftag identisch mit `3.14-slim` und `3.14.10-slim`) | Python 3.14.10: PSF-2.0. Grundsystem Debian 13 „trixie“ mit 87 Paketen, darunter GPL-2, GPL-3, LGPL, BSD, MIT/Expat, ISC u. a. (laut `/usr/share/doc/*/copyright`). Mitgeliefert: pip 26.2.2 (MIT) | Laufzeit für Werkzeuge, Tests und Typprüfung der Testfabrik; unverändert benutzt, nicht Teil des eigenen Codes (Frage 4, Option A) | Docker Hub `library/python` |
| mypy 2.4.1 | MIT; mitgezogen: mypy_extensions 1.2.0 (MIT), librt 0.17.0 (MIT), ast-serialize 0.13.1 (MIT), typing_extensions 4.16.0 (PSF-2.0), pathspec 1.1.1 (MPL-2.0) | Typprüfung, nur in `check` und `check-offline` | PyPI |

Abweichungen von der Startunterlage:

- Zu Frage 1 (Abschnitte 5.2 und 6): Die Testfabrik hat einen eigenen kleinen Rahmen – Compose-Datei `deploy/compose/testfactory.yaml`, Tests unter `testfactory/tests` mit `unittest`, mypy per pip im Prüf-Image – statt pytest, uv und Ruff unter `backend/tests`. Grund: T1 hängt nicht am Django-Gerüst, und die Werkzeuge laufen im unveränderten Python-Image. Auftrag 114 hängt die Prüfungen in CI und Ruff ein.
- Zu Frage 2 (Abschnitt 10.3): `manifest.yaml` wird in JSON-Schreibweise geführt (gültiges YAML) und mit dem Modul `json` gelesen. Keine Abhängigkeit; keine Kommentare, dafür das Feld `notes`.
- Zu Frage 3 (Abschnitt 6): Die Ordnerübersicht wächst um `deploy/compose/testfactory.yaml` und `.Dockerfile`, `testfactory/__init__.py`, `manifest_tools.py`, `mypy.ini`, `README.md`, `testfactory/tests/`.
