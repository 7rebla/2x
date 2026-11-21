# Auftrag 009 – docling-serve als Container

Meilenstein: M0 · Freigabestufe: C · Status: wartet auf a7

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

**Status: wartet auf a7.** Alle Akzeptanzkriterien 0 bis 10 sind erfüllt (Läufe am 21.11.2026 im Container, letzter Durchlauf von leerem Zustand auf dem endgültigen Stand). Offen sind drei Fragen (siehe unten): zwei Modell-Lizenzen im Image und die Bestätigung der Maßnahme gegen die gefundene Telemetrie von ONNX Runtime.

### Was wurde gebaut?

- `deploy/compose/compose.yaml`: Dienst `docling`
  - Image `quay.io/docling-project/docling-serve-cpu:v1.38.2@sha256:7a480a1604fa3b42efeddc7db9527690d9f9bc903226136013e2bfe6b1a4dfb0` (Digest des Multi-Plattform-Index; linux/amd64-Manifest `sha256:7b31b3c2efa17534dfcffb61665b71bbc959ad309b5b7ed82c3bbdcc63cc3d58`). Tag an der Registry geprüft (`docker buildx imagetools inspect`).
  - Kein Host-Port, kein Volume (die Modelle liegen im Image).
  - Umgebungsvariablen: `DOCLING_SERVE_ENABLE_UI=false`, `DOCLING_SERVE_SHOW_VERSION_INFO=true`, `DOCLING_SERVE_OTEL_ENABLE_METRICS=false`, `DOCLING_SERVE_OTEL_ENABLE_PROMETHEUS=false`, `DOCLING_SERVE_OTEL_ENABLE_TRACES=false`, `DOCLING_SERVE_OTEL_ENABLE_OTLP_METRICS=false`, `DOCLING_SERVE_ENABLE_REMOTE_SERVICES=false`, `DOCLING_SERVE_ALLOW_EXTERNAL_PLUGINS=false`, `HF_HUB_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1`, `ORT_DISABLE_TELEMETRY=1` (siehe Netzverhalten).
  - Healthcheck: Python im Image ruft `http://localhost:5001/ready` (503, solange die Modelle laden); `start_period: 300s`, `start_interval: 5s`, `interval: 15s`, `restart: unless-stopped`.
  - Kein anderer Dienst hängt von `docling` ab; `api`, `worker`, `migrate`, `backend-dev` sind unverändert.
- `backend/twox/ingest/management/commands/check_docling.py`: Befehl `check_docling` (nur Standardbibliothek). Drei Schritte: Name auflösen, TCP-Verbindung, `GET <TWOX_DOCLING_URL>/version`; liest daraus den Schlüssel `docling-serve`. Ausgabe genau eine Zeile `OK: docling-serve <Version> at <Adresse>` (Exit 0) oder `FAILED: …` (Exit 1) mit Ursache: Adresse ungültig, Name löst nicht auf, Verbindung abgelehnt, Zeitlimit beim Verbinden oder beim Warten auf Antwort, unerwartete Antwort (HTTP-Status, keine gültige HTTP-Antwort, keine Versionsangabe; bei 403 Hinweis auf `DOCLING_SERVE_SHOW_VERSION_INFO`). Option `--timeout <Sekunden>`, Vorgabe 5, je Schritt. Ohne Proxy, Antwort auf 64 KiB begrenzt.
- `backend/tests/ingest/test_check_docling.py`: 23 Testfälle mit Ersatzserver aus der Standardbibliothek auf 127.0.0.1; keine echte Namensauflösung, kein Docling-Container nötig.
- `settings.py` ist nicht geändert (`TWOX_DOCLING_URL` mit Vorgabe `http://docling:5001` gab es schon).

**Gewählte Pfade:** Healthcheck `/ready`, `check_docling` `/version`. Laut `GET /openapi.json` des laufenden Containers gibt es `/health`, `/ready`, `/version` und die `/v1/…`-Endpunkte; `/metrics`, `/ui` und `/` antworten mit 404. Die Antwort von `/version`: `{"docling-serve":"1.38.2","docling-jobkit":"3.9.1","docling":"2.142.1","docling-core":"2.104.0","docling-ibm-models":"4.0.4","docling-parse":"7.23.0","python":"cpython-312 (3.12.15)","plaform":"…"}` (der Schlüssel heißt im Dienst wirklich `plaform`).

**curl** ist im Image vorhanden (`/usr/bin/curl`); der Healthcheck nutzt trotzdem Python wie die anderen Dienste.

### Wie wurde getestet?

