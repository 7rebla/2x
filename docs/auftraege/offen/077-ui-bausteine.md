# Auftrag 077 – UI-Bausteine Knopf, Feld, Auswahl

Meilenstein: Gestaltung (D1) · Freigabestufe: B · Status: zur Prüfung

Voraussetzung: 070 und 071 sind auf `main`.

## Ziel

Die UI-Analyse (lokal, `docs/design/bildmarke/ui-analyse.md`, Befund Ü4) zeigt: Es gibt keine gemeinsamen Bausteine. Primärknöpfe gibt es in drei, Sekundärknöpfe in vier Varianten, Eingaben mit `px-2 py-1` und `px-3 py-2` gemischt, Steuerhöhen 29/30/32/34 px nebeneinander (z. B. Filterleiste im Änderungsprotokoll), `disabled:opacity-50` und `-60` gemischt. Nach diesem Auftrag gibt es kleine, typisierte Bausteine, und alle Seiten nutzen sie. Die Optik bleibt sonst gleich (Farben, Radien, Schrift aus 070).

## Umfang

- Neu unter `web/src/components/ui/`:
  - `Button` (Varianten primary/secondary/ghost/danger, Größen sm/md, optional Icon über `web/src/icons`, `type` Pflicht, Lade- und Deaktiviert-Zustand einheitlich).
  - Klassen bzw. Bausteine für `Input`, `Select`, `Textarea` (gleiche Höhe wie Button md, Fehlerzustand mit `aria-invalid`).
  - Einheitliche Steuerhöhe: md 36 px, sm 28 px; einheitlicher Deaktiviert-Zustand (Deckkraft und `cursor-not-allowed`).
- Alle Seiten und Komponenten auf die Bausteine umstellen (Knöpfe, Eingaben, Auswahlfelder), ohne Verhalten oder Texte zu ändern.
- README unter `web/src/components/ui/` (Zweck, Varianten, Beispiele); Tests je Baustein (Varianten, Zustände, Barrierefreiheit).
- Kontraste weiter über `theme/contrast.test.ts` abgedeckt (neue Farbkombinationen dort ergänzen, falls welche entstehen).

## Nicht-Ziele

- Keine Änderung an Seitenraster, Tabellenlayout, Navigation, Strukturbaum, Animationen (eigene Aufträge bzw. Entscheidungen von a7).
- `BrandMark.tsx`, `TextMotion.tsx` und die Animationsabschnitte in `index.css` nicht anfassen (Auftrag 076 läuft parallel).
- Keine neue Abhängigkeit.

## Betroffene Bereiche (Ordner, Dateien)

- neu: `web/src/components/ui/*`
- alle `web/src/pages/**/*.tsx` und `web/src/components/**/*.tsx` außer `BrandMark.tsx`, `TextMotion.tsx` (nur Austausch der Knopf-/Feldklassen gegen die Bausteine), zugehörige Tests
- `web/src/index.css` nur für Baustein-Klassen in einem eigenen Abschnitt (nicht die Animationsabschnitte)

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Web-Job aus `.github/workflows/ci.yml` grün (lint, typecheck, test, build, licenses), `api:generate` ohne Unterschied.
2. e2e wie in `ci.yml` grün.
3. Ein Suchlauf (`grep`) im Kurzbericht zeigt, dass außerhalb von `components/ui/` keine Knopf-Klassen-Kopien (`bg-accent … px-`) mehr stehen; Ausnahmen begründet.
4. Steuerhöhen im Browser gemessen (Filterleiste Änderungsprotokoll, Suche, Anmeldung): einheitlich 36 px (md).
5. `down -v` der eigenen Compose-Projekte endet mit Exit 0.

## Vorgaben und Hinweise

- Herkunft: UI-Analyse (Priorität 1), Entscheidung der Leitstelle (Stufe B, Optik bleibt gleich). Größen 36/28 px als Vorschlag der Analyse; a7 kann sie nach dem Ansehen ändern.
- Gestaltung: Tokens aus 070, Icons nur über `web/src/icons` (071).

