# Auftrag 070 – Theme, Schrift, Text-Animationen und Einstellungsseite

Meilenstein: Gestaltung (D1, parallel zu M2) · Freigabestufe: C · Status: zur Prüfung

## Ziel

Die Oberfläche bekommt ein zentrales Farb- und Schriftsystem: hell, dunkel und „wie System“, eine vom Benutzer wählbare Akzentfarbe (Standard Aubergine), Inter als UI-Schrift (lokal, ohne CDN), dezente Text-Animationen und eine Seite „Einstellungen“. Grundlage sind die von a7 ausgewählten Design-Vorlagen; es wird nichts neu gestaltet.

## Umfang

- **Theme-Tokens** zentral als CSS-Variablen in `web/src/index.css` und über Tailwind 4 (`@theme`) nutzbar: Hintergrund, Fläche, Text, gedämpfter Text, Rand, Akzent, Akzent-Text, Fokusring; Statusfarben (Erfolg, Warnung, Fehler, Info) **getrennt** vom Akzent und unabhängig von der Akzentwahl. Keine festen Farbwerte mehr in Komponenten: alle heutigen Tailwind-Farbklassen (z. B. `bg-slate-…`, `text-gray-…`) auf die Tokens umstellen.
- **Vorläufige Palette** (Werte dürfen nach Kontrastmessung angepasst werden, Abweichungen im Kurzbericht): Akzent `#765477`, heller Akzent `#A98BAD` (im Dunkelmodus als Akzent `#B496B8`), dunkler Akzent `#49334F`; Dunkel-Hintergrund `#19171D`, Dunkel-Fläche `#25212A`; Hell-Hintergrund `#F8F6F9`. Dunkelmodus überwiegend neutrales Anthrazit mit sparsamem Akzent, keine violetten Flächen. **Kein Petrol/Türkis.**
- **Modus:** hell / dunkel / System (Standard: System). Umschalten ohne Neuladen und ohne Aufblitzen der falschen Farbe beim Laden (kleines Inline-Skript in `index.html` setzt `data-theme` vor dem ersten Zeichnen; CSP-verträglich, keine externen Quellen).
- **Akzentfarbe:** Auswahl aus 5–6 vorgegebenen Akzenten (Aubergine Standard; weitere ruhige Töne, kein Petrol/Türkis), jeweils mit geprüftem Kontrast in hell und dunkel. Keine freie Farbwahl.
- **Kontraste messen:** Text auf Hintergrund und Fläche mindestens WCAG AA (4,5:1, große Schrift 3:1), Akzent-Text auf Akzent ebenfalls; Fokusring sichtbar (3:1). Messung als Vitest-Test über die Token-Werte (kleine eigene Kontrastfunktion, keine Bibliothek).
- **Schrift Inter:** Datei `InterVariable.woff2` (Version 4.1, SIL OFL 1.1) **unverändert** übernehmen nach `web/src/assets/fonts/inter/` samt `LICENSE.txt`; einbinden per `@font-face` mit `font-display: swap`. Quelle für die Datei: der lokale Design-Ordner der Leitstelle (siehe Vorgaben). `font-feature-settings`: `ss02` (unterscheidet I/l/1) standardmäßig an. Kennungen, IP-Adressen, Versionen und Zahlenspalten mit `font-variant-numeric: tabular-nums slashed-zero` in der UI-Schrift statt `font-mono`; Monospace nur noch für Prüfsummen. Hinweis in `THIRD-PARTY-NOTICES.txt` (Stufe `web-build` im `backend/Dockerfile`) ergänzen.
- **Text-Animationen** in reinem CSS (keine Bibliothek), nach den vier Mustern der Vorlage: A wortweises Aufklaren für Seitenüberschriften (kleine typisierte React-Komponente zerlegt die Überschrift in Wörter), B Zeilenmaske für Seitentitel/Gerätekopf, C Navigationslinie (Unterstrich wächst; Breite des aktiven Punkts per unsichtbarem fettem Doppelgänger reserviert – behebt das heutige Springen der Navigation), D Lade-Schimmer für Ladezustände. Nur `opacity`, `transform`, `filter`, `background-position`, `background-size` animieren. Bei `prefers-reduced-motion: reduce` keine Animation und kein Übergang.
- **Seite „Einstellungen“** unter `/settings` (Rolle `read` genügt) mit Navigationseintrag bzw. Zugang über das Benutzermenü: Darstellung (System/hell/dunkel), Akzentfarbe (Vorschau-Kacheln), Sprache (Deutsch/Englisch – der vorhandene Umschalter bleibt im Kopf, beide wirken auf dieselbe Einstellung), Bewegung reduzieren (zusätzlich zur Systemeinstellung). Gespeichert im Browser (`localStorage`, Schlüssel unter `twox.`), in `try/catch`; ohne Speicher funktioniert alles mit Standardwerten.
- Texte de/en in einer neuen Locale-Datei `settings.json`.
- **Tests:** Vitest für Theme-Auflösung (System/hell/dunkel, gespeicherte Wahl, kaputter Speicher), Akzentwahl, Kontrast aller Kombinationen, reduzierte Bewegung (keine Animationsklassen); Playwright: Einstellungen ändern → `data-theme`/Akzent am `<html>` gesetzt, bleibt nach Neuladen; Dunkelmodus per `colorScheme: 'dark'` des Browser-Kontexts als System-Standard.

