# Auftrag 078 – Barrierefreiheit: Sprunglink, Seitentitel, Überschriften, Fokus

Meilenstein: Gestaltung (D1) · Freigabestufe: B · Status: zur Prüfung

Voraussetzung: 077 ist auf `main`.

## Ziel

Es gibt keinen Sprunglink, der Browser-Titel ist auf jeder Seite „2x“, die Marke ist auf jeder Seite das `h1` und der Seitentitel nur `h2`, und nach einem Seitenwechsel bleibt der Fokus in der Navigation (WCAG 2.4.1, 2.4.2, 2.4.3). Danach ist das behoben.

## Umfang

- Sprunglink „Zum Inhalt“ als erstes fokussierbares Element; `<main id="inhalt" tabIndex={-1}>`.
- Browser-Titel je Route („Struktur – 2x“; Gerät und Datei mit Namen), kleiner Hook `usePageTitle`.
- Seitentitel als `h1` (`AnimatedHeading` Standard `level=1`), Marke ohne Überschrift, Abschnitte `h2`.
- Nach Routenwechsel Fokus auf die Seitenüberschrift (nicht beim ersten Laden).
- Tests (Vitest; e2e, wo Layout oder Bedienung sich ändern) für das neue Verhalten; bestehende Tests angepasst, nicht abgeschwächt.
- Doku: `web/src/pages/README.md` bzw. `web/src/theme/README.md` nachziehen, wo betroffen.

## Nicht-Ziele

- Keine neue Abhängigkeit, keine Änderung an API oder Backend.
- Nur der genannte Bereich; andere Befunde der UI-Analyse haben eigene Aufträge.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/components/Layout.tsx`, `web/src/components/TextMotion.tsx` (nur Überschriften-Ebene), `web/src/routes.tsx`, neu `web/src/hooks/usePageTitle.ts`, alle Seiten unter `web/src/pages/` (Titel, Überschriftenebene), Tests

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
  - Sprunglink „Zum Inhalt“ / „Skip to content“ (`common:skipToContent`) als erstes fokussierbares Element in `Layout.tsx`; oberhalb des Fensters, bei Fokus oben links sichtbar. Ein Klick fokussiert `<main id="inhalt" tabIndex={-1}>`, ohne `#inhalt` in die Adresse zu schreiben.
  - `web/src/hooks/usePageTitle.ts`: Browser-Titel „Seite – 2x“ (Name aus `common:appTitle`); Gerät und Datei mit ihrem Namen, bei 404 übernimmt `NotFound` („Seite nicht gefunden – 2x“). Jede Seite ruft den Hook mit dem Text ihrer Überschrift auf, vor allen frühen Rückgaben.
  - Überschriften: `AnimatedHeading` und `MaskedTitle` haben Standard `level=1`; die Marke im Kopf ist kein `h1` mehr (nur noch der vorhandene Link auf `/`). Abschnitte eine Ebene höher: `h3`→`h2` (Dokumentseite, Import, Selbsttest-Karten, Strukturformulare, `DeviceFiles`), `h4`→`h3` (`UploadForm`).
  - Fokus nach Seitenwechsel (`useHeadingFocus` in `Layout.tsx`): bei neuem Pfad Fokus auf das `h1` der neuen Seite, auch wenn es später erscheint (nachgeladene Seite, Ladezustand → Gerätename; per `MutationObserver`). Nicht beim ersten Laden, nicht bei reiner Query-Änderung (Suche, Filter), nicht bei einer Umleitung ohne vorherige Bedienung (Start → `/login`); nach der Anmeldung schon. Der Fokus wird nie einem Element weggenommen, auf das der Nutzer inzwischen gewechselt ist; Klick oder Taste beendet die Beobachtung. Kein Fokusring um `main` und das fokussierte `h1` (keine Bedienelemente).
  - Doku: `web/src/pages/README.md` (Überschriften, Titel, Sprunglink, Fokus).
