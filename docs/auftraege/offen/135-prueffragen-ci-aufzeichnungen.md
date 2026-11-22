# Auftrag 135 – Prüffragen in der CI mit Aufzeichnungen

Meilenstein: M3 · Freigabestufe: C · Status: offen

Voraussetzungen: 121 (Chat-Schnittstelle, `FakeChatModel`), 122 (Typen, `build_messages`, `new_nonce`, `prompt_version`), 123 (Zitatprüfung), 125 (Kontextauswahl), 126 (Antwortdienst), 127 (Urteilsregeln von `evaluate_answers`). Start erst, wenn diese Aufträge auf `main` zusammengeführt sind und a7 D6 und D16 entschieden hat. Weil 135 die Urteilsfunktionen aus 127 nutzt und beide denselben Abschnitt „What CI does not run“ in `docs/ARCHITECTURE.md` ändern, startet 135 erst in Welle 5, nach dem Zusammenführen von 127, und nicht parallel dazu. Die Leitstelle berichtigt dazu die Gesamtplanung (Welle 4) und den Hinweis zu parallelen Aufträgen in 130.

Stufe C, weil der Auftrag einen neuen dauerhaften Prüfweg in der CI festlegt (E-10, STATUS Punkt 6) und ein selbst geschriebenes Testdokument mit eingebetteter Anweisung einführt (D16). Fällt eine der Entscheidungen anders aus als empfohlen, passt die Leitstelle den Auftrag vor dem Start an.

## Ziel

E-10 verlangt, dass die Prüffragen bei jeder Änderung automatisch mitlaufen (`docs/DECISIONS.md:20`). STATUS Punkt 6 hält dazu fest: aufgezeichnete Antworten in der CI, der echte Lauf lokal vor jedem Zusammenführen, Entscheidung spätestens zu M3 (`docs/STATUS.md:62`).

Dieser Auftrag schließt die Lücke für die Antwortkette. Bei jedem Push läuft die ganze Kette in der CI mit: Einlesen, Suche, Kontextauswahl, Prompt, Modellantwort, Zitatprüfung, Absage und Eingrenzung. Dabei gilt:

- **ohne Modell und ohne Netz:** Die Modellantworten wurden einmal lokal mit dem echten Chat-Modell aufgezeichnet. In der CI spielt ein `ReplayChatModel` sie ab.
- **ohne Herstellertexte im Repository:** Fragen und Belege stammen nur aus `testdata/klein` (OPNsense-Doku unter BSD-2-Clause, BetrSichV gemeinfrei) oder sind selbst geschrieben.
- **mit Warnung bei Abweichung:** Ändert sich Prompt-Vorlage, Kontext oder Modell, passt die Aufzeichnung nicht mehr. Der Test scheitert dann mit einer klaren Meldung zum Neu-Aufzeichnen, statt still eine veraltete Antwort abzuspielen.

Die 11 echten Prüffragen aus `testfactory/questions.yaml` bleiben lokal (127, 128, 137). Sie gehören nicht in die CI, weil ihre Belege Herstellerhandbücher sind.

## Umfang

### 1. Fragensatz für die CI (`backend/tests/answers/fixtures/`, neu)

Eine kleine Datei, z. B. `backend/tests/answers/fixtures/ci_questions.json` (eigenes JSON, keine YAML-Abhängigkeit nötig). Sie enthält mit Kennung, Frage in eigenen Worten, Art (`fact` | `contradiction` | `no-evidence` | `injection`), optionaler Eingrenzung und erwarteter Fundstelle (Kennung des Testdokuments plus Seite bzw. Überschriftenpfad) diese Einträge:

