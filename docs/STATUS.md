# Status

Stand: 21.11.2026 · gepflegt von der Leitstelle

## Freigegeben

Alle Aufträge für M0 und T1 (E-21). Die Fragen in den Aufträgen sind nach Empfehlung entschieden (E-23).
Höchstens fünf Bearbeiter gleichzeitig (E-24), M0 und T1 zusammen gezählt. Eine Welle startet erst, wenn ihre Voraussetzungen nach `main` zusammengeführt sind. M0 hat Vorrang, damit früh etwas zum Ansehen da ist; T1-Aufträge füllen freie Plätze.

### M0 – Gerüst

| Nr. | Auftrag | Stufe | Welle | Hängt ab von | Status |
| --- | --- | --- | --- | --- | --- |
| 001 | Backend: Werkzeuge und Container | C | 1 | – | erledigt |
| 002 | Oberfläche als Grundgerüst | C | 1 | – | erledigt |
| 003 | Suche nach Geheimnissen | C | 1 | – | erledigt (CI grün) |
| 004 | Messung Dateizugriff | B | 2 | 001, 002 | erledigt |
| 005 | API-Grundlage | C | 3 | 001 | erledigt |
| 006 | Lizenzprüfung | C | 3 | 001, 002 | erledigt |
| 007 | Prüfung der Erreichbarkeit von Ollama | B | 3 | 001 | erledigt |
| 008 | Celery-Worker mit Valkey | C | 4 | 005 | erledigt |
| 009 | docling-serve als Container | C | 5 | 008 | erledigt |
| 010 | Testseite, Teil API | C | 5 | 005, 008 | erledigt |
| 011 | CI-Hauptworkflow | C | 5 | 002, 005, 006, 008 | erledigt (CI grün auf GitHub) |
| 012 | Testseite, Teil Oberfläche | C | 6 | 002, 010 | erledigt |
| 013 | Auslieferung der Oberfläche durch Django | C | 6 | 002, 009, 010 | erledigt |
| 014 | Playwright-Test der Testseite | C | 7 | 011, 012, 013 | erledigt |
| 015 | ARCHITECTURE.md und README | B | 8 | 006, 007, 009, 013, 014 | erledigt |

### T1 – Testfabrik Teil 1

| Nr. | Auftrag | Stufe | Welle | Hängt ab von | Status |
| --- | --- | --- | --- | --- | --- |
| 101 | Manifest-Format und Werkzeug-Container | C | 1 | – (Python-Version aus 001 eintragen) | erledigt |
| 102 | Quellen und Lizenzlage der Fertigungslinie | C | 1 | – | erledigt |
| 103 | Quellen und Nutzungsbedingungen: Standardgeräte, UR5e, URSim, OPNsense-Doku | C | 1 | – | erledigt |
| 104 | Lade-Skript `fetch.py` | B | 2 | 101 | erledigt |
| 105 | Manifest-Einträge der Fertigungslinie | C | 2 | 101, 102 | erledigt |
| 106 | Aufbau der Testfabrik: Geräteliste, Netzplan, Beschreibung | C | 2 | 101, 102 | erledigt |
| 107 | Manifest-Einträge: Standardgeräte, UR5e, URSim, OPNsense-Doku | C | 3 | 103, 105 | erledigt |
| 108 | Frei lizenzierte Testunterlagen in `testdata/klein` | C | 3 | 101, 103 | erledigt |
| 109 | Erstabruf: Unterlagen laden und Prüfsummen eintragen | B | 4 | 104, 105, 106, 107 | erledigt |
| 110 | Stände und Nutzungsvermerke nachtragen | C | 5 | 109 | erledigt |
| 111 | Prüffragen der Fertigungslinie mit Fundstelle | C | 5 | 109 | erledigt |
| 112 | Prüffragen des Roboters (Fragen 9 und 10) | C | 6 | 110, 111 | erledigt |
| 113 | Nachweis der drei Bedingungen je Anlage und Gerät | C | 6 | 106, 110 | erledigt |
| 114 | Testfabrik-Prüfungen in CI und Werkzeugkette | B | 7 | 101, 112, 113, 011 | erledigt |

## In Arbeit

- keine; alle 29 Aufträge für M0 und T1 sind erledigt.

## Wartet auf a7

Nichts davon hält die laufende Arbeit auf.

