# Auftrag 058 – Abnahmetests M2 (CI-Teil und lokaler Teil)

Meilenstein: M2 · Freigabestufe: B · Status: zur Prüfung

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

- **Nachtrag der Leitstelle (E-59, KI optional):** Einbettungen, Vektorsuche und alles, was ein Modell braucht, sind eine aktivierbare Zusatzfunktion. Schalter `TWOX_AI_ENABLED` (Einstellung in `settings.py`, Standard `False`; `.env.example` mit Kommentar). Bei „aus“: kein Aufruf von Ollama, keine Einbettungs-Aufgaben, Einlesen endet nach den Abschnitten erfolgreich, die Suche arbeitet nur mit der Stichwortsuche, Selbsttest und Oberfläche zeigen „KI nicht aktiviert“ als neutralen Zustand (kein Fehler, kein Warnsymbol). Jede KI-abhängige Stelle braucht einen Test für beide Zustände; die CI läuft mit „aus“ und mit „an“ plus Attrappe.

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

**Status: zur Prüfung.** Läufe am 22.11.2026 im Container, Projekte `twox-058` und `twox-058-web`, Port 18058, Docker Engine 29.9.3, Compose v5.7.0. Kriterien 0 bis 8 erfüllt. Keine neue Abhängigkeit, kein Produktcode geändert. Der lokale Teil des Browser-Tests ist geschrieben, aber nicht gelaufen (Nicht-Ziel, 060).

### Was wurde gebaut?

- **`backend/tests/acceptance/test_m2.py`** (CI, 6 Fälle, je mit KI aus und KI an = 12 Läufe, E-59). Der ganze Weg über die API und die echten Worker-Aufgaben: Upload über `POST /api/v1/devices/{id}/documents/` → Einlese-Auftrag `queued` und Nachricht `twox.ingest.convert`; die aufgezeichneten Nachrichten laufen danach nacheinander durch die echten Celery-Aufgaben `convert`/`poll`/`embed` (ohne Broker, Countdowns werden nicht abgewartet). Docling ist die HTTP-Attrappe aus 041 (`fake_docling.py`), angesprochen vom echten `DoclingClient`, mit den echten Docling-Ergebnissen aus `tests/ingest/fixtures/` (BetrSichV S. 1–5 als PDF, `sftp-backup.md` als Markdown). KI an: Einbettungs-Attrappe aus 048 (Abschnitte) und Anfrage-Attrappe aus 050 (Suche); KI aus: jeder Zugriff auf das Modell lässt den Test scheitern.
  - *Eingelesen:* im Test erzeugte einseitige PDF (gültige Signatur und Querverweistabelle) und eine Markdown-Datei → `done`, PDF mit 5 Seiten, Markdown ohne Seiten, Abschnitte decken die Seiten 1–5 ab; Schritt `embed` und Einbettungen nur bei KI an; Docling sieht nur `version-<id>.pdf`/`.md`; danach kein Auftrag `queued`/`running`.
  - *Kennung wörtlich mit Seite:* `31990L0270` (CELEX-Nummer auf S. 1 der BetrSichV-Fixture) → erster Treffer `exact`, Seite 1, markiert, Fundort mit Dateiname, Version, Gerät; `semantic` `used` bzw. `disabled`.
  - *IP-Adresse wörtlich:* `192.168.1.10` aus der Markdown-Fixture → erster Treffer `exact`, markiert, ohne Seite; `192.168.1.1` trifft weder exakt noch per Stichwort.
  - *Sinngemäße Frage:* eine Frage ohne ein Wort aus dem gemeinten Abschnitt (BetrSichV § 2 Abs. 5) → KI an: erster Treffer genau dieser Abschnitt, nur `semantic`, mit Seiten; KI aus: `{"semantic": "disabled", "hits": []}` ohne Modellaufruf.
  - *Fehler sichtbar:* Docling antwortet 422 → `failed`/`docling_rejected`; Inhalt nach dem Upload entfernt → `failed`/`content_missing`; `.txt` → sofort `skipped`/`unsupported_format` ohne Nachricht. Für `manage` und `read` sichtbar (Dateiseite und `/api/v1/ingest-jobs/`), bereinigter Text ohne Dateiname und Adresse, `requested_by` nur für `manage` (E-57).
  - *Erneut einlesen:* `read` → 403, keine Nachricht; `manage` → 202, neuer Auftrag `queued`, danach `done` mit gleicher Abschnittszahl, ohne neuen Docling-Upload (gespeicherte Antwort, 046); beide Versuche bleiben gelistet.