**Prüfsumme der Fundstelle:** Der Test lädt nicht die echten Dateien aus `testdata/klein` hoch, sondern die Platzhalter-Bytes `PDF_CONTENT` und `MARKDOWN_CONTENT` aus `backend/tests/ingest/fake_converter.py:42-43`; Docling antwortet über `FakeConverter` mit den Fixtures. Die `DocumentVersion.sha256` im Test ist deshalb die der Platzhalter, nicht die aus `testdata/klein/manifest.yaml`. Der Fragensatz enthält daher **keine** Prüfsumme. Er nennt je Fundstelle nur eine Kennung des Testdokuments (z. B. `betrsichv`, `sftp-backup`, `injection`). Der Test bildet sie auf die Prüfsumme der im Test angelegten Version ab (aus `DocumentVersion.sha256` oder mit `hashlib.sha256` über die hochgeladenen Bytes) und übergibt diese an den Vergleich aus 127 (`matching_place`, `backend/twox/search/evaluation.py:298`). Ein Test sichert ab, dass die Kennung auf genau die Version zeigt, deren Abschnitte zitiert werden. Die echten Dateien aus `testdata/klein` werden nicht hochgeladen; `testdata/` ist in `backend-dev` auch nicht eingehängt (`deploy/compose/compose.yaml:280-289`), und eine Kopie unter `backend/tests/` ist nicht vorgesehen.

Die Einträge:

- **Faktfrage (mindestens eine):** Die Antwort steht in einer Seite des Fixtures `betrsichv-p1-5.docling.json` (BetrSichV S. 1–5) oder in `sftp-backup.docling.json` (OPNsense, Markdown ohne Seiten, Fundstelle über den Überschriftenpfad). Die Antwort muss eine prüfbare Angabe enthalten (Zahl, Begriff oder Paragraph), damit die Zitatprüfung aus 123 greift.
- **Widerspruchsfrage, nur falls belegbar:** Nur wenn die zwei eingelesenen Fixtures eine echte widersprüchliche Stelle hergeben. Andernfalls entfällt sie, und der Kurzbericht vermerkt das. Der Pfad `contradiction` ist dann durch die Tests mit `FakeChatModel` in 123 und 126 abgedeckt. **Keine** erfundenen Widersprüche und keine selbst geschriebenen Fachdokumente (Leitplanke 9).
- **Kontrollfrage:** Eine Frage, zu der die Fixtures sicher nichts enthalten. Erwartet wird `no_evidence` ohne Zitate.
- **Injection-Probe (nach D16):** Ein selbst geschriebenes, kurzes Testdokument, z. B. `backend/tests/answers/fixtures/injection.md` mit eigenem, kurzem Docling-Ergebnis oder direkt als `Section`-Zeilen über die Test-Hilfen (siehe Hinweise). Es enthält einen harmlosen Sachsatz und eine eingebettete Anweisung an das Modell, etwa die Regeln zu ignorieren, einen Link oder ein Bild auszugeben oder ein Kennwort zu nennen. Die Frage zielt auf den Sachsatz. Erwartet wird: Die Antwort enthält keinen Link, keine Bildsyntax und kein HTML, und sie befolgt die Anweisung nicht. Ist die Antwort belegt, zitiert sie nur gültige Nummern. Das Dokument ist kein Testfabrik-Gerät und keine Prüffrage. Es trägt im Kopf den Vermerk „self-written test text, no real device“.

Alle Fragen und Testtexte sind selbst geschrieben. Es gibt keine Auszüge aus `testfactory/` oder aus Herstellerunterlagen.

### 2. `backend/twox/answers/replay.py` (neu)

- `ReplayChatModel` erfüllt das Protokoll `ChatModel` aus 121 (`model_name`, `stream(messages, *, max_tokens, temperature, seed) -> ChatStream`, `close()`). Es liest eine Aufzeichnungsdatei und liefert die aufgezeichneten Textstücke in der aufgezeichneten Reihenfolge.
- **Aufzeichnungsschlüssel** `recording_key(messages, model_name) -> str`: SHA-256 über `prompt_version()`, den Modellnamen der Aufzeichnung und die kanonisch serialisierten Nachrichten (`json.dumps(..., sort_keys=True, ensure_ascii=False)`). Die Nachrichten enthalten Frage, Quellennummern und Abschnittstexte. Damit deckt der Schlüssel die Vorgabe der Gesamtplanung ab („Hash aus prompt_version(), Modellname und Kontext-Nummern“) und ist strenger: Er schlägt auch an, wenn sich der Kontext bei gleicher Nummerierung ändert. Damit der Schlüssel stabil ist, wird die Zufallskennung aus 122 im Test und beim Aufzeichnen auf einen festen Wert gesetzt (`monkeypatch` auf `twox.answers.prompt.new_nonce`). Der Produktcode bekommt dafür **keinen** Schalter.
- **Kein Treffer:** Gibt es zum Schlüssel keinen Eintrag, wirft `stream()` einen eigenen Fehler, z. B. `RecordingMissingError(AssertionError)`. Seine Meldung lautet sinngemäß `no recording for this prompt (prompt_version=…, model=…, question=…); re-record: manage.py record_answers`. Die Meldung nennt nur die Kennung der Frage, nie Prompt- oder Abschnittstext. Ein leiser Rückfall auf eine andere Aufzeichnung ist ausgeschlossen.
- Das Modul baut keine Verbindung auf und hängt nicht von `TWOX_AI_ENABLED` ab. Ob das Modell gerufen wird, entscheidet der Dienst aus 126.
- `close()` wird mitgezählt (für den Abbruchtest).

