# Auftrag 121 – Schnittstelle Sprachmodell

Meilenstein: M3 · Freigabestufe: B · Status: erledigt

## Ziel

Das Chat-Modell für die Auskunft (M3) ist nur über eine austauschbare Schnittstelle erreichbar (E-04, `docs/DECISIONS.md:14`; Arbeitsregel „Schnittstellen vor Umsetzung“). Für diese Schnittstelle gelten dieselben Schutzregeln wie für den Einbettungs-Client aus 044:

- Bei ausgeschalteter KI wird keine Verbindung aufgebaut (E-59, `docs/DECISIONS.md:69`).
- Cloud-Modelle werden abgewiesen, kein Text verlässt das Haus (Leitplanke 6).
- Fehlermeldungen sind kurz und nennen weder Adressen noch Prompttexte.

Heute gibt es keinen Chat-Client. `backend/twox/answers/` enthält nur `embeddings.py` und den Befehl `check_llm` (`docs/ARCHITECTURE.md:134`). Dieser Auftrag liefert den Client, die gemeinsame Cloud-Sperre, die Einstellungen und eine Attrappe für Tests. Damit können 125, 126, 129 und 135 auf einer festen Schnittstelle aufbauen, ohne ein echtes Modell zu brauchen.

## Umfang

### 1. Gemeinsame Cloud-Sperre `backend/twox/answers/llm_guard.py` (neu)

Die Prüfung „nur lokale Modelle“ wandert aus `embeddings.py` in ein eigenes Modul, das Einbettung und Chat gemeinsam nutzen:

- `is_cloud_model_name(model: str) -> bool` (heute `embeddings.py:120-124`).
- `ollama_root(base_url: str) -> str` und `full_model_name(model: str) -> str` (heute `embeddings.py:127-137`, dort mit Unterstrich).
- Konstante `TAGS_PATH = "/api/tags"` (heute `embeddings.py:62`).
- Eine reine Funktion, die die Antwort von `GET /api/tags` auswertet und den Eintrag des Modells findet. Vorschlag: `find_local_model(body: bytes, model: str) -> Mapping[str, object]`. Sie meldet die drei Fälle wie heute `embeddings.py:266-290`: unlesbare Liste, Modell nicht geladen, Modell läuft entfernt (`remote_host`/`remote_model`).
  - Die Funktion wirft eigene, neutrale Ausnahmen aus `llm_guard` (z. B. `ModelListError`, `ModelNotLoadedError`, `RemoteModelError`).
  - Embedder und Chat übersetzen sie in ihre eigenen Fehlerklassen.
  - Die Meldungen bleiben inhaltlich wie heute, einschließlich des Hinweises `ollama pull <modell>` (`embeddings.py:287-290`).
- Optional: eine kleine gemeinsame Hilfsfunktion `is_timeout(error)` (heute doppelt in `embeddings.py:140-144` und `check_llm.py:66-70`). `check_llm.py` wird in diesem Auftrag aber **nicht** geändert, das macht 129.

### 2. Umstellung `backend/twox/answers/embeddings.py`

- `embeddings.py` nutzt `llm_guard` und verhält sich **unverändert**: gleiche Fehlerklassen, gleiche Meldungen, gleiche Reihenfolge der Anfragen.
- `is_cloud_model_name` bleibt aus `twox.answers.embeddings` importierbar (Re-Export), weil `backend/tests/answers/test_embeddings.py:13-23` es von dort importiert.
- Die Zeitlogik des Query-Embedders bleibt in `embeddings.py` und nutzt weiter den Modulnamen `monotonic`: `backend/tests/search/test_vector_search.py:350` ersetzt `embeddings.monotonic` per `monkeypatch`.
- Kein bestehender Test wird geändert. Kriterium 6 prüft das.

### 3. Chat-Client `backend/twox/answers/chat.py` (neu)

Typen und Protokoll:

- `ChatMessage` als `TypedDict` mit `role: Literal["system", "user", "assistant"]` und `content: str`. `chat.py` ist das einzige Modul, das diesen Typ festlegt, und importiert nichts aus `prompt.py` oder `types.py`. Vorgabe zur Abstimmung mit 122 siehe „Vorgaben und Hinweise“.
- Protokoll `ChatModel`:
  - Eigenschaft `model_name -> str`
  - `stream(messages: Sequence[ChatMessage], *, max_tokens: int | None = None, temperature: float | None = None, seed: int | None = None) -> Iterator[str]`. `None` bedeutet: Wert aus den Einstellungen.
  - `close() -> None`. Bricht einen laufenden Strom ab und schließt die HTTP-Antwort. Mehrfacher Aufruf ist harmlos.
- `get_chat_model() -> ChatModel` ist der einzige Zugang. Tests ersetzen diese Funktion wie `get_embedder` (`embeddings.py:379-385`). Bei KI aus wirft sie `ChatDisabledError`, bevor irgendetwas aufgebaut wird. Ist `TWOX_CHAT_MODEL` leer, wirft sie einen eigenen, klaren Fehler, z. B. `ChatUnavailableError("no chat model configured (TWOX_CHAT_MODEL is empty)")`.

Fehlerklassen, analog zu `embeddings.py:74-100`:

