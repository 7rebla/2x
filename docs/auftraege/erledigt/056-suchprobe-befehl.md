# Auftrag 056 – Suchprobe: Befehl `evaluate_search` und Probenliste

Meilenstein: M2 · Freigabestufe: B · Status: erledigt

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

- **Nachtrag der Leitstelle (E-59, KI optional):** Einbettungen, Vektorsuche und alles, was ein Modell braucht, sind eine aktivierbare Zusatzfunktion. Schalter `TWOX_AI_ENABLED` (Einstellung in `settings.py`, Standard `False`; `.env.example` mit Kommentar). Bei „aus“: kein Aufruf von Ollama, keine Einbettungs-Aufgaben, Einlesen endet nach den Abschnitten erfolgreich, die Suche arbeitet nur mit der Stichwortsuche, Selbsttest und Oberfläche zeigen „KI nicht aktiviert“ als neutralen Zustand (kein Fehler, kein Warnsymbol). Jede KI-abhängige Stelle braucht einen Test für beide Zustände; die CI läuft mit „aus“ und mit „an“ plus Attrappe.

Voraussetzung: 050 ist nach `main` zusammengeführt.

- Welle 5, parallel zu 048 und 049. Einziger Auftrag seiner Zeit, der `compose.yaml` ändert.
- **Keine neue Abhängigkeit.**
- Herstellerunterlagen liegen nicht im Arbeitsverzeichnis (`testfactory/extern/` ist ungetrackt und nicht in `.worktreeinclude`); Fundstellen kommen nur aus `questions.yaml` und `devices.csv`. Keine Zitate, keine Ausschnitte von PDF-S. 38 der APS-Dokumentation (Standard-Zugangsdaten).
- fischertechnik-Material: laden ja, weitergeben nein (offener Punkt 3); deshalb nur Verweise.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

- **Was wurde gebaut?**
  - `backend/twox/search/evaluation.py`: Probenliste lesen und prüfen (`load_probes`, klare Meldungen mit Fundort wie `probes[0].expected[0].sha256: …`), Messung über die Such-Schnittstelle, Auswertung und Ausgabe. Drei Listen je Probe: Stichwort (Suche über `get_search_backend()` mit `override_settings(TWOX_AI_ENABLED=False)` für genau diese Anfrage), Vektor (`embed_query` + `nearest_sections` aus `postgres.py`, Abschnitte mit gleichem Rang = gleicher Abstand zu einem Eintrag zusammengefasst), zusammen (Suche wie für Nutzer). Je Probe und Art: Rang der ersten richtigen Fundstelle (innerhalb der ersten 50 = `VECTOR_CANDIDATES`), Zahl richtiger Einträge unter den ersten 5 und 10, Kehrwert des Rangs, Zeit, `manifest_id` und Seite der ersten richtigen Fundstelle. Je Art: Recall@5 und Recall@10 (Anteil gemessener Proben mit richtigem Eintrag unter den ersten 5 bzw. 10), MRR, Gesamt- und Mittelzeit; dazu Modellname und `TWOX_SECTION_MAX_CHARS`. Richtig ist ein Eintrag, wenn ein Fundort die erwartete Prüfsumme, eine erwartete Seite im Seitenbereich und (falls angegeben) das erwartete Gerät hat.
  - „Nicht eingelesen“: keine Dokumentversion (Art „Dokument“) mit der Prüfsumme hat Abschnitte. Solche Proben werden gar nicht gesucht (kein Modellaufruf) und zählen nicht gegen die Suche; bei teilweise eingelesenen Proben wird gegen die vorhandenen Dateien gemessen und der Rest genannt.
  - E-59: KI aus → nur Stichwort gemessen, Vektor und zusammen „not measured: AI features not enabled“, eigene Hinweiszeile, Ollama wird nie angesprochen. KI an, Modell fällt aus → Vektor und zusammen „not measured: model service not available“.
  - Befehl `evaluate_search` (Tabelle oder `--json`), liest UTF-8 von der Standardeingabe (BOM wird entfernt), Terminal ohne Umleitung und kaputte Eingabe enden mit `CommandError` und Exit-Code 1. Ausgegeben werden nur Kennungen, Ränge, Seiten, Zahlen – weder Abschnittstexte noch Ausschnitte noch die Anfragen.
  - `backend/twox/search/probes/m2.json`: 7 Proben, nur Verweise (`manifest_id`, `sha256`, Seiten, Feld `basis` mit Prüffrage oder Gerät): IP `192.168.0.100` (Prüffrage 1: PDF-S. 18, 31, 38), SPS Bohrstation `192.168.0.50` (`devices.csv` drill-plc: PDF-S. 38), Prüffragen 1, 3, 7, 9, 10 in eigenen Worten mit allen PDF-Seiten ihrer Quellen (10 nach E-33, mit `ur5e-software-handbook-en` S. 46). Quellen in den Git-Repositorien (Zeilenangaben, keine Prüfsumme) sind weggelassen.
  - `deploy/compose/compose.yaml`, nur `backend-dev`: `testfactory/manifest.yaml` und `testfactory/questions.yaml` je `:ro`.
