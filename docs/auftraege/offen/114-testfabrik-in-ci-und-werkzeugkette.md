# Auftrag 114 – Testfabrik-Prüfungen in CI und Werkzeugkette übernehmen

Meilenstein: T1 · Freigabestufe: B · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
