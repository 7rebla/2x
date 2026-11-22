# Auftrag 131 – Oberfläche: Antwortstrom und Hook

Meilenstein: M3 · Freigabestufe: B · Status: zur Prüfung

Voraussetzung: 130 (Antwort-API mit SSE und Status) ist auf `main`; `web/openapi/schema.yml` und `web/src/api/generated/**` enthalten damit `POST /api/v1/answers/` (Antwort `text/event-stream`) und `GET /api/v1/answers/status/`. Den Ereignisvertrag (Typen `sources`, `delta`, `done`, `error`, Statuswerte, Fehlercodes) legt 122 fest; er steht in `docs/ARCHITECTURE.md`, Abschnitt `answers`.

## Ziel

Die Oberfläche bekommt eine dünne, getestete Client-Schicht für den Antwortstrom der Auskunft (M3 „Frage und Antwort, Quellenanzeige“). Der Strom kommt per POST als Server-Sent Events. Die Schicht

- schickt die Frage mit denselben Kopfzeilen wie jeder andere Aufruf (CSRF, Accept-Language; E-38),
- behandelt Fehler wie der übrige API-Client (`ApiError`, 403 an `reportForbidden`),
- stellt eine Frage **nie automatisch erneut** (ein zweiter Aufruf würde das Modell noch einmal rechnen lassen und eine andere Antwort liefern),
- lässt sich jederzeit abbrechen, auch beim Verlassen der Seite,
- liefert der Seite (Auftrag 132) einen Zustand, den sie nur noch darstellen muss.

Ohne neue Abhängigkeit (Leitplanke 7, E-59: KI ist optional; die Oberfläche muss auch bei ausgeschalteter KI sauber reagieren).

## Umfang

1. **Prüfen, was der Generator liefert.** Nach 130 prüfen, ob `@hey-api/openapi-ts` 0.99 (`web/package.json`, `web/openapi-ts.config.ts`) für den `text/event-stream`-Endpunkt eine eigene SDK-Funktion in `web/src/api/generated/sdk.gen.ts` erzeugt (z. B. mit `client.sse.post`). Wenn ja, diese nutzen; wenn nein, `client.sse.post` aus `web/src/api/generated/client/client.gen.ts:228-246` (Methoden-Tabelle `sse` ab Z. 264) direkt mit `url: "/api/v1/answers/"` aufrufen. Ergebnis und Begründung kommen in den Kurzbericht. Generierte Dateien werden **nicht** von Hand geändert.