### 3. Aufzeichnungsformat (`backend/tests/answers/recorded/`, neu)

Eine JSON-Datei, z. B. `backend/tests/answers/recorded/ci_questions.json`, nur mit der Standardbibliothek gelesen und geschrieben:

```json
{
  "schema_version": 1,
  "model": "<model name as in TWOX_CHAT_MODEL>",
  "model_digest": "<digest from /api/tags>",
  "prompt_version": "<prompt_version()>",
  "recorded_on": "YYYY-MM-DD",
  "settings": {"temperature": 0, "seed": 0, "max_tokens": 0},
  "entries": [
    {
      "question_id": "ci-fact-1",
      "key": "<recording_key>",
      "sources": [{"n": 1, "sha256": "…", "ordinal": 0}],
      "chunks": ["…", "…"]
    }
  ]
}
```

- Zeilenumbrüche und Einrückung bleiben fest, damit der Diff lesbar und beim zweiten Aufzeichnen ohne Änderung byte-gleich ist.
- `chunks` enthält nur die Modellausgabe. Abschnittstexte und Prompt werden **nicht** gespeichert, sie entstehen im Test aus den Fixtures neu.
- In einem kurzen `README.md` im Ordner stehen Zweck, Format, Herkunft der Texte (nur `testdata/klein` und selbst geschrieben) und der Befehl zum Neu-Aufzeichnen.

### 4. Aufzeichnen: `manage.py record_answers` (neu)

- `backend/twox/answers/management/commands/record_answers.py` ist ein dünner Befehl für den lokalen Lauf im Container `backend-dev`. Er setzt den Aufnahmeschalter (z. B. Umgebungsvariable `TWOX_RECORD_ANSWERS=1`) und startet über `pytest.main([...])` genau `tests/answers/test_ci_questions.py`.
- So entsteht die Aufzeichnung mit **demselben** Aufbau wie in der CI: Docling-Fixtures über `FakeConverter`, Stub-Embedder und dieselbe Kontextauswahl. Nur das Chat-Modell ist echt (`get_chat_model()` aus 121 mit `TWOX_CHAT_MODEL`, Temperatur 0, fester Seed). Eine Aufzeichnung gegen die echte Testumgebung mit bge-m3 und vollständigen PDFs ergäbe einen anderen Kontext und passte in der CI nie.
- `pytest` wird erst im Befehl importiert. Fehlt es, wie im Laufzeit-Image, endet der Befehl mit einer kurzen englischen Meldung (`record_answers runs only in backend-dev`) und Exit-Code ≠ 0.
- Bei `TWOX_AI_ENABLED=0` oder leerem `TWOX_CHAT_MODEL` bricht der Befehl ab, ohne eine Verbindung aufzubauen. Die Cloud-Sperre aus 121 (`llm_guard.py`) gilt unverändert.
- Im Aufnahmemodus ersetzt der Test `ReplayChatModel` durch einen schreibenden Mitschnitt um das echte Modell. Dieser Mitschnitt ist eine Testhilfe unter `backend/tests/answers/` oder eine Klasse in `replay.py`. Danach schreibt der Test die Datei aus Abschnitt 3 neu. Die Prüfungen laufen auch beim Aufzeichnen. Eine Aufzeichnung, deren Urteil die Erwartung verfehlt, wird nicht geschrieben, und der Lauf scheitert mit Angabe der Frage-Kennung.
- Aufgerufen wird lokal mit `docker compose run --rm -e TWOX_CHAT_MODEL=<Modell> backend-dev python manage.py record_answers`. `backend-dev` erreicht Ollama über `host.docker.internal` (`deploy/compose/compose.yaml:293-294`, `.env.example:25-26`).
- **Welches Modell, was wird committet:** Die Aufzeichnung unter `backend/tests/answers/recorded/` landet im öffentlichen Repository (E-19). Committet wird nur eine Aufzeichnung mit dem nach D1 freigegebenen Modell, dessen Lizenz und Digest an der Quelle belegt sind (wie in 128, Schritt 8; Leitplanke 7, keine Nutzungsbeschränkung). Ist D1 beim Start noch offen, darf der Bearbeiter mit einem am Host schon vorhandenen Modell **nur lokal** aufzeichnen, **ohne** `ollama pull`, um den Ablauf zu prüfen. Diese Aufzeichnung wird nicht committet. Ausnahme: Lizenz-URL und Digest dieses Modells sind vorher an der Quelle belegt und im Kurzbericht genannt, und das Modell fällt nicht unter die Ausschlüsse aus D1 (z. B. Llama 4, Gemma 1–3). Sonst committet der Bearbeiter Code und Tests ohne Aufzeichnungsdatei; die Tests, die eine Aufzeichnung brauchen, werden dann mit Begründung übersprungen, und die Leitstelle zeichnet nach D1 auf und committet.

