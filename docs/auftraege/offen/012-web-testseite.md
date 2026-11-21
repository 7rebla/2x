# Auftrag 012 – Testseite, Teil Oberfläche

Meilenstein: M0 · Freigabestufe: C · Status: offen

## Ziel

Die Oberfläche zeigt auf einer Testseite den Wert aus der Datenbank und das Ergebnis aus dem Worker. Sie spricht die API über einen Client an, der aus der OpenAPI-Beschreibung erzeugt wird (Abschnitt 5.2).

## Umfang

- OpenAPI-Schema des Backends als Datei `web/openapi/schema.yml` (eingecheckt), erzeugt mit `python manage.py spectacular`.
- Client-Generator nach a7s Antwort auf Frage 1 in Auftrag 002 (Empfehlung dort: `@hey-api/openapi-ts`). npm-Skript `api:generate` erzeugt den Client nach `web/src/api/generated/` (eingecheckt).
- Die Testseite ersetzt den Platzhalter aus Auftrag 002 und zeigt:
  - Datenbank: Zustand und `server_version`.
  - Worker: Zustand, `result` und Dauer.
  - Ladezustand, Fehlerzustand je Teil (mit dem Fehlertext der API) und einen eigenen Zustand, wenn die API gar nicht antwortet.
  - Eine Schaltfläche zum erneuten Prüfen.
- Alle sichtbaren Texte liegen gesammelt in einem Modul (Englisch), damit die spätere Übersetzung (Deutsch/Englisch) sie an einer Stelle findet.
- Stabile Testmerkmale (`data-testid`) an den Werten für Datenbankversion, Worker-Ergebnis und Fehlerzustand (für Auftrag 014).
- Vitest-Tests mit nachgestellter API: alles in Ordnung · Worker ausgefallen · API nicht erreichbar · erneutes Prüfen löst einen neuen Abruf aus.
- Die API wird mit relativem Pfad (`/api/...`) angesprochen; Oberfläche und API kommen im Betrieb vom selben Ursprung (Auftrag 013).

## Nicht-Ziele

- Auslieferung der gebauten Oberfläche durch Django (Auftrag 013), Playwright-Test (Auftrag 014).
- Übersetzungsbibliothek, Routing, Anmeldung, Gestaltung über das Nötige hinaus.
- Änderungen am Backend und an Compose-Dateien.

## Betroffene Bereiche (Ordner, Dateien)

- `web/openapi/schema.yml` (neu)
- `web/src/**` (Testseite, Texte, `api/generated/`)
- `web/package.json`, `web/package-lock.json` (Generator, Skript `api:generate`), Konfigurationsdatei des Generators
- ESLint-Konfiguration nur, um den erzeugten Code auszunehmen
- `web/scripts/` (nur die Regeldatei der Lizenzprüfung, falls ein mitgezogenes Paket eine bereits genehmigte Lizenz in neuer Schreibweise trägt)

## Akzeptanzkriterien (prüfbar)

`W` steht für `docker compose -p twox-012 -f deploy/compose/compose.web.yaml`, `B` für `docker compose -p twox-012`. Vorher `.env.example` nach `.env` kopieren (falls nicht vorhanden).

