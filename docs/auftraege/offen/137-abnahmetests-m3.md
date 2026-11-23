# Auftrag 137 – Abnahmetests M3 und Browserfluss

Meilenstein: M3 · Freigabestufe: B · Status: offen

Voraussetzung: 127 (`evaluate_answers`), 130 (Antwort-API mit SSE und Status), 133 (Eingrenzen auf Gerät und Anlage) und 134 (Navigation Auskunft) sind auf `main`. Damit sind auch 121, 122, 126, 131 und 132 vorhanden.

## Ziel

Wiederholbare Tests belegen das ROADMAP-Kriterium von M3 (`docs/ROADMAP.md:13`): „mindestens 8 von 10 Prüffragen richtig; Kontrollfrage ohne erfundene Antwort“, dazu die Merkmale „Frage und Antwort, Quellenanzeige, Eingrenzen auf Gerät“. Das Muster sind die Abnahmetests von M2 (Aufträge 058 und 090):

- **CI-Teil:** Ein Browsertest prüft den ganzen Ablauf auf der Seite Auskunft, mit abgefangenem Antwortstrom (`page.route`). Er braucht kein Modell und kein Netz.
- **Lokaler Teil:** Er läuft nur mit dem Schalter `TWOX_M3_LOCAL=1` in der Testumgebung mit den Handbüchern und dem Chat-Modell. Ein Backend-Test ruft `evaluate_answers` auf und verlangt das Abnahmekriterium. Ein Browsertest stellt echte Fragen auf der Seite Auskunft. Ausgeführt wird der lokale Teil im Abnahmelauf 138, nicht in diesem Auftrag.

## Umfang

### 1. Backend `backend/tests/acceptance/test_m3.py` (neu)

- Modul-Docstring nach dem Muster von `backend/tests/acceptance/test_m2.py:1-17`: Bedingung von M3, Verweis auf `web/e2e/m3-acceptance.spec.ts` und auf den Abnahmelauf 138.
- **Lokale Fälle** laufen nur mit `TWOX_M3_LOCAL=1`. Ohne den Schalter werden sie mit `pytest.mark.skipif` und Begründung übersprungen, z. B. „Local part: runs only with TWOX_M3_LOCAL=1 in the test environment with the manuals and the chat model (acceptance run, work order 138).“
- **Wichtig zur Datenbank:** pytest-django legt für Tests mit `django_db` eine leere Testdatenbank an, in der keine Handbücher liegen. Die lokalen Fälle sind deshalb **keine** `django_db`-Tests. Sie starten `python manage.py evaluate_answers --json …` als Unterprozess (`subprocess.run`, `cwd` gleich dem Backend-Verzeichnis, Umgebung geerbt). Der Unterprozess nutzt die konfigurierte Datenbank der Testumgebung, wie `docker compose exec -T api python manage.py evaluate_search` in 060. `backend-dev` hat dieselbe Umgebung wie `api` (`deploy/compose/compose.yaml:279`, `*backend-environment`) und erreicht Ollama am Host über `host.docker.internal` (`compose.yaml:293-294`). Prüfe das und nenne den gewählten Weg im Kurzbericht. Falls der Unterprozess-Weg nicht trägt, ist die Alternative ein JSON-Bericht, den die Leitstelle vorher mit `docker compose exec -T api python manage.py evaluate_answers --json` erzeugt und dessen Pfad der Test aus einer Variablen liest. Dann wird die Abweichung begründet.
- Die Laufbedingungen kommen aus Variablen, die nur über `docker compose run -e …` gesetzt werden und nicht in `.env` stehen:
  - `TWOX_M3_RUNS` (Standard `3`)
  - `TWOX_M3_MODE` (`majority` | `strict`, Standard `majority`, nach der Empfehlung zu D5)
  - `TWOX_M3_MINIMUM` (Standard `8`)

  Ungültige Werte lassen den Test mit Meldung scheitern.
- Der lokale Fall verlangt:
  1. Die KI ist an (`TWOX_AI_ENABLED`), und das Chat-Modell ist konfiguriert. Sonst scheitert der Test mit einer klaren Meldung und wird nicht übersprungen, denn die Abnahme gilt nur mit KI an (D5, D10).
  2. Mindestens `TWOX_M3_MINIMUM` der Fragen 1 bis 10 sind richtig, so wie `evaluate_answers` urteilt.
  3. Die Kontrollfrage 11 ist in **allen** Läufen bestanden: Status `no_evidence` und keine Zitate.
  4. Jede als richtig gewertete Antwort hat mindestens ein gültiges Zitat mit Datei und Seite, bei Markdown mit Datei und Überschriftenpfad (138, Kriterium 2).
  5. Die Fehlermeldung bei Misserfolg nennt je Frage das Urteil, die fehlenden key_facts und die fehlenden Fundstellen, nur als Kennungen. Antworttext und Abschnittstext erscheinen nicht, so wie der JSON-Bericht aus 127.
