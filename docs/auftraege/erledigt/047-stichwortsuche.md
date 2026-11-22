# Auftrag 047 – Such-Schnittstelle und Stichwortsuche in PostgreSQL

Meilenstein: M2 · Freigabestufe: C · Status: erledigt

## Ziel

Die App `search` bekommt die eigene Such-Schnittstelle (Startunterlage 5.2 und 5.4, E-03) und ihre PostgreSQL-Umsetzung für die Stichwortsuche. Sie findet Wörter in deutscher und englischer Form und Kennungen wörtlich (IP-Adressen, Teilenummern, Fehlercodes), sodass `192.168.0.5` nicht `192.168.0.50` trifft. Auffindbar ist, was Abschnitte hat – unabhängig davon, ob Einbetten gescheitert ist oder ein neues Einlesen läuft. Gleicher Inhalt bei mehreren Geräten ergibt einen Treffer mit allen Fundorten.

## Umfang

- `backend/twox/search/interface.py`:
  - `SearchRequest` (`query`, `device_ids`, `plant_ids`, `limit`).
  - `HitLocation`: Kennungen und Namen von Dokument, Version (mit Nummer und `is_latest_version`), Gerät und Anlage.
  - `SearchHit`: `section_id`, `score`, `match_kinds` (`exact`, `keyword`, später `semantic`), `snippet` als reiner Text, `highlights` (Start und Ende im Ausschnitt), `page_start`, `page_end`, `heading_path`, `locations: list[HitLocation]` (mindestens ein Eintrag).
  - `SearchResult` (`hits`, `semantic_used: bool`).
  - Protokoll `SearchBackend` mit `search(request) -> SearchResult`; `get_search_backend()`.
- `backend/twox/search/postgres.py`, `PostgresSearchBackend`, Teil Stichwort:
  - Volltext mit `websearch_to_tsquery` in `simple`, `german` und `english` (ODER) auf `Section.search_vector`, Rang mit `ts_rank`.
  - Kennungen erkennen (`backend/twox/search/identifiers.py`), mindestens IPv4 mit optionalem Präfix (`/24`), IPv6, MAC-Adressen und Zeichenfolgen aus Buchstaben und Ziffern mit `-`, `_`, `.` oder `/`, die eine Ziffer enthalten (z. B. `PLC-01`, `E1234`). Jede erkannte Kennung sucht zusätzlich als exakte Zeichenfolge mit Wortgrenzen (regulärer Ausdruck mit maskierter Eingabe, beschleunigt durch den Trigramm-Index). Exakte Treffer zuerst.
  - **Versionsregel nach Frage 1** (Empfehlung): Je Dokument zählen die Abschnitte der neuesten Version, die Abschnitte hat. Der Status des letzten Auftrags spielt keine Rolle. Ist eine neuere Version noch nicht oder nicht erfolgreich eingelesen, trägt der Fundort `is_latest_version = false`.
  - Nur Dokumente der Art `document`; optional Gerät und Anlage.
  - **Zusammenfassen nach Frage 4 in 042:** Treffer mit gleicher Prüfsumme des Inhalts, gleicher Seite (bzw. gleichem Überschriftenpfad ohne Seite) und gleichem Text werden zu einem Treffer mit allen Fundorten; gerankt wird einmal.
  - Ausschnitt in Python um die erste Fundstelle, höchstens etwa 300 Zeichen. Kein `ts_headline`-HTML.
