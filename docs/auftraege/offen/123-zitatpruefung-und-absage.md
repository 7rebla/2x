# Auftrag 123 – Zitatprüfung und feste Absage

Meilenstein: M3 · Freigabestufe: B · Status: zur Prüfung

## Ziel

Nach der Erzeugung einer Antwort prüft der Server deterministisch, ob sie belegt ist (Leitplanke 3: Antworten nur mit Quelle). Unbelegte Aussagen werden verworfen oder gekennzeichnet. Bleibt kein gültiger Beleg, gilt die feste Absage „Dazu finde ich nichts in den Unterlagen“. So entsteht keine Antwort ohne Quelle, und die beiden Sonderfälle der Abnahme lassen sich maschinell bewerten: die Kontrollfrage 11 (`testfactory/questions.yaml:350-357`, Art `no-evidence`) und die Widerspruchsfrage 6 (`testfactory/questions.yaml:178-200`, Art `contradiction`).

Ergebnis ist eine reine Funktion ohne Datenbank, ohne Netz und ohne Modell. Sie wird später vom Antwortdienst (126) nach dem Modellstrom aufgerufen; ihr Ergebnis füllt das Ereignis `done` (Vertrag aus 122) und ist die Grundlage für das Messwerkzeug (127).

## Umfang

### 1. Modul `backend/twox/answers/citations.py` (neu)

Öffentliche Schnittstelle (Namen verbindlich, damit 126 und 127 parallel planen können):

```python
NO_EVIDENCE_TEXT: Final = "Dazu finde ich nichts in den Unterlagen."
CONTRADICTION_PHRASE: Final = "Die Unterlagen widersprechen sich"

VerdictStatus = Literal["answered", "no_evidence", "contradiction"]
IssueReason = Literal["no_citation", "unknown_citation", "unsupported_value"]

@dataclass(frozen=True, slots=True)
class SentenceIssue:
    index: int                         # 0-based position of the sentence in the answer
    reason: IssueReason
    values: tuple[str, ...]            # check values not found (only for unsupported_value)
    invalid_numbers: tuple[int, ...]   # cited numbers outside the source set

@dataclass(frozen=True, slots=True)
class Verdict:
    status: VerdictStatus
    cited: tuple[int, ...]             # valid source numbers used in kept sentences, ascending, unique
    removed_sentences: tuple[SentenceIssue, ...]   # dropped or flagged sentences
    cleaned_text: str                  # final text for done.final_text

def verify(
    answer_text: str,
    sources: Mapping[int, str],
    *,
    drop_unsupported: bool,
) -> Verdict: ...
```

`sources` bildet die Quellennummer `n` (1..k aus der Kontextauswahl) auf den Abschnittstext ab, den das Modell gesehen hat. Weitere Hilfsfunktionen bleiben privat (`_split_sentences`, `_extract_citations`, `_check_values`, `_normalise`). Die Statuswerte sind dieselben Zeichenketten wie im Ereignis `done` aus 122 (`answered | no_evidence | contradiction`).

### 2. Ablauf von `verify`

1. **Sätze bilden.** Der Text wird in Sätze zerlegt, ohne den Wortlaut zu ändern (Positionen im Original merken):
   - Satzende ist `.`, `!` oder `?` mit folgendem Leerraum oder Textende, außerdem jeder Zeilenumbruch. Listenpunkte (`-`, `*`, `1.` am Zeilenanfang) sind eigene Sätze.
   - Kein Satzende nach gängigen Abkürzungen (mindestens `z. B.`, `d. h.`, `u. a.`, `bzw.`, `ca.`, `ggf.`, `vgl.`, `usw.`, `inkl.`, `Nr.`, `S.`, `Abb.`, `Tab.`, `Kap.`), nicht innerhalb von Zahlen, IP-Adressen und Versionsangaben (`1.5`, `192.168.0.5`, `V2.3.1`) und nicht bei Ordnungszahlen mit folgender Ziffer oder Kleinbuchstaben.
   - Quellennummern, die direkt hinter dem Satzzeichen stehen (`… 24 V. [2]`), gehören zum vorangehenden Satz.
   - Leere Sätze (nur Leerraum oder nur Nummern ohne Text) entfallen.
