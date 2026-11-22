# Auftrag 051 – Einlese-API: Status, Verlauf, erneut anstoßen

Meilenstein: M2 · Freigabestufe: C · Status: zur Prüfung

## Ziel

Die API zeigt je Dokumentversion den Einlese-Status mit Fehlerart, listet alle Einlese-Aufträge mit Filtern und erlaubt Verwaltern, das Einlesen erneut anzustoßen. Benutzernamen sieht nur, wer auch das Änderungsprotokoll lesen darf (Frage 1). Grundlage für die Oberfläche (053, 055).

## Umfang

- Die Version im Datei-Endpunkt (`GET /api/v1/documents/{document_id}/`) bekommt ein Feld `ingest` mit dem neuesten Auftrag oder `null`: `id`, `status`, `step`, `error_code`, `error_detail` (nach Frage 2), `section_count`, `page_count`, `created_at`, `finished_at`. Gleiches Feld in der Dateiliste eines Geräts für die neueste Version. Nur ein zusätzlicher Abfragesatz, kein N+1; ein Test zählt die Abfragen.
- `POST /api/v1/document-versions/{version_id}/ingest/`: `CanManage`; 202 mit dem neuen Auftrag; 409, wenn schon ein Auftrag läuft; 400 für Dokumente der Art `configuration`. Nutzt `request_ingest` aus 049; `requested_by` ist der angemeldete Benutzer.
- `GET /api/v1/ingest-jobs/`: `CanRead`, 50 je Seite, neueste zuerst; Filter `status` (mehrfach), `device`, `document`, `version`. Jeder Eintrag trägt Dokument (Kennung, Titel), Version (Kennung, Nummer, Dateiname), Gerät (Kennung, Schlüssel, Name) und `requested_by` (Benutzername für `manage`, für `read` immer `null` – nach Frage 1).
- Neue Datei `backend/twox/ingest/urls.py`, eingebunden in `backend/twox/config/urls.py`. Views und Serializer in `backend/twox/ingest/api.py`.
- `backend/tests/config/expected_paths/ingest.py` und `__init__.py`; der Pfadtest aus 025 bleibt grün (anonym und ohne Rolle 403).
- OpenAPI-Schema (`web/openapi/schema.yml`) und Client (`web/src/api/generated/`) neu erzeugen und einchecken.
- Neue Meldungen (z. B. für 409) in `backend/locale/de/LC_MESSAGES/django.po` übersetzen.
- **Tests:** Rechte je Rolle; 202, 409 und 400; Filter und Seiten; `requested_by` je Rolle; `error_detail` je Rolle; Felder im Schema.

## Nicht-Ziele

- Keine Oberfläche (053, 055).
- Kein Abbrechen, kein Löschen von Aufträgen oder Abschnitten.
- Kein Herunterladen der Docling-Antwort.

## Betroffene Bereiche (Ordner, Dateien)

- neu: `backend/twox/ingest/api.py`, `backend/twox/ingest/urls.py`
- `backend/twox/config/urls.py`
- `backend/twox/files/serializers.py` (Feld `ingest`), gegebenenfalls `backend/twox/files/views.py` (Abfrage vorladen)
- neu: `backend/tests/config/expected_paths/ingest.py`; `backend/tests/config/expected_paths/__init__.py`
- neu: `backend/tests/ingest/test_api.py`; `backend/tests/files/test_api.py`
- `backend/locale/de/LC_MESSAGES/django.po`
- `web/openapi/schema.yml`, `web/src/api/generated/**`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-051`, `W` für `docker compose -p twox-051-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18051` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev web-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Tests:
   - `D run --rm backend-dev pytest tests/ingest tests/files tests/config -v` endet mit Exit-Code 0.
   - `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen.
   - `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
3. `D run --rm backend-dev ruff check .` meldet `All checks passed!`, `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0, `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
4. Weitere Prüfungen wie in `ci.yml`, jeweils ohne Unterschied zum eingecheckten Stand:
   - `D run --rm backend-dev python manage.py makemessages -l de --add-location=file`, danach `git diff --exit-code -I '^"POT-Creation-Date:' -- backend/locale`;
   - `D run --rm backend-dev python manage.py makemigrations --check --dry-run` endet mit Exit-Code 0;
   - `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0;
   - `D run --rm -v "$PWD/web/openapi:/out" backend-dev python manage.py spectacular --file /out/schema.yml` (unter Git Bash mit vorangestelltem `MSYS_NO_PATHCONV=1`), danach `git diff --exit-code -- web/openapi` ohne Unterschied zum eingecheckten neuen Stand.
