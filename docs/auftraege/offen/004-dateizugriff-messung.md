# Auftrag 004 – Messung Dateizugriff

Meilenstein: M0 · Freigabestufe: B · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