`D` = `docker compose -p twox-009` im Wurzelverzeichnis des Arbeitsverzeichnisses, `.env` mit `TWOX_API_PORT=18009`, Docker Engine 29.9.3, Compose v5.7.0.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `29.9.3`, `Docker Compose version v5.7.0`, beide Exit-Code 0 |
| 1 | erfüllt | `Container twox-009-docling-1 Healthy`, Exit-Code 0; `D ps`: `docling Up 15 seconds (healthy)` |
| 2 | erfüllt | `OK: docling-serve 1.38.2 at http://docling:5001`, Exit-Code 0 |
| 3 | erfüllt | `FAILED: cannot resolve host 'docling' (Name or service not known) - is the docling container running in the same compose project?`, Exit-Code 1 |
| 4 | erfüllt | Exit-Code 0; `db`, `valkey`, `api`, `worker` healthy, `docling Exited (0)` |
| 5 | erfüllt | Exit-Code 0; `api`, `db`, `docling`, `valkey`, `worker` jeweils `(healthy)`, `migrate` beendet; danach erneut `OK: docling-serve 1.38.2 …` |
| 6 | erfüllt | bei angehaltenem `docling`: `78 passed, 3 deselected in 21.91s`, Exit-Code 0, nichts übersprungen (die 3 abgewählten sind die `worker`-Tests aus Auftrag 008) |
| 7 | erfüllt | `All checks passed!`; zusätzlich `ruff format --check`: `47 files already formatted`; `Success: no issues found in 47 source files` |
| 8 | erfüllt | `Publishers` von `docling`: 5001/tcp und 8080/tcp (im Image deklariert) mit `PublishedPort 0` und leerer Adresse; einziger veröffentlichter Port im Projekt: `api` auf `127.0.0.1:18009` |
| 9 | erfüllt | `quay.io/docling-project/docling-serve-cpu:v1.38.2@sha256:7a480a16…dfb0` |
| 10 | erfüllt | `D down -v` Exit-Code 0 (beide Volumes und das Netz entfernt); danach `D --profile dev down -v` Exit-Code 0 („No resource found“); keine Container und Volumes des Projekts mehr. Das Projekt `2x` der Leitstelle lief durchgehend weiter |

- Größe des Images: `docker image ls` meldet 7.57 GB Plattenbedarf, 2.22 GB Inhalt (komprimiert). Erster Abruf: 99 s.
- Zeit bis `healthy`: 11 bis 19 s in allen Läufen (die Modelle liegen im Image und laden in etwa 2 s).
- Probeumwandlung (nicht Teil der Kriterien): ein kleines, selbst erzeugtes PDF mit Überschrift und Tabelle wird mit und ohne `force_ocr` korrekt in Markdown umgewandelt, auch ohne Netz.

### Netzverhalten (Leitplanke 6)

Vorgehen: (1) Python-Audit-Hook (`sys.addaudithook`, über `PYTHONPATH` geladen) protokolliert jede Namensauflösung, jedes `connect`, jede urllib-Anfrage und jeden Unterprozess des Dienstes. (2) Ein Abtaster im Container liest alle 50 ms `/proc/net/tcp` und `/proc/net/tcp6` und ordnet Verbindungen zu fremden Adressen über die Socket-Inode dem Prozess zu. Damit sind auch Verbindungen aus nativem Code sichtbar. (3) Start in einem Netz mit `internal: true`. Alle Hilfsdateien lagen nur im Zwischenordner der Sitzung, nichts davon ist eingecheckt.

Befunde:

1. **Ohne Internet läuft der Dienst.** Im Netz mit `internal: true` wird er nach 18 bis 19 s `healthy`, und Umwandlungen gelingen. Das Protokoll meldet `artifacts_path is set to a valid directory. No model weights will be downloaded at runtime.` `DOCLING_SERVE_ARTIFACTS_PATH` setzt das Image selbst (`/opt/app-root/src/.cache/docling/models`). Der Audit-Hook zeigt im Dienstprozess außer `uname -p` keine Namensauflösung und kein `connect`.
2. **Fehlende Modelle werden nicht nachgeladen.** Probeweise angefordert wurden Bildbeschreibung, Code/Formel, die VLM-Pipeline und EasyOCR auf Japanisch. Jede Anfrage scheitert sofort mit einer Meldung wie `Model 'ibm-granite/granite-docling-258M' not found in artifacts_path` oder `Missing …/EasyOcr/japanese_g2.pth and downloads disabled`. Es gab keinen Download-Versuch.
3. **Telemetrie von ONNX Runtime: gefunden und abgeschaltet.** Ohne Schalter öffnet der Dienstprozess (pid 1) etwa 20 s nach dem Start eine HTTPS-Verbindung zu einer Microsoft-Adresse. Beobachtet: 52.182.143.212, 4.150.223.102, 74.151.238.96/.129, 51.132.193.106, jeweils Port 443, die Verbindung wird aufgebaut und wieder geschlossen. Der Audit-Hook sieht sie nicht, sie kommt also aus nativem Code. Die geladene Bibliothek `onnxruntime_pybind11_state…so` (onnxruntime 1.31.0, MIT) enthält den Namen `mobile.events.data.microsoft.com`; der löst im Container auf 74.151.238.101 auf, dasselbe Netz. Sie enthält außerdem Zeichenketten zu 1DS-Telemetrie, eine dauerhafte „telemetry device ID“ und den Schalter `ORT_DISABLE_TELEMETRY`. Gegenprobe mit gleichem Ablauf (Start, Umwandlung, 3 Minuten beobachtet): ohne `ORT_DISABLE_TELEMETRY` gibt es die Verbindung, mit `ORT_DISABLE_TELEMETRY=1` keine einzige Verbindung nach außen. Der Schalter steht jetzt in `compose.yaml`. Welche Daten gesendet werden, habe ich nicht untersucht (TLS). Eine offizielle Doku des Schalters für Linux habe ich nicht gefunden. Belegt sind er durch die Zeichenkette in der Bibliothek, die Messung und einen Upstream-Fix ([microsoft/onnxruntime #32226](https://app.semanticdiff.com/gh/microsoft/onnxruntime/commit/9aa8fb069273d75d07d137629d9127f9ef5deb69), laut Suchergebnis: POSIX-Telemetrie seit 1.29, `ORT_DISABLE_TELEMETRY=1`). Die ältere [Privacy.md](https://sources.debian.org/src/onnxruntime/1.23.2%2Bdfsg-6/docs/Privacy.md) nennt Telemetrie nur für Windows und ist damit überholt.
4. **Metriken/OpenTelemetry:** Mit den vier `DOCLING_SERVE_OTEL_*`-Schaltern liefert `/metrics` 404. Die FastAPI-Instrumentierung meldet sich beim Start trotzdem (`Instrumenting FastAPI with OpenTelemetry`); ohne Exporter und ohne Endpunkt gab es keine Verbindung.
5. **Sonst im Code gesucht:** `sentry_sdk` wird nur von `fastapi_cloud_cli` importiert, nicht vom Dienst. In docling-serve, docling, docling-jobkit, rapidocr und easyocr gibt es keine Aufrufe an Analysedienste. Download-Code gibt es (rapidocr von modelscope.cn, easyocr, Hugging Face Hub), er wird aber bei gesetztem `artifacts_path` nicht benutzt (siehe 2.).
6. **Was der Dienst nur auf Anfrage nach außen tut:** Eine Quelle `{"kind": "http", "url": …}` an `/v1/convert/source` löst der Dienst selbst auf (beobachtet: `getaddrinfo('example.org')`, danach `URL is not allowed`). Das Backend darf Docling deshalb nur Dateien schicken, keine Adressen. Die Seiten `/docs` und `/scalar` laden Schriften und Skripte von CDNs, aber im Browser des Betrachters; ohne Host-Port sind sie nicht erreichbar.
7. **Im Image, aber nicht gestartet:** Ray (`ray/_raylet.so`). Ray kann Nutzungsstatistiken senden, startet mit der lokalen Engine aber nicht; in keinem Lauf gab es eine Verbindung. Nicht weiter abgesichert (möglich wäre `RAY_USAGE_STATS_ENABLED=0`; nicht gemessen, daher nicht gesetzt).

Grenzen der Prüfung: Der Abtaster sieht TCP, aber keine UDP-Anfragen an den DNS-Dienst von Docker (127.0.0.11); ob nativer Code nach dem Abschalten noch Namen auflöst, ist ungeprüft. Beobachtet wurde jeweils bis etwa 3 Minuten nach dem Start, mit Umwandlungen. Ein Versand in größeren Abständen (Stunden) ist nicht ausgeschlossen. Wirksam dagegen wäre, `docling` in ein Netz mit `internal: true` zu legen, an dem `api` und `worker` zusätzlich hängen (Frage 3).

### Lizenzen

Dienst und Image:

| Bestandteil | Version | Lizenz | Quelle |
| --- | --- | --- | --- |
| docling-serve | 1.38.2 | MIT | Image-Label `org.opencontainers.image.licenses=MIT`; https://github.com/docling-project/docling-serve |
| Basis-Image `quay.io/sclorg/python-312-c9s` (CentOS Stream 9, Python 3.12.15) | – | Betriebssystempakete unter verschiedenen Lizenzen, Label `org.label-schema.license=GPLv2` | Image-Labels; unverändert als Laufzeit benutzt, nicht einzeln geprüft |
| onnxruntime (im Image) | 1.31.0 | MIT | `pip show` im Container |

Weitere Python-Pakete im Image (torch, transformers, easyocr, rapidocr, ray, pyarrow …) habe ich nicht einzeln auf Lizenzen geprüft: unverändertes Image, Nicht-Ziel.

Modelle im Image (`/opt/app-root/src/.cache/docling/models`, Größen aus `du`):

| Modell (Ordner, Dateien) | Zweck | Lizenz | Quelle | Bewertung |
| --- | --- | --- | --- | --- |
| `docling-project--docling-layout-heron` (model.safetensors, 164 MB) | Layout (wird beim Start geladen) | Apache-2.0 | README im Image (`license: apache-2.0`); https://huggingface.co/docling-project/docling-layout-heron | zugelassen |
| `docling-project--docling-layout-heron-onnx` (model.onnx, 164 MB) | Layout, ONNX-Fassung | Apache-2.0 | README im Image (`license: apache-2.0`) | zugelassen |
| `docling-project--docling-models` (model_artifacts/tableformer, 342 MB) | TableFormer (Tabellenstruktur) | **CDLA-Permissive-2.0** | README im Image (`license: cdla-permissive-2.0`); die HF-Seite https://huggingface.co/docling-project/docling-models zeigt die Kennzeichen `cdla-permissive-2.0` und `apache-2.0` ohne Zuordnung; Lizenztext https://cdla.dev/permissive-2-0/ | **nicht auf der Liste → Frage 1** |
| `docling-project--DocumentFigureClassifier-v2.5` (model.onnx, model.safetensors, 33 MB) | Bildklassifikation | MIT | README im Image (`license: mit`); https://huggingface.co/docling-project/DocumentFigureClassifier-v2.5 (Basis google/efficientnet-b0, deren Lizenz nicht geprüft) | zugelassen |
| `RapidOcr` (PP-OCRv6_det_small, PP-OCRv6_rec_small je .onnx und .pth, ch_ppocr_mobile_v2.0_cls_mobile, ppocrv6_dict.txt; 62 MB) | Texterkennung; vom Dienst automatisch gewählt (`Auto OCR model selected rapidocr with onnxruntime`) | Apache-2.0 | RapidOCR-README: Modelle „derived from official PaddleOCR models“, Apache-2.0 (https://github.com/RapidAI/RapidOCR); https://huggingface.co/PaddlePaddle/PP-OCRv6_small_det (Apache-2.0); PaddleOCR Apache-2.0 (https://github.com/PaddlePaddle/PaddleOCR). Die genannte Datei MODEL_LICENSES.md war nicht abrufbar (404); rec_small und cls nicht einzeln an einer Modellseite geprüft | zugelassen (Beleg teilweise mittelbar) |
| `EasyOcr` (craft_mlt_25k.pth, english_g2.pth, latin_g2.pth; 109 MB) | Texterkennung, nur wenn eine Anfrage `ocr_engine: easyocr` verlangt | **nicht feststellbar.** Code: EasyOCR Apache-2.0, CRAFT-pytorch MIT. Für die Gewichte nennen weder https://github.com/JaidedAI/EasyOCR noch https://github.com/clovaai/CRAFT-pytorch noch die Model-Hub-Seite https://www.jaided.ai/easyocr/modelhub/ eine Lizenz (dort nur der Seitenfuß „All rights reserved“) | | **→ Frage 2** |
| Tesseract `eng.traineddata`, `osd.traineddata` (Systempaket unter `/usr/share/tesseract/tessdata`) | Texterkennung, nur auf Anfrage | Apache-2.0 | https://github.com/tesseract-ocr/tessdata | zugelassen |

Keine Modelllizenz mit Nutzungsbeschränkung (nicht-kommerziell o. ä.) gefunden. CDLA-Permissive-2.0 schränkt den Einsatzbereich nicht ein; Abschnitt 3.1 legt der Nutzung von „Results“ (dazu zählen ausdrücklich Modelle) keine Pflichten auf. Sie steht aber nicht auf der Liste.

### Fragen an a7

**Frage 1 – TableFormer unter CDLA-Permissive-2.0.**
- (a) Als benannte Ausnahme zulassen, nur für das unverändert eingesetzte Image (wie ein Basis-Image). *Empfehlung:* Die Lizenz ist freizügig und ohne Einsatzbeschränkung, und ohne TableFormer gibt es keine Tabellenstruktur; Gerätelisten und Netzpläne sind oft Tabellen.
- (b) Nicht zulassen. Dann bräuchte es ein eigenes Image ohne das Modell, und Tabellenstruktur fiele weg.

**Frage 2 – EasyOCR-Gewichte ohne feststellbare Lizenz.**
- (a) Als Bestandteil des unveränderten Images hinnehmen, mit der Regel, dass das Backend nie `ocr_engine: easyocr` anfordert; der Dienst wählt von sich aus RapidOCR. *Empfehlung.*
- (b) Eigenes Image aus dem Containerfile von docling-serve bauen, mit `MODELS_LIST` ohne `easyocr`. Das ist ein eigener Bau und damit kein unverändertes Image mehr, und er muss gepflegt werden.
- (c) Auf die angekündigten schlanken Images ohne Modelle warten und die Modelle selbst auswählen (Zeitpunkt offen).

**Frage 3 – Telemetrie von ONNX Runtime.** Gefunden und mit `ORT_DISABLE_TELEMETRY=1` abgeschaltet (Messung siehe oben). Zu entscheiden:
- (a) Den Schalter als Maßnahme bestätigen und im Entscheidungsprotokoll festhalten. *Empfehlung.*
- (b) Zusätzlich `docling` in ein eigenes Netz mit `internal: true` legen und `api` und `worker` daran mit anhängen. Docling braucht keinen Weg nach außen, und das deckte auch künftige oder nicht gemessene Telemetrie ab. Das wäre ein eigener kleiner Auftrag (betrifft die Netze in `compose.yaml`, damit Architektur).

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a0c5c03a0a243c4a2`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a0c5c03a0a243c4a2` (relativ zum Projektordner)

### Abweichungen und Hinweise

- **Über den Wortlaut hinaus gesetzt:** `DOCLING_SERVE_OTEL_ENABLE_TRACES=false`, `DOCLING_SERVE_OTEL_ENABLE_OTLP_METRICS=false` (ohnehin Vorgabe), `DOCLING_SERVE_ENABLE_REMOTE_SERVICES=false`, `DOCLING_SERVE_ALLOW_EXTERNAL_PLUGINS=false` (ohnehin Vorgabe, laut `settings.py` im Image), `HF_HUB_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1` und `ORT_DISABLE_TELEMETRY=1` (Befund 3). Mit allen Schaltern laufen Start, Healthcheck und Umwandlung fehlerfrei.
- **Image per Tag und Digest** festgelegt. Das Tag `latest` zeigte am 21.11.2026 auf einen anderen Digest (`sha256:f8d3a401…`); ob es eine neuere Version als 1.38.2 gibt, habe ich nicht geprüft.
- **`check_docling` übernimmt Aufbau und Hilfsfunktionen von `check_llm`** (Auftrag 007) als Kopie. Eine gemeinsame Hilfsdatei hätte die App `answers` berührt; das liegt außerhalb des Auftrags. Kandidat für eine spätere Bereinigung.
- `check_docling` prüft Erreichbarkeit und Version, nicht die Bereitschaft (`/ready`). Lädt der Dienst noch, meldet der Befehl trotzdem `OK`, weil `/version` sofort antwortet. Das ist so verlangt; bei Bedarf ließe sich `/ready` ergänzen.
- Der Healthcheck protokolliert alle 15 s eine Zeile `GET /ready … 200` im Log von Docling.
- Container laufen als UID 1001 (Vorgabe des Images).
- Die Tests prüfen den Befehl nur gegen den Ersatzserver. Gegen den echten Dienst liefen die Kriterien 2, 3 und 5.
- Lokal liegen noch: das Image `quay.io/docling-project/docling-serve-cpu` (7.57 GB) und die Images `twox-009-backend-dev`, `-api`, `-worker`, `-migrate`. Die lokale `.env` (ignoriert) hat `TWOX_API_PORT=18009`.
- `docs/DECISIONS.md` und `docs/STATUS.md` sind nicht angefasst. Einträge fürs Entscheidungsprotokoll nach den Antworten auf die Fragen: Image docling-serve-cpu 1.38.2 (MIT, Tag und Digest wie oben), die Modell-Lizenzen aus der Tabelle, die Telemetrie-Schalter.