- `ChatError` (Basis)
- `ChatDisabledError`
- `ChatUnavailableError`: keine Verbindung, Zeitgrenze, HTTP 5xx, unbrauchbare Antwort oder Abbruch mitten im Strom
- `ChatRejectedError`: HTTP 4xx, Modell nicht geladen, Modell ohne Fähigkeit `completion`
- `ChatRemoteModelError`

Der ursprüngliche Fehler hängt jeweils an `__cause__`.

`OpenAICompatibleChat`:

- Der Konstruktor prüft seine Werte wie `embeddings.py:155-189`: `base_url` mit Schema und Host, Modell nicht leer, positive Zeitgrenze, `max_tokens >= 1`, `0 <= temperature <= 2`.
- `from_settings()` baut den Client aus den Einstellungen.
- Die Anfrage geht als `POST {TWOX_LLM_BASE_URL}/chat/completions` mit JSON `{"model", "messages", "stream": true, "max_tokens", "temperature"}`.
  - `seed` wird nur mitgeschickt, wenn er gesetzt ist.
  - `reasoning_effort` wird mitgeschickt, außer die Einstellung ist `omit` (siehe Einstellungen).
  - Kein Feld `user`, keine `tools`, kein `response_format`.
- Transport: `urllib` mit `ProxyHandler({})` wie `embeddings.py:188-189`. Kein `httpx`, kein `openai`.
- Der Strom wird zeilenweise gelesen:
  - Zeilen, die mit `data:` beginnen, werden einzeln als JSON gelesen; aus `choices[0].delta.content` kommt das Textstück, leere Stücke werden übersprungen.
  - Leerzeilen und Kommentarzeilen (`:`) werden ignoriert.
  - `data: [DONE]` beendet den Strom.
  - Ein `error`-Objekt im Strom ergibt `ChatUnavailableError`, ohne dessen Text weiterzugeben.
  - Endet die Verbindung ohne `[DONE]` und ohne `finish_reason`, ergibt das ebenfalls `ChatUnavailableError`.
  - Die Gesamtgröße ist begrenzt, ähnlich `MAX_ANSWER_BYTES` in `embeddings.py:65`. Eine zu lange Zeile ergibt einen Fehler.
- `TWOX_CHAT_TIMEOUT_SECONDS` ist die Socket-Zeitgrenze der Verbindung und damit die Lesegrenze zwischen zwei Stücken. Eine Gesamtzeit gibt es hier nicht, die regelt später der Dienst.
- `stream()` ist ein Generator. Wird er vorzeitig geschlossen (`generator.close()`, `GeneratorExit`) oder ruft jemand `close()` auf, schließt der Client die HTTP-Antwort sofort.
- Vor der ersten Anfrage gilt die Cloud-Sperre über `llm_guard`, wie `embeddings.py:241-264`:
  - Der Modellname wird bei jeder Anfrage geprüft.
  - Die Modellliste `/api/tags` wird einmal je Client geprüft.
  - Antwortet `/api/tags` nicht mit 200 (anderer OpenAI-kompatibler Server), wird nur der Name geprüft und das als `info` protokolliert, wie `embeddings.py:260-263`.
- **Fähigkeit `completion`:** Der Chat prüft zusätzlich, dass das Modell Text erzeugen kann. Ein Einbettungsmodell wie `bge-m3` wird mit `ChatRejectedError` abgewiesen. Der Weg dorthin steht unter „Vorgaben und Hinweise“, Punkt „Fähigkeit completion“.
- Protokolliert werden nur Fehlerart, Modellname und Dauer, nie Nachrichten, Prompt oder Antworttext.

`FakeChatModel` (in `chat.py`, damit 125, 126, 127 und 135 es ohne Testpaket nutzen können):

- Liefert vorgegebene Textstücke.
- Zeichnet die erhaltenen `messages` und Parameter auf.
- Kann nach n Stücken einen vorgegebenen `ChatError` werfen.
- Zählt `close()`.
- Kann so eingestellt werden, dass schon der Aufruf von `stream()` fehlschlägt. Das braucht 126, Kriterium 4.
- Keine Netzverbindung.

### 4. Einstellungen

`backend/twox/config/settings.py` bekommt einen neuen Block direkt nach `TWOX_SEARCH_EMBED_TIMEOUT_SECONDS` (Z. 446, vor `CELERY_TASK_QUEUES` Z. 448). Er enthält nur `TWOX_CHAT_*` und eine Hilfsfunktion für Kommazahlen:

| Variable | Bedeutung | Standard |
| --- | --- | --- |
| `TWOX_CHAT_MODEL` | Chat-Modell in Ollama | leer (kein Standard bis D1 in 128) |
| `TWOX_CHAT_TIMEOUT_SECONDS` | Lesegrenze zwischen zwei Stücken, auch für das erste Stück (Laden des Modells) | `120` |
| `TWOX_CHAT_MAX_TOKENS` | Höchstzahl erzeugter Tokens je Antwort | `1024` |
| `TWOX_CHAT_TEMPERATURE` | Temperatur, `0` bis `2` | `0` |
| `TWOX_CHAT_REASONING_EFFORT` | Wert für `reasoning_effort`: `none`, `low`, `medium` oder `high`; `omit` bedeutet, das Feld wird nicht gesendet; leer oder nicht gesetzt bedeutet Standard | `none` |

