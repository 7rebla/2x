# Auftrag 042 – Datenmodell: Einlese-Auftrag und Abschnitt

Meilenstein: M2 · Freigabestufe: C · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
