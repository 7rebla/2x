# Auftrag 076 – Schriftzug in der Kopfzeile tippt sich

Meilenstein: Gestaltung (D1) · Freigabestufe: C (entschieden mit E-64) · Status: offen

Voraussetzung: E-64; 070 und 072 sind auf `main`.

## Ziel

Der Schriftzug „2x“ neben der Bildmarke tippt sich wie in einer Konsole auf – als fünftes Animationsmuster neben den vier aus E-52.

## Umfang

- **Wann:** einmal pro Sitzung (Browser-Sitzung, z. B. `sessionStorage` mit try/catch), auf der Anmeldeseite und beim ersten Öffnen nach der Anmeldung (Struktur `/`), nicht bei jedem Seitenwechsel. Bei „Bewegung reduzieren“ (System oder Einstellung in der App) steht der Name sofort fertig da.
- **Aussehen:** Zeichen erscheinen einzeln und hart (ohne Einblenden), 110–130 ms je Zeichen, Start nach etwa 300 ms. Dahinter ein schmaler Balken als Cursor in der Markenfarbe (Token `brand`); er blinkt nach dem Tippen 2–3 Mal und verschwindet dann. Schrift bleibt Inter, keine Monospace. Die Bildmarke ist von Anfang an sichtbar, nur der Schriftzug tippt sich.
- **Beliebige Namenslänge:** nicht fest auf zwei Zeichen (späterer Produktname).
- **Technik:** Eine unsichtbare Kopie des Namens reserviert die volle Breite (wie `.nav-label`), die getippten Zeichen liegen darüber, damit die Navigation nicht springt. Reines CSS mit gestaffelten Verzögerungen je Zeichen (z. B. CSS-Variable je Zeichen), keine neue Abhängigkeit. Barrierefreiheit: Der Link behält den vollen Namen als zugänglichen Namen, die Tipp-Ebene ist `aria-hidden`.
- **Doku:** `web/src/theme/README.md`, Tabelle der Animationsmuster um „Tippen“ ergänzen (Wann, Dauer, Abschaltung).
- **Tests:** Vitest für einmal pro Sitzung, „Bewegung reduzieren“ (System und Einstellung), beliebige Länge (z. B. 2 und 9 Zeichen), zugänglicher Name, Platzhalter reserviert die Breite; e2e: Kopfzeile bleibt einzeilig (bestehende `navigation.spec.ts`).

## Nicht-Ziele

- Kein Produktname im Code (es bleibt „2x“).
- Keine Änderung der übrigen Animationen.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/components/BrandMark.tsx`, `web/src/components/TextMotion.tsx`, `web/src/index.css`
- `web/src/components/BrandMark.test.tsx`, `web/src/components/TextMotion.test.tsx`
- `web/src/theme/README.md`
- gegebenenfalls `web/src/components/Layout.tsx` und die Anmeldeseite (nur das Einbinden)

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Web-Job aus `.github/workflows/ci.yml` grün (lint, typecheck, test, build, licenses), `api:generate` ohne Unterschied.
2. e2e wie in `ci.yml` grün.
3. Bildschirmaufnahme oder Bildfolge im Kurzbericht beschrieben (lokal, nicht eingecheckt).
4. `down -v` der eigenen Compose-Projekte endet mit Exit 0.

## Vorgaben und Hinweise

- Herkunft: E-64 (a7, 22.11.2026), Vorschlag der Sitzung „UI-Analyse“.
- Kontraste und Tokens aus 070.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
