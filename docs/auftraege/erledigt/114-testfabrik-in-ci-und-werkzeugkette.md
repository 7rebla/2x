# Auftrag 114 – Testfabrik-Prüfungen in CI und Werkzeugkette übernehmen

Meilenstein: T1 · Freigabestufe: B · Status: erledigt

## Ziel

Die Tests, die Typprüfung und die Manifest-Prüfungen der Testfabrik laufen bei jeder Änderung in der CI mit, und der Code unter `testfactory/` hält die Ruff-Regeln des Projekts ein. Damit ist die Lücke zwischen dem eigenen Rahmen aus Auftrag 101 und der Werkzeugkette aus M0 geschlossen.

## Umfang

1. In der CI-Datei aus dem M0-Auftrag zur CI (laut Entwurf `.github/workflows/ci.yml`; an der zusammengeführten Datei prüfen) einen Job `testfactory` ergänzen, der ohne Zugriff auf fremde Downloads läuft:
   - `TF build check`
   - `TF run --rm check-offline python -m unittest discover -s testfactory/tests -t . -v`
   - `TF run --rm check mypy --config-file testfactory/mypy.ini testfactory`
   - `TF run --rm fetch python -m testfactory.manifest_tools check`
   - `TF run --rm fetch python -m testfactory.manifest_tools check --complete testdata/klein/manifest.yaml`
   - die Ruff-Aufrufe aus Punkt 2
2. Ruff für `testfactory/`: Ruff in genau der Version, die M0 festgelegt hat (aus `backend/pyproject.toml` bzw. `backend/uv.lock` ablesen), in das Prüf-Image `deploy/compose/testfactory.Dockerfile` aufnehmen. Einstellungen aus M0 verwenden (`--config backend/pyproject.toml`, sofern dort Ruff-Einstellungen stehen; sonst Standardeinstellungen, im Kurzbericht nennen). Befunde im Code unter `testfactory/` beheben, ohne das Verhalten zu ändern.
3. Tests, die geladene Dateien unter `testfactory/extern/` brauchen, darf es nicht geben; findet sich einer, wird er so umgebaut, dass er ohne `extern/` grün ist, oder die Abweichung wird als Frage gemeldet.
4. Abschnitt „Checks“ in `testfactory/README.md` (Englisch): die Befehle aus Punkt 1 und 2 und der Hinweis, dass derselbe Satz in der CI läuft.

## Nicht-Ziele

- Kein Umzug der Tests nach `backend/tests`, kein Wechsel auf pytest oder uv (das wäre Option B der Frage 1 in Auftrag 101).
- Kein Abruf fremder Quellen in der CI; `fetch` wird dort nicht ausgeführt.
- Keine Prüffragen-Läufe mit einem Sprachmodell (M3; wie sie in der CI laufen, klärt ein M0-Auftrag).
- Keine Änderung an den übrigen CI-Jobs, an Lizenzprüfung oder Geheimnissuche.
- Keine neue Abhängigkeit über das in M0 genehmigte Ruff hinaus.

## Betroffene Bereiche (Ordner, Dateien)

- `.github/workflows/ci.yml` (nur der neue Job `testfactory`)
- `deploy/compose/testfactory.Dockerfile` (nur Ruff)
- `testfactory/**/*.py` (nur Ruff-Korrekturen), `testfactory/README.md` (nur Abschnitt „Checks“)

## Akzeptanzkriterien (prüfbar)

In den Befehlen steht `TF` für `docker compose -f deploy/compose/testfactory.yaml`.

- `docker version` und `docker compose version` enden mit Exit 0 (sonst siehe Hinweise).
- `TF build check` endet mit Exit 0.
- `TF run --rm check ruff check testfactory` endet mit `All checks passed!`; `TF run --rm check ruff format --check testfactory` endet mit Exit 0.
- `TF run --rm check-offline python -m unittest discover -s testfactory/tests -t . -v` endet mit `OK` – auch in einem frischen Arbeitsverzeichnis ohne `testfactory/extern/`.
- `TF run --rm check mypy --config-file testfactory/mypy.ini testfactory` endet mit `Success: no issues found`.
- `TF run --rm fetch python -m testfactory.manifest_tools check` und derselbe Befehl mit `check --complete testdata/klein/manifest.yaml` enden mit Exit 0.
- `git grep -n "testfactory" -- .github/workflows/ci.yml` zeigt den Job mit allen Befehlen aus Umfang 1.
- `git diff main...HEAD -- .github/workflows/ci.yml` zeigt nur hinzugefügte Zeilen des Jobs `testfactory`.
- `git diff --stat main...HEAD` zeigt nur die unter „Betroffene Bereiche“ genannten Dateien sowie die eigene Auftragsdatei unter `docs/auftraege/offen/`.
- Nach dem Push durch die Leitstelle (auf a7s Freigabe) prüft die Leitstelle: Der Job `testfactory` ist im Lauf der CI grün. Bis dahin bleibt der Auftrag „zur Prüfung“.