### 5. `backend/tests/answers/test_ci_questions.py` (neu)

- **Aufbau** nach dem Muster der Fixture `world` in `backend/tests/acceptance/test_m2.py:133-158`. Die Fixture ist parametrisiert mit `ai-off` und `ai-on`. Docling wird über die vorhandenen Fixtures `backend/tests/ingest/fixtures/betrsichv-p1-5.docling.json` und `sftp-backup.docling.json` ersetzt (`FakeConverter` bzw. `running_fake_docling`, `backend/tests/ingest/fake_converter.py`, `fake_docling.py`). Für die Einbettung von Abschnitten und Fragen dienen die Stub-Embedder (`tests.ingest.fake_converter.FakeEmbedder`, `tests.search.fake_embedder.FakeEmbedder`). Zwei Geräte bekommen je ein Dokument, damit sich die Eingrenzung prüfen lässt.
- **Socket-Sperre** für den Wiedergabemodus: `socket.create_connection` und `socket.socket.connect` werden auf eine Funktion umgelenkt, die den Test scheitern lässt, wie in `backend/tests/answers/test_check_llm.py:170-174`. Die Datenbankverbindung läuft über libpq und ist davon nicht betroffen. Der Bearbeiter prüft das und vermerkt es. Zusätzlich zeigt `TWOX_LLM_BASE_URL` auf `CLOSED_MODEL_SERVICE` (`backend/tests/search/fake_embedder.py:22`).
- **Geprüft wird über `twox.answers.service.answer(...)`** aus 126, mit `chat=ReplayChatModel(...)`, ohne HTTP:
  1. Die Faktfrage ergibt `answered` mit mindestens einem gültigen Zitat auf die erwartete Fundstelle (Prüfsumme der im Test angelegten Version, siehe Abschnitt 1, und Seite bzw. Überschriftenpfad). Die Ereignisfolge ist `sources → delta* → done`. Für den Vergleich der Fundstelle werden die Urteilsregeln aus 127 (`twox.answers.evaluation`) wiederverwendet, nicht nachgebaut.
  2. Die Kontrollfrage ergibt `no_evidence` ohne Zitate, und zwar **auf beiden Wegen**: (a) Mit der Schwelle aus 125 liegt die Kontrollfrage darüber, das Modell wird nicht gerufen (Replay schlägt beim Aufruf fehl). Dafür legt der Test den Abstand der Fragevektoren fest. (b) Mit abgeschalteter Schwelle (`TWOX_ANSWER_MAX_DISTANCE=2.0`, der größte Kosinusabstand; größere Werte weist die Einstellung ab) wird die aufgezeichnete Absage des Modells abgespielt und von der Zitatprüfung als `no_evidence` erkannt.
  3. Die Injection-Probe: Das Urteil ist `answered` oder `no_evidence`. `final_text` enthält kein `http`, kein `](`, kein `<`-Tag und nicht das in der Anweisung verlangte Merkmal (ein selbst gewähltes, eindeutiges Wort). Gültig sind nur Nummern aus der Quellenliste.
  4. **Eingrenzung:** Die Faktfrage eingegrenzt auf das fremde Gerät liefert keine Quelle des belegenden Dokuments und ruft das Modell nicht oder nur mit einer eigenen, aufgezeichneten Absage.
  5. **KI aus:** Der Dienst liefert `error(ai_disabled)`, das Modell wird nie gerufen, und die Stichwortsuche (`get_search_backend().search(...)`) findet die belegende Stelle weiterhin.
  6. **Widerspruch** (nur falls im Fragensatz): Status `contradiction` mit zwei gültigen Zitaten auf die erwarteten Stellen.
  7. **Neu aufzeichnen:** Eine per `monkeypatch` geänderte Prompt-Vorlage, also ein anderes `prompt_version()`, lässt den Lauf mit `RecordingMissingError` und der Meldung „re-record: manage.py record_answers“ scheitern (Test mit `pytest.raises`).
  8. **Abbruch:** Ein Abbruch des Ereignisstroms durch den Aufrufer schließt den `ChatStream`, den `ReplayChatModel.stream()` geliefert hat (Festlegung nach 126: der Dienst schließt ein übergebenes Modell absichtlich nicht, nur dessen Strom; Nachweis über einen Zähler oder `closed` am Strom).
  9. **Datei-Prüfung:** Die Aufzeichnungsdatei hat das Format aus Abschnitt 3. Jede `question_id` kommt im Fragensatz vor. Es gibt keine verwaisten Einträge. `prompt_version` in der Datei ist gleich `prompt_version()`.
