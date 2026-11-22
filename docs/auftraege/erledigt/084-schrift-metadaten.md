# Auftrag 084 – Schriftgröße der Metadaten

Meilenstein: Gestaltung (D1) · Freigabestufe: C (entschieden mit E-65) · Status: erledigt

Voraussetzung: 077, 079 und 083 sind auf `main` (dieselben Dateien).

## Ziel

12 px wird sehr häufig verwendet (Zeitpunkte, Statusdetails, Protokollfelder, Art-Kennzeichen) – für Fachanwender am Werkstattrechner oder Tablet grenzwertig. Nach E-65 (5) sind Metadaten 13–14 px, 12 px nur für Großbuchstaben-Kennzeichen.

## Umfang

- Ein Token bzw. eine Klasse für Metadaten (13 px) in `index.css`/Theme; `text-xs` an den betroffenen Stellen ersetzen, außer bei Großbuchstaben-Kennzeichen.
- Kontraste der kleineren Texte über `theme/contrast.test.ts` abgesichert.
- Tests (Vitest; e2e, wo Layout oder Bedienung sich ändern) für das neue Verhalten; bestehende Tests angepasst, nicht abgeschwächt.
- Doku: `web/src/pages/README.md` bzw. `web/src/theme/README.md` nachziehen, wo betroffen.

## Nicht-Ziele

