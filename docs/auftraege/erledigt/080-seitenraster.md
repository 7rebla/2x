# Auftrag 080 – Einheitliches Seitenraster

Meilenstein: Gestaltung (D1) · Freigabestufe: C (entschieden mit E-65) · Status: erledigt

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

**Was wurde gebaut?**

- `Layout.tsx`: Kopf und Inhalt nutzen ein gemeinsames Raster `PAGE_GRID` (`mx-auto w-full max-w-7xl px-4`); die frühere Kombination `max-w-5xl` / `xl:max-w-7xl` ist weg. Absätze direkt in der `<section>` einer Seite (Einleitungen) begrenzt `PAGE_PROSE` (`[&>section>p]:max-w-prose`) auf `<main>` – die Seiten selbst mussten dafür nicht geändert werden.
- `SelftestPage.tsx`: Kopf (Überschrift und Knopf) bleibt in einer schmalen Spalte (`max-w-xl`), die Ergebniskarten stehen unter 1024 px in einer Spalte, ab 1024 px (`lg`) in zwei und ab 1280 px (`xl`) in drei.
- `SettingsPage.tsx`: bleibt eine schmale Spalte (`max-w-2xl`, jetzt mit `w-full`) am linken Rand des Rasters; nur Kommentar und Klasse.
- `MapPage.tsx`: Die Karte nimmt die ganze Rasterbreite ein und reicht bis zum unteren Fensterrand (`useRestHeight`: Fensterhöhe minus Lage der Karte minus 32 px Innenabstand von `main`, neu gemessen bei Größenänderung). Mindesthöhe 28rem wie bisher, bis zur Messung 70vh. „Ansicht einpassen“ (beim Öffnen und per Knopf) begrenzt den Zoom auf 0,6 bis 1,25 (`FIT_VIEW_OPTIONS`). Die Legende steht als kleines Feld oben rechts in der Karte (React-Flow-`Panel`, `role="note"`, Name „Legende“/„Legend“) mit einem Muster der gestrichelten Linie; unter 640 px sind die Details nur für Screenreader da.
- `locales/{de,en}/map.json`: `legend` ist jetzt ein Objekt (`label`, `dashed`, `inNetwork`, `detail`) statt eines einzelnen Satzes.
- Doku: `web/src/pages/README.md` (Abschnitte „Frame and navigation“ und „Map“).

**Messung bei 1600 px** (eigenes Projekt, im eingebauten Browser und im e2e-Test): Marke 176 px, Seitentitel 176 px (Landkarte, ohne Scrollleiste); auf der Strukturseite mit Scrollleiste (Seitenbreite 1585 px) beide 168,5 px. Vorher lagen 169 und 297 px auseinander (UI-Analyse). Raster 1280 px, Einleitung 654 px breit.

**Wie wurde getestet?**

0. `docker version` und `docker compose version`: Exit 0.
1. Web-Job wie in `ci.yml` (Projekt `twox-080-web`): lint, typecheck, test (883 Tests), build, licenses – alle Exit 0; `api:generate` ohne Unterschied.
2. e2e wie in `ci.yml` (Projekt `twox-080`, frische Datenbank nach `down -v`, Testkonto per „Create test account“): 72 bestanden, 1 übersprungen, Exit 0. Neu: `web/e2e/layout.spec.ts` (gleiche linke Kante von Marke und Titel bei 375/1024/1600 px, gleiche Rasterbreite, Einleitung schmaler als das Raster, Selbsttest-Karten in 3/2/1 Spalten, Einstellungen 672 px breit, Karte in Rasterbreite bis 32 px über dem Fensterrand, Legende in der Ecke, Zoom nach Einpassen zwischen 0,6 und 1,25, bei 375 px kein waagerechtes Scrollen und kompakte Legende). Vitest: neue Fälle in `Layout.test.tsx`, `SelftestPage.test.tsx`, `SettingsPage.test.tsx` und `map/MapPage.test.tsx` (Legende de/en, Resthöhe mit Größenänderung); die alte Prüfung des Legendensatzes über der Karte ist durch die Prüfung der Eckenlegende ersetzt.
3. Sichtprüfung im eingebauten Browser gegen 127.0.0.1:18080 bei 1600, 1024 und 375 px, hell und dunkel: Marke und Titel bündig auf allen Breiten; Selbsttest drei Karten nebeneinander (1600), zwei plus eine (1024), gestapelt (375); Karte füllt bei 1600×900 den Rest des Fensters (552 px hoch, Seite scrollt nicht), bei 375 px Mindesthöhe; Legende im Dunkelmodus gut lesbar. Kein waagerechtes Scrollen auf Struktur, Karte, Selbsttest und Einstellungen.
4. `down -v` beider Projekte (`twox-080`, `twox-080-web`): Exit 0.

**Zweig und Arbeitsverzeichnis:** `worktree-agent-a7c51dea93169bc53`, `.claude/worktrees/agent-a7c51dea93169bc53`.

**Abweichungen und Beobachtungen**

- `web/src/locales/{de,en}/map.json` geändert (nicht in „Betroffene Bereiche“, aber nach „Texte in Deutsch und Englisch“ nötig). `nodes.tsx` und `index.css` blieben unverändert; nötig war dort nichts.
- Einpassen hat zusätzlich eine Obergrenze 1,25 (vorher 2), damit eine kleine Struktur nicht nur aus zwei riesigen Knoten besteht. Die Suche passt weiter auf alle Treffer ein, ohne Mindestzoom (sonst lägen Treffer außerhalb der Karte).
- Bei Mindestzoom 0,6 und großer Struktur zeigt das Einpassen die Mitte der Struktur; der Rest ist über Verschieben, Übersichtskarte oder Herauszoomen erreichbar. Alternative wäre, oben links zu beginnen – bei Bedarf eigener Auftrag.
- Mindesthöhe der Karte: zunächst 24rem gesetzt; bei 1280×720 wurde die Karte damit kleiner als vorher und `map.spec.ts` schlug auf einer Datenbank mit Daten aus drei Läufen fehl (Suche nach einer Adresse mit vielen Treffern). Deshalb bleibt es bei 28rem wie bisher; danach grün auf frischer Datenbank.
- Einmal ist `structure-tree.spec.ts` („fixed columns at 1024 px“, Kennung in zweiter Zeile) fehlgeschlagen; dreimal einzeln wiederholt und im nächsten Gesamtlauf grün. Bei 1024 px ist die Inhaltsbreite unverändert (vorher und nachher 992 px), daher halte ich es für wackelig und nicht durch 080 verursacht.
- Beobachtung außerhalb des Auftrags: Die Übersichtskarte (MiniMap) erscheint bei vielen Knoten als fast leere helle Fläche, bei 375 px nimmt sie viel Platz ein.
