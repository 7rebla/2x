# Auftrag 049 – Einlesen anstoßen: nach dem Upload, Formatprüfung, Befehl

Meilenstein: M2 · Freigabestufe: C · Status: erledigt

## Ziel

Jede neue Dokumentversion bekommt nach dem Speichern automatisch einen Einlese-Auftrag. Formate außerhalb einer festen Liste werden sichtbar übersprungen, besonders Textformate, in denen Konfigurationen stecken können (Leitplanke 5, M1-Grenze „Configuration files“). Ein Verwaltungsbefehl stößt das Einlesen für vorhandene, gescheiterte oder hängende Versionen an; das braucht die Testumgebung, deren Handbücher vor M2 hochgeladen wurden. Tests ohne Marker `worker` senden nie an den echten Broker.

## Umfang

- `backend/twox/ingest/formats.py`: Formatbestimmung über Dateiendung des Originalnamens **und** Inhalt. Liste nach Frage 1 (Empfehlung): PDF (Signatur `%PDF-`), DOCX/XLSX/PPTX (ZIP-Signatur und Eintrag `[Content_Types].xml`), Markdown (`.md`; UTF-8 ohne NUL), Bilder PNG, JPEG, TIFF, BMP, WEBP (je Signatur). Der vom Browser gemeldete Typ allein reicht nie.
- `backend/twox/ingest/services.py`:
  - `request_ingest(version, user) -> IngestJob`: legt einen Auftrag `queued` an und sendet `twox.ingest.convert` nach dem Commit (`transaction.on_commit`).
  - Auftrag läuft schon: `IngestAlreadyActiveError`. Version eines Dokuments der Art `configuration`: `IngestNotAllowedError`.
  - Format nicht in der Liste: Auftrag sofort `skipped`/`unsupported_format`, ohne Docling.
  - Scheitert das Senden, bleibt der Auftrag `queued`; Warnung ins Server-Protokoll.
- `backend/twox/files/services.py`: `create_document` und `add_version` rufen nach dem Commit für Dokumente der Art `document` `request_ingest(version, user)` auf (Ansatzpunkt aus 024). Ausdrücklicher Aufruf, kein Signal; Import innerhalb der Funktion. Ein Fehler beim Senden lässt den Upload nicht scheitern.
- `backend/tests/conftest.py`: autouse-Fixture, die das Senden von `twox.ingest.*` in allen Tests ohne Marker `worker` durch eine Attrappe ersetzt (auch in Tests mit `transaction=True`, z. B. `tests/files/test_services.py`). Einfaches `pytest` braucht weiter kein Valkey.
- Verwaltungsbefehl `ingest_versions` (wie `import_devices`: Probelauf als Vorgabe, `--commit` zum Ausführen, `--user` Pflicht, Konto mit Rolle `manage`, wird `requested_by`):
  - `--missing`: Versionen ohne Auftrag;
  - `--failed`: Versionen, deren letzter Auftrag `failed` ist;
  - `--stuck MINUTEN`: Aufträge, die länger als MINUTEN `queued` oder `running` sind (nach `updated_at`), werden `failed`/`timeout` und neu angestoßen;
  - `--all`: neuer Auftrag für jede Version (bildet Abschnitte mit der aktuellen `TWOX_SECTION_MAX_CHARS` neu; die Umwandlung wird über die Wiederverwendung aus 046 übersprungen);
  - `--version ID` (mehrfach).
  - Ausgabe: Zahl der angelegten, übersprungenen und laufenden Aufträge.
- **Tests:** Upload über die API erzeugt nach dem Commit genau einen Auftrag (`django_capture_on_commit_callbacks`); neue Version erzeugt neuen Auftrag; gescheiterter Commit erzeugt keinen; `.txt`, `.json`, `.xml`, `.yaml`, `.conf`, `.rst`, `.html`, `.zip` und eine Datei mit PDF-Endung, aber anderem Inhalt werden `skipped`; PDF, DOCX und Markdown kommen in die Warteschlange; zweiter Anstoß bei laufendem Auftrag wird abgewiesen; Senden scheitert → Auftrag `queued` → `ingest_versions --stuck 0 --commit` stößt neu an; alle Optionen des Befehls, Probelauf ändert nichts, Konto ohne `manage` abgewiesen.

