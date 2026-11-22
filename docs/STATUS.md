# Status

Stand: 22.11.2026 · gepflegt von der Leitstelle

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
3. ~~Lizenzlage fischertechnik~~ – entschieden mit E-63: keine Anfrage. Frühere Beschreibung: **Lizenzlage fischertechnik (Auftrag 102, Frage 1):** Beide Repositories haben keine Lizenz, die Zentralsteuerung ist ausdrücklich „UNLICENSED". Soll a7 beim Hersteller anfragen? Den Entwurf der Anfrage liefert Auftrag 102. Bis dahin gilt: laden ja, weitergeben nein.
4. ~~URSim~~ – entschieden mit E-63: keine Anfrage. Frühere Beschreibung: **URSim (Auftrag 103, Frage 3):** Die Nutzungsbedingungen erlauben nur eigene interne Nutzung. Anfrage bei Universal Robots vor T2? Arbeitsstand bis dahin: nur selbst erzeugte Dateien einchecken.
5. **GitHub Secret Scanning mit Push Protection** am Repository einschalten (Auftrag 003, Frage 1) – Einstellung am Konto, nimmt a7 selbst vor.
6. **Prüffragen in der CI (Auftrag 011, Frage 1):** Empfehlung: aufgezeichnete Antworten in der CI, dazu der echte Lauf lokal vor jedem Zusammenführen. Entscheidung spätestens zu M3.
7. **Startunterlage berichtigen (Auftrag 102, Frage 5):** Laut Recherche haben fünf statt vier Module eine S7-1200 (zusätzlich DPS). Die Leitstelle ändert die Startunterlage nicht ohne a7.
8. ~~Gebündelte Bibliotheken in psycopg-binary~~ – bestätigt mit E-28.
9. ~~Siemens: Klausel gegen Text- und Data-Mining~~ – entschieden mit E-27: nur lokal, von Hand geladen.
10. **Siemens: welche Ausgabe (Auftrag 103, Frage 6).** Aktuell ist V4.7 (12/2024, nur im Browser abrufbar); V4.6 (11/2022) passt vermutlich besser zu TIA Portal V18, das ist nicht bestätigt. Empfehlung und Arbeitsstand: beide führen, V4.6 maßgeblich, V4.7 als Verweis; beides ohne automatischen Abruf.
11. ~~Eigenes Feld~~ – entschieden mit E-62 (Auftrag 068). Frühere Beschreibung: **Eigenes Feld für Teilumwandlungen (Aufträge 048, 061; Stufe C, Datenmodell).** Heute wird eine Teilumwandlung am Textpräfix `converted with ` in `error_detail` erkannt. Scheitert danach das Einbetten, überschreibt die Fehlermeldung den Hinweis, und die Oberfläche zeigt die Umwandlung als vollständig. Optionen: (a) Feld `partial_errors` (Zahl) am Einlese-Auftrag, Migration, Anzeige darüber – Empfehlung; (b) so lassen, Lücke dokumentieren. Blockiert nichts.
12. ~~Messlauf 057~~ – entschieden mit E-60 (bge-m3, 2 000 Zeichen, Docling 8 GiB über 066, 2 h je Dokument).
13. ~~Client-Adresse~~ – entschieden mit E-62 (Auftrag 069). Frühere Beschreibung: **Client-Adresse im Zugriffsprotokoll (Prüfung 059; Stufe C, Anmeldung/Datenschutz).** Das Zugriffsprotokoll von uvicorn enthält bei jeder Anfrage die Client-Adresse, auch bei fehlgeschlagenen Anmeldungen; die Doku sagte bisher „nie mit IP-Adresse“ (wird mit 059 berichtigt). Optionen: (a) Client-Adresse im Zugriffsprotokoll entfernen oder kürzen (z. B. letztes Oktett), wie schon die Suchtexte – Empfehlung, passt zu „Betrieb mit möglichst wenig personenbezogenen Daten“; (b) so lassen und als Betriebsinformation dokumentieren (hilft bei der Fehlersuche und gegen Anmeldeversuche).
14. ~~Abnahmelauf 060 – Befunde zur Suchgüte~~ – entschieden mit E-61 (Auftrag 067, danach 060 wiederholen). Frühere Beschreibung: Alles andere ist erfüllt (Handbücher eingelesen, Fehler sichtbar). (1) IP-Probe: Die richtige Stelle steht auf Rang 2 – in der englischen APS-Dokumentation (gleiche Seite 38); Probe und Test zählen nur die deutsche (Rang 4). Empfehlung: beide Sprachfassungen als richtige Fundstelle werten (Probe `m2.json` und Abnahmetest ergänzen). (2) Prüffrage 9: Vektor Rang 1, zusammen Rang 12 (verlangt: unter den ersten 5). Empfehlung: Folgeauftrag „bei Fragen keine eigene exakte Liste“ (Option B aus 063), danach 060 wiederholen. Alternative: Grenze für Fragen im Abnahmetest auf 15 lockern – nicht empfohlen.
15. ~~Swap~~ – entschieden mit E-62 (Auftrag 075). Frühere Beschreibung: **Swap für Docling (Auftrag 066; Stufe C).** `mem_limit: 8g` begrenzt nur den Arbeitsspeicher; Docker erlaubt zusätzlich Swap (bis zur gleichen Menge, hier begrenzt durch 4 GiB Swap der Docker-VM). Optionen: (a) so lassen; (b) `memswap_limit` auf denselben Wert setzen, dann ist bei 8 GiB wirklich Schluss – Empfehlung (Swap verlangsamt die Umwandlung stark, die Variable soll die ganze Grenze bedeuten).
16. ~~Abnahme M2~~ – abgenommen mit E-67. Frühere Beschreibung: Wiederholung von 060 nach 067: Handbücher eingelesen, Fehler sichtbar, IP-Adresse auf Rang 2, Prüffrage 9 auf Rang 1 – das ROADMAP-Kriterium ist erfüllt. Der Abnahmetest scheitert nur noch an Prüffrage 10 in seiner eigenen Formulierung (Rang 10 statt ≤ 5; in der Formulierung der Probe Rang 1). Optionen: (a) M2 abnehmen, Prüffrage 10 als Thema für M3 (Antwort mit Quellen) vormerken und den Abnahmetest auf das ROADMAP-Kriterium (eine sinngemäße Frage) zurückführen – Empfehlung; (b) vor der Abnahme die Suche weiter verbessern (z. B. Abschnittsüberschriften stärker gewichten, Rangfolge mit einem Reranker – neue Abhängigkeit) und 060 erneut laufen lassen.

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
| 070 | Theme, Schrift Inter, Text-Animationen, Einstellungsseite | C | – (E-50, E-52) | erledigt |
| 071 | Icon-Schicht mit Lucide | C | 070 (E-51) | erledigt |
| 072 | Marke: Bildmarke im Kopf, Favicon | C | 070 (E-52) | erledigt |
| 073 | Gerätetyp als Feld, API, Admin, CSV-Spalte, Testfabrik | C | – (E-53) | erledigt |
| 074 | Eigene Geräte-Icons in Baum, Geräteseite, Landkarte | B | 071, 073 | erledigt |
| 076 | Schriftzug in der Kopfzeile tippt sich (E-64) | C (entschieden) | 070, 072 | erledigt |
| 077 | UI-Bausteine Knopf, Feld, Auswahl (UI-Analyse Prio 1) | B | 070, 071 | erledigt |
| 078 | Barrierefreiheit: Sprunglink, Seitentitel, Überschriften, Fokus | B | 077 | erledigt |
| 079 | Tabellen am Desktop lesbar | B | 077 | erledigt |
| 080 | Einheitliches Seitenraster (E-65) | C (entschieden) | 077 | erledigt |
| 081 | Tabellen auf schmalen Bildschirmen als Karten (E-65) | C (entschieden) | 079 | erledigt |
| 082 | Navigation unter 1280 px (E-65) | C (entschieden) | 080 | in Arbeit |
| 083 | Strukturbaum entrümpeln (E-65) | C (entschieden) | 077 | erledigt |
| 084 | Schriftgröße der Metadaten (E-65) | C (entschieden) | 077, 079, 083 | offen |
| 085 | Überschriften-Animation zurücknehmen (E-65) | C (entschieden) | 076 | erledigt |
| 086 | Anmeldeseite als zentrierte Karte (E-65) | C (entschieden) | 077, 080 | erledigt |
| 087 | Suchtreffer kompakter | B | 077 | erledigt |
| 088 | Einheitliche Dateiauswahl | B | 077 | erledigt |
| 089 | Ergebniszahl als Live-Region, Brotkrumen Dateiseite | B | 077, 079, 083 | in Arbeit |
| 090 | Abnahmetest M2 auf das ROADMAP-Kriterium (E-67) | C (entschieden) | 058, 067 | erledigt |
| 091 | Seite „keine Berechtigung“ mit Titel und h1 | B | 078 | erledigt |
| 092 | Wackeligen e2e-Test des Strukturbaums stabilisieren | B | 083 | in Arbeit |