- **`web/e2e/m2-acceptance.spec.ts`**, Anmeldung über die Anmeldeseite, Konsole ab dort fehlerfrei:
  - *CI-Teil:* neues Testgerät; `.txt` und `.md` über das Formular der Geräteseite hochgeladen; Geräteseite (Abzeichen), Dateiseite (Status, Meldung, technischer Text) und `/ingest` (Filter „All“, Gerätefilter, zwei Zeilen, Gerät, „Started by“): `.txt` „Skipped“ mit Begründung, `.md` „Queued“/„Ingesting…“/„Error“. Suchseite über die Navigation; Suche ohne Treffer → „No hits…“, der Hinweis passt zum echten `semantic` der Antwort. E-59 mit Antworten über `page.route`: KI an (Treffer „Meaning“, kein Hinweis) und KI aus (Treffer „Keyword“, ruhige Zeile „Keyword search (AI features not enabled)“ ohne Icon, kein Warnhinweis).
  - *Lokaler Teil* (nur `TWOX_M2_LOCAL=1`, sonst `test.skip` mit Begründung; ohne `TWOX_M2_REQUIRED` oder `TWOX_M2_FAILED_FILE` scheitert er mit Meldung): `/ingest?status=all` ohne Zeile `running`/`queued` und ohne Abfragehinweis, dazu über alle Seiten der API; jede Datei aus `TWOX_M2_REQUIRED`: neuester Auftrag jeder Version mit diesem Namen `done` und in `/ingest` (Filter „All“, Gerät, ggf. weitergeblättert) als „Ingested“; Suche `192.168.0.100` → `aps-documentation-de` mit S. 18, 31 oder 38 unter den ersten drei; Nutzlast UR5e in eigenen Worten → `ur5e-user-manual-de` S. 16, 101 oder 102 unter den ersten fünf; Prüffrage 10 nach E-33 → `ur5e-user-manual-de` S. 81, 84, 86 oder 252 oder `ur5e-software-handbook-en` S. 46 unter den ersten fünf; der Treffer zeigt auf der Seite dieselbe Seitenangabe und den Link zur Datei. Die Handbücher werden über die SHA-256 aus `testfactory/manifest.yaml` erkannt (neueste Version der Dateien aller Geräte), nicht über den Dateinamen. `TWOX_M2_FAILED_FILE`: neuester Auftrag `failed`, in `/ingest?status=failed` mit „Error“, Fehlerart und Meldung, ebenso auf der Dateiseite.
- **`deploy/compose/compose.web.yaml`:** Dienst `e2e` reicht `TWOX_M2_LOCAL`, `TWOX_M2_REQUIRED`, `TWOX_M2_FAILED_FILE` als `${VAR:-}` durch.

### Abdeckung der M2-Abnahme

| Anforderung (ROADMAP M2) | Backend `test_m2.py` | Browser `m2-acceptance.spec.ts` |
| --- | --- | --- |
| Handbücher eingelesen | `test_manuals_are_ingested_with_pages_and_sections` (Attrappe) | lokal: Pflichtliste „Ingested“, nichts offen |
| Suche findet eine IP-Adresse | `test_search_finds_an_ip_address_word_for_word`, Kennung mit Seite: `test_search_finds_an_identifier_word_for_word_with_its_page` | lokal: `192.168.0.100` unter den ersten drei |
| Suche findet eine sinngemäße Frage | `test_search_answers_a_question_in_other_words_by_meaning` | lokal: Prüffragen 9 und 10 unter den ersten fünf; CI: Anzeige „Meaning“ (Attrappe) |
| Fehler sichtbar | `test_errors_are_visible_over_the_api` | CI: „Skipped“ mit Begründung, `.md` ggf. „Error“; lokal: absichtlich gescheiterter Auftrag |
| Erneut anstoßen, Rechte | `test_manage_starts_the_ingestion_again_read_may_not` | (bestehend: `ingest-status.spec.ts`, `ingest.spec.ts`) |
| KI an/aus (E-59) | alle Fälle zweifach (`ai-off`, `ai-on`) | CI: `semantic` used/disabled per `page.route`, echte Suche je nach Zustand |

### Wie wurde getestet?

