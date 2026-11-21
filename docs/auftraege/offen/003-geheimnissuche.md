# Auftrag 003 – Suche nach Geheimnissen

Meilenstein: M0 · Freigabestufe: C · Status: offen

## Ziel

Jede Änderung wird auf versehentlich eingecheckte Geheimnisse geprüft: lokal mit einem Befehl im Container und in GitHub Actions bei jedem Push.

## Umfang

- `deploy/compose/compose.tools.yaml` mit zwei Diensten auf Grundlage des Werkzeugs gitleaks (Kommandozeile):
  - `gitleaks-dir`: durchsucht das eingebundene Arbeitsverzeichnis (ohne Verlauf). Das ist der Lauf des Auftragsbearbeiters.
  - `gitleaks-git`: durchsucht den gesamten Git-Verlauf. Das ist der Lauf der Leitstelle im Hauptordner und der Lauf in der CI. Im Dienst ist `safe.directory` für den eingebundenen Pfad gesetzt (zum Beispiel über `GIT_CONFIG_COUNT`, `GIT_CONFIG_KEY_0`, `GIT_CONFIG_VALUE_0`), weil der Ordner im Container einem anderen Benutzer gehört.
- `.gitleaks.toml` im Wurzelverzeichnis: Standardregeln von gitleaks. Pfad-Ausnahmen mit Kommentar für `testfactory/extern/` (geladene Herstellerunterlagen, nicht im Repository) und `.claude/worktrees/` (Arbeitsverzeichnisse anderer Aufträge). Weitere Ausnahmen nur, wenn ein Fehlalarm belegt ist, und dann so eng wie möglich (Datei und Regel).
- `.github/workflows/secrets.yml`: läuft bei Push auf alle Zweige und bei Pull Requests, checkt mit vollständigem Verlauf aus (`fetch-depth: 0`) und ruft den Dienst `gitleaks-git` auf. Berechtigungen des Workflows: nur `contents: read`.
- Nachweis, dass die Suche anschlägt (Kriterium 3).

## Nicht-Ziele

- **Nicht** die GitHub-Action `gitleaks/gitleaks-action` verwenden: Sie steht unter einer proprietären Lizenz (EULA), nur das Werkzeug selbst ist MIT.
- Nicht TruffleHog (AGPL-3.0) und nicht detect-secrets (kaum gepflegt).
- Lizenzprüfung (Auftrag 006), übrige CI (Auftrag 011).
- Einstellungen am GitHub-Konto oder Repository (siehe Frage 1; das macht a7).

## Betroffene Bereiche (Ordner, Dateien)

- `deploy/compose/compose.tools.yaml` (neu)
- `.gitleaks.toml` (neu)
- `.github/workflows/secrets.yml` (neu)

## Akzeptanzkriterien (prüfbar)

`T` steht für `docker compose -p twox-003 -f deploy/compose/compose.tools.yaml`.

0. Vorab: `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren oder ausführen; Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. `T run --rm gitleaks-dir` endet mit Exit-Code 0 und meldet, dass keine Funde vorliegen (`no leaks found`).
2. `T run --rm gitleaks-dir version` (oder gleichwertig) zeigt die festgeschriebene gitleaks-Version.
3. Gegenprobe: Eine vorübergehend angelegte, **nicht eingecheckte** Datei mit einem erfundenen Schlüssel im Format eines bekannten Anbieters lässt `T run --rm gitleaks-dir` mit Exit-Code ungleich 0 enden. Danach wird die Datei gelöscht; `git status --short` zeigt sie nicht mehr. Befehl und Ausgabe stehen im Kurzbericht (ohne den Schlüssel selbst).
4. Pfad-Ausnahme: Dieselbe Probedatei unter `testfactory/extern/` (Ordner vorübergehend anlegen) führt zu **keinem** Fund. Danach Datei und Ordner wieder löschen.
5. `git grep -n 'uses:' -- .github/workflows/secrets.yml` zeigt nur `actions/checkout`, festgelegt auf einen Commit-Hash; `gitleaks-action` kommt nicht vor.
6. Der Workflow ruft `gitleaks-git` aus `compose.tools.yaml` mit derselben `.gitleaks.toml` auf, die auch die Leitstelle verwendet (Durchsicht der Datei).
7. Verlaufs-Suche – prüft die Leitstelle, nicht der Bearbeiter: Im Hauptordner endet `docker compose -f deploy/compose/compose.tools.yaml run --rm gitleaks-git` nach dem Zusammenführen mit Exit-Code 0. Im Arbeitsverzeichnis des Bearbeiters ist das nicht möglich (siehe Hinweise).
8. Nach dem Push durch die Leitstelle (auf a7s Freigabe): `gh run list --workflow secrets.yml --limit 1 --json conclusion` zeigt `success`. Diesen Punkt prüft die Leitstelle; bis dahin bleibt der Auftrag „zur Prüfung“.
9. Abräumen: `T down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

