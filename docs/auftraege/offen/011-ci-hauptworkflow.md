# Auftrag 011 – CI-Hauptworkflow

Meilenstein: M0 · Freigabestufe: C · Status: offen

## Ziel

GitHub Actions prüft jede Änderung mit denselben Befehlen wie lokal: Lint, Typprüfung, Tests und Lizenzprüfung für Backend und Oberfläche, alles in den Containern aus `docker compose`.

## Umfang

- `.github/workflows/ci.yml`, ausgelöst bei Push auf alle Zweige und bei Pull Requests. Berechtigungen: nur `contents: read`. Ein neuer Lauf auf demselben Zweig bricht den älteren ab.
- Vorbereitung im Workflow: `.env.example` nach `.env` kopieren.
- Job `backend`:
  - Images bauen, `db`, `valkey`, `worker` und `api` starten und auf `healthy` warten (Dienste ausdrücklich benannt, damit später hinzukommende Dienste wie `docling` nicht mitstarten).
  - `ruff check .`, `ruff format --check .`, `mypy .`, `pytest`, `pytest -m worker`, `manage.py makemigrations --check --dry-run` – jeweils über den Dienst `backend-dev`.
  - Lizenzprüfung Python: `sh scripts/check-licenses.sh` über `backend-dev`.
- Job `web`: `npm ci`, `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`, `npm run licenses` – über den Dienst `web-dev`.
- `docling` wird in der CI nicht gestartet (Image mehrere Gigabyte). Ollama gibt es in der CI nicht.
- Bei einem Fehlschlag gibt der Workflow die Protokolle der Container aus (`docker compose logs`).

## Nicht-Ziele

- Ein Job für Prüffragen. In M0 gibt es keine Prüffragen; ein Platzhalter, der immer grün endet, würde eine Prüfung vortäuschen. Der Job entsteht mit den Prüffragen (M3, spätestens M6) nach a7s Antwort auf Frage 1.
- Suche nach Geheimnissen (Auftrag 003, eigene Datei `secrets.yml`).
- Playwright-Test in der CI (Auftrag 014).
- Tests der Testfabrik (T1; eigener Folgeauftrag nach T1).
- Veröffentlichen von Images, Deployments, Abzeichen im README.
- Einstellungen am Repository (zum Beispiel Schutz von `main`): macht a7.

## Betroffene Bereiche (Ordner, Dateien)

- `.github/workflows/ci.yml` (neu)

## Akzeptanzkriterien (prüfbar)

Lokale Läufe im Wurzelverzeichnis mit `-p twox-011`; vorher `.env.example` nach `.env` kopieren (falls nicht vorhanden) und darin `TWOX_API_PORT=18011` setzen.

