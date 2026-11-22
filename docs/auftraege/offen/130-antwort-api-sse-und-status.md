# Auftrag 130 – Antwort-API mit SSE und Status

Meilenstein: M3 · Freigabestufe: C · Status: offen

Voraussetzung: 126 (Antwortdienst `answer()` und Befehl `ask`) und 129 (Modellprüfung für Selbsttest und `check_llm --chat`) sind auf `main`; damit auch 121 (`get_chat_model()`, `TWOX_CHAT_*`), 122 (`types.py`, Ereignisvertrag) und 123/125. Start erst nach Entscheidung von D7 und D14 durch a7 (siehe unten).

## Ziel

Die Auskunft wird über HTTP erreichbar, damit die Oberfläche (131–133) sie nutzen kann:

- `POST /api/v1/answers/` nimmt eine Frage an und streamt den Ereignisstrom des Antwortdienstes (`sources` → `delta`* → `done`, oder `error`) als Server-Sent Events. Das ist der „Antwort-Stream“ aus der Technik-Tabelle zu E-03 (`docs/DECISIONS.md:95`).
- `GET /api/v1/answers/status/` meldet vorab, ob die Auskunft verfügbar ist, damit die Seite bei ausgeschalteter KI (E-59) einen ruhigen Hinweis zeigen kann, statt erst nach dem Absenden zu scheitern.

Beides ist zustandslos: Es wird nichts gespeichert (D7), es kommt keine neue Abhängigkeit hinzu, und Frage, Antwort und Abschnittstexte erscheinen in keinem Protokoll.

## Umfang

### 1. Antwort-Endpunkt `POST /api/v1/answers/` (`backend/twox/answers/api.py`, neu)

- **Ansicht:** synchrone DRF-`APIView` (`AnswerView`) mit `permission_classes = (CanRead,)` (E-40), Authentifizierung über die Standardeinstellung `SessionAuthentication` und damit CSRF-Prüfung bei jedem POST (E-38, `backend/twox/config/settings.py:241-252`). Rechte, CSRF, Throttle und Eingabeprüfung laufen damit vor dem Stream im gewohnten DRF-Ablauf; erst danach beginnt der Stream. Die Ansicht selbst bleibt synchron, der Stream ist asynchron (Option A): Das erfüllt E-03 („asynchrone Django-Ansicht mit SSE“) beim Senden, ohne DRF-Rechte und -Throttle selbst nachzubauen.
- **Eingabe** (`AnswerRequestSerializer`, JSON-Body):
  - `question`: Text, nach Trimmen 1 bis 500 Zeichen (`MAX_QUESTION_CHARS: Final = 500`, gleiche Grenze wie `MAX_QUERY_CHARS` in `backend/twox/search/api.py:50`).
  - `device` und `plant`: optionale Listen von Ids (je höchstens 100), Prüfung wie `_id_list` in `backend/twox/search/api.py:58-65` (wiederverwenden oder gleich gebaut, `MAX_ID` aus `twox.assets.views`). Sie werden an `answer(question, device_ids=…, plant_ids=…)` aus 126 durchgereicht.
  - Die Frage steht nur im Body, nie in der Adresse.
