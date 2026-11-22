# Auftrag 094 – Beschriftung der Netzlinien auf der Landkarte nach E-65

Meilenstein: Gestaltung (D1) · Freigabestufe: B · Status: zur Prüfung

## Ziel

Folgepunkt aus der Prüfung von 084: Die Beschriftung der Netzlinien auf der Landkarte („im Netz“ / „in network“) steht als Inline-Stil `labelStyle: { fontSize: 11, … }` in `web/src/pages/MapPage.tsx`. Nach E-65 Punkt 5 haben Metadaten 13–14 px; 12 px sind nur für Großbuchstaben-Kennzeichen erlaubt. Die Quelltextregel aus 084 (`web/src/theme/sourceTypography.test.ts`) erfasst Inline-Schriftgrößen bisher nicht.

## Umfang

- Linienbeschriftung auf die Metadaten-Stufe aus 084 setzen (13 px, möglichst über den Token `--text-meta`, sonst 13).
- `sourceTypography.test.ts` so erweitern, dass Inline-Schriftgrößen unter 13 px (z. B. `fontSize: 11` oder `fontSize: "12px"`) im Quelltext auffallen; Ausnahme nur für Großbuchstaben-Kennzeichen, falls es solche als Inline-Stil gibt.
- Sichtprüfung: Die Beschriftung passt weiter an die Linien und überdeckt keine Knoten.

## Nicht-Ziele

- Kein Umbau der Landkarte, keine Änderung an Einpassen oder Zoom.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/pages/MapPage.tsx`, `web/src/theme/sourceTypography.test.ts`, ggf. `web/src/pages/map/MapPage.test.tsx`, `web/src/theme/README.md`

## Akzeptanzkriterien (prüfbar)

1. Im gebauten Frontend ist die Linienbeschriftung 13 px groß (Vitest oder e2e-Messung).
2. `sourceTypography.test.ts` schlägt bei einer Inline-Schriftgröße unter 13 px fehl (belegt durch einen Testfall mit Beispieltext) und ist auf dem Stand grün.
3. Sichtprüfung bei 1024 und 1600 px, hell und dunkel.
4. Alle Prüfungen aus `.github/workflows/ci.yml` (web, e2e) sind grün.

## Vorgaben und Hinweise

- Kurzberichte von 080, 084 und 093 lesen.

## Fragen an a7 (mit Optionen und Empfehlung)

## Kurzbericht (füllt der Auftragsbearbeiter aus)

Status: zur Prüfung

**Was wurde gebaut?**

- `web/src/pages/MapPage.tsx`: `labelStyle` der Netzlinien jetzt `fontSize: "var(--text-meta)"` statt `11`. Der Token wirkt: React Flow setzt `labelStyle` als Inline-Stil am SVG-Text, die berechnete Schriftgröße ist 13 px (gemessen, siehe unten). Der Rückfall auf die Zahl 13 war nicht nötig.
- `web/src/theme/sourceTypography.test.ts`: neue Regel „keine Inline-Schriftgröße unter 13 px“. Erfasst `fontSize: 11`, `fontSize: "12px"`, `fontSize: "0.75rem"` und `font-size: 11px` in Quelltextstrings (rem/em mal 16). Ausnahme: ein Stilobjekt, das auch `textTransform: "uppercase"` setzt. Keine Treffer bei `var(--text-meta)`, ab 13 px, bei anderen Zahlen (`strokeWidth: 11`, `zIndex: 12`, `width: 11`) und bei `const fontSizes = [11, 12]`.
- Beleg, dass die Regel fehlschlägt: Testfall mit Beispieltexten (`finds an inline font size below 13 px in an example text, and nothing else`) und zusätzlich Gegenprobe am echten Quelltext: `MapPage.tsx` kurz auf `fontSize: 11` zurückgesetzt, `sourceTypography.test.ts` schlägt fehl („../pages/MapPage.tsx: fontSize: 11“), danach wiederhergestellt.
- `web/e2e/map.spec.ts`: misst im gebauten Frontend die Beschriftung der aktiven Linie („in network“) mit 13 px.
- `web/src/theme/README.md`: Abschnitt „Small text“ um die neue Regel und die Linienbeschriftung ergänzt.

**Wie wurde getestet?**

- Web-Job wie `ci.yml` (Projekt `twox-094-web`): `npm ci`, lint, typecheck, test, build, licenses alle Exit 0; `api:generate` Exit 0, keine Änderung an `web/openapi` oder `web/src/api`.
- e2e wie `ci.yml` (Projekt `twox-094`, API-Port 18094, Testkonto per `create_account`): 82 bestanden, 1 übersprungen (lokaler Teil der M2-Abnahme, wie in der CI), darunter `map.spec.ts` mit der 13-px-Messung.
- Sichtprüfung (eigener Tab, `twox094.localhost:18094`, Testdatenbank mit vielen Linien aus den e2e-Läufen): bei 1600 px dunkel, 1600 px hell, 1024 px hell und 1024 px dunkel je 37 Linienbeschriftungen, berechnete Größe überall 13 px, keine überdeckt einen Knoten (Messung der Rechtecke aller Beschriftungen gegen alle Knoten, 0 Überschneidungen), kein seitliches Scrollen bei 1024 px. Bildschirmfotos nur im Fenster, nicht eingecheckt. Die Beschriftung bleibt klein auf dem Bildschirm, weil die Karte bei dieser Datenmenge auf etwa 0,6 herausgezoomt ist (wie die Knotentexte); die Schrift selbst ist 13 px im Kartenmaß.
- `down -v` beider Projekte Exit 0; Tab geschlossen, Viewport zurückgesetzt.

**Zweig und Arbeitsverzeichnis**

- Zweig `worktree-agent-a6dbfd129c6f44d8f`, Arbeitsverzeichnis `.claude/worktrees/agent-a6dbfd129c6f44d8f`. Nicht gepusht.

**Abweichungen**

- Zusätzlich angefasst: `web/e2e/map.spec.ts` (Messung) statt `MapPage.test.tsx`, weil jsdom keine berechneten Stile aus CSS-Variablen auflöst. Kein Eingriff in Landkarte, Einpassen oder Zoom; keine neue Abhängigkeit.
- Es gibt keine Inline-Großbuchstaben-Kennzeichen im Quelltext; die Ausnahme in der Regel ist daher nur vorsorglich und im Testfall belegt.