## Nicht-Ziele

- Logo, Favicon, Wortmarke (Auftrag 072), Icons (Auftrag 071).
- Einstellungen auf dem Server je Benutzer (später, M6).
- Beschneiden der Schriftdatei (eigener kleiner Auftrag, falls die Größe stört).
- Neue npm- oder Python-Abhängigkeiten.

## Betroffene Bereiche (Ordner, Dateien)

- `web/index.html`, `web/src/index.css`, `web/src/main.tsx`
- `web/src/theme/` (neu: Tokens, Auflösung, Speicher, Kontrast, Tests), `web/src/assets/fonts/inter/` (neu)
- `web/src/components/` (Layout, Animationskomponente, Ladeanzeige; Farbklassen in allen Komponenten und Seiten umstellen)
- `web/src/pages/SettingsPage.tsx` (neu), `web/src/routes.tsx`, `web/src/navigation.ts`, `web/src/locales/{de,en}/settings.json` (neu), `nav.json`, `web/src/i18n.ts`, `web/src/i18next.d.ts`
- `web/e2e/settings.spec.ts` (neu), betroffene bestehende Tests
- `backend/Dockerfile`, nur Stufe `web-build` (Hinweis für Inter)

## Akzeptanzkriterien (prüfbar)

`W` = `docker compose -p twox-070-web -f deploy/compose/compose.web.yaml`, `D` = `docker compose -p twox-070`, `.env` mit `TWOX_API_PORT=18070`.

0. `docker version` und `docker compose version` enden mit Exit 0.
1. `W --profile dev build web-dev`, `W run --rm web-dev npm ci`, dann `lint`, `typecheck`, `test`, `build`, `licenses` je Exit 0.
2. `W run --rm web-dev npm run api:generate`, danach `git diff --exit-code -- web/openapi web/src/api` ohne Unterschied.
3. `git grep -nE "(bg|text|border|ring|from|to|via)-(slate|gray|zinc|neutral|stone|red|green|blue|amber|yellow|teal|cyan|emerald|violet|purple)-[0-9]" -- web/src` findet nichts außer begründeten Ausnahmen, die im Kurzbericht stehen.
4. `D --profile dev build migrate api worker web-dev` Exit 0; `THIRD-PARTY-NOTICES.txt` im Image enthält Inter mit OFL-Text.
5. Browser-Test wie in `ci.yml` (inkl. „Create test account“) meldet alle Tests bestanden, auch `settings.spec.ts`; ein zweiter Lauf ohne `down -v` ebenfalls.
6. Kontrasttest (Vitest) bestanden; im Kurzbericht eine Tabelle mit den gemessenen Kontrasten je Modus und Akzent.
7. Abräumen mit `down -v` beider Projekte endet mit Exit 0.

## Vorgaben und Hinweise

Voraussetzung: a7 hat die Lizenzfrage zur Schrift (Frage 1) beantwortet; parallel laufende M2-Aufträge berühren `web/` nur in eigenen Dateien – `routes.tsx`, `navigation.ts`, `i18n.ts` nur minimal ändern.

