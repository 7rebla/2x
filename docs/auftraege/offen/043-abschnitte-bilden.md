# Auftrag 043 – Abschnitte aus dem Docling-Ergebnis bilden

Meilenstein: M2 · Freigabestufe: C · Status: zur Prüfung

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

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

1. **Abschnitte selbst bilden oder den Chunker von Docling nutzen?** (Architektur: Darauf bauen Datenmodell und Suche.)
   - (a) selbst aus dem DoclingDocument-JSON bilden;
   - (b) Endpunkt `/v1/chunk/hybrid/file/async` von docling-serve.
   Empfehlung: (a). Keine Abhängigkeit vom Tokenizer-Modell `all-MiniLM-L6-v2` (ob es im Image liegt und ohne Internet läuft, ist ungeprüft, E-32); Seiten und Tabellen bleiben unter eigener Kontrolle; ein späterer Wechsel bleibt möglich, weil die Docling-Antwort gespeichert wird.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Läufe am 22.11.2026 im Container, Projekt `twox-043`, Port 18043, Docker Engine 29.9.3, Compose v5.7.0. Kriterien 0 bis 6 erfüllt. Keine neue Abhängigkeit, keine Migration, nur die zwei genannten Dateien (plus dieser Bericht).

### Was wurde gebaut?

- `backend/twox/ingest/sections.py` (neu), nur Standardbibliothek (`re`, `unicodedata`, `dataclasses`, `collections.abc`, `typing`):
  - `build_sections(document, *, max_chars) -> list[SectionDraft]`, reine Funktion, gleiche Eingabe ergibt gleiche Ausgabe (wichtig für die Übernahme von Einbettungen in 048).
  - `SectionDraft` (frozen Dataclass): `ordinal` (ab 0, lückenlos), `heading_path: tuple[str, ...]`, `text` (nie leer), `page_start`, `page_end` (beide gesetzt oder beide `None`, Anfang ≤ Ende). Die Feldnamen passen zum Protokoll `SectionDraftLike` aus 042 (Zweig `worktree-agent-a47fdd39495c9edee`, gelesen mit `git show`); `models.py` ist nicht berührt.
  - `UnsupportedDocumentError` (Unterklasse von `ValueError`), `clean_text()` und die Konstanten der Regeln.
