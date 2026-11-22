# Auftrag 078 – Barrierefreiheit: Sprunglink, Seitentitel, Überschriften, Fokus

Meilenstein: Gestaltung (D1) · Freigabestufe: B · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