- Design-Vorlagen der Leitstelle liegen **lokal und ungetrackt** im Hauptordner unter `docs/design/bildmarke/schrift-auswahl/` (`BEWERTUNG.md`, `vergleich.src.html` mit den vier Animationsmustern, `fonts/inter/InterVariable.woff2` und `LICENSE.txt`). Im Arbeitsverzeichnis des Bearbeiters fehlen sie (ignoriert); lies sie aus dem Hauptordner. Nur `InterVariable.woff2` und `LICENSE.txt` ins Repository übernehmen, sonst nichts aus `docs/design/bildmarke/`. Den Ordner nie committen, keine Dateinamen daraus in Commits nennen.
- In diesem Ordner und in Übergabedokumenten kommt ein künftiger Produktname vor: **Diesen Namen nie in Code, Kommentare, Tests, Commits oder den Kurzbericht schreiben.** Der Anzeigename bleibt „2x“.
- Barrierefreiheit: Bedienelemente der Einstellungen sind echte Formularelemente mit Label; Akzent-Kacheln mit zugänglichem Namen; Fokus sichtbar in allen Modi.
- Sprache: Code und Kommentare Englisch, Kurzbericht Deutsch. Keine Personennamen (a7), keine lokalen Pfade mit Benutzernamen in Dateien oder Commits. Markdown mit dem Write-Werkzeug schreiben, nicht über PowerShell-Strings.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Empfehlungen übernommen (E-50 bis E-52).

1. **Schriftlizenz SIL OFL 1.1 für Inter zulassen?** (a) Ja, als benannte Ausnahme für die unverändert ausgelieferte Schriftdatei; (b) Nein, dann Systemschriften. Empfehlung: (a) – OFL ist die übliche freie Schriftlizenz, erlaubt Weitergabe mit Lizenztext, Inter hat keinen reservierten Namen.
2. **Welche Animationsmuster?** (a) alle vier (A–D), dezent; (b) nur C und D (Navigation, Laden); (c) keine. Empfehlung: (a), mit Abschaltung über „Bewegung reduzieren“.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Kriterien 0–7 sind erfüllt; alle Läufe am 22.11.2026 im Container (Docker Engine 29.9.3, Compose v5.7.0). Keine neue npm- oder Python-Abhängigkeit. Keine offene Frage, die die Arbeit aufhält; Hinweise unter „Abweichungen“.

### Was wurde gebaut?