2. **`web/src/api/answers.ts` (neu)** mit einer Funktion, etwa
   `streamAnswer(request: AnswerRequest, options: { signal: AbortSignal; onEvent: (event: AnswerEvent) => void }): Promise<AnswerStreamOutcome>`.
   - Ruft den SSE-Client immer mit `sseMaxRetryAttempts: 1` und dem übergebenen `signal` auf. Kein Wiederholen, kein `Last-Event-ID`.
   - Übergibt eine **eigene `fetch`-Hülle** über die Option `fetch` (wird in `serverSentEvents.gen.ts:132` verwendet). Sie ist nötig, weil beim SSE-Client nur die Request-Interceptoren laufen (`client.gen.ts:236`), nicht aber die Response- und Error-Interceptoren aus `client.ts:93-106` und `errors.ts:93`. Die Hülle
     - ruft den echten `fetch` auf,
     - ruft `reportForbidden(response, request)` (`web/src/api/client.ts:79`) für jede Antwort auf,
     - liest bei einem Status außerhalb 2xx den Body **bevor** der generierte Code ihn mit der nackten Meldung `SSE failed: …` verwirft (`serverSentEvents.gen.ts:135`). Daraus entsteht ein `ApiError("http", status, detail)` nach denselben Regeln wie `toApiError`/`errorDetail` (`web/src/api/errors.ts:42-79`; DRF `detail`, Klartext nur bei `text/plain`, gekürzt auf `MAX_DETAIL_LENGTH`). Dazu wird das Feld `code` aus dem JSON-Body gelesen (Format `{detail, code}` wie `IngestRequestError` in `web/openapi/schema.yml`), damit 409 `ai_disabled` erkannt wird. `errors.ts` selbst bleibt unverändert; wenn eine kleine Hilfsfunktion aus `errors.ts` exportiert werden müsste, lieber lokal nachbauen und im Kurzbericht begründen.
     - Netzfehler (kein Response) werden zu `ApiError("network", null, null)`, ein 2xx ohne `text/event-stream` zu `ApiError("invalid-answer", …)`.
   - **Achtung Generatorverhalten:** Ein Fehler im Stream wird in `serverSentEvents.gen.ts:224-230` nur an `onSseError` gegeben; danach endet der Generator **ohne** Ausnahme. `answers.ts` muss den Fehler deshalb über `onSseError` festhalten und nach dem Ende der Schleife auswerten.
   - Jedes `data:`-Ereignis wird geprüft (Typ-Wächter in `events.ts`, siehe 3) und an `onEvent` gegeben. Ein Ereignis, das nicht dem Vertrag entspricht, beendet den Strom mit `invalid-answer` (kein stilles Weiterlaufen).
   - Endet der Strom ohne `done`- oder `error`-Ereignis (Verbindung weg, Server-Abbruch), ist das Ergebnis „unterbrochen“, nicht „fertig“.
   - Ein Abbruch über `signal` ist kein Fehler: Ergebnis „abgebrochen“, keine Fehlermeldung, kein weiterer `fetch`.
   - Rückgabe als unterscheidbare Vereinigung, z. B. `{ kind: "completed" } | { kind: "aborted" } | { kind: "interrupted" } | { kind: "ai-disabled" } | { kind: "failed"; error: ApiError }` (Namen frei, aber im Kurzbericht genannt).
   - Die Frage steht nur im POST-Body, nie in der Adresse (Datenschutz; die Eingrenzung per `?device=`/`?plant=` regelt 133).

3. **`web/src/pages/answer/events.ts` (neu):** Typen der Ereignisse nach dem Schema aus 130/122, möglichst aus `web/src/api/generated/types.gen.ts` abgeleitet; was das Schema für `text/event-stream` nicht abbildet, wird hier von Hand und eng am Vertrag in `docs/ARCHITECTURE.md` beschrieben. Dazu eine reine Funktion `parseAnswerEvent(data: unknown): AnswerEvent | null` als Laufzeit-Wächter (Felder und Typen prüfen, unbekannte `status`- oder Fehlercodes ablehnen). Kein `any`.

4. **Status-Query:** In `answers.ts` eine Hilfe für `GET /api/v1/answers/status/` über die vom Generator erzeugten TanStack-Query-Optionen (`web/src/api/generated/@tanstack/react-query.gen.ts`), z. B. `answersStatusQueryOptions()` mit kurzer `staleTime` (der Server speichert den Status selbst kurz zwischen, siehe 130). Sie meldet `enabled`, `chat_model_configured`, `available`. Die Seite (132) entscheidet damit, ob das Formular gesperrt ist; 131 baut keine Oberfläche.