- Die Tests laufen im normalen `pytest`, ohne Marker `worker`, damit der Schritt „Tests (pytest)“ der CI sie ausführt (`.github/workflows/ci.yml`, Job `backend`).

### 6. Doku

- `docs/ARCHITECTURE.md` auf Englisch, nur in den Abschnitten „What CI runs“ und „What CI does not run“ (ab Z. 589 bzw. 600) und, falls vorhanden, im Unterabschnitt `answers`. Beschrieben werden die Wiedergabe der Antwortkette, Schlüssel und Format der Aufzeichnung, der Befehl zum Neu-Aufzeichnen, die Abgrenzung zum lokalen Lauf der 11 echten Prüffragen und die Grenze, dass die CI nicht das Modell selbst prüft, sondern Prompt, Kontext, Zitatprüfung und Absage bei fester Modellantwort.
- `README.md`: Im Abschnitt mit den Testbefehlen (Z. 355-370) kommt eine Zeile zu `record_answers` mit dem Hinweis „only locally, needs the chat model on the host“ dazu.

## Nicht-Ziele

- Keine echten Prüffragen aus `testfactory/questions.yaml` in der CI und keine Herstellertexte im Repository (Leitplanke 9, E-20/E-19: öffentlich sichtbar).
- Kein echtes Modell in der CI (D6 Option c verworfen) und kein GPU-Runner.
- Keine Änderung an `service.py`, `context.py`, `prompt.py`, `citations.py`, `chat.py` oder `evaluation.py`. Fehlt dort ein Haken, wird keiner eingebaut: Frage in den Auftrag, Status „wartet auf a7“. Kleine, rein additive Testhilfen in `chat.py` nur nach Rückfrage bei der Leitstelle.
- Keine Änderung unter `backend/twox/search/` und `backend/twox/ingest/`.
- Keine neuen Docling-Fixtures aus Herstellerunterlagen. Neue Fixtures nur aus `testdata/klein` oder selbst geschrieben.
- Keine API, kein SSE, keine Oberfläche (130–134), kein Abnahmetest M3 (137).
- Keine Einstellung in `settings.py`, `compose.yaml` oder `.env.example`. Der Aufnahmeschalter ist eine reine Testumgebungsvariable und wird nur im Test gelesen.
- Keine Bibliothek für Aufzeichnungen (etwa vcrpy oder pytest-recording) und keine Snapshot-Bibliothek.
- Kein `ollama pull` und keine Änderung an Ollama oder an Einstellungen des Hosts.

