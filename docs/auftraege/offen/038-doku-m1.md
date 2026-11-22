# Auftrag 038 – README und ARCHITECTURE auf den Stand von M1

Meilenstein: M1 · Freigabestufe: B · Status: zur Prüfung

## Ziel

`README.md` und `docs/ARCHITECTURE.md` beschreiben den Ist-Stand nach M1: Anmeldung, Rollen, Struktur, Import, Dateien, Protokoll, Sprachen.

## Umfang

- `README.md` (Englisch):
  - Status-Absatz; nicht mehr „early scaffold (milestone M0)“.
  - Schnellstart:
    - erstes Konto anlegen (`createsuperuser` bzw. `create_account` mit `TWOX_ACCOUNT_PASSWORD`, Bedeutung von `--update`);
    - anmelden;
    - Geräteliste importieren (Oberfläche und `import_devices`).
  - „Security notes“: „No login yet“ ersetzen.
    - Rollen; Sitzung und CSRF; Sitzungsdauer; Ratenbegrenzung der Anmeldung.
    - Admin nur für Superuser, über die Anmeldeseite.
    - Selbsttest nur angemeldet.
    - Dateien nur über die API, Download immer als Anhang.
    - Konfigurationsdateien noch nicht angenommen (falls so entschieden).
    - Protokoll mit seinen Grenzen (`auditlogflush`, Datenbankzugang).
    - Was für den Betrieb über HTTPS noch fehlt (M6).
  - Neue Umgebungsvariablen: `TWOX_CACHE_URL`, `TWOX_MEDIA_ROOT`, `TWOX_UPLOAD_MAX_BYTES`, `TWOX_E2E_USERNAME`, `TWOX_E2E_PASSWORD`. Das Volume `media-data` auch beim Löschen der Volumes erwähnen.
  - CSV-Format (13 Spalten) und die Regeln des Abgleichs.
- `docs/ARCHITECTURE.md` (Englisch):
  - die Apps und ihr Inhalt (`assets` mit dem CSV-Import, `files`, `accounts`; `importers` weiter leer und für Einlese-Module vorgesehen);
  - Datenmodell;
  - Speicher-Schnittstelle (inhaltsadressiert, atomar; Volume, später S3);
  - Anmeldung (allauth headless, Sitzung, Valkey-Zwischenspeicher), Rollen und Standardrecht der API;
  - Protokoll;
  - Auslieferung der Oberfläche für alle Pfade (ersetzt „Only / maps to the UI“);
  - Übersetzung (i18next, gettext; `.mo` nur im Image und in den Tests).
- `web/openapi/README.md`: Hinweis auf `MSYS_NO_PATHCONV=1` (Vormerkung aus 015), falls dort noch nicht vorhanden.
- Jede Aussage gegen den Code prüfen; Befehle wörtlich wie in `ci.yml`.

## Nicht-Ziele

- Installationsanleitung für Tester und `.env`-Vorlage ohne Debug (M6, vorgemerkt in `docs/STATUS.md`).
- Änderungen an Code, Tests, `docs/DECISIONS.md`, `docs/STATUS.md` und `docs/ROADMAP.md`.

## Betroffene Bereiche (Ordner, Dateien)

- `README.md`, `docs/ARCHITECTURE.md`, `web/openapi/README.md`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses.

1. `git diff --stat main` nennt nur die drei Dateien.
2. Jeder Befehl in den geänderten Abschnitten steht wörtlich so in `.github/workflows/ci.yml` oder ist im Kurzbericht mit Lauf und Ergebnis belegt (`docker compose -p twox-038 …`, Port 18038).
3. `grep -n \"No login yet\" README.md` findet nichts. `grep -n \"milestone M0\" README.md` findet höchstens historische Verweise, nicht den Status.
4. `grep -n \"Only / maps to the UI\" docs/ARCHITECTURE.md` findet nichts.
5. Geheimnissuche: `docker compose -f deploy/compose/compose.tools.yaml run --rm gitleaks-dir` endet mit Exit-Code 0.
6. Keine Personennamen und keine lokalen Pfade mit Benutzernamen (E-22): `git diff main | grep -n -i -F -e ':\\users' -e ':/users' -e '/home/'` findet nichts.

## Vorgaben und Hinweise

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); 027, 028, 030, 031, 034, 035 und 036 sind nach `main` zusammengeführt.

- Welle 8, parallel zu 037. Nur die drei Dateien.
- Die Aufträge 027 (Abschnitt „Browser test“) und 034 (Abschnitt „Backend“) haben in `README.md` bereits einzelne Abschnitte ergänzt. Diese übernehmen, nicht widersprechen.
- **Keine neue Abhängigkeit.**
- README und ARCHITECTURE auf Englisch (CLAUDE.md, Sprache).
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Akzeptanzkriterien erfüllt; Läufe am 22.11.2026 im Container (Docker Engine 29.9.3, Compose v5.7.0). Keine neue Abhängigkeit, kein Code geändert, keine offene Frage an a7.

### Was wurde gebaut?

