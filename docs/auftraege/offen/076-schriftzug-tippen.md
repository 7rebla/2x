# Auftrag 076 – Schriftzug in der Kopfzeile tippt sich

Meilenstein: Gestaltung (D1) · Freigabestufe: C (entschieden mit E-64) · Status: zur Prüfung

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

**Status: zur Prüfung.** Alle Kriterien 0–4 erfüllt; alle Läufe am 22.11.2026 im Container (Docker Engine 29.9.3, Compose v5.7.0). Keine neue Abhängigkeit, keine offene Frage an a7.

### Was wurde gebaut?

- **`web/src/components/TextMotion.tsx`:** Muster E `TypedText({ text, run })`. Läufe `sign-in` (Anmeldeseite, auch wenn die Sitzung nicht geladen werden kann) und `app` (erste Seite nach der Anmeldung); bereits getippte Läufe stehen in `sessionStorage` unter `twox.typed` (`typedRuns()`, `markTyped()`, jeder Zugriff in `try/catch`). Die Entscheidung fällt einmal je Lauf und bleibt, solange die Kopfzeile steht; Seitenwechsel tippen nie erneut. Während die Sitzung lädt („pending“) bleibt der Platz leer, wenn in dieser Sitzung noch nichts getippt hat, sonst steht der Name sofort da. Bei „Bewegung reduzieren“ (Einstellung oder System) rendert die Komponente den Namen als schlichten Text ohne `tx-`-Klassen (auch wenn es während des Tippens eingeschaltet wird); der Lauf zählt dann als erledigt. Zeichen werden als Grapheme zerlegt (`Intl.Segmenter`, `typedCharacters()`), damit ein späterer Name mit Akzent nicht zerfällt (ESLint verbietet den Spread auf Zeichenketten).
- **Aufbau:** Der Name selbst (`.tx-type-text`) bleibt Textknoten im Fluss, reserviert die volle Breite und ist der zugängliche Name des Links, wird aber nicht gezeichnet (`opacity: 0`). Darüber liegt absolut die Tipp-Ebene (`.tx-type-layer`, `aria-hidden`), deren Zeichen aus `data-char` per `::before { content: attr(data-char) }` kommen – der Seitentext bleibt also genau „2x“ (bestehende Tests mit `getByText("2x")` und `textContent` unverändert grün). Je Zeichen `--tx-char`.
- **`web/src/index.css`:** eigener Abschnitt „E“ nach den Keyframes von D (eigener `@layer components`-Block plus drei Keyframes `tx-type-char`, `tx-type-cursor`, `tx-type-blink`); die übrigen Animationsabschnitte sind unverändert. Start 300 ms (`--tx-type-start`), 120 ms je Zeichen (`--tx-type-step`), Zeichen hart (`step-end`, nur `opacity`). Cursor `max(2px, 0.07em)` breit in `var(--twox-brand)`: wartet vor dem ersten Zeichen, folgt jedem Zeichen, blinkt nach dem letzten dreimal (je 300 ms an/aus, 1,8 s) und verschwindet. Schrift bleibt Inter.
- **`web/src/components/BrandMark.tsx`:** neue Eigenschaft `typing` und Hilfsfunktion `typingRunFor(status)` (Sitzungszustand → Lauf). Ohne `typing` steht der Name still wie bisher. Die Bildmarke ist von Anfang an sichtbar.
- **`web/src/components/Layout.tsx`:** nur das Einbinden (Import und `<BrandMark typing={typingRunFor(session.status)} />`, 2 Zeilen). Die Anmeldeseite musste nicht geändert werden, weil die Kopfzeile dort aus `Layout` kommt.
- **Doku:** `web/src/theme/README.md` – Tabellenzeile „E, typing“ und Abschnitt „Typing (pattern E)“ mit Wann, Dauer, Aussehen, Aufbau/Barrierefreiheit, Abschaltung.
- **Tests:** `TextMotion.test.tsx` +16 Fälle (Länge 2, 9 und mit Leerzeichen; Graphem mit kombinierendem Akzent; Ebene `aria-hidden` ohne Text, Name als Text; Platzhalter reserviert die Breite (DOM-Reihenfolge und CSS-Regeln aus `index.css?raw`); Zeiten 300 ms / 110–130 ms, harte Zeichen, Cursor in `brand`, keine eigene Schrift; einmal pro Sitzung; `app` nach `sign-in` mit neuer Ebene; Abmelden tippt nicht erneut; „pending“ leer bzw. sofort fertig; reduzierte Bewegung durch Einstellung, System und während des Tippens; blockierter Speicher; unbekannte Speicherwerte). `BrandMark.test.tsx` +8 Fälle (`typingRunFor` für alle vier Zustände, zugänglicher Name „2x“ mit Tippen, nur der Name tippt, reduzierte Bewegung, ohne `typing` kein Tippen und kein Speichereintrag). Beliebige Länge nur mit neutralen Platzhaltern („abcdefghi“, „a b“).