- Die Auswertung des JSON-Berichts steht in einer reinen Hilfsfunktion im Testmodul, z. B. `judge_report(report: Mapping[str, object], *, minimum: int) -> list[str]`, die die Liste der Verstöße zurückgibt. Sie wird mit **selbst geschriebenen** Berichts-Dicts geprüft: 8/10 mit bestandener Kontrollfrage, 7/10, eine Kontrollfrage mit Zitat, eine richtige Antwort ohne Seite. Diese Tests laufen ohne Schalter in der CI, ohne Datenbank und ohne Netz.
- Das Format des JSON-Berichts legt 127 fest (`backend/twox/answers/evaluation.py`, Kurzbericht 127). Fehlt dort ein Feld, das dieser Test braucht, wird `backend/twox/answers/` **nicht** geändert. Die Lücke kommt in den Kurzbericht und als Frage in diesen Auftrag.

### 2. Browser, CI-Teil `web/e2e/answer.spec.ts` (neu)

- Anmeldung mit dem Testkonto wie in `web/e2e/fixtures.ts` bzw. `m2-acceptance.spec.ts:57-77`. Ab der Anmeldung ist die Konsole fehlerfrei (`collectConsoleErrors` nach dem Muster von `m2-acceptance.spec.ts:80-91`).
- Status-Endpunkt `GET /api/v1/answers/status/` und Antwort-Endpunkt `POST /api/v1/answers/` werden über `page.route` beantwortet. In der CI gibt es kein Chat-Modell; ohne Abfangen meldet der echte Status „nicht verfügbar“, wie in 132 (`answer-page.spec.ts`). Den SSE-Body baut der Test aus Ereignis-Objekten im Format des Ereignisvertrags (`docs/ARCHITECTURE.md`, Abschnitt answers, aus 122 und 130): `content-type: text/event-stream`, die Ereignisse `sources`, `delta`, `done` und `error`. Alle Texte sind selbst geschriebene Testsätze, ohne Herstellertext.
- Hinweis zu `route.fulfill`: Der Body kommt auf einmal an. Ob der Text fortlaufend wächst, prüfen die Vitest-Tests aus 131 und 132. Hier wird geprüft, dass die `delta`-Stücke ankommen und `done.final_text` den gestreamten Text ersetzt. Dazu enthält ein `delta` einen Satz, der in `final_text` fehlt (als entfernt gekennzeichnet nach D8), und dieser Satz ist danach nicht mehr sichtbar.
- Fälle, je in **de und en** (zwei `describe`-Blöcke mit `test.use({ locale: "de-DE" })` bzw. `"en-US"`):
  1. **Frage und Antwort mit Quellen:** Frage eintragen und absenden. Der Anfrage-Body enthält die Frage, die Adresse enthält sie nicht (D14, E-54). Die Antwort erscheint. Die Quellenliste zeigt je Quelle Datei, Seite (z. B. „p. 14“ bzw. „S. 14“) und einen Link auf `/documents/<id>`. Die Markierung `[n]` ist ein Link mit zugänglichem Namen „Source n: <Titel>, page x“ bzw. „Quelle n: …, Seite x“. Ein `<img>` im Antworttext erscheint als Text.
  2. **Ohne Beleg (`no_evidence`):** der feste Satz „Dazu finde ich nichts in den Unterlagen“ bzw. seine englische Fassung aus `answers.json`, ohne Quellenliste.
  3. **KI aus:** Der Status meldet `enabled=false`. Ein ruhiger Hinweis mit Link zur Suche erscheint, Formular und Knopf sind gesperrt, es gibt keinen POST. Zusätzlich: Antwortet der POST mit 409 `ai_disabled`, erscheint derselbe Hinweis.
  4. **Fehler:** Ein `error`-Ereignis, z. B. `model_unavailable`, erscheint in `role="alert"` ohne Rohtext.
  5. **Eingrenzung:** Ein neues Testgerät mit Anlage wird wie in `m2-acceptance.spec.ts:138-148` (`newDevice`) angelegt. `/ask?device=<id>` zeigt den Chip „Eingegrenzt auf: …“ bzw. die englische Fassung. Der Anfrage-Body enthält `device`. „Eingrenzung aufheben“ entfernt Chip und Parameter. Dasselbe gilt für `?plant=<id>`. Der Knopf „Frage zu diesem Gerät“ auf der Geräteseite führt nach `/ask?device=<id>`.
  6. **Erreichbarkeit:** Die Auskunft ist über den Menüpunkt aus 134 erreichbar.
