# Auftrag 065 – Frist für Einlese-Aufträge, deren Docling-Aufgabe nie startet

Meilenstein: M2 · Freigabestufe: B · Status: offen

Voraussetzung: 048 und 049 sind nach `main` zusammengeführt.

## Ziel

Die Frist eines Einlese-Auftrags zählt ab dem ersten `started` von Docling (046). Bleibt eine Docling-Aufgabe dauerhaft `pending` (Docling hängt, Warteschlange verloren), hat der Auftrag keine Frist: `poll` fragt weiter ab, schreibt bei jeder Abfrage `updated_at` (seit 048), und `ingest_versions --stuck` greift deshalb auch nicht. Nach diesem Auftrag endet ein solcher Auftrag nach einer festen Zeit mit `timeout`.

## Umfang

- `backend/twox/ingest/pipeline.py`, `_deadline_passed`: Gibt es kein `docling_started_at`, gilt eine Frist ab dem Einreichen bei Docling (bzw. ab `started_at` des Auftrags, falls kein eigener Zeitpunkt vorliegt) von `TWOX_INGEST_TIMEOUT_SECONDS`. Die bestehende Frist ab `docling_started_at` bleibt unverändert. Ergebnis bei Ablauf wie bisher `failed`/`timeout` mit verständlichem `error_detail` („Docling hat die Aufgabe nicht begonnen“ sinngemäß, Englisch im Code, übersetzt wie die übrigen Meldungen, falls Meldungen übersetzt werden).
- Docstring und Hilfe von `ingest_versions` (`--stuck`) an das Verhalten seit 048 anpassen: `poll` schreibt `updated_at` bei jeder Abfrage; `--stuck` erfasst Aufträge, die gar nicht mehr abgefragt werden (z. B. nach hartem Abbruch des Workers).
- Tests: Docling bleibt `pending` über die Frist → `timeout`; bleibt `pending` kürzer → weiter `running`; `started` später → Frist ab `docling_started_at` wie bisher; Fall „Docling war zwischen zwei Abfragen schon fertig“ (kein `started` gesehen) endet `done`.

## Nicht-Ziele

- Kein neues Datenbankfeld, keine Migration (falls für den Einreichezeitpunkt ein Feld fehlt: `started_at` des Auftrags verwenden und das im Kurzbericht begründen).
- Keine Änderung an Oberfläche oder API.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/ingest/pipeline.py`
- `backend/twox/ingest/management/commands/ingest_versions.py` (nur Docstring und Hilfe)
- `backend/tests/ingest/test_pipeline.py`, gegebenenfalls `backend/tests/ingest/test_ingest_versions_command.py`
- `backend/locale/de/LC_MESSAGES/django.po` (nur falls neue übersetzte Meldung)
- `docs/ARCHITECTURE.md` (nur der Satz zur Grenze „pending ohne Frist“)

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Alle Prüfungen des backend-Jobs aus `.github/workflows/ci.yml` sind grün.
2. Die vier Testfälle aus „Umfang“ bestehen.
3. `down -v` des eigenen Compose-Projekts endet mit Exit 0.

## Vorgaben und Hinweise

- Herkunft: Kurzbericht von 059 (Ungereimtheit 2), Entscheidung der Leitstelle.
- Tests nie gegen echtes Docling (`backend/tests/ingest/fake_converter.py`, `fake_docling.py`).

## Fragen an a7 (mit Optionen und Empfehlung)

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