- **Schrift:** `web/src/assets/fonts/inter/InterVariable.woff2` und `LICENSE.txt`, unverändert aus dem Design-Ordner der Leitstelle übernommen. Prüfung gegen die Quelle: Die Git-Blob-Kennungen beider Dateien stimmen mit github.com/rsms/inter, Tag `v4.1` (Commit `e3a3d4c`), `docs/font-files/InterVariable.woff2` (352 240 Byte) und `LICENSE.txt` überein (GitHub-API, ohne Herunterladen). **SHA-256 der Schriftdatei: `693b77d4f32ee9b8bfc995589b5fad5e99adf2832738661f5402f9978429a8e3`** (Lizenztext: `262481e844521b326f5ecd053e59b98c8b2da78c8ee1bdbb6e8174305e54935a`). Eingebunden per `@font-face` mit `font-display: swap`, `ss02` für die ganze Oberfläche.
- **Theme-Tokens** in `web/src/index.css`: CSS-Variablen `--twox-*` für hell und dunkel, über `@theme inline` als Tailwind-Farben `canvas`, `surface`, `surface-muted`, `fg`, `fg-muted`, `line`, `line-strong`, `accent`, `accent-strong`, `accent-soft`, `on-accent`, `focus` sowie `success`/`warning`/`danger`/`info` je mit `-soft` und `-line`. Statusfarben hängen nicht vom Akzent ab (Test). Globaler Fokusring über `:focus-visible` im Akzent.
- **Modus und Akzent:** `<html>` trägt `data-theme` (light/dark), `data-accent` und `data-motion` (reduce/full). Ein kleines Inline-Skript im `<head>` von `web/index.html` setzt sie vor dem ersten Zeichnen (lädt nichts, kein `'unsafe-inline'` nötig; SHA-256-Hash für eine spätere CSP steht in `web/src/theme/README.md`, ein Test prüft ihn). Fünf Akzente: Aubergine (Standard), Indigo, Beere, Umbra, Graphit; kein Petrol/Türkis (Test über den Farbton).
- **Einstellungen** `web/src/theme/settings.ts` (Regeln, Schlüssel `twox.theme`, `twox.accent`, `twox.reduceMotion`, jeder Speicherzugriff in `try/catch`) und `web/src/theme/store.ts` (Live-Zustand mit `useSyncExternalStore`; folgt `prefers-color-scheme`, `prefers-reduced-motion` und Änderungen aus anderen Tabs; `installDisplaySettings()` in `main.tsx`).
- **Seite „Einstellungen“** `web/src/pages/SettingsPage.tsx` unter `/settings` (Rolle `read`, kein Eintrag in `navigation.ts`), erreichbar über den Link „Einstellungen“ im Benutzerbereich (`UserMenu.tsx`, nur mit Rolle). Darstellung (Radio-Gruppe), Akzentfarbe (Radio-Kacheln mit Namen und Vorschau über `data-accent-preview`), Sprache (Auswahlfeld, gleiche Einstellung wie der Umschalter im Kopf), „Bewegung reduzieren“ (Checkbox, mit Hinweis, wenn das System es schon verlangt). Alle Elemente sind echte Formularelemente mit Label. Texte in `locales/{de,en}/settings.json`, Seitenname `settings` in `nav.json`.
- **Text-Animationen** (reines CSS in `index.css`, nur `opacity`, `transform`, `filter`, `background-*`): `components/TextMotion.tsx` mit `AnimatedHeading` (A, alle Seitenüberschriften), `MaskedTitle` (B, Geräteseite und Dateititel), `LoadingText` (D, in `Loading` und „Wird geprüft…“ des Selbsttests); Muster C als Klasse `nav-link` mit `data-label` in `Layout.tsx` und für den Einstellungs-Link. Bei reduzierter Bewegung rendern die Komponenten keine Animationsklassen; zusätzlich schaltet `index.css` bei `prefers-reduced-motion` und `data-motion="reduce"` alle Animationen und Übergänge ab.
- **Umstellung aller Komponenten und Seiten** auf die Tokens (22 Dateien). Primäre Knöpfe `bg-accent text-on-accent`, Links im Akzent mit Unterstrich, Ränder von Eingabefeldern und Knöpfen `border-line-strong` (3:1), Meldungen in den Statusfarben. Kennungen, IP-Adressen, Softwarestände und Zahlenspalten mit `tabular-nums slashed-zero` statt `font-mono`; Monospace nur noch für die Prüfsumme (`files/parts.tsx`). Landkarte: Farben über `var(--twox-…)`, React Flow folgt dem gezeigten Modus (`forceColorMode`), eigene CSS-Variablen von React Flow auf die Tokens gesetzt.
- **Tests (Vitest, neu):** `theme/contrast.test.ts` (Kontrastfunktion, Token-Vollständigkeit, Seite = Vorschau, Statusfarben unabhängig, kein Türkis, alle 30 Paare × 2 Modi × 5 Akzente), `theme/settings.test.ts` (Auflösung System/hell/dunkel, gespeicherte Wahl, unbekannte Werte, blockierter und voller Speicher, Inline-Skript gegen `applySettings()` in 24 Kombinationen, CSP-Hash), `theme/store.test.tsx` (sofortige Anwendung, Systemwechsel, anderer Tab), `theme/sourceColours.test.ts` (keine Palettenklasse, kein fester Farbwert im Quelltext), `components/TextMotion.test.tsx` (Muster A/B/D, keine Animationsklassen bei reduzierter Bewegung durch Benutzer oder System), `pages/SettingsPage.test.tsx` (10 Fälle). Hilfe `test/fakeMatchMedia.ts`.
- **Playwright** `web/e2e/settings.spec.ts` (8 Fälle): Modus und Akzent ändern → `data-theme`/`data-accent` und Hintergrund, bleibt nach Neuladen; erste Darstellung ohne JavaScript-Bündel (Skripte blockiert) schon dunkel mit Akzent; Sprache gemeinsam mit dem Kopf-Umschalter; „Bewegung reduzieren“ → keine `tx-`-Klassen, `document.getAnimations()` leer; Inter geladen, `ss02` aktiv, keine Anfrage an fremde Hosts; Breite der Navigationspunkte bleibt beim Seitenwechsel gleich; `colorScheme: 'dark'` als System-Standard; `reducedMotion: 'reduce'` des Systems.
- **`backend/Dockerfile`, Stufe `web-build`:** prüft die SHA-256 der Schriftdatei und vergleicht sie mit der von Vite ausgegebenen Kopie; hängt den Abschnitt „Inter 4.1 (OFL-1.1)“ mit dem unveränderten Lizenztext an `THIRD-PARTY-NOTICES.txt` an.
- **Doku:** `web/src/theme/README.md` (neu: Tokens, Modi, Akzente, Kontrast, Inline-Skript mit CSP-Hash, Schrift, Animationen), `web/src/pages/README.md`, `web/src/locales/README.md`.