## Nicht-Ziele

- Keine API und keine Oberfläche (051, 053).
- Keine Erkennung von Zugangsdaten, kein Schwärzen (M5).
- Kein Einlesen von ZIP-Archiven, kein HTML.
- Keine Plugin-Schnittstelle für Einlese-Module (Frage 2).
- Der CSV-Import bleibt synchron und unverändert.
- Keine Änderung an `pipeline.py` und `tasks.py` (048 arbeitet dort gleichzeitig).

## Betroffene Bereiche (Ordner, Dateien)

- neu: `backend/twox/ingest/services.py`, `backend/twox/ingest/formats.py`, `backend/twox/ingest/management/commands/ingest_versions.py`
- `backend/twox/files/services.py` (nur der Aufruf nach dem Commit)
- `backend/tests/conftest.py` (autouse-Fixture)
- neu: `backend/tests/ingest/test_services.py`, `backend/tests/ingest/test_formats.py`, `backend/tests/ingest/test_ingest_versions_command.py`; `backend/tests/files/test_services.py`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-049`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18049` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev web-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Tests:
   - `D run --rm backend-dev pytest tests/ingest tests/files -v` endet mit Exit-Code 0.
   - `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen.
   - `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
   - `D stop valkey worker`, danach `D run --rm backend-dev pytest` endet weiter mit Exit-Code 0 (kein Test sendet an den Broker); danach `D up -d --wait --wait-timeout 300 valkey worker`.
3. `D run --rm backend-dev ruff check .` meldet `All checks passed!`, `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0, `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
4. Weitere Prüfungen wie in `ci.yml`, jeweils ohne Unterschied zum eingecheckten Stand:
   - `D run --rm backend-dev python manage.py makemessages -l de --add-location=file`, danach `git diff --exit-code -I '^"POT-Creation-Date:' -- backend/locale`;
   - `D run --rm backend-dev python manage.py makemigrations --check --dry-run` endet mit Exit-Code 0;
   - `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0;
   - `D run --rm -v "$PWD/web/openapi:/out" backend-dev python manage.py spectacular --file /out/schema.yml` (unter Git Bash mit vorangestelltem `MSYS_NO_PATHCONV=1`), danach `git diff --exit-code -- web/openapi`.
5. Browser-Test wie im CI-Job `e2e`: `D --profile e2e pull e2e`, `D --profile dev run --rm web-dev npm ci`; dann der Schritt „Create test account“ aus `ci.yml` wörtlich, nur mit `D` statt `docker compose` (Kennwort nur über den Variablennamen `TWOX_ACCOUNT_PASSWORD`); dann `D --profile e2e run --rm e2e`: alle Fälle bestanden, Exit-Code 0. Danach zeigt `D logs worker` keine unbehandelte Ausnahme; die Aufträge aus den Tests sind `skipped`, `queued`, `running` oder `failed`. Die Laufzeit des e2e-Laufs steht im Kurzbericht (Zeitlimit des CI-Jobs: 20 Minuten).
6. Lokal, mit Docling und Modell: Eine PDF-Datei aus `testdata/klein/` über die Oberfläche hochladen; ohne weiteren Befehl ist ihr Auftrag nach dem Durchlauf `done` (bei gemeinsamem Stand mit 048: nach dem Schritt `embed`).
7. Lokal: `D exec -T api python manage.py ingest_versions --missing --user <konto mit manage>` (Probelauf) nennt die richtige Zahl und ändert nichts; mit `--commit` werden die Aufträge angelegt.
8. Abräumen: `D --profile dev --profile e2e down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

