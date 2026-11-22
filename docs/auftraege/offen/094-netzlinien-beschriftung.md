# Auftrag 094 – Beschriftung der Netzlinien auf der Landkarte nach E-65

Meilenstein: Gestaltung (D1) · Freigabestufe: B · Status: in Arbeit

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