5. Oberfläche wie im CI-Job `web`: `W --profile dev build web-dev` und `W run --rm web-dev npm ci`, danach `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build` und `npm run licenses`, je über `W run --rm web-dev …`, mit Exit-Code 0. `W run --rm web-dev npm run api:generate`, danach `git diff --exit-code -- web/openapi web/src/api` ohne Unterschied.
6. Browser-Test wie im CI-Job `e2e`: `D --profile e2e pull e2e`, `D --profile dev run --rm web-dev npm ci`; dann der Schritt „Create test account“ aus `ci.yml` wörtlich, nur mit `D` statt `docker compose` (Kennwort nur über den Variablennamen `TWOX_ACCOUNT_PASSWORD`); dann `D --profile e2e run --rm e2e`: alle Fälle bestanden, Exit-Code 0.
7. Abräumen: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

- **Nachtrag der Leitstelle (E-59, KI optional):** Einbettungen, Vektorsuche und alles, was ein Modell braucht, sind eine aktivierbare Zusatzfunktion. Schalter `TWOX_AI_ENABLED` (Einstellung in `settings.py`, Standard `False`; `.env.example` mit Kommentar). Bei „aus“: kein Aufruf von Ollama, keine Einbettungs-Aufgaben, Einlesen endet nach den Abschnitten erfolgreich, die Suche arbeitet nur mit der Stichwortsuche, Selbsttest und Oberfläche zeigen „KI nicht aktiviert“ als neutralen Zustand (kein Fehler, kein Warnsymbol). Jede KI-abhängige Stelle braucht einen Test für beide Zustände; die CI läuft mit „aus“ und mit „an“ plus Attrappe.

Voraussetzung: 049 ist nach `main` zusammengeführt. Fragen 1 und 2 sind entschieden.

- Welle 6. Einziger Auftrag seiner Zeit, der `urls.py`, Schema, Client, `django.po` und `expected_paths/__init__.py` ändert; 052 wartet auf ihn.
- **Keine neue Abhängigkeit.**
- Rechte wie bisher (E-40): Lesen dürfen beide Rollen, erneut anstoßen nur `manage`. Benutzernamen nur für `manage` wie beim Änderungsprotokoll (E-43, `/audit`).
- Stufe C, weil neue Endpunkte Rechte festlegen.
- Konflikte in `web/src/api/generated` und `schema.yml` beim Zusammenführen immer durch Neuerzeugen lösen, nie von Hand.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

1. **Wer sieht, wer ein Einlesen angestoßen hat (`requested_by`)?** (E-43: das Änderungsprotokoll lesen nur Verwalter.)
   - (a) nur `manage`; `read` bekommt `null`;
   - (b) alle Rollen, als ausdrückliche Abweichung von E-43.
   Empfehlung: (a). Gleiche Linie wie `/audit`; für die Arbeit mit Lesezugriff ist der Name nicht nötig.
2. **Darf die Rolle „Lesen“ den technischen Fehlertext (`error_detail`) sehen?**
   - (a) ja, alle Rollen sehen Fehlerart und Text;
   - (b) „Lesen“ sieht nur die übersetzte Fehlerart.
   Empfehlung: (a). Der Text ist nach 046 bereinigt (keine Pfade, Adressen, Dateinamen, Inhalte) und hilft bei der Meldung an den Verwalter.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Läufe am 22.11.2026 im Container, Projekt `twox-051` (Web: `twox-051-web`), Port 18051, Docker Engine 29.9.3, Compose v5.7.0. Akzeptanzkriterien 0 bis 7 erfüllt. Keine neue Abhängigkeit, keine Migration. Die 048-Dateien (`pipeline.py`, `tasks.py`, Selbsttest) sind unberührt. Sieben kleine Abweichungen (siehe unten), keine offene Frage an a7.

