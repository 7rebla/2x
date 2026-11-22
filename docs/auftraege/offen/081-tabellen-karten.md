# Auftrag 081 – Tabellen auf schmalen Bildschirmen als Karten

Meilenstein: Gestaltung (D1) · Freigabestufe: C (entschieden mit E-65) · Status: offen

Voraussetzung: 079 ist auf `main`.

## Ziel

Bei 375–768 px sind Dateien-, Einlese- und Protokolltabelle doppelt so breit wie der Platz, ohne Hinweis aufs Wischen. Nach E-65 (2) werden Zeilen unter 768 px zu gestapelten Karten.

## Umfang

- Gemeinsamer Baustein (z. B. `components/ui/ResponsiveTable`) bzw. Klassen: unter `md` jede Zeile als Karte mit Titel, Status und Metadaten als Beschriftung/Wert-Paare; ab `md` unverändert Tabelle.
- Anwenden auf Dateien (Gerät, Datei), Einlesen, Änderungsprotokoll.
- Zugänglich: Tabellen-Semantik ab `md`, unter `md` Liste mit Überschrift je Karte.
- Tests (Vitest; e2e, wo Layout oder Bedienung sich ändern) für das neue Verhalten; bestehende Tests angepasst, nicht abgeschwächt.
- Doku: `web/src/pages/README.md` bzw. `web/src/theme/README.md` nachziehen, wo betroffen.

## Nicht-Ziele

- Keine neue Abhängigkeit, keine Änderung an API oder Backend.
- Nur der genannte Bereich; andere Befunde der UI-Analyse haben eigene Aufträge.

## Betroffene Bereiche (Ordner, Dateien)

- neu Baustein unter `web/src/components/ui/`, `web/src/components/DeviceFiles.tsx`, `web/src/pages/DocumentPage.tsx`, `web/src/pages/IngestPage.tsx`, `web/src/components/AuditTrail.tsx`, Tests

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