## Fragen an a7 (mit Optionen und Empfehlung)

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Kriterien 0–5 sind erfüllt; alle Läufe am 22.11.2026 im Container (Docker Compose v5.7.0). Keine neue Abhängigkeit, `web/src/index.css` nicht angefasst (die Bausteine kommen mit Tailwind-Klassen aus, kein eigener CSS-Abschnitt nötig). `BrandMark.tsx`, `TextMotion.tsx`, Raster, Tabellen, Navigation und Strukturbaum unverändert. Keine offene Frage.

### Was wurde gebaut?

- **Neu `web/src/components/ui/`:**
  - `Button.tsx`: Varianten `primary`, `secondary` (Standard), `ghost`, `danger`; Größen `md` (36 px, Text 16 px, Icon 20 px) und `sm` (28 px, Text 14 px, Icon 16 px); `type` ist Pflicht (Typfehler sonst); `icon` über `web/src/icons` (dekorativ), `iconPosition` `start`/`end`; `loading` = deaktiviert, `aria-busy="true"`, drehendes `loading`-Icon am Anfang statt des eigenen Icons, Text bleibt der des Aufrufers; `disabled` einheitlich `opacity-50` und `cursor-not-allowed`, Hover nur im aktiven Zustand. `ref` und alle übrigen Attribute gehen an den nativen `<button>`. Jede Variante hat einen Rand (wo unsichtbar: transparent), damit alle Varianten einer Größe gleich groß sind. Höhe über `min-h-9`/`min-h-7`: eine Zeile genau 36/28 px, ein langer Text darf auf schmalen Bildschirmen umbrechen statt überzulaufen.
  - `fields.tsx`: `Input` (nur Texttypen: `text`, `search`, `password`, `email`, `url`, `tel`, `number`), `Select` (ein Wert), `Textarea`. Gleiche Höhen wie die Knöpfe (`h-9`/`h-7`), Rand `line-strong`, Fehlerzustand über `invalid` → `aria-invalid` und Rand in `danger`; Größe über `size` (ersetzt das native `size`-Attribut). Label, Hinweis und Fehlerliste bleiben beim Aufrufer (`aria-describedby`).
  - `classes.ts`: die Klassen dahinter (`buttonClasses`, `fieldClasses`, `textareaClasses`), `CONTROL_HEIGHT_PX = { md: 36, sm: 28 }`.
  - `README.md` (Zweck, Größen, Varianten, Beispiele, Kontrast, Tests).
- **Umstellung** aller Knöpfe, Eingaben und Auswahlfelder in Seiten und Komponenten (Texte, Testkennungen und Verhalten unverändert): Struktur (Neuer Standort, Zeilenaktionen `sm`, Suche), Formulare der Struktur (Felder, Speichern/Abbrechen), Geräteseite (Bearbeiten), Upload-Formulare, Import (Prüfen, Übernehmen), Einlesen (Filter, Blättern), Erneut einlesen (`sm`), Suche, Landkarte (Suche, Ansicht einpassen), Änderungsprotokoll (Filterleiste, Blättern), Selbsttest, Einstellungen (Sprache), Anmeldung, Benutzermenü (Menüknopf `ghost sm`, Abmelden `sm`), Sprachumschalter (`Select sm`), Seitenladefehler (Neu laden). Wo der Text beim Warten wechselte („Wird gespeichert…“ usw.), steht jetzt `loading`.
- **Prüfung im Quelltext** `components/ui/sourceControls.test.ts`: außerhalb von `components/ui/` kein nativer `<button>`, `<select>`, `<textarea>`; native `<input>` nur für Checkbox, Radio und Datei; keine Kopie `bg-accent … px-` und kein `disabled:opacity-*` mehr (Kommentare ausgenommen).
- **Kontrast** `theme/contrast.test.ts` um die neuen Paare ergänzt: `danger` auf `danger-line` (Text, gehoverter Gefahrknopf), `danger` als Rand auf `surface` und `canvas` (3:1). Alle Paare bestehen in beiden Modi mit allen Akzenten.
- **Doku nachgezogen:** `web/src/pages/README.md` (Regel und Beispiel mit `Button`), `web/src/theme/README.md` (Verweis), `web/src/icons/README.md` (Beispiel ohne kopierte Knopfklassen).

