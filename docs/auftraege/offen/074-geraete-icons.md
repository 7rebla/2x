# Auftrag 074 – Eigene Geräte-Icons in Baum, Geräteseite und Landkarte

Meilenstein: Gestaltung (D1, parallel zu M2) · Freigabestufe: B · Status: zur Prüfung

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

**Status: zur Prüfung.** Akzeptanzkriterien 0–4 erfüllt, Läufe am 22.11.2026 im Container (Docker Engine 29.9.3, Compose v5.7.0). Keine neue Abhängigkeit, keine offene Frage an a7.

### Was wurde gebaut?

- **Icons** (`web/src/icons/industrial/`): die acht bestätigten SVGs unverändert übernommen (Dateinamen wie in der Vorlage). Sie werden von der Anwendung nicht importiert, sondern sind die Referenz. `industrial/glyphs.tsx` bildet jede Datei als Komponente auf `SvgGlyph` nach (`PlantGlyph`, `DeviceGlyph`, `PlcGlyph`, `ControllerGlyph`, `ComputerGlyph`, `RouterGlyph`, `RobotGlyph`, `FirewallGlyph`).
- **Tabelle** (`web/src/icons/names.ts`): `plant` und `device` zeigen jetzt die eigenen Zeichnungen (Lucide `Factory` und `Cpu` entfernt); neu `devicePlc`, `deviceController`, `deviceComputer`, `deviceRouter`, `deviceRobot`, `deviceFirewall`.
- **Zentrales Mapping** (`web/src/pages/structure/deviceClass.ts`): Tabelle `device_class → IconName` mit `satisfies Record<DeviceClassEnum, IconName>`; `deviceClassIcon()` liefert für `other`, fehlenden und unbekannten Wert `device`; `PLANT_ICON = "plant"`. Die Reihenfolge der Klassen (`deviceClasses`) kommt jetzt aus derselben Tabelle.
- **Strukturbaum**: Gerätezeile zeigt statt „Gerät“ Icon und Bezeichnung der Klasse (`data-testid="device-class"`, z. B. „SPS“); Anlagenzeilen zeigen das Anlagen-Icon.
- **Geräteseite**: Klassen-Icon (24 px) vor dem Namen (`device-heading`) und in der Brotkrume des Geräts; Anlagen-Icon in der Brotkrume der Anlage; neues Feld „Gerätetyp“ in der Feldliste (nach „Name“, Text aus `assets:deviceClass`) – erledigt damit den offenen Punkt aus 073.
- **Landkarte**: `DeviceData.deviceClass` (graph.ts); Geräteknoten zeigt das Klassen-Icon, die Klasse als Tooltip (`title`) und im Namen des Knotens für Hilfstechnik („Device X (key), PLC, …“, de/en in `map.json`); Anlagenknoten mit Anlagen-Icon.
- Alle Icons bleiben dekorativ (`aria-hidden`), die Klasse steht überall zusätzlich als Text.
- **Doku**: `web/src/icons/README.md` (Abschnitt eigene Icons, Pflege von Datei und Komponente, Mapping), `web/src/pages/README.md`.

### Wie wurde getestet?

- Vitest: `industrial/glyphs.test.tsx` vergleicht je Icon die gerenderte Komponente Element für Element (Tag und Attribute) mit der SVG-Datei und prüft, dass jede Datei nur `path`/`rect`/`circle` ohne Text enthält und die Regeln (24er-Raster, Strich 2, `currentColor`, runde Enden) erfüllt; `icons.test.tsx` prüft die neuen Namen automatisch mit (Raster, keine eigenen Farben, alle Zeichnungen verschieden). `deviceClass.test.ts`: jede Klasse → erwartetes Icon, Fallback für `undefined`, `null`, `""`, `switch`, `PLC`, `__proto__`, `toString`. Baum, Geräteseite und Kartenknoten mit Icon-, Text- und Tooltip-Prüfungen (de/en). Ergebnis: 33 Testdateien, 566 Tests grün.
- Web-Job aus `ci.yml` mit `W`: lint, typecheck, test, build, licenses, api:generate jeweils Exit 0; `git status` ohne Änderung unter `web/openapi` und `web/src/api`.
- Playwright (`web/e2e/map.spec.ts` erweitert): Gerät mit `device_class: "plc"` zeigt auf der Karte das SPS-Icon (`data-icon="devicePlc"`, `aria-hidden`) mit Tooltip „PLC“, auf der Geräteseite Icon und Feld „PLC“, im Strukturbaum Icon und Text „PLC“. Ablauf wie in `ci.yml` mit `D` inkl. „Create test account“: zwei Läufe ohne `down -v`, je 41 bestanden.
- Kriterium 2: Die committeten Blobs haben dieselbe Git-Prüfsumme wie die Vorlagedateien; SHA-256 je Datei:

| Datei | SHA-256 |
| --- | --- |
| obj-03-anlage.svg | 2d0a9e4eab5195d2d3f5d13112aea6e39c404dc9c53f00f0cd086b682b0de76d |
| obj-04-geraet.svg | 628902e1b96691795974d82e6ce4e249625d71b1e844136b90ec5f38f6c2845b |
| dev-01-sps.svg | 2114e4844d985be4c674b787e1aeee8b8e6330f05955e295e149ea627645b1b8 |
| dev-02-controller.svg | 6325f6769c4169f55ffd5995a15702d50363afcaa003f15e59572e5adad3b9e6 |
| dev-03-rechner.svg | 9e577dd33b2368f9d6d7e7356b3d52584a61497a5586a9e8717af3eb7fa2c172 |
| dev-04-router.svg | 0d0027755d2698c6d0829ec88b7bc0256e8e0d3fbf64d7a48f982d9b1da09bf4 |
| dev-05-roboter.svg | a7153e94c06f1b2b5d88edb532f6e425f96bf5354bc3ed7a35d6672dd4667ef5 |
| dev-06-firewall.svg | bad4348cd96db54f60c7e0c18206983c1728f07998c7ce51e94bb7107b8a2ebc |

- Abräumen: `D … --profile dev --profile e2e down -v` und `W … --profile dev down -v` jeweils Exit 0.

### Zweig und Arbeitsverzeichnis

Zweig `worktree-agent-af81c64b502a5704b`, Arbeitsverzeichnis `.claude/worktrees/agent-af81c64b502a5704b`. Nicht gepusht.

### Abweichungen

- Die Zeichnungen stehen zweimal im Repository: als unveränderte SVG-Datei (Vorgabe „byte-gleich“) und als TSX-Komponente (Vorgabe „typisierte Komponente“ auf `SvgGlyph`). Ein Test hält beide gleich. Alternative wäre ein Import der SVG als Text mit `dangerouslySetInnerHTML` gewesen; das habe ich bewusst nicht gewählt.
- Die Gerätezeile im Baum nennt jetzt die Klasse statt des Worts „Gerät“ (bei `other` also „Sonstiges“).
- Die Namen der Geräteknoten auf der Karte enthalten zusätzlich die Klasse; `map.json` (de/en) und die Tests wurden angepasst. Die sichtbare Knotenhöhe bleibt unverändert (Klasse nur als Tooltip, nicht als weitere Zeile).
- Die Seite „Datei“ (`DocumentPage.tsx`) zeigt beim Gerät weiter das generische Geräte-Icon (nicht im Umfang); es ist jetzt die eigene Zeichnung.
- Nicht im Browser von Hand angesehen; geprüft wurde nur über Vitest und Playwright.