- `TWOX_CHAT_MODEL` wird mit `os.environ.get(..., "").strip()` gelesen, nicht mit `env_str`. Dessen Rückfall auf den Standard (`settings.py:20-25`) würde bei `None` mit `ImproperlyConfigured` abbrechen.
- Zahlen mit `env_positive_int` (`settings.py:45-58`).
- Für die Temperatur eine neue Funktion `env_float(name, default, *, minimum, maximum)` neben den anderen `env_*`, mit derselben Art von Fehlermeldung.
- Ein ungültiger `TWOX_CHAT_REASONING_EFFORT` ergibt `ImproperlyConfigured`.
- Leer und nicht gesetzt müssen dasselbe bedeuten: Die Compose-Zeile `${TWOX_CHAT_REASONING_EFFORT:-}` liefert einen leeren String, wenn die Variable in einer bestehenden `.env` fehlt (`compose.yaml:4-34`, alle Zeilen nach diesem Muster). Deshalb ist leer der Standard `none` und nicht „Feld weglassen“; dafür gibt es den eigenen Wert `omit`.

Weitere Dateien:

- `deploy/compose/compose.yaml`: im Block `x-backend-environment` (Z. 4-34) nach Z. 23 je eine Zeile `TWOX_CHAT_*: ${TWOX_CHAT_*:-}`.
- `.env.example`: nach Z. 48 ein kommentierter Block.
  - `TWOX_CHAT_MODEL=` bleibt leer, mit dem Hinweis, dass das Modell nach dem Messlauf 128 festgelegt und mit `ollama pull` geladen wird.
  - Dazu die übrigen Variablen mit ihren Standardwerten; bei `TWOX_CHAT_REASONING_EFFORT` mit dem Hinweis auf `omit`.
  - Keine Modellnamen als Empfehlung, solange D1 offen ist.

### 5. Systemprüfung `backend/twox/answers/checks.py` (neu)

- Registriert in `AnswersConfig.ready()` in `backend/twox/answers/apps.py`, nach dem Muster `backend/twox/ingest/apps.py:10-15` und `backend/twox/ingest/checks.py`.
- Ist die KI an und `TWOX_CHAT_MODEL` leer, gibt es **eine Warnung** `twox.answers.W001` mit Hinweis, z. B. „Set TWOX_CHAT_MODEL to a local chat model loaded in Ollama; answers stay unavailable until then.“ Ein Fehler ist das nicht: Testumgebung und CI starten mit `.env.example` (KI an, Modell leer) und sollen das weiter tun.
- Bei KI aus gibt es keine Meldung.
- Ein Modellname, der wie ein Cloud-Modell aussieht, ist bei KI an ein **Fehler** `twox.answers.E001`. Das braucht keine Verbindung, nur `is_cloud_model_name`.
- Die Prüfung baut keine Verbindung auf.

### 6. Tests `backend/tests/answers/test_chat.py` (neu), `backend/tests/answers/test_llm_guard.py` (neu)

- Alle Tests laufen mit lokalem Fake-HTTP-Server, ohne echtes Modell.
- `backend/tests/answers/fake_ollama.py` wird **additiv** erweitert:
  - Route `POST /v1/chat/completions`, die vorgegebene SSE-Zeilen sendet. Einstellbar sind Stücke, Leerzeilen, Kommentarzeilen, `[DONE]` ja/nein, Abbruch mitten im Strom, HTTP-Status, Pause vor einem Stück und Fehlerobjekt.
  - Modelleinträge mit `capabilities`.
  - Gegebenenfalls `POST /api/show`.
  - Bestehende Felder und Standardwerte bleiben, damit die Embedder-Tests unverändert grün sind.
- Beide KI-Zustände werden getestet (E-59).
- Für „keine Verbindung“ ersetzt ein Test `socket.socket.connect` bzw. `socket.create_connection` per `monkeypatch` durch eine Funktion, die fehlschlägt. Muster: `backend/tests/answers/test_check_llm.py:170`.
- Die Testtexte sind selbst geschrieben, kein Handbuchtext.

### 7. Dokumentation

`docs/ARCHITECTURE.md`:

- Z. 134, Zeile `answers` der App-Tabelle, wird **nicht** geändert. Diese Zeile wollen auch 122 (parallel) und später 125, 126, 127 und 130 ergänzen; sie pflegt allein die Leitstelle beim Zusammenführen. Der Kurzbericht nennt die Stichworte dafür (`chat.py`, Protokoll `ChatModel`, `get_chat_model`, `FakeChatModel`, `llm_guard.py`).
- Konfigurationstabelle Z. 539-547: Zeile `TWOX_LLM_BASE_URL` um „chat“ ergänzen, `TWOX_AI_ENABLED` um „answers“, neue Zeilen für alle `TWOX_CHAT_*`.
- Satz Z. 559 um die neuen Zahlen ergänzen.
- Ein kurzer Absatz zur Cloud-Sperre und zur Fähigkeitsprüfung des Chats, dort, wo die Tabelle auf `embeddings.py` verweist. Kein eigener Abschnitt zu Prompt oder Ereignissen, das macht 122.

## Nicht-Ziele

