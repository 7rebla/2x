# Auftrag 044 – Einbettungen über Ollama: Client und Prüfung

Meilenstein: M2 · Freigabestufe: C · Status: zur Prüfung

## Ziel

Das Backend berechnet Einbettungen lokal über die OpenAI-kompatible Schnittstelle von Ollama am Windows-Host (`host.docker.internal:11434`). Der Zugriff läuft über eine eigene Modell-Schnittstelle, damit der Anbieter austauschbar bleibt (Startunterlage 5.2, E-04). Standardmodell nach Frage 1: bge-m3 mit 1 024 Dimensionen. Cloud-Modelle werden abgewiesen, damit keine Handbuchtexte das Haus verlassen (Leitplanke 6).

## Umfang

- Neues Modul `backend/twox/answers/embeddings.py`:
  - Protokoll `Embedder` mit `model_name`, `dimensions`, `embed_documents(texts: Sequence[str]) -> list[list[float]]` und `embed_query(text: str) -> list[float]`.
  - Umsetzung `OpenAICompatibleEmbedder` mit `urllib` (wie `check_llm`): `POST {TWOX_LLM_BASE_URL}/embeddings` mit `model` und `input` als Liste; kein Feld `user`.
  - Stapelgröße nach Einstellung, Zeitlimit je Anfrage, Prüfung von Anzahl und Länge der Vektoren.
  - Optionaler Vorsatz für Anfragen (`TWOX_EMBED_QUERY_PREFIX`), leer bei bge-m3.
  - Fehlerarten: `EmbeddingUnavailableError` (keine Verbindung, Zeitüberschreitung, 5xx; neuer Versuch sinnvoll), `EmbeddingRejectedError` (4xx, z. B. Modell nicht geladen; Meldung nennt `ollama pull <modell>`), `EmbeddingDimensionError`, `EmbeddingRemoteModelError` (Modell ist als entfernt laufendes Cloud-Modell gekennzeichnet).
  - `get_embedder()` für Attrappen.
- Einstellungen in `backend/twox/config/settings.py`, je mit Vorgabe und Prüfung beim Start (ganze Zahlen größer 0): `TWOX_EMBED_MODEL` (`bge-m3`), `TWOX_EMBED_DIMENSIONS` (`1024`), `TWOX_EMBED_BATCH_SIZE` (`16`), `TWOX_EMBED_QUERY_PREFIX` (leer), `TWOX_EMBED_TIMEOUT_SECONDS`.
- Die Variablen in `x-backend-environment` (`deploy/compose/compose.yaml`) und `.env.example`.
- `check_llm` (`backend/twox/answers/management/commands/check_llm.py`) bekommt `--embed`: bettet einen festen kurzen Satz ein und meldet `OK:` mit Modell, Dimension und Laufzeit oder `FAILED:` mit Fehlerart (gleiches Präfix wie bisher). Zeigt `TWOX_LLM_BASE_URL` nicht auf `host.docker.internal`, `localhost`, `127.0.0.1` oder `::1`, gibt es zusätzlich eine Zeile `WARNING:` (ein vorhandener Modell-Dienst im eigenen Netz ist nach 5.2 erlaubt, deshalb nur Warnung). Ohne Option bleibt das Verhalten gleich.
- Tests (CI, ohne Ollama) mit einer Attrappe über `http.server` in einem Thread: Stapel, Reihenfolge, falsche Dimension, 404 für ein unbekanntes Modell, Verbindungsfehler, Zeitüberschreitung, Vorsatz nur bei Anfragen, kein Feld `user`, Cloud-Modell abgewiesen, Warnung bei entfernter Basisadresse.

## Nicht-Ziele

- Keine Celery-Aufgabe (048), kein Chat-Modell (M3).
- Kein Laden von Modellen durch Code (`ollama pull` ist Frage 2).
- Keine neue Abhängigkeit (weder `openai` noch `httpx`).

## Betroffene Bereiche (Ordner, Dateien)