0. Vorab: `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren oder ausführen; Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. Jeder Befehl, den der Workflow ausführt, läuft lokal in derselben Reihenfolge mit Exit-Code 0 durch. Die Liste der Befehle mit Ergebnis steht im Kurzbericht.
2. `git grep -n 'uses:' -- .github/workflows/ci.yml` zeigt nur `actions/checkout`, festgelegt auf einen Commit-Hash.
3. `git grep -n -i -E 'docling|ollama|prueffragen' -- .github/workflows/ci.yml` zeigt keinen Start dieser Dienste und keinen Platzhalter-Job (höchstens Kommentare).
4. Der Workflow enthält keine Geheimnisse und braucht keine: `git grep -n 'secrets\.' -- .github/workflows/ci.yml` ist leer.
5. Die lokale Suche nach Geheimnissen bleibt ohne Fund: `docker compose -p twox-011 -f deploy/compose/compose.tools.yaml run --rm gitleaks-dir` endet mit Exit-Code 0.
6. Der Kurzbericht nennt das Ergebnis der drei Prüfpunkte zu den Runnern (siehe Hinweise) mit Quelle.
7. Abräumen: `docker compose -p twox-011 down -v` endet mit Exit-Code 0.
8. Nach dem Push durch die Leitstelle (auf a7s Freigabe): `gh run list --workflow ci.yml --limit 1 --json conclusion` zeigt `success`; die Laufzeit des gesamten Workflows trägt die Leitstelle in `docs/STATUS.md` ein. Diesen Punkt prüft die Leitstelle; bis dahin bleibt der Auftrag „zur Prüfung“.
9. Gegenprobe (durch die Leitstelle auf einem Wegwerf-Zweig): Ein absichtlich fehlschlagender Test lässt den Lauf rot werden.

## Vorgaben und Hinweise

- **Voraussetzung:** Die Aufträge 002, 005, 006 und 008 sind zusammengeführt (und damit 001).
- **Abhängigkeiten.** Mit der Freigabe der Auftragsliste genehmigt a7 die Action `actions/checkout` (MIT, laut Prüfbefund vom 21.11.2026 an der LICENSE-Datei belegt). Jede weitere Fremd-Action (auch für Zwischenspeicher oder Docker-Build) ist nicht genehmigt; wird eine gebraucht: Frage in den Auftrag mit Lizenz und Quelle, Status „wartet auf a7“.
- **Prüfpunkte zu den GitHub-Runnern (ungeprüft, an der GitHub-Doku prüfen):**
  - Welche Docker- und Compose-Version die Runner mitbringen (wegen `include`, `--wait` und einmaliger Dienste).
  - Ob `host-gateway` in `extra_hosts` auf den Runnern funktioniert (sonst startet `api` nicht).
  - Unter welcher Benutzerkennung der Checkout liegt (vermutlich 1001) und ob die Dev-Dienste im eingebundenen Ordner schreiben können (`web/dist`, das Volume für `node_modules`). Die Stufen `dev` laufen als root und legen Zwischenspeicher unter `/tmp` ab (Aufträge 001 und 002); stellt sich das als unzureichend heraus: Befund in den Kurzbericht, nicht die Dockerfiles ändern.
- Die Befehle sind dieselben wie in den Akzeptanzkriterien der Aufträge 001, 002, 005, 006 und 008. Die Aufträge 009 und 010 laufen gleichzeitig; ihre Tests laufen über `pytest` und `pytest -m worker` automatisch mit.
- Private Repositories haben ein begrenztes Kontingent an Actions-Minuten (Höhe ungeprüft). Läufe kurz halten. Dauert ein Lauf voraussichtlich länger als etwa 10 Minuten: Vorschlag zur Beschleunigung in den Kurzbericht, nicht eigenmächtig Fremd-Actions einbauen.
- Der Bearbeiter kann den Lauf auf GitHub nicht selbst auslösen (kein Push). Er liefert den Workflow und den lokalen Nachweis.
- Parallele Arbeitsverzeichnisse: immer mit `-p twox-011` und Port 18011 arbeiten.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle.
- Kein Push. Die Leitstelle committet nach `main` und pusht auf a7s Freigabe.
- Die Frage unten ändert den Umfang dieses Auftrags nicht. Beantwortet a7 sie nicht mit der Freigabe der Liste, führt die Leitstelle sie als eigenen Eintrag unter „Wartet auf a7“ (Entscheidung bis M3); das Zusammenführen dieses Auftrags entscheidet a7 ohnehin (Stufe C).

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

1. **Wie laufen die Prüffragen in der CI?** E-10 (bestätigt) verlangt, dass sie bei jeder Änderung automatisch mitlaufen; die Abnahme von M6 nennt „Prüffragen in der CI“. GitHub Actions hat aber kein Ollama mit Grafikkarte, und auch Docling läuft dort nicht (Image mehrere Gigabyte).
   - (a) Kleines Modell auf der CPU in der CI. Langsam, kostet Minuten, und die Antworten eines kleinen Modells sagen wenig über das Modell im Betrieb.
   - (b) Aufgezeichnete Antworten: Modell- und Einbettungsantworten und die Ergebnisse von Docling werden lokal einmal aufgezeichnet und in der CI abgespielt. Schnell und wiederholbar; geprüft wird alles außer dem Modell selbst (Suche, Quellenangabe, „Dazu finde ich nichts“). Die Aufzeichnungen müssen bei Änderungen an Prompt oder Modell erneuert werden. Herstellerunterlagen dürfen nicht ins Repository (Abschnitt 10.4): Die Aufzeichnungen stützen sich auf `testdata/klein` oder enthalten keine längeren Auszüge.
   - (c) Nur lokal: Die Leitstelle lässt die Prüffragen vor jedem Zusammenführen gegen das echte Modell auf dem Entwicklungsrechner laufen. Die CI prüft sie nicht. (c) allein widerspricht E-10 und der Abnahme M6 und wäre eine Änderung einer bestätigten Entscheidung.
   - Empfehlung: (b) in der CI **und** (c) vor jedem Zusammenführen nach `main`. So läuft bei jeder Änderung etwas automatisch mit, und die echte Qualität wird dort gemessen, wo das echte Modell läuft. Die Entscheidung wird spätestens zu M3 gebraucht.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