2. **Nummern sammeln.** Erkannt werden `[n]`, `[n, m]` (auch mit `;`) und `[n][m]`. `n` ist eine positive Ganzzahl. Andere Formen (`[1-3]`, `[Quelle 2]`, hochgestellte Ziffern) gelten nicht als Beleg. Gültig ist eine Nummer nur, wenn sie ein Schlüssel von `sources` ist.
3. **Prüfkennzeichen bilden.** Je Satz werden die prüfbaren Werte gesammelt:
   - Zahlen mit Einheit (`5 kg`, `5kg`, `24 V DC`, `0,5 bar`, `400 mm`, `10 ms`, `16 A`, `50 Hz`, `°C`, `%`); die Einheitenliste ist eine Konstante im Modul und im Docstring genannt.
   - IPv4 und IPv6 (mit optionalem Präfix), MAC-Adressen.
   - Ports (`Port 502`, `:502` hinter einer Adresse).
   - Versionsangaben (`V18`, `v2.3.1`, `Version 4.1`, `Firmware 5.12`).
   - Typbezeichnungen aus Buchstaben und Ziffern (`S7-1200`, `1512SP`, `UR5e`).
   Für IP, MAC und Typbezeichnungen wird `find_identifiers` aus `backend/twox/search/identifiers.py:138` wiederverwendet (nur importieren, nicht ändern); Zahl mit Einheit, Port und Version ergänzt das Modul mit eigenen Ausdrücken. Die Quellennummern selbst (`[2]`) sind keine Prüfkennzeichen.
4. **Vereinheitlichen und vergleichen.** Satzwerte und Quelltexte werden gleich vereinheitlicht: Unicode NFKC, `casefold`, alle Bindestrich- und Strichvarianten (`‐ ‑ ‒ – —` und geschütztes Leerzeichen) auf `-` bzw. Leerzeichen, dann Leerraum und `-` entfernt; Dezimalkomma zwischen zwei Ziffern wird zu Punkt. Damit gelten `5 kg`/`5kg`, `S7-1200`/`S7 1200` und `0,5 bar`/`0.5 bar` als gleich. Ein Wert gilt als gefunden, wenn er im vereinheitlichten Text **mindestens einer im selben Satz gültig zitierten** Quelle vorkommt, mit Grenzen: davor und danach keine Ziffer bzw. kein Buchstabe, der den Wert verlängert (`192.168.0.5` trifft nicht `192.168.0.50`, `5 kg` nicht `25 kg`). Die Quelltexte werden je Aufruf nur einmal vereinheitlicht.
5. **Satzurteil.** Ein Satz ist
   - `unknown_citation`, wenn er nur ungültige Nummern trägt;
   - `no_citation`, wenn er keine Nummer trägt;
   - `unsupported_value`, wenn er gültige Nummern trägt, aber ein Prüfkennzeichen in keiner davon steht;
   - sonst belegt. Ungültige Nummern in einem belegten Satz (`[2][9]` bei 5 Quellen) werden aus dem Satz entfernt und in `invalid_numbers` vermerkt; der Satz bleibt.
   Ausnahmen ohne Nummer: der Absagesatz und ein Satz, der nur die Widerspruchs-Wendung enthält.
6. **Bereinigte Fassung.** Bei `drop_unsupported=True` werden unbelegte Sätze aus `cleaned_text` entfernt (mit dem folgenden Leerraum, Absätze bleiben erhalten), bei `False` bleiben sie stehen und stehen nur in `removed_sentences`. Belegte Sätze bleiben wörtlich, bis auf entfernte ungültige Nummern. Kein Umformulieren.
7. **Gesamturteil.**
   - `no_evidence`: Die Antwort ist leer, besteht nur aus der Absage (Vergleich nach Vereinheitlichung ohne Satzzeichen und Anführungszeichen, also mit und ohne Punkt) oder enthält nach Schritt 5 keinen belegten Satz. Dann ist `cited` leer und `cleaned_text == NO_EVIDENCE_TEXT`, unabhängig von `drop_unsupported`. `removed_sentences` nennt die verworfenen Sätze.
   - `contradiction`: Die Antwort enthält `CONTRADICTION_PHRASE` (vereinheitlicht verglichen) und die belegten Sätze zitieren mindestens **zwei verschiedene** gültige Nummern.
   - `answered`: sonst. Enthält eine Antwort mit belegten Sätzen zusätzlich den Absagesatz (Teilantwort), bleibt der Absagesatz stehen und das Urteil ist `answered`.
   - Die Widerspruchs-Wendung mit weniger als zwei verschiedenen gültigen Nummern ergibt kein `contradiction`, sondern das Urteil nach den übrigen Regeln.

