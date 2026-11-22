# Auftrag 080 – Einheitliches Seitenraster

Meilenstein: Gestaltung (D1) · Freigabestufe: C (entschieden mit E-65) · Status: offen

Voraussetzung: 077 ist auf `main`; nicht gleichzeitig mit 078.

## Ziel

Ab 1280 px sind Kopfzeile (`max-w-7xl`) und Inhalt (`max-w-5xl`) verschieden breit; Marke und Seitentitel stehen bei 1600 px 128 px versetzt, Tabellen quetschen sich auf 1024 px. Nach E-65 (1) haben Kopf und Inhalt dieselbe Breite.

## Umfang

- Kopf und Inhalt `max-w-7xl`; Einleitungen und Fließtext `max-w-prose`.
- Formularseiten (Einstellungen, Selbsttest) behalten eine schmale Spalte innerhalb des Rasters; Selbsttest-Karten bei breitem Raster in 2–3 Spalten. Die Anmeldeseite macht 086.
- Landkarte: volle Inhaltsbreite und Resthöhe des Fensters, Mindestzoom beim Einpassen etwa 0,6, Legende in der Kartenecke.
- Bei 1600 px liegen linke Kante von Marke und Seitentitel auf derselben Linie (im Kurzbericht gemessen).
- Tests (Vitest; e2e, wo Layout oder Bedienung sich ändern) für das neue Verhalten; bestehende Tests angepasst, nicht abgeschwächt.
- Doku: `web/src/pages/README.md` bzw. `web/src/theme/README.md` nachziehen, wo betroffen.

## Nicht-Ziele

- Keine neue Abhängigkeit, keine Änderung an API oder Backend.
- Nur der genannte Bereich; andere Befunde der UI-Analyse haben eigene Aufträge.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/components/Layout.tsx`, `web/src/pages/SelftestPage.tsx`, `web/src/pages/SettingsPage.tsx`, `web/src/pages/MapPage.tsx`, `web/src/pages/map/nodes.tsx`, `web/src/index.css` (nur Kartenabschnitt), Tests

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