5. **`web/src/pages/answer/useAnswerStream.ts` (neu):** Hook mit `useReducer`, Zustände `idle | streaming | done | error`:
   - `ask(request)`: nur aus `idle`, `done` oder `error` erlaubt; während `streaming` wird ein zweiter Aufruf ignoriert (kein paralleler Strom; der Server erlaubt ohnehin nur eine laufende Antwort je Benutzer, 130).
   - `sources` übernimmt die Quellenliste, `delta` hängt Text an, `done` übernimmt Status (`answered | no_evidence | contradiction`), gültige Zitate, `removed_sentences` und **ersetzt den gestreamten Text durch `final_text`** (D9 (a)), `error`-Ereignis führt in `error` mit dem festen Code.
   - Im Zustand `error` ist die Ursache unterscheidbar: `ai-disabled` (409 `ai_disabled` vor dem Strom oder `error`-Ereignis mit Code `ai_disabled`), `forbidden` (403), `http` mit `ApiError` (z. B. 400 mit Text), `network`, `invalid-answer`, `interrupted`, `stream` mit Ereigniscode (z. B. `model_unavailable`, `timeout`).
   - `cancel()`: bricht über `AbortController` ab, Zustand zurück auf `idle` oder ein eigener Endzustand „abgebrochen“ (Wahl im Kurzbericht begründen); Text bis dahin darf bleiben, gilt aber nicht als geprüfte Antwort.
   - Beim Unmount wird ein laufender Strom abgebrochen; nach dem Unmount wird kein `dispatch` mehr ausgeführt.
   - Der Antworttext bleibt ein **reiner String**: kein HTML, kein Markdown-Rendering, keine Umwandlung von `[n]` (das macht 132 beim Darstellen als Text).
   - Der Reducer ist als reine Funktion exportiert und für sich testbar.

6. **Tests (Vitest, jsdom)** mit einem `fetch`-Stub, der eine `Response` mit `ReadableStream`-Body und `Content-Type: text/event-stream` liefert (Ereignisse in mehreren Stücken, auch über Stückgrenzen geteilte Zeilen und `\r\n`). Vorhandene Helfer aus `web/src/test/fakeApi.ts` nutzen oder ergänzen nur, wenn nötig (dann im Kurzbericht nennen). Prüfen, ob `TextDecoderStream` (benutzt in `serverSentEvents.gen.ts`) in der jsdom-Umgebung von Vitest (`web/vite.config.ts:10`) vorhanden ist; falls nicht, in der Testeinrichtung aus Node bereitstellen, nicht im Produktcode umgehen.

7. **Doku:** `web/src/pages/README.md`, Abschnitt „Fetching data“ (Z. 128-148): ein kurzer Absatz, dass die Auskunft nicht über TanStack Query, sondern über `api/answers.ts` und `useAnswerStream` läuft, mit den Regeln „kein Wiederholen“, „Fehler wie ApiError“, „Abbruch beim Verlassen“.

## Nicht-Ziele

- Keine Seite, kein Formular, keine Route, keine Übersetzungen, keine Icons (132, 133, 134).
- Keine Änderung am Backend, an `web/openapi/schema.yml` oder an `web/src/api/generated/**` (außer einer neuen Erzeugung, falls sie nach 130 ohne Unterschied durchläuft).
- Keine Änderung an `web/src/api/client.ts`, `web/src/api/errors.ts`, `web/src/api/queryClient.ts`.
- Keine neue Abhängigkeit (kein `@microsoft/fetch-event-source`, kein `eventsource-parser` o. Ä.).
- Kein Speichern von Fragen oder Antworten, auch nicht in `localStorage` (D7: nichts speichern).
- Kein automatisches Absenden einer Frage, kein erneuter Versuch nach Fehler (auch nicht bei Netzfehler; anders als `queryClient.ts` `NETWORK_RETRIES`).

## Betroffene Bereiche (Ordner, Dateien)

