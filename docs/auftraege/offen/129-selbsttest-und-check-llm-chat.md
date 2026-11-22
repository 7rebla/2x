# Auftrag 129 – Selbsttest und check_llm für Chat

Meilenstein: M3 · Freigabestufe: B · Status: zur Prüfung

## Ziel

Der Betrieb der Auskunft (M3) soll sichtbar und prüfbar sein, bevor es Antworten gibt. Selbsttest und `check_llm` zeigen, ob das Chat-Modell aus `TWOX_CHAT_MODEL` vorhanden, lokal und für Text geeignet ist. Der Selbsttest ruft das Modell dafür nicht auf, er liest nur die Modellliste. `check_llm --chat` lässt das Modell einmal einen festen Testsatz beantworten und misst die Zeit bis zum ersten Textstück und die Geschwindigkeit. Die Betriebsdoku im README nennt, was am Host für das Chat-Modell einzustellen ist.

Bei ausgeschalteter KI (E-59) bleibt alles neutral, und keine Verbindung wird aufgebaut.

## Umfang

1. **Selbsttest, Teil `ai`** (`backend/twox/config/selftest.py`):
   - `AiCheck` und `AiCheckSerializer` bekommen drei optionale Felder, die nur bei KI an gesetzt werden:
     - `chat_model: str` – Wert von `TWOX_CHAT_MODEL`, leer, wenn nicht gesetzt;
     - `chat_ok: bool`;
     - `chat_error: str` – kurzer, bereinigter englischer Text, sonst leer.
   - Die bestehenden Felder `enabled`, `ok`, `model`, `dimensions` und `error` behalten ihre Bedeutung. Sie gelten weiter nur für das Einbettungsmodell.
   - Neue Funktion `check_chat()` (oder ein Teil von `check_ai()`), die **nur** `GET /api/tags` auswertet und keine Erzeugung startet:
     - Ist `TWOX_CHAT_MODEL` leer, ist `chat_ok` false, `chat_error` lautet `chat model not configured`. Es wird kein Aufruf gemacht. Das ist der erwartete Zustand bis D1 (Auftrag 121, Warnung statt Fehler).
     - Der Modellname wird mit der gemeinsamen Cloud-Sperre aus `backend/twox/answers/llm_guard.py` (Auftrag 121) geprüft: Cloud-Name, `remote_host`/`remote_model` in `/api/tags`, Modell nicht vorhanden, Fähigkeit `completion` fehlt. Jeder Fall wird zu einem kurzen `chat_error` ohne Host-Adresse, ohne URL und ohne Antworttext von Ollama.
     - Fehlerklassen aus `backend/twox/answers/chat.py` (121) werden wie in `check_ai()` behandelt: bekannte Fehler bereinigt mit `sanitize_error_detail`, unerwartete Fehler mit festem Text (analog `AI_FAILED_DETAIL`, `selftest.py:41`), Einzelheiten nur ins Server-Log.
   - **Zeitbudget:** Die Seite wartet höchstens 15 s (`SELFTEST_TIMEOUT_MS`, `web/src/api/selftest.ts:4`). Der Worker braucht bis zu 5 s (`selftest.py:34`), die Prüfung der Einbettung bis zu 2 × 4 s (`selftest.py:36-38`, Kurzbericht 048). Eine weitere Anfrage mit 4 s würde die Grenze überschreiten (5 + 3 × 4 = 17 s). Deshalb wird `/api/tags` im Teil `ai` höchstens einmal je Selbsttest abgefragt und für Einbettung und Chat gemeinsam ausgewertet, oder die Chat-Prüfung bleibt anders nachweisbar im Budget. Im schlechtesten Fall muss der ganze Selbsttest unter 15 s bleiben. Ein Test mit Zeitattrappe oder mit gezählten Anfragen an die Attrappe belegt das.
   - Die Karte bleibt **eine** Karte „KI-Funktionen“, mit zusätzlichen Zeilen für das Chat-Modell.
