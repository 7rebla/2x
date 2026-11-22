# Auftrag 048 – Einbettungs-Aufgabe im Worker

Meilenstein: M2 · Freigabestufe: B · Status: erledigt

## Ziel

Nach den Abschnitten berechnet der Worker auf der Warteschlange `embed` die Einbettungen über die Modell-Schnittstelle aus 044 und speichert sie mit Modellnamen. Eine Aufgabe arbeitet nur eine begrenzte Zeit und plant sich für den Rest neu ein. Gleicher Inhalt wird nicht doppelt eingebettet. Ist Ollama nicht erreichbar, endet der Auftrag sichtbar mit Fehler; die Abschnitte bleiben über die Stichwortsuche auffindbar. Ein Befehl bettet nach einem Modellwechsel neu ein.

## Umfang

- `backend/twox/ingest/pipeline.py` und `tasks.py`:
  - Nach dem Schritt `sections` geht es mit Schritt `embed` weiter statt mit `done`.
  - **`twox.ingest.embed(job_id)`** (Route `embed` aus 045): unbekannte `job_id` wird protokolliert und ignoriert.
  - Zuerst Prüfung: `TWOX_EMBED_DIMENSIONS` gleich der Spaltendimension aus 042, sonst `failed`/`embedding_dimension_mismatch` mit klarer Meldung.
  - Übernahme: Abschnitte, deren Version dieselbe Prüfsumme hat wie eine andere Version mit gleichem `ordinal`, gleichem Text und Einbettung des aktuellen Modells, bekommen diese Einbettung kopiert (Frage 4 in 042).
  - Den Rest (ohne Einbettung oder mit anderem Modell) stapelweise einbetten (`embed_documents`), jeden Stapel sofort mit `bulk_update` von `embedding` und `embedding_model` schreiben.
  - Nach `TWOX_EMBED_TASK_MAX_SECONDS` plant sich die Aufgabe für den Rest neu ein, statt weiterzumachen. Am Ende `done`.
- **Fehler:** `EmbeddingUnavailableError` → neuer Versuch mit wachsendem Abstand bis `TWOX_INGEST_MAX_RETRIES`, dann `failed`/`embedding_unavailable` im Schritt `embed`; `EmbeddingRejectedError` → `failed`/`embedding_rejected` mit Hinweis auf `ollama pull` in `error_detail`; `EmbeddingRemoteModelError` → `failed`/`embedding_rejected`.
- Django-Systemprüfung (`checks.register`) in `ingest`: Dimension der Einstellung gegen die Spalte, Fehler bei Abweichung; läuft mit `manage.py check` und vor `migrate`.
- Verwaltungsbefehl `embed_sections`:
  - wie `import_devices`: Probelauf als Vorgabe, `--commit` zum Ausführen, `--user` (Konto mit Rolle `manage`, Pflicht).
  - `--missing` (Vorgabe): Versionen mit Abschnitten ohne Einbettung oder mit anderem Modell als `TWOX_EMBED_MODEL`; `--all`: alle Versionen mit Abschnitten.
  - Legt je betroffener Version einen neuen `IngestJob` (Schritt `embed`, `requested_by` = Konto) an und sendet `embed` nach dem Commit; Versionen mit laufendem Auftrag werden übersprungen und gezählt.
  - Ausgabe: Zahl der Versionen und Abschnitte (angelegt, übersprungen).
- **Tests:** mit Attrappe von `Embedder`: Einbettungen und Modellname gespeichert, `done`; Fehler mitten im zweiten Stapel lässt den ersten stehen, der neue Versuch bettet nur den Rest ein; Zeitgrenze erreicht → Neueinplanung, Fortsetzung macht nur den Rest; Übernahme bei gleichem Inhalt ruft das Modell nicht auf; jede Fehlerart ergibt den erwarteten Status; Abweichung der Dimension (Aufgabe und Systemprüfung); Befehl zählt richtig, Probelauf ändert nichts, Konto ohne `manage` wird abgewiesen.

## Nicht-Ziele