- Kein Prompt, keine Antworttypen, keine Ereignisse (122). Keine Zitatprüfung (123), keine Kontextauswahl (125), kein Antwortdienst und kein Befehl `ask` (126).
- Keine Änderung an `check_llm.py`, `config/selftest.py`, Selbsttest-Seite oder README (129).
- Keine API, kein SSE-Endpunkt, keine Oberfläche (130–134).
- Kein `ollama pull`, keine Modellwahl, kein Standardwert für `TWOX_CHAT_MODEL`, keine Änderung an Ollama oder am Host (D1, 128).
- Keine Aufzeichnung oder Wiedergabe für die CI (`ReplayChatModel`, 135).
- Keine Änderung unter `backend/twox/search/`, an `ingest/` oder an der Datenbank. Keine Migration.
- Keine neue Abhängigkeit, auch nicht für Tests.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle.

## Betroffene Bereiche (Ordner, Dateien)

- neu: `backend/twox/answers/chat.py`, `backend/twox/answers/llm_guard.py`, `backend/twox/answers/checks.py`
- geändert: `backend/twox/answers/embeddings.py` (nur Umstellung auf `llm_guard`, Verhalten gleich), `backend/twox/answers/apps.py` (`ready()` registriert die Prüfung)
- geändert: `backend/twox/config/settings.py` (nur `env_float` und der Block `TWOX_CHAT_*` nach Z. 446)
- geändert: `deploy/compose/compose.yaml` (nur `x-backend-environment`, Z. 4-34), `.env.example` (nur neuer Block `TWOX_CHAT_*`)
- neu: `backend/tests/answers/test_chat.py`, `backend/tests/answers/test_llm_guard.py`, `backend/tests/answers/test_checks.py`
- geändert (additiv): `backend/tests/answers/fake_ollama.py`
- geändert: `docs/ARCHITECTURE.md` (Konfigurationstabelle Z. 539-547 und Z. 559, kurzer Absatz zum Chat-Client; nicht Z. 134)

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-121`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18121` setzen. Die KI ist damit an, `TWOX_CHAT_MODEL` ist leer.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0. Die Dienste starten also auch mit KI an und leerem `TWOX_CHAT_MODEL`.
2. Tests des Chat-Clients mit dem Fake-HTTP-Server, ohne echtes Modell, je mit eigenem Test:
   1. Der Strom liefert die Textstücke in der richtigen Reihenfolge, auch mit `data: [DONE]`, Leerzeilen, Kommentarzeilen und Stücken mit leerem `content`. Nach `[DONE]` wird nichts mehr gelesen.
   2. Die Anfrage enthält `model`, `messages`, `stream: true`, `max_tokens`, `temperature`. `seed` erscheint nur, wenn er gesetzt ist. `reasoning_effort` ist standardmäßig `none`, auch wenn die Einstellung leer ist, und fehlt nur bei `omit`. Felder wie `user`, `tools` oder `response_format` gibt es nicht.
   3. Bei `TWOX_AI_ENABLED=False` werfen `get_chat_model()` und `stream()` eines schon gebauten Clients `ChatDisabledError`, ohne eine Verbindung aufzubauen. Der Test ersetzt die Socket-Verbindung durch eine Funktion, die fehlschlägt, und der Fake-Server zählt null Anfragen.
   4. Ein Cloud-Modell wird abgewiesen (`ChatRemoteModelError`), bevor `/chat/completions` gerufen wird: am Namen (`…:cloud`, `…-cloud`) und über `remote_host`/`remote_model` in `/api/tags`.
   5. Ein Modell ohne Fähigkeit `completion` (Eintrag wie `bge-m3`, nur `embedding`) wird mit `ChatRejectedError` abgewiesen.
   6. Ein nicht geladenes Modell ergibt `ChatRejectedError` mit Hinweis `ollama pull <modell>`.
   7. `/api/tags` mit 404 (anderer Server): Nur der Name wird geprüft, der Chat läuft.
   8. Die Zeitgrenze zwischen zwei Stücken ergibt `ChatUnavailableError`. Die HTTP-Antwort ist danach geschlossen; der Test prüft das am Server oder an der Antwort.
   9. `close()` während des Stroms und das Schließen des Generators nach dem ersten Stück schließen die HTTP-Antwort. Weitere Stücke kommen nicht. Ein zweiter `close()` ist harmlos.
   10. HTTP 404/400 ergibt `ChatRejectedError`, HTTP 5xx `ChatUnavailableError`. Ein Fehlerobjekt im Strom, ein Abbruch ohne `[DONE]`, kein JSON und eine zu große Antwort ergeben `ChatUnavailableError`.
   11. Fehlermeldungen sind englisch und kurz. Sie enthalten weder Host, Port, URL noch Text aus `messages`. Ein Test schickt eine unverwechselbare Markierung im Prompt und eine Fake-Adresse und prüft `str(error)`.
   12. Logzeilen enthalten nie Prompt- oder Antworttext. Ein Test mit `caplog` auf allen Loggern sucht die Markierung aus 11.
   13. `FakeChatModel`: Stücke, Aufzeichnung der Nachrichten, Fehler nach n Stücken, Fehlschlag beim Aufruf, Zähler für `close()`.
   14. `get_chat_model()` mit leerem `TWOX_CHAT_MODEL` bei KI an ergibt einen klaren `ChatError`, ohne Verbindung.