2. **Testseite** (`web/src/pages/SelftestPage.tsx`, `AiCard` ab Z. 146):
   - **KI aus:** unverändert neutral (`tone="neutral"`, Text `ai.disabled`), kein Chat-Feld.
   - **KI an:** neue Felder „Chat-Modell“ (Name oder „nicht festgelegt“) und Status des Chat-Modells.
   - **Ton der Karte:**
     - `failed`, wenn die Einbettung scheitert oder ein Chat-Modell eingetragen ist und `chat_ok` false ist;
     - `ok`, wenn die Einbettung in Ordnung ist und kein Chat-Modell eingetragen ist. In diesem Fall erscheint ein ruhiger Hinweis „Chat-Modell noch nicht festgelegt“ ohne `role="alert"`.
   - `chat_error` erscheint wie die anderen Fehler über `CheckError`.
   - Texte in `web/src/locales/de/selftest.json` und `web/src/locales/en/selftest.json` unter `ai.*` mit denselben Schlüsseln.
   - Schema und Client neu erzeugen: `web/openapi/schema.yml`, `web/src/api/generated/**`.
   - `web/src/api/selftest.ts` nur anpassen, wenn die Prüfung der Antwortform die neuen optionalen Felder sonst ablehnt.
3. **`check_llm --chat`** (`backend/twox/answers/management/commands/check_llm.py`):
   - Neue Option `--chat`, die sich mit `--embed` ausschließt.
   - Bei KI aus wird nur `DISABLED_LINE` ausgegeben (Z. 41-44), Exit-Code 0, keine Verbindung. Das entspricht dem heutigen Verhalten bei Z. 245-248.
   - Bei KI an kommt zuerst die `WARNING:`-Zeile aus `remote_host_warning` (Z. 167-180), wie bei `--embed`. Danach wird über `get_chat_model()` (121) ein fester, selbst geschriebener englischer Testsatz gesendet (Konstante `CHAT_TEST_PROMPT`, kein Handbuchinhalt). Die Grenzen sind ein kleines `max_tokens` (Konstante, z. B. 32), Temperatur 0 und ein fester Seed. Der Strom wird mit `close()` geschlossen, auch bei einem Fehler.
   - Ausgabe genau einer Ergebniszeile:
     - `OK: chat with <model>: first token after <x.xx>s, <n> chunks in <y.yy>s (<z.z> chunks/s)`;
     - `FAILED: <Fehlerklasse>: <Meldung>`, Exit-Code 1;
     - leeres `TWOX_CHAT_MODEL` ergibt `FAILED: invalid configuration: TWOX_CHAT_MODEL is empty`.
   - Die Antwort des Modells wird **nie** ausgegeben und nie protokolliert.
   - Die Schnittstelle aus 121 liefert Textstücke, keine Token-Zahlen. Gemessen werden deshalb Textstücke je Sekunde, und die Ausgabe nennt sie ehrlich `chunks`. Liefert 121 eine Token-Zahl, darf sie zusätzlich erscheinen.
   - Modul-Docstring und `help` werden ergänzt.
4. **README** (englisch):
   - Im Abschnitt „AI features“ (nach Z. 167-187) ein Unterabschnitt für das Chat-Modell:
     - `ollama pull <chat model>` als Platzhalter, weil das Modell erst mit D1 gewählt wird;
     - `TWOX_CHAT_MODEL`;
     - Host-Einstellungen `OLLAMA_CONTEXT_LENGTH` (Ollama kürzt sonst den Kontext still, die Länge lässt sich über `/v1` nicht je Anfrage setzen), `OLLAMA_NUM_PARALLEL` und `OLLAMA_KEEP_ALIVE` mit Zweck und Hinweis auf den Speicherbedarf; konkrete Werte nur als „set after the model decision“;
     - der Hinweis, dass Ollama am Host Prompts und damit Dokumenttexte protokollieren kann (z. B. mit Debug-Protokoll), und dass das Log des Hosts deshalb zu den schützenswerten Daten gehört.
   - Im Abschnitt `check_llm` (Z. 315-338) `--chat` mit allen möglichen Zeilen wie bei `--embed`.
   - Z. 89 (Selbsttest-Karte) ergänzen.
