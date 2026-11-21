# Auftrag 009 – docling-serve als Container

Meilenstein: M0 · Freigabestufe: C · Status: offen

## Ziel

docling-serve läuft als eigener Container in der Compose-Umgebung (CPU-Variante). Ein Befehl prüft, ob das Backend den Dienst erreicht. Damit enthält Compose alle Container aus Abschnitt 5.2, und `docker compose up` startet alles.

## Umfang

- `deploy/compose/compose.yaml`: Dienst `docling` mit dem CPU-Image von docling-serve in fester Version (Tag und Digest), ohne Host-Port, Weboberfläche des Dienstes ausgeschaltet, Healthcheck mit großzügiger Anlaufzeit (die Modelle laden beim Start).
- `api` und `worker` hängen **nicht** vom Zustand von `docling` ab; sie starten auch, wenn Docling noch lädt oder fehlt.
- Django-Befehl `check_docling` in der App `ingest` (`backend/twox/ingest/management/commands/check_docling.py`): liest `settings.TWOX_DOCLING_URL`, fragt Erreichbarkeit und Version ab und gibt genau eine Zeile aus:
  - `OK: docling-serve <Version> at <Adresse>` (Exit 0)
  - `FAILED: ...` mit Ursache (Name löst nicht auf, Verbindung abgelehnt, Zeitlimit, unerwartete Antwort) und Exit 1.
  - Option `--timeout <Sekunden>`, Vorgabe 5.
- Tests unter `backend/tests/ingest/` für die Ausgänge, mit einem Ersatzserver im Test (Standardbibliothek). Die Tests brauchen keinen laufenden Docling-Container.
- Prüfung „Betrieb ohne Internet“ (Leitplanke 6) und Prüfung der Modell-Lizenzen mit Ergebnis im Kurzbericht (siehe Hinweise).

## Nicht-Ziele

- Dokumente umwandeln, Einlese-Aufträge, Abschnitte (M2).
- GPU-Varianten des Images. Docling läuft auf der CPU (Abschnitt 5.5); ein ROCm-Image für die Radeon wird nicht veröffentlicht.
- Docling in der CI (das Image ist mehrere Gigabyte groß; Auftrag 011 lässt den Dienst weg).
- Eine eigene Warteschlange oder mehrere Worker für Docling (Skalierungspfad, Abschnitt 5.4).

## Betroffene Bereiche (Ordner, Dateien)

- `deploy/compose/compose.yaml` (nur der Dienst `docling` und sein Volume, falls nötig)
- `backend/twox/ingest/management/**` (neu)
- `backend/tests/ingest/` (neu)

## Akzeptanzkriterien (prüfbar)

Alle Befehle im Wurzelverzeichnis. `D` steht für `docker compose -p twox-009`. Vorher `.env.example` nach `.env` kopieren (falls nicht vorhanden) und darin `TWOX_API_PORT=18009` setzen.

