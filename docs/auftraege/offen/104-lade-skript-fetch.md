# Auftrag 104 – Lade-Skript fetch.py

Meilenstein: T1 · Freigabestufe: B · Status: offen

## Ziel

`testfactory/fetch.py` lädt alle Einträge des Manifests mit `fetch: auto` nach `testfactory/extern/`, prüft jede Datei gegen ihre Prüfsumme und meldet klar, was geladen, übersprungen, von Hand zu holen oder fehlgeschlagen ist. Das Skript braucht nur die Python-Standardbibliothek und läuft im Dienst `fetch` aus Auftrag 101.

## Umfang

1. `testfactory/fetch.py`, vollständig typisiert, nutzt `testfactory.manifest_tools` zum Lesen, Prüfen und Zurückschreiben. Aufruf: `python -m testfactory.fetch`.
2. Befehlszeile:
   - ohne Schalter: alle `auto`-Einträge laden und prüfen. Eine vorhandene Datei mit passender Prüfsumme wird übersprungen (zweiter Lauf ohne Netz möglich).
   - `--only ID [ID …]`: nur diese Einträge.
   - `--verify`: nichts laden, nur vorhandene Dateien gegen das Manifest prüfen.
   - `--record`: für Einträge ohne Prüfsumme laden, `sha256` bzw. `tree_sha256`, `size_bytes` und `retrieved_on` berechnen und ins Manifest zurückschreiben. Vorhandene Prüfsummen werden nie überschrieben.
   - `--dry-run`: nur anzeigen, was geschehen würde.
   - `--strict`: fehlende Handabrufe führen zu Exit 1.
   - `--manifest PFAD`, `--dest PFAD` (Standard `testfactory/manifest.yaml`; Ziel ist das im Manifest genannte `root`).
3. Verhalten je `kind`:
   - `file`: HTTPS-Abruf in eine Zwischendatei, Prüfsumme während des Schreibens, erst bei Übereinstimmung an den Zielort verschieben. Bei Abweichung: Datei verwerfen, Eintrag als fehlgeschlagen melden.
   - `git-archive`: Archiv des festen Commits von GitHub per HTTPS laden (Adressmuster für Archive eines Commits an der GitHub-Dokumentation prüfen), sicher entpacken, `tree_sha256` nach der Definition aus Auftrag 101 prüfen. Kein `git` nötig.
   - `container-image`, `reference`, `local` und alle mit `fetch: none`: nicht laden; `local` wird gegen `sha256` geprüft, die übrigen erscheinen in der Zusammenfassung als „nur Verweis“.
   - `fetch: manual`: nicht laden; liegt die Datei am Zielort, wird sie geprüft, sonst erscheint ein Hinweis mit `landing_page`.
4. HTTPS-Pflicht: Die Adressprüfung aus `manifest_tools` ist die einzige Stelle. Die Ladefunktionen reichen den nur im Code setzbaren Parameter `allow_insecure_loopback` durch (Standard `False`); es gibt dafür keinen Befehlszeilenschalter und keine Umgebungsvariable.
5. Zusammenfassung am Ende als Tabelle (ID, Ergebnis, HTTP-Status bei Fehler, Größe). Exit 0 nur, wenn jeder verlangte `auto`-Eintrag vorhanden ist und seine Prüfsumme passt; fehlende Handabrufe führen zu Exit 0 mit Warnung, außer mit `--strict`.
6. Tests in `testfactory/tests/test_fetch.py` (`unittest`, ohne Internet: ein lokaler `http.server` auf 127.0.0.1 in einem Thread liefert Testdateien aus einem temporären Verzeichnis; die Tests rufen die Funktionen mit `allow_insecure_loopback=True` auf): Erfolg · falsche Prüfsumme · Überspringen bei vorhandener Datei · `--record` schreibt die Prüfsumme und lässt vorhandene unverändert · `--verify` · Handabruf fehlt/liegt vor · Archiv mit Pfad außerhalb des Zielordners wird abgelehnt · HTTP-Fehler erscheint mit Status in der Zusammenfassung · Exit-Codes · **die Befehlszeile lehnt ein Manifest mit `http://`-Adresse immer ab, auch für 127.0.0.1**.
7. Abschnitt „Fetching“ in `testfactory/README.md` ergänzen (Englisch): Befehle, Bedeutung der Ergebnisse, Hinweis „Herstellerunterlagen nie ins Repository“.