- **Nachtrag der Leitstelle (E-59, KI optional):** Einbettungen, Vektorsuche und alles, was ein Modell braucht, sind eine aktivierbare Zusatzfunktion. Schalter `TWOX_AI_ENABLED` (Einstellung in `settings.py`, Standard `False`; `.env.example` mit Kommentar). Bei „aus“: kein Aufruf von Ollama, keine Einbettungs-Aufgaben, Einlesen endet nach den Abschnitten erfolgreich, die Suche arbeitet nur mit der Stichwortsuche, Selbsttest und Oberfläche zeigen „KI nicht aktiviert“ als neutralen Zustand (kein Fehler, kein Warnsymbol). Jede KI-abhängige Stelle braucht einen Test für beide Zustände; die CI läuft mit „aus“ und mit „an“ plus Attrappe.

Voraussetzung: 046 ist nach `main` zusammengeführt. Fragen 1 und 2 sind entschieden.

- Welle 5, parallel zu 048 und 056 (andere Dateien).
- **Keine neue Abhängigkeit.**
- Stufe C wegen Leitplanke 5 und des Eingriffs in `files/services.py`.
- `skipped` ist kein Fehler, wird aber genauso sichtbar angezeigt (053, 055).
- Ab hier erzeugt jeder Upload in den bestehenden Browser-Tests (M1) einen Auftrag. In der CI gibt es kein Docling; Markdown und PDF enden nach den Wiederholungen mit `failed`. Das ist erwartet.
- Restrisiko im Kurzbericht und für die Doku (059): Markdown wird nur nach Endung und Textprüfung erkannt; eine als `.md` oder PDF hochgeladene Konfiguration wird eingelesen.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

1. **Welche Formate werden in M2 eingelesen?** (Restrisiko Leitplanke 5: eine als Dokument hochgeladene Konfiguration würde sonst indexiert.)
   - (a) alles, was Docling annimmt;
   - (b) feste Liste nach Startunterlage 4 („PDF, Office, Markdown, Bilder mit Text“): PDF, DOCX, XLSX, PPTX, Markdown, PNG, JPEG, TIFF, BMP, WEBP, je mit Prüfung des Inhalts; alles andere (Klartext, JSON, XML, YAML, `.conf`, `.rst`, HTML, ZIP) sichtbar übersprungen bis M5;
   - (c) wie (b) plus Mustersuche nach Kennwörtern mit Sperre.
   Empfehlung: (b). Wenig Code, klar erklärbar; HTML fehlt bewusst, weil die Startunterlage es nicht nennt. Restrisiko: Markdown nur nach Endung und Textprüfung, Konfiguration als PDF oder Markdown wird eingelesen – steht in der Doku. (c) wäre ein halbes Schwärzen und gehört nach M5.
2. **Plugin-Schnittstelle für Einlese-Module** (Startunterlage 5.2: Entry Points; ARCHITECTURE nennt `importers` ab M2):
   - (a) Schnittstelle jetzt bauen, Docling-Dokumente als erstes Modul;
   - (b) in M2 fest in `ingest` (`formats.py`), Schnittstelle mit dem ersten Konfigurations-Modul in M5; die Zeile `importers` in ARCHITECTURE wird angepasst (059).
   Empfehlung: (b). Mit nur einem Modul wäre die Schnittstelle geraten; M5 bringt den zweiten Fall und damit eine belastbare Form.
3. **Standard-Zugangsdaten in Herstellerhandbüchern** (aps-documentation-de/en enthalten laut Manifest auf PDF-S. 38 eine Tabelle mit Zugangsdaten des Auslieferungszustands; nach dem Einlesen sieht jede Rolle `read` sie im Suchausschnitt):
   - (a) als öffentliche Herstellerangabe einlesen und in der Doku als Grenze nennen; Schwärzen in Dokumenten wird mit M5 geprüft;
   - (b) betroffene Abschnitte bis M5 von der Suche ausnehmen (eigene Erkennung, halbes Schwärzen);
   - (c) betroffene Handbücher bis M5 nicht einlesen.
   Empfehlung: (a). Die Angaben sind öffentlich und beschreiben den Auslieferungszustand, nicht diese Anlage; (c) nähme die wichtigste Quelle der Abnahme. In Tests, Probenlisten und Berichten werden nie Ausschnitte dieser Seite wiedergegeben, nur Rang und Seite.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Läufe am 22.11.2026 im Container, Projekt `twox-049`, Port 18049, Docker Engine 29.9.3, Compose v5.7.0. Akzeptanzkriterien 0 bis 8 erfüllt; bei 6 lief der Upload über die Datei-API statt über die Oberfläche (siehe Abweichungen). Keine neue Abhängigkeit, keine Migration, kein neuer übersetzter Text. `pipeline.py`, `tasks.py`, `checks.py`, `apps.py`, `settings.py` und `compose.yaml` sind unverändert.