- Die Selektoren sind die `data-testid` und Rollen aus den Kurzberichten von 132 und 133 (z. B. `answer-device`, `answer-plant`, `answer-scope`, `answer-scope-reset`, `device-ask`). Fehlt ein stabiler Selektor, wird nach Rolle und Name gesucht; der Produktcode bleibt unverändert, Ausnahme siehe Nicht-Ziele.
- Zugänglichkeit ohne neue Abhängigkeit (siehe Frage 2 an a7): Im Endzustand gibt es `role="status"` mit kurzer Zustandsmeldung, das Antwort-`article` hat nach `done` `aria-busy="false"`, Fehler stehen in `role="alert"`, der Fokus bleibt nach dem Absenden im Formular, und das Absenden geht mit der Tastatur.

### 3. Browser, lokaler Teil `web/e2e/m3-acceptance.spec.ts` (neu)

- Läuft nur mit `TWOX_M3_LOCAL=1`, sonst `test.skip` mit Begründung wie in `m2-acceptance.spec.ts:488-491`. `test.setTimeout` großzügig, z. B. 600 s, denn das Modell antwortet langsam.
- **Legt keine Daten an:** keine Geräte, kein Upload. Er stellt nur Fragen.
- Am Anfang wird geprüft, dass der Status-Endpunkt `available=true` meldet. Sonst scheitert der Test sofort mit der Meldung „answers not available (AI off or no chat model)“ und wartet nicht bis zur Zeitgrenze.
- Handbücher werden wie in `m2-acceptance.spec.ts:324-348, 423-438` über die SHA-256 aus `testfactory/manifest.yaml` erkannt, nicht über den Dateinamen. Geräte werden über ihren Schlüssel aus `testfactory/layout/devices.csv` gefunden: `ur5e` und, als fremdes Gerät, `drill-plc` (`devices.csv:5, 14`).
- Schritte, Fragen in eigenen Worten, keine Zitate:
  1. **Frage mit Quellenanzeige:** Prüffrage 9, die Nutzlast des UR5e, ohne Eingrenzung (`testfactory/questions.yaml:276-304`). Erwartet: Zustand „beantwortet“; die vereinheitlichte Antwort enthält das key_fact aus `questions.yaml` (`5 kg`, mit „5kg“ als gleichwertig wie in 123); mindestens eine Quelle aus `ur5e-user-manual-de` mit PDF-Seite 16, 101 oder 102. Die Quellenkarte zeigt die Seite und einen Link auf die Datei.
  2. **Eingrenzung:** dieselbe Frage über `/ask?device=<id von ur5e>`. Mindestens eine Quelle gehört zu einem UR5e-Handbuch. Danach über `/ask?device=<id von drill-plc>`: keine Quelle stammt aus einem UR5e-Handbuch (`ur5e-*` im Manifest). Erlaubt sind `no_evidence` oder Quellen des fremden Geräts.
  3. **Kontrollfrage 11** in eigenen Worten, ohne den Hinweistext aus `questions.yaml:352`: Der feste Satz erscheint, ohne Quellenliste und ohne `[n]`.
- Jeder Schritt schreibt Zustand, Zahl der Quellen und Dauer als `test.info().annotations` (Muster `m2-acceptance.spec.ts:557-560`), ohne Antworttext.

### 4. Weitere Dateien

- `deploy/compose/compose.web.yaml`: Der Dienst `e2e` reicht `TWOX_M3_LOCAL: ${TWOX_M3_LOCAL:-}` durch, mit Kommentar nach dem Muster von Z. 46-52. In der Datei steht kein Wert.
- `README.md`: neuer Abschnitt „Acceptance of M3 by hand“ nach „Acceptance of M2 by hand“ (Z. 237-256). Er enthält:
  - die Voraussetzungen: Testumgebung mit Handbüchern, KI an, Chat-Modell gezogen und konfiguriert, Testkonto;
  - die Schrittfolge von Hand, entsprechend Abschnitt 3;
  - beide Befehle für den lokalen Lauf:

    ```sh
    docker compose run --rm -e TWOX_M3_LOCAL=1 -e TWOX_M3_RUNS=3 -e TWOX_M3_MODE=majority backend-dev pytest tests/acceptance/test_m3.py -v
    TWOX_M3_LOCAL=1 docker compose --profile e2e run --rm e2e npx playwright test e2e/m3-acceptance.spec.ts
    ```

  Außerdem wird der Satz in `README.md:469` nachgezogen, nach dem die Prüffragen noch nicht gegen ein Sprachmodell laufen.