### 3. Tests `backend/tests/answers/test_citations.py` (neu)

Tabellengetrieben mit `pytest.mark.parametrize`, ohne Datenbank (kein `django_db`), mit selbst geschriebenen Texten zu einer erfundenen, neutralen Beispielmaschine (keine Herstellertexte, keine echten Handbuchsätze). Mindestens die Fälle aus den Akzeptanzkriterien, dazu Satzzerlegung (Abkürzungen, IP am Satzende, Nummern hinter dem Punkt, Listenpunkte) und `cleaned_text` mit Absätzen.

## Nicht-Ziele

- Keine inhaltliche Prüfung über Prüfkennzeichen hinaus (keine Bedeutungsprüfung, kein Modellaufruf, kein Embedding-Vergleich).
- Kein Ereignisstrom, keine Typen aus `types.py` (122), kein Prompt (122), kein Dienst (126), keine API, keine Oberfläche.
- Keine Änderung unter `backend/twox/search/` (nur Import aus `identifiers.py`).
- Keine Einstellung in `settings.py`, kein `TWOX_*`-Schalter. `verify` hängt nicht von `TWOX_AI_ENABLED` ab; ob überhaupt geprüft wird, entscheidet der Dienst (126).
- Keine Übersetzungstexte (`gettext`): Gründe sind feste englische Codes.
- Keine Änderung an `testfactory/questions.yaml`.

## Betroffene Bereiche (Ordner, Dateien)

- neu: `backend/twox/answers/citations.py`
- neu: `backend/tests/answers/test_citations.py`
- nur gelesen bzw. importiert: `backend/twox/search/identifiers.py`

Vorhanden sind in `backend/twox/answers/` bisher nur `__init__.py`, `apps.py`, `embeddings.py` und `management/commands/check_llm.py`; in `backend/tests/answers/` `__init__.py`, `fake_ollama.py`, `test_check_llm.py`, `test_embeddings.py`. Diese bleiben unverändert.

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md:355-370`.

- `D` steht für `docker compose -p twox-123`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18123` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. `D run --rm backend-dev pytest tests/answers/test_citations.py -v` endet mit Exit-Code 0 und enthält mindestens diese Fälle:
   1. Die erfundene Nummer `[9]` bei 5 Quellen wird verworfen; ein Satz nur mit `[9]` ist `unknown_citation`, ein Satz mit `[2][9]` bleibt ohne `[9]`, `invalid_numbers == (9,)`.
   2. Ein Satz mit einer IP-Adresse, die in keinem im Satz zitierten Abschnitt steht, ist `unsupported_value`; steht sie nur in einem nicht zitierten Abschnitt, ebenfalls. `192.168.0.5` gilt nicht als gefunden, wenn die Quelle nur `192.168.0.50` enthält.
   3. `5 kg` und `5kg` gelten als gleich, ebenso `0,5 bar`/`0.5 bar` und `S7-1200`/`S7 1200`; `5 kg` gilt nicht als gefunden in einer Quelle mit nur `25 kg`.
   4. Die Absage mit und ohne Schlusspunkt, mit Anführungszeichen und mit umgebendem Leerraum ergibt `no_evidence`, `cited == ()`, `cleaned_text == NO_EVIDENCE_TEXT`.
   5. Eine Antwort ohne jede Nummer ergibt `no_evidence` ohne Zitate.
   6. Sind alle Sätze unbelegt (gemischt aus `no_citation`, `unknown_citation`, `unsupported_value`), ergibt das `no_evidence`, und `removed_sentences` nennt jeden Satz mit Grund.
   7. Die Widerspruchs-Wendung mit zwei gültigen, verschiedenen Zitaten ergibt `contradiction`; mit nur einer Nummer (auch zweimal dieselbe) nicht.
   8. `drop_unsupported=True` entfernt unbelegte Sätze aus `cleaned_text`, `False` lässt sie stehen; in beiden Fällen ist `removed_sentences` gleich.
   9. Laufzeit: `verify` mit 8 Quellen à 2 000 Zeichen und einer Antwort von etwa 1 500 Zeichen braucht im Mittel aus 20 Läufen unter 50 ms (`time.perf_counter`).
   10. Satzzerlegung: `z. B.`, `S. 34`, `V2.3.1` und eine IP am Satzende trennen nicht falsch; `[2]` hinter dem Punkt gehört zum vorigen Satz.
   11. Teilantwort: belegter Satz plus Absagesatz ergibt `answered`, der Absagesatz bleibt im Text.
   12. Leere Antwort und Antwort nur aus Leerraum ergeben `no_evidence`; leere `sources` ergeben `no_evidence` für jede Antwort.
3. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen; `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
4. `D run --rm backend-dev ruff check .` meldet `All checks passed!`, `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0, `D run --rm backend-dev mypy .` meldet `Success: no issues found`. Jede Funktion hat Typangaben.
5. Weitere Prüfungen wie in `ci.yml`, jeweils ohne Unterschied zum eingecheckten Stand:
   - `D run --rm backend-dev python manage.py makemessages -l de --add-location=file`, danach `git diff --exit-code -I '^"POT-Creation-Date:' -- backend/locale`;
   - `D run --rm backend-dev python manage.py makemigrations --check --dry-run` endet mit Exit-Code 0;
   - `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0;
   - `MSYS_NO_PATHCONV=1 D run --rm -v "$PWD/web/openapi:/out" backend-dev python manage.py spectacular --file /out/schema.yml`, danach `git diff --exit-code -- web/openapi`.
   Der Web- und der Testfabrik-Teil der CI sind nicht berührt; sie bleiben grün, weil keine Datei darin geändert wird.
6. `git diff --stat main...` zeigt nur die zwei neuen Dateien. Keine neue Abhängigkeit (`backend/pyproject.toml` und Lockdatei unverändert).
7. Der Docstring von `citations.py` beschreibt die Regeln aus Umfang 2 (Satzgrenzen, Nummernformen, Prüfkennzeichen, Vereinheitlichung, Urteil) auf Englisch.
8. Abräumen: `D --profile dev down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

- **Welle 1, parallel zu 120, 121 und 122.** Keine gemeinsamen Dateien. `docs/ARCHITECTURE.md` (Abschnitt `answers`, `docs/ARCHITECTURE.md:134`) ändert in dieser Welle 122; dieser Auftrag beschreibt seine Regeln nur im Modul-Docstring, die Leitstelle übernimmt beim Zusammenführen einen Satz und den Verweis nach `ARCHITECTURE.md`.
- **Abgrenzung zu 122:** 122 legt `types.py` (u. a. `DoneEvent` mit `status`, `cited`, `removed_sentences`, `final_text`) und den Prompt an. `citations.py` importiert nichts aus `types.py` und `prompt.py`. Die Statuswerte und die Konstanten `NO_EVIDENCE_TEXT` und `CONTRADICTION_PHRASE` müssen zu 122 passen; beim Zusammenführen gleicht die Leitstelle ab (Vorschlag: `prompt.py` importiert beide Konstanten aus `citations.py`, damit der Wortlaut nur an einer Stelle steht). Weicht der Wortlaut in 122 ab, wird der Kurzbericht das nennen, nicht 122 geändert.
- **Abgrenzung zu 126 und 127:** Der Dienst (126) ruft `verify` mit den Quelltexten aus der Kontextauswahl (125) und `drop_unsupported` nach D8 auf und baut daraus `done`. Das Messwerkzeug (127) wertet `status` und `cited` aus. Beides ist nicht Teil dieses Auftrags.
- **Widerspruchs-Wendung:** „Die Unterlagen widersprechen sich“ entspricht der erwarteten Antwort zu Frage 6 (`testfactory/questions.yaml:183`). Sie ist eine Konstante, damit eine spätere Entscheidung nur eine Stelle ändert.
- **Absage:** Wortlaut nach Leitplanke 3 (`CLAUDE.md`, Leitplanken) und Kontrollfrage 11 (`testfactory/questions.yaml:355-357`).
- **Sprachfassungen (E-61, `docs/DECISIONS.md:71`):** Die Prüfung kennt keine Dokumente, nur Nummern; ob eine en-Quelle für eine de-Antwort zählt, entscheidet 127. Prüfkennzeichen sind sprachneutral, deshalb funktioniert der Vergleich auch gegen englische Abschnitte.
- **Mehrere Fundorte (E-55, `docs/DECISIONS.md:65`)** betreffen die Quellenliste, nicht die Prüfung.
- **KI optional (E-59, `docs/DECISIONS.md:69`):** `verify` ist ohne KI aufrufbar und braucht deshalb keinen Test für beide Zustände; es liest keine Einstellung.
- **Leitplanke 4 (Dokumentinhalte sind Daten):** Quelltexte werden nur verglichen, nie ausgewertet oder ausgeführt. Reguläre Ausdrücke werden nur aus festen Mustern gebaut; Werte aus Antwort oder Quelle gehen nie ungeschützt in ein Muster (`re.escape`). Laufzeit muss bei ungünstigen Eingaben linear bleiben (keine verschachtelten Quantoren); ein Test mit 20 000 Zeichen ohne Satzzeichen bleibt unter der Zeitgrenze.
- **Keine Ausgabe von Texten:** `verify` protokolliert nichts. Ausnahmen enthalten keinen Antwort- oder Abschnittstext (vorbereitend für die Log-Tests in 126 und 130, D7).
- **Testtexte selbst schreiben** (Arbeitsregel „Keine längeren Auszüge aus fremden Handbüchern“, Leitplanke 9 gilt sinngemäß): neutrale Beispielwerte wie `Greifer G-12`, `24 V`, `10.0.0.7`, keine Sätze aus Handbüchern der Testfabrik.
- Tests laufen im Container aus dem Verzeichnis `backend` (`testpaths = ["tests"]`, `backend/pyproject.toml:81-87`), daher `tests/answers/...` statt `backend/tests/answers/...` im Befehl.
- Muster für reine Prüffunktionen mit Tabellentests: `backend/twox/search/identifiers.py` und seine Tests unter `backend/tests/search/`.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Commits klein auf dem eigenen Zweig, nicht auf `main`. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