- neu `web/src/api/answers.ts`, neu `web/src/api/answers.test.ts`
- neu `web/src/pages/answer/events.ts` (ggf. mit `events.test.ts` für den Wächter)
- neu `web/src/pages/answer/useAnswerStream.ts`, neu `web/src/pages/answer/useAnswerStream.test.ts(x)`
- `web/src/pages/README.md` (nur Abschnitt „Fetching data“)
- nur falls nötig: `web/src/test/fakeApi.ts` bzw. Testeinrichtung (nur Test-Helfer)

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Web-Job aus `.github/workflows/ci.yml` (Z. 98-150) im eigenen Compose-Projekt grün: `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`, `npm run licenses`; `api:generate` ohne Unterschied in `web/openapi` und `web/src/api`.
2. Backend-Job aus `ci.yml` unverändert grün (es wird kein Backend-Code geändert; einmal durchlaufen lassen, weil `api:generate` vom Schema abhängt). e2e wie in `ci.yml` grün (keine neuen e2e-Tests in diesem Auftrag).
3. Vitest mit `fetch`-Stub und `ReadableStream` prüft:
   1. Die Zustandsfolge `idle → streaming → done` mit `sources`, mehreren `delta` und `done`; Quellen und Status sind übernommen.
   2. Ein Abbruch (`cancel()` und Unmount) beendet den Strom; danach gibt es **keinen** weiteren `fetch`-Aufruf und keine Zustandsänderung.
   3. Nach einem Fehler (Netzfehler, 503, Strom bricht ohne `done` ab) gab es **genau einen** `fetch`-Aufruf.
   4. 403 ruft `reportForbidden` auf (über `onForbidden`-Listener geprüft) und ergibt die Ursache `forbidden`.
   5. 400 mit `{"detail": "…"}` liefert einen `ApiError` mit `status` 400 und dem Text.
   6. 409 mit `code: "ai_disabled"` wird als eigene Ursache `ai-disabled` erkannt, ebenso ein `error`-Ereignis mit diesem Code.
   7. `final_text` aus `done` ersetzt den gestreamten Text.
   8. Der Text bleibt ein reiner String: ein `delta` mit `<img src=x onerror=…>` steht unverändert als Zeichenkette im Zustand.
   9. Ein ungültiges Ereignis (falscher Typ, unbekannter Status) führt zu `invalid-answer`.
   10. Die Anfrage ist `POST` auf `/api/v1/answers/`, trägt `X-CSRFToken` und `Accept-Language` (mit `installClientConfig()` im Test) und enthält die Frage nur im Body, nicht in der Adresse.
   11. Ein zweites `ask()` während `streaming` löst keinen zweiten `fetch` aus.
4. `tsc` ohne Fehler, `eslint` ohne Warnung, kein `any`, keine `eslint-disable`-Zeile ohne Begründung.
5. Keine neue Abhängigkeit: `web/package.json` und `web/package-lock.json` unverändert (`git diff --exit-code web/package.json web/package-lock.json`).
6. `down -v` der eigenen Compose-Projekte endet mit Exit 0.

Eine Sichtprüfung im Browser entfällt, weil der Auftrag keine Oberfläche baut; sie folgt in 132.

## Vorgaben und Hinweise

- **Festlegung der Leitstelle nach 130 (SDK-Funktion):** hey-api erzeugt `answer()` als `client.sse.post` mit Rückgabe `Promise<ServerSentEventsResult<AnswerResponses>>`; `AnswerEvent` ist eine Union mit Literal-`type`, `status` und `code` sind im Schema Text (`string`). Der SSE-Client von hey-api versucht ohne `sseMaxRetryAttempts` **unbegrenzt** neu – auch bei 409/503 – und liest den JSON-Fehlerkörper nicht (nur „SSE failed: 409 …“). Deshalb: `sseMaxRetryAttempts: 1` (kein automatischer Neuversuch, passt zu „kein `retry:`“ aus 130) und die Fehler vor dem Strom (400, 403, 409 `ai_disabled`/`answer_in_progress`, 429, 503 `chat_not_configured`) selbst auswerten: entweder über einen eigenen `fetch`-Weg für den Antwortkopf oder indem vorab `answerStatus()` gefragt und der HTTP-Status der SSE-Antwort ausgewertet wird. Bekannte Werte von `status`/`code` als eigene Literal-Typen im Hook, unbekannte als `internal` behandeln. Test: 409 führt zu genau einer Anfrage und einer klaren Meldung. Achtung Namen: Der generierte Typ `AnswerStatus` ist die Antwort des Status-Endpunkts, nicht der `status` von `done`; die Werte von `status` (answered, no_evidence, contradiction) und `code` (Liste in `backend/twox/answers/types.py`) als eigene Literal-Vereinigungen in `events.ts` anlegen.