- neu: `backend/twox/answers/embeddings.py`
- `backend/twox/answers/management/commands/check_llm.py`
- `backend/twox/config/settings.py` (neue `TWOX_EMBED_*`)
- `deploy/compose/compose.yaml` (nur `x-backend-environment`), `.env.example`
- neu: `backend/tests/answers/test_embeddings.py`; `backend/tests/answers/test_check_llm.py`; gegebenenfalls `backend/tests/config/test_settings.py`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-044`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18044` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Tests:
   - `D run --rm backend-dev pytest tests/answers tests/config -v` endet mit Exit-Code 0.
   - `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen.
   - `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
3. `D run --rm backend-dev ruff check .` meldet `All checks passed!`, `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0, `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
4. Weitere Prüfungen wie in `ci.yml`, jeweils ohne Unterschied zum eingecheckten Stand:
   - `D run --rm backend-dev python manage.py makemessages -l de --add-location=file`, danach `git diff --exit-code -I '^"POT-Creation-Date:' -- backend/locale`;
   - `D run --rm backend-dev python manage.py makemigrations --check --dry-run` endet mit Exit-Code 0;
   - `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0;
   - `D run --rm -v "$PWD/web/openapi:/out" backend-dev python manage.py spectacular --file /out/schema.yml` (unter Git Bash mit vorangestelltem `MSYS_NO_PATHCONV=1`), danach `git diff --exit-code -- web/openapi`.
5. Lokal, nicht in der CI: `D exec -T api python manage.py check_llm` meldet weiterhin `OK:`.
6. Lokal, nur wenn das Modell nach Frage 2 geladen ist: `D exec -T api python manage.py check_llm --embed` meldet `OK:` mit `bge-m3` und Dimension 1024; Laufzeit im Kurzbericht. Fehlt das Modell, meldet der Befehl `FAILED:` mit Hinweis auf `ollama pull`; dann bleibt nur dieses Kriterium mit „wartet auf a7“ offen.
7. Lokal: Der Kurzbericht enthält einen Vorschlag für die Zeile der Abhängigkeitstabelle in `docs/DECISIONS.md` für das Modell: Name, Ollama-Tag mit Digest (aus `GET /api/tags`), Größe, Lizenz mit Quelle (Model Card auf Hugging Face und die Lizenzangabe des Ollama-Manifests aus `POST /api/show`), Zweck. Beide Abfragen aus dem Container `api` mit `python -c` und `urllib` gegen `http://host.docker.internal:11434`. Eintragen tut die Leitstelle.
8. Abräumen: `D --profile dev down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

- **Nachtrag der Leitstelle (E-59, KI optional):** Einbettungen, Vektorsuche und alles, was ein Modell braucht, sind eine aktivierbare Zusatzfunktion. Schalter `TWOX_AI_ENABLED` (Einstellung in `settings.py`, Standard `False`; `.env.example` mit Kommentar). Bei „aus“: kein Aufruf von Ollama, keine Einbettungs-Aufgaben, Einlesen endet nach den Abschnitten erfolgreich, die Suche arbeitet nur mit der Stichwortsuche, Selbsttest und Oberfläche zeigen „KI nicht aktiviert“ als neutralen Zustand (kein Fehler, kein Warnsymbol). Jede KI-abhängige Stelle braucht einen Test für beide Zustände; die CI läuft mit „aus“ und mit „an“ plus Attrappe.

Voraussetzung: 040 und 041 sind nach `main` zusammengeführt (dieselben Dateien `settings.py` und `compose.yaml`). Frage 1 ist entschieden.

- Welle 2, parallel zu 042 und 043.
- **Keine neue Abhängigkeit**; `urllib` wie in `check_llm`. `TWOX_LLM_BASE_URL` endet schon auf `/v1`.
- Laut https://docs.ollama.com/api/openai-compatibility unterstützt `/v1/embeddings` `model`, `input` (Text oder Liste), `encoding_format` und `dimensions`; `user` nicht.
- Dass bge-m3 in Ollama 1 024 Werte liefert, zeigt die Ollama-Seite nicht; Kriterium 6 belegt es.
- Wie Ollama 0.40.17 Cloud-Modelle kennzeichnet (Namensendung `-cloud`/`:cloud` oder ein Feld in `/api/show`), ist ungeprüft; am laufenden Ollama prüfen, das Merkmal im Kurzbericht nennen und so prüfen.
- Betrieb ohne Internet: Der Client spricht nur `TWOX_LLM_BASE_URL` an. Keine Telemetrie.
- Die Dimension muss zur Spalte `vector(1024)` aus 042 passen; die Prüfung baut 048 ein.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

1. **Einbettungsmodell (Modell mit Lizenz).**
   - (a) bge-m3 (567M, MIT laut Model Card https://huggingface.co/BAAI/bge-m3, 1 024 Dimensionen, 8 192 Token, über 100 Sprachen; Ollama `bge-m3`, 1,2 GB).
   - (b) qwen3-embedding:0.6b (Apache-2.0 laut https://huggingface.co/Qwen/Qwen3-Embedding-0.6B, bis 1 024 Dimensionen, 32K Token, Anfragen brauchen eine Anweisung; Ollama etwa 0,64 GB).
   - (c) granite-embedding:278m (Apache-2.0 laut Hugging Face, 768 Dimensionen, 512 Token).
   Ausgeschlossen: embeddinggemma (Gemma-Nutzungsbedingungen mit Nutzungsbeschränkung, Leitplanke 7).
   Empfehlung: (a) als Standard (Startunterlage 5.5) mit fester Dimension 1024; (b) ist Herausforderer im Messlauf 057, gleiche Dimension, also ohne Migration wechselbar.
2. **Wer lädt die Modelle in Ollama?** `ollama pull bge-m3` und `ollama pull qwen3-embedding:0.6b` laden zusammen etwa 1,8 GB in den Modellordner von Ollama im Windows-Benutzerprofil, also außerhalb des Projektordners.
   - (a) a7 führt beide Befehle selbst aus.
   - (b) a7 erlaubt der Leitstelle diese beiden Befehle einmalig – als ausdrückliche Ausnahme von den Regeln „Nur im Projektordner arbeiten“ und „Nichts wird global installiert“, mit Eintrag im Entscheidungsprotokoll.
   Empfehlung: (b), damit die lokalen Prüfungen nicht warten; Ollama selbst hat a7 schon installiert, die Modelle sind dessen Nutzdaten. Die CI braucht kein Modell.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Läufe am 22.11.2026 im Container, Projekt `twox-044`, Port 18044, Docker Engine 29.9.3, Compose v5.7.0, Ollama 0.40.17 am Host. Alle Kriterien 0 bis 8 erfüllt. Keine neue Abhängigkeit, keine Migration, kein `ollama pull`, am Host nichts geändert.

### Was wurde gebaut?

- `backend/twox/answers/embeddings.py` (neu):
  - Protokoll `Embedder` (`model_name`, `dimensions`, `embed_documents`, `embed_query`) und `get_embedder()` (Tests ersetzen die Funktion durch eine Attrappe).
  - `OpenAICompatibleEmbedder`, nur `urllib`, ohne Proxy. `POST {TWOX_LLM_BASE_URL}/embeddings` mit genau `model` und `input` (immer eine Liste), kein `user`, kein `dimensions`.
  - Stapel nach `TWOX_EMBED_BATCH_SIZE`; Socket-Zeitlimit je Anfrage `TWOX_EMBED_TIMEOUT_SECONDS`; Antwort höchstens 64 MiB.
  - Prüfung der Antwort: Anzahl gleich Anzahl der Texte; Reihenfolge nach `index` (nicht nach Position); jeder Vektor eine Liste endlicher Zahlen (kein `bool`); Länge gleich `TWOX_EMBED_DIMENSIONS`.
  - `TWOX_EMBED_QUERY_PREFIX` nur in `embed_query`.
  - Fehlerarten, alle mit Basis `EmbeddingError`, Meldungen ohne Adresse und ohne Text, Ursache als `__cause__`:
    - `EmbeddingUnavailableError`: Verbindung abgelehnt, Zeitlimit, Netzfehler, HTTP 5xx, unbrauchbare Antwort.
    - `EmbeddingRejectedError`: HTTP 4xx; bei 404 und bei fehlendem Modell in der Modellliste mit `load it with: ollama pull <modell>`.
    - `EmbeddingDimensionError`, `EmbeddingRemoteModelError`.
    - zusätzlich `EmbeddingDisabledError` (E-59, siehe Abweichung 1).
  - Cloud-Modelle (siehe „Merkmal“ unten): einmal je Embedder vor der ersten Anfrage. Erst der Name (ohne Netz), dann `GET /api/tags` (Basisadresse ohne `/v1`). Das Modell muss dort stehen (`bge-m3` passt auf `bge-m3:latest`), und der Eintrag darf kein `remote_host` oder `remote_model` tragen. Antwortet `/api/tags` mit einem anderen Status als 200 (kein Ollama, sondern ein anderer OpenAI-kompatibler Dienst im eigenen Netz), bleibt es bei der Namensprüfung (Protokollzeile INFO).
- `backend/twox/config/settings.py`: `TWOX_AI_ENABLED` (`env_bool`, Standard `False`), `TWOX_EMBED_MODEL` (`bge-m3`), `TWOX_EMBED_DIMENSIONS` (1024), `TWOX_EMBED_BATCH_SIZE` (16), `TWOX_EMBED_QUERY_PREFIX` (leer, unverändert übernommen, Leerzeichen am Ende bleiben), `TWOX_EMBED_TIMEOUT_SECONDS` (120). Die drei Zahlen über `env_positive_int`; falsche Werte brechen den Start ab.
- `deploy/compose/compose.yaml`: die sechs Variablen in `x-backend-environment`.
- `.env.example`: die sechs Variablen mit Kommentar; `TWOX_AI_ENABLED=true`, weil E-59 die Entwicklungsvorlage ausdrücklich auf „an“ stellt. Ohne den Eintrag gilt „aus“.
- `check_llm`:
  - Neue Option `--embed`: bettet den festen Satz „Check the oil level of the pump every 500 operating hours.“ ein. Ausgabe `OK: embedded a test sentence with <modell> at <adresse>/embeddings: <n> dimensions in <x>s` oder `FAILED: <Fehlerart>: <Meldung>`, Exit-Code 0 bzw. 1. Ohne Erreichbarkeitsschritte; die Anfrage selbst belegt die Erreichbarkeit.
  - Mit `--embed` steht vorher eine Zeile `WARNING: …`, wenn der Host von `TWOX_LLM_BASE_URL` nicht `host.docker.internal`, `localhost`, `127.0.0.1` oder `::1` ist (Groß-/Kleinschreibung egal).
  - KI aus: mit und ohne `--embed` genau eine Zeile `DISABLED: AI features are not enabled (TWOX_AI_ENABLED is false); the model service was not contacted`, Exit-Code 0, keine Namensauflösung, keine Verbindung.
  - Ohne Option und mit KI an: unverändert.
- Tests:
  - `backend/tests/answers/fake_ollama.py` (neu): Attrappe auf `http.server` in einem Thread, bildet `GET /api/tags` und `POST /v1/embeddings` wie Ollama 0.40.17 nach, auch 404 `not_found_error`.
  - `backend/tests/answers/test_embeddings.py` (neu, 55 Fälle): Stapel 3+3+1 in Reihenfolge; Reihenfolge nach `index`; nur `model` und `input`, `input` immer Liste; Vorsatz nur bei Anfragen; Zahlen als `float`; leere Liste ohne Anfrage; nur Zeichenketten; Modellliste einmal je Embedder; `bge-m3` = `bge-m3:latest`; Cloud-Namen abgewiesen ohne jede Anfrage; Cloud-Eintrag mit `remote_host`/`remote_model` abgewiesen ohne Einbettungsanfrage; fehlendes Modell → Rejected mit `ollama pull bge-m3`; Dienst ohne Modellliste; unbrauchbare Modellliste; 404, 400, 500/502/503; falsche Dimension; falsche Anzahl; doppelter oder falscher Index, Zeichenkette, `bool`, kein Objekt, `NaN`; abgelehnte Verbindung (ohne Adresse in der Meldung); Zeitüberschreitung an einem stummen Port (0,3 s) und nach der Modellprüfung; ungültige Konstruktion; `get_embedder()` aus den Einstellungen; Attrappe statt `get_embedder()`; KI aus: `get_embedder()` und beide Methoden ohne Anfrage, auch für einen schon benutzten Embedder.
  - `backend/tests/answers/test_check_llm.py`: die 15 bisherigen Fälle laufen mit KI an (Fixture), dazu 22 neue: `DISABLED:` mit und ohne `--embed` (Netz gesperrt, keine Anfrage); `--embed` mit `OK:` (nur `/api/tags` und eine Einbettung); `FAILED:` je Fehlerart; Hinweis `ollama pull`; Cloud-Modell; abgelehnte Verbindung; Zeitüberschreitung; ungültige Adresse; `WARNING:` bei Basisadresse `127.0.0.2` (echte Anfrage an die Attrappe, kein DNS); keine Warnung für die vier lokalen Namen; Warnung für andere; ohne `--embed` keine Einbettung.
  - `backend/tests/config/test_settings.py`: Vorgaben (KI aus, bge-m3, 1024, 16, leer, 120), Übernahme aus der Umgebung, ungültige Zahlen für die drei Zahlenwerte, Wahrheitswerte und ungültiger Wert für `TWOX_AI_ENABLED`.

### Wie wurde getestet?

`D` = `docker compose -p twox-044`, `.env` aus `.env.example` (ohne BOM) mit `TWOX_API_PORT=18044`. Kriterien 1 bis 6 auf dem committeten Code-Stand (Images danach neu gebaut).

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | Engine 29.9.3, Compose v5.7.0, Exit 0 |
| 1 | erfüllt | Bau Exit 0; `up -d --wait …` Exit 0, db, valkey, api, worker Healthy |
| 2 | erfüllt | `pytest tests/answers tests/config -v`: `315 passed, 4 deselected`; `pytest`: `1342 passed, 4 deselected`, nichts übersprungen; `pytest -m worker`: `4 passed, 1342 deselected` |
| 3 | erfüllt | `All checks passed!`; `144 files already formatted`; `Success: no issues found in 143 source files` |
| 4 | erfüllt | `makemessages` ohne Unterschied in `backend/locale`; `No changes detected`; `License check passed.`; `spectacular` ohne Unterschied in `web/openapi` |
| 5 | erfüllt | `OK: http://host.docker.internal:11434/v1/models is reachable, 2 model(s) reported` |
| 6 | erfüllt | `OK: embedded a test sentence with bge-m3 at http://host.docker.internal:11434/v1/embeddings: 1024 dimensions in 3.56s` (erster Aufruf, Modell wird geladen); zweiter Aufruf `… in 0.06s` |
| 7 | erfüllt | Abfragen mit `python -c` und `urllib` aus `api`, Werte unten |
| 8 | erfüllt | `D --profile dev down -v` Exit 0; keine Container und Volumes `twox-044*` mehr. „2x“ und „twox-leit“ nicht angefasst |