- **`README.md`** (Gliederung): Status (M1 gebaut, Abnahme offen; M1b/039 als „in progress“ ohne Einzelheiten) · Requirements · Quick start (1 `.env`, 2 `up`, 3 erstes Konto mit `createsuperuser` und `create_account` samt `TWOX_ACCOUNT_PASSWORD` und `--update`, 4 Anmelden, 5 Geräteliste über `/import` und `import_devices` in `backend-dev`, 6 Selbsttest; `down -v` nennt `media-data`) · The web UI (Seiten, Rollen, Löschen nur im Admin) · Device list (CSV) (13 Spalten, Abgleichsregeln, Grenzen) · Configuration (neue Variablen) · Services and networks (+ Volumes) · Check commands · Maintenance (`remove_stale_uploads`) · Development commands (Abschnitte aus 027 und 034 übernommen; im Abschnitt „Browser test“ nur der Halbsatz „einmal je Playwright-Worker“ ergänzt) · Security notes („No login yet“ ersetzt: Netz, Anmeldung, keine Selbstbedienung, Ratenbegrenzung, Rollen, Admin, Selbsttest, Dateien, Konfigurationen, Protokoll mit Grenzen, was für HTTPS fehlt) · Licence.
- **`docs/ARCHITECTURE.md`** (Gliederung): Containers (mit `media-data`, Valkey-Datenbank 2) · Networks · Restrictions on Docling · Images (mit `locale-build`) · Repository layout · Django apps (Inhalt in M1; `importers` leer, für Einlese-Module) · Data model (Mermaid-ER-Diagramm) · File storage (Schnittstelle, inhaltsadressiert, atomar, Volume, später S3; Upload-Grenze; Downloads) · Sign-in and sessions · Roles and API permissions (Endpunkt-Tabelle) · Change log · Serving the web UI (ersetzt „Only / maps to the UI“) · Translation (i18next, gettext, `.mo` nur im Image und in den Tests) · Compose files · Path of a request: the self-test page (jetzt `/selftest`, angemeldet) · Task queues · API and the generated client („no runtime dependency“ berichtigt) · Configuration (alle Variablen) · Quality tools / CI · **Limits and known gaps**.
- **„Limits and known gaps“** enthält alle in `docs/STATUS.md` für 038 vorgemerkten Punkte: 020 (Sperre 400 statt 429, Proxy und `ALLAUTH_TRUSTED_PROXY_COUNT`, geschlossene allauth-Pfade), 021/027 (Kennwort nur als Variablenname, Testkonto nur über den Schritt), 022/029 (`.part`-Dateien, `remove_stale_uploads` nur von Hand, Restdatei in `/tmp` des api-Containers, fehlender Blob → 500), 024 (Inhalt ohne Version, Unveränderlichkeit nur über `save()`, Konfiguration als Dokument nicht erkannt), 028 (`auditlogflush` und `auditlogmigratejson` nicht gesperrt, `groups.clear()`, Gruppenseite, gelöschter Benutzer, `actor_email`, `bulk_create`/`update`), 030 (Admin-Anmeldung nur über `/login`), 031 (keine eigene Größengrenze, Formel-Zeichen, Abbruch nach Lesefehler), 033 (Feldnamen unübersetzt, Filter nicht in der Adresse), 034 (unübersetzte Texte), 036 (Protokoll der Dateiseite nur `files.document`, Bündelgröße), dazu 016 (200 MB dezimal), 017 (bis etwa 10 s), 019 (Kennungsmuster), 026 (Wettlauf jetzt 400), 032/036 (eigene fetch-Hüllen).
- **`web/openapi/README.md`:** Schema-Befehl wörtlich wie in `ci.yml` (`$PWD` statt `$(pwd)`) und die Form für Git Bash mit `MSYS_NO_PATHCONV=1`.

### Wie wurde getestet?

Compose-Projekte `twox-038` und `twox-038-web`, `.env` aus `.env.example` (ohne BOM, mit dem Write-Werkzeug) mit `TWOX_API_PORT=18038`; `.env` nie über Git Bash eingelesen. In der Doku stehen die Befehle ohne `-p twox-038`; geprüft wurden sie mit diesem Zusatz.

