# Auftrag 015 – ARCHITECTURE.md und README

Meilenstein: M0 · Freigabestufe: B · Status: offen

## Ziel

Ein Mitentwickler versteht aus zwei englischen Dokumenten, wie das Gerüst aufgebaut ist und wie er es startet und prüft. a7 kann die Abnahme von M0 anhand der README Schritt für Schritt nachvollziehen.

## Umfang

- `docs/ARCHITECTURE.md` (Englisch), beschränkt auf das, was nach M0 wirklich vorhanden ist:
  - Container und ihre Aufgaben: `api`, `worker`, `db`, `valkey`, `docling`; Ollama außerhalb auf dem Host.
  - Aufbau des Repositories (Abschnitt 6 der Startunterlage) und der Django-Apps mit je einem Satz zum vorgesehenen Zweck.
  - Aufbau der Compose-Dateien (`compose.yaml` im Wurzelverzeichnis mit `include`, Dateien unter `deploy/compose`, Profile `dev` und `e2e`).
  - Weg einer Anfrage der Testseite durch alle Schichten (Oberfläche → API → Datenbank; API → Broker → Worker → Ergebnis).
  - Die drei Warteschlangen und wofür sie vorgesehen sind.
  - Wie der API-Client der Oberfläche aus dem OpenAPI-Schema entsteht.
  - Tabelle der Umgebungsvariablen (`TWOX_...`) mit Bedeutung und Vorgabe, abgeglichen mit `.env.example`.
  - Qualitätswerkzeuge und die Befehle dafür (einschließlich `pytest` und `pytest -m worker`); welche Prüfungen in der CI laufen und welche nicht (Docling, Ollama, Prüffragen).
- `README.md` (Englisch) im Wurzelverzeichnis:
  - Ein Absatz, was 2x ist (aus Abschnitt 1 der Startunterlage), Hinweis auf den frühen Stand.
  - Voraussetzungen: Docker mit Compose; Ollama optional und außerhalb der Container.
  - Schnellstart: `.env.example` kopieren, `docker compose up`, Adresse der Testseite.
  - Prüfbefehle `check_llm` und `check_docling` mit der Bedeutung ihrer Ausgaben.
  - Befehle für Lint, Typprüfung, Tests, Browser-Test, Lizenzprüfung und Suche nach Geheimnissen.
  - Hinweis zur Größe und Anlaufzeit des Docling-Images.
  - Lizenz (Apache-2.0).

## Nicht-Ziele

- Beschreibung von Funktionen, die es noch nicht gibt (Einlesen, Suche, Auskunft, Anmeldung). Höchstens ein Verweis auf `docs/ROADMAP.md`.
- Installationsanleitung für fremde Rechner (M6).
- Änderungen an Code, Compose-Dateien oder CI. Stimmt ein Befehl nicht: nicht den Code ändern, sondern im Kurzbericht melden.
- `docs/DECISIONS.md`, `docs/STATUS.md`, `docs/ROADMAP.md`, `CLAUDE.md` – pflegt die Leitstelle.

## Betroffene Bereiche (Ordner, Dateien)

- `docs/ARCHITECTURE.md` (neu)
- `README.md` (neu)

## Akzeptanzkriterien (prüfbar)

Vorher `.env.example` nach `.env` kopieren (falls nicht vorhanden) und darin `TWOX_API_PORT=18015` setzen; alle Läufe mit `-p twox-015`.

0. Vorab: `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren oder ausführen; Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. Jeder Befehl aus der README (Schnellstart, Prüfbefehle, Lint, Typprüfung, Tests, Browser-Test, Lizenzprüfung, Suche nach Geheimnissen im Verzeichnis) wurde im Arbeitsverzeichnis in der angegebenen Reihenfolge ausgeführt und verhält sich wie beschrieben. Die Liste der Befehle mit Ergebnis steht im Kurzbericht. Ausnahme: Für `check_llm` genügt eine der beiden beschriebenen Ausgaben (`OK:` oder `FAILED:`).
2. Jede Umgebungsvariable aus `.env.example` steht in der Tabelle und umgekehrt: `git grep -o -h -E 'TWOX_[A-Z_]+' -- .env.example | sort -u` und derselbe Befehl für `docs/ARCHITECTURE.md` liefern dieselbe Liste.
3. Jeder in den Dokumenten genannte Dienst, Pfad und Befehl existiert: alle Dienstnamen gegen `docker compose -p twox-015 --profile dev --profile e2e config --services`, alle genannten Pfade gegen `git ls-files`.
4. Beide Dateien sind auf Englisch; `git grep -n -I -E '[äöüÄÖÜß]' -- README.md docs/ARCHITECTURE.md` ist leer.
5. Keine persönlichen Angaben und keine rechnerspezifischen Pfade: `git grep -n -i -e 'a7' -e 'Desktop' -- README.md docs/ARCHITECTURE.md` ist leer.
6. Die Dokumente nennen keine Funktion als vorhanden, die es nach M0 nicht gibt (Durchsicht durch die Leitstelle).
7. `git diff --stat main...HEAD` zeigt nur `README.md`, `docs/ARCHITECTURE.md` und diese Auftragsdatei.
8. Die Suche nach Geheimnissen bleibt ohne Fund: `docker compose -p twox-015 -f deploy/compose/compose.tools.yaml run --rm gitleaks-dir` endet mit Exit-Code 0.
9. Abräumen: `docker compose -p twox-015 down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

**Nachtrag der Leitstelle (21.11.2026):** `.env.example` setzt `TWOX_DEBUG=true` für die Entwicklung; im Browser zeigt Django deshalb bei 404 die URL-Liste. Die README muss sagen, dass `TWOX_DEBUG` für jeden Betrieb außerhalb der Entwicklung leer bzw. `false` bleibt (Vorgabe in `settings.py` ist aus). Für M6 (Installation in 10 Minuten) braucht es eine eigene Vorlage ohne Debug – als Hinweis für den M6-Auftrag in den Kurzbericht.

- **Voraussetzung:** Die Aufträge 006, 007, 009, 013 und 014 sind zusammengeführt (damit alle M0-Aufträge außer der Messung 004, die für die Doku nicht gebraucht wird).
- **Keine neue Abhängigkeit**, kein Werkzeug zur Doku-Erzeugung. Schaubilder als Text oder als Mermaid-Block im Markdown (wird von GitHub dargestellt; nichts wird installiert). Stufe B gilt nur, solange das so bleibt.
- Sprache nach Abschnitt 7: README und Entwicklerdoku Englisch.
- Keine Auszüge aus fremden Handbüchern, kein Material des Arbeitgebers (Leitplanke 1, Abschnitt 10.4).
- Versionen nicht im Fließtext wiederholen, sondern auf die Dateien verweisen, in denen sie festgeschrieben sind (`uv.lock`, `package-lock.json`, Compose-Dateien). So veraltet die Doku nicht.
- Der Start aller Container einschließlich Docling dauert beim ersten Mal lange (Image mehrere Gigabyte); als Hintergrundbefehl starten.
- Parallele Arbeitsverzeichnisse: immer mit `-p twox-015` und Port 18015 arbeiten. In der README steht der Normalfall (Port 8000, kein `-p`).
- Kein Push. Die Leitstelle committet nach `main` und pusht auf a7s Freigabe.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