Zusätzlich gegen das echte Ollama (Umgebungsvariable nur für den einen Aufruf mit `exec -e`):

- `TWOX_EMBED_MODEL=qwen3-embedding:0.6b`: `OK: … 1024 dimensions in 2.92s`.
- `TWOX_EMBED_MODEL=nomic-embed-text` (nicht geladen): `FAILED: EmbeddingRejectedError: model 'nomic-embed-text' is not loaded in Ollama; load it with: ollama pull nomic-embed-text`, Exit 1.
- `TWOX_EMBED_MODEL=gpt-oss:20b-cloud`: `FAILED: EmbeddingRemoteModelError: model 'gpt-oss:20b-cloud' is an Ollama cloud model; only local models are allowed`, Exit 1.
- `TWOX_AI_ENABLED=false`, mit und ohne `--embed`: `DISABLED: …`, Exit 0.

Beobachtungen am Ollama 0.40.17 (direkt, vor dem Bau des Clients):

- `/v1/embeddings` liefert `object`, `data` (je `object`, `embedding`, `index`), `model` und `usage`.
- Unbekanntes Modell: 404 `{"error":{"message":"model '…' not found","type":"not_found_error",…}}`.
- Ein Feld `user` wird ohne Fehler angenommen (der Client schickt es trotzdem nicht).
- Ein leerer Text liefert einen Vektor.

