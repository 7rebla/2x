# Auftrag 068 – Eigenes Feld für Teilumwandlungen

Meilenstein: M2 · Freigabestufe: C (entschieden mit E-62) · Status: erledigt

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

**Status: zur Prüfung.** Läufe am 22.11.2026 im Container, Projekte `twox-068` und `twox-068-web`, Port 18068, Docker Compose v5.7.0. Alle Akzeptanzkriterien 0 bis 4 erfüllt. Keine neue Abhängigkeit. Eine Migration (`ingest.0003_ingestjob_conversion_error_count`). Die Dateien von 069 und 075 sowie die Umgebungen „2x“ und „twox-leit“ sind nicht berührt.

### Was wurde gebaut?

- **Modell** (`ingest/models.py`): `IngestJob.conversion_error_count` (`PositiveIntegerField`, Vorgabe 0, deutsch „Umwandlungsfehler“). `PARTIAL_DETAIL_PREFIX` ist entfernt (diente nur noch der Erkennung).
- **Migration** `0003_ingestjob_conversion_error_count`: Feld anlegen, dann aus `error_detail` füllen: Text beginnt mit `converted with ` → Zahl aus `converted with N errors`, mindestens 1 (siehe Abweichung 1); keine lesbare Zahl → 1; alle anderen Aufträge 0. Ein `UPDATE` je Zahl, `updated_at` bleibt. Präfix und Muster stehen fest in der Migration. Rückwärts: Spalte entfällt, `error_detail` bleibt unverändert (`RunPython.noop`).
- **Ablauf** (`ingest/pipeline.py`): `_finish` setzt das Feld bei `partial_success` (Zahl der Fehler, mindestens 1), sonst 0 – auch bei einer wiederverwendeten Antwort, die dort neu gelesen wird. `_fail` lässt das Feld stehen, also bleibt die Zahl bei gescheitertem Einbetten erhalten. Wiederverwendung nur bei `conversion_error_count=0` (statt Textprüfung). Neue Hilfen `conversion_error_count(errors)` und `partial_detail(count, pages)`; der Hinweis „converted with N errors on pages …“ bleibt in `error_detail` für Menschen.
- **`embed_sections`**: `conversion_state()` übernimmt `page_count` und `conversion_error_count` der neuesten fertigen Umwandlung (wie 061: `done` oder `failed`/`embed` mit gespeicherter Antwort). Hinweistext: von einer `done`-Umwandlung ihr eigener, von einer gescheiterten (dort steht der Einbettungsfehler) ein aus der Zahl gebauter („converted with N errors“, ohne Seiten); bei 0 keiner.
- **API** (`files/serializers.py`, gilt auch für die Liste in `ingest/api.py`): `partly_converted` = `conversion_error_count > 0` (unabhängig vom Status), neues Feld `conversion_error_count` (Ganzzahl ≥ 0, Pflicht) im Feld `ingest` und in `GET /api/v1/ingest-jobs/`. Hilfetexte angepasst; Modul-Doku von `api.py` um einen Satz ergänzt.
- **Schema und Client**: `web/openapi/schema.yml` und `web/src/api/generated/types.gen.ts` neu erzeugt. Die Oberfläche ist unverändert; nur Testdaten (`testData.ts`, `IngestPage.test.tsx`) und `IngestStatus.test.tsx` (Testdaten plus zwei Tests: Hinweis am `done`-Einbettungsauftrag nach gescheitertem Einbetten; ein gescheiterter Auftrag mit Teilumwandlung zeigt weiter den Einbettungsfehler).
- **Doku**: `docs/ARCHITECTURE.md` – Datenmodell (Absatz „Ingest jobs“) und der Grenzen-Punkt zur Teilumwandlung.
- **Übersetzung**: `backend/locale/de/LC_MESSAGES/django.po` – ein Eintrag „conversion errors“ → „Umwandlungsfehler“ (sonst schlägt die CI-Prüfung des Katalogs fehl).

### Wie wurde getestet?

Neue Testdateien:

- `tests/ingest/test_conversion_errors.py` (19 Fälle, KI an und aus): `partial_success` → Feld 3 und Hinweis mit Seiten; vollständige Umwandlung → 0; `partial_success` ohne Fehlerliste → 1; neue Umwandlung derselben Version setzt neu; Teilumwandlung + Einbetten scheitert (echter Ablauf mit Attrappe) → `failed`/`embed`, Feld 3, `partly_converted` wahr in Feld `ingest` und Liste, für read und manage; API zeigt Zahl aus dem Ablauf (read/manage × KI an/aus); Wiederverwendung übernimmt 0 einer vollständigen Umwandlung; Teilergebnis wird über das Feld nicht wiederverwendet; Regel folgt dem Feld, nicht dem Text (Zahl ohne Text → nicht wiederverwendet, Text ohne Zahl → wiederverwendet); Hilfsfunktionen.
- `tests/ingest/test_migration_conversion_error_count.py` (9 Fälle): mit `MigrationExecutor` zurück auf 0002, sieben Aufträge mit und ohne Präfix (u. a. `converted with 0 errors`, wartender Einbettungsauftrag mit Hinweis, Fehlertext mit „converted with“ in der Mitte) über die alten Modelle angelegt, vorwärts → erwartete Zahlen, `error_detail` und `updated_at` unverändert; rückwärts → Spalte weg, Texte unverändert; Daten ganz ohne Präfix → überall 0; Zerlegung des Textes einzeln.

