# Auftrag 070 – Theme, Schrift, Text-Animationen und Einstellungsseite

Meilenstein: Gestaltung (D1, parallel zu M2) · Freigabestufe: C · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