- Vor dem Bau im Datenbank-Container prüfen und berichten: `SELECT * FROM ts_debug('german','192.168.0.50')`, ebenso `PLC-01`, `10.0.0.1/24`, `fe80::1`; `\dF+ german`.
- Tests in `backend/tests/search/` mit selbst angelegten Abschnitten in eigenen Worten, ohne Herstellertexte:
  - IP findet genau den Abschnitt mit dieser Adresse, `.5` trifft nicht `.50`; Adresse in einer Tabellenzeile (` | `) wird gefunden.
  - „Steuerungen“ findet „Steuerung“; englische Wortformen werden gefunden.
  - Filter nach Gerät und Anlage.
  - Dokumente der Art `configuration` erscheinen nicht.
  - Versionsregel: neueste Version mit Abschnitten wird durchsucht; ältere Version erscheint nur, wenn die neueste keine Abschnitte hat, dann mit `is_latest_version = false`.
  - Abschnitte ohne Einbettung (Einbetten gescheitert) werden gefunden.
  - Während ein neuer Auftrag derselben Version `queued` oder `running` ist, werden die vorhandenen Abschnitte gefunden.
  - Zwei Geräte mit derselben Datei ergeben einen Treffer mit zwei Fundorten; mit Gerätefilter nur den passenden Fundort.
  - Leere Anfrage und Sonderzeichen (`'`, `\`, `(`) ergeben keinen Fehler; Hervorhebungen liegen auf der Fundstelle.

## Nicht-Ziele

- Keine Vektorsuche (050), keine API (052), keine Oberfläche.
- Kein OpenSearch, kein Qdrant.
- Keine Rechte je Gerät (siehe Hinweise).

## Betroffene Bereiche (Ordner, Dateien)

- neu: `backend/twox/search/interface.py`, `backend/twox/search/postgres.py`, `backend/twox/search/identifiers.py`
- neu: `backend/tests/search/` (`__init__.py`, `test_identifiers.py`, `test_keyword_search.py`)

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-047`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18047` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Tests:
   - `D run --rm backend-dev pytest tests/search -v` endet mit Exit-Code 0.
   - `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen.
   - `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
3. `D run --rm backend-dev ruff check .` meldet `All checks passed!`, `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0, `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
4. Weitere Prüfungen wie in `ci.yml`, jeweils ohne Unterschied zum eingecheckten Stand:
   - `D run --rm backend-dev python manage.py makemessages -l de --add-location=file`, danach `git diff --exit-code -I '^"POT-Creation-Date:' -- backend/locale`;
   - `D run --rm backend-dev python manage.py makemigrations --check --dry-run` endet mit Exit-Code 0;
   - `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0;
   - `D run --rm -v "$PWD/web/openapi:/out" backend-dev python manage.py spectacular --file /out/schema.yml` (unter Git Bash mit vorangestelltem `MSYS_NO_PATHCONV=1`), danach `git diff --exit-code -- web/openapi`.
5. Der Kurzbericht enthält die Ausgaben von `ts_debug` und `\dF+ german` (über `D exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "..."'`) und den Abfrageplan (`EXPLAIN ANALYZE`) einer IP-Suche über 10 000 Testabschnitte nach `ANALYZE`, ohne `enable_seqscan=off`. Nutzt der Planer den Trigramm-Index nicht, gilt der Plan mit Begründung im Kurzbericht ebenfalls als Ergebnis.
6. Abräumen: `D --profile dev down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

- **Nachtrag der Leitstelle (E-59, KI optional):** Einbettungen, Vektorsuche und alles, was ein Modell braucht, sind eine aktivierbare Zusatzfunktion. Schalter `TWOX_AI_ENABLED` (Einstellung in `settings.py`, Standard `False`; `.env.example` mit Kommentar). Bei „aus“: kein Aufruf von Ollama, keine Einbettungs-Aufgaben, Einlesen endet nach den Abschnitten erfolgreich, die Suche arbeitet nur mit der Stichwortsuche, Selbsttest und Oberfläche zeigen „KI nicht aktiviert“ als neutralen Zustand (kein Fehler, kein Warnsymbol). Jede KI-abhängige Stelle braucht einen Test für beide Zustände; die CI läuft mit „aus“ und mit „an“ plus Attrappe.

Voraussetzung: 042 ist nach `main` zusammengeführt. Frage 1 hier und Frage 4 in 042 sind entschieden.

- Welle 3, parallel zu 045.
- **Keine neue Abhängigkeit.** `pg_trgm` und die Volltextsuche gehören zu PostgreSQL, die Django-Teile zu `django.contrib.postgres`.
- Benutzereingaben gehen nur als Parameter in SQL; in regulären Ausdrücken werden sie maskiert.
- pg_trgm ignoriert Zeichen außer Buchstaben und Ziffern; Ähnlichkeitswerte taugen für IP-Adressen wenig. Der Index beschleunigt aber Zeichenfolge und regulären Ausdruck; deshalb die exakte Suche mit Wortgrenzen.
- Rechte: Startunterlage 5.6 nennt „gefiltert nach Gerät und Rechten“. In M2 gelten die Rollen aus E-40; die Rolle prüft die API (052), wer `read` hat, darf alles durchsuchen. Rechte je Gerät sind nicht Teil von M2; die Schnittstelle bleibt dafür erweiterbar (z. B. ein Feld im `SearchRequest`). Grenze in der Doku (059).
- Austauschbar gegen OpenSearch oder Qdrant: keine Django-Querysets in `SearchResult`.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

1. **Welche Version eines Dokuments wird durchsucht?**
   - (a) die neueste Version, die Abschnitte hat; ist eine neuere noch nicht (oder nicht erfolgreich) eingelesen, wird der Treffer als „ältere Version“ gekennzeichnet;
   - (b) nur die neueste Version; hat sie (noch) keine Abschnitte, ist das Dokument nicht auffindbar;
   - (c) alle Versionen mit Angabe der Version.
   Empfehlung: (a). Die Suche hängt an vorhandenen Abschnitten, nicht am Status des letzten Auftrags: Dokumente bleiben während eines erneuten Einlesens und nach einem Ausfall von Ollama auffindbar. Veraltete Treffer sind gekennzeichnet; (c) passt später zum Änderungsvergleich (M8).

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Läufe am 22.11.2026 im Container (Docker Engine 29.9.3, Compose v5.7.0). Keine neue Abhängigkeit. Ergebnis der Akzeptanzkriterien in der Tabelle unter „Wie wurde getestet?“.

### Was wurde gebaut?

- `backend/twox/search/interface.py`: `SearchRequest` (`query`, `device_ids`, `plant_ids`, `limit`; Grenze 1–100, Standard 20; Anfrage höchstens 1 000 Zeichen, sonst `ValueError`), `HitLocation` (Abschnitt, Dokument mit Titel, Version mit Nummer und `is_latest_version`, Gerät und Anlage je mit ID, Schlüssel und Name), `Highlight` (`start`, `end`), `SearchHit` (`section_id`, `score`, `match_kinds`, `snippet`, `highlights`, `page_start`, `page_end`, `heading_path`, `locations`), `SearchResult` (`hits`, `semantic_used`), `MatchKind` (`exact`, `keyword`, `semantic`), Protokoll `SearchBackend`, `get_search_backend()`. Alles unveränderliche Dataclasses mit einfachen Werten; keine Querysets oder Modellobjekte.
- `backend/twox/search/identifiers.py`: Erkennen von Kennungen in der Anfrage und reguläre Ausdrücke dafür (PostgreSQL `~*` und Python `re`, beide mit maskierter Eingabe).
- `backend/twox/search/postgres.py`: `PostgresSearchBackend` mit höchstens drei Abfragen je Suche: (1) `websearch_to_tsquery` je Konfiguration, (2) die Suche selbst als eine SQL-Abfrage mit benannten Parametern, (3) Fundstellen der Wörter für die Hervorhebung. Ausschnitt und Hervorhebungen entstehen in Python.

**Suchregeln in Kürze**

- *Stichwort:* `websearch_to_tsquery` in `simple`, `german`, `english`, mit ODER verbunden, auf `Section.search_vector` (GIN-Index).
- *Exakt:* Jede Kennung der Anfrage (höchstens 10) wird zusätzlich mit `text ~* <Muster>` gesucht (Trigramm-Index). Erkannt werden IPv4 mit optionalem Präfix (Oktette ≤ 255, Präfix ≤ 32), IPv6 (geprüft mit `ipaddress`, optionales Präfix), MAC mit `:` oder `-`, sonst ASCII-Buchstaben und Ziffern, optional verbunden durch `-`, `_`, `.`, `/`, mit mindestens einer Ziffer und mindestens einem Buchstaben oder Verbinder (`PLC-01`, `E1234`, `S7-1200`, `3.5`). Reine Zahlen (`1200`) bleiben der Volltextsuche überlassen. Klammern, Anführungszeichen und Satzzeichen um eine Kennung werden entfernt; ein Wort mit führendem `-` ist ein Ausschluss und wird nicht exakt gesucht.
- *Wortgrenzen:* Vor und nach der Kennung steht kein Buchstabe, keine Ziffer, kein `_` und kein `.`/`-`, auf das ein weiteres Zeichen dieser Art folgt; bei IPv6 und MAC zählt auch `:` als Verbinder. Damit trifft `192.168.0.5` den Text `IP:192.168.0.5`, `192.168.0.5/24`, `192.168.0.5:502`, `… 192.168.0.5.` und `| 192.168.0.5 |`, aber nicht `192.168.0.50`, `10.192.168.0.5` oder `192.168.0.5.1`. Groß- und Kleinschreibung zählt nicht. Schreibvarianten derselben Adresse (`fe80::1` / `fe80:0::1`, MAC mit `-` statt `:`) werden nicht vereinheitlicht.
- *Gewichtung:* `score` = Zahl der exakt gefundenen Kennungen + (bei Stichworttreffer) `ts_rank(search_vector, Anfrage, 32)`. Normierung 32 heißt `rank/(rank+1)`, also unter 1; exakte Treffer stehen damit immer vor reinen Stichworttreffern. `ts_rank` mit den Standardgewichten: Überschrift (A) 1,0, Text (B) 0,4. Gleicher Wert: kleinere Abschnitts-ID zuerst.
- *Versionsregel (Frage 1, E-57):* je Dokument der Art `document` die höchste Version, zu der es Abschnitte gibt; der Auftragsstatus spielt keine Rolle. `is_latest_version` ist `false`, wenn es eine höhere Versionsnummer ohne Abschnitte gibt.
- *Filter:* `device_ids` und `plant_ids`; leer heißt kein Filter, beide zusammen schränken gemeinsam ein (UND).
- *Zusammenfassen (E-55):* gleiche Prüfsumme der Version, gleiche Seiten (ohne Seiten: gleicher Überschriftentext) und gleicher Text (`md5`) ergeben einen Treffer; `LIMIT` zählt zusammengefasste Treffer. Vertreter ist der Abschnitt mit der kleinsten ID; Fundorte sind nach Anlage, Gerät, Titel, Version sortiert, je Version einer.
- *Phrasen (Hinweis aus 042, geprüft):* Der verkettete Suchvektor hat Nahtstellen; z. B. passt `"öffnen Ventil"` auf den Text „Ventil öffnen“, weil „öffnen“ (Kopie `simple`) direkt vor „Ventil“ (Kopie `german`) steht – im Test nachgewiesen. Enthält eine Anfrage einen Phrasenoperator (`<->`, auch bei `PLC-01` oder `fe80::1`), wird ein Treffer je Konfiguration nachgeprüft: `(to_tsvector(cfg, heading_text) || to_tsvector(cfg, text)) @@ Anfrage(cfg)`. Der GIN-Index grenzt vorher ein. Folge: Eine Phrase gilt innerhalb der Überschriften oder innerhalb des Textes, nicht von der Überschrift in den Text.
- *Ausschnitt:* höchstens 300 Zeichen des Textes ab etwa 80 Zeichen vor der ersten Fundstelle, an Leerraum geschnitten, „…“ an Schnittstellen. Hervorhebungen: exakte Kennungen über den Python-Ausdruck, Stichwörter über `ts_headline(…, HighlightAll=true)` mit privaten Markierungszeichen, die in keinem der Texte vorkommen; das Ergebnis von `ts_headline` wird nur ausgewertet, nie weitergegeben. Liegt die Fundstelle nur in der Überschrift, beginnt der Ausschnitt am Textanfang ohne Hervorhebung.
- *Robustheit:* Leere Anfrage ergibt ohne SQL ein leeres Ergebnis; NUL wird durch Leerzeichen ersetzt; Anfragen nur aus Sonderzeichen oder Stoppwörtern ohne Kennung ergeben ein leeres Ergebnis.
- *E-59:* Die Stichwortsuche braucht kein Modell und keine Einbettung; `semantic_used` ist immer `false`. Der Code liest `TWOX_AI_ENABLED` nicht (die Einstellung entsteht in 044/045); die Vektorsuche kommt mit 050.

**Prüfung im Datenbank-Container vor dem Bau** (`D exec -T db sh -c 'psql … -c "…"'`):

```
SELECT * FROM ts_debug('german','192.168.0.50')
  alias  |  description   |    token     | dictionaries | dictionary |    lexemes
 version | Version number | 192.168.0.50 | {simple}     | simple     | {192.168.0.50}

SELECT * FROM ts_debug('german','PLC-01')
   alias   |   description   | token | dictionaries  | dictionary  | lexemes
 asciiword | Word, all ASCII | PLC   | {german_stem} | german_stem | {plc}
 int       | Signed integer  | -01   | {simple}      | simple      | {-01}

SELECT * FROM ts_debug('german','10.0.0.1/24')
  alias  |    description    |  token   | dictionaries | dictionary |  lexemes
 version | Version number    | 10.0.0.1 | {simple}     | simple     | {10.0.0.1}
 file    | File or path name | /24      | {simple}     | simple     | {/24}

SELECT * FROM ts_debug('german','fe80::1')
  alias  |       description        | token | dictionaries | dictionary | lexemes
 numword | Word, letters and digits | fe80  | {simple}     | simple     | {fe80}
 blank   | Space symbols            | ::    | {}           |            |
 uint    | Unsigned integer         | 1     | {simple}     | simple     | {1}

\dF+ german
Text search configuration "pg_catalog.german"
Parser: "pg_catalog.default"
      Token      | Dictionaries
 asciihword      | german_stem
 asciiword       | german_stem
 email           | simple
 file            | simple
 float           | simple
 host            | simple
 hword           | german_stem
 hword_asciipart | german_stem
 hword_numpart   | simple
 hword_part      | german_stem
 int             | simple
 numhword        | simple
 numword         | simple
 sfloat          | simple
 uint            | simple
 url             | simple
 url_path        | simple
 version         | simple
 word            | german_stem
```

Folgerung: Der Parser behandelt IPv4 als `version` (ganzes Lexem, `.5` trifft `.50` schon im Volltext nicht), zerlegt aber `PLC-01` in `plc` und `-01`, `10.0.0.1/24` in zwei Teile und `fe80::1` in `fe80` und `1` (`::` fällt weg). Deshalb die zusätzliche exakte Suche mit Wortgrenzen.

- Tests: `backend/tests/search/test_identifiers.py` und `backend/tests/search/test_keyword_search.py`, zusammen 167 Fälle (mit Parametrisierung), alle Texte selbst geschrieben:
  - Kennungen: Erkennung je Art, Satzzeichen, Ausschlüsse, Doppelte, Höchstzahl; 27 Grenzfälle der Wortgrenzen jeweils in Python **und** in PostgreSQL (gleiches Ergebnis); Maskierung.
  - IP findet genau den Abschnitt (`.5` nicht `.50`, nicht `10.192.168.0.5`), auch in einer Tabellenzeile mit ` | `; Präfix, IPv6, MAC, `PLC-01`, `E1234` wörtlich; exakte Treffer vor Stichworttreffern; Kennung allein zusätzlich zu Wörtern.
  - „Steuerungen“ findet „Steuerung“, „pump runs“ findet „pumps are running“; Überschrift und Text zusammen; Überschrift rankt vor Text.
  - Phrasen: Nahtstelle im gespeicherten Vektor nachgewiesen und durch die Nachprüfung ausgeschlossen; Phrase mit Wortformen; Phrase nicht über Überschrift und Text.
  - Art `configuration` erscheint nicht; Versionsregel (neueste Version mit Abschnitten; ältere mit `is_latest_version = false`, wenn die neuere keinen, einen wartenden, laufenden, gescheiterten oder übersprungenen Auftrag hat); Abschnitte werden gefunden, während derselbe Version ein Auftrag `queued` bzw. `running` ist; ohne Einbettung (Auftrag gescheitert oder fertig) und mit Einbettung.
  - Filter nach Gerät, Anlage und beidem; vollständiger Fundort; zwei Geräte mit derselben Datei ergeben einen Treffer mit zwei Fundorten, mit Gerätefilter nur den passenden; andere Seite oder anderer Text bleibt getrennt; ohne Seiten nach Überschriften; verschiedene Dateien mit gleichem Text bleiben getrennt; `limit` zählt zusammengefasste Treffer.
  - 19 leere bzw. Sonderzeichen-Anfragen (`'`, `\`, `(`, `"`, NUL, SQL-artige Eingabe, `%s`, Operatoren) ohne Fehler; leere Anfrage ohne SQL; Verbindung danach nutzbar; Prüfung von `limit` und Länge.
  - Hervorhebungen liegen auf der Fundstelle (auch in langem Text mit „…“ an beiden Enden), Ausschnittregeln, Markierungszeichen im Text stören nicht.
  - Schnittstelle: `get_search_backend()`, Ergebnis enthält nur einfache Werte; höchstens drei Abfragen je Suche (drei bei Treffern, unabhängig von ihrer Zahl).
  - E-59: Stichwortsuche mit `TWOX_AI_ENABLED` aus und an jeweils gleich, `semantic_used = false`, kein Netzaufruf aus Python (Socket gesperrt).

### Wie wurde getestet?

`D` = `docker compose -p twox-047`, `.env` aus `.env.example` (ohne BOM, mit dem Write-Werkzeug) mit `TWOX_API_PORT=18047`. Die Umgebungen „2x“ und „twox-leit“ wurden nicht berührt.

| AK | Ergebnis |
| --- | --- |
| 0 | erfüllt: `docker version` (Engine 29.9.3) und `docker compose version` (v5.7.0), Exit 0 |
| 1 | erfüllt: Bau Exit 0, `up -d --wait` Exit 0 (am Anfang und nach dem letzten Commit erneut) |
| 2 | erfüllt: `pytest tests/search -v` 167 bestanden; `pytest` `1510 passed, 4 deselected`, mit `-rs` kein übersprungener Test; `pytest -m worker` `4 passed` |
| 3 | erfüllt: `All checks passed!`; `152 files already formatted`; `Success: no issues found in 151 source files` |
| 4 | erfüllt: `makemessages`, danach `git diff -I POT-Creation-Date -- backend/locale` ohne Unterschied und `git status` leer; `makemigrations --check --dry-run`: `No changes detected`; `License check passed.`; `spectacular` Exit 0, `git diff -- web/openapi` ohne Unterschied |
| 5 | erfüllt: `ts_debug` und `\dF+ german` oben, Abfrageplan unten |
| 6 | erfüllt: `D --profile dev down -v` Exit 0 |

**Abfrageplan (Kriterium 5).** 10 000 Abschnitte (100 Geräte, je ein Dokument mit 100 Abschnitten, 60–160 zufällige Wörter aus einer eigenen Wortliste, je eine Adresse `192.168.0–9.x` zweimal im Text, eine Tabellenzeile) per Skript außerhalb des Repositorys in die Entwicklungsdatenbank geschrieben, danach `ANALYZE`; Suche nach `192.168.3.17` (zwei Abschnitte enthalten sie). Die SQL-Abfrage ist die des Backends mit eingesetzten Parametern (`mogrify`), ausgeführt mit `EXPLAIN (ANALYZE, BUFFERS)` über `psql` im Datenbank-Container, ohne `enable_seqscan=off`. Gekürzt auf die Knoten der Abschnittssuche; der übrige Plan sind Hash-Joins über 100 Versionen und Index-Scans über Primärschlüssel für die zwei Treffer:

```
Sort  (cost=646.11..646.12 rows=1 width=819) (actual time=36.000..36.005 rows=2.00 loops=1)
  CTE matched
    ->  Hash Join  (actual time=20.482..35.897 rows=2.00 loops=1)
          Hash Cond: (s.document_version_id = sv.version_id)
          ->  Bitmap Heap Scan on ingest_section s  (cost=120.20..548.79 rows=150 width=901) (actual time=19.267..34.643 rows=2.00 loops=1)
                Recheck Cond: ((search_vector @@ '''192.168.3.17'' | ''192.168.3.17'' | ''192.168.3.17'''::tsquery) OR (text ~* '(?<![[:alnum:]_])(?<![[:alnum:]_][\.\-])192\.168\.3\.17(?![[:alnum:]_])(?![\.\-][[:alnum:]_])'::text))
                Rows Removed by Index Recheck: 1200
                Heap Blocks: exact=768
                ->  BitmapOr  (actual time=0.833..0.833 rows=0.00 loops=1)
                      ->  Bitmap Index Scan on ingest_section_search_gin  (cost=0.00..30.93 rows=149 width=0) (actual time=0.080..0.080 rows=2.00 loops=1)
                            Index Cond: (search_vector @@ '''192.168.3.17'' | ''192.168.3.17'' | ''192.168.3.17'''::tsquery)
                      ->  Bitmap Index Scan on ingest_section_text_trgm  (cost=0.00..89.20 rows=1 width=0) (actual time=0.752..0.752 rows=1202.00 loops=1)
                            Index Cond: (text ~* '(?<![[:alnum:]_])(?<![[:alnum:]_][\.\-])192\.168\.3\.17(?![[:alnum:]_])(?![\.\-][[:alnum:]_])'::text)
          ->  Hash  (rows=100)  -- searchable: DISTINCT ON über 100 Versionen, EXISTS per Index Only Scan auf ingest_section_version_ordinal_unique
  ->  Nested Loop … HashAggregate über matched (2 Zeilen), Limit 20, Index Scans auf ingest_section_pkey, files_documentversion_pkey, files_document_pkey, assets_device_pkey, assets_plant_pkey
Planning Time: 4.988 ms
Execution Time: 36.297 ms
```

Der Planer nutzt beide Indizes (`BitmapOr` aus GIN auf dem Suchvektor und Trigramm-Index auf dem Text). Der Trigramm-Index liefert 1 202 Kandidaten, weil `192` und `168` in jedem Abschnitt stehen und `3`, `17` zu kurz für eigene Trigramme sind; 1 200 fallen bei der Nachprüfung des Ausdrucks heraus. Das kostet hier rund 35 ms; in echten Unterlagen mit weniger gleichförmigen Adressen ist die Kandidatenmenge kleiner.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a7b47d69d9f4b2ced`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a7b47d69d9f4b2ced`
- Commits: `a1e995c` (Schnittstelle, Kennungen, PostgreSQL-Suche), `e564afe` (Tests), dazu dieser Kurzbericht. Nicht gepusht, nichts zusammengeführt.

### Abweichungen und Hinweise

1. **`ts_headline` intern:** Die Fundstellen der Stichwörter (mit Wortformen aller drei Konfigurationen) bestimmt `ts_headline` mit `HighlightAll=true` und privaten Markierungszeichen; Python sucht die markierten Wörter im Originaltext und schneidet den Ausschnitt selbst. Es wird kein `ts_headline`-HTML ausgegeben. Eine reine Python-Lösung müsste die Stammformen von PostgreSQL nachbauen.
2. **Phrasen-Nachprüfung über den Umfang hinaus** (Hinweis aus 042): nur bei Anfragen mit Phrasenoperator; rechnet `to_tsvector` für die Kandidaten des GIN-Index neu. Eine Phrase spannt nicht von der Überschrift in den Text (das tut sie auch im gespeicherten Vektor nicht). Positionen eines tsvector enden bei 16 383; in sehr langen Abschnitten (mehrere tausend Wörter) werden Phrasen am Ende der späteren Kopien nicht mehr gefunden. Eine Lücke zwischen den Kopien im Suchvektor wäre eine Änderung am Datenmodell (042) und ist nicht gemacht.
3. **Exakte Suche nur im Text, nicht in der Überschrift:** Der Trigramm-Index liegt nur auf `text`. Kennungen in Überschriften findet die Volltextsuche (Treffer der Art `keyword`).
4. **Zusätzliche Felder** in `HitLocation`: `section_id` des jeweiligen Abschnitts sowie `device_key` und `plant_key` (die Schlüssel aus M1) neben IDs und Namen. `Highlight` als eigene kleine Dataclass.
5. **Grenzen in `SearchRequest`:** `limit` 1–100, Anfrage höchstens 1 000 Zeichen (sonst `ValueError`; die API in 052 soll das als 400 melden); höchstens 10 Kennungen je Anfrage werden exakt gesucht.
6. **Reine Ausschlussanfrage** (`-pumpe`) ist nach `websearch_to_tsquery` gültig und findet alle Abschnitte ohne das Wort; der GIN-Index hilft dabei nicht (sequenzieller Lauf, begrenzt durch `limit`). Für 052 vorgemerkt: solche Anfragen eventuell abweisen.
7. **`get_search_backend()`** liefert fest `PostgresSearchBackend`; eine Einstellung zur Wahl des Backends gibt es nicht (Einstellungen gehören in diesem Zeitraum 044). Der Schalter `TWOX_AI_ENABLED` wird hier nicht gelesen: Die Stichwortsuche hängt von ihm nicht ab; der Test setzt ihn per `settings`-Fixture auf an und aus.
8. Keine Änderung an `README.md` oder `docs/ARCHITECTURE.md`; die Suchregeln stehen in den Modul-Docstrings, die Doku folgt mit 059 (dort auch die Grenze „keine Rechte je Gerät in M2“).
9. Keine offene Frage an a7.
