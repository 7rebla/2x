# Auftrag 048 – Einbettungs-Aufgabe im Worker

Meilenstein: M2 · Freigabestufe: B · Status: offen

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

- **Nachtrag der Leitstelle (E-59, KI optional):** Einbettungen, Vektorsuche und alles, was ein Modell braucht, sind eine aktivierbare Zusatzfunktion. Schalter `TWOX_AI_ENABLED` (Einstellung in `settings.py`, Standard `False`; `.env.example` mit Kommentar). Bei „aus“: kein Aufruf von Ollama, keine Einbettungs-Aufgaben, Einlesen endet nach den Abschnitten erfolgreich, die Suche arbeitet nur mit der Stichwortsuche, Selbsttest und Oberfläche zeigen „KI nicht aktiviert“ als neutralen Zustand (kein Fehler, kein Warnsymbol). Jede KI-abhängige Stelle braucht einen Test für beide Zustände; die CI läuft mit „aus“ und mit „an“ plus Attrappe.

Voraussetzung: 046 ist nach `main` zusammengeführt.

- Welle 5, parallel zu 049 und 056 (andere Dateien).
- **Keine neue Abhängigkeit.**
- `bulk_update` schreibt keine Einträge ins Änderungsprotokoll; gewollt (Frage 1 in 042).
- In der CI gibt es kein Ollama; echte Läufe nur lokal (Kriterien 6 und 7).
- Anfrage- und Abschnittstexte nie ins Protokoll schreiben.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