Angepasst: `test_pipeline.py` (Feld statt Präfix), `test_embed_sections_command.py` (Zahl wird übernommen, neuer Test für den Fall aus 061: Teilumwandlung, deren Einbetten scheiterte → neuer Einbettungsauftrag mit Zahl und Hinweis, `done`, `partly_converted` wahr; gescheitertes Einbetten zeigt jetzt `partly_converted` wahr), `tests/ingest/test_api.py` und `tests/files/test_api.py` (Feld in read und manage, gescheitertes Einbetten, Text allein markiert nicht mehr, KI an/aus, Schema).

`D` = `docker compose -p twox-068`, `W` = `docker compose -p twox-068-web -f deploy/compose/compose.web.yaml`, `.env` aus `.env.example` (ohne BOM) mit `TWOX_API_PORT=18068`, also KI an. Alle Läufe auf dem committeten Stand.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version` Exit 0, `Docker Compose version v5.7.0` Exit 0 |
| 1 | erfüllt | backend: Bau, `up -d --wait` je Exit 0; `All checks passed!`; `196 files already formatted`; `Success: no issues found in 195 source files`; `pytest` `2380 passed, 6 deselected`, kein `SKIPPED`; `pytest -m worker` `6 passed`; `makemessages` + `git diff -I POT-Creation-Date -- backend/locale` Exit 0; `makemigrations --check` `No changes detected`; `License check passed.`; `spectacular` + `git diff -- web/openapi` Exit 0, `git status` leer. web: Bau, `npm ci`, `lint`, `typecheck`, `test` (38 Dateien, 732 Tests), `build`, `licenses` je Exit 0, `api:generate` + `git diff -- web/openapi web/src/api` Exit 0. e2e: Bau, `pull e2e`, `npm ci`, `up` je Exit 0; „Create test account“ → `Created account 'e2e-manager' with role 'manage'.`; `D --profile e2e run --rm e2e` `55 passed (1.5m)` |
| 2 | erfüllt | siehe Testdateien oben, alle im Gesamtlauf grün |
| 3 | erfüllt | siehe unten |
| 4 | erfüllt | siehe Schlussantwort an die Leitstelle (Abräumen nach dem Commit dieses Berichts) |

Kriterium 3 (`D --profile dev run --rm -T backend-dev python manage.py …` gegen die Datenbank von `twox-068`):

```
showmigrations ingest   → [X] 0001_extensions, [X] 0002_ingest_job_section, [X] 0003_ingestjob_conversion_error_count
migrate ingest 0002     → Unapplying ingest.0003_ingestjob_conversion_error_count... OK   (Exit 0)
showmigrations ingest   → [ ] 0003_ingestjob_conversion_error_count
migrate ingest          → Applying ingest.0003_ingestjob_conversion_error_count... OK     (Exit 0)
showmigrations ingest   → [X] 0003_ingestjob_conversion_error_count
```

Mit Daten (Präfix/ohne) sind vorwärts und rückwärts im Test `test_migration_conversion_error_count.py` belegt.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-aaada8cb907b8aea6`
- Arbeitsverzeichnis: `.claude/worktrees/agent-aaada8cb907b8aea6` (relativ zum Projektordner)
- Commits: `Keep the number of conversion errors in a field of its own`, `Regenerate the schema and the web client for conversion_error_count`, `Document the field for partial conversions in the architecture`, dazu dieser Kurzbericht. Nicht gepusht, nichts zusammengeführt.

### Abweichungen und Hinweise

1. **Mindestens 1 bei Teilumwandlung.** Docling kann `partial_success` ohne Fehlerliste melden (bisher Hinweis „converted with 0 errors“, Test aus 048). Mit 0 im Feld wäre so eine Umwandlung vollständig erschienen und wiederverwendet worden. Deshalb: Ablauf und Migration setzen bei Teilumwandlung mindestens 1. Der Auftrag sagt für die Migration „Zahl aus dem Text, sonst 0“; ich lese „sonst 0“ als „Aufträge ohne Präfix“. Folge: Der neue Hinweistext lautet in diesem Fall „converted with 1 errors“.
2. **`partly_converted` hängt nicht mehr am Status `done`**, sondern nur am Feld: wahr auch für gescheiterte (`failed`/`embed`) und wartende Einbettungsaufträge. Die Oberfläche wertet das Feld weiter nur bei `done` aus (unverändert); ein gescheiterter Auftrag zeigt den Einbettungsfehler, der Hinweis erscheint wieder, sobald ein späterer Auftrag `done` ist (z. B. nach `embed_sections`). So steht es jetzt als Grenze in `docs/ARCHITECTURE.md`.
3. **Zusätzlich geändert** (nicht unter „Betroffene Bereiche“): `backend/locale/de/LC_MESSAGES/django.po` (neuer übersetzter Feldname, CI-Prüfung), `web/src/components/files/IngestStatus.test.tsx` (Testdaten und zwei Tests), `backend/twox/ingest/api.py` nur Modul-Doku. `web/e2e/*.spec.ts` enthalten nachgebaute API-Antworten ohne das neue Feld; sie sind nicht typgeprüft, die Oberfläche liest das Feld nicht – unverändert gelassen.
4. `docs/ARCHITECTURE.md` Abschnitt Datei-API (Feld `ingest`) und `web/src/pages/README.md` sind unverändert und weiter zutreffend (Hinweis der Leitstelle: nur Datenmodell und Grenzen-Punkt).
5. `pipeline._partial_detail` heißt jetzt `partial_detail(count, pages)` (öffentlich, vom Befehl genutzt); `pipeline.PARTIAL_DETAIL_PREFIX` gibt es nicht mehr.

Keine offene Frage an a7.