- **Wie wurde getestet?** `tests/search/test_evaluation.py` (32 Tests: Rang/Zählungen/RR und Recall@5/10/MRR an von Hand gerechneten Beispielen, Seitenbereiche und Gerät, Tiefe 50; gegen die Datenbank mit eigenen Texten: KI aus nur Stichwort ohne Modellaufruf, KI an mit `FakeEmbedder` alle drei Listen mit von Hand bestimmten Rängen, Modellausfall, nicht/teilweise eingelesen, Datei ohne Abschnitte; Befehl: Tabelle, JSON, keine Abschnittstexte/Wörter/Anfragen in der Ausgabe, 12 fehlerhafte Eingaben mit klarer Meldung, UTF-8/BOM). `tests/search/test_probes.py` (6 Tests: Probenliste gültig, jede `manifest_id`/`sha256` im Manifest, jede Seite in `questions.yaml` bzw. `devices.csv` belegt und umgekehrt alle PDF-Seiten der Prüffrage erwartet, Prüffragen 1/3/7/9/10 in eigenen Worten, Adressen aus `questions.yaml`/`devices.csv`).
  - Akzeptanzkriterien mit `-p twox-056`, `TWOX_API_PORT=18056`: 0 Docker vorhanden; 1 build und up Exit 0; 2 `pytest tests/search -v` 238 passed, `pytest` 1851 passed / 5 deselected / 0 failed / 0 skipped, `pytest -m worker` 5 passed; 3 ruff `All checks passed!`, format ohne Änderung, mypy `Success: no issues found in 166 source files`; 4 makemessages ohne Unterschied, makemigrations „No changes detected“, Lizenzprüfung bestanden, OpenAPI ohne Unterschied; 5 `D exec -T api python manage.py evaluate_search < backend/twox/search/probes/m2.json` Exit 0, alle 7 Proben „not ingested“ („Not ingested: 7 of 7 probes“), auch mit `--json`; fehlerhafte Liste Exit 1 mit Meldung; 6 `down -v` Exit 0.
- **Zweig und Arbeitsverzeichnis:** Zweig `worktree-agent-a2610cacabe013069`, Arbeitsverzeichnis `.claude/worktrees/agent-a2610cacabe013069`.
- **Abweichungen:**
  - Ausgabe auf Englisch wie die übrigen Befehle: „not ingested“ statt „nicht eingelesen“, JSON-Status `not_ingested`.
  - Recall@k ist als Trefferquote je Probe definiert (mindestens eine richtige Fundstelle unter den ersten k), nicht als Anteil aller erwarteten Seiten; die Zahl richtiger Einträge unter den ersten 5/10 steht zusätzlich je Probe.
  - In der Tabelle steht bei nicht eingelesenen Proben die fehlende `manifest_id` in der letzten Spalte (Überschrift „first correct place“), ein kleiner Schönheitsfehler.
  - Die Stichwortliste nutzt `django.test.utils.override_settings` im Produktcode, um die KI für eine Anfrage abzuschalten, weil `postgres.py` und `interface.py` nicht geändert werden sollten; mit 052 ließe sich das durch einen Schalter in `SearchRequest` ersetzen.
  - README nicht ergänzt (nicht im Bereich des Auftrags); die Bedienung steht im Docstring des Befehls.
  - Keine offenen Fragen.
