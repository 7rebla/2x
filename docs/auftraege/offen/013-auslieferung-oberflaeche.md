# Auftrag 013 – Auslieferung der Oberfläche durch Django

Meilenstein: M0 · Freigabestufe: C · Status: offen

## Ziel

Die Oberfläche wird fertig gebaut von Django ausgeliefert; im Betrieb läuft kein Node-Server (Abschnitt 5.2). Unter `/` des Dienstes `api` erscheint die Oberfläche aus `web/`.

## Umfang

- Mehrstufiger Image-Bau: Eine Node-Stufe baut die Oberfläche (`npm ci`, `npm run build`); das Ergebnis wird in die Stufe `runtime` des Backend-Images kopiert. Im fertigen Image ist kein Node enthalten.
- Django liefert unter `/` die `index.html` der Oberfläche und unter `/static/` die gebauten Dateien aus – nach a7s Antwort auf Frage 1.
- Statische Dateien werden beim Bau des Images eingesammelt (`collectstatic`), nicht beim Start.
- `deploy/compose/compose.yaml`: Bau-Kontext und Stufen so anpassen, dass `api` und `worker` das Image mit der Oberfläche nutzen. Dienstnamen und Aufrufe bleiben unverändert.
- `.dockerignore` im Wurzelverzeichnis als **Positivliste**: alles ausschließen, nur `backend/` und `web/` zulassen, darin wiederum `node_modules`, `dist`, Zwischenspeicher und `.env` ausschließen. So gelangen weder `.git`, `.claude/` (Arbeitsverzeichnisse anderer Aufträge), `testfactory/`, `testdata/` noch `docs/` in den Bau-Kontext.
- Tests unter `backend/tests/config/`:
  - `/` liefert HTML mit dem Wurzelelement der Oberfläche (im Test aus einem vorbereiteten Verzeichnis, nicht aus dem echten Build).
  - `/api/...` wird nicht von der Auslieferung der Oberfläche abgefangen.
  - Ein unbekannter Pfad unter `/static/` liefert 404.

## Nicht-Ziele

- Playwright-Test (Auftrag 014), Doku (Auftrag 015).
- Ein zusätzlicher Reverse-Proxy-Container, TLS, Sicherheits-Header – später.
- Entwicklungs-Server von Vite mit Weiterleitung an die API.
- Der Antwort-Stream (M3).
- Änderungen unter `web/` und an `.github/workflows/`.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/Dockerfile` (oder Verlagerung des Dockerfiles, wenn der Bau-Kontext es verlangt – dann im Kurzbericht begründen), `backend/.dockerignore` (entfällt, falls der Kontext wechselt)
- `.dockerignore` im Wurzelverzeichnis (neu)
- `backend/pyproject.toml`, `backend/uv.lock` (falls Frage 1 mit WhiteNoise entschieden)
- `backend/twox/config/settings.py`, `backend/twox/config/urls.py`, Ansicht für die Startseite in `backend/twox/config/`
- `backend/tests/config/` (neue Testdateien)
- `backend/scripts/` (nur die Regeldatei der Lizenzprüfung, falls nötig)
- `deploy/compose/compose.yaml`

## Akzeptanzkriterien (prüfbar)

Alle Befehle im Wurzelverzeichnis. `D` steht für `docker compose -p twox-013`. Vorher `.env.example` nach `.env` kopieren (falls nicht vorhanden) und darin `TWOX_API_PORT=18013` setzen. `HOLE <Pfad>` steht für `D exec api python -c "import urllib.request as u,sys; r=u.urlopen('http://localhost:8000'+sys.argv[1]); print(r.status, r.headers.get('Content-Type')); print(r.read(300).decode(errors='replace'))" <Pfad>`.

0. Vorab: `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren oder ausführen; Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. `D --profile dev build` endet mit Exit-Code 0.
2. `D up -d --wait db valkey worker api` endet mit Exit-Code 0; alle vier Dienste sind `healthy`. (Docling ist hier bewusst nicht dabei; den Start aller Container prüft Auftrag 009 und die Abnahme.)
3. `HOLE /` zeigt Status 200, `text/html` und das Wurzelelement der Oberfläche (`<div id="root">`).
4. Die in der ausgelieferten `index.html` genannten Skript- und Stil-Dateien unter `/static/` liefern mit `HOLE` Status 200 und den passenden Inhaltstyp (JavaScript bzw. CSS).
5. `HOLE /api/v1/selftest/` liefert weiterhin JSON mit `database.ok: true` und `worker.ok: true`; `HOLE /api/v1/health/` liefert `{"status":"ok"}`.
6. `D exec api sh -c 'command -v node || echo no-node'` gibt `no-node` aus.
7. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen; `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0; `ruff check .` meldet `All checks passed!`; `mypy .` meldet `Success: no issues found`. Der Dienst `backend-dev` funktioniert weiter ohne gebaute Oberfläche.
8. Die Befehle aus `.github/workflows/ci.yml` (Jobs `backend` und `web`) laufen lokal unverändert mit Exit-Code 0 durch – der Workflow selbst wird nicht geändert. Liste mit Ergebnis im Kurzbericht.
9. Lizenzprüfung: `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0.
10. Bau-Kontext: Die Ausgabe von `D build api` nennt die übertragene Kontextgröße; sie liegt im Bereich von `backend/` und `web/` ohne `node_modules` (Wert in den Kurzbericht). Eine Probedatei unter `.claude/` ändert den Build-Cache nicht (zweiter Build läuft vollständig aus dem Cache).
11. `D down` (ohne `-v`) und erneutes `D up -d --wait db valkey worker api`: `HOLE /` zeigt dieselbe Seite.
12. Abräumen: `D down -v` endet mit Exit-Code 0.
13. Sichtprüfung durch die Leitstelle nach dem Zusammenführen von 012 und 013: `http://localhost:8000/` zeigt im Browser die Testseite mit der Versionsnummer der Datenbank und `pong`. (Automatisiert wird das in Auftrag 014.)