1. ~~Freigabe für den Push~~ – entschieden mit E-26: `main` wird nach jedem geprüften Zusammenführen gepusht.
2. **Durchsicht der Entscheidungen nach E-23** in `docs/DECISIONS.md`, vor allem die Lizenz-Ausnahmen (psycopg LGPL, pathspec und lightningcss MPL-2.0, pandoc GPL als Einmalwerkzeug) und das Zusammenführen von Stufe-C-Aufträgen ohne Einzelfreigabe.
3. **Lizenzlage fischertechnik (Auftrag 102, Frage 1):** Beide Repositories haben keine Lizenz, die Zentralsteuerung ist ausdrücklich „UNLICENSED". Soll a7 beim Hersteller anfragen? Den Entwurf der Anfrage liefert Auftrag 102. Bis dahin gilt: laden ja, weitergeben nein.
4. **URSim (Auftrag 103, Frage 3):** Die Nutzungsbedingungen erlauben nur eigene interne Nutzung. Anfrage bei Universal Robots vor T2? Arbeitsstand bis dahin: nur selbst erzeugte Dateien einchecken.
5. **GitHub Secret Scanning mit Push Protection** am Repository einschalten (Auftrag 003, Frage 1) – Einstellung am Konto, nimmt a7 selbst vor.
6. **Prüffragen in der CI (Auftrag 011, Frage 1):** Empfehlung: aufgezeichnete Antworten in der CI, dazu der echte Lauf lokal vor jedem Zusammenführen. Entscheidung spätestens zu M3.
7. **Startunterlage berichtigen (Auftrag 102, Frage 5):** Laut Recherche haben fünf statt vier Module eine S7-1200 (zusätzlich DPS). Die Leitstelle ändert die Startunterlage nicht ohne a7.
8. ~~Gebündelte Bibliotheken in psycopg-binary~~ – bestätigt mit E-28.
9. ~~Siemens: Klausel gegen Text- und Data-Mining~~ – entschieden mit E-27: nur lokal, von Hand geladen.
10. **Siemens: welche Ausgabe (Auftrag 103, Frage 6).** Aktuell ist V4.7 (12/2024, nur im Browser abrufbar); V4.6 (11/2022) passt vermutlich besser zu TIA Portal V18, das ist nicht bestätigt. Empfehlung und Arbeitsstand: beide führen, V4.6 maßgeblich, V4.7 als Verweis; beides ohne automatischen Abruf.

## Offene Abnahmebedingungen M0

1. ~~`check_llm` gegen das echte Ollama~~ – erfüllt am 21.11.2026: `OK:` aus dem Container über `host.docker.internal`, Ollama mit Standardbindung, keine Einstellung nötig.
2. ~~Eigenes Arbeitsverzeichnis je Auftragsbearbeiter~~ – erfüllt: Zweig und Ordner unter `.claude/worktrees/` bei jedem Start belegt.
3. ~~Messung 004~~ – entschieden mit E-34: bleiben.
4. ~~CI-Läufe grün~~ – erfüllt am 21.11.2026: Workflows `ci` (backend, web) und `secrets` grün auf GitHub.
5. ~~Sichtprüfung der Testseite~~ – von der Leitstelle am 21.11.2026 im Chrome geprüft: Datenbank und Worker grün; bei gestopptem Worker rote Karte mit Fehlermeldung; nach Neustart wieder grün. Noch durch a7 anzusehen.
6. ~~Abnahme durch a7~~ – M0 abgenommen (E-35), T1 abgenommen mit Lücke O-1 (E-36).

## Erledigt seit dem letzten Bericht

- Rechner geprüft: Git 2.55, GitHub CLI, WSL 2, Docker Desktop (Engine 29.9.3, Compose 5.7.0), Ollama 0.40.17 (noch kein Modell geladen; Modellwahl in M2/M3).
- Grundgerüst angelegt und auf `main` committet.
- Entscheidungen E-14 bis E-23 protokolliert.
- 29 Aufträge für M0 und T1 recherchiert, entworfen, von drei Prüfern gegengelesen (64 Befunde) und überarbeitet.

## Als Nächstes