1. **D8 Absage-Regel und Teilantworten** (betrifft 123, 125, 126). Der Auftrag ist ohne Entscheidung startbar, weil `verify` beide Varianten über `drop_unsupported` anbietet; die Entscheidung legt nur fest, wie der Dienst (126) es aufruft.
   - Absage: (a) harte Regel im Code: Ohne Treffer unter der kalibrierten Schwelle kommt der feste Satz ohne Modellaufruf; das Modell darf selbst absagen, und die Zitatprüfung verwirft unbelegte Antworten. (b) Regel nur im Prompt.
   - Teilantworten: (c) unbelegte Sätze entfernen und die Entfernung kennzeichnen; (d) die ganze Antwort verwerfen, sobald ein Satz unbelegt ist.
   - Empfehlung: (a) und (c). Lokale Modelle neigen dazu, Belege zu erfinden; eine Regel nur im Prompt reicht für die Kontrollfrage nicht. Bis zur Entscheidung gilt „entfernen und kennzeichnen“ (`drop_unsupported=True`, verworfene Sätze in `removed_sentences`). Variante (d) ließe sich im Dienst aus `removed_sentences` ableiten, ohne dieses Modul zu ändern.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- **Was wurde gebaut?** `backend/twox/answers/citations.py` mit der verbindlichen Schnittstelle (`NO_EVIDENCE_TEXT`, `CONTRADICTION_PHRASE`, `VerdictStatus`, `IssueReason`, `SentenceIssue`, `Verdict`, `verify`) sowie den öffentlichen Konstanten `UNITS` und `ABBREVIATIONS`. Reine Funktion ohne Datenbank, Netz, Modell, Einstellung und Protokollausgabe. Satzzerlegung über Positionen im Original (je Zeile, Listenmarken nicht Teil des Satzes), Quellennummern `[n]`, `[n, m]`, `[n; m]`, `[n][m]` (höchstens sechs Ziffern), Prüfkennzeichen aus eigenen Ausdrücken (Zahl mit Einheit, Port, Version) und `find_identifiers` (IP, MAC, Typbezeichnungen; nur importiert). Vergleich auf vereinheitlichtem Text ohne Leerraum und `-`, wobei gemerkt wird, wo Leerraum oder `-` stand, damit die Grenzregeln (`192.168.0.5` ≠ `192.168.0.50`, `5 kg` ≠ `25 kg`) trotz Entfernen gelten. Kein Wert aus Antwort oder Quelle geht in ein Muster (Suche mit `str.find`). Die Regeln stehen auf Englisch im Modul-Docstring, einschließlich der Einheitenliste. Konstanten mit gleichem Wortlaut wie in 122 (`types.py`), dort als maßgeblich vorgesehen; beim Zusammenführen auf Import aus `types.py` umstellen.
