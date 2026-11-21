# Auftrag 004 – Messung Dateizugriff

Meilenstein: M0 · Freigabestufe: B · Status: erledigt

## Ziel

a7 kann anhand von Messwerten entscheiden, ob das Repository im Windows-Ordner bleibt oder in das WSL-2-Dateisystem umzieht (Abschnitt 5.5: „Entscheidung in M0 nach Messung“). Der Auftrag liefert Messskript und Zahlen; die Entscheidung trifft a7 getrennt.

## Umfang

- Ein wiederholbares Messskript `deploy/compose/bench-file-access.sh` und, falls nötig, `deploy/compose/compose.bench.yaml`.
- Gemessen werden dieselben Arbeitsschritte in zwei Lagen:
  - **Lage 1 – Windows-Ordner:** Quelltext als Bind-Mount aus dem Arbeitsverzeichnis (so arbeiten die Aufträge heute).
  - **Lage 2 – Linux-Dateisystem:** eine Kopie des Quelltexts in einem benannten Docker-Volume (liegt im WSL-2-Dateisystem).
- Arbeitsschritte, je dreimal; angegeben werden Median und Spannweite in Sekunden:
  - Backend (Dienst `backend-dev`, eingebundener Quelltext): `pytest`, `mypy .`, `ruff check .`, `python manage.py check`.
  - Web (Dienst `web-dev`): `npm ci`, `npm run test`, `npm run build`.
  - Dateisystem allgemein, mit einem kleinen Python-Skript aus der Standardbibliothek: 10 000 kleine Dateien anlegen, lesen und löschen; alle Dateien des Quelltexts rekursiv auflisten und mit `stat` abfragen.
- Ergebnis im Kurzbericht: Tabelle (Arbeitsschritt · Lage 1 · Lage 2 · Faktor), Messbedingungen (Docker-Desktop-Version, WSL-Version, Datum) und ein Entwurf für den Eintrag im Entscheidungsprotokoll mit Empfehlung.

## Nicht-Ziele

- Der Umzug selbst. Er wäre ein eigener Auftrag nach a7s Entscheidung.
- Änderungen an Docker Desktop, an WSL oder an Windows-Einstellungen.
- Arbeiten außerhalb des Projektordners.
- Messungen mit Git im Container: Die genehmigten Images enthalten kein Git, und im Arbeitsverzeichnis eines Auftrags zeigt `.git` auf einen Pfad außerhalb des Containers.
- Messung des Dienstes `api` (er nutzt die Stufe `runtime` ohne Bind-Mount und sagt nichts über den Dateizugriff).
- Optimierungen am Code oder an den Dockerfiles.

## Betroffene Bereiche (Ordner, Dateien)

- `deploy/compose/bench-file-access.sh` (neu)
- `deploy/compose/compose.bench.yaml` (neu, falls nötig)
- Diese Auftragsdatei (Kurzbericht mit Messtabelle)

## Akzeptanzkriterien (prüfbar)

