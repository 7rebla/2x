# Auftrag 074 – Eigene Geräte-Icons in Baum, Geräteseite und Landkarte

Meilenstein: Gestaltung (D1, parallel zu M2) · Freigabestufe: B · Status: offen

## Ziel

Die acht von a7 bestätigten eigenen Icons (Anlage, generisches Gerät, SPS, Controller, Rechner, Router, Roboter, Firewall) werden in die Icon-Schicht aus 071 aufgenommen und je Gerätetyp (Feld aus 073) im Strukturbaum, auf der Geräteseite, in Brotkrumen und auf der Landkarte angezeigt.

## Umfang

- SVG-Dateien unverändert übernehmen nach `web/src/icons/industrial/` und als typisierte Komponenten im Icon-Mapping aus 071 registrieren (`currentColor`, 24er-Raster, Strich 2 – passend zu Lucide).
- Zentrales Mapping `device_class → IconName` an einer Stelle; `other` und fehlender Wert → generisches Gerät; Anlagen → Anlagen-Icon.
- Einsatz: Strukturbaum (Gerät- und Anlagenzeilen), Geräteseite (Kopf), Brotkrumen, Landkarte (Geräte- und Anlagenknoten). Icon dekorativ (`aria-hidden`), der Typ steht zusätzlich als Text (z. B. Tooltip/Feld „Gerätetyp“) – nie nur Symbol.
- Tests: Vitest für das Mapping (jeder Typ → erwartetes Icon, Fallback), Rendern in Baum und Kartenknoten; Playwright: ein Gerät mit Typ `plc` zeigt das SPS-Icon im Baum und auf der Karte.

## Nicht-Ziele

- Weitere Icons, Anlagentyp-Icons, Statusanzeigen.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/icons/industrial/` (neu), `web/src/icons/` (Mapping), `web/src/pages/StructurePage.tsx` bzw. `pages/structure/`, `web/src/pages/DevicePage.tsx`, `web/src/pages/map/nodes.tsx`, betroffene Tests, `web/e2e/` (Prüfung im bestehenden oder neuen Spec)

## Akzeptanzkriterien (prüfbar)

`W` = `docker compose -p twox-074-web -f deploy/compose/compose.web.yaml`, `D` = `docker compose -p twox-074`, `.env` mit `TWOX_API_PORT=18074`.

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Web-Job aus `ci.yml` komplett grün.
2. Übernommene SVGs byte-gleich mit der Vorlage (SHA-256 je Datei im Kurzbericht).
3. Browser-Test wie in `ci.yml` (inkl. „Create test account“) bestanden, zweimal ohne `down -v`.
4. Abräumen mit `down -v` endet mit Exit 0.

## Vorgaben und Hinweise

Voraussetzung: 071 (Icon-Schicht) und 073 (Feld `device_class`) sind auf `main`.

- Vorlage liegt NUR im Hauptordner (ignoriert): `docs/design/bildmarke/geraete-icons/iteration-2/icons/` (acht `.svg`, Regeln in der README dort). Nur diese acht SVGs übernehmen; vor dem Commit prüfen, dass sie keinen Text außer SVG-Daten enthalten. Im Design-Ordner kommt ein künftiger Produktname vor – nie in Code, Commits, Kurzbericht oder Schlussantwort schreiben.
- Keine neue Abhängigkeit. Sprache: Code Englisch, Kurzbericht Deutsch. Keine Personennamen, keine lokalen Pfade mit Benutzernamen. Nur ausdrücklich genannte Pfade stagen. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine: Icons von a7 bestätigt; Typfeld nach E-53.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