- 078/079/083/085/087/088 zusammengeführt am 22.11.2026. Lücke aus 078: Die Seite „keine Berechtigung“ (RequireRole) hat weder Seitentitel noch h1 – Auftrag 091.
- Reihenfolge: 080, 081, 086 und 091 erledigt; 082, 089 und 092 laufen; zuletzt 084 (berührt fast alle Seiten).
- 080: Hinweise aus der Prüfung – der Warnkasten der Seite „keine Berechtigung“ (091) ist jetzt auf Lesebreite begrenzt (gewollt gelassen). Gesehen vom Bearbeiter: Übersichtskarte (MiniMap) bei vielen Knoten fast leer und bei 375 px groß; Einpassen großer Strukturen zeigt die Mitte – Kandidaten für einen späteren Auftrag.
- 081: Kartenansicht unter 768 px (E-65). Zwischen 768 und etwa 900 px scrollen Protokoll, Einlesen und Dateien noch im eigenen Kasten (Seite scrollt nicht); Grenze ließe sich mit `WIDE_TABLE_QUERY` auf 1024 px setzen – a7 gefragt, bis dahin 768 px.
- 086: Name über der Karte steht still und ist für Screenreader verborgen (nur der Kopf tippt, E-64); `BrandMark` hat dafür `link={false}`.

