# Auftrag 126 – Antwortdienst und Befehl `ask`

Meilenstein: M3 · Freigabestufe: B · Status: erledigt

## Ziel

Ein Dienst setzt Kontextauswahl (125), Prompt (122), Chat-Modell (121) und Zitatprüfung (123) zu einem Ereignisstrom zusammen: `sources`, dann `delta`*, dann `done` oder `error`. Der Dienst kommt ohne HTTP aus. So sind die Messung (127, 128) und die Aufzeichnung für die CI (135) möglich, bevor es API (130) und Oberfläche (131–134) gibt. Der Befehl `manage.py ask` macht den Dienst in der Testumgebung von Hand bedienbar.

Leitplanke 3 gilt hart: Eine Antwort ohne gültige Quelle endet als `no_evidence` mit dem festen Satz „Dazu finde ich nichts in den Unterlagen“. Leitplanke 4 gilt ebenso: Dokumentinhalte gehen nur über `prompt.build_messages` an das Modell.

## Umfang

### 1. `backend/twox/answers/service.py` (neu)

Öffentliche Funktion:

```python
def answer(
    question: str,
    *,
    device_ids: Sequence[int] = (),
    plant_ids: Sequence[int] = (),
    chat: ChatModel | None = None,
    seed: int | None = None,
) -> Iterator[AnswerEvent]: ...
```

`seed` ist optional und wird unverändert an `chat.stream(..., seed=seed)` durchgereicht. `None` heißt: kein Seed, das Feld wird nach 121 nicht gesendet (121 hat keine Einstellung für den Seed). So können 127 (`evaluate_answers --seed`), 128, 135 und 138 einen festen Seed setzen, ohne neue Einstellung.

**Importform (verbindlich):** `service.py` importiert die Module und ruft über sie auf: `from twox.answers import chat as chat_module, context, prompt, citations` und dann `chat_module.get_chat_model()`, `prompt.new_nonce()`, `prompt.build_messages(...)`, `context.select_context(...)` (Muster `embeddings.get_query_embedder()` in `backend/twox/search/postgres.py:614`). Kein `from twox.answers.chat import get_chat_model` und kein `from twox.answers.prompt import new_nonce`: Sonst greift `monkeypatch` am Modul nicht, und 135 kann die Kennung für einen stabilen Aufzeichnungsschlüssel nicht festlegen (135 darf `service.py` nicht ändern).

Ablauf, in genau dieser Reihenfolge:

1. **KI aus (E-59, D10):** Ist `settings.TWOX_AI_ENABLED` falsch, kommt genau ein Ereignis `ErrorEvent(code="ai_disabled")`, dann endet der Strom. Es gibt keine Kontextauswahl, keinen Aufruf von `get_chat_model()` und keine Netzverbindung. Ein übergebenes `chat` wird nicht benutzt.
2. **Eingabe prüfen:** Leere Frage oder nur Leerraum → `ValueError` vor dem ersten Ereignis (die API in 130 prüft die Länge selbst; der Dienst prüft nur leer). Die Höchstlänge übernimmt der Dienst nicht, sie liegt bei `SearchRequest` (`backend/twox/search/interface.py:81-82`) und bei 130.
3. **Kontext:** `context.select_context(question, device_ids, plant_ids)` aus 125. Fehlschlag der Datenbank oder Suche → `ErrorEvent` mit passendem Code aus der festen Liste in `types.py` (122), ohne Rohtext.
4. **`sources`:** Ein `SourcesEvent` mit den `ContextSource` der Auswahl (Nummern 1..n, wie 125 sie vergibt).
5. **Unter der Schwelle:** Ist `selection.below_threshold` gesetzt, ist das `SourcesEvent` leer, und sofort folgt `DoneEvent(status="no_evidence", cited=[], removed_sentences=0, final_text=<fester Satz>)`. Das Modell wird nicht gefragt; `get_chat_model()` wird nicht aufgerufen.
6. **Modell:** `chat` oder, falls `None`, `get_chat_model()` (121). Nachrichten nur über `prompt.build_messages(question, sources, nonce)` mit einer frischen Kennung je Aufruf aus `prompt.new_nonce()` (die Erzeugung der Kennung gehört zu 122; der Dienst ruft nur auf). `max_tokens` und `temperature` bleiben `None`, damit 121 die Einstellungen `TWOX_CHAT_MAX_TOKENS` und `TWOX_CHAT_TEMPERATURE` nimmt; `seed` kommt aus dem Parameter von `answer()`. Keine neuen Einstellungen in diesem Auftrag.
7. **`delta`:** Jedes Textstück aus `chat.stream(...)` wird sofort als `DeltaEvent` weitergegeben und für die Prüfung gesammelt (D9 (a): streamen, am Ende prüfen).
8. **`done`:** Nach dem Ende des Stroms `citations.verify(text, {n: source.text}, drop_unsupported=True)` (123; D8 (c) als Vorgabe: unbelegte Sätze entfernen und kennzeichnen). Daraus `DoneEvent` mit `status`, `cited`, `removed_sentences` und `final_text`. Bei `no_evidence` ist `final_text` immer der feste Satz und `cited` leer, auch wenn das Modell etwas anderes geschrieben hat.
9. **Fehler im Modell:** Jede Ausnahme aus 121 (`ChatDisabledError`, `ChatUnavailableError`, `ChatRejectedError`, `ChatRemoteModelError`, Zeitgrenze) wird auf einen festen Code abgebildet (Vorschlag: `ai_disabled`, `model_unavailable`, `model_rejected`, `timeout`) und als `ErrorEvent` ausgegeben, auch mitten im Strom nach schon gesendeten `delta`. Nach `error` kommt kein `done`. Das `ErrorEvent` enthält weder Ausnahmetext noch Adresse noch Modellausgabe. Unerwartete Ausnahmen werden protokolliert (nur Typname) und als allgemeiner Code aus der Liste von 122 gemeldet.
10. **Abbruch:** Schließt der Aufrufer den Generator (`close()`, also `GeneratorExit`), oder endet der Strom auf andere Weise, wird der Modellstrom in einem `finally` geschlossen (`close()` am Iterator bzw. `chat.close()` nach dem Vertrag von 121). Ein vom Aufrufer übergebenes `chat` wird nicht geschlossen, nur sein Strom; ein selbst über `get_chat_model()` geholtes Modell wird geschlossen.
11. **Protokoll (D7 (a), E-62):** Ein Logger `twox.answers.service` schreibt je Anfrage höchstens eine Zeile, auf Englisch: Ergebnis (`status` oder Fehlercode), Modellname, Dauer in ms, Zahl der Quellen, bei `done` die Zahl gültiger Zitate und entfernter Sätze. Nie Frage, Antwort, Textstücke, Abschnittstext, Dateinamen, Titel, Geräte- oder Anlagenkennungen, Basisadresse. Bei Fehlern nur der Typname der Ausnahme, kein `logger.exception` mit Traceback, der Text enthalten könnte.

Der Dienst ist zustandslos und speichert nichts (D7 (a)): keine Modelle, keine Migration, kein Cache.

### 2. `backend/twox/answers/management/commands/ask.py` (neu)

```
manage.py ask "<Frage>" [--device ID ...] [--plant ID ...] [--seed N] [--json]
```

- `--seed` (ganzzahlig, optional) wird an `answer(seed=...)` durchgereicht; ohne Angabe kein Seed.
- `--device` und `--plant` nehmen ganzzahlige Kennungen, mehrfach angebbar (`action="append"`, `type=int`); werden an `device_ids`/`plant_ids` durchgereicht.
- Ohne `--json`: Die Textstücke erscheinen fortlaufend auf der Standardausgabe (mit `flush`). Danach die Quellenliste (`[n] Titel, Version, Seite(n) bzw. Überschriftenpfad`) und eine Schlusszeile `status: answered|no_evidence|contradiction` mit Zahl der gültigen Zitate und entfernten Sätze. Bei `done` mit bereinigter Fassung wird diese unter einer Zeile `final:` ausgegeben, wenn sie vom gestreamten Text abweicht.
- Mit `--json`: Je Ereignis eine Zeile JSON (JSON Lines) mit dem Ereignistyp und den Feldern aus der Serialisierung von 122 (Roundtrip aus 122 wiederverwenden, keine eigene Serialisierung).
- `error`: Zeile `FAILED: <code>` auf der Fehlerausgabe, Exit-Code 1. `ai_disabled`: Zeile `DISABLED: …` wie bei `check_llm` (`backend/twox/answers/management/commands/check_llm.py:41-44`), Exit-Code 0, nichts wird kontaktiert. Leere Frage → `CommandError`, Exit-Code 1.
- Der Befehl ist für die Testumgebung und die Messung gedacht. Er gibt Antwort und Quellen auf dem Terminal aus (das ist sein Zweck), schreibt sie aber nie in einen Logger und nie in eine Datei.
- Hilfetext und Ausgaben auf Englisch.