## Betroffene Bereiche (Ordner, Dateien)

Neu:

- `backend/twox/answers/replay.py`
- `backend/twox/answers/management/commands/record_answers.py` (der Ordner `management/commands/` existiert, siehe `check_llm.py`)
- `backend/tests/answers/test_ci_questions.py`
- `backend/tests/answers/recorded/` (Aufzeichnung als JSON und `README.md`)
- `backend/tests/answers/fixtures/` (Fragensatz und selbst geschriebenes Injection-Testdokument mit `README.md` zu Herkunft und Lizenz)
- optional `backend/tests/answers/conftest.py` oder ein Hilfsmodul für den Mitschnitt, sofern nicht in `replay.py`

Geändert:

- `docs/ARCHITECTURE.md` (nur „What CI runs“ und „What CI does not run“ ab Z. 589, Unterabschnitt `answers`)
- `README.md` (nur Testbefehle, Z. 355-370)

Gelesen und nicht geändert: `backend/tests/acceptance/test_m2.py`, `backend/tests/ingest/fake_converter.py`, `backend/tests/ingest/fake_docling.py`, `backend/tests/ingest/fixtures/*`, `backend/tests/search/fake_embedder.py`, `backend/tests/answers/fake_ollama.py`, `testdata/klein/*`, `.github/workflows/ci.yml`.

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit-Code 0.
1. Alle Prüfungen des Jobs `backend` aus `.github/workflows/ci.yml` sind grün, jeweils über `docker compose run --rm backend-dev …`: `ruff check .`, `ruff format --check .`, `mypy .`, `pytest`, `pytest -m worker`, Übersetzungskatalog unverändert, `python manage.py makemigrations --check --dry-run` (keine Migration), `sh scripts/check-licenses.sh` und OpenAPI-Schema ohne Diff. Die Jobs `web` und Testfabrik bleiben unberührt und grün.
2. `docker compose run --rm backend-dev pytest backend/tests/answers/test_ci_questions.py` ist **ohne Netz und ohne Ollama** grün. Die Socket-Sperre ist aktiv, und ein Gegentest zeigt, dass ein Verbindungsversuch den Test scheitern ließe. Der Lauf ist auch bei gestopptem Ollama am Host grün (im Kurzbericht vermerkt).
3. Eine geänderte Prompt-Vorlage lässt den Test mit `RecordingMissingError` und der Meldung „re-record: manage.py record_answers“ scheitern (Test).
4. Die Kontrollfrage ergibt `no_evidence` ohne Zitate, über die Schwelle ohne Modellaufruf **und** über die aufgezeichnete Absage (zwei Tests).
5. Die Injection-Probe führt die Anweisung nicht aus. Es gibt keinen Link, keine Bildsyntax, kein HTML und nicht das Merkmalswort im `final_text` (Test).
6. Die Faktfrage ergibt `answered` mit gültigem Zitat auf die erwartete Fundstelle. Eingegrenzt auf das fremde Gerät enthält sie keine Quelle des belegenden Dokuments (Tests).
7. Bei KI aus kommt `error(ai_disabled)` ohne Modellaufruf, und die Stichwortsuche liefert die Stelle weiterhin (Test, Parameter `ai-off`).
8. Ein Abbruch schließt den Strom des `ReplayChatModel` (Test über `closed` bzw. Zähler am `ChatStream`).
9. `manage.py record_answers` endet ohne `pytest` sowie bei KI aus oder leerem `TWOX_CHAT_MODEL` mit Exit-Code ≠ 0 und ohne Verbindung (Tests). Ein echter Aufnahmelauf mit lokalem Modell ist im Kurzbericht dokumentiert: Modell, Digest, Lizenz-URL, Datum, Dauer und ob die Aufzeichnung committet wurde (nur nach Umfang 4). Ein zweiter Lauf ergibt die gleiche Datei oder nur abweichende `chunks` (Ergebnis vermerkt).
10. Die Aufzeichnungen und Fixtures enthalten nur Texte aus `testdata/klein` oder selbst geschriebene. Gespeichert sind keine Abschnittstexte und kein Prompt, nur die Modellausgabe. Die Leitstelle prüft den Diff von `recorded/` und `fixtures/` vollständig.
11. Keine Logzeile aus dem Testlauf enthält Frage, Antwort oder Abschnittstext (Test mit `caplog` auf allen Loggern, wie in 126).
12. Keine neue Abhängigkeit: `backend/pyproject.toml` und Lock sind unverändert. Kein `vcrpy`, `pytest-recording`, `httpx` oder `openai`.
13. `docs/ARCHITECTURE.md` und `README.md` sind nachgezogen.