5. **Tests** (siehe Akzeptanzkriterien), mit der vorhandenen Ollama-Attrappe `backend/tests/answers/fake_ollama.py`. Wenn nötig wird sie um Chat-Antworten und `capabilities` in `/api/tags` erweitert, abgestimmt mit dem, was 121 dort ergänzt.

## Nicht-Ziele

- Keine Änderung an `chat.py`, `llm_guard.py`, `embeddings.py`, `settings.py`, `compose.yaml` oder `.env.example`; das ist Auftrag 121. Fehlt dort etwas, folgt eine Frage im Kurzbericht und keine Änderung.
- Keine Erzeugung durch das Modell im Selbsttest.
- Kein Antwortdienst, keine Antwort-API und kein Status-Endpunkt `/api/v1/answers/status/` (126, 130).
- Keine Modellwahl, kein `ollama pull` am Host und keine Änderung an Host-Einstellungen (D1, Auftrag 128).
- Keine neue Karte, keine neue Seite, kein Navigationseintrag.
- Keine Änderung an `docs/DECISIONS.md`, `docs/STATUS.md` oder `docs/ROADMAP.md`.

## Betroffene Bereiche (Ordner, Dateien)

Vorhanden, wird geändert:
- `backend/twox/config/selftest.py`
- `backend/twox/answers/management/commands/check_llm.py`
- `backend/tests/config/test_selftest.py`
- `backend/tests/answers/test_check_llm.py`
- `backend/tests/answers/fake_ollama.py` (nur Erweiterung)
- `web/src/pages/SelftestPage.tsx`, `web/src/pages/SelftestPage.test.tsx`
- `web/src/locales/de/selftest.json`, `web/src/locales/en/selftest.json`
- `web/src/api/selftest.ts` und `web/src/api/selftest.test.ts` (nur falls nötig, siehe Umfang 2)
- `web/src/App.test.tsx` und `web/e2e/selftest.spec.ts` (nur falls die neuen Felder sie berühren)
- `web/openapi/schema.yml`, `web/src/api/generated/**` (neu erzeugt, nicht von Hand)
- `README.md` (Abschnitte „AI features“, `check_llm`, Selbsttest Z. 89)
- `docs/ARCHITECTURE.md`, nur die Zeile `/api/v1/selftest/` (Z. 370). Der Abschnitt `answers` (Z. 134) gehört zu 121.

