# Auftrag 083 – Strukturbaum entrümpeln

Meilenstein: Gestaltung (D1) · Freigabestufe: C (entschieden mit E-65) · Status: zur Prüfung

Voraussetzung: 077 ist auf `main`.

## Ziel

Jede Zeile des Strukturbaums trägt zwei umrandete Knöpfe (über 20 bei 13 Geräten); bei 375 px stehen sie zwischen Name und Kennung; Kennung und IP beginnen je nach Typtext an anderer Stelle; der Baum ist nicht einklappbar. Nach E-65 (4) wird das behoben.

## Umfang

- Aktionen „Bearbeiten“ und „Neu …“ als Icon-Knöpfe rechts (Stift, Plus) mit `aria-label`; am Desktop bei Hover/Fokus der Zeile deutlich, auf Touch immer sichtbar.
- Gerätezeilen im Raster: Typ-Icon, Name, Kennung, IP in festen Spalten; Typtext als Tooltip bzw. Kurzform.
- Bereiche und Anlagen einklappbar (Knopf mit `aria-expanded`), Zustand je Browser in `localStorage` (mit try/catch); die Suche klappt Treffer auf.
- Trefferzahl des Filters als Live-Region (`role="status"`).
- Tests (Vitest; e2e, wo Layout oder Bedienung sich ändern) für das neue Verhalten; bestehende Tests angepasst, nicht abgeschwächt.
- Doku: `web/src/pages/README.md` bzw. `web/src/theme/README.md` nachziehen, wo betroffen.

## Nicht-Ziele