- **Wie wurde getestet?** `tests/answers/test_citations.py`, 94 Fälle, tabellengetrieben, ohne Datenbank, nur selbst geschriebene Texte zu einem erfundenen Greifer G-12. Abgedeckt: alle Fälle 2.1–2.12 der Akzeptanzkriterien, dazu Grenzfälle (IPv6, MAC, Port hinter Adresse, `24 V` gegen `24 VDC`, `V18` gegen `Version 18`, geschützte Bindestriche), Regex-Sonderzeichen als reiner Text, Docstring nennt jede Einheit, Laufzeit typisch ca. 4 ms und sechs ungünstige Eingaben mit je 20 000 Zeichen unter 50 ms. Im Container (`docker compose -p twox-123`, Port 18123): Build und `up --wait` Exit 0; `pytest tests/answers/test_citations.py -v` 94 bestanden; `pytest` 2486 bestanden, 0 fehlgeschlagen; `pytest -m worker` 6 bestanden; `ruff check .` „All checks passed!“; `ruff format --check .` Exit 0; `mypy .` „Success: no issues found in 197 source files“; `makemessages` Exit 0 ohne Unterschied unter `backend/locale`; `makemigrations --check --dry-run` „No changes detected“; `check-licenses.sh` Exit 0; `spectacular` Exit 0 ohne Unterschied unter `web/openapi`; `git diff --stat main...` nur die zwei neuen Dateien; `--profile dev down -v` Exit 0.
- **Zweig und Arbeitsverzeichnis:** `worktree-agent-ae3973aba54a10337`, `.claude/worktrees/agent-ae3973aba54a10337`.
- **Abweichungen und Auslegungen:**
  1. Ein belegter Satz mit erfundener Nummer (`[2][9]`) bleibt im Text (ohne `[9]`) und steht trotzdem in `removed_sentences`, mit Grund `unknown_citation`, `invalid_numbers == (9,)` und (seit der Nachbesserung) `kept=True`. `removed_sentences=len(...)` in 126 zählt gekennzeichnete und verworfene Sätze, wie 122 es festlegt; `Verdict.dropped_count` zählt nur die verworfenen. Bei `no_evidence` enthält `removed_sentences` nur die verworfenen Sätze.
  2. Als Ausnahme gilt der Absagesatz auch dann, wenn er Nummern trägt (`… Unterlagen [2].` zählt nicht als Beleg). Der Satz, der nur aus der Widerspruchs-Wendung besteht, ist nur ohne Nummer ausgenommen. Ausgenommene Sätze sind weder belegt noch gelistet. Eine Antwort nur aus der Widerspruchs-Wendung ergibt deshalb `no_evidence`.
  3. `in` und `t` fehlen in der Einheitenliste (zu oft gewöhnliche Wörter). `24 V DC` wird als `24 V` geprüft, ein folgendes `AC`/`DC` in der Quelle verlängert den Wert nicht.
  4. `usw.` und weitere Abkürzungen beenden nie einen Satz, auch nicht am echten Satzende; dann werden zwei Sätze gemeinsam geprüft.
  5. `docs/ARCHITECTURE.md` nicht geändert (wie vorgegeben). Keine neue Abhängigkeit, keine offene Frage an a7.