## Vorgaben und Hinweise

- Voraussetzung: Auftrag 101, alle T1-Aufträge mit Tests (zuletzt 112 und 113) und der M0-Auftrag zur CI (im Entwurf Nummer 011) sind zusammengeführt. Hat a7 bei Frage 1 in Auftrag 101 Option B gewählt, entfällt dieser Auftrag.
- Kein Push. Der Bearbeiter committet nur auf seinem Auftragszweig; die Leitstelle pusht auf a7s Freigabe (Vorgabe vom 21.11.2026, weicht von Abschnitt 8.2 Stufe A ab).
- Fehlt Docker: nichts unter Windows installieren oder ausführen, Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
- Ruff ist in Abschnitt 5.2 vorgesehen und wird in M0 eingeführt; hier kommt nur dieselbe Version in ein zweites Image. Lizenz und Version nicht aus dem Gedächtnis, sondern aus dem Eintrag im Entscheidungsprotokoll von M0 übernehmen. Steht dort kein Eintrag: nicht einbauen, Frage in den Auftrag, Status „wartet auf a7“.
- Stufe B gilt nur, solange keine weitere Abhängigkeit hinzukommt, die übrigen CI-Jobs unverändert bleiben und die Ruff-Korrekturen kein Verhalten ändern (alle Tests bleiben unverändert grün). Sonst Stufe C.
- Die Namen und Pfade aus M0 (CI-Datei, Ruff-Einstellungen) sind hier nach dem Entwurfsstand genannt; maßgeblich ist der zusammengeführte Stand. Weicht er ab, im Kurzbericht nennen.
- Code, Kommentare, README und Commit-Nachrichten auf Englisch.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Keine offene Frage an a7. Alle lokal prüfbaren Kriterien sind erfüllt; der Lauf auf GitHub ist offen bis nach dem Push durch die Leitstelle. Die Ruff-Kriterien gelten mit `--config backend/pyproject.toml` (Umfang 2), siehe Abweichung 1.

### Was wurde gebaut?

- `deploy/compose/testfactory.Dockerfile`: zusätzlich `ruff==0.17.6` (Version aus `backend/uv.lock`, Lizenz MIT laut Eintrag von Auftrag 001 in `docs/DECISIONS.md`; keine mitgezogenen Pakete). `RUFF_CACHE_DIR=/tmp/ruff_cache`, weil das Repository nur lesend eingebunden ist.
- Ruff-Korrekturen unter `testfactory/` mit den Einstellungen aus `backend/pyproject.toml` (`[tool.ruff]`: Python 3.14, Zeilenlänge 100, Regeln E, W, F, I, N, UP, B, C4, SIM, ANN, DJ, RUF): `ruff format` (11 Dateien), dazu 6 automatische und 16 Handkorrekturen ohne Verhaltensänderung – `contextlib.suppress`, geteilter f-String, `DEFAULT_OPTIONS` auf Modulebene statt `Options()` als Standardwert, `ClassVar` für eine Testtabelle, `object` statt `Any`, zusammengefasste `with`-Anweisungen, f-String statt `%`, Gedankenstrich in einem Test als `–` (gleicher Wert). Ein `# noqa: B009` in `test_fetch.py`: `getattr(..., "handlers")` bleibt, weil das Attribut in den Typ-Stubs fehlt und mypy sonst scheitert (Muster wie `# noqa` im Backend).
- `.github/workflows/ci.yml`: neuer Job `testfactory` am Ende von `jobs:` (ubuntu-24.04, 15 min, `actions/checkout` per SHA wie in den anderen Jobs, `persist-credentials: false`). Schritte: Versionen, `build check`, `ruff check`, `ruff format --check`, mypy, unittest in `check-offline`, `manifest_tools check` und `format --check` für `testfactory/manifest.yaml`, `check --complete` und `format --check` für `testdata/klein/manifest.yaml`, zuletzt `test ! -e testfactory/extern`. Der Pfad der Compose-Datei steht in jedem Befehl, damit `git grep` jeden Befehl zeigt. Bestehende Jobs unverändert.
- `testfactory/README.md`: neuer Abschnitt „Checks“ mit allen Befehlen und dem Hinweis, dass derselbe Satz in der CI läuft.

### Wie wurde getestet?

Docker Engine 29.9.3, Compose v5.7.0, Projektname `twox-114` (am Ende `down -v`). Jeder `run`-Schritt des Jobs wurde per awk aus `ci.yml` in ein bash-Skript übertragen (je Schritt eigene Subshell mit `set -e`) und in einem frischen Klon des Zweigs ohne `testfactory/extern/` ausgeführt; Klon und Skript danach gelöscht.