### Wie wurde getestet?

`W` = `docker compose -p twox-077-web -f deploy/compose/compose.web.yaml`, `D` = `docker compose -p twox-077`; `.env` aus `.env.example` (ohne BOM) mit `TWOX_API_PORT=18077`. Vor den Builds `web/dist` und `web/playwright-report` gelöscht. „2x“ und „twox-leit“ nicht berührt.

| AK | Ergebnis |
| --- | --- |
| 0 | erfüllt: `docker version` Exit 0, `docker compose version` (v5.7.0) Exit 0 |
| 1 | erfüllt: `W --profile dev build web-dev`, `npm ci` („added 446 packages“), `lint` und `typecheck` ohne Meldung, `test`: **41 Dateien, 768 Fälle bestanden** (bestehende Tests unverändert grün), `build` Exit 0, `licenses`: „License check passed.“; `api:generate` Exit 0, `git diff --exit-code -- web/openapi web/src/api` Exit 0, `git status --porcelain` dazu leer |
| 2 | erfüllt: `D --profile dev build migrate api worker web-dev`, `pull e2e`, `npm ci`, `up -d --wait` (alle healthy), „Create test account“ wie in `ci.yml` (Kennwort nur als Variablenname, „Created account …“), `D --profile e2e run --rm e2e`: **55 passed, 1 skipped** (der bedingte lokale Teil von `m2-acceptance.spec.ts`, wie bisher) |
| 3 | erfüllt, siehe Suchlauf unten |
| 4 | erfüllt, siehe Messung unten |
| 5 | erfüllt: `D --profile dev --profile e2e down -v` Exit 0, `W --profile dev down -v` Exit 0; danach kein Container, Volume oder Netz mit `twox-077` |

**Suchlauf (AK 3)** auf dem Commit-Stand:

```
git grep -nE "bg-accent( |\").*px-|disabled:opacity-|<(button|select|textarea)[ >]" -- 'web/src/*.tsx' ':!web/src/components/ui/*'
web/src/pages/structure/forms.tsx:50:   * form action, and a <select> would otherwise fall back to the option of
```

Einziger Treffer ist ein Kommentar. `git grep -nE "bg-accent( |\")"` außerhalb von `components/ui/` findet nur die Vorschau-Kachel der Akzentfarbe in `SettingsPage.tsx:107` (eine Farbfläche, kein Knopf, ohne `px-`). Strenger prüft `sourceControls.test.ts` (siehe oben). **Ausnahmen:** native Checkboxen (Einlesen „ältere Versuche“, Landkarte „Netze anzeigen“, Einstellungen „Bewegung reduzieren“), Radio-Gruppen der Einstellungen (Darstellung, Akzent-Kacheln) und Dateiauswahl (Upload, Import) behalten ihr natives Aussehen; sie sind keine Steuerfelder mit Höhe. Die Knöpfe in der Steuerleiste von React Flow (Landkarte) gehören der Bibliothek. Navigationslinks (`nav-link`) und Links sind keine Knöpfe und bleiben unverändert.

**Messung (AK 4)** im Browser (Chromium aus dem Playwright-Image des Projekts, 1280 × 800, Englisch, gegen den eigenen Dienst; Höhe aus `boundingBox()`, vorübergehende Messdatei danach gelöscht, nicht committet):