- Keine Vektorsuche (050), kein Messlauf (057), kein Chat-Modell.
- Keine Änderung an `settings.py`, `compose.yaml`, `files/` oder `ingest/services.py`.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/ingest/pipeline.py`, `backend/twox/ingest/tasks.py`
- neu: `backend/twox/ingest/checks.py` (Registrierung in `backend/twox/ingest/apps.py`), `backend/twox/ingest/management/commands/embed_sections.py`
- neu: `backend/tests/ingest/test_embed.py`, `backend/tests/ingest/test_embed_sections_command.py`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-048`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18048` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Tests:
   - `D run --rm backend-dev pytest tests/ingest -v` endet mit Exit-Code 0.
   - `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen.
   - `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
3. `D run --rm backend-dev ruff check .` meldet `All checks passed!`, `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0, `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
4. Weitere Prüfungen wie in `ci.yml`, jeweils ohne Unterschied zum eingecheckten Stand:
   - `D run --rm backend-dev python manage.py makemessages -l de --add-location=file`, danach `git diff --exit-code -I '^"POT-Creation-Date:' -- backend/locale`;
   - `D run --rm backend-dev python manage.py makemigrations --check --dry-run` endet mit Exit-Code 0;
   - `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0;
   - `D run --rm -v "$PWD/web/openapi:/out" backend-dev python manage.py spectacular --file /out/schema.yml` (unter Git Bash mit vorangestelltem `MSYS_NO_PATHCONV=1`), danach `git diff --exit-code -- web/openapi`.