- **Ablauf und Befehle:** alles über `docker compose` (Web: `deploy/compose/compose.web.yaml`, wie in `ci.yml` über `$WEB_COMPOSE`), nichts unter Windows direkt, kein `npm` am Host. Eigener Compose-Projektname (z. B. `twox-131`, `twox-131-web`) und eigener API-Port, damit parallele Aufträge sich nicht stören.
- **Ereignisvertrag:** maßgeblich ist, was 122 in `docs/ARCHITECTURE.md` (Abschnitt `answers`) und 130 im Schema festgelegt haben. Weicht das Schema vom Vertrag ab oder fehlt ein Feld, das der Hook braucht: nicht raten, Frage in diesen Auftrag schreiben, Status „wartet auf a7“ (Regel „Nicht raten“).
- **Fehlerbehandlung wie im Rest:** `ApiError`-Arten und -Felder aus `web/src/api/errors.ts:9-35`; 403-Logik aus `web/src/api/client.ts:72-86` (außer `/api/v1/me/`); Kopfzeilen aus `client.ts:48-56` laufen über die Request-Interceptoren auch beim SSE-Client (`client.gen.ts:233-241`), sobald `installClientConfig()` gelaufen ist (`web/src/main.tsx:20`).
- **Kein Wiederholen:** `sseMaxRetryAttempts: 1` beendet die Schleife nach dem ersten Fehler (`serverSentEvents.gen.ts:228`). Bitte trotzdem testen (Kriterium 3.3), weil eine spätere Generator-Version das Verhalten ändern kann.
- **D9 (a), Streaming mit Prüfung am Ende:** Was gestreamt wird, ist ungeprüft. Erst `done` liefert die geprüfte Fassung; der Hook muss diesen Unterschied im Zustand erkennbar machen (z. B. Feld `verified: boolean` oder nur im Zustand `done` gesetzter `finalText`), damit 132 den Unterschied anzeigen kann.
- **D10 (a):** Bei ausgeschalteter KI gibt es keine Antwort; der Hook meldet `ai-disabled`, die Seite zeigt später den Hinweis (132).
- **Leitplanke 4 (Dokumentinhalte sind Daten):** Ereignisinhalte werden nie als HTML, Markdown oder Link gedeutet. Quellen-Texte und Antworttext bleiben Strings.
- **Datenschutz (D7, E-62):** keine Frage, keine Antwort und kein Abschnittstext in `console.*` oder in Fehlermeldungen; Fehlertexte nur aus `detail` des Servers.
- **Leitplanke 6:** keine externen Aufrufe, relative URL, gleicher Ursprung wie die Seite.
- **Abgrenzung zu parallelen Aufträgen:** 128 (Messlauf, ohne Code) kann gleichzeitig laufen. 132 baut auf diesem Auftrag auf und darf `events.ts` und `useAnswerStream.ts` nicht verändern; 133 ergänzt nur die Felder `device`/`plant` der Anfrage – deshalb sollte `AnswerRequest` sie bereits als optionale Felder führen (aus dem Schema von 130).
- Englisch in Code, Bezeichnern, Kommentaren und Commit-Nachrichten; Kurzbericht auf Deutsch. Keine Personennamen, keine lokalen Pfade mit Benutzernamen.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine. Die einschlägigen Vorgaben D7 (nichts speichern), D9 (Streaming mit Prüfung am Ende) und D10 (keine Antwort bei ausgeschalteter KI) gelten nach Empfehlung bzw. Entscheidung zu 130.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Was wurde gebaut?**

