# Auftrag 064 – Filter „nur neuester Auftrag je Version“

Meilenstein: M2 · Freigabestufe: B · Status: erledigt

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

**Status: zur Prüfung.** Läufe am 22.11.2026 im Container, Projekte `twox-064` und `twox-064-web`, Port 18064, Docker Engine 29.9.3, Compose v5.7.0. Kriterien 0 bis 4 erfüllt. Keine neue Abhängigkeit, keine Migration, nur Dateien aus „Betroffene Bereiche“ geändert. Dateien von 058 und 062 nicht berührt.

### Was wurde gebaut?

- **API (`backend/twox/ingest/api.py`):**
  - Neue Bedingung `is_newest_job()` = `Q(pk__in=newest_ingest_jobs().values("pk"))`. `newest_ingest_jobs()` ist dieselbe Funktion aus `files/serializers.py`, die das Feld `ingest` lädt (051/061: `DISTINCT ON (document_version_id)`, sortiert nach `-created_at, -pk`, alle Aufträge einschließlich Einbettungsaufträgen). Die Regel steht also nur an einer Stelle. Geprüft: Das erzeugte SQL behält das `ORDER BY` in der Unterabfrage.
  - `ingest_jobs()` annotiert `is_latest` mit dieser Bedingung. Das Feld steht in jeder Zeile der Liste und in der 202-Antwort von `POST …/ingest/` (Pflichtfeld, nur lesend). `IngestJobSummary` (Feld `ingest`, 409-Antwort) bleibt unverändert.
  - Filter `latest` (Wahrheitswert, Vorgabe `false`, Werte wie DRF-`BooleanField`, z. B. `true`/`false`/`1`/`0`; ungültig → 400 am Parameter). Er wirkt vor `status`, `device`, `document` und `version`, weil der neueste Auftrag unter allen Aufträgen der Version gewählt wird.
  - **Keine zusätzliche Abfrage:** Die neuesten Aufträge sind eine Unterabfrage derselben Abfrage. Liste mit und ohne `latest` braucht gleich viele Abfragen.
  - `requested_by` weiter nur für `manage` (E-57). Nichts hängt an KI (E-59).
- **Schema und Client** neu erzeugt (`web/openapi/schema.yml`, `web/src/api/generated/types.gen.ts`: `IngestJob.is_latest`, Abfrageparameter `latest`).
- **Oberfläche (`web/src/pages/IngestPage.tsx`):**
  - Neuer Schalter (Kontrollkästchen) „Also show older attempts“ / „Auch ältere Versuche zeigen“ neben Status und Gerät. Er steht in der Adresse als `?older=1` (Vorgabe aus, dann nicht in der Adresse). Zurück funktioniert, ein Wechsel beginnt auf Seite 1 wie die anderen Filter.
  - Ohne Schalter fragt die Seite mit `latest=true`, mit Schalter ohne `latest`.
  - Der Hinweis „Älterer Versuch“ und das Fehlen der Schaltfläche richten sich nach `is_latest`. Die Suche auf derselben Seite (`newestJobs`) ist entfernt.
  - Texte (`ingest.json` de/en): `filter.older` neu. `superseded` lautet jetzt „Älterer Versuch: Zu dieser Version gibt es einen neueren Auftrag.“ (en „Older attempt: this version has a newer job.“), weil der neuere Auftrag nicht mehr „weiter oben“ stehen muss. `intro` nennt „je Dateiversion nur der neueste Auftrag“.
- **Doku:** `web/src/pages/README.md`, Abschnitt „Ingest overview“ (Schalter, `latest`, `is_latest`, Tests).

### Wie wurde getestet?

`D` = `docker compose -p twox-064`, `W` = `docker compose -p twox-064-web -f deploy/compose/compose.web.yaml`. `.env` aus `.env.example` (ohne BOM, mit dem Write-Werkzeug) mit `TWOX_API_PORT=18064`, KI an, aber `TWOX_LLM_BASE_URL=http://127.0.0.1:9/v1` (dort antwortet nichts, wie bei 054/055; kein Test erreicht ein echtes Ollama, Docling wird nicht gestartet). Vor den Builds `web/dist` und `web/playwright-report` gelöscht. „2x“ und „twox-leit“ nicht berührt.

