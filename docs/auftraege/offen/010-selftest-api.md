# Auftrag 010 – Testseite, Teil API

Meilenstein: M0 · Freigabestufe: C · Status: offen

## Ziel

Ein API-Endpunkt liefert einen Wert aus der Datenbank und ein Ergebnis, das der Celery-Worker berechnet hat. Er ist die Datenquelle der Testseite (Auftrag 012) und belegt den Weg durch API, Datenbank, Broker und Worker.

## Umfang

- Endpunkt `GET /api/v1/selftest/`, nur lesend, mit typisierter Antwort (Serializer), damit das OpenAPI-Schema vollständig ist:
  - `database`: `ok` (Wahrheitswert), `server_version` (Zeichenkette, aus `SHOW server_version`), `error` (Zeichenkette oder leer).
  - `worker`: `ok` (Wahrheitswert), `result` (Zeichenkette, erwartet `pong`), `duration_ms` (Zahl), `error` (Zeichenkette oder leer).
- Der Endpunkt schickt die Aufgabe `ping` (aus Auftrag 008) in die Warteschlange `default` und wartet höchstens 5 Sekunden auf das Ergebnis.
- Teilausfälle führen nicht zu einem Serverfehler: Die Antwort hat HTTP 200, der betroffene Teil hat `ok: false` und einen kurzen Fehlertext ohne interne Einzelheiten (keine Zugangsdaten, keine Verbindungszeichenketten, kein Stacktrace).
- Eintrag in `backend/twox/config/urls.py`.
- Tests unter `backend/tests/config/`:
  - Datenbankteil: `ok` ist wahr, `server_version` beginnt mit der Hauptversion der laufenden PostgreSQL.
  - Workerteil, Ausfall (Broker nicht erreichbar bzw. Zeitlimit, im Test nachgestellt): HTTP 200, `ok` ist falsch, `error` ist gefüllt.
  - Der Fehlertext enthält weder Kennwort noch Broker- oder Datenbankadresse.
  - Das Schema enthält den Pfad und die Antwortfelder.
  - Workerteil, Erfolg (Markierung `worker`, gegen den laufenden Worker): `ok` ist wahr, `result` ist `pong`.

## Nicht-Ziele

- Die Seite in der Oberfläche (Auftrag 012).
- Zustand von Docling und Ollama in der Antwort (dafür gibt es `check_docling` und `check_llm`).
- Ein Datenbankmodell. Der Wert kommt ohne neue Tabelle aus der Datenbank.
- Anmeldung (M1).

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/config/` (neue Datei(en) für Ansicht und Serializer, `urls.py`) – oder nach a7s Antwort auf Frage 1
- `backend/tests/config/` (neue Testdateien)

## Akzeptanzkriterien (prüfbar)

Alle Befehle im Wurzelverzeichnis. `D` steht für `docker compose -p twox-010`. Vorher `.env.example` nach `.env` kopieren (falls nicht vorhanden) und darin `TWOX_API_PORT=18010` setzen. `ABRUF` steht für `D exec api python -c "import urllib.request as u; print(u.urlopen('http://localhost:8000/api/v1/selftest/').read().decode())"`.

0. Vorab: `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren oder ausführen; Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. `D up -d --wait db valkey worker api` endet mit Exit-Code 0.
2. `ABRUF` gibt JSON aus mit `database` → `ok: true` und einer `server_version`, sowie `worker` → `ok: true` und `result: pong`.
3. Nach `D stop worker` gibt `ABRUF` innerhalb von etwa 6 Sekunden JSON aus mit `worker` → `ok: false` und gefülltem `error`; `database` bleibt `ok: true`. Kein HTTP-Fehler. Danach `D start worker`.
4. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen.
5. `D run --rm backend-dev pytest -m worker` endet bei laufendem Worker mit Exit-Code 0; der Erfolgsfall des Selftests ist dabei.
6. `D run --rm backend-dev python manage.py spectacular --file /tmp/schema.yml` endet ohne Warnungen; das Schema enthält `/api/v1/selftest/` mit den Feldern `database` und `worker` (Nachweis im Test und im Kurzbericht).
7. `D run --rm backend-dev ruff check .` meldet `All checks passed!`; `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
8. `D run --rm backend-dev python manage.py makemigrations --check --dry-run` meldet `No changes detected` (kein neues Modell).
9. Abräumen: `D down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

- **Voraussetzung:** Die Aufträge 005 und 008 sind zusammengeführt.
- **Keine neue Abhängigkeit.**
- **Stufe C wegen der Berechtigung:** Der Endpunkt ist in M0 ohne Anmeldung erreichbar (ausdrücklich `AllowAny`), weil es noch keine Anmeldung gibt. Er gibt nur die Versionsnummer der Datenbank und `pong` aus. a7 genehmigt das mit der Freigabe der Liste. Im Kurzbericht als Folgeaufgabe für M1 vermerken: Endpunkt auf angemeldete Benutzer beschränken (er stößt bei jedem Aufruf eine Aufgabe an).
- Der Zugriff auf die Warteschlange soll an einer Stelle gekapselt sein (Abschnitt 7: Schnittstellen vor Umsetzung), damit Tests den Ausfall nachstellen können.
- Die Antwortfelder sind die Schnittstelle zu Auftrag 012; Namen nicht ändern. Abweichungen im Kurzbericht nennen.
- Auftrag 009 läuft gleichzeitig und ändert `deploy/compose/compose.yaml`; dieser Auftrag fasst die Datei nicht an.
- Parallele Arbeitsverzeichnisse: immer mit `-p twox-010` und Port 18010 arbeiten.
- Sprache: Code, Feldnamen und Fehlertexte Englisch; jede Funktion hat Typangaben.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle.
- Kein Push. Die Leitstelle committet nach `main` und pusht auf a7s Freigabe.
- Die Frage unten beantwortet a7 mit der Freigabe der Liste. Fehlt die Antwort: nicht raten, Status „wartet auf a7“.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

1. **Wo liegt der Code der Testseite?** Abschnitt 6 sieht keinen allgemeinen Bereich für so etwas vor.
   - (a) Im Paket `twox/config` (keine neue App, keine Abweichung vom Repository-Aufbau).
   - (b) Eine neue App, zum Beispiel `twox/system` – Abweichung von Abschnitt 6, dafür ein fester Platz für eine spätere Statusseite.
   - Empfehlung: (a). Die Seite ist Gerüst; wird später eine Statusseite gewünscht, lässt sich das dann entscheiden.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