- **Nachbesserung (nach Prüfung der Leitstelle):** `identifiers.py` unverändert, nichts aus `types.py` importiert.
  1. Keine still übersprungenen Werte: `find_identifiers` wird je Leerraum-Token aufgerufen (keine Zehnergrenze), ein führendes `-` wird vor der Einordnung entfernt. Tests: elf Adressen, die letzte erfunden, ergibt `unsupported_value`; `-K7` gegen eine Quelle mit `-K3` ergibt `unsupported_value`.
  2. `_SENTENCE_END` ist linear (`(?<![.!?])[.!?]++…`, possessive Quantoren). Der Laufzeittest für die typische Antwort bleibt bei 50 ms. Für 14 ungünstige Eingaben (darunter `'.' * 20000 + 'x'`) gilt jetzt: Wachstum t(20000)/t(5000) < 8 (bester von drei Läufen, kleine Zeit mit 1 ms Untergrenze) und t(20000) < 1 s.
  3. Eine Typbezeichnung mit unmittelbar folgendem, nur durch Leerraum getrenntem Ziffern-Token ist ein Wert (`S7 1500` ergibt `s71500`). Das gilt nicht, wenn die Ziffern eine Zahl mit Einheit beginnen; `Seite 34` und `Port 502` bleiben getrennt. Tests: `S7 1500 [1]` gegen `S7-1200` ergibt `unsupported_value`, `S7 1200` gegen `S7-1200` ist belegt. Die frühere Abweichung „S7 1200 nur als S7 geprüft“ entfällt.
  4. `SentenceIssue.kept: bool` (neues Pflichtfeld am Ende) und die Eigenschaft `Verdict.dropped_count`, beide im Docstring beschrieben. `removed_sentences` ist unverändert.
  5. `contradiction` gilt nur, wenn die Wendung am Anfang des ersten nicht verworfenen Satzes steht (nach führenden Satzzeichen oder Anführungszeichen) und danach bis zum Satzzeichen oder Satzende kein weiteres Wort folgt. Auslegung von „kein Buchstabe folgt“: Leerraum wird übersprungen, sonst würde `widersprechen sich nicht` weiter zählen. Folge: `Die Unterlagen widersprechen sich bei der Spannung …` ergibt ebenfalls kein `contradiction`. Tests: mit `nicht`, Wendung nicht im ersten Satz, Wendung in Anführungszeichen, erster Satz verworfen.
  6. `S.`, `Nr.`, `No.`, `Abb.`, `Tab.`, `Kap.` und `Fig.` gelten nur großgeschrieben als Abkürzung. Test: `… 10 s. Der Greifer …` ergibt zwei Sätze.
  7. Ein Minuszeichen gehört zur Zahl: `-20 °C` gegen `20 °C` ergibt `unsupported_value`, ebenso umgekehrt. Bereiche wie `2-5 kg` bleiben unberührt. Angehängte Wortteile mit mindestens vier Buchstaben werden abgeschnitten (`S7-1200-Steuerung` prüft `S7-1200`). Zahl und Einheit dürfen mit `-` verbunden sein (`24-V-Versorgung` prüft `24 V`). Je ein positiver und ein negativer Test.
  8. Öffentliche Funktion `normalise_value(text: str) -> str` für 127, mit Test.
  
  Prüfungen nach der Nachbesserung (twox-123):
  - Build und `up --wait` Exit 0.
  - `pytest tests/answers/test_citations.py -v`: 129 bestanden.
  - `pytest`: 2521 bestanden, 0 fehlgeschlagen. `pytest -m worker`: 6 bestanden.
  - `ruff check .` „All checks passed!“, `ruff format --check .` Exit 0, `mypy .` „Success: no issues found in 197 source files“.
  - `makemessages`, `check-licenses.sh` und `spectacular` Exit 0, ohne Unterschied unter `backend/locale` und `web/openapi`. `makemigrations --check` meldet „No changes detected“.
  - `--profile dev down -v` Exit 0.
- **Nachbesserung 2 (nach zweiter Prüfung der Leitstelle):**
  1. Typbezeichnung und Ziffern werden nur zusammengezogen, wenn das Token nach Entfernen der führenden Zeichen genau die Bezeichnung ist: nichts abgeschnitten, kein nachgestelltes `,` `:` `;` `)`. Tests:
     - `Die Steuerung S7-1200, 2 Erweiterungsmodule [1].` gegen eine wörtlich gleiche Quelle ergibt `answered`.
     - `G-1, 2 Stück [1].` gegen eine Quelle mit `G-12` ergibt `unsupported_value`.
     - `Typ G-12: 3 Finger [1].` wörtlich belegt ergibt `answered`.
  2. Angehängte Wortteile werden vor `find_identifiers` abgeschnitten: `-` gefolgt von mindestens vier Buchstaben (Unicode, `str.isalpha`) am Tokenende, Satzzeichen danach bleiben. Die Laufzeit bleibt linear. Tests:
     - `S7-1500-Ausführung` gegen `S7-1200` ergibt `unsupported_value`.
     - `S7-1200-Gerät` gegen `S7-1200` ist belegt.
     - `G-12-Baugröße` ist gegen `G-12` belegt, `G-14-Baugröße` nicht.
  3. Kleines `s.` (siehe) gilt als Abkürzung, außer direkt nach einer Zahl (`10 s.` beendet den Satz). Test: `(s. Abb. 3) [1]` bleibt in einem Satz.
  4. `_PORT_WORD`, `_CITATION`, `_CITATION_RUN`, `_SENTENCE_END` und `_VERSION_WORD` haben possessive Leerraum-Quantoren. `_CITATION_RUN` beginnt nur am Anfang eines Leerraumlaufs. Der neue Test `test_space_runs_in_checked_sentences_stay_linear` deckt `Port` + Leerraumlauf (mit und ohne Zahl) und Zitatläufe mit langen Leerräumen ab, mit und ohne folgende Klammer. Ein Zähler auf `_check_values` belegt, dass die Sätze geprüft werden. Bei Zitatläufen wird zusätzlich die bereinigte Fassung verglichen.
  5. Absolute Grenze für ungünstige Eingaben: 1 s für 20 000 Zeichen, festgelegt von der Leitstelle. Dazu kommt das Wachstumsmaß t(20000)/t(5000) < 8.

  Prüfungen nach Nachbesserung 2 (twox-123):
  - Build und `up --wait` Exit 0.
  - `test_citations.py`: 141 bestanden.
  - `pytest`: 2533 bestanden, 0 fehlgeschlagen. `pytest -m worker`: 6 bestanden.
  - `ruff check .` „All checks passed!“, `ruff format --check .` Exit 0, `mypy .` „Success: no issues found in 197 source files“.
  - `makemessages`, `check-licenses.sh` und `spectacular` Exit 0, ohne Unterschied. `makemigrations --check` meldet „No changes detected“.
  - `down -v` Exit 0.
