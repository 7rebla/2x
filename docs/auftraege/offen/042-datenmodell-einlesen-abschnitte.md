# Auftrag 042 – Datenmodell: Einlese-Auftrag und Abschnitt

Meilenstein: M2 · Freigabestufe: C · Status: zur Prüfung

## Ziel

Das Datenmodell bekommt die beiden Kernobjekte aus Startunterlage 5.7: **Einlese-Auftrag** (Arbeitsschritt mit Status und Fehlertext je Dokumentversion) und **Abschnitt** (Textstück mit Seite, Einbettung und Verweis auf die Dateiversion), dazu die Indizes für Volltext, Trigramme und Vektoren. Darauf bauen Ablauf (046), Suche (047, 050) und API (051).

## Umfang

Modelle in `backend/twox/ingest/models.py`, nach den Fragen 1 bis 4:

- **`IngestJob`** (je Versuch eine Zeile):
  - `document_version`: FK auf `files.DocumentVersion`, `PROTECT`, `related_name="ingest_jobs"`.
  - `status`: TextChoices `queued`, `running`, `done`, `failed`, `skipped`.
  - `step`: `convert`, `sections`, `embed` oder leer.
  - `error_code`: feste Liste, die die Oberfläche übersetzt, vollständig schon jetzt: `docling_unavailable`, `docling_rejected`, `conversion_failed`, `content_missing`, `unsupported_format`, `embedding_unavailable`, `embedding_rejected`, `embedding_dimension_mismatch`, `timeout`, `internal`; leer ohne Fehler.
  - `error_detail`: kurzer englischer Text, höchstens 2 000 Zeichen, bereinigt (046).
  - `attempts`: Zahl der Versuche innerhalb des Auftrags.
  - `requested_by`: FK auf den Benutzer, `PROTECT`, darf leer sein.
  - `docling_task_id`, `docling_started_at` (erster Status `started` bei Docling; Grundlage der Frist in 046).
  - `result_blob_key`: Schlüssel der gespeicherten Docling-Antwort im Speicher `twox.files.storage`, darf leer sein (Frage 2).
  - `reused_from`: FK auf `IngestJob`, darf leer sein; gesetzt, wenn das Ergebnis eines Auftrags mit gleichem Inhalt wiederverwendet wurde (Frage 4).
  - `page_count`, `section_count`: dürfen leer sein.
  - `created_at`, `started_at`, `finished_at`, `updated_at`.
  - Bedingungen: je Dokumentversion höchstens ein Auftrag mit Status `queued` oder `running` (UniqueConstraint mit Bedingung); Status, Schritt und Fehlerart nur aus der Liste (CheckConstraint).
- **`Section`**:
  - `document_version`: FK, `PROTECT`, `related_name="sections"`; `ingest_job`: FK, `PROTECT`.
  - `ordinal`: eindeutig je Dokumentversion.
  - `page_start`, `page_end`: leer bei Formaten ohne Seiten.
  - Nur bei Frage 3 (a): `line_start`, `line_end`, leer bei PDF.
  - `heading_path` (`ArrayField` von Text) und `heading_text` (dieselben Überschriften, mit ` > ` verbunden; Grundlage des Suchvektors).
  - `text`.
  - `search_vector`: tsvector, Gewicht A aus `heading_text`, B aus `text`, je mit `simple`, `german` und `english` (Frage 1, Punkt 3).
  - `embedding`: `VectorField(dimensions=EMBEDDING_DIMENSIONS)`, darf leer sein; Konstante 1024 (Frage 3 in 044).
  - `embedding_model`, `created_at`.