### Was wurde gebaut?

- `backend/twox/ingest/formats.py`: `check_format(filename, stream) -> FormatCheck` nach E-57. Endung des Originalnamens (klein, letzter Pfadteil) **und** Inhalt müssen passen: PDF `%PDF-` am Dateianfang; DOCX/XLSX/PPTX: ZIP-Signatur und `[Content_Types].xml` im Inhaltsverzeichnis des Archivs (es wird kein Eintrag entpackt); Markdown nur `.md`, ganzer Inhalt gültiges UTF-8 ohne NUL (stückweise gelesen); PNG, JPEG (`.jpg`/`.jpeg`), TIFF (`.tif`/`.tiff`, beide Byte-Reihenfolgen), BMP, WEBP (`RIFF…WEBP`) je Signatur. Der vom Browser gemeldete Typ wird nie gelesen. Ein übersprungener Fall bekommt einen kurzen englischen Grund ohne Dateinamen; ungewöhnliche Endungen (nicht `\.[a-z0-9]{1,10}`) werden darin nicht wiederholt.
- `backend/twox/ingest/services.py`:
  - `request_ingest(version, user) -> IngestJob`: Konfiguration → `IngestNotAllowedError`; aktiver Auftrag → `IngestAlreadyActiveError` (Vorprüfung, dazu die Bedingung aus 042 als Absicherung bei gleichzeitigen Anfragen: `IntegrityError` im Savepoint → derselbe Fehler). Formatprüfung über den Blob-Speicher: unterstützt → `queued` und `transaction.on_commit(send_convert)`; sonst sofort `skipped`/`unsupported_format` mit `finished_at` und Hinweis „…; ingested are PDF, DOCX, XLSX, PPTX, Markdown (.md) and images (…)“; fehlender Inhalt → `failed`/`content_missing`. `requested_by` = `user`.
  - `send_convert(job_id)`: `apply_async` mit `ignore_result=True` und kurzer Wiederholung (2 Versuche, höchstens 1 s Abstand). Scheitert das Senden, bleibt der Auftrag `queued`, Warnung mit Hinweis auf `ingest_versions --stuck` ins Protokoll, keine Ausnahme.
  - Hilfen `active_job`, `check_version_format`, `skipped_detail`.