| Seite | Steuerelement | Höhe |
| --- | --- | --- |
| Änderungsprotokoll, Filterleiste | Objekttyp (Select), Benutzer (Input), „Apply filter“, „Reset filter“ | 36 / 36 / 36 / 36 px (vorher laut Analyse 29/30/32/34) |
| Änderungsprotokoll | „Previous page“, „Next page“ | 36 / 36 px |
| Suche | Suchfeld, Gerät (Select), „Search“ | 36 / 36 / 36 px |
| Anmeldung | Benutzername, Kennwort, Anmelden | 36 / 36 / 36 px (vorher 40/40/~38) |
| zusätzlich: Einlesen | Status, Gerät | 36 / 36 px |
| zusätzlich: Struktur | Suche, „New site“ | 36 / 36 px |
| Kopf (sm) | Benutzermenü, Sprachumschalter | 28 / 28 px |

Sichtprüfung der Bildschirmfotos (Änderungsprotokoll, Suche, Struktur): Felder und Knöpfe einer Zeile stehen bündig, Farben, Radien und Schrift wie zuvor.

### Zweig und Arbeitsverzeichnis

Zweig `worktree-agent-aa49c9dea9b824167`, Arbeitsverzeichnis `.claude/worktrees/agent-aa49c9dea9b824167`. Commits: Bausteine, Umstellung, dieser Bericht. Nicht gepusht, nicht zusammengeführt.

Geänderte Dateien (28): `web/src/components/ui/` 7 neu · `web/src/components/` 3 · `web/src/components/files/` 2 · `web/src/pages/` 11 (davon `README.md`) · `web/src/pages/structure/` 1 · `web/src/` 1 (`LanguageSwitch.tsx`) · `web/src/theme/` 2 (`README.md`, `contrast.test.ts`) · `web/src/icons/` 1 (`README.md`).

### Abweichungen und Hinweise

1. **Kleine sichtbare Angleichungen**, die aus der Vereinheitlichung folgen: Anmeldefelder 40 → 36 px; Sekundärknöpfe haben jetzt überall die Fläche `surface` (Blättern und Filter-Zurücksetzen standen vorher ohne Fläche auf dem Hintergrund); Felder der Protokoll-Filterleiste und der Spracheinstellung jetzt 16 px Text und Fläche `surface` (vorher 14 px, ohne Fläche); Knopf-Icons in `md` einheitlich 20 px (wie `icons/README.md` für Knöpfe vorsieht; vorher teils 16 px); „Erneut einlesen“ 12 → 14 px Text (Größe `sm`); „Ansicht einpassen“ auf der Karte 14 → 16 px (md); Abstand Icon–Name im Benutzermenü 8 → 6 px.
2. **Ladezustand:** Knöpfe, deren Text beim Warten wechselt, zeigen zusätzlich das drehende Lade-Icon (bei „Bewegung reduzieren“ steht es still). Beim Selbsttest dreht dadurch während der Prüfung auch im Knopf ein Icon, neben der Ladeanzeige im Inhalt.
3. **Ausrichtung der Checkbox-Zeilen:** Bei Einlesen („Auch ältere Versuche zeigen“) und Landkarte („Netze anzeigen“) hat die Checkbox-Zeile jetzt `min-h-9`, damit sie auf der Mittellinie der 36-px-Felder steht (vorher `py-1` bzw. ohne Höhe). Sonst keine Layoutänderung.
4. **Größen der Kopfzeile:** Benutzermenü-Knopf (`ghost sm`, 28 px wie vorher) und Sprachumschalter (`Select sm`) bleiben kompakt; „Abmelden“ im Menü ist `sm`. Wenn a7 dort `md` möchte, ist es je eine Angabe.
5. **`index.css`** nicht geändert; ein eigener Abschnitt war nicht nötig. Damit kein Berührungspunkt mit 076.
6. **Mögliche Konflikte beim Zusammenführen:** `components/files/IngestStatus.tsx` (nur `IngestRetryButton`) und `components/files/UploadForm.tsx` (nur Knopf und zwei Felder), falls 068 dort ändert; Struktur-, Such- und Einlese-Seite nur an den Steuerelementen.
7. Die Größen 36/28 px sind der Vorschlag der Analyse und stehen an einer Stelle (`components/ui/classes.ts`).
