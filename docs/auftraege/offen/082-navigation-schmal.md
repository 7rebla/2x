# Auftrag 082 – Navigation unter 1280 px

Meilenstein: Gestaltung (D1) · Freigabestufe: C (entschieden mit E-65) · Status: zur Prüfung

Voraussetzung: 080 ist auf `main`.

## Ziel

Unter 1280 px zeigt die Navigation nur Icons; einige sind ohne Text nicht selbsterklärend, Tooltips fehlen auf Touch, und bei 375 px sind Einträge nur über eine Scrollleiste erreichbar. Nach E-65 (3): 768–1279 px Icon mit Kurzbeschriftung darunter, unter 768 px ein Menüknopf mit ausklappbarer Liste.

## Umfang

- Kurztexte je Eintrag (`locales/*/nav.json`), zweizeilig `text-xs` unter dem Icon zwischen 768 und 1279 px.
- Unter 768 px: Knopf „Menü“ (`aria-expanded`, `aria-controls`), Liste mit allen Einträgen und Benutzermenü, schließt mit Escape und nach Auswahl, Fokus kehrt zum Knopf zurück.
- `web/e2e/navigation.spec.ts`: einzeilig bei 1024 und 1280 px in de und en, Menü bei 375 px.
- Tests (Vitest; e2e, wo Layout oder Bedienung sich ändern) für das neue Verhalten; bestehende Tests angepasst, nicht abgeschwächt.
- Doku: `web/src/pages/README.md` bzw. `web/src/theme/README.md` nachziehen, wo betroffen.

## Nicht-Ziele