5. `D run --rm -e TWOX_EMBED_DIMENSIONS=768 backend-dev python manage.py check` endet mit Exit-Code ungleich 0 und einer klaren Meldung.
6. Lokal, mit Docling und geladenem Modell (Frage 2 in 044): `D up -d --wait --wait-timeout 600 docling`; BetrSichV wie in 046, Kriterium 5, einlesen. Ergebnis: `done`, alle Abschnitte mit `embedding_model = bge-m3`. Laufzeit des Schritts `embed` je 100 Abschnitte im Kurzbericht.
7. Lokal: Bei beendetem Ollama endet ein Auftrag mit `failed`/`embedding_unavailable`; die Abschnitte liegen vor. Nach dem Neustart von Ollama bettet `D exec -T api python manage.py embed_sections --missing --commit --user <konto mit manage>` sie ein (Konto vorher mit `create_account ... --role manage` anlegen, Kennwort nur über den Variablennamen).
8. Abräumen: `D --profile dev down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

- **Nachtrag der Leitstelle (aus 044, E-59):** Selbsttest-API `/api/v1/selftest/` um einen Teil `ai` ergänzen (`enabled`, bei an zusätzlich `ok`, `model`, `dimensions`, bereinigter `error`) und die Testseite um eine Karte, die bei „aus“ neutral „KI nicht aktiviert“ zeigt (kein Fehler). Bei „aus“ kein Netzaufruf. Schema und Client neu erzeugen; Tests für beide Zustände.

- **Nachtrag der Leitstelle (E-59, KI optional):** Einbettungen, Vektorsuche und alles, was ein Modell braucht, sind eine aktivierbare Zusatzfunktion. Schalter `TWOX_AI_ENABLED` (Einstellung in `settings.py`, Standard `False`; `.env.example` mit Kommentar). Bei „aus“: kein Aufruf von Ollama, keine Einbettungs-Aufgaben, Einlesen endet nach den Abschnitten erfolgreich, die Suche arbeitet nur mit der Stichwortsuche, Selbsttest und Oberfläche zeigen „KI nicht aktiviert“ als neutralen Zustand (kein Fehler, kein Warnsymbol). Jede KI-abhängige Stelle braucht einen Test für beide Zustände; die CI läuft mit „aus“ und mit „an“ plus Attrappe.

Voraussetzung: 046 ist nach `main` zusammengeführt.

- Welle 5, parallel zu 049 und 056 (andere Dateien).
- **Keine neue Abhängigkeit.**
- `bulk_update` schreibt keine Einträge ins Änderungsprotokoll; gewollt (Frage 1 in 042).
- In der CI gibt es kein Ollama; echte Läufe nur lokal (Kriterien 6 und 7).
- Anfrage- und Abschnittstexte nie ins Protokoll schreiben.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

- **Nachtrag der Leitstelle (Prüfung 045):** Das Socket-Zeitlimit des Einbettungs-Clients (120 s) kann zusammen mit `TWOX_EMBED_TASK_MAX_SECONDS` (240) die weiche Grenze von 300 s überschreiten. Beginne keinen neuen Stapel, wenn bis zur weichen Grenze weniger Zeit bleibt als das Socket-Zeitlimit; Test dafür. Beim kalten Herunterfahren kommen nur Aufgaben mit `acks_late` zurück in die Warteschlange (Celery 5.7.0, `cancel_active_requests`).

- **Nachtrag der Leitstelle (Prüfung 046):** Zwei Grenzen aus 046 in `pipeline.py`/`tasks.py` mit beheben, je mit Test: (1) `reject_on_worker_lost` ohne Zähler kann eine Nachricht, deren Verarbeitung den Prozess immer wieder abstürzen lässt (z. B. Speichermangel in `load_result`), endlos neu zustellen. Neuzustellungen begrenzen (z. B. über `attempts` oder `delivery_info['redelivered']`) und danach mit `failed`/`internal` enden. (2) Ergebnisse, die Docling wegen `document_timeout` nur teilweise liefert (`partial_success`), nicht für gleichen Inhalt wiederverwenden; Wiederverwendung nur bei vollständigem Erfolg.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Läufe am 22.11.2026 im Container, Projekt `twox-048`, Port 18048, Docker Engine 29.9.3, Compose v5.7.0, Ollama am Host mit `bge-m3`. Kriterien 0 bis 6 und 8 erfüllt, Kriterium 7 mit einer Abweichung (Ollama nicht beendet, sondern unerreichbar gemacht, siehe unten). Alle drei Nachträge umgesetzt. Keine neue Abhängigkeit, keine Migration, keine Änderung an `settings.py`, `compose.yaml`, `files/`, `ingest/services.py` oder den Dateien von 049.

### Was wurde gebaut?

- `backend/twox/ingest/pipeline.py`:
  - Nach den Abschnitten: KI aus → `done` wie bisher; KI an → Auftrag bleibt `running`, Schritt `embed`, Ergebnis `embedding` mit `embed_after=0`, die Aufgabe sendet `twox.ingest.embed`.
  - `embed(job_id)`: unbekannte oder ungültige ID → Warnung, `missing`. Nimmt `running`/`embed` (aus dem Ablauf) oder `queued`/`embed` (aus `embed_sections`, dann `running` mit `started_at`); alles andere `ignored`.
  - Reihenfolge: KI aus → `done` ohne Modellaufruf. Dimension `TWOX_EMBED_DIMENSIONS` gegen die Spalte → sonst `failed`/`embedding_dimension_mismatch` mit klarer Meldung, vor jedem Modellaufruf. Dann Übernahme gleicher Inhalte, dann Stapel.
  - Übernahme: ein `UPDATE … SET embedding = (Unterabfrage)` für Abschnitte ohne Einbettung des aktuellen Modells, wenn eine andere Version mit gleicher SHA-256 einen Abschnitt mit gleichem `ordinal`, gleicher Überschrift und gleichem Text und Einbettung desselben Modells hat.
  - Stapel: `TWOX_EMBED_BATCH_SIZE` Abschnitte nach `ordinal`, `embed_documents`, Länge jedes Vektors geprüft, sofort `bulk_update` von `embedding` und `embedding_model` (kein Änderungsprotokoll). Eingebettet wird `Überschriftenpfad + Leerzeile + Text` (ohne Überschrift nur der Text).
  - Zeitgrenze (Nachtrag 045): Vor jedem weiteren Stapel `should_pause`: aufhören nach `TWOX_EMBED_TASK_MAX_SECONDS` **oder** wenn bis zur weichen Grenze (300 s) weniger Zeit bleibt als `TWOX_EMBED_TIMEOUT_SECONDS` (120 s). Mit den Vorgaben beginnt also nach 180 s kein Stapel mehr. Jede Aufgabe macht mindestens einen Stapel (Fortschritt auch bei ungünstigen Werten). Dann Neueinplanung (`embed_after=0`), die Fortsetzung bettet nur den Rest ein.
  - Fehler: `EmbeddingUnavailableError` → neuer Versuch nach 10/20/40/60/60 s (`attempts`), danach `failed`/`embedding_unavailable`; `EmbeddingRejectedError` → `embedding_rejected`, `error_detail` enthält immer `ollama pull <modell>`; `EmbeddingRemoteModelError` → `embedding_rejected`; `EmbeddingDimensionError` → `embedding_dimension_mismatch`; `EmbeddingDisabledError` → `done` (neutral); weiche Zeitgrenze → `timeout`; sonst `internal`. Fertige Stapel bleiben stehen. Kein Abschnitts- oder Anfragetext im Protokoll.
  - Nachtrag 046 (1): `count_redelivery(job_id)`: Liefert der Broker eine Nachricht erneut (`delivery_info['redelivered']`, gesetzt von kombu 5.7.0 beim Zurücklegen in `_do_restore_message`, im Container nachgelesen), zählt das als Versuch (`attempts`); ab `TWOX_INGEST_MAX_RETRIES` endet der Auftrag `failed`/`internal` mit festem Text, statt den Schritt wieder auszuführen.
  - Nachtrag 046 (2): Ein Teilergebnis (`partial_success`) wird nicht wiederverwendet; erkannt am Hinweis `converted with …` in `error_detail`. Der Hinweis wird dafür nicht mehr durch `sanitize_error_detail` geschickt (er besteht nur aus Zahlen; eine Datei namens `converted.pdf` hätte das Präfix sonst unkenntlich gemacht).
  - Nachtrag der Leitstelle (Prüfung 049): `poll` schreibt `updated_at` bei jeder Abfrage eines laufenden Auftrags (bedingtes `UPDATE` nur bei `running`, wie bisher über `_update`), damit `ingest_versions --stuck` eine lange Umwandlung nicht für hängend hält. Tests: drei Abfragen mit `pending` bzw. `started` setzen `updated_at` jedes Mal neu; ein fertiger Auftrag bleibt unberührt.
  - Schutz: `poll` und `_finish` lassen einen Auftrag im Schritt `embed` in Ruhe (eine verirrte Abfrage hätte die Abschnitte neu gebaut und die Einbettungen gelöscht); `convert` übernimmt keinen `queued`-Auftrag im Schritt `embed`.
- `backend/twox/ingest/tasks.py`: Aufgabe `twox.ingest.embed` (`acks_late`, `reject_on_worker_lost`, 300/360 s), alle drei Aufgaben prüfen zuerst die Neuzustellung; `_schedule` plant `poll` oder `embed`.
- `backend/twox/ingest/checks.py` (neu), registriert in `apps.py` (`ready`): `twox.ingest.E001` (Fehler) bei Abweichung und KI an, `twox.ingest.W001` (nur Warnung) bei KI aus, damit das Produkt ohne KI startet (E-59). Läuft mit `check`, `migrate` und jedem Verwaltungsbefehl.
- `backend/twox/ingest/management/commands/embed_sections.py` (neu): `--user` (Pflicht, aktiv, Rolle `manage`), `--missing` (Vorgabe) oder `--all`, Probelauf ohne `--commit`. Je Version ein `IngestJob` (`queued`, Schritt `embed`, `requested_by`, `section_count`), `embed.delay` per `on_commit`; Versionen mit aktivem Auftrag (auch bei gleichzeitigem Anlegen, `IntegrityError`) übersprungen und gezählt. `--all` leert vorher die Einbettungen der Version (sonst hätte der Auftrag nichts zu tun). KI aus: eine Zeile `DISABLED: …`, Exit 0, nichts angelegt.
- Selbsttest (Nachtrag 044/E-59): `backend/twox/config/selftest.py` mit Teil `ai`: aus → nur `{"enabled": false}`, kein Netzaufruf; an → `ok`, `model`, `dimensions`, bereinigter `error`. Prüfung: Dimension gegen Spalte, dann eine Einbettung eines festen Satzes mit eigenem Socket-Zeitlimit 4 s (Worker 5 s + 2 × 4 s < 15 s der Seite). Schema `web/openapi/schema.yml` und Client `web/src/api/generated/` neu erzeugt.
- Testseite: `web/src/pages/SelftestPage.tsx` mit vierter Karte „KI-Funktionen“: aus → neutrale Karte (`border-line bg-surface-muted`, Symbol `info`, Status „Nicht aktiviert“, Text „KI nicht aktiviert. …“), kein `role="alert"`, kein Warn- oder Fehlersymbol; an → OK mit Modell und Dimensionen oder Fehlgeschlagen mit Fehlertext. `web/src/api/selftest.ts` verlangt den Teil `ai`. Texte de/en.
- Tests:
  - `backend/tests/ingest/test_embed.py` (neu, 46 Fälle): Speichern mit Modellname und `done`, Stapelgrößen und eingebetteter Text; Ablauf Docling → `embed` → `done`; Version ohne Abschnitte; anderes Modell wird neu eingebettet; Fehler im zweiten Stapel lässt den ersten stehen, neuer Versuch nur der Rest; Zeitgrenze mit Uhr-Attrappe → Neueinplanung, Fortsetzung nur der Rest; mindestens ein Stapel je Aufgabe; Grenzwerte von `should_pause` (auch Socket-Zeitlimit gegen weiche Grenze); Übernahme ohne Modellaufruf, nur bei gleichem `ordinal`/Überschrift/Text, nicht bei anderem Modell oder Inhalt; jede Fehlerart mit Status und Detail; Abstände 10/20/40/60/60 s bis `embedding_unavailable`; keine Abschnittstexte im Protokoll; KI aus (Schalter und `EmbeddingDisabledError`); Dimension (Einstellung, Embedder, falsche Vektorlänge); Systemprüfung (passt, Fehler bei KI an, Warnung bei KI aus); unbekannte ID, andere Zustände, zweite Nachricht; verirrtes `poll`/`convert`.
  - `backend/tests/ingest/test_embed_sections_command.py` (neu, 11 Fälle): Probelauf zählt und ändert nichts; `--missing` legt je Version einen Auftrag an und sendet nach dem Commit; aktive Aufträge übersprungen und gezählt; `--all` mit und ohne `--commit`; angelegte Aufträge werden durch die Aufgabe eingebettet; Konten `read`/ohne Rolle/unbekannt/inaktiv abgewiesen; `--user` Pflicht, `--missing`/`--all` schließen sich aus; KI aus.
  - `test_tasks_worker.py`: `embed` in Registrierung und Optionen; Ablauf KI aus ohne `embed`, KI an mit `embed`; Neueinplanung nach vorübergehendem Fehler; Neuzustellung zählt als Versuch, zu oft → `internal` (für alle drei Aufgaben), Erstzustellung zählt nicht, unbekannter/fertiger Auftrag unverändert.
  - `test_pipeline.py`: KI-Schalter beide Zustände; Teilergebnis nicht wiederverwendet (der nächste vollständige wird es); Hinweis bleibt bei Dateiname `converted.pdf` erkennbar.
  - `fake_converter.py`: `isolated_services` schaltet KI standardmäßig aus; neu `FakeEmbedder`, `install_embedder`, `add_sections`, `make_embed_job`.
  - `backend/tests/config/test_selftest.py`: Teil `ai` aus (kein Aufruf), an mit Ollama-Attrappe (OK, Modell nicht geladen, abgelehnte Verbindung ohne Adresse, falsche Dimension ohne Anfrage, unerwarteter Fehler verborgen), kurzes Zeitlimit, Schema.
  - Web: `SelftestPage.test.tsx` (neutral/OK/Fehler/deutsch), `App.test.tsx` (Teil `ai` in den Antworten, Antwort ohne `ai` ist unlesbar), `e2e/selftest.spec.ts` (Karte sichtbar, Status einer der drei Werte; die CI hat kein Ollama).

### Wie wurde getestet?

`D` = `docker compose -p twox-048`, `.env` aus `.env.example` (ohne BOM) mit `TWOX_API_PORT=18048`, also KI an.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | Engine 29.9.3, Compose v5.7.0, Exit 0 |
| 1 | erfüllt | Bau Exit 0; `up -d --wait …` Exit 0, alle `Healthy` |
| 2 | erfüllt | `pytest tests/ingest -v`: `394 passed, 1 deselected`; `pytest -rs`: `1998 passed, 6 deselected`, kein `SKIPPED`; `pytest -m worker`: `6 passed`. Nach dem Nachtrag zu 049 (Images neu gebaut): `pytest tests/ingest` `397 passed`, `pytest -rs` `2001 passed, 6 deselected`, kein `SKIPPED`, `pytest -m worker` `6 passed`; ruff und mypy erneut grün |
| 3 | erfüllt | `All checks passed!`; `176 files already formatted`; `Success: no issues found in 175 source files` |
| 4 | erfüllt | `makemessages` + `git diff -I POT-Creation-Date -- backend/locale` Exit 0; `No changes detected`; `License check passed.`; `spectacular` + `git diff -- web/openapi` Exit 0 |
| 5 | erfüllt | Exit 1: `SystemCheckError … (twox.ingest.E001) TWOX_EMBED_DIMENSIONS is 768, but the embedding column of the sections has 1024 dimensions; no embedding could be stored`, `HINT: Set TWOX_EMBED_DIMENSIONS=1024 and use an embedding model with 1024 dimensions (bge-m3, E-56).` |
| 6 | erfüllt | BetrSichV.pdf: `done/embed`, 60 Seiten, 140 Abschnitte, 140 mit `embedding_model = bge-m3`, Gesamtlaufzeit 359 s |
| 7 | erfüllt mit Abweichung | siehe unten |
| 8 | erfüllt | `D --profile dev down -v` Exit 0 (am Ende) |

Web-Job wie in `ci.yml` (eigenes Projekt `twox-048-web`): `npm ci`, `lint`, `typecheck`, `test` (`571 passed`), `build`, `licenses` (`License check passed.`), `api:generate` ohne weiteren Unterschied. e2e wie in `ci.yml` (Testkonto `e2e-manager` angelegt): `41 passed`. `web/dist` danach gelöscht, `git status` sauber.

**Messwerte Schritt `embed`** (aus dem Worker-Protokoll, CPU/GPU des Hosts wie vorhanden, Stapel 16):

| Lauf | Abschnitte | Dauer `embed` | je 100 Abschnitte |
| --- | --- | --- | --- |
| erste Einbettung nach Docling (Modell evtl. erst geladen) | 140 | 7,29 s | 5,2 s |
| `embed_sections --all --commit`, Modell geladen | 140 | 2,78 s | 2,0 s |
| gleicher Inhalt an anderem Gerät (Übernahme, kein Modellaufruf) | 140 | 0,12 s | – |

Zum Vergleich: Docling brauchte für dieselbe Datei ≈ 350 s.

**Kriterium 7:** Ollama am Host habe ich **nicht beendet**, weil der Prozess außerhalb des Projektordners läuft und auch von anderen Umgebungen genutzt wird. Stattdessen habe ich nur den Worker mit `TWOX_LLM_BASE_URL=http://host.docker.internal:11435/v1` neu erstellt (Port ohne Dienst, wie bei beendetem Ollama). Ablauf: `sftp-backup.md` eingelesen → Auftrag 2 `failed/embed`, `embedding_unavailable`, `attempts=5`, Detail `cannot reach the model service (URLError) (gave up after 5 retries)`, nach 200 s; 4 Abschnitte liegen vor, keine Einbettung. Worker mit der normalen Adresse neu erstellt („Neustart von Ollama“), Konto `e2e-manager` mit `create_account … --role manage --update` (Kennwort nur über den Variablennamen), dann `D exec -T api python manage.py embed_sections --missing --commit --user e2e-manager`: `versions: 1 jobs created, 0 skipped (queued or running job)`, `sections: 4 to embed, 0 skipped`; Auftrag 3 nach 0,12 s `done`, 4 Abschnitte mit `bge-m3`. Docker Desktop meldet für einen geschlossenen Port an `host.docker.internal` keinen „connection refused“, sondern einen allgemeinen `URLError`; bei wirklich beendetem Ollama kann die Meldung anders lauten. Ein Lauf mit beendetem Ollama steht noch aus, falls die Leitstelle ihn will.