- `docs/ARCHITECTURE.md`:
  - Z. 561: `TWOX_M3_LOCAL`, `TWOX_M3_RUNS`, `TWOX_M3_MODE` und `TWOX_M3_MINIMUM` ergänzen;
  - „What CI runs“ (Z. 596): `answer.spec.ts` und den CI-Teil von `test_m3.py` nennen;
  - „What CI does not run“ (Z. 604-605): der lokale Teil der M3-Abnahme;
  - Abschnitt zu den Abnahmetests (Z. 110) ergänzen.

  Die Änderungen sind auf Englisch und berühren nur diese Stellen.

## Nicht-Ziele

- Kein Lauf des lokalen Teils in der Testumgebung „2x“. Das macht die Leitstelle im Abnahmelauf 138 mit dem Modell aus D1 und der kalibrierten Schwelle aus 128.
- Keine Änderung an Produktcode unter `backend/twox/` und `web/src/`. Ausnahme: Fehlt für einen Fall ein stabiler Selektor, darf ein einzelnes `data-testid` ergänzt werden, mit Nennung im Kurzbericht. Gefundene Fehler kommen in den Kurzbericht.
- Keine Änderung an `evaluate_answers`, an den Urteilsregeln (127), an `backend/twox/search/probes/m3.json` (120, 136), an `testfactory/` oder `testfactory/questions.yaml`.
- Keine Änderung an `web/e2e/answer-page.spec.ts` (132), `web/e2e/navigation.spec.ts` (134) und `web/e2e/m2-acceptance.spec.ts`.
- Keine CI-Aufzeichnungen von Modellantworten; das macht 135.
- Keine neue Abhängigkeit, insbesondere kein axe-Paket (siehe Frage 2).
- Keine Herstellertexte, Handbuchauszüge oder Antworttexte in Tests, Annotationen, Kurzbericht oder Doku. Erlaubt sind nur Kennungen, Prüfsummen, Seiten und das key_fact `5 kg` aus `questions.yaml`.

## Betroffene Bereiche (Ordner, Dateien)

- neu: `backend/tests/acceptance/test_m3.py`
- neu: `web/e2e/answer.spec.ts`
- neu: `web/e2e/m3-acceptance.spec.ts`
- `deploy/compose/compose.web.yaml` (nur Dienst `e2e`, Umgebung)
- `README.md` (neuer Abschnitt „Acceptance of M3 by hand“, Satz Z. 469)
- `docs/ARCHITECTURE.md` (nur die in Umfang 4 genannten Stellen)

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`. `D` steht für `docker compose -p twox-137`, `W` für `docker compose -p twox-137-web -f deploy/compose/compose.web.yaml`. Vorher wird `.env.example` mit dem Write-Werkzeug (ohne BOM) nach `.env` kopiert und darin `TWOX_API_PORT=18137` gesetzt. Die Projekte „2x“ und „twox-leit“ werden nicht berührt.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst gilt Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev web-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Backend-Tests:
   - `D run --rm backend-dev pytest tests/acceptance -v` endet mit Exit-Code 0. Die lokalen Fälle von `test_m3.py` sind mit Begründung übersprungen, die Tests von `judge_report` bestanden.
   - `D run --rm backend-dev pytest` endet mit Exit-Code 0 und 0 fehlgeschlagen. Übersprungen sind nur die lokalen Fälle von `test_m3.py`.
   - `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