### Was wurde gebaut?

- **Feld `ingest` an jeder Version** (`backend/twox/files/serializers.py`): neuester Auftrag oder `null`, Felder `id`, `status`, `step`, `error_code`, `error_detail`, `partly_converted`, `section_count`, `page_count`, `created_at`, `finished_at` (Komponente `IngestJobSummary`). Weil `DocumentVersionSerializer` gemeinsam genutzt wird, steht das Feld in allen Versionen der Datei-API: Detail (`versions` und `latest_version`), Dateiliste eines Geräts (`latest_version`), Upload-Antwort und 409-Antwort beim Upload.
  - Laden: `documents_with_versions()` (`files/views.py`) lädt den neuesten Auftrag aller Versionen mit **einer** zusätzlichen Abfrage (`Prefetch` mit `DISTINCT ON (document_version_id)`, sortiert nach `-created_at, -pk`). Ohne Vorladen (Upload-Antwort) eine Abfrage je Version.
  - `step` und `error_code` sind im Schema `Enum | BlankEnum` (leer = noch kein Schritt bzw. kein Fehler).
  - **Teilumwandlung (für 053):** `partial_success` endet `done` mit Hinweis in `error_detail` (Präfix `converted with `, 046). `partly_converted` ist `true` genau für `done` mit diesem Präfix; `error_detail` wird bei jedem Status ausgeliefert. Ein Test prüft das Präfix gegen die echte Hilfsfunktion `pipeline._partial_detail`, damit beide nicht auseinanderlaufen.
- **`backend/twox/ingest/api.py`** (Views und Serializer der Liste) und **`backend/twox/ingest/urls.py`**, eingebunden in `backend/twox/config/urls.py`:
  - `GET /api/v1/ingest-jobs/` (`CanRead`): 50 je Seite (fest), neueste zuerst (`-created_at, -pk`). Filter `status` (mehrfach, `?status=failed&status=skipped`), `device`, `document`, `version`; ungültige Werte → 400 am Parameter, unbekannte Kennung → leere Liste. Je Eintrag zusätzlich `document` (`id`, `title`), `version` (`id`, `number`, `original_filename`), `device` (`id`, `key`, `name`) und `requested_by`. Feste Zahl an Abfragen (`select_related`).
  - `requested_by`: Benutzername nur für die Rolle `manage` (Superuser zählt als `manage`), für `read` immer `null`; Systemaufträge `null` (Frage 1 (a), E-57).
  - `POST /api/v1/document-versions/{version_id}/ingest/` (`CanManage`, ohne Anfragekörper, CSRF wie alle Schreibzugriffe): ruft `request_ingest(version, angemeldeter Benutzer)` aus 049 auf. 202 mit dem neuen Auftrag (wie in der Liste, `requested_by` gefüllt); auch nicht unterstützte Formate (`skipped`) und fehlender Inhalt (`failed`) antworten 202, weil ein neuer Auftrag entsteht. 409 `{"detail", "code": "ingest_active", "job"}` bei `queued`/`running`; 400 `{"detail", "code": "configuration_not_ingested"}` für Konfigurationen; 404 für unbekannte Versionen. Die Nachricht an den Worker geht wie in 049 erst nach dem Commit.
  - E-59: Kein Feld hängt an Einbettungen, nichts ruft das Modell; Test für KI an und aus.
