# Auftrag 039 – Landkarte als interaktive Vorschau

Meilenstein: M1b (vorgezogene Vorschau auf M7, E-48) · Freigabestufe: C · Status: zur Prüfung

## Ziel

Eine interaktive Landkarte der erfassten Struktur in der Oberfläche: Standort, Bereiche, Anlagen und Geräte als Knoten, zusätzlich die IP-Netze der Geräte. Man kann verschieben, zoomen, Knoten anklicken und kommt zur Geräteseite. Die Karte zeigt nur, was in der Datenbank steht; Verbindungen aus Konfigurationen kommen erst mit M5/M7.

## Umfang

- Neue Seite `/map` mit Navigationseintrag „Landkarte" / „Map" (Rolle `read` genügt).
- Darstellung mit `@xyflow/react` (React Flow, MIT, E-48). Version exakt festlegen; Lizenz und mitgezogene Pakete an der Quelle prüfen und im Kurzbericht nennen. Laufzeitliste und `THIRD-PARTY-NOTICES.txt` in der Stufe `web-build` von `backend/Dockerfile` nachziehen; die CSS-Datei der Bibliothek einbinden.
- Daten nur aus den vorhandenen Endpunkten (`sites`, `areas`, `plants`, `devices`) über den erzeugten TanStack-Query-Client. Keine Änderung am Backend, an Schema oder Client.
- Knoten:
  - Standort und Bereiche als Gruppen (Parent-Knoten), Anlagen als Gruppen in ihrem Bereich, Geräte als Knoten in ihrer Anlage. Beschriftung: Name, darunter Kennung; bei Geräten zusätzlich IP-Adresse und Modell, wenn vorhanden.
  - Netze: Für jedes IPv4-/24-Netz, in dem mindestens ein Gerät liegt, ein Netz-Knoten (z. B. „192.168.0.0/24"); IPv6 nach /64. Kanten nur „Gerät gehört zu Netz", gestrichelt und als solche beschriftet. Geräte ohne IP haben keine Netzkante. **Keine Verbindungen erfinden**: keine Kanten zwischen Geräten, keine abgeleiteten Beziehungen.
- Bedienung: Verschieben, Zoomen, „Ansicht einpassen", Minikarte, Steuerelemente; Klick oder Enter auf einen Geräteknoten öffnet `/devices/:id`; Auswahl hebt das Gerät und seine Netzkante hervor. Suchfeld (Name, Kennung, IP) zentriert und markiert Treffer. Ein-/Ausblenden der Netz-Knoten.
- Anordnung automatisch und stabil: gleiche Daten ergeben dieselbe Anordnung (deterministisch, ohne Zufall); verschobene Knoten werden nicht gespeichert (kein Speichern von Positionen in M1b).
- Zweisprachig (neue Locale-Datei `map.json`, de/en), Texte aus Daten nur als Text.
- Leerer Zustand („Noch keine Struktur erfasst") mit Link zur Strukturseite; Lade- und Fehlerzustände wie auf den anderen Seiten.
- Tests: Vitest für die Umrechnung API-Daten → Knoten/Kanten (Netzbildung, Geräte ohne IP, IPv6, Leerfall, Determinismus) und für die Seite (Rolle `read` sieht die Karte, Klick führt zur Geräteseite). Playwright: Struktur über die API mit `testName()`/`testIp()` anlegen, `/map` öffnen, Geräteknoten und Netz-Knoten sichtbar, Klick führt zur Geräteseite, Suche findet das Gerät.

## Nicht-Ziele

- Verbindungen aus Konfigurationen, Protokolle, MQTT-Topics (M5/M7).
- Speichern von Positionen oder eigenen Layouts, Bearbeiten in der Karte.
- Geräte-Icons nach Typ (es gibt noch kein Typfeld; siehe `docs/design/icon-bedarfsanalyse.md`, H7 T-2). Einheitliche Knotenform genügt.
- Backend-Änderungen, neue Endpunkte.

## Betroffene Bereiche (Ordner, Dateien)

- `web/package.json`, `web/package-lock.json`
- `web/src/pages/MapPage.tsx` (neu), `web/src/pages/map/` (neu: Umrechnung, Knotentypen, Tests)
- `web/src/routes.tsx`, `web/src/navigation.ts` (ein Eintrag), `web/src/locales/{de,en}/map.json` (neu), `web/src/locales/{de,en}/nav.json` (ein Schlüssel), `web/src/i18n.ts` (Namensraum registrieren)
- `web/e2e/map.spec.ts` (neu), betroffene Tests in `web/src/routes.test.tsx`
- `backend/Dockerfile`, nur Stufe `web-build`

## Akzeptanzkriterien (prüfbar)

`W` = `docker compose -p twox-039-web -f deploy/compose/compose.web.yaml`, `D` = `docker compose -p twox-039`, `.env` mit `TWOX_API_PORT=18039`.

0. `docker version` und `docker compose version` enden mit Exit 0.
1. `W --profile dev build web-dev`, `W run --rm web-dev npm ci`, dann `lint`, `typecheck`, `test`, `build`, `licenses` je Exit 0.
2. `W run --rm web-dev npm run api:generate`, danach `git diff --exit-code -- web/openapi web/src/api` ohne Unterschied.
3. `D --profile dev build migrate api worker web-dev` Exit 0 (Laufzeitliste stimmt); `THIRD-PARTY-NOTICES.txt` im Image enthält `@xyflow/react` und alle mitgezogenen Laufzeitpakete.
4. Browser-Test wie in `ci.yml` (inkl. „Create test account") meldet alle Tests bestanden, auch `map.spec.ts`; ein zweiter Lauf ohne `down -v` ebenfalls.
5. Abräumen mit `down -v` beider Projekte endet mit Exit 0.

## Vorgaben und Hinweise

Voraussetzung: E-48 (a7, 22.11.2026). Kann parallel zu 034 (Backend) und 035 (Import-Oberfläche) laufen; 035 ändert weder `package.json` noch `routes.tsx`/`navigation.ts`.

- Einzige neue Abhängigkeit: `@xyflow/react` samt dem, was es mitzieht. Keine Layout-Bibliothek (dagre, elk) – die Anordnung ist eine eigene, kleine, getestete Funktion (Gitter je Gruppe). Sollte React Flow ohne zusätzliche Pakete nicht sinnvoll anordnen lassen: Frage in den Auftrag, Status „wartet auf a7".
- Prüfe, dass die Bibliothek keine Netzanfragen, Telemetrie oder Lizenzschlüssel-Prüfung zur Laufzeit macht (Leitplanke 6) und dass das Wasserzeichen/„attribution" der MIT-Version zulässig ausgeblendet werden darf oder sichtbar bleibt – im Kurzbericht nennen.
- Barrierefreiheit: Knoten per Tastatur erreichbar, Geräteknoten haben einen zugänglichen Namen; die Karte ersetzt nicht den Baum – auf der Seite ein Link zur Strukturseite als Listenansicht.
- Bundle wächst; Vite-Warnung über 500 kB ist zulässig, im Kurzbericht die neue Größe nennen. Wenn einfach möglich, die Kartenseite per `lazy()` nachladen.
- Sprache: Code und Kommentare Englisch, Kurzbericht Deutsch. Keine Personennamen, keine lokalen Pfade mit Benutzernamen.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

Entschieden am 22.11.2026 (E-48): interaktive Vorschau vorziehen, Darstellung mit React Flow; Netze aus IP-Adressen gruppieren (Empfehlung der Leitstelle, ohne Widerspruch von a7).

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Kriterien 0–5 sind erfüllt; alle Läufe am 22.11.2026 im Container (Docker Engine 29.9.3, Compose v5.7.0). Keine offene Frage, die die Arbeit aufhält; zwei Hinweise an a7 stehen unter „Abweichungen und Hinweise“ (Versionswahl, Namensnennung von React Flow).

### Neue Pakete (an der npm-Registry geprüft)

`@xyflow/react` **13.0.2**, exakt festgelegt (`web/package.json`). Registry: Lizenz MIT, Repository `github.com/xyflow/xyflow`, veröffentlicht am 17.11.2026; `latest` = 13.0.2. Mitgezogen (laut Lock und `package.json` im Container, 20 Pakete insgesamt):

| Paket | Version | Lizenz | Im Bündel |
| --- | --- | --- | --- |
| @xyflow/react | 13.0.2 | MIT | ja |
| @xyflow/system | 1.0.0 | MIT | ja |
| classcat | 5.0.5 | MIT | ja |
| zustand | 5.1.0 | MIT | ja |
| react-compiler-runtime | 1.0.0 | MIT (im Paket keine Lizenzdatei, siehe unten) | ja |
| d3-color, d3-dispatch, d3-drag, d3-interpolate, d3-selection, d3-timer, d3-transition, d3-zoom | 3.1.1, 3.0.2, 3.0.1, 3.0.2, 3.0.1, 3.0.2, 3.0.2, 3.0.1 | ISC | ja |
| d3-ease | 3.0.2 | BSD-3-Clause | ja |
| @types/d3-color, -drag, -interpolate, -selection, -transition, -zoom | 3.1.3, 3.0.7, 3.0.4, 3.0.12, 3.0.9, 3.0.9 | MIT | nein (nur Typen, reguläre Abhängigkeit von @xyflow/system) |

Keine Lizenz außerhalb von MIT/ISC/BSD-3-Clause. `npm run licenses`: „License check passed.“ ohne Änderung der Regeln.

**Netzzugriffe, Telemetrie, Lizenzschlüssel:** Im ausgelieferten Code von @xyflow/react, @xyflow/system, zustand, classcat, react-compiler-runtime und den d3-Modulen gibt es kein `fetch`, `XMLHttpRequest`, `sendBeacon`, `WebSocket` oder `EventSource` und keine Lizenzschlüssel-Prüfung (Suche über alle `.js`/`.mjs` der Pakete). Gefundene Adressen: der Link der Namensnennung auf reactflow.dev, Hilfe-Links in Konsolenmeldungen und Homepage-Kommentare der d3-Module. Die einzige „Prüfung“ (`handleAttributionWarning`) schreibt nur im Entwicklungsmodus eine Konsolenwarnung, wenn die Namensnennung ausgeblendet ist. Die Seite lädt nichts nach; die CSS-Datei der Bibliothek ist mitgebündelt.

**Namensnennung („attribution“):** bleibt sichtbar (kleiner Link „React Flow“ unten rechts in der Karte). Rechtlich verlangt MIT das nicht, aber die Projektseite (reactflow.dev, „Remove attribution“) bittet, sie nur mit einem Pro-Abo auszublenden. Ein Klick führt auf reactflow.dev; ohne Klick entsteht keine Anfrage.

### Was wurde gebaut?

- **Seite `/map`** (`web/src/pages/MapPage.tsx`, per `lazy()` nachgeladen): Überschrift „Landkarte“/„Map“, Link „Struktur als Liste ansehen“ zur Strukturseite, Einleitung, Suchfeld, Statuszeile mit Trefferzahl (`role="status"`), Schalter „Netze anzeigen“, Legende („Gestrichelte Linie: Die Adresse des Geräts liegt in diesem Netz …“). Darunter die Karte mit React Flow: Verschieben, Zoomen, Steuerelemente (Vergrößern, Verkleinern, „Ansicht einpassen“), Minikarte (verschieb- und zoombar), Punktraster. Hell erzwungen (`forceColorMode="light"`), weil der Rest der Oberfläche hell ist. Lade-, Fehler- und Leerzustand wie auf der Strukturseite; leer: „Noch keine Struktur erfasst.“ mit Link „Zur Struktur“.
- **Umrechnung** `web/src/pages/map/graph.ts` (rein, getestet): nutzt `buildTree` der Strukturseite (gleiche Sortierung), vorher Sortierung nach id, damit gleiche Namen nicht von der Reihenfolge der Antwort abhängen.
  - Knoten: Standort, Bereich, Anlage als Gruppen (`parentId`), Geräte in ihrer Anlage (`extent: "parent"`). Beschriftung: Art, Name, bei Anlagen die Kennung; Geräte mit Name, Kennung, IP und Modell (wenn vorhanden).
  - Netze: IPv4 nach /24 (`192.168.0.0/24`), IPv6 nach /64 in der Kurzform nach RFC 5952 (`2001:db8:0:1::/64`, auch mit IPv4-Anteil). Ein Netz-Knoten je Netz mit mindestens einem Gerät, IPv4 vor IPv6, nach Adresse sortiert, als Spalte rechts neben den Standorten.
  - Kanten nur „Gerät → Netz“, gestrichelt, beschriftet „im Netz“/„in network“. Geräte ohne IP haben keine Kante; es gibt keine Kanten zwischen Geräten.
  - Anordnung: Gitter je Gruppe aus festen Knotengrößen (Spaltenbreite = breitestes Kind, Zeilenhöhe = höchstes Kind, etwa quadratisch, Spaltenzahl begrenzt). Kein Zufall; gleiche Daten ergeben dieselben Positionen. Verschobene Knoten werden nicht gespeichert. Die Karte wird nur neu aufgebaut, wenn sich die Anordnung wirklich ändert (Signatur aus ids, Positionen, Größen und Daten).
  - Suche (`matchingNodeIds`): Name, Kennung, IP-Adresse, Netz; ohne Groß-/Kleinschreibung.
- **Knoten** `web/src/pages/map/nodes.tsx`: einheitliche Form je Art (Gruppe, Gerät, Netz), keine Typ-Icons; Daten nur als Text (`title` für abgeschnittene Texte). Griffe für die Kanten sind unsichtbar und nicht verbindbar.
- **Bedienung:**
  - Klick oder Enter auf ein Gerät öffnet `/devices/:id`.
  - Geräteknoten haben die Rolle `link` und einen Namen wie „Gerät SPS Bohrstation (drill-plc), 192.168.0.50 im Netz 192.168.0.0/24, öffnet die Geräteseite“; Gruppen und Netze `group` mit Namen, Rollenbeschreibung „Knoten“. Alle Knoten sind per Tab erreichbar.
  - Hervorhebung: ausgewählte (Leertaste, Auswahlrahmen), fokussierte und gefundene Geräte bekommen einen dunklen Rahmen; ihre Netzkante wird dunkel und dicker, der Netz-Knoten ebenfalls. Treffer der Suche bekommen einen gelben Ring, die Ansicht passt sich auf die Treffer ein.
  - Gruppen sind weder verschieb- noch auswählbar, damit man über ihnen die Karte verschieben kann; Geräte (innerhalb ihrer Anlage) und Netze lassen sich ziehen. Löschen per Taste ist abgeschaltet.
  - Texte von React Flow (Steuerelemente, Minikarte, Tastaturhilfe, Ansage beim Verschieben) kommen über `ariaLabelConfig` aus `map.json`.
- **Navigation und Routen:** Eintrag „Landkarte“/„Map“ nach „Struktur“, Rolle `read` (`navigation.ts`); Route `map` in `routes.tsx` mit `Suspense`/`Loading`.
- **Texte:** `web/src/locales/{de,en}/map.json` (neu), Schlüssel `map` in `nav.json`; Namensraum in `i18n.ts` und `i18next.d.ts` registriert.
- **`backend/Dockerfile`, Stufe `web-build`:** Laufzeitliste um die 20 Pakete ergänzt; Hinweise in `THIRD-PARTY-NOTICES.txt` für alle 14 Pakete mit ausgeliefertem Code. `react-compiler-runtime` hat keine Lizenzdatei; sein Quelltextkopf verweist auf die Lizenzdatei des Repositorys facebook/react (MIT, „Copyright (c) Meta Platforms, Inc. and affiliates.“). Der Hinweis zitiert dafür die gleichlautende Datei aus dem Paket `react` und sagt das.
- **Doku:** `web/src/pages/README.md` (Adresse und Abschnitt „Map“), `web/src/locales/README.md` (Namensraum `map`).

### Wie wurde getestet?

`W` = `docker compose -p twox-039-web -f deploy/compose/compose.web.yaml`, `D` = `docker compose -p twox-039`; `.env` aus `.env.example` (ohne BOM) mit `TWOX_API_PORT=18039`. Die Umgebungen „2x“ und „twox-leit“ wurden nicht berührt.

| AK | Ergebnis |
| --- | --- |
| 0 | erfüllt: `docker version` (Server 29.9.3), `docker compose version` (v5.7.0), Exit 0 |
| 1 | erfüllt: `W --profile dev build web-dev`, `npm ci` („added 425 packages“, vor der Installation von React Flow), danach `npm install --save-exact @xyflow/react@13.0.2` („added 20 packages“). `lint`, `typecheck` ohne Meldung; `test`: 21 Dateien, 367 Fälle bestanden; `build` Exit 0; `licenses`: „422 packages … License check passed.“ |
| 2 | erfüllt: `npm run api:generate` Exit 0; `git diff --exit-code -- web/openapi web/src/api` Exit 0, `git status --porcelain --untracked-files=all` leer |
| 3 | erfüllt: `D --profile dev build migrate api worker web-dev backend-dev` Exit 0 (Prüfung der Laufzeitliste lief durch). Im laufenden Dienst `/static/THIRD-PARTY-NOTICES.txt`: alle 14 Zeilen von `@xyflow/react 13.0.2 (MIT)` bis `d3-zoom 3.0.1 (ISC)` vorhanden, 28 Abschnitte |
| 4 | erfüllt: `pull e2e`, `npm ci` („added 445 packages“), `up -d --wait` (alle healthy), „Create test account“ wie in `ci.yml` („Created account 'e2e-manager' …“), `D --profile e2e run --rm e2e`: „17 passed“, darunter `map.spec.ts`. Zweiter Lauf ohne `down -v`: „Updated account …“, „17 passed“ |
| 5 | erfüllt: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` Exit 0; danach kein Container, Volume oder Netz mit `twox-039` (die gebauten Images bleiben) |

**Vitest neu:** `pages/map/graph.test.ts` (32 Fälle: Netzbildung IPv4/IPv6 einschließlich IPv4-Anteil und ungültiger Werte, RFC-5952-Schreibweise, Gitter, Gruppen und Eltern, nur Netzkanten, Geräte ohne IP, mehrere Netze sortiert, Leerfall, Determinismus mit vier gemischten Eingabereihenfolgen, Signatur, größere Struktur ohne Überlappung und innerhalb der Eltern, Suche, Hervorhebung) und `pages/map/MapPage.test.tsx` (11 Fälle: Rolle `read` sieht Karte, Beschriftungen, Netz und Steuerelemente; Navigationseintrag; Klick und Enter auf ein Gerät öffnen die Geräteseite; Enter auf einer Gruppe nicht; Fokus hebt Gerät und Netz hervor; Suche markiert Treffer und zählt; Netze aus- und einblenden; Leerzustand mit Link; API-Fehler; Deutsch). Unter jsdom ersetzt der Test `ResizeObserver`, `DOMMatrixReadOnly`, `offsetWidth`/`offsetHeight` und `getBBox` (wie in den Testhinweisen von React Flow) und stellt sie danach wieder her.

**Playwright neu:** `web/e2e/map.spec.ts`: Struktur mit `testName()`/`testIp()` über die API, zweites Gerät ohne IP; über die Navigation zu `/map`; Netz-Knoten `192.0.2.0/24` sichtbar; Suche nach Kennung → „1 match“, Gerät im Sichtbereich, markiert, mit Name/Kennung/IP/Modell, genau eine hervorgehobene Netzkante; Gerät ohne IP → keine; Suche nach IP; Netze aus- und einblenden; Klick → Geräteseite; zurück, Fokus und Enter → Geräteseite; keine Konsolenfehler.

**Backend-Prüfungen** (wegen `backend/Dockerfile`, wie im CI-Job `backend`, mit `D`, nach Neuschreiben der `.env`): `ruff check` („All checks passed!“), `ruff format --check` („131 files already formatted“), `mypy` („no issues found in 131 source files“), `pytest` („1067 passed, 4 deselected“), `pytest -m worker` („4 passed“), `makemigrations --check --dry-run` („No changes detected“), Lizenzprüfung Python („59 packages … License check passed.“), OpenAPI-Schema neu erzeugt und `git diff --exit-code -- web/openapi` ohne Unterschied. Alle Exit 0.

**Plausibilität mit den Daten der Testfabrik** (ohne Screenshot): `testfactory/layout/devices.csv` mit `import_devices … --user e2e-manager --commit` in `twox-039` geladen („sites: 1 created, areas: 3, plants: 10, devices: 13“). Die vier Listen des Standorts „Testfabrik“ über die Serializer der API ausgegeben und mit `buildMapGraph` umgerechnet (Wegwerf-Test, nicht committet):
- **28 Knoten** (1 Standort, 3 Bereiche, 10 Anlagen, 13 Geräte, 1 Netz `192.168.0.0/24` mit 7 Geräten) und **7 Kanten**. Die sechs Geräte ohne Adresse (vier TXT-Controller, UR5e, Firewall) haben keine Kante; die Ladestation erscheint als leere Anlage.
- **Keine Überlappung** zwischen Geschwistern, kein Kind ragt aus seiner Gruppe (je 0 Befunde); umgekehrte Eingabereihenfolge ergibt dieselbe Signatur.
- Gesamtfläche 1952 × 1084 (Fertigungslinie 1292 × 752 mit 8 Anlagen in 3 Spalten, Netzübergang und Roboterzelle je 284 × 248, Netz-Spalte rechts). „Ansicht einpassen“ zeigt alles bei etwa halber Größe; zum Lesen der Gerätetexte zoomt man hinein oder nutzt die Suche.

### Zweig und Arbeitsverzeichnis

Zweig `worktree-agent-a377eae3e43b568ed`, Arbeitsverzeichnis `.claude/worktrees/agent-a377eae3e43b568ed`. Nicht gepusht, nicht zusammengeführt.

### Abweichungen und Hinweise

1. **Version 13.0.2 statt 12.12.1 (Hinweis an a7):** 13.0.2 ist die aktuelle Version (`latest`), aber die Hauptversion 13.0.0 erschien erst am 16.11.2026, mit zwei kleinen Korrekturen bis zum 17.11. (laut Changelog nur die Ansage beim Verschieben per Tastatur, die Ebene der Kanten-Werkzeugleiste und die README). Die genutzten Schnittstellen (`ReactFlow`, `MiniMap`, `Controls`, `Background`, `parentId`, `extent`, `fitView`, `onNodeClick`, `ariaLabelConfig`) sind in 13 unverändert. 12.12.1 (2.11.2026) wäre die reifere Linie mit zustand 4 und use-sync-external-store statt zustand 5 und react-compiler-runtime. Ein Wechsel wäre ein kleiner eigener Auftrag.
2. **Dateien außerhalb der genannten Liste:**
   - `web/src/i18next.d.ts`: Typen des neuen Namensraums, nötig für die Typprüfung.
   - `web/src/i18n.test.ts`: erwartet jetzt 9 statt 8 Namensräume.
   - `web/src/session.test.tsx`: Listen der Navigationseinträge je Rolle um „Map“/„Landkarte“ ergänzt.
   - `web/src/pages/README.md`, `web/src/locales/README.md`: Doku.
   - Der Seitentest liegt unter `pages/map/MapPage.test.tsx` (im Auftrag: Tests in `pages/map/`).
3. **„Auswahl“ und Klick:** Ein Klick öffnet sofort die Geräteseite (wie verlangt). Hervorgehoben wird deshalb, was ausgewählt (Leertaste, Auswahlrahmen mit Umschalt), per Tastatur fokussiert oder gefunden ist.
4. **Kanten kreuzen Gruppen:** Die Netz-Spalte steht rechts neben allen Standorten. Die Linien von der Fertigungslinie zum Netz laufen deshalb über die Gruppe „Netzübergang“. Lesbar, aber nicht kreuzungsfrei; eine bessere Führung wäre Sache von M7.
5. **Bündel:** Hauptbündel `index-….js` 505,34 kB (gzip 153,78 kB; laut 036 vorher knapp unter 500 kB, gewachsen durch Texte und Navigation), CSS 19,73 kB. Kartenseite als eigenes Stück: `MapPage-….js` 260,05 kB (gzip 89,31 kB), `MapPage-….css` 15,99 kB. Vite warnt jetzt über 500 kB (zulässig) und meldet, dass die Anweisung `"use no memo"` in `react-compiler-runtime` beim Bündeln nicht erhalten bleibt; sie richtet sich nur an den React Compiler, den das Projekt nicht nutzt.
6. **`.env` im Arbeitsverzeichnis war veraltet** (ohne `TWOX_CACHE_URL`, `TWOX_MEDIA_ROOT`, `TWOX_UPLOAD_MAX_BYTES`, `TWOX_E2E_*`). Ich habe sie aus `.env.example` neu geschrieben (ohne BOM, Port 18039) und die Dienste neu gestartet; die Backend-Prüfungen liefen danach ein zweites Mal.
7. Die Testfabrik-Daten lagen nur in der Datenbank von `twox-039` und sind mit `down -v` entfernt.
8. Der Eintrag in `docs/DECISIONS.md` (Abhängigkeitstabelle) bleibt der Leitstelle.