- **Generator (Umfang 1):** hey-api 0.99 erzeugt `answer()` in `sdk.gen.ts` als `client.sse.post` (Rückgabe `ServerSentEventsResult<AnswerResponses>`). Diese Funktion wird genutzt; generierte Dateien unverändert, `api:generate` ohne Unterschied.
- **`web/src/api/answers.ts`:** `streamAnswer(request, { signal, onEvent }): Promise<AnswerStreamOutcome>`. Ruft `answer()` immer mit `sseMaxRetryAttempts: 1`, eigenem `AbortController` (am äußeren `signal` hängend) und eigener `fetch`-Hülle auf. Die Hülle ruft `fetch` zur Laufzeit, meldet jede Antwort an `reportForbidden`, liest bei Status außerhalb 2xx den Body vor dem generierten Code (`detail` nach den Regeln von `toApiError`/`errorDetail`, Klartext nur bei `text/plain`, gekürzt auf `MAX_DETAIL_LENGTH`, dazu `code`), macht aus Netzfehlern `ApiError("network")` und aus einem 2xx ohne `text/event-stream` `ApiError("invalid-answer")`. Die Hilfen aus `errors.ts` sind lokal nachgebaut (`errors.ts` bleibt unverändert; `errorDetail` ist dort nicht exportiert). Fehler aus `onSseError` werden festgehalten und nach der Schleife ausgewertet. Jedes Ereignis geht durch `parseAnswerEvent` und eine Reihenfolgeprüfung (`sources` zuerst und nur einmal, dann `delta`/`done`; `error` jederzeit); Verstoß → `invalid-answer`, Verbindung wird beendet. Nach `done`/`error` wird nicht weitergelesen.
  - Ergebnisarten: `completed` · `stream-error` (`code`, `detail`) · `ai-disabled` (409 `ai_disabled` oder Ereignis mit diesem Code) · `aborted` · `interrupted` (Ende ohne `done`/`error`, auch Lesefehler) · `failed` (`error: ApiError`, `code`: bekannter Absage-Code oder null).
  - `answersStatusQueryOptions()`: generierte `answerStatusOptions()` mit `staleTime` 15 s (Server hält 30 s).
- **`web/src/pages/answer/events.ts`:** Ereignistypen aus `types.gen.ts` abgeleitet, mit eigenen Literal-Vereinigungen `AnswerResultStatus` (answered, no_evidence, contradiction; bewusst nicht `AnswerStatus`), `AnswerErrorCode` (Liste aus `backend/twox/answers/types.py`) und `AnswerRefusalCode` (ai_disabled, answer_in_progress, chat_not_configured). `parseAnswerEvent(data: unknown): AnswerEvent | null` prüft alle Felder bis in die Fundorte (mind. ein Fundort, `n` ≥ 1, ganze Zahlen). Für 132: `toSearchLocation(location)` bildet die flache Form aus `source_ref_to_json()` auf `SearchLocation` der Suche ab (getestet).
- **`web/src/pages/answer/useAnswerStream.ts`:** `useReducer`, Zustände `idle | streaming | done | error`, Felder `sources`, `text`, `verified` (nur in `done` true; `text` ist dort `final_text`). `error.failure.cause`: `ai-disabled`, `forbidden`, `http` (mit `ApiError` und Absage-Code), `network`, `invalid-answer`, `interrupted`, `stream` (Code und `detail`). Reducer `answerStreamReducer` exportiert. `ask()` nur ohne laufenden Strom; Ereignisse alter oder abgebrochener Ströme werden verworfen (Abgleich des Controllers), nach Unmount kein `dispatch`.
  - **Wahl bei `cancel()`:** zurück nach `idle` mit `cancelled: true`; Text und Quellen bis dahin bleiben, `verified: false`. Begründung: Abbruch ist kein Fehler (keine Fehlermeldung), das Formular ist sofort wieder frei, und 132 kann „abgebrochen“ samt ungeprüftem Text anzeigen, ohne einen fünften Zustand zu kennen.