### 3. Tests `backend/tests/answers/test_service.py` (neu)

- Mit `FakeChatModel` aus `backend/twox/answers/chat.py` (121); Kontextauswahl über Datenbank mit eigenen Texten und Stub-Embedder (Muster `backend/tests/ingest/fake_converter.py:201`, `FakeEmbedder`) oder, wo es nur um den Ablauf geht, über einen eingesetzten Stub von `select_context` (`monkeypatch`). Mindestens ein Test läuft Ende zu Ende über die echte Kontextauswahl mit Datenbank.
- Alle Testtexte selbst geschrieben, keine Herstellertexte.
- Netzsperre nach dem Muster `forbid_network` (`backend/tests/answers/test_check_llm.py:242`) für die Fälle „KI aus“ und „unter der Schwelle“.
- Befehlstests für `ask` (mit und ohne `--json`, `--device`, KI aus, Fehler) in derselben Datei oder in `backend/tests/answers/test_ask.py` (neu).

## Nicht-Ziele

- Keine HTTP-Schnittstelle, kein SSE, kein Throttle (130).
- Keine Änderung an `chat.py`, `llm_guard.py` (121), `types.py`, `prompt.py` (122), `citations.py` (123), `context.py` (125) und nichts unter `backend/twox/search/`. Fehlt dort etwas, wird es im Kurzbericht als Abweichung genannt und nicht hier nachgebaut.
- Keine neuen Einstellungen in `settings.py`, `compose.yaml` oder `.env.example`.
- Kein Speichern von Fragen oder Antworten, kein Verlauf, keine Migration (D7).
- Kein Messwerkzeug (127), kein Lauf mit echtem Modell (128), keine Aufzeichnung für die CI (135).
- Keine Änderung an Prompt-Regeln oder Schwelle; Kalibrierung folgt in 128.
- Keine Änderung an `testfactory/` oder an den Prüffragen.

## Betroffene Bereiche (Ordner, Dateien)

- neu: `backend/twox/answers/service.py`
- neu: `backend/twox/answers/management/commands/ask.py` (das Paket `backend/twox/answers/management/commands/` gibt es schon, mit `check_llm.py`)
- neu: `backend/tests/answers/test_service.py`, optional `backend/tests/answers/test_ask.py`
- `docs/ARCHITECTURE.md`: nur Zeile `answers` in der Modultabelle (Z. 134) um „Antwortdienst `service.py`, Befehl `ask`“ ergänzen und im Abschnitt „answers“ (von 122 angelegt) einen kurzen Absatz zu Ablauf, Abbruch und Protokoll

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-126`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18126` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Tests mit `FakeChatModel` in `tests/answers/test_service.py` (bzw. `test_ask.py`), je mindestens ein Test:
   1. Eine belegte Antwort ergibt die Folge `sources`, `delta`+, `done(answered)` mit gültigen Zitaten; die `delta`-Stücke kommen in der Reihenfolge des Fakes.
   2. Eine erfundene Nummer (z. B. `[9]` bei weniger Quellen) wird verworfen; erscheint sie im einzigen Satz, ergibt das `no_evidence`.
   3. Die Absage des Modells ergibt `done(no_evidence)` ohne Zitate, `final_text` ist der feste Satz.
   4. Unter der Schwelle wird das Modell nicht gerufen: ein Fake, der bei `stream()` fehlschlägt, und ein `get_chat_model`, das bei Aufruf fehlschlägt; die Folge ist `sources` (leer), `done(no_evidence)`.
   5. Bei `TWOX_AI_ENABLED=False` kommt genau `error(ai_disabled)`; weder Kontextauswahl noch Modell werden gerufen, keine Netzverbindung (Netzsperre).
   6. Ein Modellausfall mitten im Strom (Fake wirft nach zwei Stücken) ergibt `error` mit festem Code, ohne Ausnahmetext, ohne `done`. Ebenso je ein Test für die Abbildung jeder Fehlerklasse aus 121 auf ihren Code.
   7. Ein Abbruch durch den Aufrufer (`gen.close()` nach dem ersten `delta`) ruft `close()` am Strom bzw. Fake (Zähler im Fake).
   8. Log-Test mit `caplog` auf Ebene `DEBUG` für alle Logger (Wurzel-Logger): Bei Erfolg, Absage, Fehler und Abbruch steht in keiner Logzeile die Frage, ein Textstück der Antwort, ein Abschnittstext, ein Dokumenttitel oder ein Dateiname. Die eine Zeile von `twox.answers.service` enthält Status, Modellname, Dauer und Zahl der Quellen.
   9. `manage.py ask --json` läuft mit dem Fake (über `monkeypatch.setattr` auf das Modul `twox.answers.chat`, Attribut `get_chat_model`) und gibt je Ereignis eine gültige JSON-Zeile aus; ohne `--json` erscheint die Schlusszeile `status: …`; `--device` grenzt die Quellen ein (zwei Geräte, Test); KI aus gibt `DISABLED:` mit Exit-Code 0; ein Fehler gibt `FAILED: <code>` mit Exit-Code 1.
   10. Keine Datenbankschreibung durch den Dienst: Ein Aufruf über die echte Kontextauswahl führt keine Abfrage mit `INSERT`, `UPDATE` oder `DELETE` aus (Prüfung der erfassten Abfragen, z. B. mit `django.test.utils.CaptureQueriesContext`).
   11. Seed und Importform: `answer(..., seed=7)` übergibt `seed=7` an `stream()`, ohne Angabe `seed=None` (Zähler im Fake). Ein `monkeypatch.setattr` auf `twox.answers.prompt.new_nonce` mit fester Kennung wirkt im Dienst: `build_messages` erhält genau diese Kennung (Test).