### Wie wurde getestet?

`W` = `docker compose -p twox-076-web -f deploy/compose/compose.web.yaml`, `D` = `docker compose -p twox-076`, `.env` aus `.env.example` (ohne BOM) mit `TWOX_API_PORT=18076`. „2x“ und „twox-leit“ nicht berührt; `web/dist` und `web/playwright-report` vor den Builds gelöscht.

| AK | Ergebnis |
| --- | --- |
| 0 | erfüllt: `docker version` (Server 29.9.3), `docker compose version` (v5.7.0), Exit 0 |
| 1 | erfüllt: `W --profile dev build web-dev`, `npm ci`, `lint`, `typecheck`, `test` (38 Dateien, 754 Fälle bestanden), `build`, `licenses` („License check passed.“) je Exit 0; `api:generate` Exit 0, danach `git status --porcelain --untracked-files=all` leer (kein Unterschied in `web/openapi`, `web/src/api`) |
| 2 | erfüllt: `D --profile dev build migrate api worker web-dev`, `pull e2e`, `npm ci`, `up -d --wait` (Exit 0), „Create test account“ wie in `ci.yml` („Created account 'e2e-manager' with role 'manage'.“), `D --profile e2e run --rm e2e`: **55 passed**, Exit 0 (darunter `navigation.spec.ts` mit der einzeiligen Kopfzeile und `brand.spec.ts`) |
| 3 | erfüllt, Bildfolge im eingebauten Browser (lokal, nicht eingecheckt), `/login` im Dunkelmodus, Animationen per `getAnimations()` angehalten und auf feste Zeitpunkte gesetzt: 150 ms Bildmarke sichtbar, Cursor allein am Anfang · 360 ms „2“ und Cursor · 480 ms „2x“ und Cursor · 900 ms/1000 ms „2x“, Cursor aus (Blinkphase) · 1100 ms „2x“, Cursor an · 3000 ms „2x“ ohne Cursor. Neuladen in derselben Sitzung: kein Tippen (`twox.typed` = `sign-in`, keine `tx-type`-Animation). Anmelden mit dem Testkonto: auf `/` tippt der Name erneut (`sign-in,app`); Wechsel auf `/map` startet nichts neu; Abmelden → `/login` mit stehendem Namen. Danach abgemeldet und den Speicherschlüssel entfernt |
| 4 | erfüllt: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` je Exit 0; kein Container oder Volume mit `twox-076` übrig |

### Zweig und Arbeitsverzeichnis

Zweig `worktree-agent-a66380ba1bc96c0c4`, Arbeitsverzeichnis `.claude/worktrees/agent-a66380ba1bc96c0c4`. Commits `28039e9` (Umsetzung und Tests), `53dccb0` (README), dazu dieser Bericht. Nicht gepusht, nicht zusammengeführt.

### Abweichungen und Hinweise

1. **Zugänglicher Name:** Statt einer zusätzlichen unsichtbaren Kopie ist der echte Name selbst der Platzhalter (unsichtbar gezeichnet, aber im Fluss und im Barrierefreiheitsbaum); die Tipp-Ebene enthält keinen Text. So steht der Name nur einmal im DOM, und weder Tests noch Screenreader sehen „2x2x“.
2. **„Bewegung reduzieren“ verbraucht den Lauf:** Wird die Bewegung später in derselben Sitzung wieder eingeschaltet, tippt der Name nicht nachträglich (sonst würde er beim Umschalten auf der Einstellungsseite plötzlich tippen).
3. **Ladezustand:** In einer neuen Sitzung ist der Name während des Ladens der Sitzung kurz unsichtbar (die Bildmarke nicht), damit er nicht erst erscheint und dann zum Tippen verschwindet.
4. **Mögliche Überschneidung mit 077:** `Layout.tsx` (Importzeile von `BrandMark` und die Zeile `<BrandMark … />`).
5. `docs/DECISIONS.md`, `docs/STATUS.md`, `docs/ROADMAP.md` nicht geändert.