- Welle 1 prüfen und zusammenführen, dann 004 (Messung) und danach 005, 006, 007.
- Freie Plätze mit T1 füllen: zuerst 102 und 103 (reine Recherche), dann 101.
- Folgeaufträge vorgemerkt: Selbsttest-Endpunkt in M1 auf angemeldete Benutzer beschränken; Zeitlimit für den Fall „Broker erreichbar, Ergebnisspeicher nicht" (Vorschläge im Kurzbericht von 010).
- Siemens-Systemhandbuch V4.6 lädt a7 bei Gelegenheit selbst (E-27): Quelle und Ablage stehen im Kurzbericht von 109; danach `fetch --record --only siemens-s7-1200-system-manual-v4-6-de`.
- Für M2 vorgemerkt (aus 009): Jede Anfrage an Docling muss `ocr_preset: "rapidocr"` mitschicken, sonst antwortet der Dienst mit 422 (E-31). Docling lädt seine Modelle erst bei der ersten Umwandlung; `healthy` heißt nur „Server läuft". `backend-dev` erreicht Docling absichtlich nicht.
- Für M1 vorgemerkt (aus 013): Mit dem Django-Admin muss `AppDirectoriesFinder` wieder in `STATICFILES_FINDERS`.
- Für die Abnahme T1 vorgemerkt (aus 113, `testfactory/layout/evidence.md`): 69 Nachweise, davon 37 erfüllt, 24 offen, 8 „folgt in T2". Zentral offen ist O-1: Keine fischertechnik-Unterlage nennt einen APS-Softwarestand, damit ist Bedingung 2 für die ganze Fertigungslinie offen. Auslegung des Bearbeiters: Bedingung 1 gilt über den Release-Stand APS 1.3.0 als erfüllt. Beides entscheidet a7 bei der Abnahme.
- Für M6 vorgemerkt (aus 015): Eine eigene `.env`-Vorlage für Tester ohne Debug und ohne Entwicklungs-Kennwörter; `.env.example` ist eine reine Entwicklungsvorlage. Der Schema-Befehl in `web/openapi/README.md` braucht unter Git Bash `MSYS_NO_PATHCONV=1`.

## M1 – Geräte und Dateien (freigegeben 21.11.2026)

23 Aufträge 016–038 in 8 Wellen unter `docs/auftraege/offen/`. Alle 33 Fragen (`docs/auftraege/M1-FRAGEN.md`) hat a7 nach Empfehlung entschieden (E-37 bis E-46); damit sind die Aufträge freigegeben. Eine Welle startet, wenn die vorige nach `main` zusammengeführt ist; höchstens fünf Bearbeiter gleichzeitig (E-24).

| Nr. | Auftrag | Stufe | Welle | Status |
| --- | --- | --- | --- | --- |
| 016 | Backend-Grundlage: Sitzungen, Admin, CSRF, Sprachen, Zwischenspeicher | C | 1 | erledigt |
| 017 | Selbsttest: Zeitlimit Ergebnisspeicher | B | 1 | erledigt |
| 018 | Oberfläche zweisprachig | C | 1 | erledigt |
| 019 | Datenmodell Standort, Bereich, Anlage, Gerät | C | 1 | erledigt |
| 020 | Anmeldung mit django-allauth, Ratenbegrenzung | C | 2 | erledigt |
| 021 | Rollen, Konto-Endpunkt, Befehl create_account | C | 2 | erledigt |
| 022 | Dateispeicher nach Prüfsumme | C | 2 | erledigt |
| 023 | Oberfläche: Routing, Rahmen, Datenabruf | C | 3 | erledigt |
| 024 | Datenmodell Dateien und Versionen | C | 3 | erledigt |
| 025 | API-Rechte: Standard nur mit Rolle | C | 3 | erledigt |
| 026 | API und Admin für die Struktur | C | 4 | erledigt |
| 027 | Testkonto in CI, Selbsttest nur für Angemeldete | C | 4 | erledigt |
| 028 | Protokoll (Backend) | C | 5 | erledigt |
| 029 | Datei-API | C | 5 | erledigt |
| 030 | Anmeldung in der Oberfläche | C | 5 | erledigt |
| 031 | CSV-Import (Backend) | C | 6 | erledigt |
| 032 | Oberfläche: Struktur und Geräte | B | 6 | erledigt |
| 033 | Oberfläche: Protokoll | B | 6 | erledigt |
| 034 | Backend-Übersetzung (gettext) | C | 7 | erledigt |
| 035 | Oberfläche: CSV-Import | B | 7 | erledigt |
| 036 | Oberfläche: Dateien | B | 7 | erledigt |
| 037 | Nachweis der M1-Abnahme | B | 8 | erledigt |
| 038 | README und ARCHITECTURE für M1 | B | 8 | erledigt |
| 039 | Landkarte als interaktive Vorschau (M1b, E-48) | C | – | erledigt |