3. `D run --rm backend-dev ruff check .` meldet `All checks passed!`. `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0. `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
4. Weitere Prüfungen wie in `ci.yml`, jeweils ohne Unterschied zum eingecheckten Stand: `makemessages` mit `git diff --exit-code -I '^"POT-Creation-Date:' -- backend/locale`, `makemigrations --check --dry-run`, `sh scripts/check-licenses.sh`, `spectacular` (unter Git Bash mit `MSYS_NO_PATHCONV=1`) mit `git diff --exit-code -- web/openapi`.
5. Oberfläche wie im CI-Job `web`: Zuerst `W --profile dev build web-dev` und `W run --rm web-dev npm ci`. Danach laufen `npm run lint`, `npm run typecheck` (schließt `e2e/` ein), `npm run test`, `npm run build`, `npm run licenses` und `npm run api:generate` mit `git diff --exit-code -- web/openapi web/src/api`, je über `W run --rm web-dev …` und mit Exit-Code 0.
6. Browsertest wie im CI-Job `e2e`: `D --profile e2e pull e2e`, `D --profile dev run --rm web-dev npm ci`, dann der Schritt „Create test account“ aus `ci.yml` (Z. 238-241) wörtlich, nur mit `D` statt `docker compose`, dann `D --profile e2e run --rm e2e`. Erwartet: alle Fälle bestanden, `answer.spec.ts` in de und en bestanden, `m3-acceptance.spec.ts` und der lokale Teil von `m2-acceptance.spec.ts` übersprungen, Exit-Code 0, Konsole fehlerfrei.
7. Ein zweiter Lauf von Kriterium 6 ohne `down -v` bleibt grün.
8. Der Schalter wirkt und scheitert schnell. Im eigenen Projekt ohne Handbücher und ohne Chat-Modell gilt:
   - `D run --rm -e TWOX_M3_LOCAL=1 backend-dev pytest tests/acceptance/test_m3.py` scheitert mit der Meldung zur fehlenden KI bzw. zum fehlenden Chat-Modell, nicht mit einem Traceback aus dem Unterprozess;
   - `TWOX_M3_LOCAL=1 D --profile e2e run --rm e2e npx playwright test e2e/m3-acceptance.spec.ts` scheitert in unter 60 s mit „answers not available …“.

   Beide Ausgaben stehen gekürzt im Kurzbericht. Die Befehle für den echten Lauf stehen im README.
9. Bei der Eingrenzung auf ein fremdes Gerät verlangt `m3-acceptance.spec.ts`, dass Frage 9 keine Quelle aus einem UR5e-Handbuch hat. Die Bedingung steht im Code und ist im Kurzbericht genannt.
10. `git diff main --stat` zeigt nur die Dateien aus „Betroffene Bereiche“, dazu höchstens einzelne `data-testid` nach den Nicht-Zielen. `package.json`, `package-lock.json`, `pyproject.toml` und die Lock-Datei sind unverändert.
11. Keine Herstellertexte: Eine Suche in den neuen Dateien nach Sätzen aus `expected_answer` und `supports` in `questions.yaml` findet nichts. Befehl und Ergebnis stehen im Kurzbericht.
12. Abräumen: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

- **Herkunft:** Gesamtplan M3, Welle 6. ROADMAP-Kriterium `docs/ROADMAP.md:13`. Muster: 058 (`docs/auftraege/erledigt/058-m2-abnahme-tests.md`) und 090.
- **KI optional (E-59):** Die Abnahme gilt mit `TWOX_AI_ENABLED=1` (D5). Der CI-Teil prüft „KI aus“ als ruhigen Zustand ohne Warnsymbol, wie die Suchseite (`m2-acceptance.spec.ts:306-313`).
- **Andere Sprachfassung (E-61):** Eine Fundstelle in der anderen Sprachfassung desselben Handbuchs zählt. Für Frage 9 gibt es nur die deutsche Quelle (`questions.yaml:285-300`). Die Urteile über alle Fragen trifft `evaluate_answers` (127).
- **Prüffrage 10 (E-33, E-67):** Sie ist im Urteil von `evaluate_answers` enthalten. Der Browsertest verwendet sie nicht, weil ihr Rang je nach Formulierung schwankt (`docs/ARCHITECTURE.md:653`).
- **Prüffrage 8 (D2):** Ist sie nach D2 (b) oder (c) nicht belegt, zählt sie als falsch. Der Test passt die Mindestzahl nicht von selbst an; die Abnahmeregel trägt die Leitstelle über `TWOX_M3_MINIMUM` im Lauf 138 ein, nur nach Entscheidung von a7.
- **Leitplanke 3 und 4:** Die Kontrollfrage darf in keinem Lauf ein Zitat haben. Die Injection-Probe gehört zu 128 und 135, nicht hierher.
- **Datenschutz (D7):** Antworten und Fragen erscheinen weder in Annotationen noch in Testausgaben. Der Bericht von `evaluate_answers` enthält sie nach 127 ebenfalls nicht.
- **Adresse (D14, E-54):** Die Frage steht nur im POST-Body. `?q=` füllt nur das Feld; der CI-Teil prüft, dass `?q=` nichts absendet (kein POST).
- **Vorgaben aus den Vorgängern:** Ereignisvertrag und Fehlercodes stehen in `docs/ARCHITECTURE.md`, Abschnitt answers (122, 130). Fehlerzustände des Hooks stehen in 131 (`docs/auftraege/offen/131-web-antwortstrom-und-hook.md:45`). Texte und `data-testid` der Seite stehen in den Kurzberichten von 132 und 133. Nach dem Zusammenführen liegen diese Auftragsdateien unter `docs/auftraege/erledigt/`.
- **Parallele Aufträge:** 138 baut auf diesem Auftrag auf und führt ihn aus. 128 (Messlauf) und 136 (Beleg Frage 8) laufen ohne Codeänderung bzw. ändern nur `m3.json`; keine gemeinsame Datei. 135 ändert `docs/ARCHITECTURE.md` im Testabschnitt vorher. Hier werden nur die genannten Stellen ergänzt, die Leitstelle führt zusammen.
- **Keine neue Abhängigkeit.** `@types/node` fehlt in `web/`; wie in `m2-acceptance.spec.ts:23-26` werden `process` und `Buffer` lokal deklariert.
- `docs/DECISIONS.md`, `docs/STATUS.md` und `docs/ROADMAP.md` ändert nur die Leitstelle. Kein Push (E-14). Keine Personennamen, keine lokalen Pfade mit Benutzernamen (E-22).