3. `llm_guard` hat eigene Tests: Cloud-Namen, Modellliste (gefunden, nicht gefunden, entfernt, unlesbar), `full_model_name`, `ollama_root`.
4. Die bestehenden Tests `backend/tests/answers/test_embeddings.py`, `test_check_llm.py`, `backend/tests/search/` und `backend/tests/ingest/` bleiben **unverändert** und grün. `git diff main -- backend/tests/answers/test_embeddings.py backend/tests/answers/test_check_llm.py backend/tests/search backend/tests/ingest` ist leer.
5. Systemprüfung, je mit Test in `test_checks.py`:
   - KI an und Modell leer ergibt genau eine Warnung `twox.answers.W001` und keinen Fehler.
   - KI aus ergibt keine Meldung.
   - KI an mit Cloud-Namen ergibt `twox.answers.E001`.
   - Keine Prüfung baut eine Verbindung auf.
   - Zusätzlich endet `D run --rm backend-dev python manage.py check` mit Exit-Code 0 und zeigt `twox.answers.W001`.
6. Einstellungen, je mit Test:
   - Ungültige Werte (`TWOX_CHAT_TEMPERATURE=abc` oder `3`, `TWOX_CHAT_MAX_TOKENS=0`, `TWOX_CHAT_REASONING_EFFORT=extreme`) ergeben `ImproperlyConfigured` mit dem Variablennamen.
   - Die Standardwerte entsprechen der Tabelle im Umfang.
   - `TWOX_CHAT_REASONING_EFFORT` nicht gesetzt und leer (`""`) ergeben beide `none`; `omit` ergibt „nicht senden“.
7. Prüfungen des Backend-Jobs aus `ci.yml` (Z. 48-86), jeweils grün:
   - `D run --rm backend-dev ruff check .` meldet `All checks passed!`
   - `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0
   - `D run --rm backend-dev mypy .` meldet `Success: no issues found`
   - `D run --rm backend-dev pytest` endet mit 0 fehlgeschlagen und 0 übersprungen
   - `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0
   - `makemessages -l de --add-location=file`, danach `git diff --exit-code -I '^"POT-Creation-Date:' -- backend/locale`
   - `makemigrations --check --dry-run` meldet `No changes detected`
   - `sh scripts/check-licenses.sh` endet mit Exit-Code 0
   - `spectacular --file /out/schema.yml`, unter Git Bash mit `MSYS_NO_PATHCONV=1`, danach `git diff --exit-code -- web/openapi`
   - Die Jobs `web`, `testfactory` und `e2e` sind von diesem Auftrag nicht berührt und bleiben grün. Kein Unterschied unter `web/`.
8. Keine neue Abhängigkeit:
   - `git diff main -- backend/pyproject.toml backend/uv.lock` ist leer.
   - `grep -E '^name = "(httpx|openai)"' backend/uv.lock` findet nichts.