- **Voraussetzung:** keine. Das Grundgerüst der Leitstelle ist vorhanden.
- **Warum zwei Dienste:** Im Arbeitsverzeichnis eines Auftrags ist `.git` nur eine Datei, die auf einen Windows-Pfad im Hauptordner zeigt. Im Linux-Container gibt es diesen Pfad nicht; eine Suche im Verlauf findet dort kein Repository. Der Bearbeiter prüft deshalb nur das Verzeichnis; den Verlauf prüfen die Leitstelle im Hauptordner (dort ist `.git` ein echter Ordner) und die CI.
- **Abhängigkeiten.** Mit der Freigabe der Auftragsliste genehmigt a7: gitleaks (Kommandozeile, MIT) und die Action `actions/checkout` (MIT, laut Prüfbefund vom 21.11.2026 an der LICENSE-Datei belegt). Jede weitere ist nicht genehmigt. Ergibt die Prüfung an der Quelle eine andere Lizenz oder ist sie nicht feststellbar: nicht einbauen, Frage in den Auftrag, Status „wartet auf a7“.
- **Versionen (Stand der Recherche vom 21.11.2026):** gitleaks v8.30.1 (MIT, belegt). Laut Prüfbefund kennt gitleaks die Unterbefehle `git` (Verlauf, ruft `git log -p` auf) und `dir` (Verzeichnis ohne Verlauf). Ungeprüft und hier an der Quelle zu prüfen: ob das Image `ghcr.io/gitleaks/gitleaks` existiert, welche Tags es hat und ob es Git enthält; die genaue Befehlsform; aktuelle Version von `actions/checkout`; ob der Verzeichnis-Lauf Pfad-Ausnahmen aus `.gitleaks.toml` beachtet (Kriterium 4 ist der Nachweis).
- Image mit fester Version und Digest festlegen.
- Die Gegenprobe darf kein echtes Geheimnis verwenden und nichts davon einchecken.
- Der Bearbeiter lädt nichts außerhalb von Containern herunter und installiert nichts auf dem Rechner.
- Pfade in `compose.tools.yaml` relativ zu `deploy/compose` schreiben (das Repository liegt zwei Ebenen darüber).
- `.gitignore`, `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Im Kurzbericht Name, Version, Digest, Lizenz und Quelle nennen.
- Kein Push. Die Leitstelle committet nach `main` und pusht auf a7s Freigabe.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

1. **Zusätzlich GitHub Secret Scanning mit Push Protection einschalten?** Das ist eine Einstellung am Repository bzw. Konto und damit a7s Sache. Ob es für private Repositories im kostenlosen Tarif verfügbar ist, ist ungeprüft.
   - (a) a7 prüft beim Anlegen des Repositories, ob die Funktion verfügbar ist, und schaltet sie ein.
   - (b) Nur gitleaks in der CI.
   - Empfehlung: (a) als zweite Sicherung, falls ohne Aufpreis verfügbar; gitleaks bleibt in jedem Fall. Der Auftrag wartet nicht auf diese Antwort; sie betrifft keine Datei im Repository.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
