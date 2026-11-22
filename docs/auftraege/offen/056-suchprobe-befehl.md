# Auftrag 056 – Suchprobe: Befehl `evaluate_search` und Probenliste

Meilenstein: M2 · Freigabestufe: B · Status: offen

## Ziel

Ein wiederholbarer Befehl misst, wie gut die Suche erwartete Fundstellen findet, getrennt nach Stichwort, Bedeutung und beidem zusammen. Er ist das Werkzeug für den Messlauf mit den echten Handbüchern (057) und den Abnahmelauf (060). Dieser Auftrag liefert nur Befehl, Probenliste und CI-Tests; gemessen wird in 057.

## Umfang

- `backend/twox/search/evaluation.py` (Berechnung) und Verwaltungsbefehl `backend/twox/search/management/commands/evaluate_search.py`:
  - liest eine Probenliste als JSON von der Standardeingabe;
  - je Probe: Anfrage (eigene Worte), erwartete Fundstellen als `manifest_id`, `sha256` der Datei und Seite(n), optional Gerät;
  - gibt je Probe und Art (Stichwort, Vektor, zusammen) aus: Rang der ersten richtigen Fundstelle, Treffer unter den ersten 5 und 10 (Recall@5, Recall@10), MRR und Antwortzeit; dazu Modellname, `TWOX_SECTION_MAX_CHARS` und Summen; Tabelle oder `--json`;
  - gibt nie Ausschnitte oder Abschnittstexte aus, nur Rang, Seite und Kennungen;
  - fehlt eine Datei mit der erwarteten Prüfsumme, zählt die Probe als „nicht eingelesen“, nicht als Fehler der Suche.
- Probenliste `backend/twox/search/probes/m2.json`, nur Verweise über `manifest_id`, `sha256` und Seite, keine Zitate (wie `testfactory/questions.yaml`):
  - IP `192.168.0.100` mit den Fundstellen aus Prüffrage 1 in `testfactory/questions.yaml`;
  - eine SPS-Adresse aus `testfactory/layout/devices.csv` mit der dort genannten Handbuchseite;
  - Prüffragen 1, 3, 7, 9 und 10 sinngemäß in eigenen Worten mit den Fundstellen aus `testfactory/questions.yaml` (Prüffrage 10 nach E-33);
  - nur Adressen und Seiten, die schon in `questions.yaml` oder `devices.csv` stehen.
- `deploy/compose/compose.yaml`, Dienst `backend-dev`: zusätzliche Einbindung `../../testfactory/manifest.yaml:/testfactory/manifest.yaml:ro`. Ein Test prüft, dass jede `manifest_id` und `sha256` der Probenliste im Manifest steht (das Manifest ist JSON-Schreibweise und wird mit `json` gelesen) und jede Seite in `questions.yaml` bzw. `devices.csv` belegt ist (`testfactory/layout` ist schon eingebunden; `questions.yaml` liegt unter `testfactory/` und wird gleich mit eingebunden).
- Tests (`backend/tests/search/test_evaluation.py`) mit Abschnitten aus eigenen Texten und Attrappe von `Embedder`: Rang, Recall und MRR an einem von Hand gerechneten Beispiel; „nicht eingelesen“; fehlerhafte Eingabe ergibt eine klare Meldung; die Ausgabe enthält keinen Abschnittstext.

## Nicht-Ziele

- Kein Lauf mit Herstellerunterlagen (057).
- Keine Antworten mit Sprachmodell, keine Prüffragen in der CI (M3, offener Punkt 6 bei a7).
- Keine Änderung der Voreinstellungen.

## Betroffene Bereiche (Ordner, Dateien)

- neu: `backend/twox/search/evaluation.py`, `backend/twox/search/management/__init__.py`, `backend/twox/search/management/commands/__init__.py`, `backend/twox/search/management/commands/evaluate_search.py`
- neu: `backend/twox/search/probes/m2.json`
- neu: `backend/tests/search/test_evaluation.py`, `backend/tests/search/test_probes.py`
- `deploy/compose/compose.yaml` (nur Dienst `backend-dev`, Einbindungen von `testfactory/manifest.yaml` und `testfactory/questions.yaml`, je `:ro`)

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-056`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18056` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Tests:
   - `D run --rm backend-dev pytest tests/search -v` endet mit Exit-Code 0.
   - `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen.
   - `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
3. `D run --rm backend-dev ruff check .` meldet `All checks passed!`, `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0, `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
4. Weitere Prüfungen wie in `ci.yml`, jeweils ohne Unterschied zum eingecheckten Stand:
   - `D run --rm backend-dev python manage.py makemessages -l de --add-location=file`, danach `git diff --exit-code -I '^"POT-Creation-Date:' -- backend/locale`;
   - `D run --rm backend-dev python manage.py makemigrations --check --dry-run` endet mit Exit-Code 0;
   - `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0;
   - `D run --rm -v "$PWD/web/openapi:/out" backend-dev python manage.py spectacular --file /out/schema.yml` (unter Git Bash mit vorangestelltem `MSYS_NO_PATHCONV=1`), danach `git diff --exit-code -- web/openapi`.
5. Auf leerer Datenbank: `D exec -T api python manage.py evaluate_search < backend/twox/search/probes/m2.json` endet mit Exit-Code 0 und meldet jede Probe als „nicht eingelesen“ (die Probenliste ist im Image nicht nötig, sie kommt über die Standardeingabe).
6. Abräumen: `D --profile dev down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: 050 ist nach `main` zusammengeführt.

- Welle 5, parallel zu 048 und 049. Einziger Auftrag seiner Zeit, der `compose.yaml` ändert.
- **Keine neue Abhängigkeit.**
- Herstellerunterlagen liegen nicht im Arbeitsverzeichnis (`testfactory/extern/` ist ungetrackt und nicht in `.worktreeinclude`); Fundstellen kommen nur aus `questions.yaml` und `devices.csv`. Keine Zitate, keine Ausschnitte von PDF-S. 38 der APS-Dokumentation (Standard-Zugangsdaten).
- fischertechnik-Material: laden ja, weitergeben nein (offener Punkt 3); deshalb nur Verweise.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
