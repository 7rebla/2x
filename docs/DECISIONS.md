# Entscheidungsprotokoll

Architekturentscheidungen trifft a7. Dieses Protokoll hält sie mit Begründung fest.
Zeichen: ✔ von a7 bestätigt · ◻ Vorschlag, noch zu bestätigen.
Quelle der Einträge E-01 bis E-13: `STARTUNTERLAGE.md`, Entwurf 2 vom 21.11.2026.

## Entscheidungen

| Nr. | Entscheidung | Stand | Datum |
| --- | --- | --- | --- |
| E-01 | Zielnutzer: OT-/IT-Verantwortlicher im kleinen Fertigungsbetrieb | ✔ | 21.11.2026 |
| E-02 | Umfang Stufe 1 und Nicht-Ziele (Startunterlage Abschnitt 4) | ✔ | 21.11.2026 |
| E-03 | Technik: Python, Django, PostgreSQL, Celery, React (Abschnitt 5). Ersetzt den .NET-Vorschlag | ✔ (siehe E-21) | 21.11.2026 |
| E-04 | Sprachmodell lokal als Standard, austauschbar; „weiß ich nicht" ist erlaubt | ✔ | 21.11.2026 |
| E-05 | Sicherheit ab Tag 1 (Leitplanken 2–6, Anmeldung und Rollen) | ✔ | 21.11.2026 |
| E-06 | Testfabrik nur aus echten Anlagen mit passender Doku | Grundsatz ✔ · Auswahl (Abschnitt 10.2) ✔ (siehe E-21) | 21.11.2026 |
| E-07 | Sprache: Code und README Englisch, Oberfläche Deutsch und Englisch | ✔ | 21.11.2026 |
| E-08 | Lizenz Apache-2.0; Entscheidungsprotokoll im Repository | ✔ | 21.11.2026 |
| E-09 | Arbeitsname „2x"; technischer Bezeichner `twox` | Name ✔ · Bezeichner ✔ (siehe E-21) | 21.11.2026 |
| E-10 | Qualität: Prüffragen laufen bei jeder Änderung automatisch mit | ✔ | 21.11.2026 |
| E-11 | Arbeitsweise: Leitstelle plus Auftragsbearbeiter, Betrieb ohne a7 am Rechner (Abschnitt 8) | ✔ · Freigabestufen (8.2) ✔ (siehe E-21, geändert durch E-14) | 21.11.2026 |
| E-12 | Spätere Stufen sind als Meilensteine 7–11 eingeplant (Reihenfolge untereinander offen) | ✔ | 21.11.2026 |
| E-13 | Technik wird nach Marktlage gewählt, nicht nach den Vorkenntnissen von a7 | ✔ | 21.11.2026 |
| E-14 | Nur der Push nach GitHub braucht die Freigabe von a7. Commits und das Zusammenführen nach `main` erledigt die Leitstelle selbst | ✔ | 21.11.2026 |
| E-15 | Die Leitstelle läuft in der Claude-Desktop-App (statt Terminal-Sitzung mit `--remote-control`) | ✔ | 21.11.2026 |
| E-16 | `CLAUDE.md` ist auf Deutsch verfasst | ✔ | 21.11.2026 |
| E-17 | Das GitHub-Repository wird vor dem ersten Push angelegt (erledigt, siehe E-19) | ✔ | 21.11.2026 |
| E-18 | entfällt | – | – |
| E-19 | Das GitHub-Repository `7rebla/2x` ist von Anfang an öffentlich. Weicht von Abschnitt 12 der Startunterlage ab (dort: privat, öffentlich ab Version 0.1) | ✔ | 21.11.2026 |
| E-20 | `STARTUNTERLAGE.md` kommt nicht ins Repository. Sie bleibt lokal (`.gitignore`) und wird über `.worktreeinclude` in Arbeitsverzeichnisse kopiert | ✔ | 21.11.2026 |
| E-21 | Die Leitstelle beginnt selbstständig mit dem Bauen, sobald sie kann; die bisher mit ◻ markierten Punkte gelten als bestätigt | ✔ | 21.11.2026 |
| E-22 | In Repository-Dateien heißt der Projektinhaber „a7"; Personennamen stehen nicht im Repository | ✔ | 21.11.2026 |
| E-23 | Die Fragen in den Aufträgen für M0 und T1 entscheidet die Leitstelle gemäß der jeweiligen Empfehlung; a7 kann jede Entscheidung nachträglich ändern | ✔ (aus E-14 und E-21 abgeleitet) | 21.11.2026 |
| E-24 | Höchstens fünf Aufträge gleichzeitig statt drei (ändert Abschnitt 8.5). Einzelne Aufträge dürfen als eigene Sitzungen laufen, damit a7 hineinsehen kann | ✔ | 21.11.2026 |
| E-25 | BlueOak-1.0.0, CC-BY-3.0, CC-BY-4.0 und CC0-1.0 sind bei reinen Entwicklungs- und Build-Paketen zugelassen (nicht im ausgelieferten Code). Anlass: mitgezogene Pakete in Auftrag 002 | ✔ | 21.11.2026 |
| E-26 | Die Leitstelle pusht `main` nach jedem geprüften Zusammenführen ohne Einzelrückfrage; vorher laufen Geheimnissuche und Namensprüfung über den Verlauf. Auftragszweige werden weiterhin nicht gepusht (ergänzt E-14) | ✔ | 21.11.2026 |
| E-27 | Siemens-Unterlagen (S7-1200-Systemhandbuch) werden nur von a7 selbst im Browser geladen (Lade-Art `manual`) und nur lokal eingelesen; nichts davon wird veröffentlicht, kein automatischer Abruf von Siemens-Adressen. Das Restrisiko der Klausel gegen Text- und Data-Mining (Siemens-Nutzungsbedingungen A.6.2) wird in Kauf genommen und im Manifest vermerkt. Maßgeblich V4.6 (11/2022), V4.7 (12/2024) als Verweis | ✔ | 21.11.2026 |
| E-28 | Die in psycopg-binary gebündelten Bibliotheken – darunter keyutils (LGPL-2.0-or-later) und libxcrypt (LGPL-2.1-or-later), dazu OLDAP-2.8 und BSD-Varianten mit Nennungsklausel – gehören zur benannten Ausnahme psycopg (unverändert eingebunden, Leitplanke 7) | ✔ | 21.11.2026 |
| E-29 | Hintergrundarbeit läuft über Celery (Startunterlage 5.2); Djangos eingebautes Tasks-Framework wird nicht verwendet. Valkey wird über Celerys Redis-Transport angesprochen (Adressen mit `redis://`, Client redis-py), weil Celery kein `valkey://` kennt. Nur JSON-Serialisierung, kein pickle | ✔ (nach E-23) | 21.11.2026 |
| E-30 | Das Tabellen-Modell TableFormer (docling-models) unter CDLA-Permissive-2.0 ist als benannte Ausnahme für das unveränderte Docling-Image zugelassen | ✔ | 21.11.2026 |
| E-31 | Die EasyOCR-Gewichte im Docling-Image (Lizenz nicht feststellbar) werden hingenommen, aber nie benutzt: Das Backend fordert nie `ocr_engine: easyocr` an, nur RapidOCR (Apache-2.0). Bestätigt von a7 auch nach dem Befund, dass die Nutzungsbedingungen von jaided.ai die kostenlose Version auf nicht-kommerzielle Nutzung beschränken (ob das die Gewichte betrifft, ist unklar): 2x gibt das Image nicht weiter und nutzt die Gewichte nie; Restrisiko bekannt | ✔ | 21.11.2026 |
| E-32 | Docling darf nicht ins Internet: `ORT_DISABLE_TELEMETRY=1` (dokumentiert in den Release Notes von ONNX Runtime 1.29.0) (ONNX Runtime baute sonst eine Verbindung zu Microsoft-Telemetrieadressen auf) UND ein internes Docker-Netz ohne Internetzugang für docling, an das nur api und worker angebunden sind | ✔ | 21.11.2026 |
| E-33 | Prüffrage 10 („Wie wird der UR5e nach einem Schutzstopp wieder freigegeben?") meint den Halt durch eine Schutzeinrichtung (SF2, Safeguard Stop), nicht den vom Roboter selbst ausgelösten Halt (Robot Stop) | ✔ | 21.11.2026 |
| E-34 | Das Projekt bleibt im Windows-Ordner (Messung aus Auftrag 004: Entwicklerbefehle nur 1,0- bis 1,5-mal langsamer als im Docker-Volume). Regel: Abhängigkeiten, Build-Ergebnisse und Zwischenspeicher nie in den eingebundenen Quelltext; neu messen, wenn der Quelltext stark wächst | ✔ | 21.11.2026 |
| E-35 | Meilenstein M0 ist abgenommen | ✔ | 21.11.2026 |
| E-36 | Meilenstein T1 ist abgenommen, mit der benannten Lücke O-1 (keine fischertechnik-Unterlage nennt einen Softwarestand der Anlage; Bedingung 2 für die Fertigungslinie offen, siehe `testfactory/layout/evidence.md`) | ✔ | 21.11.2026 |
| E-37 | Alle 33 Fragen zu M1 (`docs/auftraege/M1-FRAGEN.md`, F-1 bis F-33) sind nach der Empfehlung entschieden; die M1-Aufträge 016–038 sind freigegeben. Die wichtigsten Punkte stehen einzeln in E-38 bis E-46 | ✔ | 21.11.2026 |
| E-38 | Anmeldung: django-allauth headless, Browser-Client mit Django-Sitzung (Cookie, CSRF) am selben Ursprung, kein Token im Browser; eigene Anmeldeseite in der Oberfläche; Sitzung 8 Stunden; Kennwort mindestens 12 Zeichen; Fehlversuche nach allauth-Standard, ausdrücklich gesetzt und in Valkey gezählt. Keine Selbstregistrierung, kein Zurücksetzen per E-Mail, keine eigene Kennwortänderung in M1 (vorgemerkt für M6). OIDC und Zwei-Faktor erst nach M1 (F-1, F-4, F-5, F-9, F-11, F-12, F-14, F-30) | ✔ | 21.11.2026 |
| E-39 | Django-Admin unter `/admin/` nur für Superuser; ab Auftrag 030 Anmeldung dort nur über die Anmeldeseite der Oberfläche. Django liefert die Oberfläche für alle Pfade außer `api/`, `static/`, `admin/`, `_allauth/`, `accounts/` (F-2, F-3) | ✔ | 21.11.2026 |
| E-40 | Rollen „Verwalten" und „Lesen" als zwei Django-Gruppen (`manage`, `read`) mit eigenen DRF-Rechteklassen; jeder API-Endpunkt verlangt standardmäßig `CanRead`, Ausnahmen stehen ausdrücklich in einem Test (F-13, F-22) | ✔ | 21.11.2026 |
| E-41 | Datenmodell Struktur: Standort und Bereich mit Name, Anlage und Gerät mit Kennung und Name; Gerätefelder 1:1 aus `testfactory/layout/devices.csv` als Freitext, IP geprüft; Kennungen im ganzen System eindeutig; Löschen in M1 nur durch den Superuser im Admin (F-7, F-8, F-23) | ✔ | 21.11.2026 |
| E-42 | Dateien: Ablage nach SHA-256 im Docker-Volume (gleicher Inhalt einmal, atomar geschrieben), S3 später über dieselbe Schnittstelle; Feld `kind` (document, configuration), **in M1 werden nur Dokumente angenommen**, Konfigurationen erst mit dem Schwärzen in M5 (Leitplanke 5); gleicher Inhalt wie die neueste Version derselben Datei wird abgewiesen (409), an anderer Stelle angenommen mit Hinweis; Upload-Grenze `TWOX_UPLOAD_MAX_BYTES`, Standard 200 MB (F-15, F-16, F-19, F-20, F-21, F-29) | ✔ | 21.11.2026 |
| E-43 | Änderungsprotokoll mit django-auditlog: Struktur, Dateien, Benutzer (ohne Kennwort-Hash) samt Rolle, Sperre und Superuser-Recht; keine IP-Adressen; lesen dürfen nur Verwalter; in M1 nur Admin-Leseschutz und kein API-Schreibweg, Schutz in der Datenbank vor Version 0.1 erneut prüfen (F-24 bis F-28) | ✔ | 21.11.2026 |
| E-44 | CSV-Import genau im Format von `testfactory/layout/devices.csv` (13 Spalten, Komma, UTF-8); Abgleich über `plant_id` und `device_id`, anlegen und aktualisieren, nie löschen, alles oder nichts, Probelauf als Standard (F-31, F-32) | ✔ | 21.11.2026 |
| E-45 | Neue Abhängigkeiten für M1 zugelassen: django-allauth[headless] mit pyjwt, cryptography, cffi, pycparser; django-auditlog; i18next und react-i18next (mit html-parse-stringify); react-router (mit cookie-es, @remix-run/route-pattern); @tanstack/react-query (mit query-core). Die Lizenz MIT-0 (cffi) kommt in die Lizenzregeln (F-6, F-10, F-17, F-18, F-24) | ✔ | 21.11.2026 |
| E-46 | GNU gettext (GPL) ist als Werkzeug im Dev-Image und in einer Bau-Stufe zugelassen, nicht im Laufzeit-Image und nicht eingebunden; `.mo`-Dateien kommen nie ins Repository (F-33) | ✔ | 21.11.2026 |
| E-47 | Font Awesome Free 6.7.2 (CC-BY-4.0) ist als benannte Ausnahme zugelassen, nur als Teil des unveränderten Django-Admins (`admin/img/*.svg`); die Namensnennung liefert die mitgelieferte `admin/img/README.md` | ✔ | 21.11.2026 |

## Begründungen

### E-03 Technik (Vorschlag 2 vom 21.11.2026, bestätigt mit E-21)

**Auswahlregel (E-13):** Gewählt wird, was vergleichbare erfolgreiche Open-Source-Projekte einsetzen und womit KI-Werkzeuge am zuverlässigsten arbeiten.

**Vergleichsprojekte:** NetBox (Django, PostgreSQL, Redis) · Paperless-ngx (Django, Celery, PostgreSQL, Redis) · Onyx (FastAPI, Celery, PostgreSQL, Redis, eigener Suchindex, Next.js) · Dify (Flask, PostgreSQL, Next.js).

**Weitere Befunde:** GitHub-Jahresbericht 2026: TypeScript vor Python und JavaScript. Microsoft-Studie von Ende 2025 (SWE-Sharp-Bench): KI-Werkzeuge lösten rund 70 % der Python-, aber nur rund 40 % der C#-Aufgaben; SWE-bench Verified besteht fast zur Hälfte aus Django-Aufgaben. Der Abstand kann mit neueren Modellen kleiner sein.

| Schicht | Wahl | Grund |
| --- | --- | --- |
| Backend-Sprache | Python (3.13 oder neuer; M0 legt die Version fest) | Sprache aller vier Vergleichsprojekte; Docling und die Bibliotheken für Batfish, NetBox, Verwaltungsschale und MCP sind in Python zu Hause |
| Web-Framework | Django 6.1, ab April 2027 Django 6.2 (Langzeit-Support) | Der Kern ist eine Verwaltungsanwendung (Geräte, Dateien, Benutzer, Rechte, Protokoll, zwei Sprachen); gleiches Muster wie NetBox und Paperless-ngx |
| API | Django REST Framework mit OpenAPI (drf-spectacular) | verbreiteter Standard; daraus entsteht der typisierte Client der Oberfläche |
| Antwort-Stream | asynchrone Django-Ansicht mit Server-Sent Events | Antworten des Sprachmodells erscheinen fortlaufend |
| Hintergrundarbeit | Celery-Worker mit getrennten Warteschlangen (Einlesen, Einbetten, Sonstiges) | Standard in Paperless-ngx und Onyx; jede Warteschlange skaliert für sich |
| Broker und Zwischenspeicher | Valkey (Redis-kompatibel, BSD) | Redis hat 2024 die BSD-Lizenz aufgegeben, Valkey führt sie fort |
| Datenbank | PostgreSQL 17 oder neuer mit pgvector | Daten, Volltext- und Vektorsuche in einem System; wenige Bausteine für kleine Betriebe |
| Suche | eigene Schnittstelle; Standard PostgreSQL (Volltext, Trigramme, pgvector) | große Installationen wechseln auf OpenSearch oder Qdrant, ohne den Rest zu ändern |
| Dateien | Dateisystem-Volume, wahlweise S3-kompatibel (django-storages) | einfach im Kleinen, austauschbar im Großen |
| Einlesen | docling-serve als eigener Container | fertiger Dienst; hält die schweren Modelle aus dem Anwendungs-Image heraus |
| Sprachmodell und Einbettungen | OpenAI-kompatible Schnittstelle; Standard Ollama | lokal und austauschbar |
| Oberfläche | React, TypeScript, Vite, Tailwind CSS; fertig gebaut von Django ausgeliefert | auch Onyx und Dify nutzen React und TypeScript; kein Node-Server im Betrieb |
| Anmeldung | lokale Konten, OpenID Connect und Zwei-Faktor über django-allauth | Firmen-Login ohne Aufpreis |
| Erweiterungen | Einlese-Module als Plugins (Python Entry Points) | Hersteller-Formate als eigene Pakete, ohne den Kern zu ändern (Vorbild NetBox-Plugins) |
| Betrieb | Docker Compose; später zusätzlich Helm | ein Befehl im Kleinen, Kubernetes im Großen |
| Qualität | uv, Ruff, strenge Typprüfung, pytest gegen echte PostgreSQL, Vitest, Playwright | Python hat keinen Compiler als Sicherheitsnetz; Typprüfung und Tests übernehmen das |
| CI | GitHub Actions: Lint, Typprüfung, Tests, Prüffragen, Lizenzprüfung, Suche nach Geheimnissen | jede Änderung wird gleich geprüft |

**Zur Geschwindigkeit:** Die Rechenlast liegt in PostgreSQL, Docling und dem Modell-Server, nicht im Python-Code. Die API hält keinen Zustand und läuft in beliebig vielen Instanzen.

**Geprüft und verworfen:**

- **.NET:** Keines der Vergleichsprojekte nutzt es. KI-Werkzeuge schnitten in C# deutlich schlechter ab. Die Python-Bibliotheken wären nur als getrennte Dienste nutzbar.
- **Alles in TypeScript (Node):** meistgenutzte Sprache, aber die Bibliotheken für Dokumente, Netz und OT fehlen dort.
- **FastAPI statt Django:** schlanker und durchgehend asynchron, aber Anmeldung, Rechte, Migrationen und Verwaltungsoberfläche müssten zusammengesetzt werden – mehr eigener sicherheitskritischer Code.
- **Microservices, Kubernetes und eigener Suchserver ab Tag 1:** Aufwand ohne Nutzen für kleine Betriebe. Der Skalierungspfad hält den Weg offen.

**Skalierungsgrundsatz:** Skalierbarkeit entsteht durch Schnittstellen (API, Worker, Broker, Datenbank, Suche, Dateien, Einlesen, Sprachmodell, Anmeldung, Betrieb). Kein Baustein für große Betriebe wird gebaut, bevor ein Nutzer ihn braucht – aber keiner darf durch den Entwurf verbaut werden.

### E-09 Bezeichner `twox`

Python-Pakete und Umgebungsvariablen dürfen nicht mit einer Ziffer beginnen.

### E-14 Nur der Push braucht eine Freigabe

Erste Fassung von a7 am 21.11.2026: „die leitstelle commitet und pusht auf meine freigabe". Auf Rückfrage präzisiert: „ich gebe nur push auf github frei, rest machst du".
Folge: Die Leitstelle committet auf `main` und führt Auftragszweige zusammen, ohne zu fragen. Jeder Push nach GitHub – `main` wie Auftragszweige – wartet auf a7. Das ändert Stufe A (dort lag das Schieben der Zweige beim Auftragsbearbeiter) und die Sicherungsregel aus Abschnitt 8.5: gesichert wird erst nach Freigabe.

### E-21 Selbstständig bauen

Wortlaut von a7 am 21.11.2026 auf die Bitte, die vier ◻-Punkte zu bestätigen: „okay, sobald du schon sachen bauen kannst fange selbstständig an, damit ich so früh wie möglich die ersten sachen lokal testen/ansehen kann".
Auslegung der Leitstelle: E-03, die Auswahl der Testfabrik (E-06), der Bezeichner `twox` (E-09) und die Freigabestufen (8.2, mit der Änderung aus E-14) sind bestätigt. Aufträge für M0 und T1 dürfen ohne Einzelfreigabe der Liste starten; die dort aufgeführten Abhängigkeiten des Stacks aus Abschnitt 5.2 gelten als genehmigt. Fragen der Stufe C darüber hinaus (Lizenzklärung fremder Unterlagen, Anmeldung, Rechte, Schwärzen, Abnahme) gehen weiterhin an a7. Widerspricht a7 dieser Auslegung, wird der Eintrag korrigiert.

### E-23 Fragen in den Aufträgen nach Empfehlung entschieden

Grundlage: a7 am 21.11.2026: „ich gebe nur push auf github frei, rest machst du" und „fange selbstständig an". Die Leitstelle hat daraus abgeleitet, dass sie die in den Aufträgen 001–015 und 101–114 gestellten Fragen selbst nach der dort begründeten Empfehlung entscheidet, damit die Arbeit nicht steht. Das ist eine Auslegung der Leitstelle, keine wörtliche Entscheidung von a7.

Die wichtigsten so getroffenen Festlegungen (Einzelheiten und Alternativen stehen im jeweiligen Auftrag):

- **Python 3.14**, **PostgreSQL 18** mit pgvector, **Valkey 9.1.x**, **Node 24**, **TypeScript 6** (Version 7 tragen typescript-eslint und der Client-Generator noch nicht).
- **Compose:** `compose.yaml` im Wurzelverzeichnis bindet `deploy/compose/compose.yaml` ein, damit `docker compose up` wörtlich gilt.
- **Typprüfung** mit mypy (strict) und django-stubs. **ASGI-Server** uvicorn. **Auslieferung der Oberfläche** über WhiteNoise. **API-Client** mit @hey-api/openapi-ts.
- **Eigenes Benutzermodell** (`accounts.User`, unveränderte Ableitung von `AbstractUser`) schon in M0, weil ein späterer Wechsel aufwendig ist. Anmeldung und Rollen bleiben M1.
- **Lizenzen:** ISC, 0BSD, PSF-2.0 und Python-2.0 gelten als gleichwertig freizügig. Benannte Ausnahmen: psycopg (LGPL-3.0-only, in Leitplanke 7 selbst genannt), pathspec (MPL-2.0, nur Entwicklung, über mypy), lightningcss (MPL-2.0, nur Build, über Tailwind und Vite). pandoc (GPL-2.0-or-later) nur als einmaliges Werkzeug im Wegwerf-Container, nicht eingebunden.
- **Geheimnissuche** mit der gitleaks-Kommandozeile (MIT), nicht mit der gitleaks-action (proprietäre Bedingungen).
- **Testfabrik:** eigener kleiner Rahmen unabhängig vom Django-Gerüst; Manifest in JSON-Schreibweise ohne YAML-Bibliothek; Dokumente auf Deutsch, Quellen unter `docs/testfabrik/`; UR5e und URSim auf Softwarestand 5.25.1; Raspberry-Pi-Abbild nur als Verweis.
- **Stufe C wie Stufe B zusammenführen**, wenn beim Abschluss nichts über das im Auftrag Genannte hinaus dazugekommen ist (keine weitere Abhängigkeit, keine nicht gedeckte Lizenz, keine offene Frage, keine Abweichung).

Nicht entscheidbar durch die Leitstelle und deshalb unter „Wartet auf a7" in `docs/STATUS.md`: Anfragen an Hersteller zur Lizenzlage, Einstellungen am GitHub-Konto, Push, Abnahme.

### E-19 Repository von Anfang an öffentlich

Entscheidung von a7 am 21.11.2026 auf Rückfrage der Leitstelle („Bleibt öffentlich"). Eine Begründung wurde nicht genannt.
Folgen, die die Leitstelle daraus ableitet:

- Alles, was gepusht wird, ist sofort öffentlich – auch Zweige der Auftragsbearbeiter, Auftragsdateien und Status.
- Die Regeln aus Abschnitt 10.4 gelten ab dem ersten Push ohne Schonfrist: keine Herstellerunterlagen, keine längeren Auszüge, Nutzungsbedingungen je Quelle beachten.
- Geheimnissuche und Lizenzprüfung gehören in den ersten CI-Auftrag, nicht erst zu Version 0.1.
- „Version veröffentlichen" bleibt Stufe C.

## Abhängigkeiten

Jede neue Abhängigkeit bekommt hier einen Eintrag (Leitplanke 7). Bevorzugt: MIT, Apache-2.0, BSD, PostgreSQL-Lizenz. LGPL und MPL nur als unverändert eingebundene Bibliothek.

| Name | Lizenz | Zweck | Eingeführt mit Auftrag | Genehmigt von a7 |
| --- | --- | --- | --- | --- |
| gitleaks (Kommandozeile, Image `ghcr.io/gitleaks/gitleaks:v8.30.1`, per Digest festgelegt) | MIT | Suche nach Geheimnissen, lokal und in der CI | 003 | nach E-23 |
| actions/checkout v7.0.1 (per Commit festgelegt) | MIT | Auschecken in GitHub Actions | 003 | nach E-23 |
| react, react-dom 19.3.1 | MIT | Oberfläche (einzige Laufzeitpakete im ausgelieferten Build, mit scheduler) | 002 | nach E-23 |
| typescript 6.0.3 | Apache-2.0 | Typprüfung der Oberfläche (Entwicklung) | 002 | nach E-23 |
| vite 8.3.8, @vitejs/plugin-react 6.3.0 | MIT | Build der Oberfläche | 002 | nach E-23 |
| tailwindcss 4.3.5, @tailwindcss/vite 4.3.5 | MIT | CSS (Build) | 002 | nach E-23 |
| lightningcss 1.33.0 samt Plattformpaketen (mitgezogen) | MPL-2.0 | CSS-Verarbeitung beim Build, nicht im ausgelieferten Code | 002 | benannte Ausnahme nach E-23 |
| vitest 5.1.1, @testing-library/react 16.3.3, @testing-library/dom 10.4.2, jsdom 31.0.1 | MIT | Tests der Oberfläche | 002 | nach E-23 |
| @types/react 19.3.0, @types/react-dom 19.3.0 | MIT | Typen (Entwicklung) | 002 | nach E-23 |
| eslint 10.15.0, typescript-eslint 8.73.0, eslint-plugin-react-hooks 7.1.1 | MIT | Linter der Oberfläche | 002 | nach E-23 |
| license-checker-rseidelsohn 5.0.1 | BSD-3-Clause | Lizenzliste der npm-Pakete (Entwicklung) | 002 | nach E-23 |
| Mitgezogene Entwicklungspakete der Oberfläche (über jsdom, @tailwindcss/node, license-checker, ESLint): ISC, 0BSD, BlueOak-1.0.0, CC-BY-3.0, CC-BY-4.0, CC0-1.0 | wie genannt | nur Entwicklung und Build, nicht im ausgelieferten Code | 002 | E-23 und E-25 |
| Image `node:24-slim` (nur per Tag festgelegt) | Node.js: MIT; Lizenzen des Debian-Grundsystems im Image ungeprüft | Build- und Testumgebung der Oberfläche, nicht im Betrieb | 002 | nach E-23 |
| Python 3.14 (Image `python:3.14.10-slim`, per Tag festgelegt) | PSF-2.0; Lizenzen des Debian-Grundsystems im Image ungeprüft | Laufzeit und Basis-Image des Backends | 001 | nach E-23 |
| Django 6.1.3 (mit asgiref, sqlparse) | BSD-3-Clause | Web-Framework | 001 | nach E-23 |
| psycopg 3.3.9, psycopg-binary 3.3.9 | LGPL-3.0-only; Lizenzen der gebündelten Bibliotheken noch nicht belegt (Auftrag 006) | PostgreSQL-Treiber, unverändert eingebunden | 001 | benannte Ausnahme nach Leitplanke 7 und E-23 |
| uv 0.13.9 (Image `ghcr.io/astral-sh/uv`) | MIT OR Apache-2.0 | Paket- und Umgebungsverwaltung | 001 | nach E-23 |
| ruff 0.17.6, mypy 2.4.1, django-stubs 6.1.2, pytest 9.2.0, pip-licenses 5.5.5 | MIT | Lint, Typprüfung, Tests, Lizenzliste (Entwicklung) | 001 | nach E-23 |
| pytest-django 4.14.0 | BSD-3-Clause | Django-Anbindung für pytest (Entwicklung) | 001 | nach E-23 |
| pathspec 1.1.1 (mitgezogen von mypy) | MPL-2.0 | nur Entwicklung | 001 | benannte Ausnahme nach E-23 |
| typing_extensions 4.16.0 (mitgezogen von mypy und django-stubs) | PSF-2.0 | nur Entwicklung | 001 | nach E-23 |
| Image `pgvector/pgvector:0.8.7-pg18` (PostgreSQL 18.7 mit pgvector 0.8.7) | PostgreSQL-Lizenz | Datenbank | 001 | nach E-23 |
| Image `python:3.14.10-slim-trixie` (per Digest festgelegt) als Laufzeit der Testfabrik-Skripte; Debian-Grundsystem mit 87 Paketen, darunter GPL- und LGPL-Programme | Python: PSF-2.0; Grundsystem gemischt | unveränderte Laufzeit, nicht eingebunden | 101 | nach E-23 |
| mypy 2.4.1 mit mypy_extensions, librt, ast-serialize (MIT), typing_extensions (PSF-2.0), pathspec (MPL-2.0) im Prüf-Image der Testfabrik | wie genannt | Typprüfung der Testfabrik-Skripte (zweiter Einbauort, dieselben Versionen wie in 001) | 101 | nach E-23 |
| djangorestframework 3.18.3, drf-spectacular 0.30.0 (mit PyYAML, uritemplate, inflection, jsonschema, referencing, rpds-py, attrs) | BSD-3-Clause; mitgezogene Pakete MIT bzw. BSD; gebündelte Bestandteile von rpds-py und PyYAML noch nicht belegt | API und OpenAPI-Beschreibung | 005 | nach E-23 |
| uvicorn 0.54.0 (mit click, h11) | BSD-3-Clause; h11 MIT | ASGI-Server | 005 | nach E-23 |
| djangorestframework-stubs 3.18.2 | MIT | Typen für DRF (Entwicklung) | 005 | nach E-23 |
| In psycopg-binary 3.3.9 gebündelt (Rad für linux/x86_64): libpq 18.6 (PostgreSQL-Lizenz), OpenSSL 3.5.9 (Apache-2.0), MIT Kerberos 1.22.2 und libcom_err (MIT-artig), OpenLDAP (OLDAP-2.8, BSD-artig), Cyrus SASL (BSD-artig mit Nennungsklausel), keyutils (LGPL-2.0-or-later, nur aus Zweitquelle belegt), libxcrypt (LGPL-2.1-or-later) | wie genannt; kein GPL, AGPL und keine Nutzungsbeschränkung gefunden | unverändert als eigene, dynamisch geladene Dateien im Rad; gelangen ins Laufzeit-Image | 006 | ✔ a7, 21.11.2026 (E-28) |
| Eigenes npm-Paket `twox-web` (private; vom Werkzeug als UNLICENSED gemeldet, Projektlizenz Apache-2.0) | Apache-2.0 | von der Lizenzprüfung ausgenommen | 006 | nach E-23 |
| poppler-utils (im offiziellen Python-Image einmalig nachinstalliert) | GPL-2.0 | einmaliges Werkzeug zum Lesen von PDF-Seiten im Wegwerf-Container; nicht eingebunden, nicht im Repository, in keinem Projekt-Image | 106 | wie pandoc nach E-23 |
| celery[redis] 5.7.0 (mit kombu, amqp, billiard, vine, click-Erweiterungen, prompt-toolkit, python-dateutil, tzlocal, six) | BSD-3-Clause; mitgezogene Pakete BSD, MIT bzw. Apache/BSD | Hintergrundarbeit | 008 | nach E-23 |
| redis (redis-py) 8.1.0 | MIT | Client für Valkey | 008 | nach E-23 |
| celery-types 0.26.0 | Apache-2.0 | Typen für Celery (Entwicklung) | 008 | nach E-23 |
| Image `valkey/valkey:9.1.4` | BSD-3-Clause | Broker und Ergebnisspeicher | 008 | nach E-23 |
| pandoc 3.14 (Image `pandoc/core:3.14.0.0`, per Digest festgelegt; Basis Alpine 3.24.4) | GPL-2.0-or-later | einmaliges Werkzeug: vier OPNsense-Seiten nach Markdown umgewandelt, `docker run --rm --network none`; nicht eingebunden, in keinem Projekt-Image | 108 | nach E-23 |
| Testdaten `testdata/klein/`: vier Seiten der OPNsense-Dokumentation (Commit `953dd3d`, LICENSE unverändert beigelegt) und die Betriebssicherheitsverordnung als PDF von gesetze-im-internet.de | BSD-2-Clause bzw. amtliches Werk (§ 5 Abs. 1 UrhG) | Testmaterial für die CI, liegt im Repository; Leitstelle hat alle Dateien bytegleich mit dem Original geprüft | 108 | nach E-23 |
| @hey-api/openapi-ts 0.99.0 (mit 42 mitgezogenen Paketen, alle nur Entwicklung: MIT, ISC, BSD-2-Clause, Python-2.0) | MIT | erzeugt den typisierten API-Client der Oberfläche; der erzeugte Code (aus MIT-Vorlagen) liegt im ausgelieferten Bündel – Lizenzhinweis klärt Auftrag 013 | 012 | nach E-23 |
| docling-serve-cpu 1.38.2 (Image `quay.io/docling-project/docling-serve-cpu:v1.38.2`, per Digest festgelegt; Basis CentOS Stream 9) | MIT; Modelle: Apache-2.0, MIT, CDLA-Permissive-2.0 (E-30); EasyOCR-Gewichte ohne feststellbare Lizenz, ungenutzt (E-31) | Einlese-Dienst, unverändertes Image, ohne Internetzugang (E-32) | 009 | E-30 bis E-32 |
| whitenoise 6.12.0 | MIT | Auslieferung der gebauten Oberfläche durch Django; Drittanbieter-Hinweise unter `/static/THIRD-PARTY-NOTICES.txt` | 013 | nach E-23 |
| @playwright/test 1.65.1 (mit playwright, playwright-core) | Apache-2.0 | Browser-Test der Testseite (Entwicklung) | 014 | nach E-23 |
| Image `mcr.microsoft.com/playwright:v1.65.1-noble` (per Digest festgelegt; Ubuntu 24.04) | Playwright Apache-2.0, Chromium BSD-3-Clause, Node MIT; im Image zusätzlich Firefox (MPL-2.0), WebKit (LGPL/BSD) und ein Chrome-for-Testing-Build mit Google-Nutzungsbedingungen und WidevineCdm (proprietär) | unveränderte Testlaufzeit nur in CI und lokal, wird nicht weitergegeben; der Test nutzt Chromium | 014 | nach E-23 (unveränderte Laufzeit); Hinweis an a7 |
| ruff 0.17.6 im Prüf-Image der Testfabrik | MIT | Lint und Formatprüfung der Testfabrik-Skripte (zweiter Einbauort, dieselbe Version wie in 001) | 114 | nach E-23 |
| i18next 27.2.3, react-i18next 18.0.3, html-parse-stringify 4.0.1 (mitgezogen) | MIT | Zweisprachige Oberfläche; im ausgelieferten Bündel, Hinweise in `THIRD-PARTY-NOTICES.txt`. typescript, @types/react und csstype erscheinen als optionale Peer-Abhängigkeiten in der Laufzeitliste, kommen aber nicht ins Bündel | 018 | E-45 |
| Fremdbibliotheken des Django-Admins (mit Django 6.1.3, unverändert ausgeliefert): jQuery 3.7.1, Select2 4.0.13, XRegExp 5.1.1 (enthält Teile von core-js) | MIT, abgelesen an den mitgelieferten Lizenzdateien | Admin für Superuser (E-39) | 016 | E-39 |
| Font Awesome Free 6.7.2 (Symbole im Django-Admin) | CC-BY-4.0 | Admin für Superuser; Namensnennung in `admin/img/README.md` | 016 | ✔ a7, 21.11.2026 (E-47) |
| redis (redis-py) 8.1.0 – seit 016 auch direkt von Djangos `RedisCache` genutzt (bisher nur über `celery[redis]` im Lock) | MIT | Zwischenspeicher in Valkey | 016 | nach E-23; bei Änderungen an der Celery-Abhängigkeit beachten |