- Keine neue Abhängigkeit, keine Änderung an API oder Backend.
- Nur der genannte Bereich; andere Befunde der UI-Analyse haben eigene Aufträge.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/components/Layout.tsx`, `web/src/index.css` (Navigationsabschnitt), `web/src/navigation.ts`, `web/src/locales/*/nav.json`, `web/src/components/Layout.test.tsx`, `web/e2e/navigation.spec.ts`

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

- **Was wurde gebaut?**
  - Ab 1280 px unverändert: Icon und Text nebeneinander.
  - 768–1279 px: Icon über einer Kurzbeschriftung (`text-xs`, `nav:short.*` in `locales/de|en/nav.json`). Kurztexte de: Struktur, Karte, Suche, Einlesen, Import, Protokoll, Selbsttest; en: Structure, Map, Search, Ingest, Import, Log, Self-test. Jeder Kurztext ist Teil des vollen Textes (WCAG 2.5.3, per Test geprüft). Der volle Text bleibt Linktext, zugänglicher Name und Tooltip. Den Kurztext zeichnet CSS aus `data-short` (`.nav-short::before` in `index.css`) in einem `aria-hidden`-Element, wie schon beim Tippen (076). Dadurch bleiben `textContent`-Prüfungen in fremden Tests (`routes.test.tsx`, `session.test.tsx`) unverändert gültig. Die fette Breite ist wie bei `nav-label` reserviert. Ein Eintrag ist in dieser Form 42 px hoch, genauso hoch wie ab 1280 px. Der Kopf bleibt deshalb bei allen Breiten 76 px hoch, und `layout.spec.ts` bleibt ohne Änderung grün. Dafür scrollt die Leiste nur noch ab 1280 px auf Überlauf (`xl:overflow-x-auto`). Darunter passt alles, geprüft bei 768 und 1024 px in de und en.
  - Unter 768 px (`NARROW_QUERY` = `(width < 48rem)`, per `matchMedia` mit `useSyncExternalStore`): Im Kopf stehen nur Bildmarke mit Schriftzug und der Knopf „Menü“/„Menu“ (`Button` ghost md, Icon `menu`, geöffnet `close`, `aria-expanded`, `aria-controls`). Er öffnet ein Feld unter dem Kopf mit allen Einträgen (Icon und voller Text, je Zeile, mindestens 40 px hoch) und dem Inhalt des Benutzermenüs (Name, Rolle, Einstellungen, Sprache, Abmelden).
  - Das Feld schließt bei Escape (Fokus zurück auf den Knopf), bei einem Klick außerhalb, bei einem zweiten Klick auf den Knopf, bei jedem Adresswechsel und wenn das Fenster auf 768 px wächst. Nach einer Auswahl schließt es ebenfalls; der Fokus geht zuerst auf den Knopf und dann, wie in 078, auf die Überschrift der neuen Seite. Bei Auswahl der aktuellen Seite bleibt der Fokus auf dem Knopf. Ohne Rolle enthält das Menü nur den Benutzerteil; vor der Anmeldung gibt es kein Menü, die Sprachwahl bleibt im Kopf.
  - Neue Icons `menu` (Lucide `Menu`) und `close` (Lucide `X`) in `icons/names.ts` und `icons/README.md`.
  - Doku: `pages/README.md` (Abschnitt „Frame and navigation“) und `theme/README.md` (Muster C).
- **Wie wurde getestet?**
  - Alle Prüfungen in Containern (Compose-Projekte twox-082-web und twox-082, API-Port 18082). `docker version` und `docker compose version`: Exit 0.
  - Web-Job wie in `ci.yml`: lint, typecheck, test (44 Dateien, 899 Tests), build und licenses mit Exit 0; `api:generate` ohne Unterschied.
  - e2e wie in `ci.yml` mit Testkonto: 76 bestanden, 1 übersprungen (lokaler Teil der M2-Abnahme, braucht `TWOX_M2_LOCAL`), Exit 0.
  - Vitest in `Layout.test.tsx`: Kurztexte (Attribute, `aria-hidden`, Klassen, de/en, Teil des vollen Textes) und zehn neue Fälle für das Menü mit `fakeMatchMedia` (geschlossen, geöffnet mit allen Einträgen und Benutzerinhalt, Escape, Auswahl mit Fokus auf Überschrift, aktuelle Seite, Klick außerhalb, Breitenwechsel, ohne Rolle, Deutsch, vor der Anmeldung).
  - `e2e/navigation.spec.ts`: eine Zeile bei 1280, 1024 und neu 768 px in en und de (Kurztexte sichtbar, unter dem Icon, kein Überlauf von Leiste und Seite). Die Telefonprüfung bei 375 px ist neu gefasst: Menü mit Maus, nur mit Tastatur (Enter, Leertaste, Tab, Escape), auf Deutsch, Rückkehr der Leiste bei 768 px.
  - `down -v` beider Projekte: Exit 0.
- **Sichtprüfung** im eingebauten Browser gegen 127.0.0.1:18082 (Testkonto) bei 375, 768, 1024, 1279, 1440 und 1600 px, hell und dunkel:
  - 375 px: Kopf mit Bildmarke und „☰ Menü“. Das geöffnete Feld liegt mit Schatten über dem Inhalt, der aktuelle Eintrag hat den weichen Akzenthintergrund, darunter folgt nach einer Trennlinie der Benutzerteil. Kein waagerechter Überlauf.
  - 768 und 1024 px: alle sieben Kurztexte in einer Zeile mit Platz vor dem Benutzernamen.
  - 1279 px: genauso, mit viel Luft.
  - 1440 und 1600 px: unverändert Icon und Text nebeneinander.
  - Kopfhöhe bei 375, 1440 und 1600 px gemessen: 76 px. Für 1024 px belegt die bestandene Prüfung in `layout.spec.ts` dieselbe Höhe.
  - Bildschirmfotos nur lokal.
- **Zweig und Arbeitsverzeichnis:** `worktree-agent-a26ab5b47d3245f4c`, `.claude/worktrees/agent-a26ab5b47d3245f4c`
- **Abweichungen:**
  - Fremde Dateien, jeweils minimal:
    - `components/UserMenu.tsx`: Inhalt des Panels als `UserMenuContent` herausgelöst, das Verhalten ist unverändert.
    - `icons/names.ts` und `icons/README.md`: zwei neue Icons.
    - `pages/README.md` und `theme/README.md`: Doku, wie im Auftrag vorgesehen.
  - `text-xs` (12 px) für die Kurztexte stand so im Auftrag, wich aber von E-65 Punkt 5 ab. Mit der Nachbesserung ist das erledigt: jetzt 13 px, der Kopf bleibt 76 px hoch.
  - Die Sichtprüfung lief im gemeinsamen Browserfenster: Eine andere Sitzung (Port 18089) hat zwischendurch denselben Tab benutzt und über das geteilte Cookie auf 127.0.0.1 eine Abmeldung ausgelöst. Danach habe ich in einem eigenen Tab neu angemeldet und weitergeprüft.
- **Offene Fragen:** keine.

### Nachbesserung (nach Prüfung der Leitstelle)

1. **Fokus verlässt das Menü (unter 768 px):** Knopf und Feld stehen in einem gemeinsamen Wrapper mit `onBlur` (focusout). Geht der Fokus auf ein Element außerhalb (`relatedTarget` außerhalb, also Tab nach „Abmelden“ oder Umschalt+Tab vor dem Knopf), schließt das Feld. Der Fokus bleibt dort, wo er hingegangen ist, wie im Muster „Disclosure Navigation“ der APG. Geht der Fokus ins Leere (`relatedTarget` null, etwa bei einem Klick auf Text im Feld), bleibt das Feld offen; einen Klick außerhalb fängt weiter `pointerdown` ab. Tests: Vitest (innen bleibt offen, ins Leere bleibt offen, nach außen schließt ohne Rückholen) und ein e2e-Schritt in `navigation.spec.ts`. Dort schließt Tab nach „Sign out“ das Feld, der Fokus liegt sichtbar in `main` und nicht auf dem Knopf. Umschalt+Tab vor dem Knopf schließt ebenfalls.
2. **Schriftgröße der Kurztexte:** 13 px mit 16 px Zeilenhöhe (`text-[13px] leading-4`, E-65 Punkt 5). Gemessen bei 768 px auf Deutsch: Leiste 42 px hoch, Kopf 76 px.
3. **Überlauf bei 768 px:** Gemessen auf Deutsch mit einem Benutzernamen, der den Knopf ausreizt (192 px). Mit den bisherigen Abständen lief die Leiste um 40 px über, und „Selbsttest“ lag unter dem Benutzerknopf.
   - Abstände unter 1280 px verkleinert: kein `gap` zwischen den Einträgen, Innenabstand 4 px statt 8 px.
   - `overflow-x-auto` gilt jetzt als Rückfall bei allen Breiten. Der Fokusrahmen liegt unter 1280 px innen (`-outline-offset-2`), damit die Scrollbox ihn nicht abschneidet und der Kopf 76 px hoch bleibt. Akzent auf `accent-soft` ist in `contrast.test.ts` mit 3:1 geprüft.
   - Messwerte bei 768 px, Deutsch, langer Name: freie Breite 25 px, auch mit sichtbarer 15-px-Bildlaufleiste des Fensters. Kein Überlauf der Seite, Kopf 76 px.
   - Neuer e2e-Schritt: 768 px, Deutsch, langer Name über eine umgeschriebene Antwort von `/api/v1/me/`. Geprüft wird: Knopf 192 px breit, Leiste endet vor dem Knopf und scrollt nicht, eine Zeile, Kopf 76 px, kein Überlauf der Seite.
4. **Kurztexte:**
   - Englisch jetzt „Ingestion“ statt „Ingest“. Bei 768 px mit langem Namen bleiben 41 px frei (vor der Verkleinerung der Abstände gemessen).
   - Damit sind alle englischen Kurztexte ganze Wörter des vollen Namens („Log“ aus „Change log“).
   - Deutsch bleibt „Karte“ und „Protokoll“. „Landkarte“ braucht 29 px mehr und passt bei 768 px neben einem langen Namen nicht sicher; „Änderungsprotokoll“ passt nicht. Die Abweichung steht in `web/src/pages/README.md`.

Geprüft:
- Web-Job wie in `ci.yml`: lint, typecheck, test (44 Dateien, 900 Tests), build und licenses mit Exit 0; `api:generate` ohne Unterschied.
- e2e: 77 bestanden, 1 übersprungen (lokaler Teil der M2-Abnahme), Exit 0.
- Sichtprüfung im eigenen Tab unter `twox082.localhost:18082` (in der ungetrackten `.env` unter `TWOX_ALLOWED_HOSTS` eingetragen), mit einem zweiten Testkonto mit langem Namen, hell und dunkel bei 768 px.
- `down -v` beider Projekte: Exit 0.
