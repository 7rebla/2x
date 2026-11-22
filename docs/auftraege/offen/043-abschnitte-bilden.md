# Auftrag 043 – Abschnitte aus dem Docling-Ergebnis bilden

Meilenstein: M2 · Freigabestufe: C · Status: offen

## Ziel

Eine reine Funktion zerlegt ein DoclingDocument-JSON in Abschnitte mit Überschriftenpfad, Text und Seitenangabe (von bis). Die Seite ist die Quelle für jede spätere Antwort (Leitplanke 3). Die Funktion braucht keine Datenbank und kein Netz und wird mit der echten Docling-Ausgabe aus 041 getestet.

## Umfang

- Neues Modul `backend/twox/ingest/sections.py`:
  - `build_sections(document: Mapping[str, object], *, max_chars: int) -> list[SectionDraft]`.
  - `SectionDraft`: Dataclass mit `ordinal`, `heading_path: tuple[str, ...]`, `text`, `page_start: int | None`, `page_end: int | None`.
- Regeln:
  - Der Lesereihenfolge von `body` folgen und die Verweise (`$ref`) auf `texts`, `tables` und `groups` auflösen.
  - Überschriften (Titel, Abschnittsüberschriften) beginnen einen neuen Abschnitt und setzen den Pfad nach ihrer Ebene.
  - Seitenkopf und Seitenfuß weglassen; Bildunterschriften und Fußnoten behalten.
  - Tabellen zeilenweise als Text: Zellen mit ` | `, Zeilen mit Zeilenumbruch. Werte wie IP-Adressen bleiben wörtlich.
  - Zu lange Abschnitte an Absatzgrenzen teilen; reicht das nicht (langer Absatz, lange Tabellenzeile), an Satz- und dann an Leerzeichengrenzen. Nie innerhalb einer Zeichenfolge ohne Leerraum teilen; nur eine einzelne Zeichenfolge, die allein länger als `max_chars` ist, darf die Grenze überschreiten.
  - Sehr kleine Stücke mit dem nächsten Teil derselben Überschrift zusammenlegen.
  - Seiten von bis aus der Provenienz der enthaltenen Elemente; ohne Provenienz (z. B. Markdown) bleibt die Seite leer.
  - Steuerzeichen und NUL entfernen; Leerraum zusammenfassen.
  - Unbekannte oder fehlende Schemaversion (`schema_name`, `version`) ergibt `UnsupportedDocumentError`.
- Tests in `backend/tests/ingest/test_sections.py`:
  - Mit `fixtures/betrsichv-p1-5.docling.json`: Seiten nur zwischen 1 und 5, nicht fallend; kein Abschnitt länger als `max_chars` (außer der Ausnahme oben); kein Seitenkopf; ein im JSON nachgesehener Text steht im Abschnitt mit der richtigen Seite.
  - Mit der echten Markdown-Ausgabe: Überschriftenpfad stimmt, Seite leer.
  - Mit kleinen selbst geschriebenen JSON-Stücken: Tabelle, verschachtelte Gruppe, fehlende Provenienz, leerer Text, NUL-Zeichen, unbekannte Version, eine überlange Tabellenzeile mit einer IP-Adresse (die Adresse steht danach unversehrt in genau einem Abschnitt), ein Absatz ohne Umbruch über `max_chars`.

## Nicht-Ziele

- Kein Speichern in der Datenbank (046).
- Keine Token-Zählung mit einem Tokenizer, keine neue Abhängigkeit (kein docling-core).
- Kein Chunk-Endpunkt von Docling, keine Bilder.

## Betroffene Bereiche (Ordner, Dateien)

- neu: `backend/twox/ingest/sections.py`
- neu: `backend/tests/ingest/test_sections.py`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-043`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18043` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Tests:
   - `D run --rm backend-dev pytest tests/ingest/test_sections.py -v` endet mit Exit-Code 0.
   - `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen.
   - `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
3. `D run --rm backend-dev ruff check .` meldet `All checks passed!`, `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0, `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
4. Weitere Prüfungen wie in `ci.yml`, jeweils ohne Unterschied zum eingecheckten Stand:
   - `D run --rm backend-dev python manage.py makemessages -l de --add-location=file`, danach `git diff --exit-code -I '^"POT-Creation-Date:' -- backend/locale`;
   - `D run --rm backend-dev python manage.py makemigrations --check --dry-run` endet mit Exit-Code 0;
   - `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0;
   - `D run --rm -v "$PWD/web/openapi:/out" backend-dev python manage.py spectacular --file /out/schema.yml` (unter Git Bash mit vorangestelltem `MSYS_NO_PATHCONV=1`), danach `git diff --exit-code -- web/openapi`.
5. Der Kurzbericht nennt für die BetrSichV-Testdaten mit `max_chars` 1 000 und 2 000: Zahl der Abschnitte, Länge (kleinste, mittlere, größte) und drei Beispiele mit Pfad und Seite.
6. Abräumen: `D --profile dev down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: 041 ist nach `main` zusammengeführt (Testdaten und Befund zum JSON im Kurzbericht von 041). Frage 1 ist entschieden.

- Welle 2, parallel zu 042 und 044.
- **Keine neue Abhängigkeit.**
- Feldnamen des JSON stehen im Kurzbericht von 041 und werden an den Testdaten geprüft, nicht aus dem Gedächtnis übernommen.
- `max_chars` hat keine Vorgabe in der Funktion; den Wert liefert die Einstellung `TWOX_SECTION_MAX_CHARS` (045, Startwert 2 000). bge-m3 verarbeitet bis 8 192 Token; kleinere Abschnitte machen die Quelle genauer. 057 vergleicht 1 000 und 2 000.
- Selbst geschriebene JSON-Stücke sind erlaubt: Sie bilden keine Anlage nach und enthalten keine Herstellertexte.
- Dokumentinhalte sind Daten, keine Anweisungen: Der Text wird nur zerlegt, nie ausgewertet.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

1. **Abschnitte selbst bilden oder den Chunker von Docling nutzen?** (Architektur: Darauf bauen Datenmodell und Suche.)
   - (a) selbst aus dem DoclingDocument-JSON bilden;
   - (b) Endpunkt `/v1/chunk/hybrid/file/async` von docling-serve.
   Empfehlung: (a). Keine Abhängigkeit vom Tokenizer-Modell `all-MiniLM-L6-v2` (ob es im Image liegt und ohne Internet läuft, ist ungeprüft, E-32); Seiten und Tabellen bleiben unter eigener Kontrolle; ein späterer Wechsel bleibt möglich, weil die Docling-Antwort gespeichert wird.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