## Fragen an a7 (mit Optionen und Empfehlung)

Der Auftrag ist ohne Antwort startbar; beide Fragen betreffen nur Vorgabewerte bzw. eine Prüfung, die hier nicht eingebaut wird.

1. **D5 Abnahmeregeln: Läufe, Urteil, key_facts (127, 128, 137, 138).**
   - Läufe je Frage: (a) 3 Läufe, Mehrheit; (b) 3 Läufe, alle richtig; (c) 1 Lauf mit Temperatur 0 und festem Seed.
   - Urteil: (d) automatisch vorgeschlagen und von a7 in der Spalte „Urteil a7“ bestätigt; (e) rein automatisch.
   - key_facts: (f) Feld `key_fact_alternatives` in `questions.yaml` als Datenänderung mit Prüfung durch a7; (g) wörtlich lassen.

   Die Abnahme gilt mit `TWOX_AI_ENABLED=1`.
   **Empfehlung:** (a), (d) und (f). Die Kontrollfrage muss in allen Läufen bestanden sein. Dieser Auftrag setzt nur die Vorgaben `TWOX_M3_RUNS=3` und `TWOX_M3_MODE=majority`; beide sind ohne Codeänderung umstellbar.

2. **Zugänglichkeitsprüfung mit axe in den Browsertests (betrifft auch 132 und 134).** Der Gesamtplan verlangt „axe ohne Befund“. Im Repository gibt es aber kein axe-Paket: `web/package.json` hat keinen Treffer, `web/e2e/accessibility.spec.ts` prüft nur mit Rollen und Tastatur. `@axe-core/playwright` wäre eine neue Abhängigkeit; axe-core steht unter MPL-2.0 und braucht nach Leitplanke 7 einen Eintrag im Entscheidungsprotokoll (Stufe C).
   - (a) Ohne axe prüfen, mit Rollen, zugänglichen Namen, `role="status"`/`role="alert"`, `aria-busy` und Tastatur, wie bisher.
   - (b) `@axe-core/playwright` als neue Entwicklungsabhängigkeit in einem eigenen Auftrag (Stufe C, Lizenzeintrag), danach axe in `answer.spec.ts`, `answer-page.spec.ts` und `navigation.spec.ts`.

   **Empfehlung:** (a) für M3. (b) als eigener Auftrag nach der Abnahme, falls a7 eine automatische Regelprüfung will. Bis zur Entscheidung gilt (a).

## Kurzbericht (füllt der Auftragsbearbeiter aus)