- Keine neue Abhängigkeit, keine Änderung an API oder Backend.
- Nur der genannte Bereich; andere Befunde der UI-Analyse haben eigene Aufträge.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/pages/StructurePage.tsx`, `web/src/pages/StructurePage.test.tsx`, `web/src/locales/*/` (nur neue Texte), e2e für den Baum

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

**Was wurde gebaut?**

- `StructurePage.tsx`: Zeilen von Standort, Bereich und Anlage haben links die beschreibenden Teile (Art, Name, Kennung, Gerätezahl; umbrechend) und rechts „Bearbeiten“ und „Neu …“ als Icon-Knöpfe (Stift, Plus; `Button` `ghost`/`sm`, 28 px). `aria-label` wie bisher („Edit plant …“, „New device in …“), zusätzlich als Tooltip (`title`). Mit feinem Zeiger (Maus) sind die Knöpfe durchsichtig, bis die Zeile überfahren wird oder den Fokus hat (`pointer-fine:opacity-0`, `group-hover`, `group-focus-within`); auf Touch immer sichtbar. Die Überblendung ist eine Transition und entfällt bei „Bewegung reduzieren“.
- Geräte einer Anlage stehen in einem Raster (Zeilen als Subgrid): Typ, Name, Kennung, IP in festen Spalten. Ab 640 px Typ-Icon mit Text, darunter nur Icon mit Typtext als Tooltip und für Screenreader (`sr-only sm:not-sr-only`); Kennung und IP dann in zweiter Zeile unter dem Namen. Ab 1024 px Mindestbreiten der Spalten (11rem/8rem/8rem), damit auch verschiedene Anlagen bündig stehen.
- Bereiche und Anlagen mit Kindern sind einklappbar: Knopf mit Chevron vor der Zeile, `aria-expanded`, `aria-controls` (solange offen), Namen „Contents of area …“/„Inhalt von Bereich …“ und „Devices of plant …“/„Geräte von Anlage …“. Eingeklappte Kinder werden nicht gerendert, die Gerätezahl bleibt. Zustand je Browser in `localStorage` (`twox.structure.collapsed`, alle Zugriffe mit try/catch) über das neue Modul `pages/structure/collapse.ts`. Die Suche klappt alle Treffer auf, ohne den gespeicherten Zustand zu ändern; Einklappen während einer Suche gilt nur für diesen Suchtext, Aufklappen wird gespeichert. „Neue Anlage“/„Neues Gerät“ klappt den Bereich bzw. die Anlage auf.
- Live-Region (`role="status"`) unter dem Suchfeld: „N Geräte angezeigt“ / „N devices shown“ bzw. „Nichts passt zur Suche.“; ohne Suche leer.
- Neues Icon `disclosure` (Lucide `ChevronDown`) in `web/src/icons/names.ts`; eingeklappt um −90° gedreht.
- Texte de/en in `locales/*/assets.json` (`matchCount`, `toggleArea`, `togglePlant`); Doku in `web/src/pages/README.md` und `web/src/icons/README.md`.

**Wie wurde getestet?**

- Kriterium 0: `docker version` und `docker compose version` Exit 0.
- Kriterium 1: Web-Job wie `ci.yml` im Projekt `twox-083-web`: lint, typecheck, test (42 Dateien, 816 Tests), build, licenses – alle Exit 0; `api:generate` ohne Unterschied in `web/openapi` und `web/src/api`.
- Kriterium 2: e2e wie `ci.yml` im Projekt `twox-083` (Testkonto `e2e-manager` angelegt wie in `ci.yml`): 61 bestanden, 1 übersprungen (M2-Abnahme, lokaler Teil, wie vorgesehen). Neu: `web/e2e/structure-tree.spec.ts` (6 Tests: feste Spalten bei 1024 und 1600 px; 375 px Knöpfe rechts, 28 px, Kennung unter dem Namen, kein seitliches Scrollen; Maus: Deckkraft 0 → 1 bei Hover und Fokus; Touch: immer sichtbar; Einklappen, Erhalt nach Neuladen, Suche klappt auf, Live-Region).
- Vitest: neue Tests in `StructurePage.test.tsx` (Live-Region de/en, Raster und Zellen, Tooltip des Typs, Icon-Knöpfe, Einklappen, Speichern und Wiederherstellen, Suche, Aufklappen bei „Neues Gerät“, ohne nutzbaren Speicher, deutsche Namen) und `structure/collapse.test.ts`.
- Kriterium 3: im eingebauten Browser gegen das eigene Projekt (Daten der Testfabrik aus der M1-Abnahme) bei 375, 1024 und 1600 px, hell und dunkel. Beobachtungen: Spalten Typ/Name/Kennung/IP stehen ab 1024 px über alle Anlagen bündig; Stift und Plus erscheinen am Desktop erst beim Überfahren der Zeile ganz rechts; bei 375 px (Touch-Emulation) stehen die Knöpfe immer sichtbar rechts neben dem Namen, der Baum zerreißt nicht mehr, kein seitliches Scrollen; Geräte zeigen bei 375 px nur das Typ-Icon, Kennung und IP in zweiter Zeile; eingeklappter Bereich zeigt Chevron nach rechts und behält die Gerätezahl. Beide Farbmodi lesbar. Die Seitenüberschrift erscheint in Bildschirmfotos des verborgenen Browserbereichs teils unscharf (Animation, bekannt aus der UI-Analyse), nicht Teil dieses Auftrags.
- Kriterium 4: `down -v` für `twox-083` und `twox-083-web` mit Exit 0.

**Zweig und Arbeitsverzeichnis**

- Zweig `worktree-agent-a8c0d7587afecf31c`, Arbeitsverzeichnis `.claude/worktrees/agent-a8c0d7587afecf31c`.

**Abweichungen**

- Dateien außerhalb der genannten Liste, jeweils klein: `web/src/icons/names.ts` und `web/src/icons/README.md` (neues Icon `disclosure`, Hinweis zur Typanzeige in der Baumzeile), `web/src/pages/structure/collapse.ts` mit Test (Speicherlogik), neue e2e-Datei `web/e2e/structure-tree.spec.ts`. Bestehende e2e-Specs blieben unverändert: die zugänglichen Namen der Knöpfe sind gleich geblieben.
- Bestehender Vitest angepasst, nicht abgeschwächt: Das Plant-Icon wird jetzt am Art-Kennzeichen der Zeile geprüft, weil vor ihm der Einklapp-Knopf mit eigenem Icon steht.
- Sichtprüfung über `127.0.0.1:18083` statt `localhost:18083`, weil parallele Aufträge auf `localhost` dieselben Cookies teilen und die Anmeldung überschrieben. Dabei wurde einmal versehentlich der Browser-Tab eines anderen Auftrags (Port 18085) auf die eigene Adresse umgeleitet; danach nur noch der eigene Tab.
- Keine neue Abhängigkeit, keine Änderung an API oder Backend.
