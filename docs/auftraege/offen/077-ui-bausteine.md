# Auftrag 077 – UI-Bausteine Knopf, Feld, Auswahl

Meilenstein: Gestaltung (D1) · Freigabestufe: B · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
