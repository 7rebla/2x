# Auftrag 047 – Such-Schnittstelle und Stichwortsuche in PostgreSQL

Meilenstein: M2 · Freigabestufe: C · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
