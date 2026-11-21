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
