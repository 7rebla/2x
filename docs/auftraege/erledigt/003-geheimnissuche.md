# Auftrag 003 – Suche nach Geheimnissen

Meilenstein: M0 · Freigabestufe: C · Status: erledigt

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

Stand: 21.11.2026. Status „zur Prüfung“; die Kriterien 7 und 8 prüft die Leitstelle (8 wartet auf Push-Freigabe).

### Was wurde gebaut?

- `deploy/compose/compose.tools.yaml` mit den Diensten `gitleaks-dir` (Verzeichnis ohne Verlauf) und `gitleaks-git` (gesamter Verlauf, `safe.directory=/repo` über `GIT_CONFIG_*`). Das Repository wird nur lesend nach `/repo` eingebunden, die Dienste haben kein Netz (`network_mode: none`), Funde werden geschwärzt ausgegeben (`--redact`).
- `.gitleaks.toml`: Standardregeln (`[extend] useDefault = true`) und zwei Pfad-Ausnahmen mit Kommentar: `testfactory/extern/` und `.claude/worktrees/`, am Wurzelverzeichnis verankert. Keine weiteren Ausnahmen.
- `.github/workflows/secrets.yml`: Push auf alle Zweige und Pull Requests, `permissions: contents: read`, `actions/checkout` auf Commit-Hash mit `fetch-depth: 0` und `persist-credentials: false`, danach `docker compose -f deploy/compose/compose.tools.yaml run --rm gitleaks-git`.

### Festgelegte Versionen (für `docs/DECISIONS.md`)

| Name | Version | Festlegung | Lizenz | Quelle und Beleg |
| --- | --- | --- | --- | --- |
| gitleaks (Kommandozeile, Container-Image) | v8.30.1 | `ghcr.io/gitleaks/gitleaks:v8.30.1@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f` | MIT | github.com/gitleaks/gitleaks, Tag v8.30.1 = Commit `83d9cd684c87d95d656c1458ef04895a7f1cbd8e`; LICENSE-Datei an diesem Tag gelesen („MIT License“); Image-Label `org.opencontainers.image.licenses=MIT`, Label `revision` nennt denselben Commit |
| actions/checkout (GitHub Action) | v7.0.1 | `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` | MIT | github.com/actions/checkout, Tag v7.0.1 (und v7) zeigt auf diesen Commit; LICENSE-Datei an diesem Tag gelesen („The MIT License (MIT)“) |

An der Quelle geprüft (alles im Container, nichts unter Windows installiert): Das Image existiert und lässt sich mit Tag und Digest laden. Es enthält Git (2.49.1), Einstiegspunkt ist `gitleaks`, Benutzer ist root. Befehlsform: `gitleaks dir [flags] [path]` und `gitleaks git [flags] [path]`. v8.30.1 ist laut Tag-Liste die neueste 8.30-Version. Die Pfad-Ausnahmen werden im Verzeichnis-Lauf beachtet (Kriterium 4); der Verzeichnis-Lauf meldet absolute Pfade (`/repo/...`), der Verlaufs-Lauf relative – deshalb das optionale Präfix `/repo/` in den Ausnahmen.

### Wie wurde getestet?