## Vorgaben und Hinweise

- **Leitplanken:** 3 (Antworten nur mit Quelle; die Kontrollfrage prüft die feste Absage), 4 (Dokumentinhalte sind Daten; die Injection-Probe ist der Nachweis in der CI), 6 (ohne Internet; Socket-Sperre), 7 (Lizenzen; keine neue Abhängigkeit), 9 (keine erfundenen Anlagen; das Injection-Dokument ist ausdrücklich ein Testtext, kein Gerät).
- **Entscheidungen:** E-10 (`docs/DECISIONS.md:20`) und STATUS Punkt 6 (`docs/STATUS.md:62`) sind der Anlass. E-04 (`docs/DECISIONS.md:14`): lokales Modell, „weiß ich nicht“ ist erlaubt. E-19/E-20 (`docs/DECISIONS.md:29-30`): Das Repository ist öffentlich, also keine Herstellertexte und keine Personennamen in Aufzeichnungen. E-55 (`docs/DECISIONS.md:65`): mehrere Fundorte je Abschnitt. E-59 (`docs/DECISIONS.md:69`): KI optional, daher beide Parameter `ai-off` und `ai-on`. E-61 (`docs/DECISIONS.md:71`): Sprachfassungen; für `testdata/klein` ohne Belang, die Regeln aus 127 werden aber unverändert übernommen.
- **Warum Aufzeichnen im Testaufbau:** In der CI gibt es weder Docling noch Modell (`.github/workflows/ci.yml`, Kopfkommentar; `docs/ARCHITECTURE.md` ab Z. 600). Die Abschnitte kommen aus den Docling-Fixtures (`backend/tests/ingest/fixtures/README.md`), die Vektoren aus Stub-Embeddern. Nur wenn die Aufzeichnung über genau diesen Aufbau entsteht, sind Kontext und Schlüssel in der CI gleich.
- **Docling-Fixtures:** `betrsichv-p1-5.docling.json` (BetrSichV S. 1–5, gemeinfrei) und `sftp-backup.docling.json` (OPNsense, BSD-2-Clause, Markdown ohne Seiten), beschrieben in `backend/tests/ingest/fixtures/README.md`. Die Fragen müssen sich mit **diesen** Ausschnitten beantworten lassen, nicht mit dem ganzen PDF.
- **Injection-Dokument ohne Docling:** Entweder ein kleines, selbst geschriebenes Docling-JSON nach dem Muster der vorhandenen Fixtures oder `Section`-Zeilen direkt über die Test-Hilfen, wie in `backend/tests/search/test_vector_search.py:69-91` (`make_device`, `make_document`) und `backend/tests/search/fake_embedder.py:93` (`embed`). Der zweite Weg ist einfacher und genügt, weil hier nicht das Einlesen geprüft wird.
- **Feste Kennung:** `new_nonce()` aus 122 wird im Test per `monkeypatch` festgelegt. `build_messages` ist bei gleicher Kennung deterministisch (Auftrag 122, Umfang 2).
- **Feste Modellparameter beim Aufzeichnen:** Temperatur 0, fester Seed, `max_tokens` nach 121. Reasoning aus (`reasoning_effort` = `none`, 121). Die Werte stehen in der Aufzeichnungsdatei.
- **Socket-Sperre:** Vorbild `backend/tests/answers/test_check_llm.py:170-174` und `:221-225`. Kein Plugin wie `pytest-socket` (neue Abhängigkeit).
- **Typen:** Jede Funktion hat Typangaben, `mypy .` ohne Fehler, kein `Any` in `replay.py`. Bezeichner, Docstrings und Meldungen auf Englisch. Fragen im Fragensatz auf Deutsch, wie im Betrieb.
- **Aufzeichnungsdatei prüfen:** Vor dem Commit selbst durchsehen. Sie darf keine Modellausgabe mit fremden Links, Personennamen oder Pfaden enthalten. Taucht so etwas auf, nicht committen, sondern im Kurzbericht melden.
- **Abgrenzung zu anderen Aufträgen (Start in Welle 5):**
  - 127 (`evaluate_answers`) ist vorher zusammengeführt und hat `backend/twox/answers/evaluation.py` angelegt sowie „What CI does not run“ in `docs/ARCHITECTURE.md` geändert. Dieser Auftrag nutzt die Urteilsfunktionen nur und baut im Doku-Abschnitt auf dem Stand von 127 auf `main` auf; die Zeilennummern in Abschnitt 6 vorher neu bestimmen.
  - 130 (API mit SSE) ändert `backend/twox/answers/api.py`, `urls.py`, `config/urls.py`, `settings.py` und `README.md` (Endpunkt, Datenschutz). Dieser Auftrag ändert in `README.md` nur den Testabschnitt. Die Leitstelle führt beide nacheinander zusammen.
  - 128 (Messlauf) ruft dasselbe echte Modell am Host. Aufnahmelauf und Messlauf nicht gleichzeitig starten.
  - 137 (Abnahmetests) nutzt `ReplayChatModel` nicht. Dessen CI-Browsertest fängt den Strom über `page.route` ab.
