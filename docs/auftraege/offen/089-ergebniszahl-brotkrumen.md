# Auftrag 089 – Ergebniszahl als Live-Region, Brotkrumen auf der Dateiseite

Meilenstein: Gestaltung (D1) · Freigabestufe: B · Status: offen

Voraussetzung: 077, 079 und 083 sind auf `main`.

## Ziel

Gefilterte Listen (Protokoll, Einlesen) melden die Trefferzahl Screenreadern nicht; die Dateiseite zeigt als Brotkrumen nur „Datei“, die Geräteseite den ganzen Pfad.

## Umfang

- Gemeinsamer Baustein „Ergebniszahl“ mit `role="status"` für Protokoll und Einlesen (Struktur macht 083).
- Brotkrumen der Dateiseite: Standort › Bereich › Anlage › Gerät › Datei, gemeinsamer Baustein mit der Geräteseite.
- Tests (Vitest; e2e, wo Layout oder Bedienung sich ändern) für das neue Verhalten; bestehende Tests angepasst, nicht abgeschwächt.
- Doku: `web/src/pages/README.md` bzw. `web/src/theme/README.md` nachziehen, wo betroffen.
- Nachtrag der Leitstelle (Prüfung 068): `IngestError` in `web/src/components/files/IngestStatus.tsx` zeigt den Hinweis „Nur teilweise umgewandelt“ auch, wenn ein Auftrag `failed` ist und `partly_converted` wahr (zusätzlich zur Fehlermeldung), sowie bei wartenden/laufenden Einbettungsaufträgen mit `partly_converted`; Tests anpassen (`IngestStatus.test.tsx`). `IngestStatus.tsx` und der Test gehören dafür zu den betroffenen Bereichen.

## Nicht-Ziele

- Keine neue Abhängigkeit, keine Änderung an API oder Backend.
- Nur der genannte Bereich; andere Befunde der UI-Analyse haben eigene Aufträge.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/components/AuditTrail.tsx`, `web/src/pages/IngestPage.tsx`, `web/src/pages/DocumentPage.tsx`, `web/src/pages/DevicePage.tsx`, neu Baustein unter `web/src/components/`, Tests

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