**Verhalten bei KI aus/an:**

- **Aus:** Kein Code dieses Auftrags spricht Ollama an. `get_embedder()` und jede Anfrage des Embedders werfen vorher `EmbeddingDisabledError`; die Prüfung steht in der einen Methode, die Anfragen sendet, wirkt also auch bei einem Embedder, der vor dem Umschalten gebaut wurde. `check_llm` meldet `DISABLED:` (neutral, Exit 0).
- **An:** wie oben beschrieben.
- Selbsttest (`/api/v1/selftest/`) und Testseite sprechen Ollama nicht an und sind unverändert. Ihre Tests liefen grün in beiden Gesamtläufen. Den Browser-Test (e2e) habe ich nicht laufen lassen, weil weder Selbsttest noch Oberfläche geändert sind.
- In der CI kommt `.env` aus `.env.example`, der Dienst läuft also mit KI an, ohne Ollama. Die Tests stellen jeden Zustand selbst ein und prüfen beide (mit Attrappe für „an“).

### Merkmal für Cloud-Modelle in Ollama 0.40.17 (am laufenden Ollama geprüft)

- **Name:** Cloud-Modelle heißen `<name>:<größe>-cloud` oder `<name>:cloud`. Geprüft wird nur der Teil nach dem letzten `:` (bzw. der ganze Name ohne `:`), ohne Groß-/Kleinschreibung.
- **`POST /api/show` taugt nicht als Merkmal:** Für das nie geladene `gpt-oss:20b-cloud` antwortete Ollama mit HTTP 200 und den Schlüsseln `capabilities`, `details`, `model_info`, `modified_at`, `thinking`, ohne `remote_host`/`remote_model`. Diese Angaben kann Ollama nur bei ollama.com geholt haben; die Abfrage löst also vermutlich eine Verbindung des Hosts ins Internet aus. Ich habe sie zweimal gestellt (einmal zur Prüfung des Merkmals, einmal zur Ansicht der Schlüssel). Der Client fragt `/api/show` deshalb nie.
- **`GET /api/tags`** listet nur, was auf dem Rechner liegt (hier `bge-m3:latest` und `qwen3-embedding:0.6b`, beide ohne `remote_*`). Dass ein hinzugefügtes Cloud-Modell dort `remote_host`/`remote_model` trägt, weiß ich aus dem Ollama-Quelltext (`api/types.go`); in dieser Sitzung habe ich das nicht nachgelesen. Am laufenden Ollama ist es nicht nachgestellt, weil kein Cloud-Modell geladen werden durfte. Die Prüfung ist aber auch ohne dieses Feld sicher: Ein Modell, das nicht in der Liste steht, wird gar nicht angefragt.