- Regeln (Feldnamen an beiden Testdaten geprüft, siehe unten):
  - **Lesereihenfolge:** `body.children`, Verweise `{"$ref": "#/kind/N"}` auf `texts`, `tables`, `groups` und `pictures` rekursiv aufgelöst. Jedes Element höchstens einmal (Schutz vor doppelten Verweisen und Zyklen), Tiefe höchstens 200. Ungültiger Verweis, fehlender `body` oder zu tiefe Verschachtelung ergeben `UnsupportedDocumentError`.
  - **Überschriftenpfad:** `title` hat Ebene 0, `section_header` seine `level` (fehlend oder ungültig: 1). Eine Überschrift beginnt einen neuen Abschnitt und ersetzt alle Überschriften gleicher oder tieferer Ebene. Die Überschrift steht im Pfad, nicht noch einmal im Text. Eine Überschrift, die ersetzt wird, bevor Text unter ihr stand, wird zum ersten Absatz des nächsten Abschnitts – sonst ginge sie verloren, weil Docling im PDF alle Überschriften auf Ebene 1 setzt (z. B. „Abschnitt 1 Anwendungsbereich …“ direkt vor „§ 1 …“). Eine Überschrift ganz am Ende ohne Text ergibt einen Abschnitt aus ihrem eigenen Wortlaut.
  - **Weggelassen:** Labels `page_header`, `page_footer` und die Ebenen `furniture` und `background`. Bildunterschriften (`caption`) und Fußnoten (`footnote`) bleiben, auch an Tabellen und Bildern (`captions`/`footnotes`). Bilder selbst liefern keinen Text.
  - **Text:** Absätze durch Leerzeile getrennt. Listenpunkte mit ihrem `marker` (sonst „-“) je auf eigener Zeile, verschachtelte Listen folgen ihrem Punkt. Die Teile einer `inline`-Gruppe bilden einen Absatz (mit Leerzeichen verbunden). Code behält seine Zeilenumbrüche.
  - **Tabellen:** aus `data.table_cells` nach `start_row_offset_idx`/`start_col_offset_idx`; eine Zeile je Tabellenzeile, Zellen mit ` | `; eine Zelle über mehrere Spalten oder Zeilen erscheint einmal an ihrem Anfang; leere Zeilen entfallen (z. B. die leere Kopfzeile der Markdown-Tabelle). Erst Bildunterschrift, dann Zeilen, dann Fußnoten.
  - **Größe:** Jeder Absatz, jeder Listenpunkt und jede Tabellenzeile bis `max_chars` bleibt ganz. Längere werden an Zeilenumbrüchen, dann an Satzenden (Leerraum nach `. ! ? …`, auch hinter schließendem Anführungszeichen oder Klammer), dann an Leerraum geteilt – nie innerhalb einer Zeichenfolge ohne Leerraum. Die Stücke werden gierig gefüllt: kleine Absätze, Listenpunkte, Zeilen und der Rest eines geteilten Absatzes kommen zum nächsten Teil derselben Überschrift, solange `max_chars` nicht überschritten wird. Nur eine einzelne Zeichenfolge ohne Leerraum, die allein länger ist, überschreitet die Grenze; sie steht dann allein.
  - **Seiten:** kleinstes und größtes `prov[].page_no` (ganze Zahl ≥ 1) der enthaltenen Elemente; Gruppen über ihre Kinder. Ohne Provenienz bleiben beide Seiten `None`.
  - **Bereinigung:** Steuerzeichen (Unicode Cc, also auch NUL), einzelne Surrogate (Cs, PostgreSQL könnte sie nicht speichern) sowie weiches Trennzeichen, Nullbreiten-Leerzeichen, Wortverbinder und BOM werden entfernt; Leerraum wird zu einem Leerzeichen. Gilt auch für Überschriften und Zellen.
  - **Schema:** `schema_name` muss `DoclingDocument` sein, `version` die Form `1.x.y` (Hauptversion 1); sonst `UnsupportedDocumentError`. `max_chars` < 1 ergibt `ValueError`.
- `backend/tests/ingest/test_sections.py` (neu, 61 Testfälle): die echten Testdaten aus 041 und kleine selbst geschriebene JSON-Stücke (Feldnamen wie im echten JSON, keine Anlage, kein Herstellertext).

### Aufbau des JSON, an den Testdaten geprüft

- Wie im Bericht von 041. Zusätzlich gesehen: Listenpunkte tragen `marker` (`"1."`) und `enumerated`; `text` ist ohne, `orig` mit Marker. Ein Absatz über zwei Seiten hat zwei `prov`-Einträge (`#/texts/65`: Seiten 4 und 5, je mit `charspan`). Im PDF sind alle zehn `section_header` Ebene 1; im Markdown ist der Titel `title`, die drei Unterüberschriften `section_header` Ebene 1. Die Markdown-Tabelle hat eine leere erste Zeile.

### Wie wurde getestet?

`D` = `docker compose -p twox-043`, `.env` aus `.env.example` mit `TWOX_API_PORT=18043`.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | Engine 29.9.3, Compose v5.7.0, Exit 0 |
| 1 | erfüllt | Bau Exit 0; `up -d --wait …` Exit 0, db, valkey, api, worker healthy |
| 2 | erfüllt | `pytest tests/ingest/test_sections.py -v`: `61 passed`; `pytest`: `1310 passed, 4 deselected`, nichts übersprungen; `pytest -m worker`: `4 passed` |
| 3 | erfüllt | `All checks passed!`; `143 files already formatted`; `Success: no issues found in 142 source files` |
| 4 | erfüllt | `makemessages` ohne Unterschied in `backend/locale`; `No changes detected`; `License check passed.`; `spectacular` ohne Unterschied in `web/openapi` |
| 5 | erfüllt | siehe unten |
| 6 | erfüllt | `D --profile dev down -v` Exit 0; keine Container, Volumes oder Netze `twox-043*` mehr. „2x“ und „twox-leit“ nicht angefasst |

Die Tests decken ab:

- BetrSichV (Seiten 1–5), je mit `max_chars` 1 000 und 2 000: Seiten nur 1 bis 5, Anfang und Ende nicht fallend, erster Abschnitt Seite 1, letzter Seite 5; kein Abschnitt über `max_chars` (auch mit 300 und 120); kein Wort verloren, verdoppelt oder zerschnitten (Wortfolge aller Abschnitte gleich der ungeteilten); zwei benachbarte Abschnitte derselben Überschrift passen nie zusammen in `max_chars`; keine Kopf- oder Fußzeile (alle zehn `furniture`-Texte und „Seite 1 von 60“ fehlen); `#/texts/17` (im JSON nachgesehen: Seite 2) steht in genau einem Abschnitt, Seite 2, Pfad „§ 1 Anwendungsbereich und Zielsetzung“; jeder Text der Ebene `body` steht in einem Abschnitt, dessen Seiten seine Seiten umfassen; `#/texts/65` ergibt Seiten 4–5; Listen, Inhaltsverzeichnis-Tabelle und die mitgenommene Überschrift; gleiche Ausgabe bei jedem Lauf.
- Markdown (`sftp-backup`): Pfade `(Titel)`, `(Titel, Preparation)`, `(Titel, Initial setup)`, `(Titel, Finish and test)`, alle Seiten leer; `inline`-Gruppe als ein Absatz; Code mit Zeilenumbrüchen; Tabellenzeile mit `sftp://opnsense@192.168.1.10//…` wörtlich.
- Selbst geschriebene Stücke: Tabelle (Zellen, Spannen, leere Zeile, Bildunterschrift, Fußnote, Seiten 2–3); verschachtelte Gruppen (Kapitel, Liste in Liste, `inline` in `inline`); Überschriftenebenen; Überschrift ohne Text; fehlende und ungültige Provenienz; leere Texte, leere Tabelle, leere Gruppe ergeben keinen Abschnitt; NUL, Steuerzeichen, unsichtbare Zeichen und einzelnes Surrogat in Text, Überschrift, Zelle und Code; Kopf-/Fußzeile und Ebene `background`; neun unbekannte oder fehlende Schema-Angaben, drei angenommene Versionen; sieben kaputte Verweise; fehlender `body` und zu tiefe Verschachtelung; doppelter Verweis; überlange Tabellenzeile mit `192.168.100.200` bei `max_chars` 60 (Adresse unversehrt in genau einem Abschnitt, keine Teiladresse woanders); Absatz über `max_chars` mit Sätzen, ohne Satzende und mit einer Zeichenfolge von 150 Zeichen ohne Leerraum; Satzende hinter Anführungszeichen und Klammer; Zusammenlegen kleiner Absätze; `max_chars` 0, −1, `True`.
- E-59: Ergebnis mit `TWOX_AI_ENABLED` aus und an gleich; das Modul importiert nur die Standardbibliothek (AST-Prüfung), also kein Django, keine Datenbank, kein Netz, kein Modell.

### Kriterium 5: BetrSichV, Seiten 1–5

| `max_chars` | Abschnitte | kleinste | Mittel | Median | größte |
| --- | --- | --- | --- | --- | --- |
| 1 000 | 20 | 346 | 794 | 840 | 982 |
| 2 000 | 13 | 301 | 1 223 | 1 144 | 1 960 |

Beispiele (Pfad, Seiten, Länge, Anfang):

- 1 000, Nr. 4: „§ 1 Anwendungsbereich und Zielsetzung“, Seite 2, 848 Zeichen, beginnt mit der mitgenommenen Überschrift „Abschnitt 1 Anwendungsbereich und Begriffsbestimmungen“, dann „(1) Diese Verordnung gilt …“.
- 1 000, Nr. 2: „I nha l t s ü be r s i ch t“ (so von Docling gelesen), Seiten 1–2, 903 Zeichen: „Inhaltsübersicht“ (mitgenommen), dann die Tabellenzeilen „§ 1 | Anwendungsbereich und Zielsetzung“ usw.; Nr. 3 setzt die Tabelle auf Seite 2 fort.
- 1 000, Nr. 15: „§ 3 Gefährdungsbeurteilung“, Seiten 4–5, 854 Zeichen, „(5) Der Arbeitgeber kann bei der Festlegung …“ (Absatz über den Seitenwechsel).
- 2 000, Nr. 3: „§ 1 Anwendungsbereich und Zielsetzung“, Seiten 2–3, 1 951 Zeichen, „Abschnitt 1 …“ bis Absatz (4).
- 2 000, Nr. 5: „§ 2 Begriffsbestimmungen“, Seite 3, 1 645 Zeichen, „(1) Arbeitsmittel sind Werkzeuge …“ mit den Listen.
- 2 000, Nr. 10: „§ 3 Gefährdungsbeurteilung“, Seite 5, 1 949 Zeichen, „(6) Der Arbeitgeber hat Art und Umfang …“.