`T` = `docker compose -p twox-003 -f deploy/compose/compose.tools.yaml`, ausgeführt im Arbeitsverzeichnis des Auftrags.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version`: Server 29.9.3, Exit 0 · `docker compose version`: v5.7.0, Exit 0 |
| 1 | erfüllt | `T run --rm gitleaks-dir` → `scanned ~324395 bytes … no leaks found`, Exit 0 |
| 2 | erfüllt | `T run --rm gitleaks-dir version` → `v8.30.1`, Exit 0 |
| 3 | erfüllt | Datei `gegenprobe-003.txt` im Wurzelverzeichnis mit zufällig erzeugter Zeichenfolge im Format eines GitHub-Zugriffstokens (nicht eingecheckt). `T run --rm gitleaks-dir` → `RuleID: github-pat`, `File: /repo/gegenprobe-003.txt`, `Line: 1`, `Secret: REDACTED`, `leaks found: 1`, Exit 1. Datei gelöscht; `git status --short` zeigte danach nur die drei neuen, damals noch nicht eingecheckten Pfade des Auftrags |
| 4 | erfüllt | Dieselbe Datei unter `testfactory/extern/` → `no leaks found`, Exit 0. Datei und Ordner `testfactory/` gelöscht |
| 5 | erfüllt | `git grep -n 'uses:' -- .github/workflows/secrets.yml` → eine Zeile: `uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`; `gitleaks-action` kommt nicht vor (`git grep` ohne Treffer) |
| 6 | erfüllt (Durchsicht) | Workflow ruft `docker compose -f deploy/compose/compose.tools.yaml run --rm gitleaks-git` auf; der Dienst verwendet `/repo/.gitleaks.toml`, also die Datei aus dem Wurzelverzeichnis |
| 7 | offen – prüft die Leitstelle nach dem Zusammenführen | im Arbeitsverzeichnis nicht möglich (siehe unten) |
| 8 | offen – wartet auf Push-Freigabe | kein Push, kein CI-Lauf; der Workflow ist auf GitHub ungetestet |
| 9 | erfüllt | `T down -v` → Exit 0 (Hinweis „No resource found to remove“, weil `run --rm` nichts hinterlässt) |

Zusätzliche Prüfungen:

- Verlaufs-Lauf an einem Wegwerf-Repository im Container (`/tmp/r`, drei Commits: Probedatei angelegt, wieder gelöscht, dieselbe Probe unter `testfactory/extern/`): `gitleaks git` mit derselben `.gitleaks.toml` meldet genau einen Fund (die gelöschte Datei, mit Commit-Hash), Exit 1; die Datei unter `testfactory/extern/` wird nicht gemeldet. Damit sind Befehlsform, Fund im Verlauf und Pfad-Ausnahme im Verlaufs-Lauf belegt.
- `T run --rm gitleaks-git` im Arbeitsverzeichnis → `fatal: not a git repository … gitleaks-git: /repo is not a readable Git repository with commits`, Exit 2 (erwartet, `.git` ist dort nur eine Verweisdatei).
- `T config --quiet` → Exit 0.

Nicht getestet: `gitleaks-git` an einem echten eingebundenen Repository (Kriterium 7), die Wirkung von `safe.directory` auf dem eingebundenen Ordner, der Workflow auf GitHub (Kriterium 8). Im Wegwerf-Repository lief Git auch ohne passendes `safe.directory` durch; ob die Einstellung auf dem Windows-Mount oder im CI-Runner nötig ist, zeigt erst Kriterium 7 bzw. 8.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a947fc8545e8ccadc`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a947fc8545e8ccadc`

### Abweichungen

1. **Vorprüfung im Dienst `gitleaks-git` (nicht im Auftrag verlangt).** Befund: Kann Git das Repository nicht lesen, meldet gitleaks v8.30.1 `0 commits scanned … no leaks found` und endet mit Exit-Code 0. Ein kaputter Mount oder ein fehlendes `safe.directory` sähe in der CI wie ein sauberer Lauf aus. Der Dienst startet deshalb über `/bin/sh -ec`, prüft zuerst `git -C /repo rev-parse --verify --quiet HEAD` und bricht sonst mit Exit-Code 2 ab. Folge: `T run --rm gitleaks-git <Unterbefehl>` nimmt keine gitleaks-Argumente mehr an (bei `gitleaks-dir` unverändert möglich, Kriterium 2).
2. **Zusätze über den Wortlaut hinaus:** `network_mode: none`, Einbindung nur lesend, `--redact` (Funde erscheinen nicht im öffentlichen CI-Protokoll), `persist-credentials: false` beim Checkout, `timeout-minutes: 10`, Läufer `ubuntu-24.04`.
3. **`actions/checkout` v7.0.1** ist die neueste Version laut Tag-Liste (im Auftrag war die Version offen). Sie läuft mit `node24`.
4. Der Auftrag spricht vom privaten Repository; laut E-19 ist es öffentlich. Für die Dateien ändert das nichts.

### Hinweise für die Leitstelle

- Der Verzeichnis-Lauf liest alles im eingebundenen Ordner, auch von Git ignorierte Dateien wie `STARTUNTERLAGE.md` oder eine `.env` (nicht `.git`, `testfactory/extern/` und `.claude/worktrees/`). Eine `.env` mit echten Zugangsdaten führt dort also zu einem Fund. Das ist kein Fehler der Suche, aber kein Grund für eine Ausnahme ohne Entscheidung.
- Frage 1 (GitHub Secret Scanning mit Push Protection) bleibt eine Einstellung am Repository und ist Sache von a7; in diesem Auftrag nicht bearbeitet.
- Offene Fragen: keine.
