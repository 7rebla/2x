# Auftrag 038 – README und ARCHITECTURE auf den Stand von M1

Meilenstein: M1 · Freigabestufe: B · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