`D` = `docker compose -p twox-058`, `W` = `docker compose -p twox-058-web -f deploy/compose/compose.web.yaml`; `.env` aus `.env.example` mit dem Write-Werkzeug (ohne BOM), nur `TWOX_API_PORT=18058` geändert. Vor jedem Web-Bau und e2e-Lauf `web/dist` und `web/playwright-report` gelöscht. „2x“ und „twox-leit“ nicht berührt.

| Nr. | Ergebnis | Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | Engine 29.9.3, Compose v5.7.0, je Exit 0 |
| 1 | erfüllt | `build migrate api worker backend-dev web-dev` Exit 0; `up -d --wait …` Exit 0, db/valkey/api/worker healthy |
| 2 | erfüllt | `pytest tests/acceptance -v`: 16 passed (4 aus M1, 12 aus M2), Exit 0; `pytest -rs`: 2307 passed, 6 deselected, 0 skipped, Exit 0; `pytest -m worker`: 6 passed, Exit 0 |
| 3 | erfüllt | `All checks passed!`; `193 files already formatted`; `Success: no issues found in 192 source files` |
| 4 | erfüllt | `makemessages`, `makemigrations --check --dry-run`, `check-licenses.sh`, `spectacular` je Exit 0; `git diff --exit-code -I '^"POT-Creation-Date:' -- backend/locale web/openapi` Exit 0, `git status --porcelain` leer |
| 5 | erfüllt | `build web-dev`, `npm ci`, `lint`, `typecheck` (schließt `e2e/` ein), `test` (37 Dateien, 711 Tests) je Exit 0 |
| 6 | erfüllt | `pull e2e`, `npm ci`, „Create test account“ wörtlich mit `D`, `run --rm e2e`: **54 passed, 1 skipped** (lokaler Teil), Exit 0; CI-Teil 3,0 s |
| 7 | erfüllt | zweiter Lauf ohne `down -v` (Testkonto mit `--update`): 54 passed, 1 skipped, Exit 0 |
| 8 | erfüllt | beide `down -v` Exit 0; kein Container, Volume oder Netz mit `twox-058` übrig |

### Abnahme von Hand (für 059 und a7)

Voraussetzung: Testumgebung „2x“ mit den Handbüchern an den Geräten, Docling läuft, Anmeldung mit einem Konto der Rolle „Verwalten“.

1. „Einlesen“ in der Kopfzeile öffnen, Filter Status „Alle“: Kein Auftrag steht auf „Wird eingelesen“ oder „In Warteschlange“; oben erscheint kein Hinweis „Es laufen Aufträge …“.
2. Je Pflicht-Handbuch (alle PDF- und Office-Handbücher der Fertigungslinie und des UR5e, ohne ZIP; E-58): Filter auf das Gerät setzen; die neueste Zeile der Datei zeigt „Eingelesen“ mit Seiten und Abschnitten. `aps-calibration-*` (ZIP) steht als „Übersprungen“ mit Begründung – das ist ein gewollter Endzustand.
3. „Suche“ öffnen, `192.168.0.100` suchen: Unter den ersten drei Treffern steht die Dokumentation der Fertigungslinie (Deutsch) mit Seite 18, 31 oder 38 (Prüffrage 1), Marke „Exakt“, Adresse markiert.
4. Eine Frage zur Nutzlast des UR5e in eigenen Worten stellen: Unter den ersten fünf Treffern steht das deutsche UR5e-Benutzerhandbuch mit Seite 16, 101 oder 102 (Prüffrage 9).
5. Fragen, wie der UR5e nach einem Halt durch eine Schutzeinrichtung wieder freigegeben wird (E-33): Unter den ersten fünf Treffern steht das deutsche Benutzerhandbuch (S. 81, 84, 86 oder 252) oder das englische Software-Handbuch (S. 46) (Prüffrage 10).
6. Bei KI aus steht über den Treffern die ruhige Zeile „Stichwortsuche (KI nicht aktiviert)“ ohne Warnsymbol; bei KI an ohne erreichbares Modell der Hinweis „Nur Stichwortsuche – Sprachmodell nicht erreichbar“.
7. Fehler sichtbar (E-58): eine selbst erzeugte beschädigte PDF an einem Gerät hochladen bzw. Docling stoppen und eine PDF hochladen; in „Einlesen“ (Filter „Fehler“) und auf der Dateiseite steht „Fehler“ mit verständlicher Meldung, unter „Technische Angaben“ der bereinigte Text. Bei gestopptem Docling erst nach den Wiederholungen (etwa 2,5 min).
8. Als Verwalter „Version 1 erneut einlesen“ klicken: Ein neuer Auftrag erscheint oben, der ältere ist als „Älterer Versuch“ gekennzeichnet. Mit einem Konto der Rolle „Lesen“ gibt es den Knopf nicht.
9. Automatisch (060): `TWOX_M2_LOCAL=1 TWOX_M2_REQUIRED=<Dateinamen, kommagetrennt> TWOX_M2_FAILED_FILE=<Dateiname> docker compose --profile e2e run --rm e2e npx playwright test e2e/m2-acceptance.spec.ts`.