- **Indizes:** `GinIndex` auf `search_vector`; `GinIndex` mit `OpClass(..., name="gin_trgm_ops")` auf `text`; `HnswIndex` auf `embedding` mit `vector_cosine_ops` (Vorgabewerte von pgvector); Index auf `(document_version, ordinal)`.
- Hilfsfunktion `section_rows(drafts, version, job) -> list[Section]`, die `heading_text` füllt; 046 schreibt Abschnitte nur darüber (`bulk_create` ruft `save()` nicht auf).
- Migration `0002_...` in `backend/twox/ingest/migrations/`.
- **Admin:** nur lesen, nur für Superuser, wie bei `files`; Abschnitte ohne Einbettung in der Liste.
- **Tests:** beide Bedingungen; der Suchvektor enthält Lexeme aus Überschrift (A) und Text (B) und folgt Änderungen am Text, auch über `QuerySet.update()`; Einbettung mit falscher Länge wird abgewiesen; NUL im Text wird von `full_clean` abgewiesen; `PROTECT` verhindert das Löschen einer Version mit Aufträgen; Admin schreibgeschützt.

## Nicht-Ziele

- Kein Ablauf und keine Aufgaben (046), keine Suche (047), keine API (051).
- Keine Registrierung im Änderungsprotokoll (Frage 1, Punkt 4).
- Kein Löschweg für gespeicherte Docling-Antworten (Frage 2).

## Betroffene Bereiche (Ordner, Dateien)

- neu: `backend/twox/ingest/models.py`, `backend/twox/ingest/admin.py`, `backend/twox/ingest/migrations/0002_*.py`
- neu: `backend/tests/ingest/test_models.py`, `backend/tests/ingest/test_admin.py`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-042`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18042` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Tests:
   - `D run --rm backend-dev pytest tests/ingest -v` endet mit Exit-Code 0.
   - `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen.
   - `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