Hinweise aus Welle 1:
- Ab 21.11.2026 startet jeder Auftrag, sobald seine eigenen Voraussetzungen auf `main` liegen, nicht erst nach der ganzen Welle.
- 016: Die Upload-Grenze „200 MB“ ist dezimal umgesetzt (200 000 000 Byte, einstellbar über `TWOX_UPLOAD_MAX_BYTES`); Entscheidung der Leitstelle, kein Widerspruch zu E-42.
- 016: Bis Auftrag 030 meldet man sich am Admin über dessen eigenes Formular an (ohne Ratenbegrenzung); 030 soll prüfen, dass `/admin/login/` danach keine Sitzung mehr ohne Ratenbegrenzung vergibt.
- 022: Temporäre Upload-Dateien (`<TWOX_MEDIA_ROOT>/tmp/upload-*.part`) bleiben nach einem harten Prozessabbruch (SIGKILL, OOM) liegen. Für 029 vorgemerkt: alte `.part`-Dateien beim Start oder regelmäßig entfernen, sonst in der Doku (038) als Grenze nennen.
- 021: Für 027 vorgemerkt: Das Testkennwort für `create_account` nur als Variablenname durchreichen (`-e TWOX_ACCOUNT_PASSWORD`), nicht als Wert in den Argumenten von `docker compose`.
- 023: Die Selbsttest-Seite liegt jetzt unter `/selftest`, `/` zeigt die Strukturseite. Für 038: `docs/ARCHITECTURE.md` nennt noch die Testseite unter `/` und „no runtime dependency" für den erzeugten Client.
- 024: Grenzen für 038: Scheitert eine Transaktion nach dem Speichern, bleibt der Inhalt ohne Version im Speicher; Unveränderlichkeit der Versionen nur über `save()`, nicht in der Datenbank; als Dokument hochgeladene Konfigurationen werden nicht erkannt (Restrisiko zu Leitplanke 5, E-42).
- 020: allauth-Pfade für Kennwort ändern, Kennwort zurücksetzen und E-Mail-Verwaltung liefern 404 (E-38). Eine Sperre nach Fehlversuchen meldet allauth mit 400 und `too_many_login_attempts`, nicht mit 429 (für 030). Hinter einem Reverse-Proxy (M6) `ALLAUTH_TRUSTED_PROXY_COUNT` setzen, sonst zählen alle Fehlversuche auf die Proxy-Adresse.
- 025: Für 027: `/api/v1/selftest/` wirklich aus `OPEN_PATHS` entfernen; der Pfadtest bemerkt einen veralteten Ausnahme-Eintrag nicht von selbst. Pfade in `OPEN_PATHS` und `ROLELESS_PATHS` werden mit allen Methoden übersprungen.
- 026: Legen zwei Anfragen gleichzeitig dieselbe Kennung bzw. denselben Namen an, endet die zweite mit 500 statt 400 (Datenbank-Constraint hält). Für 031 vorgemerkt: `save()` in den Struktur-Views in `transaction.atomic()` kapseln und `IntegrityError` je Constraint als Feldfehler (400) melden, mit Test.
- 027: Testkonto `e2e-manager` mit dem öffentlichen Entwicklungskennwort aus `.env.example`; es entsteht nur durch den Schritt „Create test account" (CI-Job e2e oder README), nie automatisch in der Testumgebung.
- 030: `/admin/login/` vergibt keine Sitzung mehr, sondern leitet auf `/login?next=/admin/…` um. Browser-Tests melden sich einmal je Worker an (storageState nur im Speicher). Offene Weiterleitung über `next` (Punkt-Segmente) in der Prüfung gefunden und behoben, auch im Admin-Redirect.
- 028: auditlog übernimmt keine Werte aus Kopfzeilen (eigene Middleware, `AUDITLOG_CID_HEADER = None`); in der Prüfung gefunden: manipulierte Kopfzeilen konnten das Schreiben des Eintrags verhindern, die Änderung blieb aber gespeichert. Für 038: `auditlogflush` nicht gesperrt; `groups.clear()` protokolliert alle Gruppen; Gruppenänderung von der Gruppenseite landet am Gruppenobjekt; gelöschter Benutzer → Akteur NULL; `actor_email` wird gespeichert (bei unseren Konten leer).
- 029: Eine eigene ASGI-Hülle (`asgi.py`) weist zu große Uploads mit 413 ab, bevor Django sie zwischenspeichert. Liegengebliebene `.part`-Dateien entfernt `python manage.py remove_stale_uploads` (nur von Hand). Für 038: Restdatei in `/tmp` des api-Containers nach hartem Abbruch möglich; fehlt ein Blob, ergibt der Download 500.
- 032: In der Prüfung gefunden und behoben: Nach einer 400-Antwort sprang die Auswahl des übergeordneten Eintrags still auf den alten Wert zurück. Für 036: `web/e2e/navigation.spec.ts` prüft den Direktaufruf über den Platzhalter `/documents/7` und muss angepasst werden. Feldfehler liest `pages/structure/save.ts` über eine eigene fetch-Hülle; brauchen 035/036 Feldfehler, ist ein Feld `body` in `ApiError` (`api/errors.ts`) die einfachere Lösung.
- 033: Protokollseite `/audit` mit Filtern (Objektart, Benutzer) und Komponente `AuditTrail` (für 036). Feldnamen erscheinen unübersetzt (z. B. `ip_address`); Filter stehen nicht in der Adresse.
- 031: CSV-Import über `POST /api/v1/imports/devices/` (Probelauf Standard, Fehler in der Datei → 200 mit Bericht und `saved: false`) und Befehl `import_devices` (verlangt Konto mit Rolle manage). Gleichzeitiges Anlegen derselben Kennung ergibt jetzt 400 statt 500. Grenze für später: keine eigene Größengrenze für die Importdatei (über die API gilt nur die Upload-Grenze von 200 MB, verarbeitet synchron im Speicher; beim Befehl unbegrenzt) – vor M6 eine kleine Importgrenze setzen. Werte mit `=`, `+`, `-`, `@` bleiben unverändert; ein späterer CSV-Export muss sie entschärfen.
- 036: Dateien je Gerät hochladen, Versionen ansehen, herunterladen. Die Dateiseite zeigt nur Protokolleinträge zu `files.document`, neue Versionen erscheinen nur unter `/audit` (für 037). `files.heading` und `files.placeholder` in `assets.json` sind ungenutzt. Hilfen aus `pages/structure/save.ts` werden auch von `components/files/` genutzt – später an einen gemeinsamen Ort ziehen. Bündel knapp unter 500 kB.
- 034: Backend-Meldungen auf Deutsch (73 Einträge, `backend/locale/de/LC_MESSAGES/django.po`, Fundstellen ohne Zeilennummern). `.mo` entsteht nur im Build (Stufe `locale-build`) und in den Tests; gettext ist nicht im Laufzeit-Image (geprüft). Unübersetzt bleiben Verwaltungsbefehle, Selbsttest-Diagnosen, OpenAPI-Texte und Djangos „No … matches the given query.“
- 039: Landkarte unter `/map` (React Flow 13.0.2, per `lazy()` geladen). Mit den Testfabrik-Daten 28 Knoten, 7 Netzkanten. Grenzen: gleiche private Netze an verschiedenen Standorten werden zu einem Netzknoten zusammengelegt; IPv4-gemappte IPv6-Adressen landen in `::/64`; Netzkanten laufen über die Gruppe „Netzübergang“. Die React-Flow-Namensnennung bleibt sichtbar. Version 13 ist sehr jung (13.0.0 vom 16.11.2026), aber mit Herkunftsnachweis und ohne Installationsskripte veröffentlicht; Rückwechsel auf 12.x wäre ein kleiner Auftrag.
- 037: Nachweis der M1-Abnahme als Browser-Test `web/e2e/m1-acceptance.spec.ts` und Backend-Test `backend/tests/acceptance/test_m1.py` (Geräteliste der Testfabrik per CSV, eine Datei mit zwei Versionen, Protokoll). Auf frischer Datenbank und im zweiten Lauf grün (20/20). Lücke für später: Die Strukturseite zeigt die Notiz einer Anlage nicht an.

**M1 ist abgenommen (E-49, 22.11.2026).**

## Gestaltung D1 (vorbereitet 22.11.2026)

Einbau der von a7 ausgewählten Design-Vorlagen, parallel zu M2. Vorlagen liegen lokal und ungetrackt unter `docs/design/bildmarke/` (in `.gitignore`); dort vorkommende Produktnamen kommen nicht ins Repository.

| Nr. | Auftrag | Stufe | Voraussetzung | Status |
| --- | --- | --- | --- | --- |
| 070 | Theme, Schrift Inter, Text-Animationen, Einstellungsseite | C | – (E-50, E-52) | in Arbeit |
| 071 | Icon-Schicht mit Lucide | C | 070 (E-51) | offen (wartet auf 070) |
| 072 | Marke: Bildmarke im Kopf, Favicon | C | 070 (E-52) | offen (wartet auf 070) |
