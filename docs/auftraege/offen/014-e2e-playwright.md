# Auftrag 014 – Playwright-Test der Testseite

Meilenstein: M0 · Freigabestufe: C · Status: offen

## Ziel

Ein Browser-Test belegt automatisch die Abnahme von M0: Die von Django ausgelieferte Testseite zeigt einen Wert aus der Datenbank und ein Ergebnis aus dem Worker. Der Test läuft lokal im Container und in der CI.

## Umfang

- `web/playwright.config.ts` und `web/e2e/selftest.spec.ts`. Der Test öffnet die von Django ausgelieferte Seite und erwartet:
  - eine sichtbare Versionsnummer der Datenbank (Muster Zahl.Zahl),
  - das sichtbare Worker-Ergebnis `pong`,
  - keinen Fehlerzustand und keine Fehlermeldung in der Browser-Konsole.
- Nur ein Browser: Chromium.
- Dienst `e2e` (Profil `e2e`) in `deploy/compose/compose.web.yaml` auf Grundlage des offiziellen Playwright-Images, dessen Version exakt zur Version von `@playwright/test` passt. Die Adresse der API kommt aus einer Umgebungsvariable (Vorgabe `http://api:8000`). Der Dienst hat **kein** `depends_on` auf Dienste anderer Dateien und keinen Host-Port.
- `compose.yaml` im Wurzelverzeichnis: Die `include`-Liste nimmt `deploy/compose/compose.web.yaml` auf. Damit liegen `e2e` und `api` im selben Projekt und Netz, und der Aufruf ist derselbe wie überall (`docker compose` im Wurzelverzeichnis, `.env` im Wurzelverzeichnis). `web-dev` und `e2e` stehen in Profilen und starten bei `docker compose up` nicht mit.
- npm-Skript `e2e`.
- `.github/workflows/ci.yml`:
  - neuer Job `e2e` (Images bauen, `db`, `valkey`, `worker`, `api` starten, Test ausführen, bei Fehlschlag Protokolle und Playwright-Bericht ausgeben),
  - im Job `web` zusätzlich `npm run api:generate` gefolgt von `git diff --exit-code -- web/src/api` (der eingecheckte Client ist aktuell).
- Liste der Abnahmebefehle für M0 im Kurzbericht (für a7 zum Nachvollziehen).

## Nicht-Ziele

- Weitere Browser, Bildvergleiche, Tests weiterer Seiten.
- Docling in der CI.
- Änderungen an der Testseite oder am Backend. Fehlt dem Test trotz Auftrag 012 ein stabiles Merkmal: nur ein Testmerkmal (`data-testid`) ergänzen.

## Betroffene Bereiche (Ordner, Dateien)

- `web/e2e/**`, `web/playwright.config.ts` (neu)
- `web/package.json`, `web/package-lock.json`
- `web/src/**` nur für Testmerkmale, falls nötig
- `web/scripts/` (nur die Regeldatei der Lizenzprüfung, falls nötig)
- `deploy/compose/compose.web.yaml` (Dienst `e2e`)
- `compose.yaml` im Wurzelverzeichnis (eine Zeile in `include`)
- `.github/workflows/ci.yml` (Job `e2e`, Aktualitätsprüfung des Clients)

## Akzeptanzkriterien (prüfbar)

Alle Befehle im Wurzelverzeichnis. `D` steht für `docker compose -p twox-014`, `W` für `docker compose -p twox-014 -f deploy/compose/compose.web.yaml`. Vorher `.env.example` nach `.env` kopieren (falls nicht vorhanden) und darin `TWOX_API_PORT=18014` setzen.