- **Was wurde gebaut?**
  - `backend/tests/acceptance/test_m3.py`: reine Hilfsfunktionen `run_conditions()` (liest `TWOX_M3_RUNS`/`_MODE`/`_MINIMUM`, ungültig → `ConditionError` mit Meldung), `judge_report(report, *, minimum) -> list[str]` und `failure_message()` (je Frage Urteil, Läufe, fehlende key_facts, fehlende Fundstellen, nicht eingelesene Handbücher – nur Kennungen). 16 CI-Tests mit selbst geschriebenen Berichten (8/10 und 10/10 bestanden, 7/10, Mindestzahl aus den Bedingungen, Kontrollfrage mit Zitat in einem von drei Läufen, Kontrollfrage mit Fehler bzw. nicht gestellt, richtige Antwort ohne Seite, ohne gültiges Zitat, Markdown mit Überschriftenpfad zählt, nicht gemessener Bericht, Bedingungen und Befehlszeile). Lokaler Fall nur mit `TWOX_M3_LOCAL=1`: KI aus oder Chat-Modell leer → `pytest.fail` ohne Traceback; sonst Unterprozess.
  - **Gewählter Weg: Unterprozess.** `subprocess.run([sys.executable, "manage.py", "evaluate_answers", "--json", "--runs", N, "--mode", M], cwd=/app)` mit geerbter Umgebung, kein `django_db`. Geprüft in twox-137 mit `-e TWOX_M3_LOCAL=1 -e TWOX_M3_RUNS=1 -e TWOX_CHAT_MODEL=e2e-no-such-model`: der Unterprozess las die konfigurierte Datenbank (Fragen 1–10 `not_ingested` mit Manifest-Kennungen, Kontrollfrage `no_evidence`), die Meldung kam ohne Traceback. `backend-dev` hat `*backend-environment` und `host.docker.internal` (compose.yaml), die Protokollzeilen gehen nach stderr, stdout ist reines JSON. Die Alternative mit vorab erzeugtem JSON-Bericht war nicht nötig.
  - Kriterium 4 (Zitat mit Datei und Seite) wird aus `found_places` der richtigen Läufe gelesen (`manifest_id` plus `page` oder nichtleerer `heading_path`) und `valid_citations >= 1`. Kein fehlendes Feld im Bericht von 127; `backend/twox/answers/` unverändert. Die Mindestzahl prüft der Test selbst (`evaluate_answers` kennt kein `--required`), die Kontrollfrage wird je Lauf geprüft (Status `no_evidence`, `valid_citations == 0`).
  - `web/e2e/answer.spec.ts`: je de und en sieben Fälle – Erreichbarkeit über die Hauptnavigation; Frage und Antwort per Strg+Enter (`?q=` sendet nichts, Frage nur im POST-Body, Adresse ohne Frage, Fokus bleibt im Feld, `role="status"` „Fertig“/„Done“, `article` mit `aria-busy="false"`, entfernter `delta`-Satz nicht mehr sichtbar, Hinweis „Nicht belegte Aussagen …“, `<img>` als Text ohne `img`-Element, `[1]` als Link mit Namen „Quelle 1: e2e test manual, Seite 14“, Quellenkarte mit „S. 14“/„p. 14“, Dateiname und Link `/documents/<id>`, Klick fokussiert die Karte ohne `#` in der Adresse); ohne Beleg; KI aus (kein POST) und 409 `ai_disabled`; `error` `model_unavailable` in `role="alert"` ohne Rohtext; Eingrenzung über den Knopf „Frage zu diesem Gerät“, Chip, `device: [id]` im Body, „Eingrenzung aufheben“, dasselbe mit `?plant=`. Beide Endpunkte per `page.route`, SSE-Body im Vertragsformat.
  - `web/e2e/m3-acceptance.spec.ts`: nur mit `TWOX_M3_LOCAL=1`, `setTimeout(600 s)`, legt nichts an, prüft zuerst `GET /api/v1/answers/status/` und scheitert sofort mit „answers not available (AI off or no chat model) …“. Handbücher über SHA-256 aus dem Manifest (`documentsOf`), Geräte über die Schlüssel `ur5e` und `drill-plc`. Schritte wie Umfang 3; Annotationen `step` mit Zustand, Zahl der Quellen und Dauer.
  - **Kriterium 9:** Im Schritt „question 9 limited to the UR5e and to another device“ wird für `/ask?device=<drill-plc>` verlangt: Zustand `answered`, `contradiction` oder `no_evidence` und `expect(foreign).toEqual([])`, wobei `foreign` die Datei-Ids der angezeigten Quellenkarten sind, deren neueste Version die Prüfsumme eines der vier `ur5e-*`-Handbücher hat.
  - `compose.web.yaml` reicht `TWOX_M3_LOCAL` an `e2e` durch; README Abschnitt „Acceptance of M3 by hand“ mit beiden Befehlen; ARCHITECTURE an den vier Stellen.
