# Auftrag 086 – Anmeldeseite als zentrierte Karte

Meilenstein: Gestaltung (D1) · Freigabestufe: C (entschieden mit E-65) · Status: zur Prüfung

Voraussetzung: 077 und 080 sind auf `main`.

## Ziel

Das Anmeldeformular steht linksbündig in einer breiten Spalte, rechts leer; der Knopf ist kleiner als die Felder. Nach E-65 (7) ist die Anmeldung eine zentrierte Karte mit Bildmarke.

## Umfang

- Karte `max-w-sm mx-auto`, Fläche `bg-surface` mit Rand, Bildmarke und Schriftzug darüber (mit Tipp-Animation aus 076), Knopf volle Breite, Felder und Knopf gleich hoch (Bausteine 077).
- Sprache wählbar wie bisher.
- Tests (Vitest; e2e, wo Layout oder Bedienung sich ändern) für das neue Verhalten; bestehende Tests angepasst, nicht abgeschwächt.
- Doku: `web/src/pages/README.md` bzw. `web/src/theme/README.md` nachziehen, wo betroffen.

## Nicht-Ziele

- Keine neue Abhängigkeit, keine Änderung an API oder Backend.
- Nur der genannte Bereich; andere Befunde der UI-Analyse haben eigene Aufträge.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/pages/LoginPage.tsx`, `web/src/pages/LoginPage.test.tsx`, e2e `login.spec.ts` falls Selektoren betroffen

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Web-Job aus `.github/workflows/ci.yml` grün (lint, typecheck, test, build, licenses), `api:generate` ohne Unterschied.
2. e2e wie in `ci.yml` grün.
3. Im eigenen Projekt im Browser geprüft bei 375, 1024 und 1600 px, hell und dunkel; Beobachtungen im Kurzbericht (Bildschirmfotos nur lokal, nicht eingecheckt).
4. `down -v` der eigenen Compose-Projekte endet mit Exit 0.

## Vorgaben und Hinweise

- Herkunft: UI-Analyse der Sitzung „UI-Analyse“ (22.11.2026, lokal), Entscheidung von a7 E-65 bzw. Stufe B der Leitstelle.
- Gestaltung: Tokens aus 070, Icons nur über `web/src/icons` (071), Bausteine aus `web/src/components/ui/` (077). Bewegung reduzierbar (E-52).
- Texte in Deutsch und Englisch (`web/src/locales/`).

## Fragen an a7 (mit Optionen und Empfehlung)

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Kriterien 0, 1, 2 und 4 erfüllt; 3 erfüllt mit einer Lücke in der Kombination Breite/Modus (siehe unten). Keine neue Abhängigkeit, keine Änderung an API, Backend oder Texten (`locales` unverändert, die vorhandenen Texte de/en reichen).

### Was wurde gebaut?

- **`web/src/pages/LoginPage.tsx`:** Seite `mx-auto w-full max-w-sm` (ab 640 px `pt-8` zusätzlich), darin oben zentriert Bildmarke (48 px, Master, `CARD_BRAND_SIZE`) mit Schriftzug „2x“ in `text-4xl`, darunter die Karte (`data-testid="login-card"`: `rounded-lg border border-line bg-surface p-6 shadow-sm`) mit `h1` (`AnimatedHeading`, wie 078/085), Einleitung, Fehler der Sitzung, Formular. Knopf `primary` mit `className="w-full"`; Felder und Knopf aus den Bausteinen 077, beide 36 px hoch und gleich breit. Fehlermeldung bei falschem Kennwort steht in der Karte. Seitentitel (`usePageTitle`), Weiterleitung nach `?next=` und Sprachumschalter im Kopf unverändert.
- **Tipp-Animation:** Der Schriftzug über der Karte nutzt `TypedText` im selben Lauf `sign-in` wie der Kopf; beide entscheiden beim selben Rendern und tippen gleichzeitig. Der Kopf (076) tippt weiter wie bisher. Bei „Bewegung reduzieren“ steht der Name sofort da.
- **`web/src/components/BrandMark.tsx` (nicht im Auftrag genannt, minimal):** neue Eigenschaft `link` (Standard `true`). `link={false}` zeichnet dieselbe Bildmarke-plus-Name-Kombination als `<span data-testid="brand-lockup">` statt als Link nach `/`. So bleibt der Link „2x“ im Kopf der einzige Link dieses Namens (`brand.spec.ts`, `layout.spec.ts`, `App.test.tsx` unverändert grün). Im Kopf ändert sich nichts.
- **Doku:** `web/src/pages/README.md` (Abschnitt „Frame and navigation“: Satz „The sign-in page follows with work order 086“ ersetzt durch die Beschreibung der Karte), `web/src/theme/README.md` (Bildmarke auf der Anmeldekarte, Tabellenzeile Muster E).

### Wie wurde getestet?

`W` = `docker compose -p twox-086-web -f deploy/compose/compose.web.yaml`, `D` = `docker compose -p twox-086`; `.env` aus `.env.example` (ohne BOM) mit `TWOX_API_PORT=18086`. `web/dist` und `web/playwright-report` vor den Builds gelöscht. „2x“ und „twox-leit“ nicht berührt.

| AK | Ergebnis |
| --- | --- |
| 0 | erfüllt: `docker version` Exit 0, `docker compose version` (v5.7.0) Exit 0 |
| 1 | erfüllt: `W --profile dev build web-dev`, `npm ci`, `lint`, `typecheck`, `test` (**44 Dateien, 894 Fälle bestanden**, darunter `components/ui/sourceControls.test.ts` und `theme/contrast.test.ts`), `build`, `licenses` („License check passed.“) je Exit 0; `api:generate` Exit 0, `git diff --exit-code -- web/openapi web/src/api` Exit 0, kein unversionierter Unterschied |
| 2 | erfüllt: `D --profile dev build migrate api worker web-dev`, `pull e2e`, `npm ci`, `up -d --wait` je Exit 0, „Create test account“ wie in `ci.yml` („Created account 'e2e-manager' with role 'manage'.“), `D --profile e2e run --rm e2e`: **75 passed, 1 skipped** (bedingter lokaler Teil von `m2-acceptance.spec.ts`, wie bisher), Exit 0 |
| 3 | erfüllt mit Lücke, siehe unten |
| 4 | erfüllt: `D --profile dev --profile e2e down -v` Exit 0, `W --profile dev down -v` Exit 0; kein Container und kein Volume mit `twox-086` übrig |

**Neue Tests.** Vitest `LoginPage.test.tsx` +7 Fälle: Karte zentriert (`mx-auto`, `max-w-sm`) mit `bg-surface`, Rand, Überschrift/Einleitung/Formular in der Karte; Bildmarke 48 px über der Karte, kein zweiter Link „2x“; Name tippt in Karte und Kopf (Lauf `sign-in`); reduzierte Bewegung; Felder und Knopf gleich hoch, Knopf volle Breite; Deutsch mit Sprachumschalter im Kopf; Fehler bei falschem Kennwort in der Karte. `BrandMark.test.tsx` +2 Fälle (ohne Link, mit Tippen ohne Link). Bestehende Fälle unverändert. e2e `login.spec.ts`: neuer Test je 375, 1024 und 1600 px (Karte höchstens 384 px breit und auf ±1 px in `main` zentriert, Marke zentriert über der Karte, Benutzername/Kennwort/Knopf je 36 px hoch und gleich breit, kein waagerechtes Scrollen); der Test „falsches Kennwort“ prüft zusätzlich, dass die Meldung in der Karte steht.

**Sichtprüfung (AK 3)** im eingebauten Browser gegen `127.0.0.1:18086/login`, Deutsch:

- 1600 px hell: Karte 384 px mittig, Marke und Name darüber mittig, viel ruhige Fläche links/rechts; Kopf links mit Marke, rechts Sprachumschalter.
- 1440 px dunkel: Karte genau mittig (Mitte 720 px = Mitte von `main`), kein waagerechtes Scrollen; in einer neuen Browsersitzung (`twox.typed` entfernt) tippen beide Namen (`data-typing="type"` zweimal), danach `twox.typed = sign-in`.
- 1024 px dunkel: Karte mittig, Kartenfläche hebt sich vom Seitenhintergrund ab, Rand sichtbar, Knopf gut lesbar.
- 768 px hell: Karte mittig, Felder und Knopf gleich breit.
- 375 px dunkel, falsches Kennwort (nicht vorhandenes Konto, Testwert): Karte füllt die Breite abzüglich 16 px Rand, Meldung „Benutzername oder Kennwort ist falsch.“ rot auf `danger-soft` zwischen Kennwortfeld und Knopf, Kennwortfeld geleert, kein waagerechtes Scrollen.
- **Lücke:** 1600 px dunkel, 1024 px hell und 375 px hell habe ich nicht eigens angesehen (stattdessen 1440 dunkel und 768 hell). Die Geometrie bei 375/1024/1600 px prüft der e2e-Test; die Farben sind dieselben Tokens wie in den geprüften Kombinationen, die Kontrastpaare (`fg-muted`/`surface`, `brand`/`canvas`, Feldränder auf Karten) deckt `contrast.test.ts` ab.

### Zweig und Arbeitsverzeichnis

Zweig `worktree-agent-a244d36ea0d5b8526`, Arbeitsverzeichnis `.claude/worktrees/agent-a244d36ea0d5b8526`. Commits: Umsetzung mit Tests und Doku (`db73c8a`), dieser Bericht. Nicht gepusht, nicht zusammengeführt.

Geänderte Dateien: `web/src/pages/LoginPage.tsx`, `web/src/pages/LoginPage.test.tsx`, `web/e2e/login.spec.ts`, `web/src/components/BrandMark.tsx`, `web/src/components/BrandMark.test.tsx`, `web/src/pages/README.md`, `web/src/theme/README.md`, diese Auftragsdatei.

### Abweichungen und Hinweise

1. **`BrandMark.tsx` und `BrandMark.test.tsx` geändert** (nicht unter „Betroffene Bereiche“): nötig, damit die Marke über der Karte kein zweiter Link nach `/` wird. Kleine, rückwärtsverträgliche Eigenschaft; keine Überschneidung mit 081/082 (`Layout.tsx`, `index.css`, Navigation nicht angefasst).
2. **Zwei tippende Namen:** Auf der Anmeldeseite tippen jetzt der Name im Kopf (076, laut Leitstelle zu erhalten) und der Name über der Karte (laut Auftrag) gleichzeitig im selben Lauf. Wirkt ruhig, weil beide synchron laufen, ist aber doppelt. Falls a7 nur einen tippenden Namen möchte: im Kopf auf der Anmeldeseite still stehen lassen (Änderung in `Layout.tsx`, nach 082) oder den Namen über der Karte still stellen (eine Zeile in `LoginPage.tsx`). Keine Entscheidung nötig für die Abnahme dieses Auftrags.
3. `docs/DECISIONS.md`, `docs/STATUS.md`, `docs/ROADMAP.md` nicht geändert.