- `backend/twox/files/services.py`: `create_document` und `add_version` registrieren innerhalb ihrer Transaktion `transaction.on_commit(...)` für Dokumente der Art `document`; der Rückruf importiert `request_ingest` innerhalb der Funktion und fängt jede Ausnahme ab (`logger.exception`), der Upload scheitert also nie daran. Rollt die Transaktion zurück (auch eine äußere), entsteht kein Auftrag.
- `backend/tests/conftest.py`: autouse-Fixture `ingest_messages` (Klasse `IngestMessages`): ersetzt in allen Tests ohne Marker `worker` `apply_async` (damit auch `delay`) jeder registrierten Aufgabe `twox.ingest.*` und `send_task` für diese Namen durch eine Aufzeichnung; `error` simuliert einen ausgefallenen Broker. Gilt auch für Tests mit `transaction=True`; erfasst künftige Aufgaben wie `twox.ingest.embed` aus 048 automatisch.
- Verwaltungsbefehl `ingest_versions` (`backend/twox/ingest/management/commands/ingest_versions.py`): Probelauf als Vorgabe, `--commit`, `--user` Pflicht (aktiv, Rolle `manage`, wird `requested_by`), Auswahl `--missing`, `--failed` (neuester Auftrag `failed`), `--stuck MINUTEN` (aktive Aufträge mit `updated_at` älter als MINUTEN → `failed`/`timeout` mit Hinweis, in derselben Transaktion neuer Auftrag; nur wenn er beim Schreiben noch hängt), `--all`, `--version ID` (mehrfach); Auswahlen werden vereinigt, mindestens eine ist Pflicht. Nur Versionen der Art `document`; unbekannte oder Konfigurations-IDs bei `--version` → Fehler ohne Änderung. Ausgabe: `versions`, `created`, `skipped (unsupported format)`, `failed (content missing)`, `running (left alone)`, `stuck (set to failed and started again)`.
- Tests (neu: `tests/ingest/test_formats.py`, `test_services.py`, `test_ingest_versions_command.py`; erweitert: `tests/files/test_services.py`), zusammen 115 neue Fälle (`tests/ingest` und `tests/files` vorher 507, nachher 622):
  - Formate: jedes Format der Liste mit passendem Inhalt; `.txt`, `.json`, `.xml`, `.yaml`/`.yml`, `.conf`, `.cfg`, `.ini`, `.rst`, `.html`/`.htm`, `.zip`, `.doc`, `.markdown` übersprungen; Inhalt passt nicht zur Endung (Text als PDF, ZIP ohne `[Content_Types].xml`, kaputtes ZIP, NUL oder ungültiges UTF-8 in Markdown, falsche Bildsignaturen); ohne Endung; Grund ohne Dateinamen; ZIP-Prüfung entpackt nichts.
  - Dienst: PDF, DOCX, Markdown → `queued`, genau eine Nachricht erst nach dem Commit; die neun Formate aus dem Auftrag (inkl. PDF-Endung mit anderem Inhalt) → `skipped` ohne Nachricht und ohne Docling; gemeldeter Typ egal; zweiter Anstoß bei `queued`/`running` abgewiesen, nach `done`/`failed`/`skipped` erlaubt; gleichzeitige Anfrage über die Bedingung abgewiesen; Konfiguration abgewiesen; fehlender Inhalt; Senden scheitert → `queued` und Warnung; Zurückrollen sendet nichts; KI an und aus (nur `convert`); Upload über die API (erste und neue Version) erzeugt je genau einen Auftrag nach dem Commit, abgewiesene Version (409) keinen.
  - `files/test_services.py`: Auftrag erst nach dem Commit, neue Version neuer Auftrag, zurückgerollter Upload ohne Auftrag, Senden scheitert ohne Upload-Fehler, beliebiger Fehler in der Einlese-Anfrage wird protokolliert, echter Commit mit `transaction=True` ohne Broker; der bestehende Test mit vier gleichzeitigen Versionen prüft zusätzlich, dass nichts gesendet wurde.
  - Befehl: alle Optionen, Probelauf ändert nichts und sendet nichts, zweiter `--missing`-Lauf findet nichts, `--failed` nur nach neuestem Auftrag, `--stuck` für `queued` und `running` (laufender junger Auftrag bleibt), „Senden scheitert → `queued` → `--stuck 0 --commit` stößt neu an“, `--all` lässt aktive Aufträge stehen, `--version` mehrfach, Kombinationen ohne Doppelte, ungültige Zahlen, Konto ohne `manage`, unbekannt, inaktiv, `--user` fehlt, keine Auswahl.

### Wie wurde getestet?