### Kontraste (gemessen aus `index.css`, Vitest `theme/contrast.test.ts`)

Neutrale und Statusfarben (Text mindestens 4,5:1, Rand von Bedienelementen mindestens 3:1):

| Paar | hell | dunkel |
| --- | --- | --- |
| Text auf Hintergrund / Fläche / gedämpfter Fläche | 15,94 / 17,13 / 14,79 | 14,69 / 13,05 / 11,70 |
| gedämpfter Text auf Hintergrund / Fläche / gedämpfter Fläche | 6,36 / 6,83 / 5,90 | 7,12 / 6,33 / 5,67 |
| Rand Bedienelement auf Hintergrund / Fläche / gedämpfter Fläche | 3,38 / 3,64 / 3,14 | 3,82 / 3,39 / 3,04 |
| Erfolg auf Meldungsgrund / Hintergrund | 5,95 / 6,07 | 8,71 / 10,44 |
| Warnung auf Meldungsgrund / Hintergrund | 6,89 / 6,96 | 9,13 / 10,86 |
| Fehler auf Meldungsgrund / Hintergrund | 7,40 / 7,61 | 9,05 / 10,47 |
| Info auf Meldungsgrund / Fläche | 7,20 / 8,02 | 8,93 / 9,16 |

Akzente (Akzent als Link-Text 4,5:1, Text auf Akzent 4,5:1, Fokusring 3:1):

| Modus | Akzent | Wert | Akzent auf Hintergrund | Akzent auf Fläche | Text auf Akzent | Text auf Akzent kräftig | Akzent kräftig auf Akzent zart | Text auf Akzent zart | Fokusring auf Hintergrund / Fläche |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hell | Aubergine | #765477 | 5,91 | 6,35 | 6,35 | 11,23 | 9,28 | 14,16 | 5,91 / 6,35 |
| hell | Indigo | #4f5590 | 6,44 | 6,92 | 6,92 | 11,22 | 9,29 | 14,19 | 6,44 / 6,92 |
| hell | Beere | #8c3d5e | 6,64 | 7,13 | 7,13 | 11,49 | 9,62 | 14,33 | 6,64 / 7,13 |
| hell | Umbra | #7a5236 | 6,33 | 6,80 | 6,80 | 10,89 | 9,17 | 14,42 | 6,33 / 6,80 |
| hell | Graphit | #52565e | 6,85 | 7,36 | 7,36 | 12,11 | 10,06 | 14,23 | 6,85 / 7,36 |
| dunkel | Aubergine | #b496b8 | 6,77 | 6,01 | 6,77 | 11,04 | 7,88 | 10,48 | 6,77 / 6,01 |
| dunkel | Indigo | #a6abdf | 8,05 | 7,15 | 8,05 | 11,73 | 8,77 | 10,98 | 8,05 / 7,15 |
| dunkel | Beere | #e09bb7 | 8,08 | 7,18 | 8,08 | 11,81 | 9,22 | 11,46 | 8,08 / 7,18 |
| dunkel | Umbra | #d2a684 | 8,06 | 7,17 | 8,06 | 11,73 | 8,67 | 10,86 | 8,06 / 7,17 |
| dunkel | Graphit | #b9bdc5 | 9,43 | 8,38 | 9,43 | 13,30 | 9,19 | 10,14 | 9,43 / 8,38 |

Die vorläufige Palette aus dem Auftrag ist unverändert übernommen (Aubergine hell `#765477`, dunkel `#B496B8`, kräftig `#49334F`; Hintergründe `#19171D`, `#25212A`, `#F8F6F9`); alle Paare bestehen ohne Anpassung.

### Wie wurde getestet?

`W` = `docker compose -p twox-070-web -f deploy/compose/compose.web.yaml`, `D` = `docker compose -p twox-070`; `.env` aus `.env.example` (ohne BOM) mit `TWOX_API_PORT=18070`. Die Umgebungen „2x“ und „twox-leit“ wurden nicht berührt.

