# Auftrag 061 – Einbettungsaufträge im Feld `ingest`

Meilenstein: M2 · Freigabestufe: B · Status: offen

Voraussetzung: 048 und 051 sind nach `main` zusammengeführt.

## Ziel

Das Feld `ingest` einer Version (051) zeigt den neuesten Einlese-Auftrag. Aufträge aus `embed_sections` (048) sind reine Einbettungsaufträge. Werden sie zum neuesten Auftrag, gehen Seitenzahl und Hinweis auf eine Teilumwandlung verloren, und ein Fehler beim Einbetten sieht in der Oberfläche wie ein gescheitertes Einlesen aus. Nach diesem Auftrag bleibt die Anzeige richtig.

## Umfang

- Ein Auftrag aus `embed_sections` übernimmt beim Anlegen `page_count` und einen etwaigen Teilumwandlungs-Hinweis (`error_detail` mit dem Präfix aus `pipeline.PARTIAL_DETAIL_PREFIX`) aus dem letzten erfolgreichen Umwandlungs-Auftrag derselben Version.
- `PARTIAL_DETAIL_PREFIX` gibt es nur einmal: `files/serializers.py` nutzt die Konstante aus `ingest/pipeline.py` (oder beide eine gemeinsame Stelle in `ingest/`), ohne Import-Zyklus.
- Tests: Einbettungsauftrag nach Teilumwandlung zeigt `partly_converted` und `page_count` wie vorher; Einbettungsauftrag nach vollständiger Umwandlung; Fehler beim Einbetten (KI an, Attrappe) – Status und `error_code` des Feldes `ingest` bleiben verständlich (`failed`/`embedding_unavailable`, Abschnitte sind da).

## Nicht-Ziele

- Keine Änderung am Datenmodell (kein neues Feld, keine Migration).
- Keine Oberflächenänderung (053/055).

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/ingest/management/commands/embed_sections.py`
- `backend/twox/files/serializers.py` (nur die Konstante)
- `backend/tests/ingest/test_embed_sections_command.py`, `backend/tests/files/test_api.py`

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Alle Prüfungen des backend-Jobs aus `.github/workflows/ci.yml` sind grün (ruff check, ruff format --check, mypy, pytest, pytest -m worker, makemessages-Vergleich, makemigrations --check, Lizenzprüfung, Schema-Vergleich).
2. Die drei Tests aus „Umfang“ bestehen; mit KI an und aus.
3. `down -v` des eigenen Compose-Projekts endet mit Exit 0.

## Vorgaben und Hinweise

- Herkunft: Prüfung von 051 durch die Leitstelle (Wechselwirkung mit 048).
- E-59: Mit KI aus gibt es keine Einbettungsaufträge; der Test für „aus“ prüft, dass sich nichts ändert.
- Tests nie gegen echtes Ollama (Attrappen in `backend/tests/answers/fake_ollama.py`, `backend/tests/search/fake_embedder.py`).

## Fragen an a7 (mit Optionen und Empfehlung)

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