0. Vorab: `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren oder ausführen; Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. `bash deploy/compose/bench-file-access.sh` (in Git Bash, im Wurzelverzeichnis) endet mit Exit-Code 0 und gibt eine Tabelle mit allen oben genannten Arbeitsschritten und je einem Median für beide Lagen aus.
2. Ein zweiter Lauf liefert für jeden Arbeitsschritt, dessen Median über 5 Sekunden liegt, einen Median, der höchstens 20 % vom ersten Lauf abweicht. Für kürzere Schritte wird nur die Spannweite angegeben. Wird die Grenze verfehlt: Ursache nennen (zum Beispiel Virenscanner) und einmal wiederholen; bleibt es dabei, beide Läufe in den Kurzbericht – der Auftrag bleibt abschließbar.
3. Nach dem Lauf sind die für die Messung angelegten Container und Volumes entfernt: `docker volume ls --filter name=twox-bench` und `docker ps -a --filter name=twox-bench` sind leer.
4. `git status --short` zeigt nach dem Lauf keine neuen oder geänderten Dateien außer dem Skript (und der Compose-Datei) selbst.
5. Das Skript hat LF-Zeilenenden: `git ls-files --eol deploy/compose/bench-file-access.sh` zeigt `i/lf w/lf`.
6. Der Kurzbericht enthält Tabelle, Messbedingungen, eine Empfehlung (bleiben oder umziehen) und die Folgen eines Umzugs (siehe Hinweise).

## Vorgaben und Hinweise

**Nachtrag der Leitstelle (21.11.2026, aus der Prüfung von Auftrag 001):** `backend-dev` wird über die `compose.yaml` im Wurzelverzeichnis angesprochen (ohne `-f`), `web-dev` über `-f deploy/compose/compose.web.yaml`. Bei direktem `-f deploy/compose/compose.yaml` zusätzlich `--env-file .env` angeben. Vorher `.env.example` nach `.env` kopieren.

**Nachtrag der Leitstelle (21.11.2026, aus der Prüfung von Auftrag 002):** Der Dienst `web-dev` liegt im Profil `dev`. Deshalb gilt abweichend vom Wortlaut dieses Auftrags: Bauen mit `build web-dev` oder `--profile dev build`; Abräumen mit `--profile dev down -v` (bei Playwright zusätzlich `--profile e2e`); den Dienst immer über `run --rm web-dev` ansprechen – ein bloßes `build`, `up` oder `down -v` ohne Profil tut nichts und meldet trotzdem Erfolg. `git check-ignore -q` nimmt nur einen Pfad je Aufruf. Zugelassene Lizenzen bei reinen Entwicklungs- und Build-Paketen zusätzlich: BlueOak-1.0.0, CC-BY-3.0, CC-BY-4.0, CC0-1.0 (E-25).

- **Voraussetzung:** Die Aufträge 001 und 002 sind zusammengeführt.
- **Keine neue Abhängigkeit.** Verwendet werden nur die Images und Werkzeuge aus den Aufträgen 001 und 002. Stufe B gilt nur, solange das so bleibt.
- Das Skript ist ein Bash-Skript, das nur `docker compose` aufruft; alle Messungen laufen in Containern. Git Bash ist mit Git für Windows vorhanden; es wird nichts installiert.
- Dieser Auftrag läuft allein in seiner Welle, damit keine anderen Aufträge Last erzeugen. Compose-Projektname `twox-bench`. Kein Host-Port.
- `pytest` läuft in der Voreinstellung; Tests, die einen laufenden Worker brauchen, gibt es zu diesem Zeitpunkt noch nicht.
- Die Unterlage nennt keine Schwelle, ab der „zu langsam“ gilt. Keine Schwelle erfinden: Zahlen liefern, die Entscheidung trifft a7.
- Im Kurzbericht die Folgen eines Umzugs nennen, soweit bekannt, und Ungeprüftes als solches kennzeichnen: Projektpfad in Abschnitt 5.5 und 13 ändert sich; ob die Claude-Desktop-App eine lokale Sitzung und Arbeitsverzeichnisse in einem WSL-Pfad führen kann (ungeprüft, an der Claude-Code-Doku prüfen); Git für Windows gegen Git in Debian; Regel „Nur im Projektordner arbeiten“.
- Alternative ohne Umzug mit benennen, falls die Messung sie nahelegt: Abhängigkeiten und Build-Ergebnisse in Volumes halten (wie `node_modules` in Auftrag 002), Quelltext im Windows-Ordner lassen.
- Die Entscheidung „bleiben oder umziehen“ gehört nicht zu diesem Auftrag. Die Leitstelle legt sie nach dem Zusammenführen mit Tabelle und Empfehlung unter „Wartet auf a7“ vor.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle.
- Kein Push. Die Leitstelle committet nach `main` und pusht auf a7s Freigabe.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

1. **Womit wird das WSL-2-Dateisystem gemessen?** a7 beantwortet das mit der Freigabe der Liste; fehlt die Antwort, gilt nichts als entschieden: Status „wartet auf a7“.
   - (a) Mit einem benannten Docker-Volume. Es liegt im WSL-2-Dateisystem, und der Auftrag bleibt im Projektordner.
   - (b) Zusätzlich mit einer vorübergehenden Kopie des Repositories in der Debian-Umgebung (zum Beispiel `~/twox-bench`), die nach der Messung gelöscht wird. Das verlässt den Projektordner und braucht a7s ausdrückliche Erlaubnis.
   - Empfehlung: (a). (b) nur nachholen, wenn das Ergebnis knapp ausfällt. Der Auftrag ist für (a) geschrieben.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Messung am 21.11.2026 abgeschlossen, zwei vollständige Läufe.

### Was wurde gebaut?

- `deploy/compose/bench-file-access.sh`: Bash-Skript, ruft nur `docker compose` auf (Statistik mit `awk`/`sort` aus Git Bash). Es baut die Images, startet `db`, kopiert `backend/` und `web/` (ohne `node_modules`, `dist`) per `tar` in zwei benannte Volumes, füllt einen gemeinsamen npm-Zwischenspeicher und misst dann jeden Schritt in einem frischen Container (`run --rm`). Die Zeit wird im Container mit `date +%s%N` um den Befehl gemessen; der Containerstart zählt nicht mit. Je Schritt ein kalter Lauf (getrennt ausgewiesen) und `BENCH_RUNS` warme Läufe (Vorgabe 5), daraus Median und Spannweite. L1 und L2 wechseln sich Schritt für Schritt ab, die Reihenfolge kehrt sich je Wiederholung um. Am Ende: `down --volumes --rmi local --remove-orphans`, `backend/.bench-fs`, `web/dist` und der leere Einhängepunkt `web/node_modules` werden entfernt (nur wenn sie vorher nicht da waren). Einstellbar: `BENCH_PROJECT` (Vorgabe `twox-bench`), `BENCH_RUNS`, `BENCH_RAW` (Rohdaten behalten).
- `deploy/compose/compose.bench.yaml`: Überlagerung zu `compose.yaml` und `compose.web.yaml`. Dienste `backend-dev-vol` und `web-dev-vol` (per `extends` aus `backend-dev`/`web-dev`, Quelltext im Volume statt Bind-Mount), `bench-seed` (Kopierdienst), Volume `npm_cache` für `web-dev` und `web-dev-vol`.
- Lage 1 (L1) = die heutigen Dienste `backend-dev` und `web-dev` (Bind-Mount aus dem Windows-Ordner; `node_modules` wie bisher im Volume). Lage 2 (L2) = Quelltext und `node_modules` in benannten Volumes (WSL-2-Dateisystem der Docker-Desktop-VM), gemäß E-23 ohne Kopie in die Debian-Umgebung.
- Arbeitsschritte: Backend `pytest -q`, `mypy .`, `ruff check .`, `python manage.py check`; Web `npm ci --prefer-offline`, `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`; Dateisystem mit Python-Standardbibliothek: 10 000 Dateien à 100 Byte anlegen, lesen, löschen (je einzeln gemessen) und `backend/` 20-mal rekursiv auflisten mit `os.stat` (je Durchgang rund 57 Dateien).

### Messbedingungen

- Datum 21.11.2026, Lauf 1 von 17:47 bis 18:04, Lauf 2 von 18:04 bis 18:21 Ortszeit (die Kopfzeile der Skriptausgabe nennt die Endzeit in UTC).
- Docker Desktop 4.99.0 (245822), Engine 29.9.3, Compose 5.7.0; WSL 2.3.26.0, Kernel 5.15.167.4-microsoft-standard-WSL2, 16 CPUs in der VM; Windows 11 Pro 10.0.26300. Rechner laut Startunterlage 5.5.
- Compose-Projekt `twox-004-bench` (über `BENCH_PROJECT`, siehe Abweichungen). Kein Host-Port.
- **Störgrößen:** Parallel liefen die Aufträge 011 (lokal mit Docker-Läufen) und 113 (ohne Docker) sowie die Testumgebung „2x“ der Leitstelle (5 Container, im Leerlauf, zusammen unter 6 % CPU bei einer Stichprobe). Ein Virenscanner unter Windows wurde nicht geprüft. Gegenmaßnahme: abwechselnde Messung (siehe oben). Einzelne Ausreißer in den Spannweiten (z. B. mypy 9,52 s in Lauf 1) gehen vermutlich auf diese Last zurück; die Mediane sind davon kaum berührt.
- `npm ci` liest aus einem gemeinsamen, vorher gefüllten npm-Zwischenspeicher (`--prefer-offline`), damit nicht die Download-Zeit gemessen wird.
- mypy- und pytest-Zwischenspeicher liegen laut Dockerfile in `/tmp` des Containers; jeder Lauf ist für sie also kalt (wie heute bei `run --rm`).

### Messtabelle (Sekunden; Median und Spannweite aus 5 warmen Läufen; Faktor = Median L1 / Median L2)

Lauf 1:

| Arbeitsschritt | L1 kalt | L2 kalt | L1 Median | L1 Spanne | L2 Median | L2 Spanne | Faktor |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pytest | 27,18 | 24,67 | 28,05 | 27,25–29,70 | 25,74 | 24,92–26,43 | 1,09 |
| mypy | 5,07 | 4,70 | 5,58 | 5,14–9,52 | 4,94 | 4,75–7,82 | 1,13 |
| ruff check | 0,10 | 0,04 | 0,09 | 0,09–0,17 | 0,04 | 0,02–0,09 | 2,25 |
| manage.py check | 2,23 | 1,94 | 2,25 | 2,25–3,22 | 2,01 | 1,95–2,49 | 1,12 |
| npm ci | 5,26 | 5,53 | 6,07 | 5,81–6,21 | 6,03 | 5,47–8,50 | 1,01 |
| npm run lint | 3,07 | 2,79 | 3,12 | 2,90–3,26 | 2,69 | 2,64–3,63 | 1,16 |
| npm run typecheck | 1,55 | 1,43 | 1,46 | 1,43–1,52 | 1,32 | 1,27–1,50 | 1,11 |
| npm run test | 1,72 | 1,22 | 1,55 | 1,50–1,57 | 1,16 | 1,06–1,26 | 1,34 |
| npm run build | 0,70 | 0,51 | 0,76 | 0,68–0,76 | 0,51 | 0,46–0,66 | 1,49 |
| 10 000 Dateien anlegen | 16,58 | 0,32 | 16,27 | 16,13–17,21 | 0,33 | 0,32–0,34 | 49 |
| 10 000 Dateien lesen | 15,37 | 0,11 | 15,02 | 14,90–16,08 | 0,11 | 0,10–0,12 | 137 |
| 10 000 Dateien löschen | 8,62 | 0,15 | 8,97 | 8,73–9,73 | 0,14 | 0,13–0,16 | 64 |
| Auflisten + stat (20 Durchgänge) | 2,38 | 0,01 | 2,38 | 2,27–2,41 | 0,01 | 0,01–0,01 | > 200 |

Lauf 2 (Kriterium 2):

| Arbeitsschritt | L1 kalt | L2 kalt | L1 Median | L1 Spanne | L2 Median | L2 Spanne | Faktor |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pytest | 27,67 | 25,61 | 28,03 | 27,70–29,75 | 25,40 | 25,35–27,96 | 1,10 |
| mypy | 5,12 | 4,66 | 5,25 | 5,12–5,39 | 4,84 | 4,67–4,90 | 1,08 |
| ruff check | 0,10 | 0,02 | 0,10 | 0,09–0,11 | 0,04 | 0,03–0,05 | 2,50 |
| manage.py check | 2,30 | 1,95 | 2,32 | 2,21–2,55 | 1,99 | 1,92–2,23 | 1,17 |
| npm ci | 5,49 | 5,40 | 5,83 | 5,70–6,08 | 5,95 | 5,69–6,18 | 0,98 |
| npm run lint | 3,24 | 3,36 | 3,04 | 3,01–3,10 | 2,72 | 2,64–2,86 | 1,12 |
| npm run typecheck | 1,63 | 1,57 | 1,54 | 1,48–1,62 | 1,36 | 1,29–1,43 | 1,13 |
| npm run test | 1,82 | 1,23 | 1,60 | 1,55–1,61 | 1,14 | 1,13–1,20 | 1,40 |
| npm run build | 0,74 | 0,59 | 0,75 | 0,71–0,81 | 0,51 | 0,49–0,57 | 1,47 |
| 10 000 Dateien anlegen | 16,37 | 0,51 | 16,55 | 16,53–17,02 | 0,32 | 0,30–0,34 | 52 |
| 10 000 Dateien lesen | 15,19 | 0,12 | 14,94 | 14,33–15,42 | 0,11 | 0,10–0,13 | 136 |
| 10 000 Dateien löschen | 9,11 | 0,14 | 8,76 | 8,49–8,99 | 0,13 | 0,13–0,14 | 67 |
| Auflisten + stat (20 Durchgänge) | 2,59 | 0,01 | 2,32 | 2,25–2,38 | 0,01 | 0,01–0,01 | > 200 |

Abweichung der Mediane über 5 s zwischen Lauf 1 und 2: pytest L1 0,1 %, L2 1,3 %; mypy L1 5,9 %; npm ci L1 4,0 %, L2 1,3 %; anlegen L1 1,7 %; lesen L1 0,5 %; löschen L1 2,3 %. Alle unter 20 %. Schritte unter 5 s: nur Spannweite (siehe Tabellen).

Ein Vorlauf mit `BENCH_RUNS=1` (17:41) lieferte dieselben Größenordnungen.

### Bewertung und Empfehlung: **bleiben**

- Die reinen Dateisystem-Operationen sind im Windows-Ordner 50- bis über 200-mal langsamer (rund 1,5 ms je angelegter, gelesener oder gelöschter Datei, rund 2 ms je `stat` (Hochrechnung aus rund 1 100 Aufrufen), gegen Mikrosekunden im Volume).
- Die tatsächlichen Entwicklerbefehle spüren das kaum, weil heute schon alles Dateireiche außerhalb des Windows-Ordners liegt: die Python-Umgebung im Image (`/opt/venv`), `node_modules` im Volume, Zwischenspeicher in `/tmp`. Der Quelltext selbst ist klein (`backend/` 57, `web/` 39 Dateien unter Git). Faktor 1,0 bis 1,5 (ruff 2,5, aber bei 0,1 s); absolut 0,0 bis 2,7 s je Befehl. Ein kompletter Durchgang aller neun Befehle kostet im Windows-Ordner etwa 49 s, im Volume etwa 44 s (Summe der Mediane, Lauf 2).
- pytest braucht in beiden Lagen rund 25 bis 28 s; der Großteil hängt also nicht am Dateizugriff (vermutlich Anlegen der Testdatenbank und Migrationen – nicht geprüft).
- Das Ergebnis ist nicht knapp. Eine Zusatzmessung nach Frage 1 (b) ist nicht nötig.
- **Alternative ohne Umzug (empfohlen als Regel):** Abhängigkeiten, Build-Ergebnisse und Zwischenspeicher weiterhin nie in den Windows-Ordner legen – wie `node_modules` in Auftrag 002 und die Zwischenspeicher in Auftrag 001. Nach den Zahlen oben würde z. B. ein `node_modules` mit einigen zehntausend Dateien im Bind-Mount allein durch das Schreiben mehrere Minuten kosten (Hochrechnung, nicht gemessen). `web/dist` (Build-Ausgabe) liegt heute noch im Bind-Mount; bei der jetzigen Größe kostet das etwa 0,25 s.
- Neu bewerten, falls der Quelltext stark wächst oder ein Werkzeug viele Dateien im Quelltextbaum schreibt (z. B. Dateibeobachtung im Vite-Entwicklungsserver; laut Claude-Code-Doku bricht die Dateibeobachtung über das Netzdateisystem – nicht gemessen).

### Folgen eines Umzugs (falls a7 anders entscheidet)

- Projektpfad in Startunterlage 5.5 und 13 ändert sich (Linux-Pfad in der Debian-Umgebung).
- Claude-Desktop-App: Laut Claude-Code-Doku (Seite „desktop-wsl“, gelesen am 21.11.2026) kann die Desktop-App Sitzungen in einer WSL-2-Distribution führen; `\\wsl.localhost\…`-Ordner öffnen sich darin, Git muss in der Distribution installiert sein, Worktrees „funktionieren“. **Ungeprüft:** ob die Unteragenten-Isolation mit Arbeitsverzeichnissen unter `.claude/worktrees/` dort genauso läuft (die Doku sagt dazu nichts ausdrücklich). Laut derselben Seite fehlen in WSL-Sitzungen Plugins, teils Konnektoren und das Terminal; Vertrauen gilt je Distribution und Ordner neu.
- Git: Git für Windows (Git Bash, Grundlage des Bash-Werkzeugs von Claude Code unter Windows) würde durch Git in Debian ersetzt; laut Doku braucht eine WSL-Einrichtung kein Git für Windows. Zugangsdaten für GitHub und Signaturen müssten in Debian neu eingerichtet werden (ungeprüft, wie aufwendig).
- Docker: Bind-Mounts aus der Debian-Umgebung laufen über die WSL-Integration von Docker Desktop; diese muss für die Distribution eingeschaltet sein (ungeprüft, ob sie es ist).
- Regel „Nur im Projektordner arbeiten“ bezöge sich auf den neuen Pfad; die Windows-Werkzeuge (Editor, Explorer) griffen dann ihrerseits über das Netzdateisystem zu.
- Ollama läuft weiter unter Windows; die Erreichbarkeit über `host.docker.internal` ändert sich durch den Umzug nicht (Annahme, nicht geprüft).

### Entwurf für das Entscheidungsprotokoll

> **E-xx Lage des Repositorys: Windows-Ordner bleibt (Entwurf, Entscheidung durch a7).** Gemessen in Auftrag 004 am 21.11.2026 (Docker Desktop 4.99.0, WSL 2.3.26.0). Die typischen Entwicklerbefehle (pytest, mypy, ruff, manage.py check, npm ci/lint/typecheck/test/build) sind im Bind-Mount aus dem Windows-Ordner 0 bis 50 % langsamer als in einem benannten Docker-Volume (ruff 150 % bei 0,1 s), absolut höchstens etwa 3 s je Befehl. Reine Dateioperationen sind im Windows-Ordner 50- bis über 200-mal langsamer. Das Repository bleibt deshalb im Windows-Ordner; Regel: Abhängigkeiten, Build-Ergebnisse und Zwischenspeicher liegen in Images, Volumes oder `/tmp` des Containers, nie im eingebundenen Quelltext. Neu messen mit `deploy/compose/bench-file-access.sh`, wenn der Quelltext stark wächst oder ein Werkzeug viele Dateien im Quelltextbaum schreibt.

### Wie wurde getestet? (Akzeptanzkriterien)

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version` (Engine 29.9.3) und `docker compose version` (v5.7.0): Exit 0 |
| 1 | erfüllt | `bash deploy/compose/bench-file-access.sh` in Git Bash (aufgerufen über PowerShell, mit `BENCH_PROJECT=twox-004-bench`): zweimal Exit 0, Tabelle mit allen Schritten und Medianen beider Lagen |
| 2 | erfüllt | Alle Mediane über 5 s weichen zwischen Lauf 1 und 2 höchstens 5,9 % ab (mypy L1) |
| 3 | erfüllt | Nach jedem Lauf leer: `docker ps -a` und `docker volume ls` mit Filter `twox-bench` und mit Filter `twox-004`; auch die gebauten `twox-004-bench-*`-Images sind entfernt |
| 4 | erfüllt | `git status --short` nach den Läufen: nur das Skript und die Compose-Datei (danach committet); `--ignored` zeigt nur `.env` und `STARTUNTERLAGE.md` |
| 5 | erfüllt | `git ls-files --eol deploy/compose/bench-file-access.sh`: `i/lf w/lf` |
| 6 | erfüllt | Tabelle, Messbedingungen, Empfehlung und Folgen eines Umzugs: siehe oben |

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a633e87805d65981b`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a633e87805d65981b` (relativ zum Projektordner)