0. Vorab: `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren oder ausführen; Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. `D up -d --wait --wait-timeout 900 docling` endet mit Exit-Code 0; `D ps` zeigt `docling` als `healthy`.
2. `D run --rm backend-dev python manage.py check_docling` gibt bei laufendem Dienst `OK: docling-serve` mit der festgeschriebenen Versionsnummer aus (Exit 0).
3. Nach `D stop docling` gibt derselbe Befehl eine Zeile aus, die mit `FAILED:` beginnt (Exit 1).
4. Bei angehaltenem `docling` endet `D up -d --wait db valkey worker api` mit Exit-Code 0 (kein Dienst hängt von Docling ab).
5. `D up -d --wait --wait-timeout 900` (ohne Dienstnamen – so lautet die Abnahme von M0) endet mit Exit-Code 0; `D ps` zeigt `db`, `valkey`, `worker`, `api` und `docling` als `healthy`.
6. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen – auch ohne laufenden Docling-Container (Nachweis: Lauf nach `D stop docling`).
7. `D run --rm backend-dev ruff check .` meldet `All checks passed!`; `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
8. `D ps --format json` zeigt für `docling` keinen veröffentlichten Host-Port.
9. `D config --images` zeigt für `docling` ein Image mit fester Version, nicht `latest` und nicht `main`.
10. Abräumen: `D down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

- **Voraussetzung:** Auftrag 008 ist zusammengeführt (und damit 001 und 005).
- **Abhängigkeiten.** Mit der Freigabe der Auftragsliste genehmigt a7 das Container-Image docling-serve (CPU-Variante), vorbehaltlich der Lizenzprüfung der enthaltenen Modelle (siehe unten). Kein Python-Paket kommt hinzu; der Befehl nutzt nur die Standardbibliothek.
- **Stand der Recherche vom 21.11.2026:** docling-serve 1.38.2 vom 27.10.2026, MIT (belegt). Images `quay.io/docling-project/docling-serve-cpu` und `ghcr.io/docling-project/docling-serve-cpu`. Port 5001. Größe der CPU-Variante laut README etwa 4,4 GB.
- **Nur teilweise belegt – am laufenden Container und an der Registry bestätigen:**
  - Endpunkte `GET /health`, `GET /ready` (503, solange die Modelle laden) und `GET /version`: laut Recherche im Quelltext (`docling_serve/app.py`) vorhanden; README und Konfigurationsdoku nennen laut Prüfbefund nur `/version`, `/docs`, `/ui` und `/v1/convert/source`. Am laufenden Container über `GET /openapi.json` nachsehen. Rückfallregel: Gibt es `/ready` nicht, Healthcheck und `check_docling` auf `/version` stützen; `/version` ist laut Konfigurationsdoku abschaltbar (`DOCLING_SERVE_SHOW_VERSION_INFO`) und muss eingeschaltet bleiben. Die gewählten Pfade in den Kurzbericht.
  - Das Tag `v1.38.2` der CPU-Variante: an der Registry prüfen (das README nennt nur `latest` und `main`). Tag und Digest festschreiben.
  - Ob `curl` im Image vorhanden ist. Sonst den Healthcheck mit dem im Image vorhandenen Python schreiben.
  - Die Weboberfläche ist laut Doku ohnehin nur mit `DOCLING_SERVE_ENABLE_UI` an; den Schalter trotzdem ausdrücklich ausgeschaltet setzen.
- **Telemetrie (Leitplanke 6):** Laut Prüfbefund sind OpenTelemetry-Metriken und ein Prometheus-Endpunkt `/metrics` standardmäßig an. An der Konfigurationsdoku prüfen und ausschalten, soweit es Schalter gibt (genannt werden `DOCLING_SERVE_OTEL_ENABLE_METRICS` und `DOCLING_SERVE_OTEL_ENABLE_PROMETHEUS`). Im Kurzbericht festhalten, ob der Dienst von sich aus Daten nach außen sendet.
- **Betrieb ohne Internet:** Container in einem Netz ohne Zugang nach außen starten (`internal: true`, nur für diese Prüfung, nicht eingecheckt) und prüfen, ob der Dienst trotzdem bereit wird und die Protokolle keine Download-Versuche zeigen. Zu prüfen ist dabei auch `DOCLING_SERVE_ARTIFACTS_PATH`. Lädt der Dienst Modelle nach: nicht umbauen, sondern als Befund und Frage aufschreiben.
- **Lizenzen der im Image enthaltenen Modelle:** an der Docling-Doku nachsehen und im Kurzbericht auflisten. Ist eine Lizenz nicht MIT, Apache-2.0, BSD oder vergleichbar frei, oder nicht feststellbar: Status „wartet auf a7“.
- Der erste Abruf des Images dauert lange. Als Hintergrundbefehl starten und im Kurzbericht die tatsächliche Größe (`docker image ls`) und die Zeit bis `healthy` nennen.
- Kleinere Images ohne Modelle („slim“) sind laut README angekündigt; nicht darauf warten.
- Parallele Arbeitsverzeichnisse: immer mit `-p twox-009` und Port 18009 arbeiten.
- Sprache: Code und Ausgaben Englisch; jede Funktion hat Typangaben.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Im Kurzbericht Image, Tag, Digest, Lizenz und Quelle nennen.
- Kein Push. Die Leitstelle committet nach `main` und pusht auf a7s Freigabe.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

Keine zum Start. Befunde aus der Prüfung „ohne Internet“, zur Telemetrie und zu den Modell-Lizenzen kommen als Fragen in den Kurzbericht; dann Status „wartet auf a7“.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