- **Nachbesserung 3 (nach dritter Prüfung der Leitstelle):** `main` zuerst konfliktfrei in den Zweig geführt (mit 120, 121, 124, 136). `.env` danach neu aus `.env.example` erzeugt.
  1. Kleines `s.` gilt nur nach Leerraum oder `(` als Abkürzung, und nicht direkt nach einer Zahl. `10 s.`, `10s.`, `250 mm/s.` und `100 Mbit/s.` beenden den Satz. Tests: beide Einheitenfälle ergeben zwei Sätze, `(s. Abb. 3) [1]` bleibt ein Satz.
  2. Wortteile werden nur abgeschnitten, wenn sie mindestens vier Buchstaben haben und Kleinbuchstaben enthalten. Großbuchstaben-Teile wie `-ENBT` bleiben. Bleiben nur Ziffern übrig, wird das ganze Token geprüft. Tests:
     - `1756-ENBT` gegen `1756-EN2T` ergibt `unsupported_value`.
     - `S7 1500-Steuerung` gegen `S7-1200` ergibt `unsupported_value`.
  3. Markdown wird wie Leerraum behandelt: `*` und Backticks immer, `_` am Wortrand (`x86_64` bleibt). Ein abschließender Ergänzungsstrich wird verworfen (`G-12-`). Führende Wortteile in jeder Schrift werden abgeschnitten (`Schütz-K3` prüft `K3`). Tests:
     - `**192.168.0.99**` gegen `192.168.0.100` ergibt `unsupported_value`.
     - `` `S7-1500` `` und `_S7-1500_` gegen `S7-1200` ergeben `unsupported_value`.
     - `Schütz-K3` gegen `-K7` ergibt `unsupported_value`.
     - Zu jedem Fall gibt es einen positiven Gegentest.
  4. Port-Schreibweisen `Port:`, `Port-Nr.`, `Port Nr.` und `Portnummer` werden geprüft, mit possessiven Quantoren. Es gibt negative und positive Tests. Der Wachstumstest deckt zusätzlich ab: `Port` mit langem `:-`-Lauf, lange Unterstrich-Läufe sowie lange Wortteil-Ketten am Tokenende und Tokenanfang.
  5. Festgelegt und im Docstring genannt: `… 24 V. [1]. Weiter …` ergibt die Sätze `… 24 V. [1].` und `Weiter …`.
  6. Neuer Docstring-Abschnitt „Limits“ mit dem, worauf sich 126 und 128 nicht stützen können:
     - Wörter ohne Ziffern (Varianten wie Basic oder Comfort)
     - Zahlen ohne Einheit
     - Ports ohne das Wort „Port“
     - Einheiten außerhalb der Liste und der Sinnzusammenhang
     - Schreibvarianten derselben Adresse
     - welche von mehreren zitierten Quellen einen Wert nennt

  Die absolute Grenze von 1 s für ungünstige Eingaben bleibt (Festlegung der Leitstelle).

  Prüfungen nach Nachbesserung 3 (twox-123):
  - Build und `up --wait` Exit 0.
  - `test_citations.py`: 167 bestanden.
  - `pytest`: 2787 bestanden, 0 fehlgeschlagen. `pytest -m worker`: 6 bestanden.
  - `ruff check .` „All checks passed!“, `ruff format --check .` Exit 0, `mypy .` „Success: no issues found in 205 source files“.
  - `makemessages`, `check-licenses.sh` und `spectacular` Exit 0, ohne Unterschied. `makemigrations --check` meldet „No changes detected“.
  - `down -v` Exit 0.
