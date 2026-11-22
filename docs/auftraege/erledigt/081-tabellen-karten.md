# Auftrag 081 – Tabellen auf schmalen Bildschirmen als Karten

Meilenstein: Gestaltung (D1) · Freigabestufe: C (entschieden mit E-65) · Status: erledigt

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

**Status: zur Prüfung.** Kriterien 0–4 erfüllt. Keine neue Abhängigkeit, keine Änderung an API oder Backend, keine offene Frage an a7.

**Was wurde gebaut?**

- Neuer Baustein `web/src/components/ui/ResponsiveTable.tsx`: Der Aufrufer beschreibt Zeilen und Spalten einmal; ab 768 px (`md`, `matchMedia("(min-width: 48rem)")`) entsteht eine `<table>` mit `<th scope="col">`, darunter eine `<ul>` mit gestapelten Karten (`<li>`, Rand `line` auf `surface`, 12 px Innenabstand). Es steht immer nur eine Form im Dokument (Tabellen-Semantik ab `md`, Liste mit Überschrift je Karte darunter); Wechsel beim Ändern der Fensterbreite sofort, ohne Animation. Ohne Media-Queries (jsdom) bleibt es Tabelle.
- Platz je Spalte auf der Karte (`card`): `title` (Überschrift, Stufe per `cardHeadingLevel`), `action` (rechts neben der Überschrift, z. B. Download-Icon-Knopf), `status` (unter der Überschrift, Spaltenname nur für Screenreader), `field`/`wide` (Beschriftung/Wert-Paare als `dl`, `wide` über die volle Breite), `detail` (ohne Beschriftung, z. B. Prüfsumme), `none`. `cardCell` ersetzt den Inhalt auf der Karte, `table: false` blendet eine Spalte in der Tabelle aus, `rowNote` ersetzt die Spalten ab einer Stelle durch einen Hinweis („Keine Version": `colspan` in der Tabelle, Absatz auf der Karte). Liste und Tabelle tragen denselben zugänglichen Namen und dieselben `data-testid`; Zeilenattribute landen auf `<tr>` bzw. `<li>`.
- Angewendet (die Tabellen-Darstellung aus 079 bleibt Klasse für Klasse gleich: Detailzeilen, `DownloadIconLink`, Prüfsumme als details/summary, übersetzte Protokoll-Feldnamen, „Technische Angaben" mit Rohdaten):
  - Dateien (`DeviceFiles.tsx`): Karte mit Titel-Link als `h3`, Download rechts, Einlese-Status, dann Art, Version, Hochgeladen (mit Benutzer), Größe; Prüfsumme am Ende.
  - Versionen (`DocumentPage.tsx`): „Version N" als `h3`, Download, Status mit Meldung und „Erneut einlesen", dann Hochgeladen, Größe, Dateiname; Prüfsumme am Ende.
  - Einlesen (`IngestPage.tsx`): Datei-Link als `h2`, Status mit Meldung/Knopf/„Älterer Versuch", dann Gerät, Version · Dateiname, Zeitpunkte, (manage) Angestoßen von. Neuer Text `column.version` (de/en „Version").
  - Änderungsprotokoll (`AuditTrail.tsx`): Objekt mit ID als Überschrift (`h2` auf `/audit`, neue Eigenschaft `cardHeadingLevel`, die Dateiseite übergibt 3), Aktion darunter, dann Zeitpunkt, Benutzer, Objektart, Änderungen über die volle Breite.
- Doku: `web/src/components/ui/README.md` (Abschnitt „Data tables and cards", Tests), `web/src/pages/README.md` (Dateien, Änderungsprotokoll, Einlesen).

**Wie wurde getestet?**

- Kriterium 0: `docker version` Exit 0, `docker compose version` (v5.7.0) Exit 0.
- Kriterium 1: Web-Job wie in `ci.yml` (Projekt `twox-081-web`, vor dem Build `web/dist` und `web/playwright-report` gelöscht): lint, typecheck, test (**45 Dateien, 901 Fälle**), build, licenses („License check passed.") jeweils Exit 0; `api:generate` Exit 0, `git diff --exit-code -- web/openapi web/src/api` Exit 0, `git status --porcelain` dazu leer. Bestehende Tests unverändert grün (keine Erwartung abgeschwächt).
- Neue Vitest-Fälle: `ResponsiveTable.test.tsx` (Tabelle ohne Media-Queries und ab 768 px, Karten darunter, Überschriftenstufen 2/3/4, Plätze auf der Karte, Status mit Screenreader-Beschriftung, `dl`-Paare, Hinweis statt Spalten mit `colspan`, Wechsel bei Breitenänderung, Media-Query wirft); je Ansicht ein Block „narrow screens" in `DeviceFiles.test.tsx`, `DocumentPage.test.tsx`, `IngestPage.test.tsx`, `AuditTrail.test.tsx` (Liste statt Tabelle, Überschriften, Paare, Knöpfe, Prüfsumme, „Keine Version" als Karte und als `colspan`-Zelle, deutsche Beschriftungen).
- Kriterium 2: e2e wie in `ci.yml` (Projekt `twox-081`, API-Port 18081, Testkonto per `create_account`): **67 passed, 1 skipped** (lokaler Teil der M2-Abnahme wie in der CI). Neu `web/e2e/tables-narrow.spec.ts`: bei 375 px Datei hochladen, Karten auf Geräte-, Datei-, Einlese- und Protokollseite, kein seitliches Scrollen der Seite; bei 1024 px wieder Tabellen.
- Kriterium 3: Sichtprüfung im eingebauten Browser gegen das eigene Projekt (eigener Hostname, siehe Abweichungen), Deutsch:
  - 375 px hell und dunkel: alle vier Ansichten als Karten, Seitenbreite 375/375 px auf Geräte-, Datei-, Einlese- und Protokollseite (vorher laut Analyse Dateien 858 px in 309 px, Einlesen 705 px in 343 px). Lange Dateinamen und Titel brechen an Bindestrichen um; Download-Knopf rechts oben; Status-Abzeichen, Fehlermeldung, „Technische Angaben" und „Erneut einlesen" gut lesbar, auch dunkel.
  - 768 px (Grenze): Tabellen. Seite 753/768 px, aber Protokoll (865 in 721 px), Einlesen (852 in 721) und Dateien (728 in 687) scrollen in ihrem Kasten waagerecht – siehe Hinweis unten.
  - 1024 px hell: Dateien 943/943, Versionen 943/943, Protokoll 977/977, Einlesen 977/977 px – wie nach 079.
  - 1440 px hell: 958/958, 958/958, 992/992, 992/992 px. 1600 px dunkel: Dateitabelle 958/958 px, unverändert.
- Kriterium 4: `down -v` beider Projekte Exit 0; danach kein Container und kein Volume mit `twox-081`.

**Zweig und Arbeitsverzeichnis**

Zweig `worktree-agent-abc8ed3a4f4b9f834`, Arbeitsverzeichnis `.claude/worktrees/agent-abc8ed3a4f4b9f834`. Nicht gepusht, nicht zusammengeführt.

**Abweichungen und Hinweise**

- Zusätzlich berührt (eng zugehörig): `web/src/locales/{de,en}/ingest.json` (ein Text), `web/e2e/tables-narrow.spec.ts` (neu), `web/src/pages/README.md`.
- Die Sichtprüfung habe ich bei 375, 768, 1024, 1440 und 1600 px gemacht (Auftrag nennt 375/1024/1600, die Leitstelle 375/768/1440).
- Für die Sichtprüfung in meiner lokalen `.env` (nicht eingecheckt) `twox081.localhost` zu `TWOX_ALLOWED_HOSTS` ergänzt (wie 079), damit die Anmeldung nicht mit parallelen Projekten auf 127.0.0.1 kollidiert.
- Zwischen 768 und etwa 900 px scrollen drei Tabellen noch in ihrem Kasten (die Seite selbst nicht). E-65 legt die Grenze bei 768 px fest; ich habe sie nicht verschoben. Falls a7 das stört: Grenze auf 1024 px (`lg`) ist eine Zeile (`WIDE_TABLE_QUERY`).
- Beim ersten e2e-Lauf schlug `structure-tree.spec.ts` („devices … fixed columns", einmal bei 1024, einmal bei 1600 px, „one line per device": 14 statt < 8 px) fehl; die Datei stammt aus 083 und wird hier nicht berührt. Allein dreimal hintereinander grün, der vollständige Lauf danach ebenfalls grün – wirkt wackelig (Zeitpunkt der Messung), nicht von diesem Auftrag verursacht.
- Der erste e2e-Lauf nutzte noch ein vor den Änderungen gebautes `api`-Image (die neue Spec schlug deshalb fehl); nach Neubau grün.