3. `D run --rm backend-dev ruff check .` meldet `All checks passed!`, `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0, `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
4. Weitere Prüfungen wie in `ci.yml`, jeweils ohne Unterschied zum eingecheckten Stand:
   - `D run --rm backend-dev python manage.py makemessages -l de --add-location=file`, danach `git diff --exit-code -I '^"POT-Creation-Date:' -- backend/locale`;
   - `D run --rm backend-dev python manage.py makemigrations --check --dry-run` endet mit Exit-Code 0;
   - `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0;
   - `D run --rm -v "$PWD/web/openapi:/out" backend-dev python manage.py spectacular --file /out/schema.yml` (unter Git Bash mit vorangestelltem `MSYS_NO_PATHCONV=1`), danach `git diff --exit-code -- web/openapi`.
5. `D exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\d ingest_section"'` zeigt `embedding` als `vector(1024)`, einen GIN-Index auf dem Suchvektor, einen GIN-Index mit `gin_trgm_ops` und einen HNSW-Index. Die Ausgabe steht im Kurzbericht.
6. Abräumen: `D --profile dev down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: 040 ist nach `main` zusammengeführt. Fragen 1 bis 4 (hier) und Frage 1 in 044 (Dimension) sind entschieden.

- Welle 2, parallel zu 043 und 044.
- **Keine neue Abhängigkeit.**
- `search_vector` bevorzugt als `GeneratedField(db_persist=True)` über `heading_text` und `text`: `to_tsvector` mit festem `regconfig` und `setweight` sind unveränderlich, `array_to_string` auf dem `ArrayField` vermutlich nicht. Vorher im Datenbank-Container prüfen: `select proname, provolatile from pg_proc where proname in ('to_tsvector','setweight','array_to_string')` und das Ergebnis berichten. Geht es nicht, beim Schreiben füllen; dann muss `section_rows` den Vektor mitliefern, und der Test deckt `bulk_create` ab.
- Die Docling-Antwort liegt nicht in der Datenbank, sondern als Inhalt im Speicher (`store_blob`, inhaltsadressiert); dort gibt es kein Löschen.
- Punkt 4 von Frage 1 hat eine Folge für die API: `requested_by` nennt Benutzer wie das Änderungsprotokoll. Wer es sehen darf, entscheidet Frage 1 in 051 (E-43).
- Daten- und Formfragen sind Stufe C; die Leitstelle führt erst nach der Entscheidung von a7 zusammen.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

1. **Grundform von Einlese-Auftrag und Abschnitt** (Startunterlage 5.7), in vier Punkten:
   1. Je Versuch eine Zeile (b) statt einer überschriebenen Zeile je Version (a). Empfehlung (b): Verlauf ohne Löschen sichtbar.
   2. Fehler als feste Fehlerart plus kurzer technischer Text (b) statt freiem übersetztem Text (a). Empfehlung (b): Die Oberfläche übersetzt die Fehlerart; `django.po` wächst nicht mit jeder Meldung.
   3. Suchvektor ohne Sprachfeld: (a) neues Feld „Sprache“ am Dokument; (b) `simple`, `german` und `english` zusammen; (c) nur `simple`. Empfehlung (b): Die Unterlagen sind gemischt Deutsch und Englisch; `simple` hält Kennungen wörtlich, die Sprachen finden Wortformen; (a) bräuchte eine Angabe beim Hochladen.
   4. Kein Eintrag im Änderungsprotokoll für Aufträge und Abschnitte (b) statt Registrierung in django-auditlog (a). Empfehlung (b): Wer angestoßen hat, steht in `requested_by` mit Zeitpunkt; Abschnitte sind abgeleitete Maschinendaten aus `bulk_create`, das auditlog ohnehin nicht protokolliert. Folge: `requested_by` ist eine Protokollangabe; siehe Frage 1 in 051.
   - Dazu: Beim erneuten Einlesen ersetzt der Ablauf die Abschnitte derselben Version in einer Transaktion (Empfehlung), statt alte Abschnitte am alten Auftrag zu behalten.
2. **Docling-Antwort aufbewahren?** (E-42 regelt nur hochgeladene Dateien.)
   - (a) im Inhaltsspeicher ohne Löschen, wie die Uploads;
   - (b) nicht aufbewahren, nur die Abschnitte;
   - (c) aufbewahren, Löschweg für alle Inhalte später (M5/M6).
   Empfehlung: (a), mit Löschweg zusammen mit dem der Uploads später. Die Antwort ermöglicht neues Bilden der Abschnitte ohne Docling (Abschnittsgröße, Modellwechsel) und das Wiederverwenden bei gleichem Inhalt. Restrisiko Leitplanke 5: Steckt in einem als PDF oder Markdown hochgeladenen Dokument eine Konfiguration mit Zugangsdaten, liegen sie auch in der Antwort – die Originaldatei liegt aber ohnehin schon unlöschbar im selben Speicher, die Antwort fügt keine neue Art von Risiko hinzu.
3. **Zeilenangabe am Abschnitt** (Startunterlage 5.7 „Seite oder Zeile“, Leitplanke 3 „Datei und Zeile“):
   - (a) `line_start`/`line_end` jetzt anlegen, leer bei PDF;
   - (b) erst mit den Einlese-Modulen für Konfigurationen in M5.
   Empfehlung: (b). Docling liefert für Markdown nach bisherigem Stand keine Zeilen (041 prüft das); ein leeres Feld hätte jetzt keinen Nutzen, eine Migration mit zwei leeren Spalten ist später klein. Folge in M2: Fundstelle bei Markdown ist Dokument plus Überschriftenpfad; das steht als Grenze in der Doku (059). Zeigt 041, dass Docling doch Zeilen liefert, wird (a) empfohlen.
4. **Gleicher Inhalt bei mehreren Geräten** (gleiche Prüfsumme; die APS-Unterlagen sind laut Manifest allen acht Anlagen zugeordnet):
   - (a) jede Version einzeln umwandeln, einbetten und als eigenen Treffer zeigen;
   - (b) Docling-Ergebnis über die Prüfsumme wiederverwenden (046), Abschnitte je Version, Einbettungen von gleichem Inhalt übernehmen (048), Treffer gleichen Inhalts und gleicher Seite in der Suche zu einem Treffer mit allen Fundorten zusammenfassen (047);
   - (c) Abschnitte je Inhalt einmal speichern, Versionen verweisen darauf (anderes Datenmodell).
   Empfehlung: (b). Kein mehrfaches stundenlanges Umwandeln, keine verdrängten Treffer, Gerätefilter bleibt einfach; Kosten nur doppelte Abschnittszeilen.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Akzeptanzkriterien 0–6 erfüllt; Läufe am 22.11.2026 im Container (Docker Engine 29.9.3, Compose v5.7.0). Keine neue Abhängigkeit, keine offene Frage an a7.

### Was wurde gebaut?

- `backend/twox/ingest/models.py`:
  - `IngestJob` mit allen Feldern aus dem Umfang. `status` (`IngestStatus`, Standard `queued`), `step` (`IngestStep`, leer erlaubt), `error_code` (`IngestErrorCode`, die zehn Werte aus dem Umfang, leer erlaubt), `error_detail` (`CharField(2000)`, ohne NUL), `attempts` (Standard 0), `requested_by` (`PROTECT`, leer erlaubt), `docling_task_id`, `docling_started_at`, `result_blob_key` (leer oder gültiger Schlüssel von `twox.files.storage`, geprüft über `validate_key`), `reused_from` (FK auf sich selbst, `PROTECT`, `related_name="reused_by"`), `page_count`, `section_count`, `created_at`, `started_at`, `finished_at`, `updated_at`.
  - Bedingungen: `ingest_job_one_active_per_version` (UniqueConstraint auf `document_version` mit `status in (queued, running)`, eigene Meldung für `full_clean`), `ingest_job_status_valid`, `ingest_job_step_valid`, `ingest_job_error_code_valid`.
  - `Section` mit `document_version` und `ingest_job` (beide `PROTECT`, `related_name="sections"`), `ordinal`, `page_start`/`page_end` (leer oder ≥ 1), `heading_path` (`ArrayField` von Text), `heading_text`, `text`, `search_vector`, `embedding` (`VectorField(dimensions=EMBEDDING_DIMENSIONS)`, nullbar), `embedding_model`, `created_at`. Keine Zeilenfelder (Frage 3 (b)).
  - `search_vector` ist ein `GeneratedField(db_persist=True)`: `setweight(to_tsvector(cfg, heading_text), 'A')` und `setweight(to_tsvector(cfg, text), 'B')` je für `simple`, `german`, `english`, mit `||` verbunden. Damit folgt der Vektor jeder Änderung, auch über `QuerySet.update()` und `bulk_create`; `section_rows` muss ihn nicht mitliefern.
  - Bedingungen: `ingest_section_version_ordinal_unique`, `ingest_section_pages_valid` (beide Seiten leer oder `1 ≤ page_start ≤ page_end`), `ingest_section_embedding_has_model` (Einbettung und Modellname nur zusammen).
  - Indizes: `ingest_section_search_gin` (GIN auf `search_vector`), `ingest_section_text_trgm` (GIN mit `OpClass(F("text"), name="gin_trgm_ops")`), `ingest_section_embedding_hnsw` (HNSW, `vector_cosine_ops`, Vorgabewerte von pgvector).
  - `save()` füllt `heading_text` aus `heading_path` (auch bei `update_fields=["heading_path"]`); `join_headings()` verbindet mit ` > `.
  - `section_rows(drafts, version, job) -> list[Section]`: ungespeicherte Zeilen für `bulk_create`, füllt `heading_text`, prüft jede Zeile mit `clean_fields` ohne Datenbankabfrage (getestet: 0 Abfragen für 50 Entwürfe). NUL, leerer Text oder Seite 0 ergeben `ValidationError`, bevor etwas geschrieben wird. Die Entwürfe werden über das Protokoll `SectionDraftLike` (Felder `ordinal`, `heading_path`, `text`, `page_start`, `page_end`) gelesen, damit `models.py` nicht von `sections.py` aus 043 abhängt; der `SectionDraft` aus 043 passt dazu.
  - Konstanten `EMBEDDING_DIMENSIONS = 1024`, `SEARCH_CONFIGS`, `HEADING_SEPARATOR`.
- `backend/twox/ingest/migrations/0002_ingest_job_section.py` (von `makemigrations` erzeugt, baut auf `ingest.0001_extensions` auf; siehe Abweichung 2).
- `backend/twox/ingest/admin.py`: beide Modelle nur lesend (Hinzufügen, Ändern, Löschen `False`), Zugang nur für Superuser wie bei `files`. Abschnittsliste mit Spalte „Einbettung vorhanden“ (Häkchen) und Filter „mit/ohne Einbettung“ sowie Filter nach Modell; `embedding` und `search_vector` werden in Liste und Detail nicht geladen (`defer`, Vorhandensein über eine Annotation).
- `backend/locale/de/LC_MESSAGES/django.po`: 50 neue deutsche Einträge (Feldnamen, Status, Schritte, Fehlerarten, Meldungen).
- Tests: `backend/tests/ingest/test_models.py` und `backend/tests/ingest/test_admin.py`, zusammen 117 Fälle (mit Parametrisierung):
  - beide Bedingungen des Auftrags: zwei aktive Aufträge je Version (alle vier Kombinationen aus `queued`/`running`) ergeben `IntegrityError`, `full_clean` meldet den Konflikt; beendete Aufträge blockieren nicht; Status, Schritt und Fehlerart außerhalb der Liste werden von Datenbank und `full_clean` abgewiesen; jede der zehn Fehlerarten ist speicherbar;
  - Suchvektor: Lexeme der Überschrift mit Gewicht A, des Textes mit B (je Wortform aus `simple` und Stamm aus `german`/`english`); generierte Spalte (`attgenerated = 's'`); folgt `save()` und `QuerySet.update()`; Stichwortsuche findet „Pumpe“ (german), „run“ (english), „S7-1200“ und „192.168.0.10“ (simple);
  - Einbettung: 1024 Werte werden gespeichert und gelesen; 3, 1023 und 1025 Werte werden von `full_clean` (`ValidationError`), `save()` und `QuerySet.update()` (`DataError` der Datenbank) abgewiesen; Einbettung ohne Modellname und umgekehrt wird abgewiesen; ein Abschnitt ohne Einbettung ist gültig (E-59);
  - NUL in Text und Überschriftenpfad wird von `full_clean` und `section_rows` abgewiesen, NUL im Fehlertext von `full_clean`;
  - `PROTECT`: Version mit Aufträgen bzw. Abschnitten, Auftrag mit Abschnitten, wiederverwendeter Auftrag und Benutzer mit Aufträgen lassen sich nicht löschen;
  - Seitenbereiche, eindeutige `ordinal` je Version, `result_blob_key`-Prüfung, Indizes und Spaltentyp `vector(1024)` aus `pg_indexes`/`pg_attribute`;
  - `section_rows` mit `bulk_create`: `heading_text` gefüllt, Suchvektor berechnet, keine Abfrage beim Bilden;
  - Admin: registriert, Superuser sieht Liste und Detail ohne Speichern-Knopf, Hinzufügen/Ändern/Löschen 403, keine Massenlöschung, die Rollen anonym, ohne Rolle, `read`, `manage` und Staff ohne Superuser-Recht landen bei `/admin/login/`, Filter mit/ohne Einbettung, Vektorspalten nicht geladen, deutsche Bezeichnungen.

**Befund `pg_proc`** (im Datenbank-Container, vor dem Bau):

| proname | Argumente | provolatile |
| --- | --- | --- |
| array_to_string | anyarray, text | s |
| array_to_string | anyarray, text, text | s |
| setweight | tsvector, "char" | i |
| setweight | tsvector, "char", text[] | i |
| to_tsvector | json / jsonb / text | s |
| to_tsvector | regconfig, json / regconfig, jsonb / regconfig, text | i |

`to_tsvector` mit festem `regconfig` und `setweight` sind unveränderlich, `array_to_string` nicht. Deshalb rechnet die generierte Spalte über `heading_text` (Text), nicht über das Array; `heading_text` füllen `save()` und `section_rows()`.

### Wie wurde getestet?

`D` = `docker compose -p twox-042`, `.env` aus `.env.example` (ohne BOM) mit `TWOX_API_PORT=18042`. Die Umgebungen „2x“ und „twox-leit“ wurden nicht berührt.

| AK | Ergebnis |
| --- | --- |
| 0 | erfüllt: `docker version` (29.9.3) und `docker compose version` (v5.7.0), Exit 0 |
| 1 | erfüllt: nach `down -v` auf dem committeten Stand Bau Exit 0, `up -d --wait` Exit 0; `D logs migrate`: `Applying ingest.0001_extensions... OK`, `Applying ingest.0002_ingest_job_section... OK` |
| 2 | erfüllt: `pytest tests/ingest` 117 bestanden (dazu 0 fehlgeschlagen); `pytest` `1267 passed, 4 deselected`, mit `-rs` kein übersprungener Test; `pytest -m worker` `4 passed` |
| 3 | erfüllt: `All checks passed!`; `142 files already formatted`; `Success: no issues found in 142 source files` |
| 4 | erfüllt: `makemessages` danach `git diff -I POT-Creation-Date -- backend/locale` ohne Unterschied, `git status` leer; `makemigrations --check --dry-run`: `No changes detected`; Lizenzprüfung `License check passed.`; `spectacular` Exit 0, `git diff -- web/openapi` ohne Unterschied |
| 5 | erfüllt, Ausgabe unten |
| 6 | erfüllt: `D --profile dev down -v` Exit 0 |

Ausgabe zu Kriterium 5 (`\d ingest_section`, Ausdruck der generierten Spalte gekürzt):

```
       Column        |           Type           | Nullable | Default