## Vorgaben und Hinweise

**Nachtrag der Leitstelle (21.11.2026, aus der Prüfung von Auftrag 002):** Der Dienst `web-dev` liegt im Profil `dev`. Deshalb gilt abweichend vom Wortlaut dieses Auftrags: Bauen mit `build web-dev` oder `--profile dev build`; Abräumen mit `--profile dev down -v` (bei Playwright zusätzlich `--profile e2e`); den Dienst immer über `run --rm web-dev` ansprechen – ein bloßes `build`, `up` oder `down -v` ohne Profil tut nichts und meldet trotzdem Erfolg. `git check-ignore -q` nimmt nur einen Pfad je Aufruf. Zugelassene Lizenzen bei reinen Entwicklungs- und Build-Paketen zusätzlich: BlueOak-1.0.0, CC-BY-3.0, CC-BY-4.0, CC0-1.0 (E-25).

- **Voraussetzung:** Die Aufträge 002, 009 und 010 sind zusammengeführt (und damit 001, 005, 006, 008). Auftrag 011 liegt ebenfalls auf `main` (für Kriterium 8).
- **Abhängigkeiten.** Mit der Freigabe der Auftragsliste genehmigt a7 – wenn er Frage 1 mit (a) beantwortet – das Paket WhiteNoise. Jede weitere direkte Abhängigkeit ist nicht genehmigt. Ergibt die Lizenzprüfung (Kriterium 9) eine nicht gedeckte Lizenz: nicht einbauen, Frage in den Auftrag, Status „wartet auf a7“.
- **Stand der Recherche vom 21.11.2026 (belegt):** WhiteNoise 6.12.0, MIT; der Classifier nennt Django nur bis 6.0. Ob es unter Django 6.1 fehlerfrei läuft, ist ungeprüft – die Kriterien 3 und 4 sind der Nachweis. Klappt es nicht: nicht ausweichen, sondern Frage in den Auftrag.
- Vite baut mit `base: "/static/"` (Auftrag 002). Die Pfade in der `index.html` müssen zu Djangos `STATIC_URL` passen.
- Der Bau-Kontext braucht `backend/` und `web/`. Auftrag 012 läuft gleichzeitig und ändert nur Inhalte unter `web/`; ausgeliefert wird, was dort zum Zeitpunkt des Baus liegt (Platzhalter oder Testseite).
- Hinweis für später (ungeprüft): Beim Antwort-Stream darf keine Zwischenschicht puffern oder komprimieren. Hier keine Komprimierung einschalten, die später Streams betrifft.
- Der Image-Bau darf keine Geheimnisse brauchen; `collectstatic` muss ohne Datenbank und ohne echte `TWOX_SECRET_KEY` laufen.
- Parallele Arbeitsverzeichnisse: immer mit `-p twox-013` und Port 18013 arbeiten.
- Sprache: Code Englisch; jede Funktion hat Typangaben.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Im Kurzbericht Name, Version, Lizenz und Quelle nennen.
- Kein Push. Die Leitstelle committet nach `main` und pusht auf a7s Freigabe.
- Die Frage unten beantwortet a7 mit der Freigabe der Liste. Fehlt die Antwort: nicht raten, Status „wartet auf a7“.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

1. **Womit liefert Django die gebauten Dateien aus?** Die Unterlage sagt „fertig gebaut von Django ausgeliefert“, nennt aber kein Mittel. Djangos eigene Auslieferung statischer Dateien ist nur für die Entwicklung gedacht.
   - (a) WhiteNoise 6.12.0 (MIT): eine zusätzliche Python-Bibliothek, kein weiterer Container.
   - (b) Ein Reverse-Proxy als weiterer Container (zum Beispiel nginx oder Caddy): ein Baustein mehr als in Abschnitt 5.2 vorgesehen.
   - Empfehlung: (a). Es entspricht der Unterlage am genauesten und hält die Zahl der Bausteine klein. Ein Proxy kann im Skalierungspfad später davor.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