| Akzeptanzkriterium | Ergebnis |
| --- | --- |
| `docker version`, `docker compose version` | erfüllt, Exit 0 |
| `TF build check` | erfüllt, Exit 0 |
| `ruff check` (mit `--config backend/pyproject.toml`) | erfüllt: `All checks passed!` |
| `ruff format --check` (mit `--config …`) | erfüllt: `18 files already formatted`, Exit 0 |
| unittest in `check-offline` | erfüllt: `Ran 215 tests`, `OK (skipped=1)`, im Arbeitsverzeichnis und im frischen Klon ohne `extern/` |
| mypy | erfüllt: `Success: no issues found in 14 source files` |
| `manifest_tools check`; `check --complete testdata/klein/manifest.yaml` | erfüllt: `OK (31 entries)` bzw. `OK (10 entries)`, Exit 0 |
| `git grep -n "testfactory" -- .github/workflows/ci.yml` | erfüllt: 14 Zeilen, alle Befehle aus Umfang 1 und 2 |
| `git diff main...HEAD -- .github/workflows/ci.yml` | erfüllt: 0 entfernte Zeilen, nur der Job `testfactory` |
| `git diff --stat main...HEAD` | erfüllt: nur `ci.yml`, `testfactory.Dockerfile`, `testfactory/**/*.py`, `testfactory/README.md` und diese Auftragsdatei |
| Job `testfactory` auf GitHub grün | offen, nach dem Push |

Lokale Laufzeit des ganzen Jobs: 41 s (Images im Build-Cache; auf GitHub wird kalt gebaut: Python-Image ziehen, mypy und Ruff per pip).

Zusatzprüfungen: Testliste vor und nach den Ruff-Korrekturen verglichen (Stand `main` gegen Zweig): dieselben 215 Tests, alle grün. Mit `--user 1000:1000` in `check-offline`: `Ran 215 tests`, `OK`, keiner übersprungen. Ruff-Version im Image: `ruff 0.17.6`. Syntax von `ci.yml` mit PyYAML geprüft: Jobs `backend`, `web`, `testfactory`.

**Tests in der CI:** alle 215 Tests aus allen zehn Modulen (`test_crossrefs` 5, `test_evidence` 10, `test_fetch` 55, `test_layout` 19, `test_manifest_aps` 12, `test_manifest_other` 13, `test_manifest_states` 5, `test_manifest_tools` 70, `test_questions` 17, `test_testdata_klein` 9). Keiner braucht `testfactory/extern/`: Sie lesen nur eingecheckte Dateien (`testfactory/manifest.yaml`, `layout/`, `questions.yaml`, `docs/testfabrik/quellen-fertigungslinie.md`, `testdata/klein/`) oder arbeiten in temporären Verzeichnissen mit einem lokalen Testserver; `check-offline` hat kein Netz. Übersprungen wird nur `test_really_unreadable_subdirectory_is_an_error`, weil der Container als root läuft und root jedes Verzeichnis lesen darf (bekannt aus 104; der Fall ist zusätzlich simuliert in `test_unreadable_subdirectory_is_an_error`). Umbauten nach Umfang 3 waren nicht nötig. Nicht in der CI: `fetch.py` (lädt Herstellerunterlagen) und Prüffragen mit Sprachmodell (Nicht-Ziele).

### Zweig und Arbeitsverzeichnis

Zweig `worktree-agent-af5905f66909a58d9`, Arbeitsverzeichnis `.claude/worktrees/agent-af5905f66909a58d9`. Nicht gepusht.

### Abweichungen

1. **Ruff ohne `--config`.** Die Kriterien nennen `ruff check testfactory` und `ruff format --check testfactory` ohne `--config`. Ohne diesen Schalter findet Ruff keine Einstellungen (im Wurzelverzeichnis liegt keine `pyproject.toml`) und nimmt seine Standardregeln: dann 17 Befunde (u. a. EXE002, weil Dateien auf dem Windows-Laufwerk im Container als ausführbar erscheinen, ISC004, FURB167) und 9 Dateien mit anderer Zeilenlänge. Nach Umfang 2 laufen CI und README mit `--config backend/pyproject.toml`; damit sind beide Kriterien erfüllt.
2. **README außerhalb von „Checks“:** Ein Codebeispiel unter „Using the module“ ist umbrochen, weil `ruff format` auch Python-Blöcke in Markdown prüft. Inhalt unverändert.
3. **Mehr Schritte als in Umfang 1:** zusätzlich `manifest_tools format --check` für beide Manifeste (Hinweis der Leitstelle) und der Schlussschritt `test ! -e testfactory/extern`.
4. **Aus dem Netz** lädt der Job nur Werkzeuge: das Python-Image (Docker Hub) und mypy/Ruff (PyPI) beim Bau. Keine Herstellerunterlagen.
5. Vorschlag für `docs/DECISIONS.md` (pflegt die Leitstelle): „ruff 0.17.6 im Prüf-Image der Testfabrik | MIT | Lint und Formatprüfung der Testfabrik-Skripte (zweiter Einbauort, dieselbe Version wie in 001) | 114 | nach E-23“.