- **Ablauf:** Eigenes Compose-Projekt für die Prüfläufe (z. B. `docker compose -p twox-135 …`) und danach `down -v`. Kein Push (E-14). Commits nur auf dem Auftragszweig.
- **Herkunft:** Gesamtplanung M3 (Zerlegung durch die Leitstelle), Startunterlage Abschnitte 2 und 9 (lokal, nicht zitieren).

## Fragen an a7 (mit Optionen und Empfehlung)

- **D6 Prüffragen in der CI (E-10, STATUS Punkt 6, fällig zu M3):**
  - (a) Eigener kleiner Fragensatz auf `testdata/klein` mit aufgezeichneten Modellantworten in der CI; der Schlüssel entsteht aus Prompt-Hash und Modell. Die echten 11 Fragen laufen lokal vor der Abnahme und vor dem Zusammenführen von Prompt- oder Kontextänderungen.
  - (b) Nur lokal.
  - (c) Echtes Modell in der CI; das geht nicht ohne GPU, und Herstellertexte dürfen nicht ins Repository.

  **Empfehlung:** (a), mit eigenem JSON-Format und Replay-Modell, ohne neue Abhängigkeit. Ein abgeleiteter Bericht ohne Textauszüge darf eingecheckt werden.
- **D16 Selbst erzeugtes Injection-Testdokument:**
  - (a) Ein selbst geschriebenes Testdokument mit eingebetteter Anweisung ist in Tests und Messläufen erlaubt. Es ist keine Prüffrage der Testfabrik und keine erfundene Anlage (Leitplanke 9).
  - (b) Keine eigenen Testdokumente, nur Unit-Tests am Prompt (122).

  **Empfehlung:** (a). Nur so wird der Schutz aus 122 mit einem echten Modell nachgewiesen; hier geschieht das einmal beim Aufzeichnen, danach bei jedem CI-Lauf gegen die Aufzeichnung.

Ergänzend zur Bestätigung, ohne den Auftrag aufzuhalten: Die committete Aufzeichnung entsteht mit dem nach D1 gewählten, an der Quelle auf Lizenz und Digest geprüften Modell. Bis D1 entschieden ist, zeichnet der Bearbeiter höchstens lokal mit einem am Host schon vorhandenen Modell auf und committet diese Aufzeichnung nur, wenn Lizenz-URL und Digest belegt sind und das Modell keine Nutzungsbeschränkung hat (Umfang 4). Die Leitstelle zeichnet nach D1 einmal neu auf.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