- **Wie wurde getestet?** (Projekte twox-137 und twox-137-web, `.env` aus `.env.example` mit `TWOX_API_PORT=18137`)
  - 0: `docker version`/`docker compose version` Exit 0. 1: Build und `up --wait` Exit 0.
  - 2: `pytest tests/acceptance -v`: 32 bestanden, 1 übersprungen (lokaler Fall mit Begründung). `pytest`: 3536 bestanden, 1 übersprungen (derselbe), 0 fehlgeschlagen. `pytest -m worker`: 6 bestanden.
  - 3: ruff `All checks passed!`, `ruff format --check` Exit 0, mypy `Success: no issues found in 230 source files`.
  - 4: makemessages ohne Unterschied, `No changes detected`, Lizenzprüfung Exit 0, spectacular ohne Unterschied.
  - 5: lint, typecheck, test, build, licenses, api:generate je Exit 0, kein Unterschied in `web/openapi web/src/api`.
  - 6 und 7: zwei Läufe ohne `down -v`, je `102 passed, 2 skipped` (lokale Teile M2 und M3), Exit 0; `answer.spec.ts` 14/14 in de und en.
  - 8: `D run --rm -e TWOX_M3_LOCAL=1 backend-dev pytest tests/acceptance/test_m3.py` → `No chat model configured (TWOX_CHAT_MODEL is empty): the acceptance of M3 needs the chat model (D5, D10).`, `1 failed, 16 passed`. Mit `-e TWOX_AI_ENABLED=false` → `The AI features are off (TWOX_AI_ENABLED): …`; mit `-e TWOX_M3_MODE=most` → `Invalid TWOX_M3_MODE='most': expected majority or strict.` Browser: `Error: answers not available (AI off or no chat model): enabled=true, chat_model_configured=false`, Test 399 ms, Befehl gesamt 4 s.
  - 10: `git diff main...HEAD --stat` zeigt nur die sechs Dateien aus „Betroffene Bereiche“ (dazu diese Auftragsdatei); keine `data-testid` ergänzt, `package.json`, `package-lock.json`, `pyproject.toml`, `uv.lock` unverändert.
  - 11: Skript im Container (`python -I`, eingebunden lesend): alle Sätze (≥ 20 Zeichen) und alle Folgen von sechs Wörtern aus `expected_answer` und `supports` (63 Texte) gegen die neuen und geänderten Dateien. Treffer nur „Dazu finde ich nichts in den Unterlagen“ (fester Satz der Anwendung, Leitplanke 3) und in ARCHITECTURE zusätzlich das bereits vorhandene „Die Unterlagen widersprechen sich“; kein Herstellertext.
  - 12: siehe Rückmeldung an die Leitstelle (nach dem Commit ausgeführt).
- **Zweig und Arbeitsverzeichnis:** `worktree-agent-a28999db5c1ff0d8d` in `.claude/worktrees/agent-a28999db5c1ff0d8d`, Basis `9809570`. Nicht gepusht.
- **Abweichungen und Befunde:**
  - Zeilennummern im Auftrag waren verschoben (ARCHITECTURE: Konfiguration Z. 620, „What CI runs“ Z. 649, „does not run“ Z. 660, Layout Z. 109; README: der Satz aus Z. 469 steht jetzt im Abschnitt „What the CI does not run“). Zusätzlich im README die Zeile „Expected output … the local part of the M2 acceptance test is skipped“ um M3 ergänzt, damit sie stimmt.
  - **Befund (Produktcode, nicht geändert):** Beim Absenden per Mausklick wird der Knopf „Fragen“ während des Stroms gesperrt (`Button` mit `loading` setzt `disabled`), der Fokus fällt dadurch aus dem Formular auf die Seite. Mit Strg+Enter bleibt er im Feld (so geprüft). Der Klickfall prüft den Fokus deshalb nicht; Vorschlag: eigener kleiner Auftrag (Fokus nach `done` zurück ins Feld oder `aria-disabled` statt `disabled`).
  - Zum Formatieren der zwei neuen Spezifikationen wurde einmalig `npx prettier@3.10.1 --print-width 120` im Wegwerf-Container ausgeführt (keine Abhängigkeit, nichts in `package.json`).
  - Der lokale Browsertest erkennt UR5e-Quellen über die Datei-Id der ersten Fundstelle der Karte und die Prüfsumme der neuesten Version (wie `documentsOf` in M2). Eine Quelle aus einer älteren Version eines Handbuchs würde nicht als UR5e erkannt.