`D` = `docker compose -p twox-049`, `.env` aus `.env.example` (ohne BOM, mit dem Write-Werkzeug) mit `TWOX_API_PORT=18049`, also KI an. Die Umgebungen „2x“ und „twox-leit“ wurden nicht berührt.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | Engine 29.9.3, Compose v5.7.0, Exit 0 |
| 1 | erfüllt | Bau (mit `web-dev`) Exit 0; `up -d --wait …` Exit 0, alle `Healthy` |
| 2 | erfüllt | `pytest tests/ingest tests/files -v`: `622 passed, 1 deselected`; `pytest`: `2034 passed, 6 deselected`, nichts übersprungen; `pytest -m worker`: `6 passed`; mit `D stop valkey worker`: `pytest` `2034 passed, 6 deselected`, Exit 0; danach `up -d --wait … valkey worker` Exit 0. Nach der letzten Änderung (`ignore_result`) noch einmal vollständig, siehe unten |
| 3 | erfüllt | `All checks passed!`; `178 files already formatted`; `Success: no issues found in 177 source files` |
| 4 | erfüllt | `makemessages` + `git diff -I POT-Creation-Date -- backend/locale` Exit 0, `git status` leer; `No changes detected`; `License check passed.`; `spectacular` + `git diff -- web/openapi` Exit 0 |
| 5 | erfüllt | `pull e2e` Exit 0, `npm ci` Exit 0, „Create test account“ wörtlich mit `D`: `Created account 'e2e-manager' with role 'manage'.`; `D --profile e2e run --rm e2e`: `41 passed (29.0s)`, Exit 0, Laufzeit des Schritts 31 s. Danach 4 Aufträge aus den Tests, alle `skipped`/`unsupported_format` (die Browser-Tests laden `.txt` hoch); `D logs worker` ohne `Traceback`/`ERROR` |
| 6 | erfüllt mit Abweichung | Docling gestartet; `BetrSichV.pdf` aus `testdata/klein/recht/` über die Datei-API hochgeladen (201). Ohne weiteren Befehl: Auftrag 11 `queued` → `done`, 60 Seiten, 140 Abschnitte, 351,7 s ab `started_at` (Docling-Warteschlange und erstes Laden der Modelle eingeschlossen) |
| 7 | erfüllt | Vier Markdown-Versionen aus `testdata/klein/opnsense/markdown/` am Upload-Dienst vorbei angelegt (wie vor M2, ohne Auftrag). `D exec -T api python manage.py ingest_versions --missing --user e2e-manager`: `versions: 4`, `created: 4`, `Dry run: nothing was changed…`; Zahl der Aufträge vorher und nachher 11, weiter 4 Versionen ohne Auftrag. Mit `--commit`: `created: 4`, `Saved.`; alle vier danach `done` (4, 2, 4, 4 Abschnitte), `requested_by` `e2e-manager` |
| 8 | erfüllt | `D --profile dev --profile e2e down -v` Exit 0; keine Container und Volumes `twox-049*` mehr |

Zusätzlich mit gestopptem Valkey (`D stop valkey`) im `api`-Container ein Upload über `create_document`:

- **Erster Versuch: der Upload kehrte erst nach 104,9 s zurück** (Auftrag `queued`, Warnung im Protokoll). Ursache: Celery meldet sich vor dem Senden beim Ergebnisspeicher an (`backend.on_task_call`) und wiederholt die Verbindung zu Valkey rund 100 s lang.
- Behoben mit `ignore_result=True` beim Senden (der Auftrag steht ohnehin in der Datenbank): **8,2 s**, Auftrag `queued`, Warnung. Danach Valkey wieder gestartet, Images neu gebaut, `ingest_versions --stuck 0` (Probelauf: `stuck: 3`, `created: 3`) und mit `--commit`: die drei hängenden Aufträge `failed`/`timeout`, drei neue `done`.

Abschließender Lauf auf dem committeten Stand (nach `ignore_result`): `pytest` `2034 passed, 6 deselected`; `pytest -m worker` `6 passed`; `All checks passed!`; `178 files already formatted`; `Success: no issues found in 177 source files`; danach `D --profile dev --profile e2e down -v` Exit 0. Die Kriterien 6 und 7 liefen auf neu gebauten Images mit dem Stand nach `ignore_result`; der e2e-Lauf (Kriterium 5) lief davor und wurde nicht wiederholt (die Änderung betrifft nur das Senden).

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a21ac86b8c1b61022`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a21ac86b8c1b61022` (relativ zum Projektordner)
- Commits: `Check uploaded files against the ingest format list by name and content`, `Request ingestion after each committed upload; keep test messages off the broker`, `Add ingest_versions command for missing, failed, stuck and all versions`, `Send convert without a result so a down Valkey does not stall uploads`, dazu dieser Kurzbericht. Nicht gepusht, nichts zusammengeführt.