---------------------+--------------------------+----------+------------------------------------------
 id                  | bigint                   | not null | generated by default as identity
 ordinal             | integer                  | not null |
 page_start          | integer                  |          |
 page_end            | integer                  |          |
 heading_path        | text[]                   | not null |
 heading_text        | text                     | not null |
 text                | text                     | not null |
 search_vector       | tsvector                 |          | generated always as (((((setweight(to_tsvector('simple'::regconfig, COALESCE(heading_text, ''::text)), 'A'::"char") || … || setweight(to_tsvector('english'::regconfig, COALESCE(text, ''::text)), 'B'::"char")) stored
 embedding           | vector(1024)             |          |
 embedding_model     | character varying(200)   | not null |
 created_at          | timestamp with time zone | not null |
 document_version_id | bigint                   | not null |
 ingest_job_id       | bigint                   | not null |
Indexes:
    "ingest_section_pkey" PRIMARY KEY, btree (id)
    "ingest_section_embedding_hnsw" hnsw (embedding vector_cosine_ops)
    "ingest_section_ingest_job_id_6cd8f29c" btree (ingest_job_id)
    "ingest_section_search_gin" gin (search_vector)
    "ingest_section_text_trgm" gin (text gin_trgm_ops)
    "ingest_section_version_ordinal_unique" UNIQUE CONSTRAINT, btree (document_version_id, ordinal)
Check constraints:
    "ingest_section_embedding_has_model" CHECK (embedding IS NULL AND embedding_model::text = ''::text OR embedding IS NOT NULL AND NOT embedding_model::text = ''::text)
    "ingest_section_ordinal_check" CHECK (ordinal >= 0)
    "ingest_section_page_end_check" CHECK (page_end >= 0)
    "ingest_section_page_start_check" CHECK (page_start >= 0)
    "ingest_section_pages_valid" CHECK (page_end IS NULL AND page_start IS NULL OR page_end >= page_start AND page_end IS NOT NULL AND page_start >= 1 AND page_start IS NOT NULL)
Foreign-key constraints:
    "ingest_section_document_version_id_75be795c_fk_files_doc" FOREIGN KEY (document_version_id) REFERENCES files_documentversion(id) DEFERRABLE INITIALLY DEFERRED
    "ingest_section_ingest_job_id_6cd8f29c_fk_ingest_ingestjob_id" FOREIGN KEY (ingest_job_id) REFERENCES ingest_ingestjob(id) DEFERRABLE INITIALLY DEFERRED
```

Gegenprobe während der Arbeit: Die erste Fassung der Seitenbedingung (`page_start >= 1 AND page_end >= page_start`) ließ `(NULL, 1)` und `(1, NULL)` durch, weil eine CHECK-Bedingung mit Ergebnis NULL als erfüllt gilt; der Test fiel, die Bedingung prüft jetzt ausdrücklich `IS NOT NULL`.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a47fdd39495c9edee`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a47fdd39495c9edee`
- Commits: `e3bd8fa` (Modelle, Migration, Admin, Katalog), `af5991d` (Tests), dazu dieser Kurzbericht. Nicht gepusht, nichts zusammengeführt.

### Abweichungen und Hinweise

1. **`backend/locale/de/LC_MESSAGES/django.po` geändert**, obwohl nicht unter „Betroffene Bereiche“: Die neuen Bezeichnungen mit `gettext_lazy` (wie in `files`) verlangen nach der CI einen aktuellen, vollständigen Katalog. Konfliktgefahr beim Zusammenführen mit 041, falls 041 ebenfalls Texte markiert (beide hängen am Dateiende an); dann `makemessages` neu laufen lassen.
2. **Index auf `(document_version, ordinal)`** ist die eindeutige Bedingung `ingest_section_version_ordinal_unique` selbst (eindeutiger B-Baum auf genau diesen Spalten), kein zusätzlicher `Index`. Der Einzelindex des Fremdschlüssels `document_version` ist abgeschaltet (`db_index=False`), weil der zusammengesetzte Index ihn abdeckt. Die Migration trägt `initial = True`, weil `0001_extensions` keine Modelle enthält; so von `makemigrations` erzeugt.
3. **Über den Umfang hinaus** (klein, je mit Test): Bedingung „Einbettung nur mit Modellname“ (048 schreibt beide Felder zusammen mit `bulk_update`); Seitenbedingung in der Datenbank; Prüfung von `result_blob_key` auf das Schlüsselformat; Python-Prüfung der Einbettungslänge für `full_clean` (die Datenbank weist ohnehin ab); `section_rows` prüft die Zeilen mit `clean_fields`.
4. **Leerer Text ist kein gültiger Abschnitt**: `section_rows` weist einen Entwurf mit leerem `text` ab. 043 muss leere Stücke weglassen (sein Test „leerer Text“ deutet darauf hin); sonst endet 046 mit einem Fehler.
5. **E-59 (KI optional):** Der in der Startnachricht genannte „Nachtrag der Leitstelle (E-59, KI optional)“ steht in dieser Auftragsdatei nicht (weder auf dem Zweig noch auf `main`); umgesetzt nach dem Hinweis der Leitstelle und dem Wortlaut der Nachträge in 044–048: `embedding` ist nullbar, ein Abschnitt ohne Einbettung besteht `full_clean` und alle Bedingungen, die Stichwortsuche braucht nur `search_vector`, der Admin zeigt „ohne Einbettung“ als neutralen Filter, nicht als Fehler. Der HNSW-Index enthält leere Einbettungen nicht und stört ohne KI nicht. Am Datenmodell hängt kein Schalter; `TWOX_AI_ENABLED` gehört zu 044/045.
6. **Kein auditlog** für beide Modelle (Frage 1, Punkt 4); `tests/accounts/test_audit.py` bleibt unverändert grün.
7. Die App `ingest` hat in `apps.py` keine `verbose_name`; der Admin zeigt die Gruppe deshalb als „Ingest“ (auch auf Deutsch). `apps.py` lag nicht im Auftragsbereich; Vorschlag: eine Zeile `verbose_name = _("ingest")` mit Übersetzung „Einlesen“ in einem späteren Auftrag.
8. `docs/ARCHITECTURE.md` nennt das Datenmodell noch nicht; das ER-Diagramm ist Teil von 059.