- `backend/twox/config/settings.py`: Eintrag `IngestStatusEnum` in `ENUM_NAME_OVERRIDES` (siehe Abweichung 2).
- `backend/locale/de/LC_MESSAGES/django.po`: zwei neue Meldungen („Konfigurationsdateien werden nicht eingelesen.“, „Diese Dokumentversion wird bereits eingelesen.“).
- `backend/tests/config/expected_paths/ingest.py` und `__init__.py`: die zwei neuen Pfade; der Pfadtest aus 025 bleibt grün (anonym und ohne Rolle überall 403).
- `web/openapi/schema.yml` und `web/src/api/generated/**` neu erzeugt (Operationen `ingest_jobs_list`, `document_version_ingest`; Komponenten `IngestJob`, `IngestJobSummary`, `IngestJobDocument`, `IngestJobVersion`, `IngestJobDevice`, `IngestConflict`, `IngestRequestError`, `PaginatedIngestJobList`, `IngestStatusEnum`, `StepEnum`, `ErrorCodeEnum`, `BlankEnum`).
- `docs/ARCHITECTURE.md`: zwei Zeilen in der Endpunkt-Tabelle und ein Absatz zum Feld `ingest`.
- **Tests:** `backend/tests/ingest/test_api.py` (24 Testfunktionen, mit Parametrisierung 50 Fälle) und 6 neue Testfunktionen (7 Fälle) in `backend/tests/files/test_api.py`:
  - Rechte je Rolle (anonym, ohne Rolle, `read`, `manage`, Superuser) für Liste und Anstoßen; `read` darf nicht anstoßen (403, kein Auftrag, keine Nachricht); nur POST bzw. nur GET erlaubt (405); CSRF-Pflicht beim Anstoßen;
  - 202 mit allen Feldern, `requested_by`, genau einer Nachricht `twox.ingest.convert` nach dem Commit; 202 für `skipped` und `content_missing`; 409 für `queued` und `running` (mit dem aktiven Auftrag, englisch und deutsch); 202 nach `done`/`failed`/`skipped`; 400 für Konfiguration (englisch und deutsch); 404;
  - Liste: Reihenfolge, Felder, Seiten (51 Aufträge → 50 + 1, `page_size` wird ignoriert, Seite 3 → 404), feste Zahl an Abfragen (1 gegen 11 Aufträge); Filter einzeln, mehrfach und kombiniert; fünf ungültige Filterwerte → 400;
  - `requested_by` je Rolle; `error_code` und `error_detail` für `read` und `manage` gleich; Teilumwandlung; KI an und aus;
  - Datei-API: `ingest` `null` ohne Auftrag, neuester Auftrag je Version im Detail, Auftrag der neuesten Version in der Geräteliste, `error_detail` für `read`, `partly_converted`, Auftrag nach echtem Upload (Commit-Rückrufe ausgeführt) im Detail sichtbar; **Abfragezählung** für Liste und Detail: 1 Dokument mit 1 Auftrag gegen 6 Dokumente mit 16 Versionen und 16 Aufträgen ergibt dieselbe Zahl an Abfragen und genau eine Abfrage auf `ingest_ingestjob`;
  - Schema: Pfade, Methoden, Operationen, Antwortcodes, Filterparameter (`status` als Array mit den fünf Werten), Felder aller neuen Komponenten, `DocumentVersion.ingest` nullbar.

### Wie wurde getestet?

`D` = `docker compose -p twox-051`, `W` = `docker compose -p twox-051-web -f deploy/compose/compose.web.yaml`; `.env` aus `.env.example` (ohne BOM, mit dem Write-Werkzeug) mit `TWOX_API_PORT=18051`, also KI an. Alle Läufe auf dem committeten Stand, in einem Durchgang. Die Umgebungen „2x“ und „twox-leit“ wurden nicht berührt.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | Engine 29.9.3, Compose v5.7.0, Exit 0 |
| 1 | erfüllt | Bau Exit 0; `up -d --wait …` Exit 0 |
| 2 | erfüllt | `pytest tests/ingest tests/files tests/config -v`: `1018 passed, 6 deselected`; `pytest -rs`: `2091 passed, 6 deselected`, nichts übersprungen; `pytest -m worker`: `6 passed`. Zusätzlich mit `-e TWOX_AI_ENABLED=false`: `tests/ingest/test_api.py tests/files/test_api.py tests/config/test_api.py` `113 passed` |
| 3 | erfüllt | `All checks passed!`; `182 files already formatted`; `Success: no issues found in 181 source files` |
| 4 | erfüllt | `makemessages` + `git diff -I POT-Creation-Date -- backend/locale` Exit 0, `git status` leer; `No changes detected`; `License check passed.`; `spectacular` + `git diff -- web/openapi` Exit 0 |
| 5 | erfüllt | `build`, `npm ci`, `lint`, `typecheck`, `test` (33 Dateien, 566 Tests), `build`, `licenses` je Exit 0; `api:generate` + `git diff -- web/openapi web/src/api` Exit 0 |
| 6 | erfüllt | `pull e2e` Exit 0, `npm ci` Exit 0, „Create test account“ wörtlich mit `D`: `Created account 'e2e-manager' with role 'manage'.`; `D --profile e2e run --rm e2e`: `41 passed (33.8s)`, Exit 0 |
| 7 | erfüllt | siehe Schlussantwort an die Leitstelle (Abräumen nach dem Commit dieses Berichts) |

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a08a1dad3927cb6c3`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a08a1dad3927cb6c3` (relativ zum Projektordner)
- Commits: `Split an over-long log line so that ruff check passes again`, `Show the newest ingest job of every version in the files API`, `Add the ingest API: list jobs with filters, start ingesting a version again`, `Regenerate the OpenAPI schema and the web client for the ingest API`, `Document the ingest endpoints and the ingest field of versions`, dazu dieser Kurzbericht. Nicht gepusht, nichts zusammengeführt.