| Befehl aus den geänderten Abschnitten | Ergebnis |
| --- | --- |
| `cp .env.example .env`, `docker compose --profile dev build migrate api worker backend-dev`, Befehle der Abschnitte „Backend“, „Web UI“, „Browser test“, „Secret scan“ | wörtlich in `ci.yml` (bzw. unverändert); Bau zusätzlich gelaufen: Exit 0 |
| `Copy-Item .env.example .env` (in einen Ordner im Scratchpad) | Exit 0, Prüfsumme gleich der Vorlage |
| `docker compose up -d --wait` | Exit 0, alle sechs Dienste healthy (mit docling) |
| `docker compose exec api python manage.py createsuperuser` | im Container unter einem Pseudo-Terminal (Python `pty`) mit erzeugtem Kennwort: Exit 0, „Superuser created successfully.“, Kennwort in keiner Ausgabe; danach Anmeldung über allauth 200, `/api/v1/me/` mit `role: manage`, `is_superuser: true`, `/admin/` 200 |
| `docker compose exec api python manage.py create_account reader --role read` | ebenso unter Pseudo-Terminal: Exit 0, „Created account 'reader' with role 'read'.“; Anmeldung 200, `role: read`, `/admin/` 403 |
| `import_devices … --user admin` (Probelauf) | Exit 0, `rows: 14`, 1/3/10/13 created, „Dry run: nothing was saved.“ |
| `import_devices … --user admin --commit` | Exit 0, 1/3/10/13 created, „Saved.“ |
| dasselbe mit `--user reader` (Gegenprobe) | Exit 1, „does not have the role 'manage'“ |
| `docker compose exec api python manage.py remove_stale_uploads` | Exit 0, „Removed 0 stale temporary upload file(s).“ |
| `check_docling`, `check_llm` (im Abschnitt geändert: „M1“ statt „M0“) | `OK: docling-serve 1.38.2 …`, `OK: … 0 model(s) reported` |
| `MSYS_NO_PATHCONV=1 docker compose run --rm -v "$PWD/web/openapi:/out" backend-dev python manage.py spectacular --file /out/schema.yml` (Git Bash) | Exit 0, Datei neu geschrieben, `git diff --exit-code -- web/openapi` ohne Unterschied; ohne `MSYS_NO_PATHCONV` Exit 1 mit `FileNotFoundError: … 'C:/Program Files/Git/out/schema.yml'` (bestätigt die Doku) |
| `docker compose -f deploy/compose/compose.web.yaml run --rm web-dev npm run api:generate` (nach `build web-dev`, `npm ci`) | Exit 0, kein Unterschied in `web/openapi web/src/api` |
| `docker compose --profile dev --profile e2e down -v` | Exit 0; `twox-038-web` ebenso; danach kein Container und kein Volume mit `twox-038` |

Aussagen zusätzlich am laufenden Dienst geprüft (Host, Port 18038): `/`, `/login`, `/devices/1` → 200 `text/html`; `/admin/` anonym → 302 auf `/admin/login/?next=/admin/`; `/api/v1/health/` 200; `/api/v1/selftest/` und `/api/v1/me/` anonym 403; `/accounts/login/` und `/_allauth/browser/v1/auth/password/request` 404; mit `Accept-Language: de` `{"detail":"Anmeldedaten fehlen."}`. Datei-API mit Wegwerfkonto (Rolle `manage`, Kennwort im Container erzeugt): Version 1 und 2 je 201, gleicher Inhalt 409 `duplicate_version`, `kind=configuration` 400, Download einer HTML-Datei als `application/octet-stream`, `attachment`, `nosniff`, `sandbox`; zwei Protokolleinträge `files.documentversion`.

| AK | Ergebnis |
| --- | --- |
| 1 | erfüllt für die Doku-Commits: `git diff --stat main` nennt `README.md`, `docs/ARCHITECTURE.md`, `web/openapi/README.md`. Mit diesem Kurzbericht kommt die Auftragsdatei hinzu (siehe Abweichungen). |
| 2 | erfüllt, siehe Tabelle oben |
| 3 | erfüllt: beide Suchen ohne Treffer |
| 4 | erfüllt: ohne Treffer |
| 5 | erfüllt: `gitleaks-dir` „no leaks found“, Exit 0 |
| 6 | erfüllt: ohne Treffer |

### Zweig und Arbeitsverzeichnis

Zweig `worktree-agent-aa4f0135f6799b9d1`, Arbeitsverzeichnis `.claude/worktrees/agent-aa4f0135f6799b9d1`. Nicht gepusht, nicht zusammengeführt.

### Abweichungen und Hinweise

1. **AK 1 und die Auftragsdatei:** Der Kurzbericht steht wie vorgeschrieben in `docs/auftraege/offen/038-doku-m1.md`; `git diff --stat main` nennt deshalb vier Dateien. Die drei Doku-Dateien stehen in einem eigenen Commit.
2. **Interaktive Befehle:** `createsuperuser` und `create_account` ohne Variable brauchen ein Terminal. Geprüft wurde der Befehl im Container unter einem Pseudo-Terminal; den TTY-Weg von `docker compose exec` selbst konnte ich in dieser Umgebung nicht prüfen.
3. **Import auf der Befehlszeile über `backend-dev`:** Nur dieser Dienst sieht `testfactory/layout/` (Einbindung aus 031). Im `api`-Container liegt die Datei nicht; der README nennt deshalb `backend-dev` und dessen Bau mit dem CI-Befehl.
4. **Abschnitt „Browser test“:** nur ein Halbsatz ergänzt (Anmeldung einmal je Worker, Hinweis aus 030); die Befehle sind unverändert und stehen wörtlich in `ci.yml`. Den Browser-Test selbst habe ich nicht laufen lassen (keine Code-Änderung).
5. **„Limits and known gaps“** steht in `docs/ARCHITECTURE.md`; `README.md` verweist dorthin und nennt die sicherheitsrelevanten Punkte zusätzlich unter „Security notes“.
6. `docs/design/icon-bedarfsanalyse.md` ist nicht verlinkt; für M1 ohne Bezug.
