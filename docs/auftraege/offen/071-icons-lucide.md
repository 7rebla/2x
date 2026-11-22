# Auftrag 071 – Icon-Schicht mit Lucide für Navigation, Aktionen, Status und Struktur

Meilenstein: Gestaltung (D1, parallel zu M2) · Freigabestufe: C · Status: zur Prüfung

## Ziel

Eine zentrale, typisierte Icon-Schicht in der Oberfläche und die ersten Icons aus Lucide (`lucide-react`) für Navigation, wiederkehrende Aktionen, Statusanzeigen und die Struktur-Ebenen. Grundlage ist die Bedarfsanalyse `docs/design/icon-bedarfsanalyse.md` (P0-Satz ohne Marke und ohne eigene Geräteklassen-Icons).

## Umfang

- Abhängigkeit `lucide-react`: Version exakt festlegen; Lizenz (ISC) und mitgezogene Pakete an der Quelle prüfen; Laufzeitliste und `THIRD-PARTY-NOTICES.txt` in Stufe `web-build` von `backend/Dockerfile` nachziehen. Nur benannte Einzelimporte (Tree-Shaking), kein dynamisches Laden aller Icons.
- `web/src/icons/` (neu): `Icon`-Komponente mit festen Größen 16/20/24 px, `currentColor`, Strichstärke einheitlich; dekorativ `aria-hidden`, bedeutungstragend mit `aria-label` (Pflicht über den Typ). Ein Namens-Mapping `IconName → Komponente` als einzige Stelle, an der Lucide importiert wird (später ergänzt um eigene Industrie-Icons).
- Einsatz (P0 laut Bedarfsanalyse, H5; IDs NAV-, OBJ-, ACT-, STA-):
  - Navigation: Struktur, Landkarte, Import, Änderungsprotokoll, Selbsttest, Einstellungen (falls 070 schon auf main), Benutzermenü/Abmelden.
  - Struktur-Ebenen im Baum, in Brotkrumen und auf der Landkarte: Standort, Bereich, Anlage, generisches Gerät, Netz; Dokument/Datei, Version.
  - Aktionen: Anlegen, Bearbeiten, Hochladen, Herunterladen, Suchen, Filtern/Zurücksetzen, Ansicht einpassen, Netze ein/aus.
  - Status: Erfolg, Warnung, Fehler, Info, Laden – immer zusammen mit Text, nie nur Farbe.
- Aktiver Navigationspunkt per dezentem Hintergrund statt gefülltem Icon.
- Tests: Vitest für das Mapping (jeder Name rendert ein SVG, `aria-hidden`/`aria-label` korrekt), Snapshot-freie Prüfungen; bestehende Tests anpassen. Playwright: Navigation zeigt Icons mit verborgenem SVG und lesbarem Text.

## Nicht-Ziele

- Eigene Industrie-Icons je Geräteklasse (SPS, Router, Roboter …): brauchen ein Typfeld am Gerät (eigener Auftrag, Datenmodell, Stufe C) und die freigegebenen Entwürfe.
- Logo und Favicon (Auftrag 072). Online/Offline-Status (es gibt kein Monitoring).

## Betroffene Bereiche (Ordner, Dateien)

- `web/package.json`, `web/package-lock.json`, `backend/Dockerfile` (nur Stufe `web-build`)
- `web/src/icons/` (neu), `web/src/components/` (Layout, Navigation, Benutzermenü, Lade-/Fehleranzeigen), `web/src/pages/` (Struktur, Gerät, Datei, Import, Protokoll, Landkarte-Knoten)
- `web/src/navigation.ts` (Icon-Feld je Eintrag), betroffene Tests, `web/e2e/navigation.spec.ts`

## Akzeptanzkriterien (prüfbar)

`W` = `docker compose -p twox-071-web -f deploy/compose/compose.web.yaml`, `D` = `docker compose -p twox-071`, `.env` mit `TWOX_API_PORT=18071`.

0. `docker version` und `docker compose version` enden mit Exit 0.
1. `W --profile dev build web-dev`, `npm ci`, `lint`, `typecheck`, `test`, `build`, `licenses` je Exit 0.
2. `git grep -n "lucide-react" -- web/src` findet Importe nur in `web/src/icons/`.
3. `D --profile dev build migrate api worker web-dev` Exit 0; `THIRD-PARTY-NOTICES.txt` enthält `lucide-react` mit ISC-Text.
4. Browser-Test wie in `ci.yml` (inkl. „Create test account“) bestanden, zweimal ohne `down -v`.
5. Bündelgröße im Kurzbericht (vorher/nachher).
6. Abräumen mit `down -v` endet mit Exit 0.