Neu: keine Produktdatei. Neue Testdateien sind erlaubt, falls die bestehenden zu groß werden.

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-129`.
- Vorher `.env.example` nach `.env` kopieren und `TWOX_API_PORT=18129` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst gilt Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. **Selbsttest bei KI aus** meldet nur `{"enabled": false}`, ohne Chat-Felder und ohne Verbindung. Der Test läuft mit Socket-Sperre oder einer Attrappe, die jeden Aufruf als Fehler wertet.
2. **Selbsttest bei KI an**, je ein Test:
   - Chat-Modell vorhanden mit `completion`: `chat_ok` true;
   - `TWOX_CHAT_MODEL` leer: `chat_ok` false, `chat_error` `chat model not configured`, kein Aufruf;
   - Modell fehlt in `/api/tags`;
   - Cloud-Modell am Namen und über `remote_host`;
   - Modell ohne `completion`, z. B. ein reines Einbettungsmodell;
   - Ollama nicht erreichbar.
   In keinem `chat_error` steht eine Host-Adresse, eine URL oder ein Antworttext. Ein Test prüft das mit einer auffälligen Adresse.
3. **Keine Erzeugung im Selbsttest:** Die Attrappe zählt die Aufrufe von `/chat/completions`; nach dem Selbsttest sind es 0 (Test).
4. **Zeitbudget:** Ein Test belegt, dass der Teil `ai` bei KI an höchstens einmal `/api/tags` abfragt, oder auf andere Weise, dass der schlechteste Fall des ganzen Selbsttests unter 15 s bleibt.
5. **`check_llm --chat`**, je ein Test:
   - KI aus: `DISABLED:`, Exit-Code 0, keine Verbindung;
   - Erfolg: eine `OK:`-Zeile mit Modell, Zeit bis zum ersten Textstück und Rate, ohne Antworttext;
   - Modell fehlt, Cloud-Modell, leeres `TWOX_CHAT_MODEL`, Zeitüberschreitung: je eine `FAILED:`-Zeile und Exit-Code 1;
   - `--chat` zusammen mit `--embed` wird abgewiesen;
   - entfernter Host: Die `WARNING:`-Zeile kommt zuerst;
   - `close()` wird auch bei einem Fehler aufgerufen.
   Die bestehenden Tests in `test_check_llm.py` bleiben unverändert grün.
6. **Vitest:** `SelftestPage.test.tsx` prüft die Zustände der Karte: KI aus (neutral), KI an mit Chat in Ordnung (OK), KI an ohne Chat-Modell (OK mit ruhigem Hinweis, kein `role="alert"`), Chat-Fehler (Fehlgeschlagen mit `chat_error`). `web/src/i18n.test.ts` ist grün; de und en haben dieselben Schlüssel.
7. **Backend-Job wie in `ci.yml`** (Images vorher neu bauen):
   - `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0;
   - `D run --rm backend-dev ruff check .` meldet `All checks passed!`;
   - `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0;
   - `D run --rm backend-dev mypy .` meldet `Success: no issues found`;
   - `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen;
   - `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0;
   - `makemessages` plus `git diff -I POT-Creation-Date -- backend/locale` ohne Unterschied;
   - `makemigrations --check --dry-run` meldet keine Änderung;
   - `scripts/check-licenses.sh` ist grün;
   - `spectacular` (unter Git Bash mit `MSYS_NO_PATHCONV=1`) erzeugt das Schema; danach zeigt `git diff -- web/openapi` nur die neuen Felder, und der Stand ist eingecheckt.
8. **Web-Job wie in `ci.yml`** mit `deploy/compose/compose.web.yaml`: `npm ci`, `lint`, `typecheck`, `test`, `build` und `licenses` sind grün; `api:generate` erzeugt keinen weiteren Unterschied in `web/openapi` und `web/src/api`.
9. **e2e wie in `ci.yml`** (Job mit `--profile e2e`): grün, auch `web/e2e/selftest.spec.ts`.
10. **Lokal mit Ollama am Host:**
    - `D exec -T api python manage.py check_llm --chat` gibt bei leerem `TWOX_CHAT_MODEL` die erwartete `FAILED:`-Zeile aus;
    - mit `-e TWOX_AI_ENABLED=false` gibt derselbe Befehl `DISABLED:` aus;
    - mit einem **bereits am Host vorhandenen** Modell, das `completion` kann (kein `ollama pull` in diesem Auftrag; gibt es keines, entfällt dieser Teil mit Vermerk), gibt er eine `OK:`-Zeile aus.
    - Der Selbsttest gegen den echten Stand (Testclient im `api`-Container) liefert bei leerem und bei gesetztem `TWOX_CHAT_MODEL` die erwarteten Felder.
    Die Ausgaben stehen gekürzt im Kurzbericht, ohne Modellantwort.
11. **Sichtprüfung** der Seite `/selftest` in de und en bei 375 und 1280 px: KI an ohne Chat-Modell und KI aus. Die Beschreibung steht im Kurzbericht. Die Karte bleibt ruhig, nichts läuft über.
12. **Keine neue Abhängigkeit** in `backend/pyproject.toml`, im Lock, in `web/package.json` oder in `package-lock.json`.
13. **Abräumen:** `D --profile dev down -v` endet mit Exit-Code 0, `git status` ist sauber bis auf die Commits.

## Vorgaben und Hinweise

- **Voraussetzung:** Auftrag 121 (Schnittstelle Sprachmodell) ist nach `main` zusammengeführt. Gebraucht werden daraus `get_chat_model()`, die Fehlerklassen `Chat*Error`, `llm_guard.py` mit der Prüfung von `completion` und die Einstellungen `TWOX_CHAT_*`. Weichen Namen in 121 von diesem Auftrag ab, gelten die Namen aus 121.
- **Welle 2**, parallel zu 124 (Suche) und 136 (Testumgebung, kein Code). Keine gemeinsame Datei mit diesen Aufträgen. `README.md` ändert später auch 130; 129 kommt vorher.
- **E-59, KI optional:** Jede KI-abhängige Stelle hat Tests für beide Zustände. Bei KI aus gibt es keine Verbindung. Der Zustand ist neutral, ohne Warn- oder Fehlersymbol, wie die bestehende Karte (`SelftestPage.tsx:143-158`, Kurzbericht 048).
- **E-04:** Das Modell ist austauschbar. Kein Modellname wird im Code fest verdrahtet, auch nicht in Tests außer als erkennbarer Beispielname.
- **Leitplanke 6 (ohne Internet) und Cloud-Sperre:** Die Prüfung läuft wie in `embeddings.py:18-28` und `:241-290`, über die gemeinsame Hilfsfunktion aus 121. Ein Cloud-Modell wird nie angefragt, auch nicht mit `--chat`.
- **Leitplanke 4 und Datenschutz:** Weder Testsatz noch Modellantwort kommen ins Log oder in die Ausgabe. Fehlertexte sind englisch und kurz und enthalten keine Adresse, wie `selftest.py:3-6`.
- **Leitplanke 2:** nur lesend. Der Selbsttest bleibt `GET` mit `CanRead` (`selftest.py:200-216`); keine neue Berechtigung.
- **Muster:** `check_embed()` (`check_llm.py:183-201`) und `check_ai()` (`selftest.py:159-197`). Für den Testsatz gilt dasselbe wie für `EMBED_TEST_SENTENCE` (Z. 37-38): fest, harmlos, selbst geschrieben.
- Die Zeitgrenze für `--chat` ist `TWOX_CHAT_TIMEOUT_SECONDS` aus 121, nicht `--timeout`. Das steht im README wie bei `--embed`.
- In der CI gibt es kein Ollama. Echte Läufe sind nur lokal möglich (Kriterium 10).
- Kein `ollama pull`, keine Änderung an Ollama am Host (D1 steht noch aus). Keine Herstellertexte in Tests oder Doku.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14). Klein committen auf dem eigenen Zweig, englische Commit-Nachrichten.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Was wurde gebaut?** In fünf Commits:

1. Selbsttest (`config/selftest.py`): `AiCheck`/`AiCheckSerializer` mit den optionalen Feldern `chat_model`, `chat_ok`, `chat_error` (nur bei KI an). `check_ai()` teilt sich in `check_embedding()` und `check_chat()`. `check_chat()` startet keine Erzeugung. Es prüft den Namen (`is_cloud_model_name`) und wertet dann die Antwort von `/api/tags` mit `llm_guard.find_local_model` und `model_capabilities` aus (Prüfung auf `completion`). Fehler werden auf die Klassen `Chat*Error` abgebildet und mit `sanitize_error_detail` bereinigt. Unerwartete Fehler ergeben den festen Text `chat model check failed`. Ist `TWOX_CHAT_MODEL` leer, wird nichts angefragt und `chat model not configured` gemeldet.
   - **Zeitbudget:** Die neue Unterklasse `SelftestEmbedder` (in `selftest.py`, `embeddings.py` bleibt unverändert) merkt sich die Antwort oder den Fehler ihrer eigenen `/api/tags`-Anfrage. `check_chat()` nutzt diese Antwort mit. Nur wenn die Einbettungsprüfung `/api/tags` nicht abgefragt hat (Dimensionsfehler, Cloud-Name beim Einbettungsmodell, unerwarteter Fehler), fragt die Chat-Prüfung die Liste selbst ab. Damit gilt: höchstens einmal `/api/tags` und höchstens zwei Anfragen im Teil `ai` (`AI_MAX_REQUESTS`). Schlechtester Fall: 5 + 2 × 4 = 13 s.
2. `check_llm --chat`:
   - schließt sich gegenseitig mit `--embed` aus (argparse-Gruppe);
   - Ablauf: `DISABLED:` → `WARNING:` → `chat.get_chat_model()` → `stream()` mit `CHAT_TEST_PROMPT`, `CHAT_TEST_MAX_TOKENS = 32`, Temperatur 0 und `CHAT_TEST_SEED = 129`;
   - Strom und Modell werden in `finally` geschlossen;
   - Ausgabe: `OK: chat with <model>: first token after x.xxs, n chunks in y.yys (z.z chunks/s)`, `FAILED: <Klasse>: <Meldung>` oder `FAILED: invalid configuration: TWOX_CHAT_MODEL is empty`;
   - zusätzlich `FAILED: empty answer: …`, falls das Modell innerhalb der 32 Tokens keinen Text liefert;
   - die Antwort wird nur gezählt, nie ausgegeben oder protokolliert.
3. Schema und Client neu erzeugt (`web/openapi/schema.yml`, `web/src/api/generated/types.gen.ts`).
4. Testseite:
   - `AiCard` mit den Zeilen „Chat-Modell“ (Name oder „nicht festgelegt“) und „Status Chat-Modell“ („bereit“) bzw. `CheckError` mit der Beschriftung „Fehler Chat-Modell“ (`CheckError` hat dafür eine optionale `label`-Eigenschaft);
   - der ruhige Hinweis „Chat-Modell noch nicht festgelegt …“ steht als `note` der Karte, ohne `role="alert"`;
   - Ton „Fehlgeschlagen“ bei Fehler der Einbettung oder wenn ein eingetragenes Chat-Modell nicht bereit ist; sonst „OK“;
   - Texte de/en unter `ai.*`.
5. README: Unterabschnitt „Chat model for answers“ (Platzhalter `ollama pull <chat model>`, `TWOX_CHAT_MODEL`, `OLLAMA_CONTEXT_LENGTH`, `OLLAMA_NUM_PARALLEL`, `OLLAMA_KEEP_ALIVE` ohne Werte, Hinweis zum Log des Hosts), `--chat` im Abschnitt `check_llm`, Selbsttest-Satz bei Schritt 7. `docs/ARCHITECTURE.md`: nur die Zeile `/api/v1/selftest/`.

**Wie wurde getestet?** `D` = `docker compose -p twox-129`, `.env` aus `.env.example` mit `TWOX_API_PORT=18129`.

| Kriterium | Ergebnis |
| --- | --- |
| 0 | Docker 29.9.3, Compose v5.7.0, Exit 0 – erfüllt |
| 1 | `test_chat_fields_are_missing_and_nothing_is_contacted_when_ai_is_off` (Socket gesperrt, `{"enabled": false}`) und der bestehende Test für KI aus – erfüllt |
| 2 | Tests in `backend/tests/config/test_selftest.py`: Modell mit `completion`, leer (ohne Anfrage), nicht geladen, Cloud über Namen (2 Namen, 0 Anfragen) und über `remote_host`/`remote_model`, ohne `completion` (`bge-m3`), nicht erreichbar. Zusätzlich: ohne `capabilities`, Server ohne `/api/tags` und unerwarteter Fehler. Auffällige Adresse und Marker: `test_chat_error_never_names_address_or_answer_text` sowie HTTP 500 und eine kaputte Liste mit URL im Antworttext – erfüllt |
| 3 | `chat_requests == []` in den Selbsttest-Tests – erfüllt |
| 4 | `test_ai_part_asks_the_model_list_at_most_once` (6 Fälle, je genau 1 × `/api/tags`, ≤ 2 Anfragen); nicht erreichbarer Port mit 1 Verbindungsversuch; stiller Port: der ganze Teil `ai` < 2 × Zeitgrenze; `WORKER + AI_MAX_REQUESTS × AI_TIMEOUT < 15` – erfüllt |
| 5 | `backend/tests/answers/test_check_llm_chat.py` (neue Datei, `test_check_llm.py` unverändert): aus, Erfolg (ohne Antwort und Prompt in Ausgabe und Log, Parameter 32/0/Seed), Modell fehlt, ohne `completion`, Cloud (Name, `remote_host`), leer, ungültige Adresse, Zeitüberschreitung (`TWOX_CHAT_TIMEOUT_SECONDS`, Server sieht den Abbruch), leere Antwort, `--chat --embed` abgewiesen, `WARNING:` zuerst, `close()` von Strom und Modell bei Fehler im Strom, bei Fehler beim Aufruf und bei Erfolg – erfüllt |
| 6 | Vitest: neue Fälle für aus (kein Chat-Feld), Chat bereit, ohne Chat-Modell (OK, Hinweis, kein `alert`), Chat-Fehler, de. 47 Dateien, 962 Tests grün; `i18n.test.ts` grün – erfüllt |
| 7 | build/up Exit 0; ruff „All checks passed!“; format Exit 0; mypy „Success: no issues found in 203 source files“; pytest 2631 passed, 0 failed, 0 skipped (6 deselected = Marker `worker`); `-m worker` 6 passed; Katalog ohne Unterschied; „No changes detected“; „License check passed.“; Schema eingecheckt, nur die neuen Felder und der Docstring – erfüllt |
| 8 | `npm ci`, lint, typecheck, test, build, licenses Exit 0; `api:generate` danach ohne weiteren Unterschied – erfüllt |
| 9 | e2e mit `--profile e2e`: 82 passed, 1 skipped (der lokale Teil der M2-Abnahme, wie in der CI), `selftest.spec.ts` grün – erfüllt |
| 10 | siehe unten – erfüllt |
| 11 | siehe unten – erfüllt |
| 12 | `git diff main -- backend/pyproject.toml backend/uv.lock web/package.json web/package-lock.json` leer – erfüllt |
| 13 | `D --profile dev --profile e2e down -v` und `docker compose -p twox-129-web … down -v` Exit 0; `git status` sauber – erfüllt |

**Kriterium 10 (Ollama am Host, nur lesend, kein pull):**

- `check_llm --chat` mit leerem `TWOX_CHAT_MODEL`: `FAILED: invalid configuration: TWOX_CHAT_MODEL is empty` (Exit 1).
- `check_llm --chat` mit `-e TWOX_AI_ENABLED=false`: `DISABLED: AI features are not enabled …` (Exit 0).
- `check_llm --chat` mit `TWOX_CHAT_MODEL=qwen3.8:27b-q4_K_M` (nur in der ungetrackten `.env`, danach wieder geleert):
  - erster Aufruf mit Laden des Modells: `OK: chat with qwen3.8:27b-q4_K_M: first token after 30.14s, 13 chunks in 30.47s (0.4 chunks/s)`;
  - zweiter Aufruf, Modell geladen: `OK: … first token after 0.16s, 13 chunks in 0.48s (26.8 chunks/s)`.
  - Die Rate rechnet über die ganze Zeit einschließlich der Zeit bis zum ersten Stück; sie ist kein Messwert für 128.
- Selbsttest im `api`-Container über `SelftestView` (`APIRequestFactory` mit `force_authenticate`, ohne Sitzung), Teil `ai`:
  - leer: `chat_model ""`, `chat_ok false`, `chat model not configured` (0,07 s);
  - qwen gesetzt: `chat_ok true` (3,1 s; die Einbettung musste neu laden);
  - mit `-e TWOX_CHAT_MODEL=bge-m3`: „cannot generate text (no capability 'completion') …“;
  - mit `-e TWOX_CHAT_MODEL=not-there-chat:1b`: „not loaded … ollama pull …“;
  - mit `-e TWOX_CHAT_MODEL=gpt-oss:120b-cloud`: „is an Ollama cloud model …“ ohne Anfrage.
- gemma4 wurde nicht aufgerufen.

**Kriterium 11 (Sichtprüfung im eingebauten Browser, Testkonto aus `.env`):**

- **KI an, ohne Chat-Modell:**
  - Die Karte „KI-Funktionen“/„AI features“ ist grün mit „OK“.
  - Darunter steht der graue Hinweis „Chat-Modell noch nicht festgelegt. Antworten auf Fragen sind erst danach möglich, alles andere funktioniert.“ bzw. der englische Text, dann Modell, Dimensionen und „Chat-Modell: nicht festgelegt“ / „Chat model: not set“.
  - Bei 375 px steht alles in einer Spalte; bei 1280 px in drei Spalten, die KI-Karte rechts.
  - `scrollWidth` ist gleich der Fensterbreite (375 bzw. 1280), die Karte läuft nicht über.
  - Kein rotes Element, kein `alert`.
- **KI aus:** unverändert neutral (grau, Info-Symbol, „Nicht aktiviert“/„Not enabled“, Hinweistext), ohne Chat-Zeilen, in de/en bei 375 und 1280 px ohne Überlauf.
- Danach Sprache und Größe zurückgesetzt, `.env` wieder mit KI an.

**Zweig und Arbeitsverzeichnis:** Zweig `worktree-agent-acf4663787b0c7e02`, Arbeitsverzeichnis `.claude/worktrees/agent-acf4663787b0c7e02`.

**Abweichungen:**

- Die Tests für `--chat` stehen in der neuen Datei `backend/tests/answers/test_check_llm_chat.py`, damit `test_check_llm.py` unverändert bleibt (Kriterium 5). Sie nutzen deren Hilfsfunktionen.
- `fake_ollama.py` musste nicht erweitert werden; 121 hatte schon alles Nötige.
- In `test_selftest.py` erwarten drei bestehende Tests jetzt zusätzlich die Chat-Felder (Gleichheitsprüfung des ganzen `ai`-Objekts und Schema-Felder). Die autouse-Fixture setzt `TWOX_CHAT_MODEL = ""`.
- Die Chat-Prüfung im Selbsttest fragt **nie** `POST /api/show` (Budget, eine Anfrage). Nennt `/api/tags` keine `capabilities`, gilt das Modell nach der Listenprüfung als bereit (wird protokolliert). Bei Ollama 0.40.17 sind sie immer vorhanden (Kurzbericht 121).
- Die Bewertung von `/api/tags` für den Chat (`check_chat_model_list`) bildet die Schritte aus `OpenAICompatibleChat._ensure_local_model` mit den Bausteinen aus `llm_guard` nach, weil `chat.py` dafür keine öffentliche Funktion hat. Der Text „cannot generate text …“ ist deshalb doppelt. Vorschlag für später: eine Funktion `check_chat_entry` in `llm_guard`, die beide nutzen.
- `SelftestEmbedder` überschreibt die geschützte Methode `_request` von `OpenAICompatibleEmbedder`, um die Antwort auf die Modellliste mitzunutzen, ohne `embeddings.py` zu ändern.
- Zusätzliche Ergebniszeile `FAILED: empty answer: …` (siehe oben).

Offene Fragen: keine.