0. Vorab: `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren oder ausführen; Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. `D config --services` nennt `db`, `valkey`, `worker`, `api`, `docling`; mit `D --profile dev --profile e2e config --services` zusätzlich `backend-dev`, `web-dev` und `e2e`. `W config` (die Web-Datei allein) endet weiter mit Exit-Code 0.
2. `D up -d --wait db valkey worker api` endet mit Exit-Code 0; `D ps` zeigt weder `web-dev` noch `e2e` als gestartet.
3. `D --profile e2e run --rm e2e` endet mit Exit-Code 0; die Ausgabe nennt mindestens einen bestandenen Test und 0 fehlgeschlagene.
4. Gegenprobe: Nach `D stop worker` endet derselbe Befehl mit Exit-Code ungleich 0, und die Meldung zeigt, dass `pong` nicht erschien. Danach `D start worker`.
5. Die Version des Playwright-Images und die Version von `@playwright/test` in `web/package-lock.json` stimmen überein (beide im Kurzbericht genannt).
6. `W run --rm web-dev npm run lint`, `npm run typecheck` und `npm run test` enden mit Exit-Code 0; Vitest führt die Playwright-Dateien nicht aus und umgekehrt.
7. Lizenzprüfung: `W run --rm web-dev npm run licenses` endet mit Exit-Code 0. Meldet sie ein Paket mit nicht gedeckter Lizenz: Frage in den Auftrag, Status „wartet auf a7“.
8. `git grep -n 'uses:' -- .github/workflows/ci.yml` zeigt weiterhin nur `actions/checkout`.
9. Jeder Befehl des neuen Jobs `e2e` und die Aktualitätsprüfung des Clients laufen lokal mit Exit-Code 0 durch (Liste im Kurzbericht).
10. Testberichte und Aufzeichnungen sind nicht eingecheckt: `git check-ignore -q web/playwright-report web/test-results` endet mit Exit-Code 0, und `git status --short` zeigt nach einem Lauf nichts Neues. Fehlt ein Eintrag in der `.gitignore`: nicht selbst ändern, im Kurzbericht melden.
11. Abräumen: `D down -v` endet mit Exit-Code 0.
12. Nach dem Push durch die Leitstelle (auf a7s Freigabe): `gh run list --workflow ci.yml --limit 1 --json conclusion` zeigt `success` einschließlich des Jobs `e2e`. Diesen Punkt prüft die Leitstelle; bis dahin bleibt der Auftrag „zur Prüfung“.

## Vorgaben und Hinweise

- **Voraussetzung:** Die Aufträge 011, 012 und 013 sind zusammengeführt (und damit alle davor außer 004 und 007).
- **Abhängigkeiten.** Mit der Freigabe der Auftragsliste genehmigt a7 `@playwright/test`, das offizielle Playwright-Container-Image und den darin enthaltenen Browser Chromium (nur für Tests, nicht Teil des Produkts). Mitgezogene npm-Pakete sind mitgenehmigt, soweit die Lizenzprüfung sie durchlässt. Jede weitere direkte Abhängigkeit ist nicht genehmigt.
- **Stand der Recherche vom 21.11.2026 (belegt):** `@playwright/test` 1.65.1, Apache-2.0, Node >=20.
- **Ungeprüft und an der Quelle zu prüfen:** Name und Tags des Images `mcr.microsoft.com/playwright` und dass es exakt zur Paketversion passen muss; Lizenz des Images und der mitgelieferten Browser (Chromium BSD; Firefox MPL-2.0 und WebKit LGPL werden nicht verwendet). Ist eine Lizenz nicht feststellbar oder nicht zulässig: nicht einbauen, Frage in den Auftrag, Status „wartet auf a7“.
- **Ungeprüft:** dass Dienste aus zwei per `include` eingebundenen Dateien ein gemeinsames Standardnetz haben (Kriterium 3 ist der Nachweis). Klappt es nicht: Befund und Vorschlag in den Auftrag, nicht auf `-f`-Ketten ausweichen (dabei richten sich relative Pfade nach der ersten Datei, und `compose.web.yaml` würde allein nicht mehr gleich funktionieren).
- Das Image ist groß. Lokal als Hintergrundbefehl ziehen; die erwartete Laufzeit des CI-Jobs nennen. Überschreitet der Job voraussichtlich etwa 10 Minuten: Vorschlag in den Kurzbericht, keine Fremd-Action eigenmächtig einbauen.
- Der Test wartet auf Inhalte (mit Zeitlimit), nicht mit festen Pausen.
- Parallele Arbeitsverzeichnisse: immer mit `-p twox-014` und Port 18014 arbeiten.
- Sprache: Code und Testnamen Englisch.
- Abnahmeliste im Kurzbericht: `docker compose up -d --wait` im Wurzelverzeichnis; Testseite unter `http://localhost:8000/` zeigt Datenbankversion und `pong`; Browser-Test; `check_docling`; `check_llm` (mit dem Hinweis, dass `OK:` ein laufendes Ollama voraussetzt); CI-Läufe `ci.yml` und `secrets.yml` grün.
- `.gitignore`, `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Im Kurzbericht Name, Version, Lizenz und Quelle nennen.
- Kein Push. Die Leitstelle committet nach `main` und pusht auf a7s Freigabe.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

Keine zum Start.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