## M2 – Einlesen und Suche (freigegeben 22.11.2026, E-54; abgenommen 22.11.2026, E-67)

21 Aufträge 040–060 unter `docs/auftraege/offen/` (Startreihenfolge nach Abhängigkeiten, höchstens fünf gleichzeitig). 21 Fragen an a7 mit Optionen und Empfehlung: `docs/auftraege/M2-FRAGEN.md`. 057 und 060 sind Läufe der Leitstelle in der Testumgebung (dort liegen die Handbücher). Kein M2-Auftrag startet vor der Antwort (Stufe C: Datenmodell, neue Abhängigkeit pgvector, Modellwahl).

| Nr. | Auftrag | Stufe | Hängt ab von | Status |
| --- | --- | --- | --- | --- |
| 040 | Datenbank: Erweiterungen vector und pg_trgm, Paket pgvector | C | – | erledigt |
| 041 | Docling-Anbindung: Client, Probelauf, Testdaten | C | – | erledigt |
| 042 | Datenmodell: Einlese-Auftrag und Abschnitt | C | 040 | erledigt |
| 043 | Abschnitte aus dem Docling-Ergebnis bilden | C | 041 | erledigt |
| 044 | Einbettungen über Ollama: Client und Prüfung | C | 040, 041 | erledigt |
| 045 | Celery und Einlese-Einstellungen | C | 044 | erledigt |
| 046 | Einlese-Ablauf im Worker | B | 042, 043, 045 | erledigt |
| 047 | Such-Schnittstelle und Stichwortsuche | C | 042 | erledigt |
| 048 | Einbettungs-Aufgabe im Worker | B | 046 | erledigt |
| 049 | Einlesen anstoßen, Formatprüfung, Befehl | C | 046 | erledigt |
| 050 | Vektorsuche und Kombination | B | 044, 047 | erledigt |
| 051 | Einlese-API | C | 049 | erledigt |
| 052 | Such-API | C | 050, 051 | erledigt |
| 053 | Oberfläche: Einlese-Status | B | 051 | erledigt |
| 054 | Oberfläche: Suchseite | B | 052 | erledigt |
| 055 | Oberfläche: Einlese-Übersicht | B | 051, 053, 054 | erledigt |
| 056 | Suchprobe: Befehl evaluate_search | B | 050 | erledigt |
| 057 | Messlauf in der Testumgebung (Leitstelle) | C | 048, 049, 050, 056 | erledigt |
| 058 | Abnahmetests M2 | B | 052–055 | erledigt |
| 059 | README und ARCHITECTURE für M2 | B | 055, 056, 058 | erledigt |
| 060 | Abnahmelauf M2 (Leitstelle) | C | 057, 058, 059 | erledigt |
| 061 | Einbettungsaufträge im Feld `ingest` | B | 048, 051 | erledigt |
| 062 | Seiten bei Bedarf nachladen (Bündelgröße) | B | 054, 055 | erledigt |
| 063 | Gewichtung exakter Treffer in der kombinierten Suche | B | 052 | erledigt |
| 064 | Filter „nur neuester Auftrag je Version“ | B | 055 | erledigt |
| 065 | Frist, wenn Docling eine Aufgabe nie startet | B | 048, 049 | erledigt |
| 066 | Speichergrenze für Docling (E-60) | C (entschieden) | E-60 | erledigt |
| 067 | Sprachfassungen in der Abnahme, keine exakte Liste bei Fragen (E-61) | C (entschieden) | E-61 | erledigt |
| 068 | Eigenes Feld für Teilumwandlungen (E-62) | C (entschieden) | E-62 | erledigt |
| 069 | Zugriffsprotokoll ohne Client-Adresse (E-62) | C (entschieden) | E-62 | erledigt |
| 075 | Swap-Grenze für Docling (E-62) | C (entschieden) | E-62 | erledigt |
- 073: Feld `device_class` (plc, controller, computer, router, firewall, robot, other) in Modell, API, Admin, Protokoll und Formular; CSV mit optionaler 14. Spalte; Testfabrik: 5 SPS, 4 Controller, je 1 Rechner, Router, Roboter, Firewall. Die Geräteseite zeigt den Typ noch nur im Bearbeiten-Formular (für 074).
- 040: Erweiterungen `vector` und `pg_trgm` per Migration `ingest.0001_extensions`. Für M6 (Betrieb ohne Superuser): `vector` ist nicht „trusted“ – ein Administrator legt die Erweiterung vor der ersten Migration an; die Rückwärtsmigration entfernt sie und braucht dann ebenfalls einen Superuser.
- Für M3 vorgemerkt (22.11.2026): Chat-Assistent als animierte Pixelfigur ist von a7 ausgewählt (Vorlage lokal und ungetrackt unter `docs/design/bildmarke/assistent/`). Einbau als eigener M3-Auftrag nach Freigabe; erscheint nur bei eingeschalteten KI-Funktionen (E-59). Der Name der Figur kommt wie der Produktname nicht in getrackte Dateien, bis a7 beide veröffentlicht; vorher Registerprüfung.
- 070: Theme mit Tokens, hell/dunkel/System, fünf Akzente (Aubergine Standard; Indigo, Beere, Umbra, Graphit als Vorschlag des Bearbeiters), Kontraste per Test aus `index.css` gemessen, Inter lokal, vier Text-Animationen, Seite `/settings` (Benutzermenü). Für M6: CSP-Hash des Inline-Skripts in `web/src/theme/README.md`. Beim lokalen Bauen vorher `web/dist/` löschen (Tailwind durchsucht es sonst).
- 041: Docling-Client (`ingest/docling.py`) mit Streaming und vier Fehlerarten, `check_docling --convert`, Fixtures aus freien Testdaten. Gemessen ~5 s je PDF-Seite auf der CPU (60 Seiten in ~5 min). Für 057: 2 000 Seiten × 5 s ≈ 2,8 h überschreiten die Grenze von 2 h je Dokument (E-55) – Grenze nach dem Messlauf neu vorschlagen. Docling liefert ein abgeholtes Ergebnis noch ~300 s lang erneut aus; RapidOCR erscheint nicht im Docling-Protokoll (Nachweis über geladene ONNX-Bibliothek).
- 042: Modelle `IngestJob` (je Versuch eine Zeile, höchstens ein aktiver Auftrag je Version) und `Section` (Suchvektor als generierte Spalte über `heading_text` und `text`, simple/german/english; Einbettung `vector(1024)` nullbar; GIN-, Trigramm- und HNSW-Index). Für 043: leere Abschnittstexte werden abgewiesen. Für 047: Phrasensuche über die Grenzen der verketteten tsvector-Kopien prüfen.
- 072: Bildmarke im Kopf neben „2x“ (Komponente `BrandMark`, Token `brand` getrennt vom Akzent), Favicon SVG/ICO und Touch-Icon; Backend liefert `/favicon.ico`, `/favicon.svg`, `/apple-touch-icon.png` über feste Pfade. `favicon.svg` danach aus der korrigierten Vorlage neu übernommen (wechselt jetzt im Dunkelmodus auf #B496B8).
- 043: Abschnitte aus dem Docling-JSON (`ingest/sections.py`), Seiten nie zu eng, Tabellen wortgetreu. Hinweise: aufeinanderfolgende Überschriften ohne Text verschiedener Ebenen landen in umgekehrter Reihenfolge im nächsten Abschnitt; jede Schemaversion 1.x.y wird angenommen (geprüft nur 1.10.0).
- 044: Einbettungs-Client (`answers/embeddings.py`), Schalter `TWOX_AI_ENABLED` (Standard aus, `.env.example` an), `check_llm --embed` mit neutralem `DISABLED:`; Cloud-Modelle werden am Namen und über `/api/tags` abgewiesen, `/api/show` wird nie aufgerufen. Offen (E-59): Selbsttest und Testseite zeigen noch keinen KI-Zustand – für 048 vorgemerkt. Doku zu `--embed` und den neuen Variablen in 059.
- 071: Lucide-Icons über `web/src/icons/` (Pflichtfeld `icon` in `navigation.ts`), einzeilige Kopfzeile, Benutzermenü mit Sprache, Einstellungen, Abmelden. Für 054/055: neue Navigationseinträge brauchen ein eigenes Icon in `names.ts` und Anpassungen in `web/e2e/navigation.spec.ts`.
- 047: Such-Schnittstelle `search/interface.py` mit Stichwortsuche in PostgreSQL (`postgres.py`, drei Sprachkonfigurationen, exakte Kennungen mit Wortgrenzen, höchstens 10, neueste eingelesene Version, gleiche Inhalte zusammengefasst). Beim Zusammenführen korrigiert: Phrasen-Nachprüfung mit Lücke zwischen Überschrift und Text; IPv4/IPv6 nur mit ASCII-Ziffern. An 052 übergeben: Dateiname der Version in `HitLocation`, Ausschlüsse auch für exakte Treffer.
- 045: Celery-Routen (convert/poll → ingest, embed → embed; `embed` nur bei eingeschalteter KI, sonst `QueueNotFound`), Worker ohne `--queues`, `--concurrency 4`, Prefetch 1, globale Zeitlimits 300/360 s, weiches Herunterfahren 60 s über `REMAP_SIGTERM=SIGQUIT` und `stop_grace_period: 90s`, sieben Einlese-Variablen, Startprüfung `check_ingest_timing`. Nur Aufgaben mit `acks_late` kommen beim Herunterfahren zurück in die Warteschlange. Die Docling-Grenze von 2 h steht an drei Stellen und ist nur nach unten einstellbar – nach 057 eine gemeinsame Variable vorschlagen. Socket-Zeitlimit gegen weiche Grenze: in 048 vorgemerkt.
- 050: Vektorsuche über `embed_query` (nur bei eingeschalteter KI, sonst kein Aufruf), 50 nächste Abschnitte mit HNSW-Einstellungen `relaxed_order`/`ef_search 100` transaktionslokal, RRF k = 60 (exakte Treffer bleiben vorne), Rückfall auf Stichwortsuche bei Modellausfall. Beim Zusammenführen korrigiert: Nachsortierung über `distance + 0` (PostgreSQL 18). Bei 10 000 Abschnitten nutzt der Planer HNSW nicht; Trefferquote misst 057. An 052/054 übergeben: Ausschlüsse auch für die Vektorliste, „KI nicht aktiviert“ getrennt von „nicht erreichbar“, eigene kurze Zeitgrenze für Suchanfragen.
- 056: Befehl `evaluate_search` (Stichwort, Vektor, zusammen; Rang der ersten richtigen Fundstelle, Recall/10, MRR, Zeit) mit Probenliste `search/probes/m2.json` (7 Proben, nur Verweise auf Manifest, Prüfsummen und Seiten). Recall zählt Proben mit mindestens einer richtigen Fundstelle unter den ersten k. Nicht eingelesene Proben werden genannt, nicht gesucht. `override_settings` im Befehl wird mit 052 durch einen Schalter ersetzt.
- 046: Einlese-Ablauf `ingest/pipeline.py` und Aufgaben `convert`/`poll` (acks_late, reject_on_worker_lost): Übernahme nur aus `queued`, Wiederverwendung gespeicherter Docling-Antworten über SHA-256 (nur aus `done`), Wiederholungen 10/20/40/60/60 s, Frist ab erstem `started`, Abschnitte am Ende in einer Transaktion. Gemessen: BetrSichV (60 Seiten) 292 s, davon Docling 258 s. `partial_success` endet `done` mit Hinweis in `error_detail` (für 051/053). An 048 übergeben: Neuzustellungen begrenzen, Teilergebnisse nicht wiederverwenden. Hängende Aufträge nach hartem Abbruch: `--stuck` aus 049.
- 049: Einlesen startet nach dem Upload (`transaction.on_commit`, nur Art „Dokument“), Formatprüfung nach Endung und Inhalt (`ingest/formats.py`), Senden mit `ignore_result` (Upload hängt nicht, wenn Valkey fehlt; Auftrag bleibt `queued`), Befehl `ingest_versions` (`--missing`/`--all`/`--failed`/`--stuck`, Probelauf als Vorgabe, `--commit --user`). Kriterium 6 hat die Leitstelle in der Testumgebung über die Oberfläche nachgeholt: BetrSichV an „SPS Bohrstation“ hochgeladen, ohne weiteren Befehl `done`, 60 Seiten, 140 Abschnitte, 292 s. Restrisiko Leitplanke 5: Konfigurationen als `.md` oder PDF würden eingelesen (Doku in 059).
- 048: Schritt `embed` (Stapel 16, Zeitbudget gegen Socket-Grenze, Übernahme bei gleichem Inhalt, Überschriften und Modell), Befehl `embed_sections` (`--missing`/`--all`), Systemprüfung E001 (KI an) / W001 (KI aus), Selbsttest-Teil `ai` mit neutraler Karte bei „aus“. Gemessen: 140 Abschnitte in 2,8 s (Modell geladen), erster Lauf 7,3 s. Neuzustellungen zählen als Versuch; Teilergebnisse werden nicht übernommen. Offen für a7 (nicht blockierend): eigener Feldwert statt Textpräfix für Teilergebnisse wäre robuster (Stufe C, Datenmodell).
- 051: `GET /api/v1/ingest-jobs/` (read; Filter status/device/document/version, 50 je Seite), `POST /api/v1/document-versions/{id}/ingest/` (manage; 202, 409 `ingest_active`, 400 `configuration_not_ingested`), Feld `ingest` an jeder Version (eine Zusatzabfrage per `DISTINCT ON`), `requested_by` nur für manage (E-57), zusätzlich `partly_converted`. Schema-Enum `StatusEnum` heißt jetzt `HealthStatusEnum`. Folgeauftrag 061: Einbettungsaufträge aus `embed_sections` als neuester Auftrag verfälschen Seitenzahl und Hinweis.
- 061: Einbettungsaufträge aus `embed_sections` übernehmen Seitenzahl und Teilumwandlungs-Hinweis der neuesten fertigen Umwandlung (auch `failed` im Schritt `embed`). `PARTIAL_DETAIL_PREFIX` steht nur noch in `ingest/models.py`. Grenze: Scheitert das Einbetten, überschreibt `_fail` den Hinweis – nur mit eigenem Feld lösbar (siehe „Wartet auf a7“).
- 053: Spalte „Einlesen“ auf der Dateiseite und Abzeichen auf der Geräteseite (In Warteschlange, Wird eingelesen: Schritt, Eingelesen mit Seiten und Abschnitten, Fehler mit Meldung je Fehlerart, Übersprungen, Nicht eingelesen), Abfrage alle 5 s nur bei laufendem Auftrag, „Erneut einlesen“ nur für Verwalter. Hinweis: Statuswechsel werden Screenreadern nicht angesagt (für 058/059 vormerken). Bündelwarnung bestand schon vorher → 062.
- 052: `GET /api/v1/search/` (read; q bis 500, device/plant je bis 100, limit bis 50), Antwort `semantic` used/disabled/unavailable, Treffer mit Ausschnitt, Markierungen in Codepoints und Fundorten (mit Dateiname der Version). Ausschlüsse (`-Wort`) wirken auf alle drei Zweige, in der Vektorsuche vor dem LIMIT. Logfilter: Suchtexte stehen nicht im Zugriffsprotokoll. Eigene Zeitgrenze `TWOX_SEARCH_EMBED_TIMEOUT_SECONDS` (20 s), Modellprüfung 300 s je Prozess zwischengespeichert. Kriterium 8 (Browser) holt die Leitstelle nach 054 nach.
- 054: Suchseite `/search` (Navigationseintrag „Suche“, Rolle read), Suchtext und Gerät in der Adresse, Treffer als Karten mit Seite, Überschriftenpfad, Marken (Exakt, Stichwort, Bedeutung), markiertem Ausschnitt und Fundorten; bei KI aus eine ruhige Zeile, Hinweis nur bei „nicht erreichbar“. Seite wird nachgeladen. Kriterium 4 von der Leitstelle in „2x“ geprüft. Kopfzeile: nur 11 px Reserve bei sechs Einträgen (Lösung in 055). Wackeliger Vitest in `session.test.tsx` → 062.
- 063: Exakte Treffer stehen nur noch bei Anfragen absolut vorne, die im Wesentlichen aus Kennungen bestehen (Kennung plus höchstens ein Wort) oder wenn es keine Vektorliste gibt; sonst sind sie eine dritte RRF-Liste (mittlerer Platz bei Gleichstand, Gleichstand geht an die Bedeutung). Nachmessung der Leitstelle mit allen Handbüchern: question-9 27 → 12, question-10 27 → 3, kombiniert Recall@5 0,286 → 0,429, MRR 0,095 → 0,144. Option „keine exakte Liste bei Fragen“ für eine spätere Messung mit mehr Proben vorgemerkt.
- 055: Seite `/ingest` (Navigationseintrag „Einlesen“, eigenes Icon) mit Filtern Status und Gerät in der Adresse (Vorgabe „Offen“), Tabelle mit Gerät, Datei, Status, Zeitpunkten, „Angestoßen von“ nur für Verwalter, Blättern zu 50, Abfrage alle 5 s bei laufenden Aufträgen. Kopfzeile: unter 1280 px nur Icons (Text `sr-only`, Tooltip), ab 1280 px breiterer Kopf. Folgeauftrag 064: gescheiterte ältere Versuche blieben unter „Offen“ stehen.
- 058: Abnahmetests M2: `backend/tests/acceptance/test_m2.py` (Einlesen, Kennung und IP wörtlich, sinngemäße Frage, Fehler sichtbar, Rechte, je KI an und aus, Docling-Attrappe) und `web/e2e/m2-acceptance.spec.ts` (CI-Teil mit `page.route`; lokaler Teil mit `TWOX_M2_LOCAL=1`, `TWOX_M2_REQUIRED`, `TWOX_M2_FAILED_FILE` für 060). Risiko für 060: Prüffrage 9 muss unter die ersten fünf (Nachmessung 063: Rang 12).
- 062: Alle Seiten außer Anmeldung und Struktur werden nachgeladen, Ladezustand nach 300 ms, „Neu laden“ bei Ladefehlern. Startlast −49 kB (gzip −11 kB), keine Größenwarnung mehr. Wettlauf beim Abmelden behoben (`flushSync`), mit Regressionstest.
- 064: `GET /api/v1/ingest-jobs/` mit Filter `latest` und Feld `is_latest` (gleiche Regel wie Feld `ingest`, keine Zusatzabfrage); `/ingest` zeigt standardmäßig nur den neuesten Auftrag je Version, Schalter „Auch ältere Versuche zeigen“ (`?older=1`).
- 059: README, ARCHITECTURE und Seiten-README für M2 (Einlesen, Suche, Befehle, Variablen, Warteschlangen, Logging, Messwerte aus 057, Abnahme von Hand aus 058). Offene Stufe-C-Punkte als „Vorgabe bis zur Entscheidung durch a7“. Beim Prüfen gefunden: Zugriffsprotokoll enthält die Client-Adresse (Doku berichtigt, Frage 13 an a7); Aufträge ohne Docling-Start haben keine Frist → 065.
- 065: Bleibt eine Docling-Aufgabe `pending`, endet der Einlese-Auftrag nach `TWOX_DOCLING_QUEUE_TIMEOUT_SECONDS` (neu, Vorgabe 24 h, ab `started_at`) mit `timeout`; Startprüfung verlangt QUEUE ≥ INGEST. Die abgelaufene Docling-Aufgabe wird nicht abgebrochen (Doku). `--stuck`-Hilfe an 048 angepasst.
- 066: Docling mit `mem_limit: ${TWOX_DOCLING_MEM_LIMIT:-8g}` (E-60). Versuch mit 1 GiB: Container wird bei Speichermangel beendet und von Docker neu gestartet, der Auftrag endet nach fünf Versuchen mit `docling_unavailable`; der Grund (Speicher) steht nicht im Auftrag, nur in `docker events`. Wartende Aufgaben in Docling gehen dabei verloren. Swap-Frage an a7 (Punkt 15).
- 067: Beide Sprachfassungen der APS-Dokumentation zählen in Probe und Abnahmetest; bei Fragen in Satzform keine eigene Liste für exakte Treffer mehr (E-61). Nachmessung mit den Handbüchern: question-9 12 → 1, ip-ccu 4 → 2, kombiniert Recall@5 0,571, Recall@10 0,857, MRR 0,535. Bekannt: `test_m2` (ai-on) wackelt gelegentlich, wenn Such- und Abnahmetests zusammen laufen (HNSW mit gleich weit entfernten Testvektoren).
- 075: Docling `memswap_limit` gleich `mem_limit` (E-62): die 8-GiB-Grenze schließt Swap ein; `docker inspect` zeigt Memory = MemorySwap.
- 069: Zugriffsprotokoll ohne Client-Adresse (Filter `DropClientAddress`, Format ohne `client_addr`); weitere Stellen geprüft, keine protokolliert Adressen (E-62 b).
- 076: Schriftzug tippt sich einmal je Sitzung (Anmeldeseite und erstes Öffnen nach der Anmeldung), Muster E in `TextMotion.tsx`, Name nur einmal im DOM; Rückfall auf Codepunkte ohne `Intl.Segmenter` (Leitstelle). Randfall: nach Abmelden und Neuladen kann der Name kurz stehen und dann tippen.
- 077: UI-Bausteine `Button`, `Input`, `Select`, `Textarea` unter `web/src/components/ui/` (md 36 px, sm 28 px), alle Seiten umgestellt, Quelltextprüfung `sourceControls.test.ts`.
- 090: Lokaler Abnahmetest M2 prüft das ROADMAP-Kriterium (IP, Prüffrage 9); Prüffrage 10 nur noch als Rang gemeldet (E-67).
- 068: Feld `conversion_error_count` am Einlese-Auftrag (Migration `ingest.0003`, übernimmt alte Hinweise; Teilumwandlung mindestens 1), `partly_converted` und Wiederverwendung richten sich nach dem Feld, `embed_sections` übernimmt es; `PARTIAL_DETAIL_PREFIX` entfällt. Anzeige nach gescheitertem Einbetten → 089.
- Hinweis Prüfumgebung: Der Landkarten-Browsertest kann scheitern, wenn sich in einer Umgebung viele Testgeräte aus früheren Läufen angesammelt haben (Einpassen auf viele Treffer); in frischer Umgebung grün. Kandidat für einen Test-Folgeauftrag.
- 074: Acht eigene Icons (Anlage, Gerät, sechs Gerätetypen) unter `web/src/icons/industrial/`, Zuordnung nur in `deviceClass.ts` (Rückfall: generisches Gerät). Typ als Text im Baum, als Feld „Gerätetyp“ auf der Geräteseite, als Tooltip auf der Karte. Notwendig mitgeändert: `graph.ts`, `MapPage.tsx`, `map.json`. Nicht von Hand bei 16 px gesichtet.
