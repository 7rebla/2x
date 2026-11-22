# Auftrag 049 – Einlesen anstoßen: nach dem Upload, Formatprüfung, Befehl

Meilenstein: M2 · Freigabestufe: C · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