Markdown zum Vergleich: 1 000 → 5 Abschnitte (261 bis 873 Zeichen), 2 000 → 4 Abschnitte (261 bis 1 475), Seiten leer.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-aadbe4a9dcf16c367`
- Arbeitsverzeichnis: `.claude/worktrees/agent-aadbe4a9dcf16c367` (relativ zum Projektordner)
- Commits: `Build sections from the DoclingDocument JSON (E-55)`, dazu dieser Kurzbericht. Nicht gepusht, nichts zusammengeführt.

### Abweichungen und Hinweise

1. **Nachtrag E-59 fehlt in dieser Auftragsdatei.** Die Leitstelle nannte einen „Nachtrag der Leitstelle (E-59, KI optional)“ unter „Vorgaben und Hinweise“; in `043-abschnitte-bilden.md` steht er weder auf diesem Zweig noch auf `main` (in 044 bis 060 steht er). Ich habe E-59 so umgesetzt: Die Abschnittsbildung hängt nicht von KI ab und läuft bei „aus“ genauso (Einlesen endet nach den Abschnitten erfolgreich, 046). Test für beide Zustände des Schalters und Nachweis, dass das Modul nur die Standardbibliothek nutzt. `TWOX_AI_ENABLED` selbst legt 044 an; hier wird es im Test nur gesetzt.
2. **Mitgenommene Überschriften.** Eine Überschrift ohne eigenen Text wird zum ersten Absatz des nächsten Abschnitts (siehe Regeln). Das steht nicht im Auftrag; ohne diese Regel fehlten im PDF z. B. „Abschnitt 1 …“, „Abschnitt 2 …“ und „Inhaltsübersicht“ in jedem Abschnitt. Der Pfad bleibt dabei unverändert.
3. **„Sehr kleine Stücke zusammenlegen“** ist durch das gierige Füllen erfüllt: Ein Stück bleibt nur dann klein, wenn das nächste Stück derselben Überschrift nicht mehr hineinpasst (Test prüft das an beiden Größen). Ein Abschnitt, der unter seiner Überschrift insgesamt klein ist, bleibt klein (kleinster Wert 301 bzw. 346 Zeichen); über Überschriften hinweg wird nicht zusammengelegt.
4. **Seiten bei geteilten Absätzen:** Ein Stück eines geteilten Absatzes bekommt die Seiten des ganzen Absatzes. Liegt der Absatz auf zwei Seiten, nennen beide Stücke beide Seiten (genauer ginge es über `charspan`; nicht umgesetzt, die Angabe ist dann eine Seite zu weit, nie falsch zu eng). Tabellenzeilen tragen die Seiten der ganzen Tabelle.
5. **Schemaversion:** angenommen wird jede Version `1.x.y`, geprüft ist nur 1.10.0. Strenger (nur 1.10.x) wäre ein Abbruch bei jedem Docling-Update; lockerer (beliebig) widerspräche dem Auftrag. Falls a7 eine feste Liste möchte, ist es eine Zeile.
6. **Leerraum im Code:** Code behält Zeilenumbrüche, Einrückung und Mehrfach-Leerzeichen werden aber zusammengefasst (Vorgabe „Leerraum zusammenfassen“). Wörter und Zeichen bleiben erhalten.
7. **Leere Tabellenzellen** bleiben als leere Stelle zwischen den Trennern, damit die Spalten zugeordnet bleiben; Leerraum am Zeilenrand wird entfernt (Beispiel: `Spare unit |`).
8. **Weitere Ebenen:** Neben `furniture` lasse ich auch `background` weg (Seitendekoration). Andere Ebenen (`body`, `notes`, z. B. Sprechernotizen in PPTX, `invisible`) bleiben.
9. `.env` (ignoriert) hat `TWOX_API_PORT=18043`. Lokal bleiben die Images `twox-043-*`.

Keine offene Frage an a7.