- **Test-Helfer:** `web/src/test/fakeApi.ts` um `sseEvent()` und `fakeEventStream()` ergänzt (steuerbarer `ReadableStream`, Text- und Byte-Stücke, Schließen, Abreißen; Abbruch des Request-Signals bricht den Body wie ein echter `fetch` ab). Neu `web/src/pages/answer/testData.ts` mit erfundenen Testereignissen (nicht im Auftrag genannt, analog `search/testData.ts`).
- **Doku:** `web/src/pages/README.md`, Abschnitt „Fetching data“, ein Absatz.

**Wie wurde getestet?** (Compose-Projekte `twox-131-web` und `twox-131`, API-Port 18131)

- Kriterium 0: `docker version`, `docker compose version` Exit 0.
- Kriterium 1: `lint`, `typecheck`, `test` (50 Dateien, 1039 Tests), `build`, `licenses`, `api:generate` – alle Exit 0; `git diff` auf `web/openapi`, `web/src/api`, `package.json`, `package-lock.json` leer.
- Kriterium 2: Backend-Job vollständig grün (ruff, format, mypy, pytest 3398 passed, pytest -m worker 6 passed, makemessages ohne Unterschied, makemigrations, Lizenzen, spectacular ohne Unterschied). e2e: 82 passed, 1 skipped.
- Kriterium 3 (Vitest, jsdom, `fetch`-Stub mit `ReadableStream`): 3.1 Zustandsfolge mit Quellen und Status; 3.2 `cancel()` und Unmount: Strom gestoppt, genau ein `fetch`, Zustand unverändert; 3.3 Netzfehler, 503, Strom ohne `done`, abgerissener Strom: genau ein `fetch` (die Tests würden bei unbegrenztem Neuversuch hängen und scheitern); 3.4 403 → `onForbidden`, Ursache `forbidden`; 3.5 400 → `ApiError` mit Status und Text; 3.6 409 `ai_disabled` und Ereignis `ai_disabled` → `ai-disabled`; 3.7 `final_text` ersetzt Text; 3.8 `<img …>` bleibt String; 3.9 falscher Typ, unbekannter Status, kein JSON, falsche Reihenfolge → `invalid-answer`; 3.10 POST auf `/api/v1/answers/`, `X-CSRFToken`, `Accept-Language`, kein `Last-Event-ID`, Frage nur im Body; 3.11 zweites `ask()` ohne zweiten `fetch`. Dazu Stücke mitten in Zeilen, zwischen CR und LF und mitten im UTF-8-Zeichen.
- `TextDecoderStream` ist in der jsdom-Umgebung von Vitest vorhanden; keine Testeinrichtung nötig.
- Kriterium 4: `tsc` und `eslint` ohne Fehler, kein `any`, kein `eslint-disable`. Kriterium 5: keine neue Abhängigkeit. Kriterium 6: `down -v` beider Projekte Exit 0.

**Zweig und Arbeitsverzeichnis:** `worktree-agent-aa013d300ea97afe1`, `.claude/worktrees/agent-aa013d300ea97afe1`.

**Abweichungen und Hinweise**

- Unbekannte Fehlercodes im `error`-Ereignis werden nach der Festlegung der Leitstelle zu `internal`, nicht abgelehnt; unbekannte `status`-Werte in `done` werden abgelehnt (`invalid-answer`, Kriterium 3.9).
- `api/answers.ts` importiert die Typen und den Wächter aus `pages/answer/events.ts` (Ort laut Auftrag vorgegeben).
- 409 `answer_in_progress`, 429 und 503 `chat_not_configured` landen als Ursache `http` mit `ApiError` und Code; 132 kann daran eigene Texte hängen.
- Die ungetrackte `.env` des Arbeitsverzeichnisses war älter als `.env.example` (ohne E2E-Zeilen); ergänzt um Port und die beiden E2E-Zeilen. Der Backend-Lauf lief daher mit den Standardwerten aus `compose.yaml` für die fehlenden `TWOX_ANSWER_*`-Zeilen; grün.