### Abweichungen und Hinweise

1. **`backend/twox/ingest/services.py` (049) geändert, eine Zeile:** Auf `main` meldete `ruff check` `E501` (Zeile 114, 101 Zeichen; die Zeile stammt aus dem Merge-Commit von 049). Der Text der Protokollmeldung ist unverändert, nur auf zwei Literale verteilt. Eigener Commit.
2. **`backend/twox/config/settings.py` geändert:** Ohne Eintrag meldet drf-spectacular eine Namenskollision zweier `status`-Felder (Selbsttest-`Health` und Einlese-Auftrag); der Schematest verlangt eine leere Fehlerausgabe. Eintrag `"IngestStatusEnum": "twox.ingest.models.IngestStatus"` in `ENUM_NAME_OVERRIDES` wie bei `AuditActionEnum`. Folge im Client: Die Aufzählung des Health-Status heißt jetzt `HealthStatusEnum` statt `StatusEnum` (in `web/src` außerhalb des erzeugten Codes nicht verwendet).
3. **`web/src/components/files/testData.ts` geändert, eine Zeile (`ingest: null`):** Das neue Pflichtfeld der Version ließ `npm run typecheck` sonst scheitern. 053 wird dort echte Werte brauchen.
4. **`docs/ARCHITECTURE.md` geändert** (nicht unter „Betroffene Bereiche“): Endpunkt-Tabelle und ein Absatz, damit die Rechte-Übersicht vollständig bleibt. Ausführliche Doku bleibt 059.
5. **Zusätzliches Feld `partly_converted`** (über den Umfang hinaus, nach dem Hinweis der Leitstelle zu `partial_success`): Die Oberfläche muss den Text nicht selbst auswerten. Nicht `partial` genannt, weil DRF-Serializer diesen Namen für Teilaktualisierungen nutzen.
6. **Der Serializer für das Feld `ingest` (`IngestJobSummarySerializer`) liegt in `files/serializers.py`**, nicht in `ingest/api.py`: `ingest/api.py` nutzt `ErrorDetailSerializer` und die Zusammenfassung aus `files/serializers.py`; umgekehrt gäbe es einen Importkreis. Der Listen-Serializer `IngestJobSerializer` in `api.py` erweitert die Zusammenfassung.
7. **Feld `ingest` an allen Versionen der Datei-API**, also auch in Upload-Antwort und 409-Antwort beim Upload (gemeinsamer `DocumentVersionSerializer`). Dort ist es meist `null` oder `queued`, weil der Auftrag erst nach dem Commit entsteht, und kostet eine Abfrage je Version.

Hinweise:

- Die Fehlermeldungen von 400 und 409 sind übersetzt (`Accept-Language`); `code` bleibt fest für die Oberfläche.
- Konflikte mit 048 beim Zusammenführen: `web/openapi/schema.yml` und `web/src/api/generated/**` durch Neuerzeugen lösen. `settings.py` und `files/serializers.py` berührt 048 nach dem Hinweis der Leitstelle nicht.
- `IngestJob.started_at`, `attempts` und `reused_from` sind nicht in der API (nicht verlangt); bei Bedarf für 055 leicht ergänzbar.
