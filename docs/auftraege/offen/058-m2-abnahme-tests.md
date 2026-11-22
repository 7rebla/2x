# Auftrag 058 – Abnahmetests M2 (CI-Teil und lokaler Teil)

Meilenstein: M2 · Freigabestufe: B · Status: offen

## Ziel

Automatische Tests belegen die Abnahme von M2 (`docs/ROADMAP.md`): „Handbücher der Fertigungslinie und des Roboters eingelesen; die Suche findet eine IP-Adresse und eine sinngemäß gestellte Frage; Fehler sind sichtbar“. Ein Teil läuft in der CI ohne Docling und Ollama; ein lokaler Teil ist vorbereitet und wird im Abnahmelauf (060) in der Testumgebung ausgeführt.

## Umfang

- **Backend-Test `backend/tests/acceptance/test_m2.py`** (CI), der ganze Weg über die API:
  - Upload einer im Test erzeugten PDF-Datei (gültige Signatur) → Einlese-Auftrag.
  - Docling-Attrappe mit den echten Testdaten aus 041 → Abschnitte mit Seiten; Einbettungs-Attrappe → `done`.
  - `/api/v1/search/` findet eine Kennung wörtlich mit Seite und eine sinngemäße Frage über den Vektorteil der Attrappe.
  - Fehler über die API sichtbar: Docling abgelehnt → `failed`/`docling_rejected`; fehlender Inhalt → `content_missing`; `.txt` → `skipped`/`unsupported_format`.
  - Erneuter Anstoß als `manage` → neuer Auftrag; als `read` → 403.
- **Playwright `web/e2e/m2-acceptance.spec.ts`:**
  - CI-Teil (als `e2e-manager`): Eine im Test erzeugte `.txt`- und eine Markdown-Datei bei einem Gerät hochladen. Beide erscheinen mit Status auf der Dateiseite und in `/ingest`, die `.txt` als „Übersprungen“ mit Begründung, die Markdown-Datei in einem der Zustände „In Warteschlange“, „Wird eingelesen“ oder „Fehler“ (kein Warten auf das Ende der Wiederholungen). Die Suchseite ist erreichbar; eine Suche ohne Treffer zeigt „keine Treffer“.
  - Lokaler Teil, nur mit `TWOX_M2_LOCAL=1`, sonst `test.skip` mit Begründung:
    - In `/ingest` (Filter „Alle“) steht kein Auftrag in „läuft“ oder „in Warteschlange“; die Liste der Pflicht-Handbücher kommt aus der Variablen `TWOX_M2_REQUIRED` (kommagetrennte Dateinamen, im Abnahmelauf nach Frage 1 in 060 gesetzt), jedes davon „Eingelesen“.
    - Suche `192.168.0.100` zeigt aps-documentation-de mit einer der Seiten aus Prüffrage 1 unter den ersten drei Treffern.
    - Eine sinngemäße Frage zur Nutzlast des UR5e in eigenen Worten zeigt das UR5e-Benutzerhandbuch mit der Seite aus Prüffrage 9 unter den ersten fünf; ebenso Prüffrage 10 (nach E-33) mit dem englischen Software-Handbuch oder dem deutschen Benutzerhandbuch.
    - Ein absichtlich gescheiterter Auftrag ist mit Meldung sichtbar (Dateiname aus `TWOX_M2_FAILED_FILE`).
  - Die Konsole ist ab der Anmeldung fehlerfrei.
- `deploy/compose/compose.web.yaml`: Dienst `e2e` reicht `TWOX_M2_LOCAL`, `TWOX_M2_REQUIRED` und `TWOX_M2_FAILED_FILE` durch (`${VAR:-}`, kein Wert in der Datei).
- Die Schrittfolge für die Abnahme von Hand (im Browser nachvollziehbar) steht im Kurzbericht; 059 übernimmt sie in die Doku.

## Nicht-Ziele

- Keine neuen Funktionen; gefundene Fehler kommen in den Kurzbericht (Ausnahme: Kleinigkeiten in Tests).
- Kein Lauf des lokalen Teils (060).
- Keine Änderung an `testfactory/`; keine Herstellerunterlagen oder Auszüge im Repository.

## Betroffene Bereiche (Ordner, Dateien)

- neu: `backend/tests/acceptance/test_m2.py`
- neu: `web/e2e/m2-acceptance.spec.ts`
- `deploy/compose/compose.web.yaml` (nur Dienst `e2e`, Umgebung)

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-058`, `W` für `docker compose -p twox-058-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18058` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev web-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Tests:
   - `D run --rm backend-dev pytest tests/acceptance -v` endet mit Exit-Code 0.
   - `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen.
   - `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
3. `D run --rm backend-dev ruff check .` meldet `All checks passed!`, `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0, `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
4. Weitere Prüfungen wie in `ci.yml`, jeweils ohne Unterschied zum eingecheckten Stand:
   - `D run --rm backend-dev python manage.py makemessages -l de --add-location=file`, danach `git diff --exit-code -I '^"POT-Creation-Date:' -- backend/locale`;
   - `D run --rm backend-dev python manage.py makemigrations --check --dry-run` endet mit Exit-Code 0;
   - `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0;
   - `D run --rm -v "$PWD/web/openapi:/out" backend-dev python manage.py spectacular --file /out/schema.yml` (unter Git Bash mit vorangestelltem `MSYS_NO_PATHCONV=1`), danach `git diff --exit-code -- web/openapi`.
5. Oberfläche wie im CI-Job `web`: `W --profile dev build web-dev` und `W run --rm web-dev npm ci`, danach `npm run lint`, `npm run typecheck` und `npm run test`, je über `W run --rm web-dev …`, mit Exit-Code 0.
6. Browser-Test wie im CI-Job `e2e`: `D --profile e2e pull e2e`, `D --profile dev run --rm web-dev npm ci`; dann der Schritt „Create test account“ aus `ci.yml` wörtlich, nur mit `D` statt `docker compose` (Kennwort nur über den Variablennamen `TWOX_ACCOUNT_PASSWORD`); dann `D --profile e2e run --rm e2e`: alle Fälle bestanden, `m2-acceptance.spec.ts` mit CI-Teil bestanden und lokalem Teil übersprungen, Exit-Code 0.
7. Ein zweiter Lauf von Kriterium 6 ohne `down -v` bleibt grün.
8. Abräumen: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: 052, 053, 054 und 055 sind nach `main` zusammengeführt.

- Welle 10.
- **Keine neue Abhängigkeit.**
- Seiten und Kennungen im lokalen Teil nur aus `testfactory/questions.yaml`; Fragen in eigenen Worten; keine Zitate.
- `aps-calibration-*` ist ein ZIP und wird übersprungen (049); das ist ein sichtbarer Endzustand, kein Fehler.
- Die Abnahme selbst nimmt a7 vor; dieser Auftrag liefert die Tests.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

Keine. (Welche Handbücher Pflicht sind, entscheidet Frage 1 in 060; der Test liest die Liste aus einer Variablen.)

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