### Abweichungen

- **Projektname:** Vorgabe im Skript ist `twox-bench` (Auftrag). Gemessen wurde nach Vorgabe der Leitstelle mit `BENCH_PROJECT=twox-004-bench`. Kriterium 3 wurde deshalb zusätzlich mit dem Filter `twox-004` geprüft.
- **Mehr Wiederholungen und Schritte als im Auftrag:** 1 kalter + 5 warme Läufe statt 3; zusätzlich `npm run lint` und `npm run typecheck` (Hinweis der Leitstelle). Messbefehl `npm ci --prefer-offline` mit gemeinsamem npm-Zwischenspeicher-Volume (sonst misst man den Download).
- **Nicht allein in der Welle:** Parallel liefen 011, 113 und die Testumgebung „2x“ (siehe Störgrößen).
- **`down --rmi local`:** Das Skript entfernt auch die eigenen gebauten Images; der Build-Zwischenspeicher von Docker bleibt.
- Nicht gemessen: `node_modules` im Bind-Mount (nur hochgerechnet), Vite-Entwicklungsserver mit Dateibeobachtung, Git-Befehle (Nicht-Ziel), Frage 1 (b).
- Ausgeführt wurde das Skript aus PowerShell über Git Bash (`bash.exe` aus Git für Windows), nicht über das Bash-Werkzeug der Sitzung.
