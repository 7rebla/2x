# Auftrag 079 – Tabellen am Desktop lesbar

Meilenstein: Gestaltung (D1) · Freigabestufe: B · Status: offen

Voraussetzung: 077 ist auf `main`.

## Ziel

Dateien-, Protokoll- und Einlese-Tabellen brechen Datum, Größe, Version und Benutzer um; die Protokolltabelle zeigt Rohfelder (id, blob_key, sha256, Fremdschlüssel) und lange Hashes und ist schon bei 1280 px breiter als der Platz; die Prüfsumme als Dreieck wirkt wie ein Fehler. Danach sind die Tabellen ruhig lesbar.

## Umfang

- `whitespace-nowrap` für Datum, Größe, Version, Benutzer.
- Prüfsumme und Benutzer in der Dateitabelle in eine Detailzeile oder einen Tooltip; „Herunterladen“ als Icon-Knopf mit `aria-label`.
- Dateinamen: `break-words` statt `break-all`, lange Namen gekürzt mit vollem Namen im `title`.
- Änderungsprotokoll: technische Felder standardmäßig unter „Technische Angaben“ einklappen (wie beim Einlesen), Hashes gekürzt, Feldnamen übersetzt; Rohdaten bleiben aufklappbar.
- Tests (Vitest; e2e, wo Layout oder Bedienung sich ändern) für das neue Verhalten; bestehende Tests angepasst, nicht abgeschwächt.
- Doku: `web/src/pages/README.md` bzw. `web/src/theme/README.md` nachziehen, wo betroffen.

## Nicht-Ziele

- Keine neue Abhängigkeit, keine Änderung an API oder Backend.
- Nur der genannte Bereich; andere Befunde der UI-Analyse haben eigene Aufträge.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/components/DeviceFiles.tsx`, `web/src/pages/DocumentPage.tsx`, `web/src/pages/IngestPage.tsx`, `web/src/components/AuditTrail.tsx`, zugehörige Tests und `locales`

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