- Keine neue Abhängigkeit, keine Änderung an API oder Backend.
- Nur der genannte Bereich; andere Befunde der UI-Analyse haben eigene Aufträge.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/index.css` (Typografie-Abschnitt), `web/src/theme/`, betroffene Seiten und Komponenten (Austausch der Klasse), Tests

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

- Token `--text-meta` (13 px, Zeilenhöhe 18 px) im `@theme`-Block von `web/src/index.css`; Tailwind macht daraus die Klasse `text-meta`. Alle Metadaten nutzen sie, `text-xs` (12 px) bleibt nur bei Großbuchstaben-Kennzeichen (`uppercase tracking-wide`).
- Die Kurztexte der Navigation (082) stehen jetzt auf `text-meta leading-4` statt `text-[13px] leading-4`: gleiche Größe, gleiche Zeilenhöhe 16 px, Kopf weiter 42/76 px. Die Kartenlegende (`text-[13px]`) ebenfalls auf `text-meta`.
- Neuer Quelltext-Test `web/src/theme/sourceTypography.test.ts`: schlägt fehl, wenn `text-xs` ohne `uppercase` in derselben Klassenliste steht, wenn eine Schriftgröße in Pixeln (`text-[13px]`) geschrieben wird oder wenn sich der Token ändert; prüft außerdem, dass `text-meta` genutzt wird.
- `theme/contrast.test.ts`: Liste der Farbpaare kleiner Schrift (13 px und 12 px) mit der Prüfung, dass jedes Paar mit 4,5:1 gemessen wird; dafür neu gemessen: `info` auf `canvas` (Hinweis „läuft bereits" auf der Seite). Alle Paare bestehen in beiden Modi und allen Akzenten, keine Farbe geändert.
- e2e `web/e2e/typography.spec.ts`: misst im Browser 13 px für Prüfsumme, Benutzer, Einlesestatus, Zeitpunkte und Versionszeile, 12 px mit `uppercase` für die Geräteklasse im Strukturbaum, und dass die Tabellen Dateien, Einlesen und Protokoll bei 1024 und 1600 px in ihren Kasten passen und die Seite nicht seitlich scrollt.
- Doku: `web/src/theme/README.md` (neuer Abschnitt „Small text"), `web/src/pages/README.md` (Navigation, Landkarte).

**Alle Vorkommen von `text-xs` (vorher 25 in `web/src`) und Entscheidung**

| Datei | Stelle | Entscheidung |
| --- | --- | --- |
| `components/AuditTrail.tsx` | Objekt-ID unter dem Objekt | Metadaten → `text-meta` |
| `components/AuditTrail.tsx` | „Technische Angaben" (details) | Metadaten → `text-meta` |
| `components/AuditTrail.tsx` | Rohdaten (`pre`, Monospace) | Metadaten → `text-meta` |
| `components/AuditTrail.tsx` | unbekannter Feldname (`code`) | Metadaten → `text-meta` |
| `components/files/IngestStatus.tsx` | Status-Abzeichen | Statusdetail → `text-meta` |
| `components/files/IngestStatus.tsx` | Zähler (Abschnitte usw.) | Metadaten → `text-meta` |
| `components/files/IngestStatus.tsx` | Fehlertext | Statusdetail → `text-meta` |
| `components/files/IngestStatus.tsx` | Hinweis „läuft bereits" (409) | Statusdetail → `text-meta` |
| `components/files/IngestStatus.tsx` | Hinweis „abgelehnt" (400) | Statusdetail → `text-meta` |
| `components/files/parts.tsx` | Prüfsumme | Metadaten → `text-meta` |
| `components/files/parts.tsx` | Benutzer unter dem Zeitpunkt | Metadaten → `text-meta` |
| `pages/IngestPage.tsx` | Gerätekennung unter dem Namen | Metadaten → `text-meta` |
| `pages/IngestPage.tsx` | Spalte Zeitpunkte | Metadaten → `text-meta` |
| `pages/IngestPage.tsx` | Zeile „Version N · Dateiname" | Metadaten → `text-meta` |
| `pages/IngestPage.tsx` | Hinweis „neuerer Versuch vorhanden" | Statusdetail → `text-meta` |
| `pages/map/nodes.tsx` | Kennung des Gruppenknotens | Metadaten → `text-meta` |
| `pages/map/nodes.tsx` | Kennung, IP, Modell des Geräteknotens | Metadaten → `text-meta` (3 Stellen) |
| `pages/map/nodes.tsx` | Art des Gruppenknotens (STANDORT …) | Großbuchstaben-Kennzeichen → bleibt `text-xs` |
| `pages/map/nodes.tsx` | Art des Netzknotens (NETZ) | Großbuchstaben-Kennzeichen → bleibt `text-xs` |
| `pages/StructurePage.tsx` | `KIND_LABEL_CLASS` (Art und Geräteklasse im Baum) | Großbuchstaben-Kennzeichen → bleibt `text-xs` |
| `pages/search/SearchHitView.tsx` | Abzeichen Stichwort/Bedeutung | Metadaten (nicht in Großbuchstaben) → `text-meta` |
| `pages/search/SearchHitView.tsx` | Abzeichen „ältere Version" | Metadaten → `text-meta` |
| `pages/SettingsPage.tsx` | Akzent-Vorschau „Aa" | keine Metadaten, sondern dekoratives Muster (`aria-hidden`) in einer 32 × 56 px großen Kachel; trotzdem auf `text-meta`, damit die Regel ohne Ausnahme bleibt; passt in die Kachel |

Dazu ohne `text-xs`: `components/Layout.tsx` Kurztexte der Navigation und `pages/MapPage.tsx` Legende, beide von `text-[13px]` auf `text-meta`. Danach gibt es in `web/src` nur noch drei `text-xs`, alle mit `uppercase`.

**Wie wurde getestet?**

- Kriterium 0: `docker version` und `docker compose version` Exit 0.
- Kriterium 1: Web-Job wie in `ci.yml` (Projekt `twox-084-web`): lint, typecheck, test (47 Dateien, 955 Tests), build, licenses grün; `api:generate` ohne Unterschied. Im gebauten CSS steht `.text-meta{font-size:var(--text-meta);line-height:var(--tw-leading,var(--text-meta--line-height))}`, `leading-4` überschreibt also die Zeilenhöhe wie vorgesehen.
- Kriterium 2: e2e wie in `ci.yml` (Projekt `twox-084`, API-Port 18084, Testkonto per `create_account`): 82 bestanden, 1 übersprungen (lokaler Teil der M2-Abnahme, wie in der CI). `navigation.spec.ts`, `layout.spec.ts`, `tables-narrow.spec.ts`, `structure-tree.spec.ts` und `login.spec.ts` unverändert grün.
- Kriterium 3: eigener Tab im eingebauten Browser gegen `twox084.localhost:18084`, Struktur, Gerät, Datei, Einlesen, Protokoll, Suche, Selbsttest, dazu Landkarte; Messung per Skript (Seitenüberlauf, Tabellenbreite zu Kastenbreite, Schriftgrößen aller sichtbaren Texte):
  - 1600 px (dunkel, Struktur hell): kein seitliches Scrollen; Tabellen Gerät 1214/1214, Datei 1214/1214 und 1248/1248, Einlesen 1248/1248, Protokoll 1248/1248. Kein sichtbarer Text unter 13 px außer den Großbuchstaben-Kennzeichen. Landkarte: alle 44 Geräteknoten ohne Überlauf (vier Zeilen passen in 96 px), Legende 13 px.
  - 1024 px hell, Datei auch dunkel: Tabellen Gerät 943/943, Datei 943/943 und 977/977, Einlesen 977/977, Protokoll 977/977; Kopf 76 px; kein Überlauf. Datum, Größe und Benutzer brechen weiterhin nicht um.
  - 375 px hell, Protokoll auch dunkel: alle Seiten als Karten, kein seitliches Scrollen; Kopf 76 px.
  - Optisch: Metadaten wirken etwas ruhiger und besser lesbar, die Dichte der Tabellen ist kaum verändert (Zeilen wenige Pixel höher). Dunkel gut lesbar.
  - Die Suche fand in der Testdatenbank keine Treffer (Textdateien werden ohne Konverter übersprungen); die beiden Abzeichen der Suche sind daher nur über Vitest und `search.spec.ts` geprüft, nicht im Augenschein.
  - Theme nur im `localStorage` umgestellt und danach entfernt; Tab geschlossen.
- Kriterium 4: `down -v` beider Projekte Exit 0.

**Zweig und Arbeitsverzeichnis**

Zweig `worktree-agent-a4578c1c256fe8176`, Arbeitsverzeichnis `.claude/worktrees/agent-a4578c1c256fe8176`. Nicht gepusht.

**Abweichungen**

- Zeilenhöhe 18 px für 13 px gewählt (zwischen `text-xs` 16 px und `text-sm` 20 px), damit Tabellenzeilen kaum wachsen. a7 kann den Wert im Token ändern.
- Zusätzlich angefasst: `pages/MapPage.tsx` (Legende `text-[13px]` → `text-meta`) und `pages/SettingsPage.tsx` (Vorschau „Aa"), damit die neue Quelltextregel ohne Ausnahmen gilt.
- Nicht geändert, zur Kenntnis: die Beschriftung der Netzlinien auf der Landkarte („im Netz") steht mit `fontSize: 11` als Inline-Stil von React Flow (`MapPage.tsx`). Sie ist kein `text-xs` und hängt an jeder Linie; eine größere Schrift würde die Karte dichter machen. Bei Bedarf eigener kleiner Auftrag.
