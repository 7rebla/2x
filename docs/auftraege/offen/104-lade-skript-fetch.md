# Auftrag 104 – Lade-Skript fetch.py

Meilenstein: T1 · Freigabestufe: B · Status: zur Prüfung

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

**Nachtrag der Leitstelle (21.11.2026, aus der Prüfung von Auftrag 101):** Zusätzlich im Umfang, jeweils klein und mit Test, in `testfactory/manifest_tools.py`: (1) Vor dem Schreiben den aufgelösten Zielpfad gegen den aufgelösten `root` prüfen – kein symbolischer Link in der Kette, kein Ausbruch. (2) Das Ziel eines Eintrags darf nicht Präfix-Verzeichnis eines anderen Ziels sein (Prüfung auf Segmentgrenzen). (3) `tree_sha256` reicht nicht lesbare Unterverzeichnisse als Fehler weiter, statt sie zu überspringen. (4) `schema_version` nur als Ganzzahl (nicht 1.0, nicht "1"). (5) `size_bytes` auch bei `kind: reference` zulassen (README-Tabelle anpassen). (6) Bei `kind: file` mit `fetch: manual` ist `url` optional, dafür `landing_page` Pflicht. (7) Ein Unterbefehl, der eine Manifest-Datei in die kanonische Form bringt (lesen und unverändert zurückschreiben), mit Aufruf in der README. Der Dienst `fetch` schreibt als root in das eingebundene Repository – in der README vermerken.

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

**Status: zur Prüfung.** Keine offene Frage an a7. Alle Akzeptanzkriterien sind erfüllt bis auf eine erwartete Abweichung beim Diff-Umfang (siehe „Abweichungen“, Punkt 1).

### Was wurde gebaut?

- `testfactory/fetch.py` (nur Standardbibliothek, vollständig typisiert), Aufruf `python -m testfactory.fetch`. Schalter: `--only`, `--verify`, `--record`, `--dry-run`, `--strict`, `--manifest`, `--dest`, zusätzlich `--max-size MIB`.
  - `file`: Abruf in eine Zwischendatei unter `<root>/.fetch-partial/`, Prüfsumme beim Schreiben, erst bei Übereinstimmung an den Zielort. Bei Abweichung wird der Abruf verworfen; eine schon vorhandene ältere Datei bleibt liegen.
  - `git-archive`: Archiv des Commits nach dem Muster `https://github.com/OWNER/REPO/archive/COMMIT.tar.gz` (am 21.11.2026 an der GitHub-Dokumentation „Downloading source code archives“ geprüft: Beispiel mit Commit-ID, „.zip oder .tar.gz“), Entpacken ohne den obersten Ordner, `tree_sha256` prüfen, erst dann an den Zielort. Nur `github.com`.
  - `manual`, `local`, `container-image`, `reference` wie im Auftrag.
  - Sicherheit: jede Adresse und jedes Weiterleitungsziel läuft durch `manifest_tools.address_problem` (höchstens fünf Weiterleitungen, vom Skript selbst verfolgt); Zertifikatsprüfung; keine Proxy-Einstellungen aus der Umgebung, keine Cookies, keine Anmeldedaten; fester `User-Agent` `twox-testfactory-fetch/1.0`; 60 s ohne Daten bzw. eine Stunde je Versuch; drei Versuche mit Pause bei Netzfehlern und 408/425/429/5xx; Größenbegrenzung je Abruf (Standard 2048 MiB bzw. `size_bytes` des Eintrags), entpackt höchstens das Vierfache und höchstens 200 000 Archiveinträge; Abrufe nacheinander; nichts Geladenes wird ausgeführt.
  - Zusammenfassung als Tabelle (ID, Ergebnis, HTTP-Status, Größe), darunter je Eintrag eine erklärende Zeile. Exit 0/1/2.