### Vorschlag für die Abhängigkeitstabelle in `docs/DECISIONS.md`

Werte aus `GET /api/tags` und `POST /api/show` (aus `api`, `python -c`, `urllib`) sowie den Model Cards (am 22.11.2026 abgerufen):

| Abhängigkeit | Lizenz | Zweck | Auftrag | Entscheidung |
| --- | --- | --- | --- | --- |
| Einbettungsmodell bge-m3 (BAAI), Ollama `bge-m3:latest`, Digest `7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab`, 1 157 672 605 Bytes (GGUF, F16, 566,70M Parameter, 1024 Dimensionen, Kontext 8192), lokal in Ollama am Host, nicht im Repository | MIT laut Model Card https://huggingface.co/BAAI/bge-m3 (Feld `license: mit`); Ollama-Manifest (`/api/show`, Feld `license`): MIT-Lizenztext, 1 068 Zeichen, mit Platzhalter „Copyright (c) [year] [fullname]“ | Standard-Einbettungsmodell für Abschnitte und Suchanfragen (Vektorsuche), nur bei `TWOX_AI_ENABLED` | 044 | E-56 |
| Einbettungsmodell Qwen3-Embedding-0.6B, Ollama `qwen3-embedding:0.6b`, Digest `ac6da0dfba84a81fdbfbaf330198c33cd77c4cdfc53e8bc50eb581914a15621d`, 639 150 858 Bytes (GGUF, Q8_0, 595,78M Parameter, 1024 Dimensionen, Kontext 32768), lokal in Ollama am Host | Apache-2.0 laut Model Card https://huggingface.co/Qwen/Qwen3-Embedding-0.6B (Feld `license: apache-2.0`); das Ollama-Manifest hat **kein** Feld `license` | nur Vergleich im Messlauf 057 | 044 | E-56 |

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-af16af1d90b588722`
- Arbeitsverzeichnis: `.claude/worktrees/agent-af16af1d90b588722` (relativ zum Projektordner)
- Commits: `Add the AI switch and the embedding settings (E-56, E-59)`, `Add the embedding client for an OpenAI-compatible model service`, `Let check_llm embed a test sentence with --embed`, dazu dieser Kurzbericht. Nicht gepusht, nichts zusammengeführt.

### Abweichungen und Hinweise

1. **Fünfte Fehlerart `EmbeddingDisabledError`** für E-59. So können 048 und die Suche „KI aus“ von einem Fehler unterscheiden.
2. **Unbrauchbare Antworten** (falsche Anzahl, kein JSON, falscher Index, keine Zahlen) ergeben wie in 041 `EmbeddingUnavailableError` („unexpected answer …“), keine eigene Fehlerart. Nur die falsche Vektorlänge ist `EmbeddingDimensionError`.
3. **Cloud-Prüfung über `/api/tags` statt `/api/show`.** Begründung unter „Merkmal“. Folge: Ein Modell, das nicht in der lokalen Liste steht, wird schon vor der Einbettung als `EmbeddingRejectedError` mit `ollama pull` gemeldet.
4. **Neue Ausgabe `DISABLED:` in `check_llm`** (dritter Präfix neben `OK:`/`FAILED:`, Exit 0). Ich wollte den neutralen Zustand weder als `OK:` noch als `FAILED:` ausgeben, weil ein Skript sonst falsch schließen kann.
5. **`--timeout` gilt nicht für `--embed`**; dort gilt `TWOX_EMBED_TIMEOUT_SECONDS`, wie im Hilfetext beschrieben. Vorgabe 120 s, weil der erste Aufruf nach dem Start von Ollama das Modell lädt (gemessen 3,6 s für bge-m3, auf langsameren Rechnern mehr).
6. **Zusätzliche Datei `backend/tests/answers/fake_ollama.py`** (wie `fake_docling.py` in 041), von beiden Testdateien benutzt.
7. **Selbsttest und Oberfläche nicht geändert.** E-59 verlangt „KI nicht aktiviert“ im Selbsttest und in der Oberfläche. Der Selbsttest hat heute keinen KI-Teil, und `web/` ist für 071/072 gesperrt. Vorschlag: Ein Folgeauftrag (z. B. mit 048) ergänzt `/api/v1/selftest/` um einen Teil `ai` (`enabled`, `ok`, `model`, `dimensions`, `error`) und die Testseite um eine neutrale Karte.
8. **Doku nicht nachgezogen:** README (Abschnitt `check_llm`) und `docs/ARCHITECTURE.md` (Variablentabelle) nennen `--embed`, `DISABLED:` und die neuen Variablen noch nicht. Beide Dateien stehen nicht im Auftrag; wie in 041 vorgesehen, gehört das zu 059.
9. **Zwei `/api/show`-Abfragen mit einem Cloud-Namen** lösten vermutlich je eine Verbindung von Ollama zu ollama.com aus (siehe „Merkmal“). Dabei wurde kein Text eingebettet und nichts aus dem Projekt gesendet, nur der Modellname.
10. Lokal liegen noch die Images `twox-044-api`, `-worker`, `-migrate`, `-backend-dev`; die ignorierte `.env` hat `TWOX_API_PORT=18044`.

Keine offene Frage, die den Auftrag aufhält. Zur Entscheidung durch a7 bzw. die Leitstelle: Punkt 7 (Folgeauftrag Selbsttest/Oberfläche) und Punkt 4 (Präfix `DISABLED:`).