3. `D run --rm backend-dev pytest tests/answers -v` endet mit Exit-Code 0. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen. `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
4. `D run --rm backend-dev ruff check .` meldet `All checks passed!`, `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0, `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
5. Weitere Prüfungen wie in `.github/workflows/ci.yml` (Job `backend`), jeweils ohne Unterschied zum eingecheckten Stand:
   - `D run --rm backend-dev python manage.py makemessages -l de --add-location=file`, danach `git diff --exit-code -I '^"POT-Creation-Date:' -- backend/locale`;
   - `D run --rm backend-dev python manage.py makemigrations --check --dry-run` endet mit Exit-Code 0 (keine Migration);
   - `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0;
   - `MSYS_NO_PATHCONV=1 D run --rm -v "$PWD/web/openapi:/out" backend-dev python manage.py spectacular --file /out/schema.yml`, danach `git diff --exit-code -- web/openapi` (das Schema bleibt unverändert).
6. In der laufenden Testumgebung (die `.env` aus `.env.example` hat `TWOX_AI_ENABLED=true` und ein leeres `TWOX_CHAT_MODEL`, `.env.example:35`):
   1. KI aus: `D exec -T -e TWOX_AI_ENABLED=false api python manage.py ask "Testfrage"` gibt eine Zeile `DISABLED:` aus und endet mit Exit-Code 0.
   2. KI an, Modell leer: `D exec -T api python manage.py ask "Testfrage"` endet entweder mit `status: no_evidence` (Datenbank ohne Treffer unter der Schwelle, Modell nicht gefragt) oder mit `FAILED: model_unavailable` auf der Fehlerausgabe und Exit-Code 1; kein Traceback, keine Adresse in der Ausgabe. Ausgabe und Exit-Code stehen im Kurzbericht.