- **Antwort bei Erfolg:** `StreamingHttpResponse` mit einem async-Generator nach dem Muster `BlobDownloadResponse.__aiter__` in `backend/twox/files/downloads.py:85-97`: Der synchrone Iterator aus `answer()` wird Ereignis für Ereignis mit `sync_to_async(..., thread_sensitive=False)` gelesen, damit kein Modell-Token den Event-Loop blockiert und Django den Strom unter ASGI nicht vorher einsammelt.
  - **Datenbankverbindungen:** Anders als in `downloads.py`, wo nur Dateiblöcke gelesen werden, führt `answer()` beim ersten `next()` die Kontextauswahl mit Datenbankabfragen aus (125, Abschnitt „Datenbankzugriffe“). Mit `thread_sensitive=False` liefen diese in einem beliebigen Thread des Pools; dessen Verbindung schließt Django nicht über `request_finished` (kein `CONN_MAX_AGE` in `backend/twox/config/settings.py`, also Standard 0). Deshalb gilt eine der beiden Formen, der Bearbeiter wählt und begründet im Kurzbericht: (a) das erste Ereignis (`sources`, Kontextauswahl) wird mit `sync_to_async(..., thread_sensitive=True)` gelesen, erst die folgenden Ereignisse (Modell-Tokens, ohne Datenbank) mit `thread_sensitive=False`; oder (b) die Hilfsfunktion im Worker-Thread ruft nach dem Lesen `close_old_connections()` auf bzw. schließt die Verbindung dieses Threads in `finally`. Greift `answer()` nach dem ersten Ereignis noch auf die Datenbank zu, gilt (b) oder die Abweichung steht im Kurzbericht.
  - Header: `Content-Type: text/event-stream; charset=utf-8`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`, `X-Content-Type-Options: nosniff`.
  - Format je Ereignis: `event: <typ>\ndata: <JSON>\n\n`, `<typ>` ∈ `sources`, `delta`, `done`, `error`. Das JSON ist die Serialisierung der Typen aus `backend/twox/answers/types.py` (122) und trägt zusätzlich das Feld `type` mit demselben Wert. Kein `id:`, kein `retry:` (der Client stellt nie automatisch neu, 131).
  - `sources` trägt je Quelle die Nummer `n` und die Angaben für die Quellenanzeige: `section_id`, `page_start`, `page_end`, `heading_path`, `snippet` und `locations` in derselben Form wie ein Suchtreffer (`hit_data` in `backend/twox/search/api.py:173-198`, wiederverwenden). Der volle Abschnittstext (`ContextSource.text`) wird **nicht** an den Browser geschickt; die Oberfläche zeigt einen Ausschnitt wie die Suche. Wie der Ausschnitt entsteht (Snippet aus der Suche oder gekürzter Text), legt der Bearbeiter fest und begründet es im Kurzbericht; höchstens etwa 300 Zeichen wie bei der Suche.
  - `done` trägt `status` (`answered` | `no_evidence` | `contradiction`), `cited`, `removed_sentences` (Anzahl als Zahl, wie in 122 festgelegt) und `final_text`.
  - `error` trägt nur `code` aus der festen Liste von 122 (z. B. `model_unavailable`, `timeout`) und eine kurze, übersetzte `detail`. Nie Rohtext des Modells, nie Adresse, nie Prompt.
- **Abbruch:** Bricht der Browser ab, wirft der Generator `asyncio.CancelledError` bzw. wird mit `aclose()` beendet. In `finally` wird der Iterator aus `answer()` geschlossen (`close()`), damit 126 den Modellstrom schließt (Akzeptanz 7 in 126), und die Sperre (unten) freigegeben.
- **Fehler vor Beginn des Streams** als normales JSON, wie es der übrige API-Client erwartet (`web/src/api/errors.ts:63-74` liest `detail`):
  - 400: ungültige Eingabe, DRF-Standard mit Fehler am Feld (wie die Suche, `docs/ARCHITECTURE.md:379`).
  - 403: ohne Rolle, ohne Anmeldung oder ohne CSRF-Token (`{"detail": …}`).
  - 409 `{"detail": …, "code": "ai_disabled"}`: `TWOX_AI_ENABLED` ist aus (D10, Vorgabe (a)). Kein Modellaufruf, keine Netzverbindung, keine Suche.
  - 409 `{"detail": …, "code": "answer_in_progress"}`: Für diesen Benutzer läuft schon eine Antwort.
  - 429: Throttle überschritten (DRF-Standard mit `detail`).
  - 503 `{"detail": …, "code": "chat_not_configured"}`: KI an, aber `TWOX_CHAT_MODEL` leer (bis D1 der Normalfall in der Testumgebung, vgl. Systemwarnung aus 121). Ohne Netzverbindung festgestellt.
  - Ein Modellausfall nach Beginn des Streams kommt als `error`-Ereignis aus dem Dienst (126), nicht als HTTP-Status.
  - Fehlerklassen mit `detail` und `code` nach dem Muster `IngestConflictSerializer` (`backend/twox/ingest/api.py:139-151`); Codes als `Final`-Konstanten wie `CODE_INGEST_ACTIVE` (`backend/twox/ingest/api.py:64`). Texte englisch im Code, mit `gettext` markiert; deutsche Übersetzung im Katalog `backend/locale/de/` (CI prüft `makemessages`, `.github/workflows/ci.yml:67-71`).

### 2. Throttle und Sperre

- `ScopedRateThrottle` nur an dieser Ansicht (`throttle_scope = "answers"`), nicht global. In `REST_FRAMEWORK` (`backend/twox/config/settings.py:241`) kommt nur `DEFAULT_THROTTLE_RATES = {"answers": TWOX_ANSWER_RATE}` hinzu; es wird **keine** `DEFAULT_THROTTLE_CLASSES` gesetzt, damit kein anderer Endpunkt betroffen ist. DRF rechnet bei angemeldeten Benutzern je Benutzer-Id, nicht je IP-Adresse (die Adresse wird nicht protokolliert, E-62). Die Zähler liegen im gemeinsamen Cache (Valkey, `backend/twox/config/settings.py:234-239`).
- `TWOX_ANSWER_RATE`: Standard `10/min` (Festlegung der Leitstelle). Begründung: Eine Antwort dauert mit einem lokalen Modell mehrere Sekunden bis Minuten, mehr als eine läuft je Benutzer ohnehin nicht (Sperre); 10 je Minute lässt schnelles Nachfragen nach einer Absage oder einem Abbruch zu und begrenzt Skripte, die die GPU für alle anderen blockieren. Neue Einstellung in `settings.py` (Format wie DRF-Raten, ungültiger Wert ergibt beim Start `ImproperlyConfigured`), `deploy/compose/compose.yaml` (Block `x-backend-environment`, Z. 4-34, nur diese eine Zeile) und `.env.example` (nur diese eine Zeile, mit Kommentar).
- **Höchstens eine laufende Antwort je Benutzer:** Sperre im Cache mit `cache.add(f"twox:answers:active:{user.pk}", 1, timeout=ANSWER_LOCK_SECONDS)` vor Beginn des Streams; scheitert `add`, folgt 409 `answer_in_progress`. Freigabe in `finally` des Generators (Ende, Fehler, Abbruch). `ANSWER_LOCK_SECONDS` als Konstante, größer als die längste erwartbare Antwort (Vorschlag 600 s), damit eine verwaiste Sperre nach einem Prozessabsturz von selbst verfällt. Die Zahl in ARCHITECTURE nennen.

### 3. Status-Endpunkt `GET /api/v1/answers/status/`

- `AnswerStatusView`, `CanRead`, liefert `{"enabled": bool, "chat_model_configured": bool, "available": bool}` (Serializer `AnswerStatusSerializer`), sonst nichts: keine Adresse, kein Modellname, keine Fehlermeldung des Modelldienstes.
- `enabled` = `TWOX_AI_ENABLED`; `chat_model_configured` = `TWOX_CHAT_MODEL` nicht leer. `available` = beide wahr **und** die Modellprüfung aus 129 (nur `/api/tags`: Modell vorhanden, Fähigkeit „completion“, kein Cloud-Modell; keine Erzeugung) ist bestanden.
- Bei `enabled=false` oder leerem Modell wird keine Verbindung aufgebaut.
- Das Ergebnis der Modellprüfung wird kurz im Cache gehalten (Konstante, Vorschlag 30 s, Schlüssel ohne Benutzerbezug), damit das Öffnen der Seite durch viele Benutzer den Modelldienst nicht belastet.
- D14 Vorgabe (a): eigener Endpunkt, `/api/v1/me/` bleibt unverändert (Anmeldung und Rechte unberührt).

### 4. URLs

- `backend/twox/answers/urls.py` (neu) mit `answers/` und `answers/status/`; Einbindung in `backend/twox/config/urls.py:48-53` als weitere Zeile `path("api/v1/", include("twox.answers.urls"))`.
- `backend/tests/config/expected_paths/answers.py` (neu) mit `EXPECTED_PATHS = ["/api/v1/answers/", "/api/v1/answers/status/"]`, eingetragen in `backend/tests/config/expected_paths/__init__.py`. `backend/tests/config/test_api.py` selbst bleibt unverändert; beide Pfade sind keine Ausnahme von E-40 (keine Änderung an `OPEN_PATHS`/`ROLELESS_PATHS`).

### 5. OpenAPI-Schema und generierter Client

- `@extend_schema` mit `operation_id="answer"` bzw. `"answer_status"`. Die Erfolgsantwort von `POST` wird als `text/event-stream` beschrieben, z. B. `responses={(200, "text/event-stream"): PolymorphicProxySerializer(component_name="AnswerEvent", serializers=[…], resource_type_field_name="type")}` mit je einem Serializer pro Ereignis (`AnswerSourcesEvent`, `AnswerDeltaEvent`, `AnswerDoneEvent`, `AnswerErrorEvent`), damit 131 die Ereignistypen aus dem Schema ableiten kann. Dazu die Fehlerantworten 400, 403, 409, 429, 503 mit ihren Serializern. Ob drf-spectacular die Form sauber erzeugt, prüft der Bearbeiter; falls nicht, die nächstbeste Form wählen und im Kurzbericht begründen. `manage.py spectacular --validate` ohne Warnung (`backend/tests/config/test_api.py:215-221`).
- `web/openapi/schema.yml` und `web/src/api/generated/**` neu erzeugen (`web/openapi/README.md`). Nur erzeugte Dateien unter `web/`; keine handgeschriebene Oberfläche (das ist 131).

### 6. Protokoll

- Die Ansicht protokolliert nur, was der Dienst aus 126 ohnehin protokolliert (Fehlerart, Modellname, Dauer, Zahl der Quellen), höchstens ergänzt um den Ausgang (`answered`, `no_evidence`, `contradiction`, `error`, `cancelled`). Nie Frage, Antwort, Abschnittstext, Benutzername oder Ids der Eingrenzung.
- Das Zugriffsprotokoll von uvicorn enthält für POST ohnehin nur Methode, Pfad und Status (Filter aus 052/069, `docs/ARCHITECTURE.md:515-516`); der Body wird nie protokolliert. Ein Test belegt das (Akzeptanz 8).

### 7. Doku

- `docs/ARCHITECTURE.md`:
  - Tabelle „Django apps“, Zeile `answers` (Z. 134): `api.py`, `urls.py`, Endpunkte nennen.
  - Tabelle „Roles and API permissions“ (Z. 366-380): zwei Zeilen für die neuen Endpunkte mit Eingabe, Statuscodes und Codes.
  - Abschnitt „API and the generated client“ (Z. 504-510): ein Punkt zu SSE (Format, Header, kein automatischer Neuversuch, Fehler vor dem Stream als JSON).
  - Abschnitt „Logging“ (Z. 512-517): ein Punkt „Questions and answers are not logged“.
- `README.md`: neuer Unterabschnitt „Answers“ nach „Search“ (Z. 219-236) mit Endpunkt, Beispiel mit `curl -N` (nur mit Platzhaltern, ohne Zugangsdaten), Verhalten bei KI aus; in „Security notes“ (Z. 471-502) ein Punkt „Questions and answers“ (nicht gespeichert, nicht protokolliert, gehen an `TWOX_LLM_BASE_URL`) und Ergänzung von „Roles“ (Z. 481-486: `read` darf Fragen stellen) und „Model server“ (Z. 496: auch Fragen und die ausgewählten Abschnitte gehen an den Modellserver).

## Nicht-Ziele

- Keine Oberfläche, kein Hook, keine handgeschriebenen Dateien unter `web/src/` (131–134).
- Keine Speicherung von Fragen, Antworten, Verlauf oder Bewertungen; kein Datenmodell, keine Migration (D7).
- Keine Änderung an Antwortdienst, Kontextauswahl, Prompt, Zitatprüfung oder Chat-Client (121–126). Fehlt dort etwas, als Abweichung im Kurzbericht melden statt selbst zu ändern.
- Keine Änderung an der Suche (`backend/twox/search/`), an `/api/v1/me/` oder an Anmeldung und Rechten.
- Kein WebSocket, kein Django Channels, keine globale Throttle-Klasse, kein Throttle je IP-Adresse.
- Keine neue Abhängigkeit (weder Python noch npm, auch kein pytest-asyncio).
- Keine Messung mit echtem Modell (128).

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/answers/api.py` (neu)
- `backend/twox/answers/urls.py` (neu)
- `backend/twox/config/urls.py` (eine Zeile `include`)
- `backend/twox/config/settings.py` (nur `DEFAULT_THROTTLE_RATES` in `REST_FRAMEWORK` und `TWOX_ANSWER_RATE`)
- `deploy/compose/compose.yaml` (nur `TWOX_ANSWER_RATE` im Block `x-backend-environment`)
- `.env.example` (nur `TWOX_ANSWER_RATE`)
- `backend/locale/de/LC_MESSAGES/django.po` (neue Meldungen, erzeugt mit `makemessages`)
- `backend/tests/answers/test_api.py` (neu)
- `backend/tests/config/expected_paths/answers.py` (neu), `backend/tests/config/expected_paths/__init__.py` (eine Zeile)
- `web/openapi/schema.yml`, `web/src/api/generated/**` (nur neu erzeugt)
- `README.md` (Abschnitte „Answers“ neu, „Security notes“)
- `docs/ARCHITECTURE.md` (Abschnitte wie oben)

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Alle Prüfungen der Jobs `backend` und `web` aus `.github/workflows/ci.yml` sind grün: ruff check, ruff format --check, mypy, `pytest`, `pytest -m worker`, Übersetzungskatalog aktuell, `makemigrations --check --dry-run` (keine Migration), Lizenzprüfung, OpenAPI-Schema ohne Diff; im Web-Job lint, typecheck, test, build, licenses und „API client up to date“. Der Job `e2e` bleibt grün.
2. `backend/tests/config/test_api.py` ist unverändert und grün; die neuen Pfade stehen in `expected_paths/answers.py`, beide antworten anonym und ohne Rolle mit 403.
3. Tests (`backend/tests/answers/test_api.py`): ohne Rolle 403; mit Rolle `read`, aber ohne CSRF-Token (`APIClient(enforce_csrf_checks=True)`, Muster `backend/tests/config/test_api.py:271-289`) 403; leere und zu lange Frage (501 Zeichen) 400 mit Fehler am Feld `question`; zu viele Ids 400. Die Rolle `read` erhält 200.
4. Mit `FakeChatModel` (121) und einem Stub für Kontextauswahl bzw. Suche (wie in den Tests von 126): Die Antwort hat `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`; der Strom liefert genau `sources`, dann mindestens ein `delta`, dann `done`, jedes Ereignis im Format `event:`/`data:` mit gültigem JSON und passendem `type`. Getestet über den asynchronen Weg (`AsyncClient` oder die ASGI-Anwendung, mit `asyncio.run` wie in `backend/tests/files/test_downloads.py:85` und `backend/tests/config/test_asgi.py:60`) **und** über den synchronen Test-Client.
5. `no_evidence` (unter der Schwelle) ergibt `sources` mit leerer Liste und `done` mit `status: "no_evidence"`, `cited: []` und dem festen Satz; das Modell wird nicht gerufen (Fake schlägt bei Aufruf fehl).
6. `sources` enthält keinen vollen Abschnittstext: Ein Test mit einem Abschnitt deutlich länger als der Ausschnitt zeigt, dass der Text hinter dem Ausschnitt nicht im Strom steht.
7. Throttle: Mit einer kleinen Rate (per `override_settings`, eigener Cache je Test oder Cache vor dem Test geleert) ergibt die Anfrage über der Grenze 429; ein zweiter Benutzer ist davon nicht betroffen (je Benutzer, nicht je IP). Eine zweite gleichzeitige Anfrage desselben Benutzers (Sperre gesetzt) ergibt 409 `answer_in_progress`; nach Ende oder Abbruch der ersten ist die Sperre frei.
8. KI aus (`TWOX_AI_ENABLED=0`): `POST` ergibt 409 `ai_disabled`, `GET …/status/` ergibt `{"enabled": false, "chat_model_configured": …, "available": false}`, beides mit Socket-Sperre (kein Verbindungsaufbau, Muster aus 121) und ohne Aufruf von Suche oder Modell. KI an und `TWOX_CHAT_MODEL` leer: `POST` 503 `chat_not_configured`, Status `available: false`, ebenfalls ohne Verbindung. KI an und Modellprüfung bestanden (Prüfung aus 129 gestubbt): `available: true`; ein zweiter Aufruf innerhalb der Cache-Zeit ruft die Prüfung nicht erneut.
9. Abbruch: Wird der async-Strom nach dem ersten `delta` geschlossen (`aclose()` bzw. `CancelledError`), ist `close()` am Fake aufgerufen und die Sperre freigegeben (Test).
9a. Datenbankverbindungen: Ein Test über den async-Weg mit nicht gestubbter Kontextauswahl (`@pytest.mark.django_db(transaction=True)`) zeigt, dass nach Ende und nach Abbruch des Stroms keine Verbindung aus einem Worker-Thread offen bleibt (z. B. Zahl der Sitzungen in `pg_stat_activity` für die Test-Datenbank vor und nach mehreren Läufen gleich, oder Prüfung, dass die im Worker-Thread genutzte `connection` geschlossen ist).
10. Ein Modellausfall mitten im Strom ergibt ein `error`-Ereignis mit Code aus der festen Liste, ohne Rohtext, ohne Adresse (Test).
11. Log-Test mit `caplog` auf dem Wurzel-Logger (alle Logger, Stufe DEBUG), einschließlich einer über den konfigurierten Logger `uvicorn.access` geschickten Zugriffszeile wie in `backend/tests/config/test_logging.py` (Auftrag 069): Eine markante Frage, die Fake-Antwort und ein markanter Abschnittstext stehen in keiner Logzeile, auch nicht bei 400, 409 und Modellausfall.
12. Schema: `web/openapi/schema.yml` enthält `/api/v1/answers/` mit Antwort `text/event-stream` und `/api/v1/answers/status/`; `manage.py spectacular --validate` ohne Warnung; `web/src/api/generated/**` ist neu erzeugt, `npm run typecheck` grün. Der Kurzbericht nennt, welche SDK-Funktion hey-api für den Stream erzeugt hat (Grundlage für 131).
13. Im eigenen Compose-Projekt mit KI aus: angemeldet mit dem Testkonto aus `.env.example`, `GET /api/v1/answers/status/` und `POST /api/v1/answers/` (mit CSRF-Token) zeigen `enabled: false` bzw. 409 `ai_disabled`; `docker compose logs api` enthält die Frage nicht (Ausgabe gekürzt im Kurzbericht). `down -v` des eigenen Projekts endet mit Exit 0. Falls die Testumgebung mit KI an und Chat-Modell schon bereitsteht (nach D1), zusätzlich `curl -N` mit einer selbst formulierten Frage: Ereignisse kommen fortlaufend, nicht gesammelt am Ende (nur Ereignistypen und Zeiten im Bericht, keine Antworttexte). Sonst als „nicht geprüft, wartet auf D1“ vermerken.
14. Keine neue Abhängigkeit: `backend/uv.lock` und `web/package-lock.json` unverändert.

## Vorgaben und Hinweise

- **Leitplanken:** Antworten nur mit Quelle – die Prüfung macht 123/126, die API reicht das Urteil aus `done` unverändert weiter und erfindet keinen eigenen Text. Dokumentinhalte sind Daten: Der Strom wird als `text/event-stream` gesendet, nie als HTML; die Oberfläche rendert nur Text (131/132). Betrieb ohne Internet: keine externen Aufrufe außer über `get_chat_model()` an `TWOX_LLM_BASE_URL`. Keine Telemetrie.
- **E-40:** jeder Endpunkt `CanRead`, keine neue Ausnahme. **E-38:** Sitzung und CSRF, keine Tokens im Browser. **E-59:** KI optional; aus heißt keine Verbindung. **E-57/E-62:** keine Suchtexte und keine Client-Adressen im Protokoll; dasselbe gilt jetzt für Fragen und Antworten. **E-03:** Antwort-Stream per SSE, API zustandslos.
- **Muster für den Stream:** `backend/twox/files/downloads.py:64-97` (async `__aiter__`, `sync_to_async(..., thread_sensitive=False)`), für Datenbankzugriffe ergänzt wie unter „Datenbankverbindungen“ in Abschnitt 1. Alle Middlewares in `settings.py:114-131` sind synchron; Django passt sie unter ASGI an, der Strom wird trotzdem fortlaufend gesendet. `RequestBodyLimitMiddleware` (`backend/twox/config/asgi.py:12-16`) betrifft nur den Request-Body.
- **Tests asynchron ohne neue Abhängigkeit:** Es gibt kein pytest-asyncio im Projekt; async-Code wird mit `asyncio.run(...)` getrieben (Fundstellen oben). Datenbankzugriffe aus dem async-Weg brauchen `@pytest.mark.django_db(transaction=True)`, falls die Kontextauswahl nicht gestubbt ist.
- **Cache in Tests:** Throttle und Sperre nutzen den Django-Cache (in CI Valkey). Tests setzen für sich einen `LocMemCache` per `override_settings` oder leeren die eigenen Schlüssel, damit sie nicht voneinander abhängen.
- **Fehlerformat im Client:** `web/src/api/errors.ts:63-74` liest nur `detail`; `code` kommt zusätzlich mit, wie bei `ingest_active` (`backend/twox/ingest/api.py:146-151`). Die Auswertung im Browser (eigener Zustand für `ai_disabled`) baut 131.
- **Zusammenspiel mit 129:** Für `available` die Prüffunktion aus 129 aufrufen, nicht nachbauen. Fehlt eine öffentliche Funktion dafür, im Kurzbericht melden.
- **Parallel laufende Aufträge:** 127 (`answers/evaluation.py`, eigener Befehl) und 135 (`answers/replay.py`, `record_answers`, `tests/answers/test_ci_questions.py`) laufen gleichzeitig und berühren keine Datei dieses Auftrags. `README.md` und `docs/ARCHITECTURE.md` ändert 135 im Testabschnitt – nur die oben genannten Abschnitte anfassen, die Leitstelle führt zusammen. `settings.py`, `compose.yaml` und `.env.example` haben 121 und 125 vorher geändert; nur die eigene Zeile ergänzen.
- **Schwärzen:** Handbücher enthalten öffentliche Standard-Zugangsdaten; die API filtert sie nicht (D15, bekannte Grenze bis M5).
- **Testtexte selbst schreiben**, keine Auszüge aus Handbüchern der Testfabrik; keine Personennamen, keine echten Adressen (Beispieladressen aus RFC 5737, z. B. `192.0.2.10`).
- Startunterlage: Leitplanken Abschnitt 2, Technik Abschnitt 5, Meilensteine Abschnitt 9 (nur lokal, nicht zitieren).

## Fragen an a7 (mit Optionen und Empfehlung)

**D7 Speichern und Protokollieren von Fragen und Antworten (126, 130)**

- (a) Nichts speichern: Die Auskunft ist zustandslos, ein Verlauf lebt nur im Browser. Protokolliert werden nur Fehlerart, Modell, Dauer und Zahl der Quellen.
- (b) Verlauf je Benutzer in der Datenbank mit Frist und Löschen; das bringt ein neues Datenmodell und die Frage, ob `manage` fremde Fragen sieht.
- (c) Anonyme Qualitätsdaten wie Daumen hoch oder runter.

Empfehlung: (a) für M3, abgesichert durch Log-Tests in 126 und 130. Das passt zu E-62 und vermeidet das Problem instabiler `section_id`: Neues Einlesen legt Abschnitte neu an (`backend/twox/ingest/pipeline.py:723-724`), und `PROTECT` würde Fremdschlüssel blockieren. (b) oder (c) später als eigener Auftrag.

**D14 Details der Oberfläche (130, 132, 133, 134) – für diesen Auftrag nur der Status-Endpunkt**

- (a) Eigener Endpunkt `/api/v1/answers/status/`.
- (b) Feld in `/api/v1/me/`, das das Konto berührt.

Empfehlung: (a). Anmeldung und Rechte bleiben unberührt. Die übrigen Punkte von D14 (Eingrenzung auf Gerät und Anlage, Sprung zur PDF-Seite später, Icon vorerst Lucide, `?q=` nur vorbelegen) betreffen 132–134; die API nimmt `device` und `plant` in jedem Fall an.

Den Grenzwert des Throttles (`TWOX_ANSWER_RATE`, 10/min) hat die Leitstelle festgelegt; er ist über `.env` änderbar.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