0. Vorab: `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren oder ausführen; Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. `B run --rm backend-dev python manage.py spectacular --file /tmp/schema.yml` erzeugt ein Schema, das inhaltsgleich mit `web/openapi/schema.yml` ist (Vergleich und Ergebnis im Kurzbericht).
2. `W run --rm web-dev npm ci` endet mit Exit-Code 0 ohne `ERESOLVE`.
3. `W run --rm web-dev npm run api:generate` endet mit Exit-Code 0; danach zeigt `git diff --exit-code -- web/src/api` keine Änderung (der eingecheckte Client ist aktuell).
4. `W run --rm web-dev npm run lint` und `W run --rm web-dev npm run typecheck` enden mit Exit-Code 0.
5. `W run --rm web-dev npm run test` endet mit Exit-Code 0; die vier oben genannten Fälle sind dabei, 0 fehlgeschlagen.
6. `W run --rm web-dev npm run build` endet mit Exit-Code 0.
7. Im Quelltext der Oberfläche steht keine feste Serveradresse: `git grep -n -E 'https?://' -- web/src` zeigt keine Treffer außerhalb von Kommentaren und erzeugtem Code ohne Laufzeitwirkung.
8. Die Typen der Antwort stammen aus dem erzeugten Client, nicht aus handgeschriebenen Kopien: `git grep -n 'server_version' -- web/src` zeigt Treffer nur im erzeugten Code, in der Testseite und in Tests.
9. Lizenzprüfung: `W run --rm web-dev npm run licenses` endet mit Exit-Code 0. Meldet sie ein Paket mit nicht gedeckter Lizenz: nichts in die Erlaubt-Liste schreiben, Frage in den Auftrag, Status „wartet auf a7“.
10. `web/openapi/schema.yml` ist UTF-8 mit LF-Zeilenenden: `git ls-files --eol web/openapi/schema.yml` zeigt `i/lf w/lf`.
11. Abräumen: `W down -v` und `B down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

- **Voraussetzung:** Die Aufträge 002 und 010 sind zusammengeführt (und damit 005, 006 und 008).
- **Abhängigkeiten.** Mit der Freigabe der Auftragsliste genehmigt a7 den Client-Generator nach seiner Antwort auf Frage 1 in Auftrag 002: bei (a) oder (c) `@hey-api/openapi-ts`, bei (b) `openapi-typescript` und `openapi-fetch`. Mitgezogene Pakete sind mitgenehmigt, soweit die Lizenzprüfung sie durchlässt (Kriterium 9). Jede weitere direkte Abhängigkeit ist nicht genehmigt.
- **Stand der Recherche vom 21.11.2026 (belegt):** `@hey-api/openapi-ts` 0.99.0 (MIT, Node >=22.18, Peer typescript >=5.5.3) · openapi-typescript 7.13.0 (MIT, Peer typescript ^5.x) · openapi-fetch 0.17.0 (MIT).
- `@hey-api/openapi-ts` ist eine 0.x-Version: exakt festschreiben. Ungeprüft und an der Paketdoku zu prüfen: ob der erzeugte Client ein zusätzliches Laufzeitpaket braucht. Falls ja: nicht einfach installieren, sondern Frage in den Auftrag, Status „wartet auf a7“.
- Schema erzeugen: Unter Windows PowerShell 5.1 schreibt die Umleitung mit `>` UTF-16. Das Schema daher im Container in eine Datei im eingebundenen Ordner schreiben lassen oder Git Bash verwenden.
- Der erzeugte Code wird nicht von Hand geändert.
- Die Feldnamen kommen aus Auftrag 010 (`database.ok`, `database.server_version`, `worker.ok`, `worker.result`, `worker.duration_ms`, jeweils `error`).
- Auftrag 013 läuft gleichzeitig und ändert Backend, Dockerfile und Compose; dieser Auftrag bleibt unter `web/`. Die Prüfung „Client ist aktuell“ hängt Auftrag 014 in die CI ein.
- Dieser Auftrag startet den Dienst `api` nicht und braucht keinen Host-Port.
- Keine Telemetrie, keine externen Schriften oder Skripte (Leitplanke 6).
- Sprache: Code und Texte Englisch.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Im Kurzbericht Name, Version, Lizenz und Quelle des Generators nennen.
- Kein Push. Die Leitstelle committet nach `main` und pusht auf a7s Freigabe.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

Keine eigenen. Maßgeblich ist die Antwort auf Frage 1 in Auftrag 002 (TypeScript-Version und Client-Generator). Fehlt sie: Status „wartet auf a7“.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