### Zweig und Arbeitsverzeichnis

Zweig `worktree-agent-a8324f073283930ee`, Arbeitsverzeichnis `.claude/worktrees/agent-a8324f073283930ee`. Commits: Backend-Test, Browser-Test mit Compose-Änderung, dieser Kurzbericht.

### Abweichungen und Hinweise

1. **IP-Adresse im CI-Teil ohne Seite.** Die PDF-Fixture (BetrSichV) enthält keine IP-Adresse. Deshalb zwei Proben: eine Kennung (`31990L0270`) wörtlich mit Seite aus der PDF und eine IP-Adresse wörtlich aus der Markdown-Fixture (Markdown hat keine Seiten). Die IP-Adresse mit Seite belegt der lokale Teil.
2. **Risiko für 060, Prüffrage 9:** In der Nachmessung zu 063 stand die Probe `question-9` kombiniert auf Rang 12. Der lokale Teil verlangt Rang 1–5 mit einer eigenen Formulierung („Wie schwer darf eine Last höchstens sein, die der UR5e bewegen soll?“), die nicht gegen die echten Daten geprüft ist. Scheitert der Schritt in 060, ist das ein Befund zur Suchgüte, kein Fehler des Tests; die Formulierung danach anzupassen, wäre ein Anpassen an das Ergebnis und sollte a7 entscheiden.
3. **CI-Teil in der Testumgebung:** Läuft die ganze e2e-Suite in „2x“, legt der CI-Teil (wie die übrigen e2e-Tests) Testgeräte und zwei kleine Dateien an; die Markdown-Datei wird dort tatsächlich eingelesen. Für 060 genügt `npx playwright test e2e/m2-acceptance.spec.ts -g "local part"`, wenn das vermieden werden soll.
4. **Keine Fehler gefunden** im Produktcode. Beobachtung: Bei KI an listet die Vektorsuche immer die nächsten Abschnitte, auch bei einer Anfrage, die nur aus einer nicht vorhandenen Kennung besteht (`192.168.1.1` liefert Treffer „Bedeutung“). Das entspricht 050/063, kann in der Oberfläche aber als „Treffer“ zur falschen Adresse gelesen werden; Vorschlag für später: bei reinen Kennungsanfragen ohne exakten Treffer die Vektorliste weglassen oder kennzeichnen.
5. Der Hinweis aus 053 (Statuswechsel werden Screenreadern nicht angesagt) ist nicht Teil dieser Tests geblieben; er gehört in die Doku (059).

### Nachbesserung nach der Prüfung der Leitstelle

1. **Blättern im lokalen Teil (`overviewRow`):** `/ingest` behält beim Laden der nächsten Seite die alten Zeilen (`keepPreviousData`, `aria-busy`) und sperrt „Weiter“. Die Schleife prüft jetzt erst, wenn `ingest-jobs` `aria-busy="false"` hat und `ingest-page-status` die erwartete Seitenzahl („Page n of m“) zeigt; nach dem Klick auf „Weiter“ wartet sie auf „Page n+1“. Ende ist erreicht, wenn n = m ist oder die Liste leer ist (`ingest-empty`), nicht mehr über `isEnabled()`.
2. **Adressprüfungen robust gegen weitere Parameter (064, `latest`):** Die drei Prüfungen auf `/ingest…$` sind durch `expectIngestAddress()` ersetzt; sie prüft den Pfad `/ingest` und nur die gemeinten Parameter (`status`, `device`) einzeln.
3. Geprüft wie in `ci.yml`: `W` build, `npm ci`, `lint` und `typecheck` je Exit 0; `D` build, `pull e2e`, `npm ci`, `up -d --wait`, „Create test account“, `run --rm e2e`: 54 passed, 1 skipped (lokaler Teil), Exit 0; danach beide `down -v` Exit 0. `overviewRow` läuft nur im lokalen Teil und ist daher nur durch Typprüfung und Lint abgesichert.