- `testfactory/tests/test_fetch.py`: 51 Tests, alle zehn im Auftrag genannten Fälle, dazu Weiterleitungen, Größenbegrenzung, abgeschnittene Antwort, Wiederholung, symbolische Links, kaputte Archive.
- `testfactory/README.md`: Abschnitt „Fetching“ (Befehle, Schalter, Verhalten je Eintrag, Bedeutung der Ergebnisse, Sicherheit, Hinweis „Vendor documents never go into the repository“), dazu `format`, der Vermerk zum Dienst `fetch` als root und die geänderten Feldbeschreibungen.
- Nachtrag der Leitstelle in `testfactory/manifest_tools.py`, je mit Test in `test_manifest_tools.py` (17 neue Tests):
  1. `checked_target_path(root_dir, target)` und `root_path(...)`: kein symbolischer Link in der Kette unterhalb von `root`, aufgelöster Pfad muss unter dem aufgelösten `root` liegen, sonst `UnsafePathError`. `fetch.py` ruft das vor jedem Lesen und Schreiben eines Ziels auf.
  2. Ein Ziel darf nicht im Ziel eines anderen Eintrags liegen (Vergleich nach Pfadsegmenten, unabhängig von der Reihenfolge).
  3. `tree_sha256` reicht nicht lesbare Unterverzeichnisse als `OSError` weiter.
  4. `schema_version` nur als Ganzzahl (`1.0`, `"1"`, `true` werden abgelehnt).
  5. `size_bytes` ist bei `kind: reference` erlaubt; README-Tabelle angepasst.
  6. `kind: file` mit `fetch: manual`: `url` optional, `landing_page` Pflicht; mit `fetch: auto` bleibt `url` Pflicht.
  7. Unterbefehl `format [--check] [PFAD]` bringt eine Manifest-Datei in die kanonische Form; Aufruf in der README.

### Wie wurde getestet?

Docker Engine 29.9.3, Compose v5.7.0. Aufrufe mit `-p twox-104`, am Ende `down -v`. `TF` wie im Auftrag.

| Akzeptanzkriterium | Ergebnis |
| --- | --- |
| `docker version`, `docker compose version` | erfüllt, Exit 0 |
| `TF run --rm fetch python -m testfactory.fetch --help` | erfüllt, Exit 0; zeigt `--only`, `--verify`, `--record`, `--dry-run`, `--strict`, `--manifest`, `--dest` (und `--max-size`); `pip list` im Image zeigt nur `pip` |
| `TF run --rm fetch python -m testfactory.fetch --dry-run` | erfüllt, Exit 0: leere Tabelle, `0 entries`, `Dry run: nothing was loaded or written.` |
| Tests in `check` | erfüllt: `Ran 121 tests`, `OK (skipped=1)`; 51 davon aus `test_fetch` |
| Tests in `check-offline` | erfüllt: `Ran 121 tests`, `OK (skipped=1)` |
| mypy in `check` | erfüllt: `Success: no issues found in 6 source files` |
| `git grep -n "allow_insecure_loopback" -- testfactory/fetch.py` | erfüllt: 16 Treffer, nur Signaturen, Weitergaben und zwei Docstrings; `main()` nennt den Parameter nicht |
| `git check-ignore testfactory/extern/probe.pdf`; `git status --porcelain` | erfüllt: Pfad wird ausgegeben; nach den Tests keine Dateien unter `testfactory/extern/` |
| `git diff --stat main...HEAD` | **abweichend**: fünf Dateien plus diese Auftragsdatei, siehe Abweichung 1 |

Zusätzlich gelaufen:

- Der eine übersprungene Test (wirklich unlesbares Verzeichnis per `chmod 0`) wird übersprungen, weil der Container als root alles lesen darf. Mit `--user 1000:1000` in `check-offline`: `Ran 121 tests`, `OK`, keiner übersprungen. Als root deckt ein zweiter Test denselben Fall mit einem simulierten Lesefehler ab.
- Alle Tests einmal im Dienst `fetch` mit den Zwischendateien auf dem eingebundenen Repository-Laufwerk (unter dem ignorierten `testfactory/extern/`, danach gelöscht): `Ran 121 tests`, `OK (skipped=1)`. Verschieben, Ersetzen und Entpacken funktionieren also auch auf dem echten Ziel-Dateisystem.
- `TF run --rm fetch python -m testfactory.manifest_tools format --check`: `already in canonical form`, Exit 0.