Selbsttest gegen den echten Stand (Djangos Testclient im `api`-Container): KI an → `{"enabled": true, "ok": true, "model": "bge-m3", "dimensions": 1024, "error": ""}`; `-e TWOX_AI_ENABLED=false` → `{"enabled": false}`; unerreichbare Adresse → `ok: false`, `error: "cannot reach the model service (URLError)"`.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a983412ee78c28f99`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a983412ee78c28f99` (relativ zum Projektordner)
- Commits: `Embed the sections in the worker after the step sections`, `Show the AI features in the self-test and on the test page`, `Name jobs and sections to embed in the output of embed_sections`, `Write updated_at on every status query of a running job`, dazu dieser Kurzbericht. Nicht gepusht, nichts zusammengeführt.

### Abweichungen und Hinweise

1. **Kriterium 7 ohne beendetes Ollama** (siehe oben).
2. **Eingebetteter Text = Überschriftenpfad + Leerzeile + Text.** Der Auftrag sagt nicht, was eingebettet wird; die Überschriften geben dem Abschnitt Zusammenhang. Deshalb verlangt die Übernahme neben `ordinal` und Text auch gleiche Überschrift. Bei anderer Entscheidung ist es eine Zeile (`embedding_text`); 057 kann beides messen.
3. **`--all` leert die Einbettungen** der ausgewählten Versionen beim Anlegen des Auftrags; bis der Auftrag fertig ist, finden diese Abschnitte nur die Stichwortsuche.
4. **Systemprüfung bei KI aus nur Warnung** (`W001`), damit ein unbenutzter KI-Wert den Start nicht verhindert (E-59). Bei KI an Fehler (`E001`), `migrate` bricht dann ab.
5. **Ein Zähler `attempts` für den ganzen Auftrag** (wie 046): Docling-Wiederholungen, Ollama-Wiederholungen und Neuzustellungen teilen sich `TWOX_INGEST_MAX_RETRIES`. Ein Auftrag, der schon fünf Docling-Wiederholungen brauchte, scheitert beim ersten Ollama-Ausfall; `embed_sections --missing` holt das nach.
6. **Neuzustellung zählt ab der ersten Wiederholung** – auch eine Rückgabe beim kalten Herunterfahren oder nach dem `visibility_timeout`. Bei fünf Neustarts des Workers während desselben Auftrags endet er also `internal`.
7. **Teilergebnis erkannt am Text** `converted with …` in `error_detail` (kein eigenes Feld, keine Migration). Ein eigenes Feld (z. B. Docling-Status) wäre robuster – Stufe C, Vorschlag für später.
8. **Zusätzlich geändert** (über die Liste der betroffenen Dateien hinaus, nötig): `tests/ingest/fake_converter.py`, `test_pipeline.py`, `test_tasks_worker.py` (Ablauf mit KI an ändert sich), `tests/config/test_selftest.py`, `web/src/App.test.tsx`, `web/e2e/selftest.spec.ts`, Übersetzungen `web/src/locales/{de,en}/selftest.json`.
9. **Grenzen:** Zwei gleichzeitige `embed`-Nachrichten desselben Auftrags (z. B. von Hand doppelt gesendet) betten einen Stapel ggf. doppelt ein – Ergebnis gleich, nur Mehrarbeit. Scheitert das Senden von `embed` nach den Abschnitten (Broker weg), bleibt der Auftrag `running`/`embed` stehen; `embed_sections` überspringt ihn (aktiv), hier hilft `--stuck` aus 049. Aufträge aus `embed_sections` haben `page_count` leer.
10. **Doku:** README und `docs/ARCHITECTURE.md` nennen `embed_sections`, den Selbsttest-Teil `ai` und die Prüfung `twox.ingest.E001` noch nicht (wie in 044 vorgesehen: 059).
11. Protokollzeilen des Workers erscheinen doppelt (eigener Handler plus Celery); unverändert von 046.

