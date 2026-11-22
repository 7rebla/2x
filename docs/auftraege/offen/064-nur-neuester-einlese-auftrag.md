# Auftrag 064 – Filter „nur neuester Auftrag je Version“

Meilenstein: M2 · Freigabestufe: B · Status: offen

Voraussetzung: 055 ist nach `main` zusammengeführt.

## Ziel

Jeder Einlese-Versuch ist eine eigene Zeile (E-55). Die Übersicht `/ingest` (055) zeigt in der Vorgabe-Ansicht „Offen“ deshalb auch gescheiterte Versuche, deren Version längst mit einem späteren Versuch eingelesen ist. Nach diesem Auftrag zeigt die Übersicht standardmäßig nur den neuesten Auftrag je Version; ältere Versuche bleiben über einen Schalter sichtbar.

## Umfang

- `GET /api/v1/ingest-jobs/` erhält den Filter `latest` (Wahrheitswert, Vorgabe `false` für Abwärtsverträglichkeit): bei `true` nur der neueste Auftrag je Version (gleiche Regel wie das Feld `ingest` aus 051 und 061, also auch Einbettungsaufträge). Die Filter `status`, `device`, `document`, `version` wirken danach auf diese Menge. Eine Abfrage mehr ist zulässig; ein Test zählt die Abfragen.
- Jede Zeile der Liste erhält `is_latest` (Wahrheitswert), auch ohne Filter.
- Oberfläche `/ingest`: Vorgabe `latest=true`; ein Schalter „Auch ältere Versuche zeigen“ (de/en) steht in der Adresse wie die übrigen Filter. Der bisherige Hinweis „Älterer Versuch …“ nutzt `is_latest` statt der Suche auf derselben Seite.
- Schema und Client neu erzeugt; `web/src/pages/README.md` nachgezogen.
- Tests: API (Filter an und aus, mit Status- und Gerätefilter, Rechte wie bisher, Abfragezahl), Vitest (Vorgabe, Schalter, Hinweis über `is_latest`), Playwright-Fall in `web/e2e/ingest.spec.ts` (Antworten per `page.route`).

## Nicht-Ziele

- Keine Änderung am Datenmodell, keine Migration.
- Keine Änderung an der Datei- oder Geräteseite.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/ingest/api.py`, `backend/tests/ingest/test_api.py`
- `web/openapi/schema.yml`, `web/src/api/generated/**`
- `web/src/pages/IngestPage.tsx`, `web/src/pages/IngestPage.test.tsx`, `web/src/locales/de/ingest.json`, `web/src/locales/en/ingest.json`, `web/src/pages/README.md`, `web/e2e/ingest.spec.ts`

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Alle Prüfungen des backend-Jobs aus `.github/workflows/ci.yml` sind grün.
2. Web-Job grün (lint, typecheck, test, build, licenses), `api:generate` ohne Unterschied.
3. e2e wie in `ci.yml` grün.
4. `down -v` der eigenen Compose-Projekte endet mit Exit 0.

## Vorgaben und Hinweise

- Herkunft: Rückfrage aus dem Kurzbericht von 055, Option (a), Entscheidung der Leitstelle (Stufe B, nur Erweiterung der API).
- E-57: `requested_by` weiter nur für manage. E-59: KI-Zustände neutral.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