7. `git diff main --stat` zeigt nur Dateien aus „Betroffene Bereiche“. Keine neue Abhängigkeit (`backend/pyproject.toml` und Lock-Datei unverändert).
8. Abräumen: `D --profile dev down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

- **Voraussetzungen:** 121, 122, 123 und 125 sind nach `main` zusammengeführt. Der Bearbeiter baut auf deren Schnittstellen auf (`ChatModel`, `get_chat_model`, `FakeChatModel`, Fehlerklassen; `ContextSource`, `AnswerEvent` und Unterklassen, Fehlercode-Liste, `build_messages`; `verify`/`Verdict`; `select_context`/`ContextSelection`). Weichen Namen von diesem Auftrag ab, gilt der Stand auf `main`; die Abweichung kommt in den Kurzbericht.
- **Welle 3** nach dem Gesamtplan M3: 126 folgt auf 125 und läuft allein in diesem Bereich. Parallel laufen höchstens Aufträge außerhalb von `backend/twox/answers/` (z. B. 129 berührt `check_llm.py` und `selftest.py`, nicht `service.py`). `docs/ARCHITECTURE.md` nur in den genannten Stellen ändern; die Leitstelle führt zusammen.
- **Schnittstellen vor Umsetzung (E-04, CLAUDE.md):** Suche nur über die Kontextauswahl (125), die ihrerseits `get_search_backend()` nutzt (`backend/twox/search/interface.py:161-166`). Das Modell nur über `get_chat_model()`/`ChatModel`. Kein direkter Zugriff auf `Section.objects` oder auf HTTP im Dienst.
- **KI optional (E-59):** Jede KI-abhängige Stelle braucht einen Test für „an“ und „aus“. Bei „aus“ keine Verbindung. Vorbild für die neutrale Meldung: `check_llm.py:245-248`.
- **Antworten nur mit Quelle (Leitplanke 3, E-04):** Der feste Satz lautet wörtlich „Dazu finde ich nichts in den Unterlagen“. Er kommt als Konstante aus 122/123 und wird nicht im Dienst neu geschrieben.
- **Dokumentinhalte sind Daten (Leitplanke 4):** Abschnittstexte nie selbst in Nachrichten einfügen, nur über `build_messages`. Keine Abschnittstexte in `ErrorEvent`, Logs oder Ausnahmen.
- **Protokoll (D7 (a), E-62):** Wie bei Suche und Zugriffsprotokoll (`backend/twox/config/settings.py:395-424`, Filter `drop_query_string`) stehen keine Nutzertexte im Log. Logger-Name unter `twox`, damit er über den bestehenden Handler läuft (`settings.py:417`).
- **Sprachfassungen (E-61) und mehrere Fundorte (E-55)** behandelt die Kontextauswahl (125). Der Dienst reicht `ContextSource` unverändert durch und ändert keine Nummern.
- **Streaming (D9 (a)):** Die gestreamten `delta` sind vorläufig; maßgeblich ist `final_text` aus `done`. Das steht im Docstring von `answer()`, weil 130 und 131 darauf aufbauen.
- **Ereignisreihenfolge** ist Vertrag (beschrieben in `docs/ARCHITECTURE.md` durch 122): genau ein `sources` vor allen `delta`, höchstens ein Endereignis (`done` oder `error`), danach nichts mehr. Ausnahme: `error(ai_disabled)` kommt ohne `sources`.
- **Synchron:** `answer()` ist ein normaler Generator. Die Anbindung an einen asynchronen Strom übernimmt 130 (`sync_to_async`, Muster `backend/twox/files/downloads.py:64-97`). Keine `async`-Funktionen in diesem Auftrag.
- **Typen:** Jede Funktion mit Typangaben, `mypy .` ohne Fehler (CLAUDE.md, Arbeitsregeln).
- **Testdaten:** nur selbst geschriebene Texte; keine Handbuchauszüge, keine Inhalte aus `testfactory/extern/` (ungetrackt). Keine Geheimnisse, keine Personennamen (E-22).
- **Keine neue Abhängigkeit.** Kein `openai`, kein `httpx`, keine Streaming-Bibliothek.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

Keine, die den Auftrag aufhalten. Umgesetzt werden die Vorgaben nach Empfehlung:

- **D7 Speichern und Protokollieren:** (a) nichts speichern, nur Fehlerart, Modell, Dauer und Zahl der Quellen protokollieren; (b) Verlauf je Benutzer in der Datenbank; (c) anonyme Qualitätsdaten. Empfehlung und Vorgabe: (a), abgesichert durch den Log-Test in Kriterium 2.8.
- **D8 Absage und Teilantworten:** (a) harte Regel im Code (Schwelle ohne Modellaufruf, Zitatprüfung) plus (c) unbelegte Sätze entfernen und kennzeichnen; Alternative (d) ganze Antwort verwerfen. Vorgabe bis zur Entscheidung: (a) und (c), also `drop_unsupported=True`.
- **D9 Antwortformat:** (a) streamen, am Ende prüfen und `final_text` ersetzen; (b) erst prüfen, dann senden; (c) JSON ohne Streaming. Vorgabe: (a). Der Ereignisvertrag bleibt bei einer späteren Umstellung auf (b) gleich.
- **D10 KI aus:** (a) keine Antwort, `error(ai_disabled)`; (b) Fundstellen ohne Antworttext. Vorgabe: (a).

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Eigenes Compose-Projekt `twox-126`, `TWOX_API_PORT=18126`. „2x“ und „twox-leit“ nicht angefasst. Keine neue Abhängigkeit, keine Migration, keine Einstellung.

### Was wurde gebaut?

- **`backend/twox/answers/service.py` (neu):** `answer(question, *, device_ids, plant_ids, chat, seed) -> Iterator[AnswerEvent]`, Ablauf in der Reihenfolge des Auftrags. Importform wie verlangt (`from twox.answers import chat as chat_module, citations, context, prompt, types`; Aufrufe über die Module; aus `chat` nur die Typen `ChatModel`, `ChatStream`). Öffentliche Hilfen `chat_error_code()` und `context_error_code()`.
  - Fehlercodes: `ChatDisabledError` → `ai_disabled`; `ChatRejectedError`, `ChatRemoteModelError` → `model_rejected`; übrige `ChatError` → `model_unavailable`, bei Zeitgrenze als Ursache (`llm_guard.is_timeout(__cause__)`) → `timeout`; `ContextDisabledError` → `ai_disabled`; `ContextUnavailableError` → `model_unavailable`; jede andere Ausnahme der Kontextauswahl (Datenbank, Suche) → `search_failed`; alles Unerwartete (auch in `build_messages`/`verify`) → `internal`.
  - Abbruch: `finally` schließt den `ChatStream`; ein selbst geholtes Modell wird geschlossen, ein übergebenes nicht.
  - Protokoll: genau eine Zeile je Anfrage, Logger `twox.answers.service`, z. B. `Answer: result=answered model=… duration_ms=… sources=2 cited=1 removed_sentences=0`, bei Fehlern zusätzlich `exception=<Typname>`; Fehler auf WARNING, sonst INFO; Abbruch als `result=cancelled`.
  - Docstring von `answer()` nennt D9 (a) (`delta` vorläufig, maßgeblich `final_text`).
- **`backend/twox/answers/management/commands/ask.py` (neu):** `ask "<Frage>" [--device ID …] [--plant ID …] [--seed N] [--json]` wie beschrieben; JSON-Zeilen über `types.to_json`; Quellenzeile `[n] Titel, version N, p. X` bzw. `pp. X-Y` bzw. Überschriftenpfad; `final:` bei Abweichung; Schlusszeile `status: <status> (k valid citation(s): …; m removed sentence(s))`.
- **Tests:** `backend/tests/answers/test_service.py` und `backend/tests/answers/test_ask.py` (zusammen 83 Fälle) mit `FakeChatModel`, nur selbst geschriebene Texte (erfundener Greifer G-12).
- **`docs/ARCHITECTURE.md`:** Zeile `answers` der Modultabelle ergänzt, Absatz „Answer service“ mit Ablauf, Fehlercodes, Abbruch, Protokoll und `ask` im Abschnitt „The package answers“.

### Wie wurde getestet?

`D` = `docker compose -p twox-126`.

| Nr. | Ergebnis | Nachweis |
| --- | --- | --- |
| 0 | erfüllt | `docker version` 29.9.3, `docker compose version` v5.7.0, je Exit 0 |
| 1 | erfüllt | Build und `up -d --wait` Exit 0 (nach den Code-Commits erneut gebaut und gestartet, Exit 0) |
| 2.1 | erfüllt | `test_supported_answer_gives_sources_deltas_and_done`, Ende zu Ende `test_end_to_end_over_the_real_context_selection` |
| 2.2 | erfüllt | `test_invented_number_is_dropped_and_alone_gives_no_evidence`, `test_invented_number_next_to_a_valid_one_is_removed` |
| 2.3 | erfüllt | `test_refusal_of_the_model_gives_no_evidence` (Absage mit/ohne Punkt, andere Absage, leere Antwort) |
| 2.4 | erfüllt | `test_below_threshold_the_model_is_not_asked` (Fake mit `fail_on_call`, `get_chat_model` schlägt fehl, Netzsperre), dazu `test_end_to_end_below_the_threshold` über die echte Kontextauswahl |
| 2.5 | erfüllt | `test_ai_off_gives_only_ai_disabled` (Spion auf `select_context`, `get_chat_model`, Netzsperre) |
| 2.6 | erfüllt | `test_model_failure_in_the_middle_gives_error_without_done` (nach zwei Stücken, je Fehlerklasse inkl. Zeitgrenze und unerwarteter Ausnahme), `test_failing_call_of_the_model_gives_error`, `test_failing_get_chat_model_gives_error`, `test_chat_errors_map_to_fixed_codes`; kein Ausnahmetext im JSON |
| 2.7 | erfüllt | `test_closing_after_the_first_delta_closes_the_stream` (`ChatStream.closed`, `close_count == 0`), `test_a_model_fetched_by_the_service_is_closed` (`close_count == 1`) |
| 2.8 | erfüllt | `test_logs_hold_no_question_text_title_or_filename` (Erfolg, Absage, Fehler, unerwartete Ausnahme, Abbruch; Wurzel und `twox` auf DEBUG; echte Kontextauswahl mit Titel und Dateiname als Markierung), dazu Zähltest und KI aus |
| 2.9 | erfüllt | `test_ask.py`: `--json` (gültige JSON-Zeilen, Roundtrip über `from_json`, `--seed`), Textausgabe mit Schlusszeile und `final:`, `--device` mit zwei Geräten, KI aus `DISABLED:` Exit 0, Fehler `FAILED: model_rejected` Exit 1, leeres Modell `FAILED: model_unavailable`, leere Frage `CommandError` |
| 2.10 | erfüllt | Ende-zu-Ende-Test mit `CaptureQueriesContext`: kein `INSERT`/`UPDATE`/`DELETE` |
| 2.11 | erfüllt | `test_seed_is_passed_on_and_settings_decide_the_rest` (7 bzw. `None`; `max_tokens`/`temperature` `None`), `test_a_patched_nonce_reaches_build_messages`, `test_each_request_gets_a_fresh_nonce` |
| Zusatz (122) | erfüllt | `test_contradiction_with_two_valid_citations_is_recognised`: `CONTRADICTION_PHRASE` + Doppelpunkt + zwei gültige Zitate ergibt `contradiction` |
| 3 | erfüllt | `pytest tests/answers` 798 passed; `pytest` 3222 passed, 6 deselected, 0 failed, 0 skipped; `pytest -m worker` 6 passed |
| 4 | erfüllt | `ruff check .` „All checks passed!“, `ruff format --check .` Exit 0, `mypy .` „Success: no issues found in 217 source files“ |
| 5 | erfüllt | `makemessages` Exit 0, kein Diff in `backend/locale`; `makemigrations --check --dry-run` „No changes detected“; Lizenzprüfung „License check passed.“; `spectacular` Exit 0, kein Diff in `web/openapi` |
| 6.1 | erfüllt | `D exec -T -e TWOX_AI_ENABLED=false api python manage.py ask "Testfrage"` → `DISABLED: AI features are not enabled (TWOX_AI_ENABLED is false); nothing was searched and the model service was not contacted`, Exit 0 |
| 6.2 | erfüllt | `D exec -T api python manage.py ask "Testfrage"` (leere Datenbank) → `sources: none`, `final:`, `Dazu finde ich nichts in den Unterlagen.`, `status: no_evidence (0 valid citation(s): none; 0 removed sentence(s))`, Exit 0; kein Traceback, keine Adresse. Auf der Fehlerausgabe die Logzeile `Answer: result=no_evidence model=- duration_ms=2924 sources=0 cited=0 removed_sentences=0` |
| 7 | erfüllt | `git diff main --stat`: nur `service.py`, `ask.py`, `test_service.py`, `test_ask.py`, `docs/ARCHITECTURE.md` (+ diese Auftragsdatei); `pyproject.toml`/Lock unverändert |
| 8 | erfüllt | `D --profile dev down -v` Exit 0 |

**Kurzer echter Probelauf (erlaubt laut Leitstelle):** zwei selbst geschriebene Abschnitte zu einem erfundenen Greifer G-12 per `manage.py shell` in die eigene Datenbank, eingebettet mit bge-m3 am Host; `TWOX_CHAT_MODEL=qwen3.8:27b-q4_K_M` nur per `exec -e` (nicht in Dateien). „Wie schwer darf die Last am Greifer G-12 sein?“ → `status: answered`, Zitat [1], 0 entfernte Sätze, rund 26 s. Eine fremde Frage lag unter der Schwelle → `no_evidence` ohne Modellaufruf. Danach `down -v`.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a0d448c0e3e77d448`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a0d448c0e3e77d448` (relativ zum Projektordner)
- Nicht gepusht, nichts zusammengeführt.

### Abweichungen und Hinweise

1. **Leere Frage:** `answer()` ist eine normale Funktion, die bei KI an und leerer Frage sofort `ValueError` wirft und sonst den Generator zurückgibt. So kommt der Fehler schon beim Aufruf (vor dem ersten Ereignis); bei KI aus gilt Schritt 1 (`error(ai_disabled)`), auch für eine leere Frage.
2. **Keine Quelle trotz Schwelle:** Ist `below_threshold` falsch, aber die Auswahl leer (z. B. alles über dem Zeichenbudget), behandelt der Dienst das wie „unter der Schwelle“ (leeres `sources`, `done(no_evidence)`, kein Modellaufruf).
3. **Fehlercodes:** `ChatRemoteModelError` → `model_rejected`; jede andere Ausnahme aus `select_context` (auch nicht aus der Datenbank) → `search_failed`.
4. **`ask` mit `--json`:** Stdout enthält nur JSON-Zeilen; die Zeile `DISABLED:` geht dann auf die Fehlerausgabe (ohne `--json` auf die Standardausgabe, wie `check_llm`). `ask` hat `requires_system_checks = []` (wie `check_llm`), damit W001 nicht jede Ausgabe einleitet. Die Logzeile des Dienstes erscheint im Container auf der Fehlerausgabe (bestehender Handler).
5. **Keine Gesamtzeitgrenze:** Der Docstring von `chat.py` sagt, eine Gesamtzeit setze „der Dienst“. Der Auftrag verbietet neue Einstellungen; der Dienst setzt deshalb keine. Die Lesegrenze zwischen zwei Stücken (`TWOX_CHAT_TIMEOUT_SECONDS`) bleibt der einzige Schutz. Vorschlag: Gesamtgrenze in 130 (API) oder mit eigener Einstellung in einem Folgeauftrag.
6. Der Dienst stützt sich nicht auf die „Limits“ aus `citations.py`; er übernimmt das Urteil unverändert und ersetzt bei `no_evidence` nur Text und Zitate durch die feste Fassung aus `types.py`.
7. Lokal bleiben die Images `twox-126-*`; die ignorierte `.env` hat `TWOX_API_PORT=18126` und ein leeres `TWOX_CHAT_MODEL`.

Offene Fragen an a7: keine.

### Nachbesserung (nach Prüfung der Leitstelle)

1. **Rückgabetyp:** `answer()` liefert `Generator[AnswerEvent, None, None]`, damit Aufrufer (130) `close()` typgerecht aufrufen können. Der Docstring sagt: Wer den Strom nicht zu Ende liest, ruft `close()` (oder nutzt `contextlib.closing`); sonst bleibt der Strom bis zur Speicherbereinigung offen. Die `type: ignore` an `close()` in den Tests sind entfallen.
   - Tests:
     - `test_closing_after_the_first_delta_closes_the_stream` prüft jetzt bei abgeschalteter Speicherbereinigung (`gc.disable()`): `close()` selbst schließt den `ChatStream`.
     - Neu `test_closing_after_the_sources_opens_no_stream`: Der `ChatStream` wird erst nach dem Ereignis `sources` geöffnet. Ein `close()` direkt danach (bei abgeschalteter Speicherbereinigung) hat also keinen Strom zu schließen. Es fragt kein Modell: `stream()` und `get_chat_model()` werden nicht gerufen, und der Generator ist sofort beendet. Ein Strom, der nach `sources` schon offen ist, wird von `close()` sofort geschlossen; das zeigt der Test nach dem ersten `delta`.
     - Neu `test_contextlib_closing_closes_the_stream`.
2. **Fehlercode für fehlende Modelle:** `ChatRejectedError` unterscheidet die Fälle nicht selbst, wohl aber über `__cause__` (aus 121, `chat.py` unverändert):
   - `llm_guard.ModelNotLoadedError` (nicht in `/api/tags`) oder `urllib.error.HTTPError` mit 404 ergeben `model_unavailable`.
   - Ohne diese Ursache gilt `ChatRejectedError` als ausdrückliche Abweisung und ergibt `model_rejected`. Das sind die fehlende Fähigkeit `completion` (ohne Ursache) und andere HTTP-4xx-Fehler.
   - `ChatRemoteModelError` ergibt `model_rejected`.
   - Tests:
     - Die Zuordnungstabelle hat neue Fälle mit Ursache.
     - Neu `test_errors_of_the_real_chat_client_map_to_their_codes` mit dem echten `OpenAICompatibleChat` gegen `fake_ollama`. Nicht geladen und HTTP 404 ergeben `model_unavailable`. HTTP 400, Einbettungsmodell und Cloud-Modell ergeben `model_rejected`.
   - Docstring und `docs/ARCHITECTURE.md` sind angepasst. Abweichung 3 oben gilt entsprechend.
3. **Prüfungen (twox-126):**
   - `ruff check .`, `ruff format --check .` und `mypy .` sind grün.
   - `pytest`: 3241 passed, 6 deselected, 0 fehlgeschlagen, 0 übersprungen. `pytest -m worker`: 6 passed.
   - `makemessages` und `spectacular` ohne Unterschied; „No changes detected“; „License check passed.“
   - `ask "Testfrage"` im `api`-Container: `status: no_evidence …`, Exit 0.
   - `down -v` Exit 0.
