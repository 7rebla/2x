# Auftrag 087 – Suchtreffer kompakter

Meilenstein: Gestaltung (D1) · Freigabestufe: B · Status: offen

Voraussetzung: 077 ist auf `main`.

## Ziel

Ein Suchtreffer listet dieselbe Datei für bis zu elf Geräte untereinander und verdrängt den Treffertext; `<mark>` mit Polster zerreißt Wörter („IP - Adressen“); die Marken „Stichwort“ und „Bedeutung“ sind unerklärt.

## Umfang

- Erste Fundstelle zeigen, weitere als „+N weitere Geräte“ ausklappbar (`aria-expanded`).
- `<mark>` ohne seitliches Polster (`px-0`, `box-decoration-clone`).
- Marken mit Erklärung (`title` und für Screenreader `sr-only`-Text) in de/en.
- Tests (Vitest; e2e, wo Layout oder Bedienung sich ändern) für das neue Verhalten; bestehende Tests angepasst, nicht abgeschwächt.
- Doku: `web/src/pages/README.md` bzw. `web/src/theme/README.md` nachziehen, wo betroffen.

## Nicht-Ziele

- Keine neue Abhängigkeit, keine Änderung an API oder Backend.
- Nur der genannte Bereich; andere Befunde der UI-Analyse haben eigene Aufträge.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/pages/search/SearchHitView.tsx`, `web/src/pages/SearchPage.tsx`, `web/src/locales/*/search.json`, Tests

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