Keine offene Frage, die den Auftrag aufhält.

### Nachbesserung aus der Prüfung der Leitstelle

`main` (mit 049) ist in den Zweig zusammengeführt, ohne Konflikte.

1. **`embed_sections --all` rechnet wirklich neu.** Bisher leerte der Befehl die Einbettungen je Version in einer eigenen Transaktion und sendete sofort. Bei zwei Versionen gleichen Inhalts und Modells übernahm der erste Auftrag die alten Vektoren der noch nicht geleerten Nachbarversion. Jetzt legt der Befehl alle Aufträge in **einer** Transaktion an (Sicherungspunkt je Version für `IntegrityError`), leert bei `--all` die Einbettungen aller dieser Versionen darin und sendet alle `embed`-Nachrichten erst nach dem Commit (ein `on_commit`). Test mit echter Transaktion (`transaction=True`) und einem Worker, der jede Nachricht sofort abarbeitet: zwei Versionen gleichen Inhalts → das Modell (Attrappe) bettet 3 Texte ein, kein alter Vektor bleibt. Mit dem alten Ablauf hätte dieser Test kein Modellaufruf gesehen. Grenze: Eine wegen eines aktiven Auftrags übersprungene Version wird nicht geleert; ihre alten Vektoren könnten übernommen werden.
2. **Verlorene `embed`-Nachricht hängt nicht mehr.** `poll` und `convert` für einen Auftrag im Schritt `embed` (`running`, bei `convert` auch `queued`) verwerfen die Nachricht nicht mehr, sondern geben `StepResult(Outcome.EMBEDDING, embed_after=0)` zurück; die Aufgabe plant `embed` neu ein (wiederholbar dank `needs_embedding`). Mit KI aus gibt es keine Aufgabe `embed`: Der Auftrag endet dann `done`. Tests: verirrtes `poll`/`convert` plant `embed`, ohne Abschnitte anzufassen; KI aus → `done`; `poll`-Aufgabe nach verlorener Nachricht sendet `twox.ingest.embed`, danach `done`.
3. **Senden wie `send_convert` (049).** `embed_sections` sendet mit `ignore_result=True`, `retry=True` und `SEND_RETRY_POLICY` aus `ingest/services.py`; ein Sendefehler gibt eine Warnung ins Protokoll und eine Zeile `WARNING: … stay queued; start them again with: manage.py ingest_versions --stuck …` aus, der Auftrag bleibt `queued`. Tests: Sendeoptionen, Sendefehler.
4. **Zusätzlich:** `backend/twox/ingest/services.py` (aus 049) hatte nach dem Zusammenführen eine Zeile mit 101 Zeichen; `ruff check` schlug fehl (E501). Ich habe den Text in zwei Teile geteilt, der Inhalt ist gleich.

5. Der neue Test mit `transaction=True` legt sein Konto als Superuser an: Ein früherer Test mit `transaction=True` leert die Gruppen aus der Datenmigration, `make_user("manage")` scheiterte deshalb im Gesamtlauf.

Prüfungen des backend-Jobs danach (Images neu gebaut, wie in `ci.yml`): `ruff check` `All checks passed!`, `ruff format --check` `182 files already formatted`, `mypy` `Success: no issues found in 181 source files`, `pytest -rs` `2120 passed, 6 deselected`, kein `SKIPPED`, `pytest -m worker` `6 passed`, `makemessages` ohne Unterschied, `makemigrations --check` `No changes detected`, `License check passed.`, `spectacular` ohne Unterschied in `web/openapi`. `web/` ist in der Nachbesserung nicht geändert.