| AK | Ergebnis |
| --- | --- |
| 0 | erfüllt: `docker version` (Server 29.9.3), `docker compose version` (v5.7.0), Exit 0 |
| 1 | erfüllt: `W --profile dev build web-dev`, `npm ci` („added 445 packages“), `lint`, `typecheck` ohne Meldung; `test`: 28 Dateien, 447 Fälle bestanden; `build` Exit 0; `licenses`: „422 packages … License check passed.“ |
| 2 | erfüllt: `npm run api:generate` Exit 0; `git diff --exit-code -- web/openapi web/src/api` Exit 0, `git status --porcelain` dazu leer |
| 3 | erfüllt: der `git grep` aus dem Auftrag findet nichts (Exit 1), keine Ausnahmen. Strenger prüft `theme/sourceColours.test.ts` (alle Palettennamen einschließlich `white`, `black`, `sky`, `indigo`; feste `#rgb`/`#rrggbb`/`rgb()`/`hsl()`-Werte) |
| 4 | erfüllt: `D --profile dev build migrate api worker web-dev` (dazu `backend-dev`) Exit 0. Im laufenden Dienst `/static/THIRD-PARTY-NOTICES.txt`: Abschnitt „Inter 4.1 (OFL-1.1)“, „SIL OPEN FONT LICENSE Version 1.1“ und „Copyright (c) 2016 The Inter Project Authors“ vorhanden (`True True True`); die ausgelieferte `assets/InterVariable-….woff2` hat dieselbe SHA-256 wie oben |
| 5 | erfüllt: `pull e2e`, `npm ci`, `up -d --wait` (alle healthy), „Create test account“ wie in `ci.yml` (Kennwort nur als Variablenname, „Created account …“), `D --profile e2e run --rm e2e`. Erster Lauf: 27 bestanden, `map.spec.ts` fehlgeschlagen (siehe Abweichung 3); nach der Korrektur zweiter Lauf ohne `down -v`: **28 passed**; nach dem letzten Commit Neubau, „Updated account …“, dritter Lauf ohne `down -v`: **28 passed** (darunter 8 Fälle aus `settings.spec.ts`) |
| 6 | erfüllt: `theme/contrast.test.ts` bestanden (19 Fälle), Tabelle oben |
| 7 | erfüllt: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` Exit 0; danach kein Container, Volume oder Netz mit `twox-070` |

Backend-Prüfungen wie im CI-Job `backend` (wegen `backend/Dockerfile`): `ruff check` („All checks passed!“), `ruff format --check` („134 files already formatted“), `mypy` („no issues found in 134 source files“), `pytest` („1097 passed, 4 deselected“), `pytest -m worker` („4 passed“), `makemessages` ohne Unterschied in `backend/locale`, `makemigrations --check --dry-run` („No changes detected“), Lizenzprüfung Python („License check passed.“), OpenAPI-Schema neu erzeugt ohne Unterschied. Alle Exit 0.

Sichtprüfung im eingebauten Browser (Testkonto, Port 18070): Strukturseite, Einstellungen und Landkarte im Dunkelmodus, Einstellungen hell mit Akzent Beere. Danach die `twox.*`-Schlüssel im Browser wieder entfernt.

**Bündelgröße** (`npm run build`, sauberer `dist/`): vorher `index-….js` 515,87 kB (gzip 156,37 kB), `index-….css` 20,52 kB (gzip 4,98 kB), `index.html` 0,40 kB. Nachher `index-….js` 525,82 kB (gzip 159,06 kB), `index-….css` 28,38 kB (gzip 6,61 kB), `index.html` 1,63 kB (Inline-Skript), dazu neu `InterVariable-….woff2` 352,24 kB (einmal geladen, nicht beschnitten). Kartenteil unverändert (`MapPage-….js` 260,22 kB, CSS 15,99 kB).

### Zweig und Arbeitsverzeichnis

Zweig `worktree-agent-aa54ca3b9d671892b`, Arbeitsverzeichnis `.claude/worktrees/agent-aa54ca3b9d671892b`. Sieben Commits von `8a55577` bis `8fa306b` (dazu dieser Bericht). Nicht gepusht, nicht zusammengeführt.

### Abweichungen und Hinweise

1. **Dateien außerhalb der genannten Liste:**
   - `web/vite.config.ts`: eine Zeile `test.css.include` für `src/index.css?raw`. Vitest leert CSS-Dateien sonst auch beim `?raw`-Import, und der Kontrasttest soll die echten Werte aus `index.css` lesen statt einer Kopie.
   - `web/e2e/map.spec.ts`: siehe Punkt 3.
   - `web/src/test/fakeMatchMedia.ts` (Testhilfe, jsdom hat kein `matchMedia`), `web/src/theme/cssTokens.ts` (liest die Token-Blöcke aus `index.css`, nur von Tests genutzt), `web/src/i18n.test.ts` (10 statt 9 Namensräume), `web/src/pages/README.md`, `web/src/locales/README.md`.
2. **`routes.tsx`, `navigation.ts`, `i18n.ts`:** `routes.tsx` +3 Zeilen (Import, Route), `navigation.ts` unverändert (die Seite hängt am Benutzermenü, `requiredRole` liefert `read`), `i18n.ts` nur der Namensraum `settings` (+6 Zeilen).
3. **Bestehender Browser-Test `map.spec.ts` war wackelig:** Die zufällige Test-IP (z. B. `192.0.2.24`) findet in der Suche auch längere Adressen anderer Testgeräte (`192.0.2.242`); die Karte passt sich dann auf beide Treffer ein, und das gesuchte Gerät kann unterhalb des Browserfensters liegen, obwohl es in der Karte sichtbar ist. Im ersten Lauf trat das auf. Die zweite Suche prüft jetzt „Knoten liegt innerhalb der Karte“ statt „im Browserfenster“; die erste Suche (eindeutige Kennung) prüft weiter `toBeInViewport()`. Der etwas höhere Kopf (Einstellungs-Link, Polster der Navigationslinie) macht das Auftreten wahrscheinlicher.
4. **Muster D:** Die Ladetexte der Kataloge enden mit „…“ (ein Zeichen). Statt drei einzeln blinkender Punkte pulsiert deshalb das Auslassungszeichen als Ganzes; der Text bleibt zeichengleich (Tests und Screenreader unverändert).
5. **Muster C** liegt auch auf dem Einstellungs-Link im Benutzerbereich (aktiv unterstrichen, wenn `/settings` offen ist). Die Klasse `nav-link` ist keine reine Animationsklasse und bleibt bei reduzierter Bewegung stehen; ihr Übergang wird dann per CSS abgeschaltet.
6. **Zusätzliches Token `line-strong`** für Ränder von Eingabefeldern, Auswahlfeldern und Nebenknöpfen (mindestens 3:1, WCAG 1.4.11); die Vorlage nutzt dort die schwache Linie (≈1,3:1). Links stehen wie in der Vorlage im Akzent, zusätzlich unterstrichen.
7. **Weitere Akzente** (Indigo, Beere, Umbra, Graphit) sind mein Vorschlag nach den Vorgaben (ruhig, kein Petrol/Türkis, nicht Rot/Grün/Gelb wegen der Statusfarben). a7 kann Töne oder Namen ändern; der Kontrasttest prüft jede Änderung.
8. **Schriftdatei nicht beschnitten** (Nicht-Ziel): +352 kB beim ersten Laden; `font-display: swap` zeigt bis dahin die Systemschrift.
9. **Tailwind im Container `web-dev`** sieht die `.gitignore` des Repositorys nicht (nur `web/` ist eingebunden) und durchsucht deshalb auch ein vorhandenes `web/dist/`. Ein alter Build kann so Klassen in die CSS-Datei des nächsten lokalen Builds tragen (einmal beobachtet). Das Image (`backend/Dockerfile`) baut ohne `dist/` und ist nicht betroffen; für spätere Messungen vorher `dist/` löschen.
10. **Nicht geändert:** `docs/ARCHITECTURE.md` (Zeile zur Stufe `web-build` könnte die Schriftprüfung nennen) und `README.md` – außerhalb des Bereichs. Die Leitstelle trägt Inter in `docs/DECISIONS.md` ein (Abhängigkeitstabelle).
11. Für Auftrag 071: Icons über `currentColor`; Statusfarben als `text-success`, `text-warning`, `text-danger`, `text-info` (siehe `web/src/theme/README.md`).