- **Wie wurde getestet?**
  - Kriterium 0: `docker version` und `docker compose version` Exit 0.
  - Kriterium 1: Web-Job im Compose-Projekt `twox-078-web`: lint, typecheck, test (42 Dateien, 821 Tests), build, licenses grün; `api:generate` ohne Unterschied. Ein erster Testlauf hatte unter hoher Last (mehrere parallele e2e-Läufe anderer Aufträge) 9 Zeitüberschreitungen, auch in nicht berührten Dateien (`AuditTrail.test.tsx`); die betroffenen Dateien einzeln und danach der volle Lauf waren grün.
  - Neue Vitest-Tests: `hooks/usePageTitle.test.tsx`; in `components/Layout.test.tsx` Sprunglink (erste Tab-Station, Ziel, de), einziges `h1`, Titel je Route, Gerät/Datei/404, Sprache, Fokus (nicht beim ersten Laden, nicht bei Umleitung ohne Bedienung, Navigation, Query-Änderung, Ladezustand → Gerätename, kein Wegnehmen des Fokus); `TextMotion.test.tsx` Standardebene 1. Bestehende Tests nur von Ebene 2 auf 1 bzw. 3 auf 2 umgestellt, Marke als Link statt Überschrift geprüft.
  - Kriterium 2: e2e im Projekt `twox-078` wie in `ci.yml`: 58 bestanden, 1 übersprungen (lokaler Teil M2). Neu `web/e2e/accessibility.spec.ts` (Sprunglink per Tastatur, Titel aller Navigationsseiten und 404, Fokus nach Enter in der Navigation und nach Zurück). Angepasst: `brand.spec.ts` (Marke im `banner`, Titel „Structure – 2x“), `settings.spec.ts` (`h1 .tx-word`), übrige Specs Ebene 2→1.
  - Kriterium 3: eingebauter Browser gegen das eigene Projekt (Port 18078), angemeldet mit dem Entwicklungs-Testkonto. 1600 px hell: Sprunglink nach Tab oben links im freien Rand, Enter fokussiert `main#inhalt`, Adresse bleibt `/`. 1024 px dunkel: Klick auf „Änderungsprotokoll“ → Titel „Änderungsprotokoll – 2x“, Fokus auf dem `h1`, ohne Ring; Überschrift sieht aus wie vorher. 375 px hell: Gerät aus der Struktur geöffnet → Titel „<Gerätename> – 2x“, Fokus auf dem `h1` mit dem Namen, genau ein `h1`, darunter `h2` „Dateien“, `h3` „Neue Datei hochladen“. 375 px dunkel, 1600 px dunkel, 1024 px hell: Sprunglink auf der Suche sichtbar und lesbar. Nach der Anmeldung landete der Fokus auf „Struktur“. Bildschirmfotos nicht eingecheckt.
  - Kriterium 4: `down -v` für `twox-078` und `twox-078-web` Exit 0.
- **Zweig und Arbeitsverzeichnis:** `worktree-agent-ad9f431d9b6e2897b`, `.claude/worktrees/agent-ad9f431d9b6e2897b`.
- **Abweichungen:**
  - `routes.tsx` blieb unverändert (Titel kommen aus den Seiten, nicht aus den Routen).
  - Außerhalb von `pages/` nur Überschriftenebenen geändert in Dateien paralleler Aufträge: `components/DeviceFiles.tsx` (079, `h3`→`h2`), `components/files/UploadForm.tsx` (088, `h4`→`h3`); dazu `NotFound.tsx` und `PagePlaceholder.tsx` (Titelaufruf) sowie `locales/*/common.json` (ein Text). In den Seiten von 079/083/087/088 nur Import, `usePageTitle`-Zeile und Überschriftenebene; in deren Tests nur die Ebenen.
  - Der fokussierte Sprunglink liegt bei 375 und 1024 px kurz über der Bildmarke (nur solange er den Fokus hat).
  - Keine neue Abhängigkeit.
