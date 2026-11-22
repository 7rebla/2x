# Auftrag 068 – Eigenes Feld für Teilumwandlungen

Meilenstein: M2 · Freigabestufe: C (entschieden mit E-62) · Status: offen

Voraussetzung: E-62; 048, 051, 061 sind auf `main`.

## Ziel

Heute erkennt das System eine Teilumwandlung (Docling `partial_success`) am Textpräfix `converted with ` in `error_detail` (`ingest/models.py`, `PARTIAL_DETAIL_PREFIX`). Scheitert danach das Einbetten, überschreibt die Fehlermeldung den Hinweis; die Oberfläche zeigt die Umwandlung dann als vollständig, und `embed_sections` (061) kann den Hinweis nicht übernehmen. Nach diesem Auftrag steht die Zahl der Umwandlungsfehler in einem eigenen Feld.

## Umfang

- `IngestJob` erhält `conversion_error_count` (positive ganze Zahl, Vorgabe 0) mit Migration; bestehende Aufträge mit Präfix in `error_detail` werden in der Migration übernommen (Zahl aus dem Text, sonst 0).
- `pipeline.py` setzt das Feld bei `partial_success` (statt bzw. zusätzlich zum Hinweis); Wiederverwendung (`reused_from`) und `embed_sections` (`conversion_state`) übernehmen das Feld; die Regel „Teilergebnisse nicht wiederverwenden“ (048) richtet sich nach dem Feld.
- API: `partly_converted` (051) wird aus dem Feld berechnet; zusätzlich `conversion_error_count` ausgeben (Feld `ingest` und Einlese-Liste). Schema und Client neu erzeugen. Die Oberfläche (053/055) zeigt den Hinweis „Nur teilweise umgewandelt“ wie bisher, jetzt auch nach gescheitertem Einbetten; sie braucht nur die Typen.
- `PARTIAL_DETAIL_PREFIX` entfällt, wo es nur noch der Erkennung diente (Text in `error_detail` für Menschen darf bleiben).
- Tests: Migration (Daten mit Präfix, ohne), Pipeline (partial_success → Feld), Teilumwandlung + gescheitertes Einbetten → `partly_converted` bleibt wahr, Wiederverwendung, `embed_sections` übernimmt das Feld, API-Felder für read und manage, KI an und aus.

## Nicht-Ziele

- Keine weiteren Felder, keine Änderung an der Gestaltung der Oberfläche.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/ingest/models.py`, neue Migration unter `backend/twox/ingest/migrations/`
- `backend/twox/ingest/pipeline.py`, `backend/twox/ingest/management/commands/embed_sections.py`, `backend/twox/ingest/api.py`, `backend/twox/files/serializers.py`
- Tests unter `backend/tests/ingest/` und `backend/tests/files/test_api.py`
- `web/openapi/schema.yml`, `web/src/api/generated/**`, gegebenenfalls `web/src/components/files/testData.ts` und Tests unter `web/src/` (nur Typen/Testdaten)
- `docs/ARCHITECTURE.md` (Datenmodell, Grenzen)

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Alle Prüfungen aus `.github/workflows/ci.yml` (backend, web, e2e) sind grün; `makemigrations --check` ohne Unterschied nach der neuen Migration.
2. Die Tests aus „Umfang“ bestehen.
3. Migration vorwärts und rückwärts im eigenen Projekt ausgeführt (Ausgabe im Kurzbericht).
4. `down -v` der eigenen Compose-Projekte endet mit Exit 0.

## Vorgaben und Hinweise

- Herkunft: E-62 (a), Befunde aus 048 und 061.
- Tests nie gegen echtes Docling oder Ollama.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