| Nr. | Ergebnis | Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version` (Engine 29.9.3) Exit 0, `docker compose version` v5.7.0 Exit 0 |
| 1 | erfüllt | Auf dem Endstand: `build migrate api worker backend-dev` und `up -d --wait …` Exit 0; `ruff check` „All checks passed!“; `ruff format --check` „192 files already formatted“; `mypy .` „Success: no issues found in 191 source files“; `pytest` „2311 passed, 6 deselected“; `pytest -m worker` „6 passed“; `makemessages` + `git diff -I POT-Creation-Date -- backend/locale` Exit 0, `git status` leer; `makemigrations --check --dry-run` „No changes detected“, Exit 0; Lizenzprüfung „License check passed.“, Exit 0; `spectacular` + `git diff --exit-code -- web/openapi` Exit 0 |
| 2 | erfüllt | `build web-dev`, `npm ci`, `lint`, `typecheck`, `test` (37 Dateien, 717 Tests), `build`, `licenses` („License check passed.“) je Exit 0; `api:generate` Exit 0, `git diff --exit-code -- web/openapi web/src/api` Exit 0, `git status` dazu leer. `IngestPage-….js` 8,56 kB (gzip 2,79 kB) |
| 3 | erfüllt | `build migrate api worker web-dev`, `pull e2e`, `npm ci`, `up -d --wait …` je Exit 0; „Create test account“ wörtlich mit `D`: „Created account 'e2e-manager' with role 'manage'.“; `D --profile e2e run --rm e2e` **54 passed**, Exit 0. Nach der letzten Backend-Änderung erneut (Images neu gebaut): „Updated account …“, **54 passed**, Exit 0 |
| 4 | erfüllt | `D --profile dev --profile e2e down -v` Exit 0, `W --profile dev down -v` Exit 0; danach kein Container, Volume oder Netz mit `twox-064` |

**API-Tests (`backend/tests/ingest/test_api.py`, neu 16 Fälle, Datei jetzt 66):** Fixture mit mehreren Versuchen je Version auf zwei Geräten: fehlgeschlagen → eingelesen; eingelesen → gescheiterter Einbettungsauftrag (Schritt `embed`, zählt als neuester); nur ein Versuch; zwei Aufträge mit gleichem `created_at` (die höhere ID entscheidet). Geprüft: `is_latest` je Zeile für `read` und `manage`; dieselben Aufträge wie im Feld `ingest` der Datei-API; `latest=true` und `latest=false`, Reihenfolge; `latest` mit Status „Offen“, mit Gerät, Gerät plus Status, Version (`latest=1`), Dokument plus Status; neuer Versuch per POST wird neuester (`is_latest` in der 202-Antwort), der alte nicht mehr; Rechte je Rolle mit `?latest=true` (anonym und ohne Rolle 403); `requested_by` mit `latest` nur für `manage`; Abfragezahl: 1 gegen 21 Aufträge gleich, mit und ohne `latest` gleich. Ungültige Werte `?latest=maybe` und `?latest=` → 400. Schematest um `latest` (boolean, Vorgabe false) und `is_latest` (Pflichtfeld) erweitert.

**Vitest (`IngestPage.test.tsx`, jetzt 32 Fälle):** Die Attrappe berechnet `is_latest` wie die API und wertet `latest` vor den übrigen Filtern aus. Neu bzw. angepasst: Adresse lesen und schreiben mit `older`; Vorgabe sendet `latest=true`, Schalter aus; „Alle“ sendet weiter `latest=true`; Vorgabe blendet den durch einen späteren Versuch eingelesenen Fehlschlag aus; Schalter schreibt `?older=1`, Anfrage ohne `latest`, ältere Zeile markiert und ohne Schaltfläche, Zurück stellt wieder her; Hinweis über `is_latest`, auch wenn der neuere Auftrag nicht in der Liste steht (`?status=failed&older=1`); Hinweis folgt der API, nicht der Seite (Antwort mit `is_latest: false` bei zwei Versionen); deutsche Texte; Erneut einlesen in der Vorgabe (neue Zeile ersetzt die alte) und mit Schalter (alte Zeile markiert).

**Playwright (`web/e2e/ingest.spec.ts`):** Erster Fall prüft zusätzlich `latest=true` in der Anfrage. Der bestehende Fall „Erneut einlesen“ zeigt jetzt in der Vorgabe nur den neuen Auftrag (ID aus der 202-Antwort) und mit dem Schalter beide, den älteren markiert. Neuer Fall mit Antworten per `page.route`: gescheiterter älterer und eingelesener neuerer Versuch derselben Version; Vorgabe „Nichts offen“ mit `latest=true`; Schalter → `?older=1`, Anfrage ohne `latest`, eine markierte Zeile ohne Schaltfläche; Zurück schaltet ab.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-ab790915f3806e909`
- Arbeitsverzeichnis: `.claude/worktrees/agent-ab790915f3806e909` (relativ zum Projektordner)
- Commits: `Add is_latest and the filter latest to the ingest job list`, `List only the newest ingest job of each version on /ingest by default`, `Test the switch for older ingest attempts in the browser`, `Filter the newest ingest jobs by a named condition so that mypy passes`, dazu dieser Kurzbericht. Nicht gepusht, nichts zusammengeführt.

### Abweichungen und Hinweise

1. **Keine zusätzliche Abfrage** statt der erlaubten einen: Unterabfrage statt eigener Abfrage. Der Test verlangt gleiche Abfragezahl mit und ohne `latest`.
2. **Adressparameter `older=1`** (nicht `latest=false`): Die Vorgabe bleibt eine leere Adresse wie bei Status und Gerät. Andere Werte als `1` gelten als aus.
3. **Kontrollkästchen folgt der Adresse:** Der Router aktualisiert die Adresse kurz nach dem Klick. Playwright-`check()` prüft sofort und meldete deshalb „did not change its state“. Die Tests klicken und warten dann auf `toBeChecked()`. Für Nutzer ist das nicht sichtbar.
4. **Texte geändert:** `superseded` und `intro` in beiden Sprachen (siehe oben), weil „steht weiter oben“ nicht mehr stimmt.
5. **`is_latest` auch in der 202-Antwort von `POST …/ingest/`**, weil sie denselben Serializer nutzt (immer `true`).
6. **`.env` mit `TWOX_LLM_BASE_URL=http://127.0.0.1:9/v1`** (Abweichung von `.env.example`, nur lokal), damit kein Test das Ollama am Host erreicht.
7. Hinweis für 058 (Abnahmetests): Die Vorgabe-Ansicht von `/ingest` sendet jetzt `latest=true`. Ein Abnahmetest, der nach erneutem Einlesen zwei Zeilen erwartet, braucht `?older=1`.