**Nicht getestet:** ein echter Abruf über HTTPS. Die Tests laufen gegen `http://127.0.0.1`; fremde Quellen sollten in diesem Auftrag nicht geladen werden. Geprüft ist nur, dass das Image einen Zertifikatsspeicher hat (148 Stammzertifikate). Der erste echte Abruf in Auftrag 109 ist damit auch der erste Test von TLS, der Weiterleitung von `github.com` auf den Archiv-Server und der Annahme, dass GitHub-Archive genau einen obersten Ordner haben (ungeprüft).

### Zweig und Arbeitsverzeichnis

- Zweig `worktree-agent-a7c4adf558f0c7cc6`
- Arbeitsverzeichnis `.claude/worktrees/agent-a7c4adf558f0c7cc6` (relativ zum Projektordner)

### Festlegungen über den Auftragstext hinaus (bitte prüfen)

- **Symbolische Links in Archiven** werden nicht abgelehnt, sondern als kleine Datei mit dem Linkziel als Inhalt abgelegt. Es wird nie ein Link angelegt. Grund: Auftrag 101 definiert `tree_sha256` genau so, und ein Repository mit einem harmlosen Link wäre sonst nicht ladbar. Harte Links, Gerätedateien und Pipes lassen das ganze Archiv scheitern. Soll auch ein symbolischer Link zum Abbruch führen, ist das eine Zeile.
- **`auto`-Eintrag ohne Prüfsumme, ohne `--record`:** Es wird nichts geladen, Ergebnis `no-checksum`, Exit 1. So liegt nie etwas Ungeprüftes am Zielort.
- **`--record` bei Handabrufen:** Liegt die von Hand geholte Datei vor und fehlt die Prüfsumme, trägt `--record` sie ein. Ohne `--record` heißt das Ergebnis `unverified` (Exit 0).
- **Exit 1** auch bei falscher Prüfsumme eines `manual`- oder `local`-Eintrags und bei fehlender `local`-Datei, nicht nur bei `auto`. **Exit 2** bei ungültigem Manifest, unbekannter ID oder falschen Schaltern. `--dry-run` endet immer mit 0.
- `--verify` und `--record` schließen sich aus.
- Bei `--record` wird ein Abruf verworfen, dessen Größe einem schon eingetragenen `size_bytes` widerspricht.
- `write_manifest` schreibt bei `--record` die ganze Datei in kanonischer Form zurück, auch nach einem Abbruch (bis dahin berechnete Werte bleiben erhalten).
- Proxy-Einstellungen aus der Umgebung werden bewusst ignoriert. Braucht a7 einen Proxy, wäre das eine eigene Entscheidung.
- Bei (1) des Nachtrags darf `root` selbst über einen Link erreichbar sein (es wird aufgelöst); geprüft wird die Kette unterhalb von `root`.

### Abweichungen

1. **Diff-Umfang:** `git diff --stat main...HEAD` zeigt neben den drei genannten Dateien und dieser Auftragsdatei auch `testfactory/manifest_tools.py` und `testfactory/tests/test_manifest_tools.py`. Das folgt aus dem Nachtrag der Leitstelle; „Betroffene Bereiche“ und das Kriterium wurden dort nicht nachgezogen.
2. **README:** Außer dem Abschnitt „Fetching“ sind die vom Nachtrag verlangten Stellen geändert (Feldtabellen, `format`, Vermerk zu root, Hinweis zu `checked_target_path`).
3. **Zusätzlicher Schalter `--max-size MIB`** für die Größenbegrenzung (Standard 2048). Ohne ihn müsste für ein größeres Repository der Code geändert werden.
4. **Umfang:** rund 2500 neue Zeilen, davon etwa 1350 Tests. Das ist mehr, als sich in 15 Minuten prüfen lässt.
5. Der Kommentarkopf von `deploy/compose/testfactory.yaml` nennt `fetch.py` noch als „später“; die Datei liegt außerhalb des Auftragsbereichs und ist unverändert.

Bekannte Grenze: Das Entpacken begrenzt Anzahl und Gesamtgröße der Dateien, nicht aber die Größe einzelner Kopfdaten im Archiv; ein eigens präpariertes Archiv könnte dort Arbeitsspeicher belegen. Für Archive eines festen Commits von GitHub halte ich das für vertretbar.