## Vorgaben und Hinweise

- **Nachtrag der Leitstelle (Rückmeldung a7, 22.11.2026):** Die Kopfzeile bricht heute um (englisch „Self-test" in zweiter Zeile, deutsch schlimmer, der Kopf springt beim Sprachwechsel). In diesem Auftrag beheben: Kopfzeile in Deutsch und Englisch einzeilig, kein Springen beim Sprachwechsel; Sprachumschalter aus der Kopfzeile ins Benutzermenü/die Einstellungen (auf der Anmeldeseite bleibt er), Angaben zu Konto und Rolle kompakt im Benutzermenü; unter ca. 1024 px Navigationspunkte als Icon mit zugänglichem Namen. Markenbereich links (072) nicht anfassen. Playwright bei 1280 und 1024 px Breite je Sprache: Navigationspunkte auf einer Zeile, gleiche Kopfhöhe; bei 375 px bedienbar ohne horizontales Scrollen der Seite.

Voraussetzung: Auftrag 070 ist auf `main` (Tokens, Farben über `currentColor`); a7 hat Frage 1 beantwortet.

- Icon-Größen und Strich nach `docs/design/icon-bedarfsanalyse.md`, Teil F. Lokale, ungetrackte Design-Vorlagen unter `docs/design/bildmarke/` nicht ins Repository übernehmen und nicht nennen; dort vorkommende Produktnamen nie in Code, Commits oder Kurzbericht.
- Sprache: Code Englisch, Kurzbericht Deutsch. Keine Personennamen, keine lokalen Pfade mit Benutzernamen. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Empfehlungen übernommen (E-50 bis E-52).

1. **Lucide (`lucide-react`, ISC) als Icon-Bibliothek zulassen?** (a) Ja; (b) eigene SVGs ohne Bibliothek. Empfehlung: (a) – laut Design-Übergabe bereits akzeptiert; ISC ist nach E-23 zulässig.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Kriterien 0–6 sind erfüllt; alle Läufe am 22.11.2026 im Container (Docker Engine 29.9.3, Compose v5.7.0). Enthalten ist der Zusatz von a7 (einzeilige Kopfzeile, Benutzermenü). Keine offene Frage, die die Arbeit aufhält; Hinweise unter „Abweichungen“.

### Neues Paket (an der npm-Registry und im Paket geprüft)

`lucide-react` **1.77.0**, exakt festgelegt (`web/package.json`). Registry: Lizenz ISC, Repository `github.com/lucide-icons/lucide`, veröffentlicht am 20.11.2026, `latest` = 1.77.0. **Keine Abhängigkeiten** (nur optionale Peers `react` und `@types/react`, beide schon vorhanden); `npm install` meldete „added 1 package“. Die Lizenzdatei im Paket enthält den ISC-Text („Lucide Icons and Contributors“) und für die aus Feather übernommenen Icons den MIT-Text („Cole Bemis“); beides steht unverändert in `THIRD-PARTY-NOTICES.txt`. Im ausgelieferten Code des Pakets kein `fetch`, `XMLHttpRequest`, `sendBeacon`, `WebSocket` oder `EventSource`. `npm run licenses`: „423 packages … License check passed.“ ohne Änderung der Regeln. Der Eintrag in `docs/DECISIONS.md` (Abhängigkeitstabelle) bleibt der Leitstelle.

### Was wurde gebaut?

- **Icon-Schicht `web/src/icons/`:**
  - `names.ts`: Tabelle `IconName → Zeichnung`, die einzige Stelle mit Importen aus `lucide-react` (nur benannte Einzelimporte, Lucides aktuelle Namen ohne veraltete Aliase). 33 Namen mit den IDs der Bedarfsanalyse (H2): Navigation (`structure`, `map`, `import`, `audit`, `selftest`, `settings`, `user`), Objekte (`site`, `area`, `plant`, `device`, `network`, `document`, `version`), Aktionen (`create`, `edit`, `upload`, `download`, `retry`, `apply`, `filter`, `resetFilter`, `search`, `fitView`, `previous`, `next`, `signOut`), Status (`success`, `error`, `warning`, `loading`, `noPermission`, `info`).
  - `Icon.tsx`: Größen 16/20/24 (Standard 16), Strich einheitlich 2 Einheiten im 24er-Raster (skaliert mit), Farbe nur `currentColor`. Der Typ verlangt genau eins von `decorative` (dann `aria-hidden`) oder `label` (dann `role="img"` mit `aria-label`).
  - `glyph.tsx`: Vertrag `GlyphProps`/`Glyph` für jede Zeichnung und der Rahmen `SvgGlyph` für eigene Icons (viewBox 0 0 24 24, kein Füllen, Strich `currentColor`, runde Enden). Für 074: eigene Komponenten auf `SvgGlyph` kommen gleichberechtigt in dieselbe Tabelle; die Zuordnung `device_class → IconName` gehört neben `pages/structure/deviceClass.ts` (steht in `icons/README.md`).
  - `README.md` (Regeln, Namen, eigene Zeichnungen, Lizenz).
- **Navigation:** `navigation.ts` hat je Eintrag ein Feld `icon`. Im Kopf steht je Eintrag Icon (20 px, verborgen) plus Text; der aktive Punkt bekommt zusätzlich zur Linie (Muster C) einen dezenten Hintergrund (`accent-soft`), das Icon bleibt Outline. Die Breitenreservierung des fetten Texts sitzt jetzt auf `.nav-label` (`index.css`).
- **Zusatz von a7 – Kopf einzeilig:** Navigation und Einträge brechen nie um (`white-space: nowrap`, `w-max`). Unter 1024 px zeigt jeder Eintrag nur das Icon; der Text bleibt als zugänglicher Name (`max-lg:sr-only`) und als Tooltip (`title`). Reicht auch das nicht (375 px), scrollt nur die Navigation waagrecht, nie die Seite. Der Sprachumschalter steht nach der Anmeldung nicht mehr im Kopf, sondern im **Benutzermenü** (und weiter auf der Einstellungsseite); vor der Anmeldung bleibt er im Kopf. Das Benutzermenü (`UserMenu.tsx`) ist ein Knopf mit Personen-Icon und Benutzername (unter 640 px nur Icon; Name „Account menu: …“/„Benutzermenü: …“); er öffnet ein Feld mit „Angemeldet als“, Rolle, Link zu den Einstellungen, Sprache und „Abmelden“. Es schließt mit Escape (Fokus zurück auf den Knopf), mit Klick außerhalb und bei jedem Adresswechsel. Der Markenbereich links (`<h1>` mit Link) ist unverändert.
- **Struktur-Ebenen:** Baum (Art-Beschriftung mit Icon für Standort, Bereich, Anlage, Gerät), Brotkrumen der Geräteseite (Struktur, Standort, Bereich, Anlage, Gerät), Landkarten-Knoten (Gruppen, Gerät, Netz), Dateiliste und Dateiseite (Dokument, Version, Gerät).
- **Aktionen:** Anlegen und Bearbeiten (Struktur, Geräteseite), Hochladen (Upload-Formulare, Import „Prüfen“), Übernehmen (Import), Herunterladen, Suchen (Struktur, Landkarte), Filtern/Zurücksetzen (Protokoll), Blättern, Erneut prüfen (Selbsttest), Abmelden, „Netze anzeigen“ mit Netz-Icon, **„Ansicht einpassen“** als Knopf mit Icon über der Karte (der gleichnamige Knopf in der Steuerleiste von React Flow ist abgeschaltet, damit es nur einen gibt).
- **Status, immer mit Text:** Erfolg, Warnung, Fehler (Upload, Import, Formulare, `ErrorMessage`, Selbsttest-Karten und -Fehler, Abmelde-Fehler), Kein Zugriff (403 und Hinweis „keine Berechtigung“), Hinweis „keine Rolle“ (Warnung), Laden (drehendes Icon in `Loading` und im Selbsttest; steht bei „Bewegung reduzieren“ still).
- **`backend/Dockerfile`, Stufe `web-build`:** Laufzeitliste um `lucide-react` ergänzt, Hinweis-Schleife um `lucide-react`, Kommentar angepasst.
- **Doku:** `web/src/icons/README.md` (neu), `web/src/pages/README.md` (Kopf, Benutzermenü), `web/src/theme/README.md` (Sprachumschalter, Muster C), `README.md` (ein Satz zum Sprachumschalter).

### Wie wurde getestet?

`W` = `docker compose -p twox-071-web -f deploy/compose/compose.web.yaml`, `D` = `docker compose -p twox-071`; `.env` aus `.env.example` (ohne BOM) mit `TWOX_API_PORT=18071`. Die Umgebungen „2x“ und „twox-leit“ wurden nicht berührt.

| AK | Ergebnis |
| --- | --- |
| 0 | erfüllt: `docker version` (Server 29.9.3), `docker compose version` (v5.7.0), je Exit 0 |
| 1 | erfüllt: `W --profile dev build web-dev`, `npm ci` („added 445 packages“, vor dem neuen Paket), `lint` und `typecheck` ohne Meldung, `test`: 31 Dateien, 508 Fälle bestanden, `build` Exit 0, `licenses`: „423 packages … License check passed.“; zusätzlich `api:generate` und `git diff --exit-code -- web/openapi web/src/api` ohne Unterschied |
| 2 | erfüllt: `git grep -n "lucide-react" -- web/src` findet nur `web/src/icons/names.ts:44` (Import) und zwei Erwähnungen in `web/src/icons/README.md` |
| 3 | erfüllt: `D --profile dev build migrate api worker web-dev backend-dev` Exit 0 (Prüfung der Laufzeitliste lief durch). Im laufenden Dienst enthält `/static/THIRD-PARTY-NOTICES.txt` den Abschnitt „lucide-react 1.77.0 (ISC)“ mit „ISC License … Lucide Icons and Contributors“ und dem MIT-Teil |
| 4 | erfüllt: `pull e2e`, `npm ci`, `up -d --wait` (alle healthy), „Create test account“ wie in `ci.yml` (Kennwort nur als Variablenname). **Erster Lauf: 31 bestanden, 3 fehlgeschlagen** (siehe Abweichung 2); nach der Korrektur und Neubau zweiter Lauf ohne `down -v`: „Updated account …“, **34 passed**; nach dem letzten Code-Commit dritter Lauf ohne `down -v`: **34 passed** |
| 5 | Bündelgröße siehe unten |
| 6 | erfüllt: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` je Exit 0; danach kein Container, Volume oder Netz mit `twox-071` (die gebauten Images bleiben) |

**Backend-Prüfungen** (wegen `backend/Dockerfile`, wie im CI-Job `backend`, mit `D`): `ruff check` („All checks passed!“), `ruff format --check` („137 files already formatted“), `mypy` („no issues found in 137 source files“), `pytest` („1173 passed, 4 deselected“), `pytest -m worker` („4 passed“), `makemessages` mit `git diff` auf `backend/locale` ohne Unterschied, `makemigrations --check --dry-run` („No changes detected“), Lizenzprüfung Python („60 packages … License check passed.“), OpenAPI-Schema neu erzeugt und `git diff --exit-code -- web/openapi` ohne Unterschied. Alle Exit 0.

**Vitest neu:** `icons/icons.test.tsx` (43 Fälle: jeder Name rendert ein SVG mit viewBox 0 0 24 24, `stroke="currentColor"`, `fill="none"`, Strich 2, ohne eigene Farben oder `style`; alle Zeichnungen verschieden; `decorative` → `aria-hidden`, `label` → `role="img"` mit Namen; Größen 16/20/24; `@ts-expect-error` für fehlende/doppelte Bedeutung und unbekannte Namen; `SvgGlyph` hält dieselben Regeln). `components/Layout.test.tsx` (9 Fälle: jeder Navigationseintrag mit eigenem, bekanntem Icon, verborgenem SVG, lesbarem Namen, Tooltip und `max-lg:sr-only`; aktiver Eintrag ohne gefülltes Icon; Benutzermenü geschlossen/offen, Escape mit Fokus zurück, Klick außen, Sprachwechsel aus dem Menü; Sprachumschalter vor der Anmeldung im Kopf). Ergänzt: `SelftestPage.test.tsx` (Status mit Icon und Text), `map/MapPage.test.tsx` (Icons der Knoten, „Ansicht einpassen“ mit Icon), `theme/contrast.test.ts` (Paar `accent` auf `accent-soft`, 3:1, für die Linie des aktiven Eintrags; besteht in allen Akzenten und beiden Modi). Angepasst: `session.test.tsx` und `SettingsPage.test.tsx` öffnen das Benutzermenü vor „Abmelden“ bzw. „Einstellungen“ (Hilfsfunktion `openUserMenu()` in `test/renderApp.tsx`).

**Playwright neu** (`web/e2e/navigation.spec.ts`): alle Einträge mit sichtbarem, `aria-hidden` SVG und lesbarem Text; bei **1280×800 und 1024×768**, je Englisch und Deutsch (Wechsel über das Benutzermenü): alle Einträge mit gleichem `top`, alle Texte sichtbar, kein Scrollen in der Navigation, Kopfhöhe und `top` in beiden Sprachen gleich; bei **375×812**: Einträge auf einer Zeile, keine waagrechte Scrollbarkeit der Seite, Tooltip und Icon vorhanden, Klick auf „Self-test“ (nur Icon sichtbar) führt zur Seite, das Benutzermenü öffnet sich innerhalb des Bildschirms. Angepasst: `login.spec.ts` (Abmelden über das Menü), `settings.spec.ts` (Einstellungen und Sprachumschalter über das Menü), `i18n.spec.ts` (Sprachumschalter über das Menü).

**Bündelgröße** (`npm run build`, vorher `web/dist` gelöscht): vorher `index-….js` 527,98 kB (gzip 159,68 kB), `index-….css` 25,81 kB (gzip 6,19 kB); nachher `index-….js` 544,69 kB (gzip 165,24 kB), `index-….css` 27,35 kB (gzip 6,47 kB). Kartenteil `MapPage-….js` 260,22 → 260,97 kB, `MapPage-….css` unverändert 15,99 kB, `index.html` unverändert 1,63 kB. Stichprobe im Bündel: `list-tree` (genutzt) enthalten, `accessibility` (nicht genutzt) nicht – das Tree-Shaking greift.

### Zweig und Arbeitsverzeichnis

Zweig `worktree-agent-a3629edcd078dc797`, Arbeitsverzeichnis `.claude/worktrees/agent-a3629edcd078dc797`. Nicht gepusht, nicht zusammengeführt.

### Abweichungen und Hinweise

1. **Zusatz von a7 umgesetzt (über den ursprünglichen Umfang hinaus):** Benutzermenü als aufklappbares Feld statt Zeile im Kopf; Sprachumschalter nach der Anmeldung im Menü. Kopf und Menü sind Teil von `Layout.tsx`/`UserMenu.tsx`; der Markenbereich (`<h1>`) ist textlich unverändert, die umschließende Zeile (`div` mit den Kopf-Klassen) hat neue Klassen (`flex-wrap`, `gap-y-4` entfallen, `gap-x-6`). Beim Zusammenführen mit 072 kann es dort einen kleinen Konflikt geben.
2. **Erster Browser-Lauf rot (3 Fälle):** `audit.spec.ts` und `m1-acceptance.spec.ts` suchen das Filterfeld mit `getByLabel("User")`, das auch den Menüknopf „User menu: …“ traf; `i18n.spec.ts` nutzte den Sprachumschalter im Kopf. Korrektur: englischer Name des Menüs „Account menu“ (deutsch unverändert „Benutzermenü“), `i18n.spec.ts` öffnet das Menü. Danach zweimal grün.
3. **Dateien außerhalb der genannten Liste:** `web/src/index.css` (Muster C mit Icon und aktivem Hintergrund), `web/src/locales/{de,en}/auth.json` (Text `userMenu`), `web/src/theme/contrast.test.ts`, `web/src/test/renderApp.tsx`, `web/src/session.test.tsx`, `web/src/pages/SettingsPage.test.tsx`, `web/src/pages/SelftestPage.test.tsx`, `web/src/pages/map/MapPage.test.tsx`, `web/src/pages/structure/forms.tsx` (Fehlerhinweis), `web/e2e/login.spec.ts`, `web/e2e/settings.spec.ts`, `web/e2e/i18n.spec.ts`, Doku `web/src/pages/README.md`, `web/src/theme/README.md`, `README.md`.
4. **Icon-Wahl (Vorschlag, leicht änderbar in `names.ts`):** Struktur `ListTree`, Landkarte `Map`, Import `Import`, Protokoll `RotateCcwClock` (früher „History“), Selbsttest `Activity`, Standort `MapPin`, Bereich `LayoutGrid`, Anlage `Factory`, Gerät `Cpu`, Netz `Network`, Version `GitCommitVertical`, Ansicht einpassen `Scan`. Für OBJ-03 (Anlage), OBJ-04 (Gerät), NAV-09 (Landkarte) und OBJ-11 (Netz) sieht die Analyse eigene Entwürfe vor; bis dahin stehen Bibliotheks-Icons.
5. **Version 1.77.0:** Lucide veröffentlicht fast täglich eine Nebenversion (1.73 bis 1.77 zwischen 14. und 20.11.2026). Die eigene Namensschicht fängt Umbenennungen ab; ein Update ändert nur `package.json` und den Lock (die Laufzeitliste im Dockerfile nennt keine Versionen).
6. **Tooltip auch bei voller Breite:** `title` steht immer am Navigationslink (auch wenn der Text sichtbar ist), weil CSS ihn nicht nur unter 1024 px setzen kann.
7. Der Eintrag in `docs/DECISIONS.md` (Abhängigkeitstabelle) und die Pflege von `docs/STATUS.md` bleiben der Leitstelle.