9. Lokal, nur lesend gegen Ollama am Host: Ausgabe von `GET /api/tags` aus dem `api`-Container, im Kurzbericht nur Modellnamen und vorhandene Felder, keine Adresse. Der Bericht sagt, ob die Einträge `capabilities` enthalten, und welcher Weg für die Prüfung „completion“ deshalb gewählt wurde. Kein `ollama pull`, keine Erzeugung mit einem echten Modell.
10. `docs/ARCHITECTURE.md` ist nachgezogen (Konfigurationstabelle, Absatz zum Chat-Client). Z. 134 ist unverändert; die Stichworte dafür stehen im Kurzbericht.
11. Abräumen: `D --profile dev down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

- **Welle 1, parallel zu 120, 122 und 123.** 120 ändert `backend/twox/search/…`, 122 `answers/types.py` und `answers/prompt.py`, 123 `answers/citations.py`. Es gibt keine gemeinsame Code-Datei.
  - In `docs/ARCHITECTURE.md` ändert 121 nur die Konfigurationstabelle und einen kurzen Absatz zum Chat-Client. Die App-Tabelle (Z. 134) pflegt die Leitstelle.
- **Prüfbarkeit des Diffs:** Der Auftrag ist groß. Deshalb in dieser Reihenfolge getrennt committen: (1) `llm_guard.py` mit Tests und Umstellung von `embeddings.py` ohne Verhaltensänderung, (2) Einstellungen, Compose und `.env.example`, (3) `chat.py` mit Fake-Server-Erweiterung und Tests, (4) Systemprüfung, (5) Doku. Die Leitstelle prüft Commit für Commit.
  - 122 schreibt den Ereignisvertrag und die Prompt-Regeln in einen eigenen Unterabschnitt, 120 den Abschnitt Suchgüte (Z. 649-659).
  - Die Leitstelle führt zusammen.
- **Abstimmung mit 122 (Nachrichtentyp):** 122 baut parallel `build_messages(...) -> list[Message]` in `answers/prompt.py`, ohne von `chat.py` abzuhängen, und legt `Message` mit `role: Literal["system", "user"]` an (122, Abschnitt Umfang). Die Schlüssel eines `TypedDict` sind veränderlich und deshalb invariant: Zwei `TypedDict` mit verschiedenen `Literal`-Mengen in `role` sind für mypy **nicht** verträglich, `list[Message]` wäre dann kein `Sequence[ChatMessage]`. Deshalb gilt:
  - Verbindlich ist `ChatMessage` aus `chat.py` mit genau den Schlüsseln `role` (`Literal["system", "user", "assistant"]`) und `content` (`str`). `stream()` nimmt `Sequence[ChatMessage]`.
  - Beim Zusammenführen von 121 und 122 ersetzt die Leitstelle den eigenen Typ in `prompt.py` durch `from twox.answers.chat import ChatMessage` (Alias `Message = ChatMessage` ist zulässig). Die Richtung ist `prompt.py` → `chat.py`, nie umgekehrt; so entsteht kein Importzyklus.
  - 121 ändert keine Datei von 122. Der Kurzbericht nennt diesen Schritt für die Leitstelle.
- **Folgeaufträge bauen darauf auf:**
  - 125 und 126 rufen nur `get_chat_model()` und nutzen in Tests `FakeChatModel`.
  - 129 nutzt `llm_guard` und die Fähigkeitsprüfung für Selbsttest und `check_llm --chat`, ohne Erzeugung.
  - 135 baut `ReplayChatModel` auf dem Protokoll auf.
  - Das Protokoll soll deshalb schlank bleiben: keine Werkzeuge, kein JSON-Modus.
- **Fähigkeit „completion“:**
  - `embeddings.py:26-29` hält fest, dass `POST /api/show` für ein nie geladenes Cloud-Modell ollama.com fragt. Deshalb gilt als Reihenfolge: zuerst Name, dann `/api/tags` (das Modell muss lokal gelistet sein, ohne `remote_*`), dann die Fähigkeit.
  - Enthält der Eintrag in `/api/tags` ein Feld `capabilities`, wird es dort gelesen.
  - Fehlt es (Kriterium 9 klärt das für Ollama 0.40.17), darf `POST /api/show` mit `{"model": <name>}` **erst nach** bestandener Prüfung über `/api/tags` gerufen werden. Das Modell ist dann nachweislich lokal, und das Feld `capabilities` wird dort gelesen.
  - Liefert der Server keine Fähigkeiten (anderer OpenAI-kompatibler Server), wird nur protokolliert, wie bei `/api/tags` mit Status ungleich 200.
  - Der gewählte Weg steht im Modul-Docstring und im Kurzbericht.
- **`reasoning_effort`:** Ollama nimmt das Feld über `/v1` an. Ob `none` bei der Version am Host angenommen wird, wird **nicht** mit einem echten Modell geprüft, weil kein Chat-Modell geladen ist (D1). Der Wert ist deshalb einstellbar, und `omit` schaltet das Feld ab. Der Messlauf 128 prüft das Verhalten.
- **Kontextlänge:** Sie lässt sich über `/v1` nicht je Anfrage setzen (`num_ctx`). Der Client sendet sie nicht. Die Einstellung `OLLAMA_CONTEXT_LENGTH` am Host gehört zu D1 und 128, die Betriebsdoku zu 129.
- **Muster und Belege im Bestand:**
  - Fehlerbehandlung von `urllib`: `embeddings.py:341-376`. Die Meldungen nennen keine Adresse, anders als `check_llm.py`, das eine Adresse ausgeben darf.
  - Zeitgrenze erkennen: `embeddings.py:140-144`.
  - Schalter E-59: `embeddings.py:147-149`.
  - Attrappe: `backend/tests/answers/fake_ollama.py:16, 35-49`.
  - Systemprüfung: `backend/twox/ingest/checks.py:25-27, 62-70`.
  - Einstellungsblock: `backend/twox/config/settings.py:426-446`.
  - Umgebungsblock: `deploy/compose/compose.yaml:16-23`.
  - Vorlage: `.env.example:25-48`.
- **Leitplanken:**
  - Kein Text verlässt das Haus. Kein Proxy, keine Telemetrie, keine Anfrage an eine andere Adresse als `TWOX_LLM_BASE_URL`.
  - Prompt und Antwort gelten als vertraulich und erscheinen in keinem Log.
  - Dokumentinhalte sind Daten, keine Anweisungen (Leitplanke 4). Der Client verändert die Nachrichten nicht und fügt nichts hinzu.
- **Antwort-Stream** nach E-03 (`docs/DECISIONS.md:95`): Der Client liefert einen synchronen `Iterator[str]`. Die asynchrone Hülle für SSE baut 130 mit `sync_to_async`. Kein `asyncio` in diesem Auftrag.
- **Sprache:** Code, Bezeichner, Docstrings und Meldungen auf Englisch, der Kurzbericht auf Deutsch.
- **Keine neue Abhängigkeit**, kein Push (E-14). Kleine Commits auf dem eigenen Zweig. Keine Personennamen und keine lokalen Pfade mit Benutzernamen in Dateien oder Commits.
- In der CI gibt es kein Ollama. Alles Prüfbare läuft gegen den Fake-Server. Kriterium 9 läuft nur lokal und nur lesend.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine, die den Auftrag aufhält. `TWOX_CHAT_MODEL` bleibt leer bis zur Entscheidung D1 (Modellwahl im Messlauf 128). Der Variablenname ist ein Vorschlag der Leitstelle.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Was wurde gebaut?** In fünf Commits, wie vorgegeben:

1. `answers/llm_guard.py` (neu): `is_cloud_model_name`, `ollama_root`, `full_model_name`, `is_timeout`, `TAGS_PATH`, `SHOW_PATH`, `COMPLETION_CAPABILITY`, `model_capabilities(answer)` und `find_local_model(body, model)` mit den neutralen Fehlern `ModelListError`, `ModelNotLoadedError`, `RemoteModelError` (Meldungen wie bisher, mit `ollama pull <modell>`). `embeddings.py` nutzt das Modul; Fehlerklassen, Meldungen, Reihenfolge und `monotonic` bleiben, `is_cloud_model_name` wird ausdrücklich wieder ausgeführt (`import … as is_cloud_model_name`).
2. Einstellungen `TWOX_CHAT_MODEL`, `_TIMEOUT_SECONDS`, `_MAX_TOKENS`, `_TEMPERATURE`, `_REASONING_EFFORT` mit `env_float` und `env_reasoning_effort` (leer = `none`, `omit` = `None` = Feld nicht senden); Compose-Zeilen und `.env.example`-Block ohne Modellnamen.
3. `answers/chat.py` (neu): `ChatMessage` (TypedDict, `role` system/user/assistant), Protokoll `ChatModel` (`model_name`, `stream(...) -> Iterator[str]`, `close()`), Fehler `ChatError`, `ChatDisabledError`, `ChatUnavailableError`, `ChatRejectedError`, `ChatRemoteModelError`, `OpenAICompatibleChat` (urllib ohne Proxy, SSE zeilenweise, Größen- und Zeilengrenze, Schließen über `close()` auch aus anderem Thread per Socket-`shutdown`), `get_chat_model()`, `FakeChatModel` (Stücke, Aufzeichnung in `calls`, Fehler nach n Stücken, `fail_on_call`, `close_count`). `stream()` prüft und sendet die Anfrage schon beim Aufruf (Ablehnung/keine Verbindung kommt sofort), die Stücke werden beim Iterieren gelesen.
4. `answers/checks.py` (neu) mit `twox.answers.W001` (KI an, Modell leer) und `twox.answers.E001` (Cloud-Name), registriert in `AnswersConfig.ready()`.
5. `docs/ARCHITECTURE.md`: Konfigurationstabelle, Satz zu den Zahlenprüfungen, Absatz zum Chat-Client (direkt nach der Tabelle, Abschnitt „Configuration“).

**Fähigkeit completion (Kriterium 9):** `GET /api/tags` aus dem `api`-Container, nur lesend, Ollama 0.40.17: Einträge `qwen3-embedding:0.6b` und `bge-m3:latest`, Felder `capabilities`, `details`, `digest`, `model`, `modified_at`, `name`, `size`. `capabilities` ist vorhanden (`bge-m3`: nur `embedding`; `qwen3-embedding`: `tools`, `thinking`, `embedding`). Gewählter Weg: Fähigkeiten aus dem Eintrag in `/api/tags`; nur wenn er keine nennt, `POST /api/show` – erst nach bestandener Prüfung über `/api/tags`. Nennt auch das keine, wird nur `info` protokolliert. Kein `ollama pull`, keine Erzeugung.

**Wie wurde getestet?** Alles in Containern (`docker compose -p twox-121`, `.env` aus `.env.example`, `TWOX_API_PORT=18121`, KI an, Modell leer):

| Kriterium | Ergebnis |
| --- | --- |
| 0 | `docker version`, `docker compose version` Exit 0 |
| 1 | build und `up -d --wait` Exit 0 |
| 2.1–2.14 | je eigene Tests in `backend/tests/answers/test_chat.py` gegen den erweiterten Fake-Server (`fake_ollama.py`: Route `/v1/chat/completions` mit SSE, Pausen, Abbruch, Fehlerobjekt, `[DONE]`/`finish_reason`, Zeilen nach `[DONE]`; `/api/show`; Einträge mit `capabilities`; Ereignis `client_closed`, das der Server beim Schließen durch den Client setzt). Zeitgrenze und `close()` prüfen das Schließen am Server. Markierung im Prompt und Fake-Adressen erscheinen weder in Fehlertexten noch in Logs. – erfüllt |
| 3 | `backend/tests/answers/test_llm_guard.py` – erfüllt |
| 4 | `git diff main -- …test_embeddings.py …test_check_llm.py backend/tests/search backend/tests/ingest` leer – erfüllt |
| 5 | `backend/tests/answers/test_checks.py` (W001 genau einmal, aus = nichts, E001, keine Verbindung); `manage.py check` Exit 0 mit `twox.answers.W001` – erfüllt |
| 6 | Einstellungstests in `test_chat.py` (Unterprozess mit Standardwerten, ungesetzt und leer; ungültige Werte mit Variablenname; `env_float`, `env_reasoning_effort`) – erfüllt |
| 7 | ruff check „All checks passed!“, ruff format Exit 0, mypy „Success: no issues found in 201 source files“, pytest 2515 passed, 0 failed, 0 skipped, `pytest -m worker` 6 passed, Übersetzungskatalog ohne Unterschied, „No changes detected“, „License check passed.“, Schema ohne Unterschied; kein Unterschied unter `web/` – erfüllt |
| 8 | `git diff main -- backend/pyproject.toml backend/uv.lock` leer, kein `httpx`/`openai` in `uv.lock` – erfüllt |
| 9 | siehe oben – erfüllt |
| 10 | ARCHITECTURE nachgezogen, Z. 134 unverändert – erfüllt |
| 11 | `down -v` Exit 0 – erfüllt |

**Zweig und Arbeitsverzeichnis:** Zweig `worktree-agent-a9f778e2b68aa1744`, Arbeitsverzeichnis `.claude/worktrees/agent-a9f778e2b68aa1744`.

**Für die Leitstelle beim Zusammenführen:**

- App-Tabelle `docs/ARCHITECTURE.md` Z. 134 (`answers`), Stichworte: Chat-Client `chat.py` (Protokoll `ChatModel`, Zugang `get_chat_model()`, Attrappe `FakeChatModel`), gemeinsame Cloud-Sperre `llm_guard.py`, Systemprüfung `checks.py` (`twox.answers.W001`/`E001`).
- Mit 122: In `answers/prompt.py` den eigenen Nachrichtentyp durch `from twox.answers.chat import ChatMessage` ersetzen (Alias `Message = ChatMessage` zulässig), Richtung `prompt.py` → `chat.py`.

**Abweichungen:**

- `settings.py` enthält neben `env_float` eine zweite kleine Hilfsfunktion `env_reasoning_effort` (mit den privaten Konstanten `_CHAT_REASONING_EFFORTS`, `_CHAT_REASONING_EFFORT_OMIT`) neben den anderen `env_*`; so ist die Prüfung „leer = none, omit = nicht senden, sonst `ImproperlyConfigured`“ einzeln testbar. Der Block selbst steht wie verlangt nach `TWOX_SEARCH_EMBED_TIMEOUT_SECONDS`.
- `llm_guard.py` bekommt zusätzlich `SHOW_PATH`, `COMPLETION_CAPABILITY` und `model_capabilities()`, damit 129 die Fähigkeitsprüfung ohne Erzeugung mitnutzen kann.
- Die Einstellungstests stehen in `test_chat.py` (der Auftrag nennt keine eigene Datei dafür); sie nutzen `run_python` aus `tests/config/test_settings.py`, ohne diese Datei zu ändern.
- `ChatUnavailableError` deckt auch „kein Modell eingestellt“ ab (Vorschlag aus dem Auftrag).
- **Verhalten von `stream()`:** Prüfungen (KI an, Nachrichten, Name, Modellliste, Fähigkeit) und das Senden der Anfrage geschehen schon beim Aufruf. Abweisung, fehlende Verbindung und HTTP-Fehler kommen also, bevor etwas zurückgegeben wird. Rückgabetyp ist nicht ein roher Generator, sondern `ChatStream` (siehe Nachbesserung): ein `Iterator[str]` mit `close()`, `closed` und `with`. Auch `FakeChatModel.stream()` und das Protokoll `ChatModel` liefern `ChatStream`.
- Hinweis: Weil `.env.example` die KI einschaltet und kein Chat-Modell setzt, zeigen jetzt alle `manage.py`-Befehle im Entwicklungsaufbau die Warnung W001 (so gewollt, Kriterium 5).

Offene Fragen: keine.

**Nachbesserung (nach Prüfung durch die Leitstelle):**

- Fehler: `stream()` gab den rohen Generator zurück. Wurde er vor dem ersten `next()` geschlossen, lief sein `finally` nie. Die HTTP-Verbindung blieb offen, Ollama erzeugte weiter, und der Eintrag blieb in `_streams`.
- Gewählte Lösung: `stream()` gibt jetzt ein Objekt `ChatStream` zurück (Iterator mit `close()`, `closed`, `__enter__`/`__exit__`). Begründung: Die Fehler sollen weiter sofort beim Aufruf kommen (126 braucht das), und dafür muss die Anfrage beim Aufruf gesendet sein. Mit „Verbindung erst beim ersten `next()` öffnen“ wären HTTP-Fehler erst beim Lesen gekommen.
- `ChatStream.close()` schließt zuerst die Verbindung über `_release` (Eintrag aus `_streams` entfernen, Socket abbauen) und danach den Generator. Das gilt vor dem ersten Stück, mitten im Strom und nach dem Ende. Mehrfacher Aufruf ist harmlos.
- Ein ungenutzt verworfenes Objekt wird über `weakref.finalize` geschlossen, sonst spätestens durch `client.close()`.
- Neue Tests in `test_chat.py`, alle mit dem Server-Ereignis `client_closed` und leerem `_streams`:
  - `close()` vor dem ersten Stück
  - `contextlib.closing` mit Ausnahme vor dem ersten Stück
  - `with`-Block
  - verworfenes Objekt mit `gc.collect()`
  - `client.close()` bei ungelesenem Strom
  - schließbarer Strom der Attrappe
- Modul- und Methoden-Docstrings beschreiben das Verhalten jetzt zutreffend.
- Prüfungen nach der Nachbesserung, alle grün:
  - ruff, ruff format, mypy (201 Dateien)
  - pytest: 2521 passed, 0 failed, 0 skipped; `pytest -m worker`: 6 passed
  - Übersetzungskatalog, Migrationen, Lizenzen, Schema; `manage.py check` Exit 0
  - `down -v` Exit 0
- Zu Kriterium 4: `git diff main -- …` ist inzwischen nicht mehr leer. Grund ist nur, dass `main` weitergelaufen ist (120 hat `tests/search/test_evaluation.py` und `test_probes_m3.py` hinzugefügt). Gegen den Ausgangspunkt des Zweigs (`808d30a`) und mit `git diff main...HEAD` ist der Diff leer. Dieser Zweig ändert die Dateien nicht.