### Abweichungen und Hinweise

1. **Kriterium 6 nicht über die Oberfläche:** Der Upload lief über die echte Datei-API (`POST /api/v1/devices/<id>/documents/`) mit Djangos Testclient im `api`-Container, angemeldet per `force_login` als `e2e-manager` (wie 046). Die Oberfläche ruft dieselbe View auf; einen Datei-Upload im Browser kann ich hier nicht bedienen. Ein Durchlauf von Hand im Browser durch a7 steht aus.
2. **`ignore_result=True` beim Senden** (über den Wortlaut hinaus, mit Test): ohne diese Option hängt ein Upload bei ausgefallenem Valkey rund 105 s. Das Ergebnis von `convert` wird nicht mehr im Ergebnisspeicher abgelegt; der Status steht im Auftrag. Der Worker-Test aus 046 sendet selbst und ist nicht betroffen. Auch mit der Änderung wartet ein Upload bei ausgefallenem Broker rund 8 s (zwei Wiederholungen); mit `retry=False` wären es weniger, dann führt aber schon ein kurzer Aussetzer zu `queued`-Aufträgen für `--stuck`.
3. **Grenze von `--stuck` bei laufenden Aufträgen:** `poll` (046) schreibt `updated_at` nur bei Zustandswechseln, nicht bei jeder Abfrage. Ein Auftrag, an dem Docling lange rechnet, sieht deshalb nach `updated_at` „hängend“ aus. Die Hilfe des Befehls rät, für laufende Aufträge mehr als `TWOX_INGEST_TIMEOUT_SECONDS` (150 min) zu wählen; `--stuck 0` beendet jeden aktiven Auftrag. Die alte Abfragekette endet danach von selbst (`ignored`), Docling rechnet aber weiter. Vorschlag für 048 oder später: `poll` aktualisiert `updated_at` bei jeder Abfrage, dann trennt `--stuck` sauber.
4. **Restrisiko Leitplanke 5 (für 059):** Markdown wird nur über `.md` und die Textprüfung erkannt, PDF nur über die Signatur. Eine als `.md` oder als PDF hochgeladene Konfiguration wird eingelesen. Die ZIP-Prüfung für Office-Dateien prüft nur `[Content_Types].xml`, nicht den Hauptteil (`word/`, `xl/`, `ppt/`); ein anderes ZIP mit dieser Datei ginge an Docling und endete dort voraussichtlich mit `conversion_failed`.
5. **PDF-Signatur nur am Dateianfang:** Manche PDF-Leser nehmen `%PDF-` auch innerhalb der ersten 1 024 Bytes an. Solche Dateien werden hier übersprungen (sichtbar, `the content does not match the extension .pdf`).
6. **`--version` ersetzt Djangos gleichnamige Option** (Ausgabe der Django-Version) nur in diesem Befehl (`conflict_handler="resolve"`).
7. **Ausgabe des Befehls** hat zwei Zeilen mehr als verlangt: `failed (content missing)` und `stuck (…)`.
8. **Doku:** nur in den Modul-Docstrings und der Hilfe des Befehls; README und Betriebsdoku gehören zu 059. `docs/DECISIONS.md`, `docs/STATUS.md` und `docs/ROADMAP.md` sind unverändert.
9. **Konflikte mit 048:** keine gemeinsamen Dateien. Die Fixture in `tests/conftest.py` fängt auch `twox.ingest.embed` ab, sobald 048 sie registriert; 048-Tests, die `send_task` oder `apply_async` selbst ersetzen, überlagern die Fixture wie bisher.
10. **Lokal vorhanden:** Images `twox-049-*`. Ins Repository kam nichts aus `testdata/` hinzu; die Kopien in den Containern sind mit `down -v` weg.

Keine offene Frage an a7.
