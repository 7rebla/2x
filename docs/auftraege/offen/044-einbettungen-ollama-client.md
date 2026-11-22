# Auftrag 044 – Einbettungen über Ollama: Client und Prüfung

Meilenstein: M2 · Freigabestufe: C · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
