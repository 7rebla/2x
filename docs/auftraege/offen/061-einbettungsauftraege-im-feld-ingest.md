# Auftrag 061 – Einbettungsaufträge im Feld `ingest`

Meilenstein: M2 · Freigabestufe: B · Status: zur Prüfung

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

- **Was wurde gebaut?**
  - `embed_sections` übernimmt beim Anlegen eines Einbettungsauftrags `page_count` und einen Teilumwandlungs-Hinweis (`error_detail` mit `PARTIAL_DETAIL_PREFIX`) aus dem neuesten Umwandlungs-Auftrag der Version mit Status `done` und gespeicherter Docling-Antwort (`result_blob_key` nicht leer; Einbettungsaufträge haben keine). Andere Texte werden nicht übernommen. Neue Funktion `conversion_state()` im Befehl.
  - `PARTIAL_DETAIL_PREFIX` steht nur noch in `ingest/models.py`. `files/serializers.py` und der Befehl importieren es von dort; `pipeline.py` exportiert es weiter (`pipeline.PARTIAL_DETAIL_PREFIX` gilt weiter).
  - Fehler beim Einbetten: Das Feld `ingest` zeigt `failed`, Schritt `embed`, `embedding_unavailable`; Abschnitte, `section_count` und `page_count` bleiben. Dafür war keine Code-Änderung nötig, die Tests belegen es.
- **Wie wurde getestet?** Drei neue Tests in `tests/ingest/test_embed_sections_command.py`, jeweils mit KI an und aus (Fixture mit Parametern `ai_on`/`ai_off`, Attrappe `FakeEmbedder`, kein echtes Ollama oder Docling):
  - Teilumwandlung: `partly_converted`, `page_count`, `section_count` und `error_detail` wie vorher, wartend und nach dem Einbetten.
  - Vollständige Umwandlung nach älterer Teilumwandlung und späterem Fehlschlag: die neuere vollständige Umwandlung zählt; kein Hinweis.
  - Fehler beim Einbetten: Wiederholungen verbraucht, dann `failed`/`embed`/`embedding_unavailable` mit Abschnitten.
  - Bei KI aus: keine Aufträge, das Feld `ingest` bleibt unverändert.
  - Alle Prüfungen des backend-Jobs im eigenen Compose-Projekt `twox-061` grün: ruff check, ruff format --check, mypy, pytest (2183 bestanden), pytest -m worker (6 bestanden), makemessages-Vergleich, makemigrations --check, Lizenzprüfung, Schema-Vergleich.
- **Zweig und Arbeitsverzeichnis:** `worktree-agent-ae741ad1a9ea17c68`, `.claude/worktrees/agent-ae741ad1a9ea17c68`.
- **Abweichungen:**
  - Die Konstante liegt in `backend/twox/ingest/models.py`, das nicht unter „Betroffene Bereiche“ steht. Der Grund: Ein Import aus `pipeline.py` hätte keinen Zyklus erzeugt, aber Celery, den Docling-Client und den Einbettungs-Client in die API geladen. Die Leitstelle hatte das als Ausweichstelle genannt.
  - Kleine Folgeänderung in `pipeline.py`: Die eigene Definition wurde durch einen Re-Export ersetzt.
  - Keine Migration, keine neue Abhängigkeit.
- **Nachbesserung nach Prüfung der Leitstelle:**
  - Als fertige Umwandlung zählt jetzt auch ein Auftrag mit `failed`, Schritt `embed` und gespeicherter Antwort. Das ist der häufigste Nachhol-Fall: Die Umwandlung gelang, das Einbetten scheiterte. Der neueste Auftrag gewinnt, auch gegen eine ältere `done`-Umwandlung.
  - Sein `error_detail` (Einbettungsfehler, ohne Präfix) wird nicht übernommen.
  - Grenze: `pipeline._fail` überschreibt einen Teilumwandlungs-Hinweis eines solchen Auftrags. Der Hinweis ist dann verloren, und der neue Einbettungsauftrag zeigt `partly_converted` false. Das lässt sich nur mit einem eigenen Feld beheben (siehe unten).
  - Ein gescheiterter Einbettungsauftrag aus `embed_sections` hat keine eigene Antwort. Dann zählt die Umwandlung davor, mit ihrem Hinweis.
  - Zwei weitere Tests mit KI an und aus. Alle backend-Prüfungen erneut grün.
- **Offen (nicht blockierend, schon unter 048 vermerkt):** Ein eigenes Feld statt des Textpräfixes wäre robuster (Stufe C).