## Nicht-Ziele

- Keine Manifest-Einträge schreiben (105, 107), kein echter Abruf fremder Quellen in diesem Auftrag (das ist 109).
- Kein Ziehen von Container-Images, kein Laden von ISO- oder Abbild-Dateien.
- Kein Entpacken von ZIP-Dateien der Hersteller; sie bleiben, wie sie sind.
- Keine neue Abhängigkeit. Stellt sich heraus, dass die Standardbibliothek nicht reicht: Frage in den Auftrag, Status „wartet auf a7“.
- Keine Änderung an `manifest_tools.py` über kleine, getestete Ergänzungen hinaus; größere Änderungen als Frage.

## Betroffene Bereiche (Ordner, Dateien)

- `testfactory/fetch.py`
- `testfactory/tests/test_fetch.py`
- `testfactory/README.md` (nur Abschnitt „Fetching“)

## Akzeptanzkriterien (prüfbar)

In den Befehlen steht `TF` für `docker compose -f deploy/compose/testfactory.yaml`.

- `docker version` und `docker compose version` enden mit Exit 0 (sonst siehe Hinweise).
- `TF run --rm fetch python -m testfactory.fetch --help` zeigt alle Schalter aus Punkt 2, Exit 0 – im unveränderten Python-Image.
- `TF run --rm fetch python -m testfactory.fetch --dry-run` läuft gegen das vorhandene Manifest mit Exit 0.
- `TF run --rm check python -m unittest discover -s testfactory/tests -t . -v` endet mit `OK`; die Tests aus Punkt 6 sind dabei.
- `TF run --rm check-offline python -m unittest discover -s testfactory/tests -t . -v` endet mit `OK` (Beleg: Tests brauchen kein Internet).
- `TF run --rm check mypy --config-file testfactory/mypy.ini testfactory` endet mit `Success: no issues found`.
- `git grep -n "allow_insecure_loopback" -- testfactory/fetch.py` zeigt den Parameter nur in Funktionssignaturen und Weitergaben, nicht in der Auswertung der Befehlszeile (Sichtprüfung).
- `git check-ignore testfactory/extern/probe.pdf` gibt den Pfad aus; `git status --porcelain` zeigt nach den Tests keine Dateien unter `testfactory/extern/`. Gibt `git check-ignore` nichts aus: nicht selbst ändern, im Kurzbericht melden, Status „wartet auf a7“ (die `.gitignore` gehört der Leitstelle).
- `git diff --stat main...HEAD` zeigt nur die drei genannten Dateien sowie die eigene Auftragsdatei unter `docs/auftraege/offen/`.

## Vorgaben und Hinweise

- Voraussetzung: Auftrag 101 ist zusammengeführt. Läuft gleichzeitig mit 105 und 106; `testfactory/manifest.yaml` wird hier nicht geändert.
- Kein Push. Der Bearbeiter committet nur auf seinem Auftragszweig; die Leitstelle pusht auf a7s Freigabe (Vorgabe vom 21.11.2026, weicht von Abschnitt 8.2 Stufe A ab).
- Fehlt Docker: nichts unter Windows installieren oder ausführen, Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
- Sicherheit: nur `https://`; Weiterleitungen nur auf `https://`; Zeitlimit je Abruf; höchstens wenige Wiederholungen mit Pause; Abrufe nacheinander, nicht gleichzeitig. Geladene Inhalte werden nie ausgeführt. Tar-Archive mit dem Daten-Filter der Standardbibliothek entpacken; Pfade außerhalb des Zielordners, Verknüpfungen und Gerätedateien ablehnen.
- Keine persönlichen Angaben in Anfragen: fester, neutraler `User-Agent` ohne Namen, E-Mail oder Rechnerangaben. Keine Anmeldedaten, keine Cookies.
- Die fischertechnik-Server liefern weder `Last-Modified` noch `ETag`; allein die eigene Prüfsumme entscheidet.
- Große Dateien blockweise lesen und schreiben, nicht im Speicher halten.
- Stufe B gilt nur, solange keine Abhängigkeit hinzukommt und das Manifest-Format aus Auftrag 101 unverändert bleibt. Hat a7 bei Auftrag 101 die Variante PyYAML gewählt, wird dieser Auftrag Stufe C.
- Code, Kommentare, Hilfetexte und Commit-Nachrichten auf Englisch.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
