# Icon-Bedarfsanalyse

Stand: 21.11.2026 · reine Analyse, keine Grafik und kein Code · Grundlage für ein extern entworfenes SVG-Icon-System und Logo.

Der Projektinhaber heißt in diesem Dokument „a7“. „2x“ ist ein Arbeitsname, der technische Bezeichner ist `twox` (E-09).

## Lesehilfe

**Projektstatus** wird überall so unterschieden:

| Kennzeichen | Bedeutung |
| --- | --- |
| **impl** | bereits implementiert, liegt auf `main` |
| **geplant** | konkret geplant, mit Fundstelle (Auftrag, Meilenstein, Startunterlage, Entscheidung) |
| **Vorschlag** | Empfehlung dieser Analyse, im Repository nicht belegt |

**Prioritäten** (für H2 und H5):

| Stufe | Bedeutung in diesem Projekt |
| --- | --- |
| **P0** | erste nutzbare Version = Oberfläche von M1: das Vorhandene plus die Aufträge 032–036 |
| **P1** | konkret geplante Funktionen bis Version 0.1 (M2–M6) |
| **P2** | spätere Stufen (M7–M11) und Vorschläge |

**Quellen.** Die Fundstellen nennen eine Datei und, wo sinnvoll, eine Zeile. „SU“ meint `STARTUNTERLAGE.md` (liegt nur lokal, E-20) mit Abschnitt. Sie wird hier nur umschrieben. Herstellerunterlagen unter `testfactory/extern/` wurden nicht gelesen und nicht zitiert. Gerätedaten stammen aus `testfactory/layout/devices.csv` und `testfactory/layout/network-plan.md`.

---

# Teil A – Projektanalyse

## A1. Hauptfunktionen heute (impl)

| Funktion | Stand | Fundstelle |
| --- | --- | --- |
| Struktur Standort → Bereich → Anlage → Gerät als Datenmodell, API und Admin | impl (Backend) | `backend/twox/assets/models.py`; Aufträge 019, 026 |
| Dateien je Gerät mit unveränderlichen Versionen, Prüfsumme, Dubletten-Erkennung, Up- und Download | impl (Backend) | `backend/twox/files/models.py`; Aufträge 022, 024, 029; E-42 |
| Anmeldung (django-allauth) mit den Rollen „Verwalten“ und „Lesen“ | impl | `backend/twox/accounts/roles.py:19-23`; `web/src/pages/LoginPage.tsx`; Aufträge 020, 021, 030; E-38, E-40 |
| Änderungsprotokoll (django-auditlog), Lesen nur für Verwalter | impl (Backend) | `backend/twox/accounts/audit.py`, `views.py:101`; Auftrag 028; E-43 |
| Selbsttest: Datenbank und Worker durch alle Schichten | impl | `web/src/pages/SelftestPage.tsx`; Aufträge 010, 012, 017 |
| Oberfläche zweisprachig (Deutsch, Englisch) mit Sprachauswahl | impl | `web/src/LanguageSwitch.tsx`, `web/src/locales/`; Auftrag 018; E-07 |
| Rahmen mit Navigation, Benutzerbereich, Lade- und Fehleranzeige | impl | `web/src/components/Layout.tsx`, `Loading.tsx`, `ErrorMessage.tsx`; Auftrag 023 |
| Prüfbefehle für Docling und Sprachmodell (nur Kommandozeile) | impl | `README.md`, Abschnitt „Check commands“ |

In der Oberfläche sind Struktur, Geräteseite, Dateiseite, Import und Protokoll heute noch **Platzhalter** (`web/src/components/PagePlaceholder.tsx`, `web/src/pages/DevicePage.tsx`).

## A2. Bereits geplante Funktionen

| Funktion | Meilenstein | Fundstelle | Status |
| --- | --- | --- | --- |
| CSV-Import der Geräteliste mit Probelauf und Fehlerbericht | M1 | Auftrag 031 (in Arbeit), 035; E-44 | geplant |
| Oberflächen für Struktur, Protokoll, Import, Dateien | M1 | Aufträge 032, 033, 035, 036 | geplant |
| Backend-Übersetzung (Fehlermeldungen zweisprachig) | M1 | Auftrag 034 | geplant |
| Einlesen im Hintergrund mit Statusanzeige, Fehler sichtbar, neuer Versuch | M2 | `docs/ROADMAP.md` M2; SU 4 und 5.7 („Einlese-Auftrag“) | geplant |
| Suche: Stichwort und Bedeutung | M2 | `docs/ROADMAP.md` M2; SU 4 | geplant |
| Auskunft: Frage, Antwort mit anklickbaren Quellen, Eingrenzen auf Gerät oder Anlage | M3 | `docs/ROADMAP.md` M3; SU 4; `testfactory/questions.yaml` | geplant |
| Steckbrief je Gerät: vorgeschlagene Felder mit Herkunft, bestätigen oder korrigieren | M4 | `docs/ROADMAP.md` M4; SU 4 und 5.7 | geplant |
| Konfigurationen einlesen, Zugangsdaten schwärzen, Anzeige mit Zeilenbezug | M5 | `docs/ROADMAP.md` M5; E-42 | geplant |
| Version 0.1: Installation, Testfabrik in einem Befehl | M6 | `docs/ROADMAP.md` M6 | geplant |
| Landkarte (Beziehungen aus Konfigurationen) | M7 | `docs/ROADMAP.md`; SU 4 „Spätere Stufen“ | geplant, ohne Termin |
| Änderungsvergleich zwischen Versionen | M8 | wie oben | geplant, ohne Termin |
| Was-wäre-wenn im Kleinen (Netzänderungen prüfen, Daten abspielen) | M9 | wie oben | geplant, ohne Termin |
| Export als Verwaltungsschale, MCP-Schnittstelle | M10 | wie oben | geplant, ohne Termin |
| Abgleich mit NetBox | M11 | wie oben | geplant, ohne Termin |
| OpenID Connect, Zwei-Faktor, eigene Kennwortänderung | nach M1 / M6 | E-38 | geplant, ohne Termin |

Ausdrücklich **nicht** in Stufe 1: Netz-Scan, Live-Daten, Simulation, Schreibzugriff auf Anlagen, Mandanten, mobile App (SU 4, „Nicht in Stufe 1“; Leitplanke 2 in `CLAUDE.md`).

## A3. Vorhandene Oberflächen

| Adresse | Seite | Inhalt heute | Fundstelle |
| --- | --- | --- | --- |
| `/login` | Anmelden | fertig | `web/src/pages/LoginPage.tsx` |
| `/` | Struktur | Platzhalter | `web/src/routes.tsx:43`, `pages/StructurePage.tsx` |
| `/devices/:deviceId` | Gerät | Platzhalter | `routes.tsx:44`, `pages/DevicePage.tsx` |
| `/documents/:documentId` | Datei | Platzhalter | `routes.tsx:45`, `pages/DocumentPage.tsx` |
| `/import` | Import | Platzhalter | `routes.tsx:46`, `pages/ImportPage.tsx` |
| `/audit` | Änderungsprotokoll | Platzhalter | `routes.tsx:47`, `pages/AuditPage.tsx` |
| `/selftest` | Selbsttest | fertig (zwei Statuskarten) | `routes.tsx:48`, `pages/SelftestPage.tsx` |
| `*` | Seite nicht gefunden | fertig | `components/NotFound.tsx` |
| `/admin/` | Django-Admin (nur Superuser) | fertig, fremdes Design | E-39 |

## A4. Laut Planung benötigte Oberflächen

- **M1 (geplant):** Strukturbaum mit Suche im Browser; Geräteseite mit Brotkrumen und Bereich „Dateien“; Formulare zum Anlegen und Bearbeiten aller vier Ebenen (032). Protokolltabelle mit Filtern, Seitenwechsel und Baustein `AuditTrail` (033). Import in drei Schritten (035). Dateiliste, Dateiseite mit Versionen, Upload-Formulare (036).
- **M2–M5 (geplant, Seiten noch nicht entworfen):** Suche, Übersicht der Einlese-Aufträge, Auskunft mit Quellenanzeige, Steckbrief am Gerät, Konfigurationsanzeige mit Zeilenbezug.
- **M7–M11 (geplant, ohne Entwurf):** Landkarte, Vergleichsansicht, Was-wäre-wenn, Export und Schnittstellen, NetBox-Abgleich.
- **Vorschlag:** eine Seite „Über“ oder „System“ für Version, Lizenzhinweise und Modellstatus. Die Lizenzhinweise liegen heute schon unter `/static/THIRD-PARTY-NOTICES.txt` (`README.md`, Abschnitt „Licence“).

## A5. Dargestellte Objekte und Entitäten

| Entität | Status | Fundstelle |
| --- | --- | --- |
| Standort (`Site`), Bereich (`Area`), Anlage (`Plant`), Gerät (`Device`) | impl | `backend/twox/assets/models.py:33-121` (Klassen ab Zeile 33, 48, 71, 94) |
| Datei (`Document`) mit Art `document` oder `configuration` | impl | `backend/twox/files/models.py:47-51, 58` |
| Dateiversion (`DocumentVersion`) | impl | `files/models.py:100` |
| Benutzer, Rolle (`manage`, `read`), Protokolleintrag (Anlegen, Ändern, Löschen) | impl | `accounts/roles.py`, `accounts/serializers.py:30-34` |
| Importbericht (angelegt, geändert, unverändert, Fehler) | geplant | Auftrag 031 |
| Abschnitt (Textstelle mit Seite oder Zeile) | geplant M2 | SU 5.7 |
| Steckbrief-Feld (vorgeschlagen, bestätigt) | geplant M4 | SU 5.7 |
| Beziehung zwischen zwei Geräten | geplant M7 | SU 5.7 |
| Einlese-Auftrag (Status, Fehlertext) | geplant M2 | SU 5.7 |
| Netz, Netzbereich (Büronetz, Anlagennetz) | nur in der Testfabrik-Beschreibung | `testfactory/layout/network-plan.md` |
| Dienst (MQTT-Broker, Node-RED, Systemdienste) | als Einlese-Quelle geplant | `docs/ROADMAP.md`, Einlese-Modul 2 |

**Wichtiger Befund:** Das Gerät hat **kein Feld für Gerätetyp oder Geräteklasse**. Die Felder sind Freitext 1:1 aus der CSV (`models.py:94-121`, E-41, E-44). Ein Icon je Geräteklasse lässt sich deshalb heute nicht zuverlässig zuordnen (siehe G6, G7 und H7 T-2).

## A6. Unterstützte Geräte und Anlagentypen

Die Software ist geräteneutral: Ein Gerät ist ein Datensatz mit Hersteller, Modell, Softwarestand, Adresse und Protokollen als Text. Konkret erfasst sind nur die Geräte der Testfabrik (13 Geräte, 10 Anlagen, 3 Bereiche; Auftrag 031, Abnahmefall):

| Geräteart | Geräte (Kennung) | Status |
| --- | --- | --- |
| SPS Siemens S7-1200 | `dps-plc`, `hbw-plc`, `drill-plc`, `mill-plc`, `aiqs-plc` | impl (CSV) |
| Controller fischertechnik TXT 4.0 | `dps-txt`, `aiqs-txt`, `agv-txt`, `cgw-txt` | impl (CSV) |
| Einplatinenrechner als Zentralsteuerung, Raspberry Pi 4B | `ccu-rpi` | impl (CSV) |
| WLAN-Router TP-Link TL-WR902AC | `aps-router` | impl (CSV) |
| Industrieroboter Universal Robots UR5e | `ur5e` | impl (CSV) |
| Firewall OPNsense als virtuelle Maschine | `opnsense-fw` | impl (CSV) |

Anlagen (Module): Wareneingang und -ausgang, Hochregallager, Bohrstation, Frässtation, Qualitätssicherung, Transportfahrzeug, Ladestation (ohne Gerät), Zentralsteuerung und Netz, Roboterzelle UR5e, Firewall zwischen Büro- und Anlagennetz (`devices.csv`).

**Zukünftig, ungeprüft** (SU 10.2, „Kandidaten“): Steuerung mit offenem Projektformat (Beckhoff TwinCAT 3 oder CODESYS), CNC-Steuerung mit Programmierplatz, Router oder Switch mit virtueller Ausgabe, Netzgeräte für Batfish (M9). Einlese-Module für SPS-Projekte und Siemens-Exporte sind geplant (`docs/ROADMAP.md`, Module 5 und 6).

## A7. UI-Komponenten mit Icon-Bedarf

| Komponente | Datei | Bedarf | Status |
| --- | --- | --- | --- |
| Kopfzeile mit Produktname | `components/Layout.tsx:24-26` | Logo statt oder neben dem Text „2x“ | impl, ohne Logo |
| Hauptnavigation | `navigation.ts:29-35`, `Layout.tsx:28-47` | je Eintrag ein Icon | impl, ohne Icons |
| Benutzerbereich, Abmelden | `components/UserMenu.tsx` | Benutzer, Abmelden | impl |
| Sprachauswahl | `LanguageSwitch.tsx` | optional Globus | impl |
| Ladeanzeige | `components/Loading.tsx` | Drehsymbol | impl, nur Text |
| Fehlermeldung, Hinweis „keine Rolle“ | `components/ErrorMessage.tsx`, `Layout.tsx:54-58` | Fehler, Kein Zugriff, Warnung | impl, nur Farbe und Text |
| Statuskarten des Selbsttests | `pages/SelftestPage.tsx:152-158` | OK, Fehlgeschlagen, Datenbank, Worker | impl, nur Farbe und Text |
| Seite nicht gefunden | `components/NotFound.tsx` | optional | impl |
| Strukturbaum, Geräteseite, Formulare | Auftrag 032 | Ebenen-Icons, Aufklappen, Anlegen, Bearbeiten, Suche | geplant |
| Protokolltabelle, `AuditTrail` | Auftrag 033 | Filter, Seitenwechsel, Objektart | geplant |
| Import | Auftrag 035 | Hochladen, Erfolg, Fehler | geplant |
| Dateiliste, Dateiseite | Auftrag 036 | Dokument, Version, Download, Upload, Dublette | geplant |

## A8. Designsystem, Farben, Icon-Bibliotheken

- **Kein Designsystem, keine eigenen Farben, kein Icon, kein Logo, kein Favicon.**
  - `web/src/index.css` enthält nur `@import "tailwindcss";`.
  - Farben sind Tailwind-Standardklassen direkt im Markup: `slate` für Flächen und Text, `red` für Fehler, `green` für OK, `amber` für Hinweise (`Layout.tsx`, `ErrorMessage.tsx`, `SelftestPage.tsx`).
- **Keine Icon-Bibliothek** in `web/package.json`. Kein `<svg>` und kein Icon im Quelltext von `web/src`.
- **Kein Favicon:** `web/index.html` hat kein `<link rel="icon">`, es gibt kein `web/public/`. Django liefert für jeden Pfad außer `api/`, `static/`, `admin/`, `_allauth/` und `accounts/` die `index.html` (E-39, `backend/twox/config/urls.py:21`). Ein Browser, der `/favicon.ico` anfragt, bekommt also HTML zurück.
- **Kein Dark Mode:** keine `dark:`-Klassen, fester heller Hintergrund (`Layout.tsx:21`).
- **Technische Vorgaben:** React 19, TypeScript 6, Vite 8 mit Basis-Pfad `/static/` (`web/vite.config.ts`), Tailwind CSS 4.3. Lizenzregeln in `web/scripts/license-rules.txt`. Betrieb ohne Internet und ohne Telemetrie (Leitplanke 6).
- **Einzige Icons im Gesamtsystem:** Font Awesome Free im unveränderten Django-Admin, als benannte Ausnahme nur dort (E-47).

---

# Teil B – Hauptlogo und Produktidentität

**B1. Drei Kernfunktionen**

1. **Anlagenakte:** Zu jedem Gerät und jeder Anlage liegen Struktur, Dokumente, Konfigurationen und Versionen an einem Ort (SU 1 und 4).
2. **Belegte Auskunft:** Jede Antwort nennt ihre Quelle. Ohne Beleg sagt die Software das ausdrücklich (Leitplanke 3; Kontrollfrage 11 in `testfactory/questions.yaml`).
3. **Lokal und nur lesend:** Das Sprachmodell läuft im eigenen Haus, die Software verändert nichts an Anlagen (Leitplanken 2 und 6).

**B2. Was das Logo zeigen sollte:** vor allem 1 und 2 zusammen, also die Verbindung zwischen der realen Anlage und ihrem belegten digitalen Abbild. Das passt zum bevorzugten Gedanken „Anlage ↔ digitales Abbild“. Punkt 3 lässt sich schlecht abbilden. Er gehört in Texte, nicht in die Marke.

**B3. Fabrik oder abstraktes Symbol?** Ein abstraktes Symbol ist besser geeignet:
- Das Sägezahndach ist ein sehr verbreitetes Industrie-Klischee und bei 16 px kaum von anderen Branchenprogrammen zu unterscheiden.
- Die Software betrifft auch IT-Geräte wie Router und Firewall, nicht nur die Fertigung.
- Ein Fabrikmotiv würde mit dem Anlagen-Icon (OBJ-03) konkurrieren. Marke und Funktions-Icon müssen getrennt bleiben.

**B4. Einfache geometrische Motive:** ein gefülltes und ein hohles Quadrat (real und Abbild), ein geteiltes Quadrat, zwei Punkte mit einer Linie, eine Dokumentecke, eckige Klammern, versetzte Ebenen, eine Spiegelachse, eine Markierung oder ein Lesezeichen, ein Baum aus drei Punkten.

**B5. Passende Metaphern:**

| Metapher | Passt zu |
| --- | --- |
| Spiegelung, Paar aus Voll und Kontur | digitales Abbild |
| Verbindung zweier Knoten | belegte Auskunft (Gerät ↔ Quelle), Landkarte (M7) |
| Ebenen und Stapel | Hierarchie, Versionen |
| Rahmen, Klammer | erfassen, einordnen, Fundstelle |
| Markierung | Quelle, Beleg |

Transformation und Vernetzung passen nur schwach: Die Software verändert nichts, und die Landkarte kommt erst später.

**B6. Motive, die man vermeiden sollte**

- **Sprechblase und Funkeln oder Stern:** das allgemeine Zeichen für KI-Assistenten. Es betont den Chat und nicht die Akte.
- **Gehirn, Glühbirne:** abgegriffen.
- **Zahnrad:** steht in fast jeder Software für Einstellungen.
- **Sechseck-Netz:** Klischee für „Industrie 4.0“.
- **Sägezahndach:** siehe B3.
- **Unendlich-Schleife:** sehr verbreitet.
- **Stilisiertes „X“ und Doppelpfeile:** Wegen des Arbeitsnamens „2x“ liegen sie nahe. Ein großes „X“ ist aber bekannte Marke eines sozialen Netzwerks, „2x“ und ein doppelter Vorwärtspfeil lesen sich als Faktor oder Geschwindigkeit.
- **Lupe allein:** gleich dem Such-Icon.
- **Logos und Farben der Testfabrik-Hersteller:** Siemens, Universal Robots, fischertechnik, OPNsense. Die OPNsense-Dokumentation nimmt ihre Logos ausdrücklich von der Lizenz aus (`docs/testfabrik/quellen-standardgeraete-roboter-firewall.md:284`).
- Eine Markenrecherche ist nötig. Sie ist für den Namen ohnehin vorgesehen (SU 12).

**B7. Anforderungen aus Favicon, Taskleiste, Header**

| Einsatz | Größe | Anforderung |
| --- | --- | --- |
| Favicon im Tab | 16 und 32 px | erkennbar auf hellem und dunklem Tab-Hintergrund |
| Taskleiste, angeheftete Seite | Windows 24–32 px, bei 125 % bzw. 150 % Skalierung 40–48 px | wie Favicon |
| Kopfzeile | ca. 28–36 px hoch, neben dem Namen | Die heutige Überschrift ist `text-3xl`, also 30 px Schrift. |

Allgemein gilt: eine geschlossene Silhouette, höchstens zwei bis drei Elemente, keine Linie dünner als 2 px bei 16 px, transparenter Hintergrund, einfarbig darstellbar, ohne Text.

**B8. Varianten nach Größe:** ja, drei Stufen.
- **Master** ab 32 px.
- **Kleinvariante** für 16–24 px: vereinfacht und auf das Pixelraster gelegt.
- **Optional eine App-Kachel** mit Hintergrundfläche für Web-App-Manifest und Apple-Touch-Icon.

**B9. Folgen des späteren Namenswechsels**

- Die Bildmarke darf keine Buchstaben oder Ziffern enthalten: kein „2“, kein „x“, keine Ligatur.
- Farben und Form dürfen nicht vom Namen abhängen.
- Eine Wortmarke wird erst nach der Namensprüfung entworfen.
- Dateinamen neutral halten, zum Beispiel `brand-mark.svg` statt `2x-logo.svg`.
- Technisch ist der Namenswechsel in der Oberfläche einfach: Der Anzeigename steht in `web/src/locales/*/common.json` (`appTitle`) und in `web/index.html` (`<title>`). Der Bezeichner `twox` bleibt technisch.

**Logo-Grundideen:** zwölf Konzepte, ausführlich in H4.

---

# Teil C – Geräte- und Anlagenicons

## C1. Anlagenkategorien

| Kategorie aus dem Auftrag | Relevant? | Beleg |
| --- | --- | --- |
| Produktionsanlagen, Fertigungslinien | ja, aber als **Bereich** „Fertigungslinie“, nicht als Anlage | `devices.csv`, Spalte `area` |
| Industrieroboter | ja, UR5e als Gerät und Anlage „Roboterzelle“. Der 6-Achs-Roboter im Modul Wareneingang ist Teil der Anlage, kein eigenes Gerät. | `devices.csv`; SU 10.2 |
| CNC-Maschinen | nicht in der Testfabrik. Bohr- und Frässtation sind verwandte Bearbeitungsstationen. Eine CNC-Steuerung ist nur ein ungeprüfter Kandidat. | `devices.csv`; SU 10.2 |
| Fördertechnik | nur als **Transportfahrzeug** (fahrerloses Fahrzeug, VDA 5050). Förderbänder sind nicht als Geräte erfasst. | `devices.csv` (`aps-agv`) |
| Steuerungsanlagen | ja: SPS, TXT-Controller, Zentralsteuerung | `devices.csv` |
| Automatisierungszellen | ja: Roboterzelle | `devices.csv` (`ur5e-cell`) |
| Sensorik und Aktorik | nur in Notizen (Kamera, 24-V-Sensoren, Motorsteuerung), **nicht als Geräte** | `devices.csv`, Spalte `notes` |

**In der Aufzählung fehlen** (aus der Testfabrik): Hochregallager, Qualitätsprüfung mit Kamera, Wareneingang und -ausgang, Ladestation, Zentralsteuerung und Netz, Netzübergang mit Firewall.

**Tatsächlich benötigt:** Für V1 genügt **ein generisches Anlagen-Icon** (OBJ-03), denn auch die Anlage hat kein Typfeld (`models.py:71-91`). Anlagentyp-Icons (ANL-01 bis ANL-06) sind P2 und setzen ein Typfeld voraus.

## C2. Industrielle IT und Netzwerkkomponenten

| Komponente | Relevant? | Beleg und Einordnung |
| --- | --- | --- |
| SPS / PLC | **ja**, 5 Geräte | S7-1200, `devices.csv` |
| Industrie-PC | **ja, als Rechner-Klasse**: Raspberry Pi 4B als Zentralsteuerung | `ccu-rpi` |
| Server | nein, kein Gerät. P2 als Variante der Rechner-Klasse. | – |
| Netzwerk-Switch | nein, kein Gerät. P2: Kandidat „Router oder Switch“ aus SU 10.2. | – |
| Router | **ja**, 1 Gerät | `aps-router` |
| Firewall | **ja**, 1 Gerät | `opnsense-fw` |
| Gateway | nur als Funktion: `cgw-txt` ist ein TXT-Controller mit Gateway-Aufgabe. Kein eigenes Icon, die Rolle steht im Namen. | `devices.csv` |
| HMI / Bedienpanel | nicht belegt. Die Bedienoberfläche der Zentralsteuerung ist ein Webdienst, kein Panel. | `network-plan.md` |
| Edge-Geräte | die Zentralsteuerung erfüllt diese Rolle, gehört zur Rechner-Klasse | `ccu-rpi` |
| IoT-Geräte | nicht als eigene Klasse. Die TXT-Controller sind Steuerungen. | – |
| Virtuelle Maschinen | **ja, als Eigenschaft**: OPNsense läuft als VM. Darstellung als Badge, nicht als Gerät. | `devices.csv`, Spalte `model` |
| Container | keine Geräte. URSim ist ein Simulator-Image der Testfabrik, Docker-Compose-Dateien sind eine Einlese-Quelle in M5. | `testfactory/manifest.yaml` (`ursim-e-series`); `docs/ROADMAP.md` |
| Speicher- und Datenbanksysteme | nicht in der Testfabrik. Datenbank nur als Teil von 2x selbst (Selbsttest). | `SelftestPage.tsx` |

**Zusätzlich aus Daten und Roadmap:**
- **Industrieroboter** (UR5e).
- **Embedded-Controller** (TXT 4.0).
- **Dienste** auf Geräten: MQTT-Broker, Node-RED, Systemdienste (Einlese-Modul 2).
- **Netzbereiche** Büronetz und Anlagennetz (`network-plan.md`).
- **Protokolle** MQTT, OPC UA, SSH, HTTP, DHCP, VDA 5050 als Werte im Feld `protocols`.

## C3. Hierarchien und Beziehungen

**Das Beispiel aus dem Auftrag stimmt nicht.** Die tatsächliche, feste Hierarchie lautet (`backend/twox/assets/models.py:1-6`, `files/models.py:1-9`, SU 5.7):

```
Standort → Bereich → Anlage → Gerät → Datei (Dokument | Konfiguration) → Version
                                    └→ (M4) Steckbrief-Felder, Herkunft = Abschnitt (M2)
                              Gerät ↔ Gerät: Beziehung (M7)
```

- Die Ebene **Bereich** fehlt im Beispiel. Eine Ebene „Maschine“ unterhalb der Anlage und eine Ebene „Komponente“ unterhalb des Geräts **gibt es nicht**.
- Eine Anlage ist ein Modul oder eine Zelle (`models.py:71`). Ein Gerät ist eine Steuerung, ein Rechner, ein Netzgerät oder ein Roboter.
- Dateien hängen **nur am Gerät** (`files/models.py:61-66`), nicht an Anlage oder Standort.

**Eigenes Icon brauchen:** Standort, Bereich, Anlage, Gerät (generisch und je Klasse), Dokument, Konfiguration, Version. Später auch Quelle (Abschnitt) und Beziehung.

**Beziehungen darstellen:** In der Struktur reichen Einrückung im Baum und Brotkrumen (032). Übergeordnet und untergeordnet brauchen **kein** eigenes Icon. In der Landkarte (M7) wird eine Beziehung als Linie zwischen Geräte-Icons gezeichnet, die Art steht als Text daran. Ein eigenes Icon „Beziehung“ braucht es nur für Navigation und Listen.

| Gewünschtes Icon | Bedarf | Begründung |
| --- | --- | --- |
| Übergeordnete Anlage | nein | Baum und Brotkrumen genügen |
| Untergeordnete Komponente | nein | Ebene existiert nicht |
| Gerätegruppe | nein | Die Anlage gruppiert die Geräte (OBJ-03) |
| Verbindung | ja, P2 (OBJ-10) | Entität „Beziehung“ in M7 |
| Abhängigkeit | nein, eigenes Icon unnötig | gerichtete Linie oder Pfeil im Diagramm, Art als Text |
| Digitales Abbild | nicht als Funktions-Icon | Das Abbild ist die Akte selbst (Steckbrief NAV-08). Der Gedanke gehört ins Logo. |

## C4. Wiederverwendbarkeit

- **Basisform „Steuerung“** (Modul mit Klemmenreihe): SPS. Die TXT-Controller und spätere Steuerungen wie TwinCAT, CODESYS oder CNC erhalten dieselbe Grundform mit **einem** Unterscheidungsmerkmal.
- **Basisform „Rechner“:** Zentralsteuerung. Später Server oder Industrie-PC als Variante, VM nur als Badge.
- **Basisform „Netzgerät“:** Router. Später Switch als Variante. Die Firewall ist die Basisform plus Schild.
- **Zwingend eigenständig:** Industrieroboter (die Form ist nicht ableitbar) und, als Anlagentyp in P2, das Transportfahrzeug.
- **Generisch genügt:** alles ohne Typ (Fallback OBJ-04), Sensorik und Aktorik, Gateway, HMI, IoT.
- **Für V1 wirklich nötig: 7 Geräte-Icons.** Das sind 1 generisches (OBJ-04) und 6 Klassen (DEV-01 bis DEV-06), aus 3 Basisformen plus Roboter. Später kommen 3 Varianten dazu (DEV-07 bis DEV-09).

---

# Teil D – Navigation und Benutzeroberfläche

**D1. Vorhandene Navigationseinträge** (`web/src/navigation.ts:29-35`, deutsche Texte aus `locales/de/nav.json`):

| Eintrag | Pfad | Rolle |
| --- | --- | --- |
| Struktur | `/` | read |
| Import | `/import` | manage |
| Änderungsprotokoll | `/audit` | manage |
| Selbsttest | `/selftest` | read |

Dazu in der Kopfzeile: Produktname als Link, Sprachauswahl, Benutzername mit Rolle und Abmelden (`Layout.tsx`, `UserMenu.tsx`). Gerät, Datei und Anmelden stehen nicht in der Navigation.

**D2. Geplante Einträge:** M1 fügt **keine** neuen Einträge hinzu: Die Aufträge 032–036 ersetzen nur Platzhalter, die Einträge bleiben laut `navigation.ts:7-8`. Später kommen dazu: Suche (M2), Einlese-Aufträge (SU 4, M2), Auskunft (M3), Steckbrief (M4, vermutlich auf der Geräteseite), Landkarte (M7), Vergleich (M8, vermutlich auf der Dateiseite), Was-wäre-wenn (M9), Export und Schnittstellen (M10), NetBox-Abgleich (M11). Wo diese Einträge stehen, ist nicht festgelegt (H7 F-1).

**D3. Individuelles Icon nötig:** keiner der vier heutigen Einträge. Bei den geplanten Einträgen die **Landkarte** (NAV-09) und optional die **Auskunft** (NAV-06), weil sie die Kernfunktion sichtbar macht. Alle Objekt- und Geräte-Icons der Struktur (siehe C) sind individuell.

**D4. Standardsymbole einer Bibliothek genügen für:**

| Bereich | Icons |
| --- | --- |
| Navigation | Struktur, Import, Änderungsprotokoll, Selbsttest, Suche, Einlese-Aufträge, Steckbrief, Vergleich, Was-wäre-wenn, Export, Schnittstelle, Abgleich, Einstellungen |
| Aktionen | alle ACT-Icons |
| Status | alle STA-Icons |
| Objekte | Standort, Bereich, Dokument, Konfiguration, Version, Benutzer, Quelle |
| System | Datenbank, Worker, Modell |

**D5. Wiederkehrende Aktionen**

| Aktion | Fundstelle | Status |
| --- | --- | --- |
| Anlegen | 032 | geplant |
| Bearbeiten | 032 | geplant |
| Hochladen | 035, 036 | geplant |
| Herunterladen | 036 | geplant |
| Erneut prüfen, neuer Versuch | `SelftestPage.tsx` impl; SU 4 für das Einlesen | impl / geplant |
| Filtern | 033 | geplant |
| Aufklappen | Baum in 032, Prüfsumme in 036 | geplant |
| Blättern | 033 | geplant |
| Abmelden | `UserMenu.tsx` | impl |
| Sprache wechseln | `LanguageSwitch.tsx` | impl |
| Übernehmen, Bestätigen | 035 Schritt 3; Steckbrief M4 | geplant |
| Quelle öffnen | M3; Dubletten-Link in 036 | geplant |
| Frage senden | M3 | geplant |

Löschen gibt es in M1 nicht in der Oberfläche (E-41, 032 „Nicht-Ziele“).

**D6. Oberflächen mit vielen Icons:**
1. Strukturbaum: Ebenen-Icons, Geräteklasse, Aufklappen, Anlegen, Bearbeiten.
2. Geräteseite: Klassen-Icon im Kopf, Dateiliste mit Art, Version, Download, Dublette.
3. Protokolltabelle: Objektart, Aktion, Filter.
4. Später die Landkarte, die Auskunft mit Quellen und die Einlese-Übersicht mit Status je Auftrag.

**D7. Desktop und Mobil**
- Eine mobile App ist ausgeschlossen (SU 4). Zielnutzer ist die verantwortliche Person für OT und IT, nicht der Werker (SU 1), also vor allem der Desktop.
- Die Kopfzeile bricht schon heute um (`flex-wrap` in `Layout.tsx:23, 30`).
- **Vorschlag:**
  - Auf dem Desktop Icon und Text in der Navigation.
  - Auf schmalen Bildschirmen (Tablet in der Halle) ein Menü-Icon (ACT-17, P2).
  - Icon-Schaltflächen ohne Text nur mit `aria-label`.
  - Trefferflächen mindestens 24 × 24 px (WCAG 2.2, 2.5.8), auf Touch-Geräten 44 × 44 px.

---

# Teil E – Status- und Funktionsicons

**E1. Statuswerte im Code (impl):**

| Statuswert | Werte | Fundstelle |
| --- | --- | --- |
| Dateiart | `document`, `configuration` | `files/models.py:47-51` |
| Protokoll-Aktion | `create`, `update`, `delete` | `accounts/serializers.py:30-34` |
| Rolle | `manage`, `read`, keine | `accounts/roles.py`; `locales/en/auth.json` |
| Sitzung | `loading`, `error`, `signed-out`, `signed-in` | `web/src/session.ts:86-89` |
| Selbsttest je Prüfung | OK oder Fehlgeschlagen | `SelftestPage.tsx:152-158` |
| Ergebnis des Selbsttest-Abrufs | `answered`, `unreachable`, `http-error`, `invalid-answer`, `unexpected-error` | `web/src/api/selftest.ts:8-12` |
| API-Fehler | Art `http`, `network`, `invalid-answer`; HTTP 403 (keine Berechtigung), 404, 409 (Dublette), 413 (zu groß) | `api/errors.ts`; `ErrorMessage.tsx`; E-42 |
| Gerät ohne Adresse | IP leer, 6 von 13 Testfabrik-Geräten | `models.py:109`; Auftrag 031 |

Ein Gerätestatus wie online, offline oder unbekannt **existiert nicht**.

**E2. Geplante Statuswerte:**

| Statuswert | Fundstelle |
| --- | --- |
| Importbericht: angelegt, geändert, unverändert, Fehler mit Zeile | 031, 035 |
| Einlese-Auftrag: Status und Fehlertext (die Werte sind nicht festgelegt), neuer Versuch möglich | SU 4 und 5.7, M2 |
| Steckbrief-Feld: vorgeschlagen, bestätigt | SU 5.7, M4 |
| Antwort mit Quellen, „Dazu finde ich nichts in den Unterlagen“ | Leitplanke 3; `questions.yaml` Art `no-evidence` |
| Widerspruch zwischen Quellen (beide Fundstellen zeigen) | `questions.yaml` Art `contradiction`; SU 10.2 |
| Zugangsdaten geschwärzt | M5; Leitplanke 5 |
| Vergleich: hinzugefügt, entfernt, geändert | M8 |
| Abgleich mit NetBox | M11, Werte offen |

**E3. Statuswerte mit Icon (Vorschlag):**
- **P0:** OK, Fehler, Warnung, Läuft, Kein Zugriff, Dublette.
- **P1:** Info, Wartet, Vorgeschlagen, Bestätigt, Keine Belege, Widerspruch, Geschwärzt.
- **P2:** Virtuell.

**Bewusst kein Icon** für online, offline, unbekannt, synchronisiert und „Daten veraltet“: Die Software prüft keine Erreichbarkeit (keine Live-Daten, kein Netz-Scan, Leitplanke 2). Solche Icons würden einen Zustand vortäuschen, den es nicht gibt. „Neue Version vorhanden“ und „Daten veraltet“ sind im Repository nicht belegt.

**E4. Besser als Farbe, Text oder Badge:**
- Protokoll-Aktion (anlegen, ändern, löschen) und Importzähler als **Text-Badge**.
- Rolle als **Text**.
- Dateiart als Icon (OBJ-05, OBJ-06) **mit** Text.
- Protokolle (MQTT, OPC UA …) als **Text-Badge**, ohne Icon.
- Fehlende Angabe („offen“, leere IP) als **Text** „–“ oder „offen“.
- Versionsnummer als Text „v2“.

**E5. Ohne Farbe unterscheidbar** (WCAG 1.4.1) sein müssen: OK und Fehler (Selbsttest, Import, Einlesen), Warnung und Fehler, Vorgeschlagen und Bestätigt, Keine Belege, Widerspruch, Geschwärzt. Der Selbsttest erfüllt das heute schon über den Text „OK“ / „Fehlgeschlagen“. Die Icons brauchen deshalb **verschiedene Formen**, zum Beispiel Haken, Kreuz, Dreieck, Uhr und Schloss, nicht nur verschiedene Farben.

**E6. Zustände aus den Verarbeitungsprozessen:**

| Prozess | Zustände | Status |
| --- | --- | --- |
| Upload | wird hochgeladen, zu groß (413), Dublette (409), Hinweis auf gleichen Inhalt an anderer Stelle, Konfiguration abgewiesen bis M5 | 036; E-42 |
| Import | Probelauf, Bericht mit Fehlern, übernommen | 035 |
| Einlesen und Einbetten | wartet, läuft, fertig, Fehler, neuer Versuch. Die Warteschlangen `ingest`, `embed` und `default` stehen im `README.md` („Services and networks“). | M2, die genauen Werte sind offen |
| Auskunft | Antwort entsteht (Stream über Server-Sent Events, SU 5.2), fertig mit Quellen, ohne Beleg, Widerspruch | M3 |
| Steckbrief | vorgeschlagen, bestätigt, korrigiert. „Korrigiert“ ist ein Vorschlag, laut SU 5.7 gibt es nur zwei Status. | M4 |

---

# Teil F – Gestaltungsrichtlinien

**F1. Benötigte Größen**

| Größe | Einsatz | Bedarf |
| --- | --- | --- |
| 16 px | Icons im Fließtext und in Tabellen (`text-sm`), Status-Badges, Favicon | nötig |
| 20 px | Navigation, Schaltflächen | nötig |
| 24 px | Überschriften, Karten, Baum, Konstruktionsraster | nötig |
| 32 px | Geräte-Icon im Kopf der Geräteseite, Favicon 32, Taskleiste | nötig |
| 48 px | leere Zustände, ICO-Größe 48, Windows-Skalierung | nötig |
| 64, 128, 256 px | nur für das Logo: README, Dokumentation, App-Kachel | nicht für UI-Icons |

**F2. ViewBox:**
- UI-, Objekt- und Geräte-Icons: `0 0 24 24`. Das ist kompatibel mit Lucide und Tabler. Der Inhalt liegt in einer Fläche von 20 × 20 mit 2 Einheiten Rand.
- Logo: ein eigenes Raster, zum Beispiel `0 0 64 64` für den Master und `0 0 16 16` für die Kleinvariante.

**F3. Strichstärke:** 2 Einheiten im 24er-Raster, mit runden Enden und Ecken. Bei 16 px ergibt das etwa 1,33 px, bei 20 px etwa 1,67 px. Innenabstände mindestens 2 Einheiten. Für Darstellungen ab 32 px kann die Strichstärke auf 1,5 sinken, damit Geräte-Icons nicht plump wirken. Die Größe der Strichstärke muss sich dafür als Parameter steuern lassen (siehe F8).

**F4. Outline oder gefüllt:** **Outline** für Navigation, Aktionen, Objekte und Geräte. **Gefüllt** nur für kleine Status-Badges, zum Beispiel ein gefüllter Kreis mit ausgespartem Haken, und für das Logo, weil eine volle Fläche bei 16 px besser trägt.

**F5. Unterschiedliche Regeln für Logo und Geräte-Icons:** ja.
- Das Logo darf Flächen und ein eigenes Raster nutzen. Es hat keine Strichpflicht und muss als einfarbige Silhouette funktionieren.
- Geräte-Icons folgen streng den UI-Regeln, weil sie neben Aktions-Icons in Listen stehen.

**F6. Komplexe Anlagen- zu einfachen Navigationsicons passend machen:**
- gleiches Raster, gleiche Strichstärke, gleicher Eckradius (Vorschlag 2) und gleiche Enden
- frontale, flache Ansicht ohne Perspektive
- je Icon eine Grundform plus **ein** Merkmal, zum Beispiel SPS = Modul plus Klemmenreihe
- höchstens 3 bis 4 Teilformen
- Basisformen wiederverwenden (C4)
- ein Prüfbogen, der alle Icons bei 16, 20 und 24 px neben den Bibliotheks-Icons zeigt und abgenommen wird

**F7. Anforderungen aus dem Frontend:**
- **React-Komponenten:** React 19 mit TypeScript und strikter Typprüfung. Jede Funktion braucht Typen (`CLAUDE.md`, „Arbeitsregeln“). Ein Icon ist also eine typisierte React-Komponente.
- **Vite** baut mit Basis-Pfad `/static/`. Dateien, die im Build-Ergebnis über einen festen Namen erreichbar sein müssen (Favicon), gehören in einen `public/`-Ordner oder werden importiert.
- **Tailwind 4:** Die Größe kommt über Klassen wie `size-4` und `size-5`, die Farbe über `text-*` und `currentColor`.
- **Tests** laufen mit Vitest und jsdom. SVG ohne Netzabruf, also direkt im Bundle.
- **Kein CDN und keine Webfont von außen** (Leitplanke 6).
- **Zweisprachige Beschriftung** über `react-i18next`.

**F8. Farben und Größen steuern:**
- Farbe nur über `stroke="currentColor"` und `fill="currentColor"`.
- Die Größe als Eigenschaft (`size`) oder als Klasse.
- Strichstärke als Eigenschaft mit Standard 2.
- Statusfarben als benannte Farben in `index.css` über Tailwinds `@theme`. Vorschlag: `--color-status-ok` und weitere, statt `green-800` im Markup.
- Keine fest eingebauten Farben in den SVG-Dateien. Ausnahme ist das farbige Logo.

**F9. Accessibility und Dark Mode:**
- Dekorative Icons neben Text bekommen `aria-hidden="true"`. Icon-only-Schaltflächen bekommen ein übersetztes `aria-label`.
- Kontrast von Icons mindestens 3:1 (WCAG 1.4.11). Status nie nur über Farbe (E5).
- Dark Mode gibt es heute nicht. `currentColor` macht die Icons automatisch tauglich dafür.
- Das Logo braucht eine helle und eine dunkle (negative) Fassung. Das SVG-Favicon kann sich über `prefers-color-scheme` selbst anpassen.

**F10. Saubere Darstellung bei 16 px:**
- Koordinaten auf ganzen oder halben Einheiten, passend zur Strichstärke.
- Keine Details unter 2 Einheiten.
- Höchstens drei Teilformen.
- Status- und Logo-Icons bekommen eine eigene 16-px-Fassung.
- Prüfung in Chrome unter Windows bei 100 %, 125 % und 150 % Skalierung, auf hellem und dunklem Grund.
- Abnahme über den Prüfbogen aus F6.

---

# Teil G – Technische Integration

**G1. Eingesetzte Icon-Bibliotheken:** keine in der Oberfläche (`web/package.json`). Nur der Django-Admin bringt Font Awesome Free mit (E-47, ausschließlich dort).

**G2. Bestehende Icon-Komponenten:** keine.

**G3. SVG-Einbindung:** Es gibt keine SVG-Dateien und keine Icon-Komponenten. Es gibt auch kein Favicon und keinen `public/`-Ordner (siehe A8).

**G4. Anzupassende Komponenten**

| Datei | Änderung |
| --- | --- |
| `web/index.html` | Favicon-Links |
| `components/Layout.tsx` | Logo in der Kopfzeile, Icons in `NavLink` |
| `navigation.ts` | neues Feld `icon` in `NavigationEntry` |
| `components/UserMenu.tsx` | Abmelden |
| `components/Loading.tsx` | Drehsymbol |
| `components/ErrorMessage.tsx` | Fehler, Kein Zugriff |
| `pages/SelftestPage.tsx` | Statuskarten |
| `components/NotFound.tsx` | Icon für die Fehlerseite |
| `LanguageSwitch.tsx` | Globus |
| Komponenten aus 032–036 | Baum, Formulare, Tabellen, Upload |

`Layout.tsx`, `navigation.ts` und `package.json` sind gemeinsame Dateien. Sie werden in 032–036 ausdrücklich nicht geändert (zum Beispiel 032, „Nicht-Ziele“). Die Icons brauchen deshalb einen **eigenen Auftrag nach M1**.

**G5. Organisation einer zentralen Bibliothek (Vorschlag):**

```
web/src/icons/
  Icon.tsx            gemeinsame Hülle: size, strokeWidth, title/aria-label, className
  names.ts            Typ IconName (Union) und Zuordnung Name → Komponente
  ui.ts               Wiederexport der gewählten Bibliotheks-Icons unter eigenen Namen
  industrial/         eigene Icons als TSX-Komponenten (Objekte, Geräte, Anlagen)
  deviceClass.ts      Zuordnung Geräteklasse → Icon, mit Rückfall auf das generische Gerät
  icons.test.tsx      prüft viewBox 0 0 24 24, currentColor, keine fest eingebauten Farben
web/public/           favicon.svg, favicon.ico, apple-touch-icon.png (von Vite nach /static/ kopiert)
docs/design/          Gestaltungsregeln, Prüfbogen, Quell-SVGs des Logos
```

Der Code verwendet Icons nur über `IconName`, nie direkt aus der Bibliothek. Dann bleibt ein späterer Bibliothekswechsel eine Änderung an einer Stelle.

**G6. Icons mit Geräte- und Anlagentypen verknüpfen:** Heute gibt es dafür kein Feld (A5). Drei Wege sind möglich:

| Weg | Bewertung |
| --- | --- |
| (a) Neues Auswahlfeld `device_class` mit festen Werten, optional auch in der CSV | sauber, aber eine Änderung an Datenmodell und CSV-Format (E-41, E-44), also Stufe C |
| (b) Ableiten aus Hersteller- und Modelltext | unzuverlässig, widerspricht „nicht raten“ |
| (c) Typ aus dem Steckbrief (M4), dort ist „Typ“ ein vorgeschlagenes Feld (SU 4) | belegt, kommt aber erst mit M4 |

Empfehlung in H7 T-2.

**G7. Zentrales Mapping:** ja. Eine Tabelle `DeviceClass → IconName` an einer Stelle, mit dem generischen Gerät als Rückfall für leer oder unbekannt. So entsteht für neue Klassen kein neuer Code in den Seiten. Dasselbe Muster gilt für Objektarten im Protokoll (Objektart → Icon) und für Dateiarten.

**G8. Bibliothek plus eigene Industrie-Icons**

Vorteile:
- etwa 50 Standard-Icons fertig, geprüft und barrierearm
- weniger Entwurfsaufwand
- Updates kommen mit der Bibliothek
- Die eigenen Icons übernehmen Raster und Strich der Bibliothek und wirken so aus einem Guss.

Nachteile:
- eine neue Abhängigkeit (Entscheidung von a7)
- Stilbindung: Die eigenen Icons müssen exakt den Regeln der Bibliothek folgen.
- Die Bibliothek kann Icons umbenennen. Abhilfe sind die eigene Namensschicht (G5) und eine feste Version.

Fazit: Die Kombination ist sinnvoll, wenn die Bibliothek strichbasiert in 24er-Raster ist (Lucide oder Tabler).

**G9. Technische und lizenzrechtliche Einschränkungen**

- **Lizenz:** erlaubt sind MIT, Apache-2.0, BSD, ISC, 0BSD (`web/scripts/license-rules.txt`). CC-BY-4.0 ist nur für Entwicklungspakete erlaubt, also **nicht** für ausgelieferte Icons wie Font Awesome Free. Jede neue Abhängigkeit braucht einen Eintrag in `docs/DECISIONS.md` und eine Entscheidung von a7 (Leitplanke 7).
- **Kopierte SVGs:** Die Lizenzhinweise der npm-Pakete erzeugt der Build automatisch (`/static/THIRD-PARTY-NOTICES.txt`). Werden SVGs aus einer Bibliothek **kopiert** statt als Paket eingebunden, fehlt dieser Hinweis und muss von Hand gepflegt werden.
- **Herstellerzeichen:** Herstellerlogos und Produktfotos sind als Geräte-Icons tabu (Markenrecht, siehe B6).
- **Offline:** kein CDN, keine Icon-Webfont (Leitplanke 6; Icon-Fonts sind zudem schlecht zugänglich und nicht tree-shakebar).
- **Öffentliches Repository** (E-19): Alles Eingecheckte ist sofort öffentlich. Entwürfe mit ungeklärten Rechten gehören nicht hinein.

**Geprüfte Bibliotheken (Vorschlag).** Lizenzen nach Wissensstand dieser Analyse, **nicht am Original verifiziert**. Vor einer Entscheidung am Paket prüfen.

| Bibliothek | Lizenz | passt zu den Projektregeln? | Raster und Stil | Bewertung |
| --- | --- | --- | --- | --- |
| Lucide (`lucide-react`) | ISC (Teile aus Feather: MIT) | ja | 24, Strich 2, rund | **Empfehlung:** großer Umfang, Komponenten einzeln importierbar, aktiv gepflegt |
| Tabler Icons (`@tabler/icons-react`) | MIT | ja | 24, Strich 2 | gute Alternative, sehr groß, mehr Technik-Motive |
| Heroicons | MIT | ja | 24 / 20 / 16 | zu klein für Industrie-Bedarf |
| Phosphor | MIT | ja | eigenes Raster 256, 6 Stärken | gut, aber anderes Raster |
| Material Symbols | Apache-2.0 | ja | 24, eigener Stil | einzelne Industrie-Motive, Stil weicht ab |
| IBM Carbon Icons | Apache-2.0 | ja | 32, eher gefüllt | viele IoT- und Netz-Motive, Stil weicht ab |
| Bootstrap Icons | MIT | ja | 16 | gut für 16 px, wenig Technik |
| Iconoir | MIT | ja | 24, Strich 1,5 | dünner Strich |
| Feather | MIT | ja | 24 | nicht mehr gepflegt, Lucide ist der Nachfolger |
| Font Awesome Free | Icons CC-BY-4.0 | **nein**, nur Entwicklung bzw. Admin (E-25, E-47) | – | nicht verwenden |
| Remix Icon | seit v4 eigene „Remix Icon License“ (nach Wissensstand) | **nein**, keine Standardlizenz | – | nicht verwenden |

**G10. Weitere Dateiformate**

| Format | Zweck | Priorität |
| --- | --- | --- |
| `favicon.svg` | moderne Browser, mit Hell/Dunkel über `prefers-color-scheme` | P0 |
| `favicon.ico` (16, 32, 48 in einer Datei) | ältere Browser, Windows-Verknüpfungen, direkte Anfragen auf `/favicon.ico` | P0 |
| `apple-touch-icon.png` (180 × 180, mit Fläche) | Lesezeichen auf iOS und iPadOS | P1 |
| PNG 192 und 512 (auch „maskable“) und `manifest.webmanifest` | nur falls die Oberfläche als App installierbar sein soll (nicht geplant) | P2 |
| PNG 1280 × 640 | Vorschaubild für das öffentliche GitHub-Repository | P2 |
| PNG 256 | README und Dokumentation | P1 |

PDF, EPS und Druckformate werden nicht gebraucht.

**Zum Favicon:** `/favicon.ico` fällt heute in den Pfad der Oberfläche und liefert HTML (A8). Entweder liegt das ICO unter `/static/` und `index.html` verweist darauf, oder Django bekommt einen eigenen Pfad für `/favicon.ico`. Das ist eine Änderung am Backend.

---

# H1. Zusammenfassung

Das Projekt hat heute **kein einziges Icon und kein Logo** (A8, G1–G3). Es braucht fünf Arten:

1. **Hauptlogo:** eine namensunabhängige Bildmarke mit Kleinvariante für Favicon und Taskleiste, einfarbiger Fassung und optional einer App-Kachel. Leitidee: Anlage ↔ belegtes digitales Abbild, abstrakt, ohne Fabrikdach.
2. **Navigation:** 4 vorhandene Einträge (Struktur, Import, Änderungsprotokoll, Selbsttest) plus Suche. Später Auskunft, Einlesen, Steckbrief, Landkarte und weitere. Alles Standardsymbole außer der Landkarte.
3. **Geräte und Anlagen:** die feste Hierarchie Standort → Bereich → Anlage → Gerät → Datei → Version (C3). Dazu 6 Geräteklassen aus der Testfabrik: SPS, Controller, Rechner, Router, Roboter, Firewall, auf 3 Basisformen plus Roboter. Das ist der eigentlich individuelle Teil.
4. **Funktionen:** etwa ein Dutzend Standard-Aktionen (Anlegen, Bearbeiten, Hoch- und Herunterladen, Filtern …), später Auskunft und Quelle.
5. **Status:** 6 in M1 (OK, Fehler, Warnung, Läuft, Kein Zugriff, Dublette), 7 in M2–M5. Bewusst **keine** Online- oder Offline-Icons, weil die Software keine Live-Daten hat.

---

# H2. Vollständiges Icon-Inventar

**Spalte „Nachweis“:** **R** = Bedarf im Repository nachgewiesen (Datei oder Auftrag), **E** = Empfehlung dieser Analyse. Spalte „Individuell“: **ja** = eigener Entwurf, **nein** = Standardsymbol einer Bibliothek, **Basis** = Bibliotheks-Icon genügt, ein eigener Entwurf ist optional.

### Marke (LOGO)

| ID | Kategorie | Icon-Bezeichnung | Bedeutung | Einsatzort | Größe | Priorität | Projektstatus | Individuell | Quelle im Repository |
|---|---|---|---|---|---|---|---|---|---|
| LOGO-01 | Marke | Bildmarke (Master) | Produktidentität ohne Namen | Kopfzeile, Anmeldeseite, README, Doku | 32–256 | P0 | Vorschlag (E); heute nur Text „2x“ | ja | `Layout.tsx:24-26`; `locales/*/common.json` `appTitle` |
| LOGO-02 | Marke | Bildmarke klein (Favicon) | dieselbe Marke, vereinfacht | Browser-Tab, Taskleiste, `favicon.svg`/`.ico` | 16, 32, 48 | P0 | Vorschlag (E); kein Favicon vorhanden | ja | `web/index.html` (ohne `rel="icon"`) |
| LOGO-03 | Marke | Bildmarke einfarbig / negativ | Fassung für dunklen Grund und Einfarbdruck | Dark Mode, Doku, Dokumente | 16–256 | P1 | Vorschlag (E) | ja | – |
| LOGO-04 | Marke | App-Kachel | Marke auf Fläche für Installation und Lesezeichen | Apple-Touch-Icon, Web-App-Manifest | 180, 192, 512 | P2 | Vorschlag (E) | ja | – |

### Navigation und Funktionen (NAV)

| ID | Kategorie | Icon-Bezeichnung | Bedeutung | Einsatzort | Größe | Priorität | Projektstatus | Individuell | Quelle im Repository |
|---|---|---|---|---|---|---|---|---|---|
| NAV-01 | Navigation | Struktur | Baum der Standorte, Bereiche, Anlagen, Geräte | Hauptnavigation | 20 | P0 | impl (Eintrag ohne Icon) · R | nein | `navigation.ts:30`; Auftrag 032 |
| NAV-02 | Navigation | Import | Geräteliste als CSV einlesen | Hauptnavigation (nur `manage`) | 20 | P0 | impl (Eintrag) · R | nein | `navigation.ts:31`; Auftrag 035 |
| NAV-03 | Navigation | Änderungsprotokoll | wer hat was wann geändert | Hauptnavigation (nur `manage`) | 20 | P0 | impl (Eintrag) · R | nein | `navigation.ts:33`; Auftrag 033 |
| NAV-04 | Navigation | Selbsttest | Systemprüfung Datenbank und Worker | Hauptnavigation | 20 | P0 | impl · R | nein | `navigation.ts:34`; `SelftestPage.tsx` |
| NAV-05 | Funktion | Suche | Stichwort- und Bedeutungssuche; Suchfeld der Struktur | Suchfeld Struktur (M1), Navigation (M2) | 16, 20 | P0 | geplant · R | nein | Auftrag 032 (Suche); `ROADMAP.md` M2 |
| NAV-06 | Funktion | Auskunft | Frage stellen, belegte Antwort | Navigation, Gerät, Anlage | 20, 24 | P1 | geplant M3 · R | Basis | `ROADMAP.md` M3; SU 4 |
| NAV-07 | Funktion | Einlese-Aufträge | Verarbeitung im Hintergrund mit Status | Navigation oder Dateiseite | 20 | P1 | geplant M2 · R | nein | SU 4 und 5.7; `ROADMAP.md` M2 |
| NAV-08 | Funktion | Steckbrief | belegte Gerätedaten (digitales Abbild) | Geräteseite (Reiter) | 20 | P1 | geplant M4 · R | nein | `ROADMAP.md` M4; SU 5.7 |
| NAV-09 | Funktion | Landkarte | Beziehungen aus Konfigurationen als Übersicht | Navigation | 20 | P2 | geplant M7 · R | ja | `ROADMAP.md` M7 |
| NAV-10 | Funktion | Änderungsvergleich | Unterschied zweier Versionen | Dateiseite | 16, 20 | P2 | geplant M8 · R | nein | `ROADMAP.md` M8 |
| NAV-11 | Funktion | Was-wäre-wenn | Netzänderung vorab prüfen, Daten abspielen | Navigation | 20 | P2 | geplant M9 · R | nein | `ROADMAP.md` M9 |
| NAV-12 | Funktion | Export Verwaltungsschale | Akte als AAS ausgeben | Gerät, Anlage | 16, 20 | P2 | geplant M10 · R | nein | `ROADMAP.md` M10 |
| NAV-13 | Funktion | Schnittstelle (MCP) | KI-Werkzeuge lesen die Akte | Einstellungen | 20 | P2 | geplant M10 · R | nein | `ROADMAP.md` M10 |
| NAV-14 | Funktion | Abgleich | Abgleich mit NetBox | Navigation oder Einstellungen | 20 | P2 | geplant M11 · R | nein | `ROADMAP.md` M11 |
| NAV-15 | Navigation | Einstellungen / System | Systemseite (Version, Lizenzen, Modell) | Kopfzeile | 20 | P2 | Vorschlag · E | nein | – |

### Objekte und Hierarchie (OBJ)

| ID | Kategorie | Icon-Bezeichnung | Bedeutung | Einsatzort | Größe | Priorität | Projektstatus | Individuell | Quelle im Repository |
|---|---|---|---|---|---|---|---|---|---|
| OBJ-01 | Objekt | Standort | Ort des Betriebs | Baum, Brotkrumen, Protokoll | 16, 20 | P0 | impl (Modell) · R | nein | `models.py:33` `Site` |
| OBJ-02 | Objekt | Bereich | Teil eines Standorts, z. B. Fertigungslinie | Baum, Brotkrumen, Protokoll | 16, 20 | P0 | impl (Modell) · R | nein | `models.py:48` `Area` |
| OBJ-03 | Objekt | Anlage (generisch) | Modul oder Zelle mit Geräten | Baum, Brotkrumen, Protokoll | 16, 20, 24 | P0 | impl (Modell) · R | ja | `models.py:71` `Plant` |
| OBJ-04 | Objekt | Gerät (generisch) | Gerät ohne bekannte Klasse; Rückfall | Baum, Geräteseite, Protokoll | 16, 20, 32 | P0 | impl (Modell) · R | ja | `models.py:94` `Device` |
| OBJ-05 | Objekt | Dokument | Datei der Art `document` | Dateiliste, Dateiseite, Protokoll | 16, 20 | P0 | impl (Modell), UI geplant · R | nein | `files/models.py:50`; Auftrag 036 |
| OBJ-06 | Objekt | Konfigurationsdatei | Datei der Art `configuration` | Dateiliste, Upload-Hinweis | 16, 20 | P1 | Modell impl, angenommen erst M5 · R | nein | `files/models.py:51`; E-42 |
| OBJ-07 | Objekt | Version | unveränderlicher Stand einer Datei | Dateiliste, Dateiseite | 16 | P0 | impl (Modell), UI geplant · R | nein | `files/models.py:100`; Auftrag 036 |
| OBJ-08 | Objekt | Benutzer | angemeldete Person, Akteur im Protokoll | Benutzerbereich, Protokoll | 16, 20 | P0 | impl · R | nein | `UserMenu.tsx`; Auftrag 033 |
| OBJ-09 | Objekt | Quelle / Fundstelle | Abschnitt mit Seite oder Zeile als Beleg | Antwort, Steckbrief, Suche | 16 | P1 | geplant M2/M3 · R | nein | SU 5.7 „Abschnitt“; Leitplanke 3 |
| OBJ-10 | Objekt | Beziehung | Verbindung zweier Geräte mit Art | Landkarte, Geräteseite | 16, 20 | P2 | geplant M7 · R | ja | SU 5.7 „Beziehung“ |
| OBJ-11 | Objekt | Netzbereich | Netzsegment, z. B. Büronetz, Anlagennetz | Landkarte | 20, 24 | P2 | Vorschlag · E (Daten in Testfabrik) | ja | `testfactory/layout/network-plan.md` |
| OBJ-12 | Objekt | Dienst | Software-Dienst auf einem Gerät (Broker, Node-RED) | Konfigurationsanzeige, Landkarte | 16, 20 | P2 | Vorschlag · E | nein | `ROADMAP.md` Einlese-Modul 2 |

### Geräteklassen (DEV)

| ID | Kategorie | Icon-Bezeichnung | Bedeutung | Einsatzort | Größe | Priorität | Projektstatus | Individuell | Quelle im Repository |
|---|---|---|---|---|---|---|---|---|---|
| DEV-01 | Gerät | SPS | speicherprogrammierbare Steuerung (Basisform „Steuerung“) | Baum, Geräteseite, Landkarte | 16, 20, 32 | P0 | 5 Geräte in Testdaten · R | ja | `devices.csv` (`*-plc`) |
| DEV-02 | Gerät | Controller | Embedded-Steuerung (Variante „Steuerung“) | wie DEV-01 | 16, 20, 32 | P0 | 4 Geräte in Testdaten · R | ja | `devices.csv` (`*-txt`) |
| DEV-03 | Gerät | Rechner / Edge-Rechner | Einplatinen- oder Industrie-Rechner (Basisform „Rechner“) | wie DEV-01 | 16, 20, 32 | P0 | 1 Gerät · R | ja | `devices.csv` (`ccu-rpi`) |
| DEV-04 | Gerät | Router | Netzgerät mit Funk (Basisform „Netzgerät“) | wie DEV-01 | 16, 20, 32 | P0 | 1 Gerät · R | ja | `devices.csv` (`aps-router`) |
| DEV-05 | Gerät | Industrieroboter | Roboterarm; auch für Anlage „Roboterzelle“ | wie DEV-01 | 16, 20, 32 | P0 | 1 Gerät · R | ja | `devices.csv` (`ur5e`) |
| DEV-06 | Gerät | Firewall | Netzübergang mit Filter (Netzgerät plus Schild) | wie DEV-01 | 16, 20, 32 | P0 | 1 Gerät · R | ja | `devices.csv` (`opnsense-fw`) |
| DEV-07 | Gerät | Switch | Netzverteiler (Variante „Netzgerät“) | wie DEV-01 | 16, 20, 32 | P2 | Kandidat, ungeprüft · E | ja | SU 10.2 „Kandidaten“ |
| DEV-08 | Gerät | Server / Industrie-PC | größerer Rechner (Variante „Rechner“) | wie DEV-01 | 16, 20, 32 | P2 | Vorschlag · E | ja | – |
| DEV-09 | Gerät | Sensor / Kamera | Sensorik, z. B. Prüfkamera | wie DEV-01 | 16, 20, 32 | P2 | nur in Notizen · E | ja | `devices.csv`, Spalte `notes` |

### Anlagentypen (ANL)

Alle ANL-Icons setzen ein Typfeld voraus.

| ID | Kategorie | Icon-Bezeichnung | Bedeutung | Einsatzort | Größe | Priorität | Projektstatus | Individuell | Quelle im Repository |
|---|---|---|---|---|---|---|---|---|---|
| ANL-01 | Anlage | Lager | Hochregallager | Baum, Landkarte | 16, 20, 24 | P2 | Anlage in Testdaten; Typ-Icon Vorschlag · E | ja | `devices.csv` (`aps-hbw`) |
| ANL-02 | Anlage | Bearbeitungsstation | Bohren, Fräsen; später CNC | Baum, Landkarte | 16, 20, 24 | P2 | wie oben · E | ja | `devices.csv` (`aps-drill`, `aps-mill`) |
| ANL-03 | Anlage | Prüfstation | Qualitätssicherung mit Kamera | Baum, Landkarte | 16, 20, 24 | P2 | wie oben · E | ja | `devices.csv` (`aps-aiqs`) |
| ANL-04 | Anlage | Transportfahrzeug | fahrerloses Fahrzeug | Baum, Landkarte | 16, 20, 24 | P2 | wie oben · E | ja | `devices.csv` (`aps-agv`) |
| ANL-05 | Anlage | Ladestation | Laden des Fahrzeugs | Baum, Landkarte | 16, 20, 24 | P2 | wie oben · E | ja | `devices.csv` (`aps-charging`) |
| ANL-06 | Anlage | Wareneingang und -ausgang | Übergabe von Werkstücken | Baum, Landkarte | 16, 20, 24 | P2 | wie oben · E | ja | `devices.csv` (`aps-dps`) |

### Aktionen (ACT)

| ID | Kategorie | Icon-Bezeichnung | Bedeutung | Einsatzort | Größe | Priorität | Projektstatus | Individuell | Quelle im Repository |
|---|---|---|---|---|---|---|---|---|---|
| ACT-01 | Aktion | Anlegen | neues Objekt | Struktur, Dateien | 16, 20 | P0 | geplant · R | nein | Aufträge 032, 036 |
| ACT-02 | Aktion | Bearbeiten | Objekt ändern; Steckbrief korrigieren | Struktur, Geräteseite | 16, 20 | P0 | geplant · R | nein | Auftrag 032; SU 4 (M4) |
| ACT-03 | Aktion | Hochladen | Datei, neue Version, CSV | Dateien, Import | 16, 20 | P0 | geplant · R | nein | Aufträge 035, 036 |
| ACT-04 | Aktion | Herunterladen | Version herunterladen | Dateiseite | 16 | P0 | geplant · R | nein | Auftrag 036 |
| ACT-05 | Aktion | Erneut ausführen | erneut prüfen, neuer Versuch | Selbsttest, Einlesen | 16, 20 | P0 | impl (Textknopf) · R | nein | `SelftestPage.tsx:44`; SU 4 |
| ACT-06 | Aktion | Filtern | Liste eingrenzen; auf Gerät oder Anlage eingrenzen | Protokoll, Auskunft | 16, 20 | P0 | geplant · R | nein | Auftrag 033; SU 4 |
| ACT-07 | Aktion | Aufklappen / Zuklappen | Baumknoten, Prüfsumme | Struktur, Dateiliste | 16 | P0 | geplant · R | nein | Aufträge 032, 036 |
| ACT-08 | Aktion | Abmelden | Sitzung beenden | Benutzerbereich | 16, 20 | P0 | impl (Textknopf) · R | nein | `UserMenu.tsx:44-52` |
| ACT-09 | Aktion | Übernehmen / Bestätigen | Import übernehmen; Steckbrief-Feld bestätigen | Import, Steckbrief | 16, 20 | P1 | geplant · R | nein | Auftrag 035; SU 4 (M4) |
| ACT-10 | Aktion | Blättern | vorige und nächste Seite | Protokoll | 16 | P0 | geplant · R | nein | Auftrag 033 |
| ACT-11 | Aktion | Schließen / Abbrechen | Dialog oder Formular verlassen | Formulare | 16, 20 | P1 | Vorschlag · E | nein | – |
| ACT-12 | Aktion | Sprache | Sprachauswahl | Kopfzeile | 16 | P1 | impl (ohne Icon) · R | nein | `LanguageSwitch.tsx` |
| ACT-13 | Aktion | Quelle öffnen | Fundstelle oder verlinkte Datei öffnen | Antwort, Dubletten-Hinweis | 16 | P1 | geplant · R | nein | SU 4 (M3); Auftrag 036 |
| ACT-14 | Aktion | Frage senden | Auskunft starten | Auskunft | 20 | P1 | geplant M3 · R | nein | `ROADMAP.md` M3 |
| ACT-15 | Aktion | Kopieren | Prüfsumme, IP-Adresse kopieren | Geräte- und Dateiseite | 16 | P2 | Vorschlag · E | nein | – |
| ACT-16 | Aktion | Löschen | Objekt entfernen | Formulare (nach M1) | 16, 20 | P2 | in M1 nur im Admin · R | nein | E-41; Auftrag 032 „Nicht-Ziele“ |
| ACT-17 | Aktion | Menü | Navigation auf schmalen Bildschirmen | Kopfzeile | 20 | P2 | Vorschlag · E | nein | `Layout.tsx:23` (`flex-wrap`) |

### Status (STA)

| ID | Kategorie | Icon-Bezeichnung | Bedeutung | Einsatzort | Größe | Priorität | Projektstatus | Individuell | Quelle im Repository |
|---|---|---|---|---|---|---|---|---|---|
| STA-01 | Status | OK / Erfolg | Prüfung bestanden, Vorgang erfolgreich | Selbsttest, Import, Einlesen | 16, 20 | P0 | impl (Farbe und Text) · R | nein | `SelftestPage.tsx:152-158`; `selftest.json` `statusOk` |
| STA-02 | Status | Fehler | Prüfung fehlgeschlagen, API-Fehler, Importfehler | Selbsttest, `ErrorMessage`, Import | 16, 20 | P0 | impl (Farbe und Text) · R | nein | `ErrorMessage.tsx`; `selftest.json` `statusFailed` |
| STA-03 | Status | Warnung | Hinweis mit Handlungsbedarf (z. B. keine Rolle) | Rahmen, Upload | 16, 20 | P0 | impl (Farbe und Text) · R | nein | `Layout.tsx:54-58`; Auftrag 036 |
| STA-04 | Status | Läuft / Laden | Daten werden geladen, Prüfung läuft | `Loading`, Selbsttest, Einlesen | 16, 20 | P0 | impl (nur Text) · R | nein | `Loading.tsx`; `selftest.json` `checking` |
| STA-05 | Status | Kein Zugriff | Rolle fehlt (403) | `ErrorMessage`, Import-Hinweis | 16, 20 | P0 | impl (nur Text) · R | nein | `ErrorMessage.tsx:17-21`; `auth.json` `noPermission` |
| STA-06 | Status | Dublette | gleicher Inhalt wie Version N oder an anderer Stelle | Upload, Dateiliste | 16 | P0 | geplant · R | nein | Auftrag 036 (409); E-42 |
| STA-07 | Status | Information | neutraler Hinweis (Formatbeschreibung u. a.) | Import, Formulare | 16 | P1 | Vorschlag · E | nein | – |
| STA-08 | Status | Wartet | Einlese-Auftrag eingereiht | Einlese-Übersicht | 16 | P1 | geplant M2 · R | nein | SU 5.7 „Einlese-Auftrag“ |
| STA-09 | Status | Vorgeschlagen | Steckbrief-Feld automatisch vorgeschlagen | Steckbrief | 16 | P1 | geplant M4 · R | nein | SU 5.7 |
| STA-10 | Status | Bestätigt | Steckbrief-Feld vom Nutzer bestätigt | Steckbrief | 16 | P1 | geplant M4 · R | nein | SU 5.7 |
| STA-11 | Status | Keine Belege | „Dazu finde ich nichts in den Unterlagen“ | Auskunft | 16, 20 | P1 | geplant M3 · R | nein | Leitplanke 3; `questions.yaml` (`no-evidence`) |
| STA-12 | Status | Widerspruch | Quellen widersprechen sich, beide Fundstellen zeigen | Auskunft, Steckbrief | 16, 20 | P1 | geplant M3 · R | nein | `questions.yaml` (`contradiction`); SU 10.2 |
| STA-13 | Status | Geschwärzt | Zugangsdaten entfernt | Konfigurationsanzeige | 16 | P1 | geplant M5 · R | nein | `ROADMAP.md` M5; Leitplanke 5 |
| STA-14 | Status | Virtuell | Gerät läuft als virtuelle Maschine (Badge am Geräte-Icon) | Baum, Geräteseite | 16 | P2 | Vorschlag · E (Datum in Testdaten) | nein | `devices.csv` (`opnsense-fw`, `model`) |

### System (SYS)

| ID | Kategorie | Icon-Bezeichnung | Bedeutung | Einsatzort | Größe | Priorität | Projektstatus | Individuell | Quelle im Repository |
|---|---|---|---|---|---|---|---|---|---|
| SYS-01 | System | Datenbank | Datenbank von 2x | Selbsttest-Karte | 20, 24 | P1 | impl (Karte ohne Icon) · R | nein | `SelftestPage.tsx`; `selftest.json` `database` |
| SYS-02 | System | Worker | Hintergrunddienst von 2x | Selbsttest-Karte | 20, 24 | P1 | impl (Karte ohne Icon) · R | nein | `SelftestPage.tsx`; `selftest.json` `worker` |
| SYS-03 | System | Sprachmodell | lokales KI-Modell, erreichbar oder nicht | Selbsttest, Auskunft | 20, 24 | P1 | Prüfbefehl impl, Oberfläche geplant M3 · R | nein | `README.md` „check_llm“; `ROADMAP.md` M3 |

**Summe: 80 Icons.**

| Kategorie | Anzahl |
| --- | --- |
| LOGO | 4 |
| NAV | 15 |
| OBJ | 12 |
| DEV | 9 |
| ANL | 6 |
| ACT | 17 |
| STA | 14 |
| SYS | 3 |

Keine Bedeutung ist doppelt vergeben. Gleiche Grundformen bei verschiedenen Bedeutungen sind erlaubt und gewollt: STA-01 (Ergebnis) und ACT-09 (Handlung) teilen den Haken, ACT-07 und ACT-10 den Winkel. Der Unterschied liegt in der Darstellung, etwa Badge gegenüber Schaltfläche.

---

# H3. Geräte- und Anlagenkatalog

Grundlage: `testfactory/layout/devices.csv`, `testfactory/layout/network-plan.md`, `backend/twox/assets/models.py`, SU 10.2. „Geplante Modelle“ nennt nur, was im Repository oder in der Startunterlage steht.

| Geräteklasse | Konkrete Gerätetypen | Existierende Modelle (Testfabrik) | Geplante Modelle | Gemeinsames Basissymbol möglich? | Eigenes Icon erforderlich? |
|---|---|---|---|---|---|
| Steuerung – SPS | Speicherprogrammierbare Steuerung | Siemens S7-1200: `dps-plc`, `hbw-plc`, `drill-plc`, `mill-plc`, `aiqs-plc` (5) | Steuerung mit offenem Projektformat, Beckhoff TwinCAT 3 oder CODESYS (Kandidat, ungeprüft); CNC-Steuerung (Kandidat) | ja, Basisform „Steuerung“ | ja (DEV-01), P0 |
| Steuerung – Embedded-Controller | Lern- und Kleinsteuerung mit MQTT | fischertechnik TXT 4.0: `dps-txt`, `aiqs-txt`, `agv-txt`, `cgw-txt` (4); `cgw-txt` arbeitet als Cloud-Gateway | – | ja, Variante von „Steuerung“ | ja (DEV-02), P0 |
| Rechner | Einplatinenrechner als Zentralsteuerung, MQTT-Broker, Node-RED | Raspberry Pi 4B: `ccu-rpi` (1) | – | ja, Basisform „Rechner“ (später Server, Industrie-PC) | ja (DEV-03), P0; Variante DEV-08 in P2 |
| Netzgerät – Router | WLAN-Router mit DHCP | TP-Link TL-WR902AC: `aps-router` (1) | „Router oder Switch mit virtueller Ausgabe“, Netzgeräte für Batfish (Kandidaten) | ja, Basisform „Netzgerät“ | ja (DEV-04), P0; Switch DEV-07 in P2 |
| Netzgerät – Firewall | Firewall zwischen Büro- und Anlagennetz | OPNsense als virtuelle Maschine: `opnsense-fw` (1) | – | ja, „Netzgerät“ plus Schild | ja (DEV-06), P0 |
| Industrieroboter | kollaborierender 6-Achs-Roboter | Universal Robots UR5e (PolyScope 5.25.1): `ur5e` (1); Simulator URSim im Manifest | – | nein, Form eigenständig | ja (DEV-05), P0 |
| Sensorik, Kamera | Prüfkamera, 24-V-Sensoren, Motorsteuerung | nur in Notizen, keine Geräte | – | generisch | P2 (DEV-09), sonst OBJ-04 |
| Gerät ohne Klasse | alles ohne Typangabe | (heute alle 13, da kein Typfeld) | – | – | generisch (OBJ-04), P0 |
| Anlage – Lager | Hochregallager | `aps-hbw` | – | nein | P2 (ANL-01), sonst OBJ-03 |
| Anlage – Bearbeitung | Bohrstation, Frässtation | `aps-drill`, `aps-mill` | CNC (Kandidat) | ja, eine Form für beide | P2 (ANL-02) |
| Anlage – Prüfung | Qualitätssicherung mit Kamera | `aps-aiqs` | – | nein | P2 (ANL-03) |
| Anlage – Transport | fahrerloses Transportfahrzeug | `aps-agv` | – | nein | P2 (ANL-04) |
| Anlage – Laden | Ladestation | `aps-charging` (ohne Gerät) | – | nein | P2 (ANL-05) |
| Anlage – Ein- und Ausgang | Wareneingang und -ausgang mit Greifroboter | `aps-dps` | – | nein | P2 (ANL-06) |
| Anlage – Roboterzelle | Zelle um den Roboter | `ur5e-cell` | – | ja, nutzt DEV-05 | nein |
| Anlage – Zentrale und Netz | Zentralsteuerung, Router, Gateway | `aps-core` | – | ja, nutzt OBJ-03 oder DEV-03 | nein |
| Anlage – Netzübergang | Firewall | `it-ot-firewall` | – | ja, nutzt DEV-06 | nein |

Bereiche der Testfabrik: Fertigungslinie, Roboterzelle, Netzübergang. Sie nutzen alle OBJ-02.

---

# H4. Produktlogo – zwölf Grundkonzepte

Alle Konzepte enthalten keine Buchstaben und sind vom Namen unabhängig (B9). „16 px“ bewertet die Erkennbarkeit der Kleinvariante.

| Nr. | Grundidee | Bedeutung | Geometrische Elemente | Komplexität | 16 px | Eignung als Marke |
|---|---|---|---|---|---|---|
| 1 | **Spiegelquadrat:** ein gefülltes Quadrat, daneben oder leicht versetzt ein gleich großes Umrissquadrat | physische Anlage ↔ digitales Abbild | 2 Quadrate (Fläche, Kontur) | sehr gering | sehr gut | gut; einfache Formen brauchen eine eigene Proportion oder einen eigenen Versatz, um unterscheidbar zu sein |
| 2 | **Geteiltes Quadrat:** ein Quadrat, eine Hälfte gefüllt, die andere nur Kontur | halb real, halb digital, ein Objekt | 1 Quadrat, 1 Teilfläche | sehr gering | sehr gut | mittel bis gut; die Grundform ist verbreitet |
| 3 | **Knotenpaar:** ein voller und ein hohler Kreis, durch eine kurze Linie verbunden | Gerät ↔ Akte, belegte Verbindung, Ausblick auf die Landkarte | 2 Kreise, 1 Linie | gering | gut, wenn die Linie mindestens 2 px stark ist | gut; Nähe zu Verbindungs-Icons beachten |
| 4 | **Akte mit Knoten:** Dokumentform mit Eselsohr, das Eselsohr ist ein voller Punkt | Wissen, das an einem Gerät hängt | 1 Rechteck mit Ecke, 1 Punkt | gering | gut | mittel; Dokumentformen sind häufig |
| 5 | **Klammerrahmen:** zwei eckige Klammern um einen vollen Punkt oder ein Quadrat | erfassen, einordnen, Fundstelle | 2 Klammern, 1 Kern | gering | gut | gut; eigenständig, wenn die Klammern kräftig sind |
| 6 | **Ebenenstapel:** zwei oder drei versetzte, flache Rauten oder Rechtecke | Hierarchie, Versionen, Schichten der Akte | 2–3 gleiche Formen | gering | mittel (Abstände eng) | mittel; Stapel sind verbreitet |
| 7 | **Spiegelachse:** einfache Giebel- oder Blockform über einer Linie, darunter dieselbe Form nur als Kontur | Anlage und ihr Spiegelbild | 2 Formen, 1 Linie | mittel | mittel | gut; Giebel nicht als Fabrikdach ausführen |
| 8 | **Markierung:** Lesezeichen- oder Fahnenform mit ausgespartem Punkt | Beleg, Quelle, „hier steht es“ | 1 Form, 1 Aussparung | gering | gut | mittel; Lesezeichen sind verbreitet |
| 9 | **Drei-Punkte-Baum:** drei Punkte, rechtwinklig verbunden (L- oder T-Form) | Struktur Standort → Anlage → Gerät | 3 Punkte, 2 Linien | gering | mittel | mittel; ähnlich Git- und Netz-Icons |
| 10 | **Zwei Rahmen im Eingriff:** zwei abgerundete Rechteck-Konturen, überlappend, eine Überlappungsfläche gefüllt | Schnittmenge aus realer und digitaler Welt | 2 Konturen, 1 Fläche | mittel | mittel | mittel; Nähe zum Kettenglied- bzw. Link-Icon |
| 11 | **Ecke und Punkt:** ein rechter Winkel (halber Rahmen) und ein voller Punkt in der offenen Ecke | ein Objekt wird erfasst; minimalste Form | 1 Winkel, 1 Punkt | sehr gering | sehr gut | gut; sehr eigenständig, wenig Aussage ohne Erklärung |
| 12 | **Punktraster:** 2 × 2 Punkte, einer voll, drei hohl | ein Gerät in der Struktur, erfasst unter vielen | 4 Kreise | gering | mittel (hohle Punkte bei 16 px klein) | mittel; ähnliche App-Raster existieren |

**Empfohlene Auswahl für die erste Entwurfsrunde:** 1 (Spiegelquadrat), 3 (Knotenpaar) und 11 (Ecke und Punkt). Diese drei treffen die Leitidee, kommen mit zwei bis drei Elementen aus und lassen sich bei 16 px gut erkennen. Konzept 3 schlägt zudem eine Brücke zum Beziehungs-Icon OBJ-10, muss sich aber deutlich davon unterscheiden: Marke und Funktions-Icon bleiben getrennt.

---

# H5. Minimales erstes Icon-Set

| Stufe | Anzahl | Davon individuell | Davon Bibliothek |
|---|---|---|---|
| **P0** | **35** | 10 (LOGO-01, LOGO-02, OBJ-03, OBJ-04, DEV-01 bis DEV-06) | 25 |
| **P1** | **21** | 1 (LOGO-03) | 20 (NAV-06 mit optionalem eigenen Entwurf) |
| **P2** | **24** | 13 (LOGO-04, NAV-09, OBJ-10, OBJ-11, DEV-07 bis DEV-09, ANL-01 bis ANL-06) | 11 |
| **Summe** | **80** | **24** | **56** |

**P0 (35)**

| Gruppe | Icons |
| --- | --- |
| Marke | LOGO-01, LOGO-02 |
| Navigation | NAV-01 bis NAV-05 |
| Objekte | OBJ-01 bis OBJ-05, OBJ-07, OBJ-08 |
| Geräte | DEV-01 bis DEV-06 |
| Aktionen | ACT-01 bis ACT-08, ACT-10 |
| Status | STA-01 bis STA-06 |

**P1 (21)**

| Gruppe | Icons |
| --- | --- |
| Marke | LOGO-03 |
| Navigation | NAV-06 bis NAV-08 |
| Objekte | OBJ-06, OBJ-09 |
| Aktionen | ACT-09, ACT-11 bis ACT-14 |
| Status | STA-07 bis STA-13 |
| System | SYS-01 bis SYS-03 |

**P2 (24)**

| Gruppe | Icons |
| --- | --- |
| Marke | LOGO-04 |
| Navigation | NAV-09 bis NAV-15 |
| Objekte | OBJ-10 bis OBJ-12 |
| Geräte | DEV-07 bis DEV-09 |
| Anlagen | ANL-01 bis ANL-06 |
| Aktionen | ACT-15 bis ACT-17 |
| Status | STA-14 |

**Für den externen Entwurf** heißt das: In der ersten Runde sind nur **8 funktionale Icons** neu zu zeichnen (OBJ-03, OBJ-04, DEV-01 bis DEV-06) plus **2 Logo-Fassungen**. Alles andere kommt aus der Bibliothek. Die Geräte-Icons DEV-01 bis DEV-06 sind in P0, obwohl das Typfeld fehlt (H7 T-2). Ohne Typfeld zeigt die Oberfläche zunächst nur OBJ-04. Die Klassen-Icons werden trotzdem jetzt entworfen, damit die Formensprache von Anfang an feststeht.

---

# H6. Technische Empfehlungen

**Eigenes Produktlogo**
- Quell-SVG für Master und Kleinvariante. Daraus werden `favicon.svg` (mit `prefers-color-scheme`), `favicon.ico` (16/32/48) und PNGs erzeugt (G10).
- Die Dateien liegen in `web/public/`. Vite kopiert sie nach `/static/`, `web/index.html` verweist mit `<link rel="icon">` darauf.
- In der Kopfzeile als React-Komponente `BrandMark` mit `currentColor` (eine Farbe) bzw. fester Markenfarbe, und mit `aria-hidden`, weil der Name daneben steht.
- Der Name bleibt Text aus `common.json`. Dadurch kostet der Namenswechsel keine Grafikänderung.

**Individuelle Geräte- und Anlagenicons**
- Als TSX-Komponenten in `web/src/icons/industrial/`, gezeichnet exakt nach den Regeln der gewählten Bibliothek (24er-Raster, Strich 2, runde Enden, `currentColor`).
- Ein zentrales Mapping `deviceClass.ts` mit Rückfall auf OBJ-04 (G7).
- Ein Vitest-Test prüft viewBox, Farbfreiheit und das Vorhandensein jedes Namens.
- Keine SVG-Lader und keine zusätzlichen Build-Plugins nötig, also keine weitere Abhängigkeit.

**Standardisierte UI-Icons**
- Eine Bibliothek, Empfehlung `lucide-react` (ISC), mit fester Version und Eintrag in `docs/DECISIONS.md`.
- Nur über die eigene Namensschicht `IconName` verwenden (G5). Import einzelner Icons, damit das Bundle klein bleibt.
- Alternative ohne Abhängigkeit: die rund 50 benötigten SVG-Pfade kopieren und den ISC-Hinweis von Hand in die Lizenzhinweise aufnehmen. Das ist mehr Pflegeaufwand und deshalb zweite Wahl.

**Einführung**
- Ein eigener Auftrag nach M1, weil er die gemeinsamen Dateien `Layout.tsx`, `navigation.ts`, `package.json` und `index.html` berührt.
- Bei einer neuen Abhängigkeit ist das Stufe C.
- Für den Favicon-Pfad eine kleine Backend-Änderung oder der Verweis über `/static/` (G10).

---

# H7. Offene Fragen

Nur Fragen, die das Repository nicht beantwortet.

## 1. Technisch notwendige Entscheidungen

**T-1 Neue Abhängigkeit für UI-Icons?**
- Optionen: (a) `lucide-react`, (b) `@tabler/icons-react`, (c) keine Abhängigkeit, kopierte SVGs.
- **Empfehlung: (a).** ISC ist erlaubt, der Strichstil passt zum Minimalismus, Icons sind einzeln importierbar und werden aktiv gepflegt. Lizenz und React-19-Kompatibilität vor der Aufnahme am Paket prüfen.

**T-2 Wie wird ein Gerät seiner Icon-Klasse zugeordnet?** Das Modell hat kein Typfeld.
- Optionen: (a) optionales Auswahlfeld `device_class` plus optionale CSV-Spalte (Stufe C, ändert E-41 und E-44), (b) aus Hersteller- und Modelltext ableiten, (c) erst über den Steckbrief in M4.
- **Empfehlung: (a)** nach M1, mit den Werten aus H3: plc, controller, computer, router, firewall, robot, sonst leer = generisch. Die CSV-Spalte bleibt optional, damit `testfactory/layout/devices.csv` gültig bleibt. (b) widerspricht „nicht raten“, (c) kommt spät.

**T-3 Typfeld auch für Anlagen?**
- **Empfehlung:** nein bis M7. Anlagen nutzen bis dahin das generische OBJ-03. Anlagentyp-Icons erst mit der Landkarte entscheiden.

**T-4 Auslieferung des Favicons**
- Optionen: (a) nur `<link rel="icon">` auf `/static/…`, (b) zusätzlich ein Django-Pfad für `/favicon.ico`.
- **Empfehlung: (a) plus (b).** Manche Werkzeuge und Browser fragen `/favicon.ico` direkt an und bekommen heute HTML zurück.
- Die ICO- und PNG-Dateien einmalig erzeugen und einchecken. Ein Erzeugungswerkzeug im Build wäre eine weitere Abhängigkeit.

**T-5 Web-App-Manifest (installierbar)?**
- **Empfehlung:** nicht vor M6. Eine mobile App ist ausgeschlossen, und für Lesezeichen genügen Favicon und Apple-Touch-Icon.

## 2. Fachliche Entscheidungen

**F-1 Wo erscheinen Suche, Auskunft, Einlesen und Steckbrief?** Als eigene Navigationseinträge oder am Gerät? Das entscheidet über die Zahl der Navigations-Icons.
- **Empfehlung:**
  - Suche und Auskunft global in der Navigation, zusätzlich am Gerät eingegrenzt.
  - Steckbrief nur auf der Geräteseite.
  - Einlese-Aufträge als Navigationseintrag für `manage`.

**F-2 Sollen Protokolle (MQTT, OPC UA, SSH …) Icons bekommen?**
- **Empfehlung:** nein, Text-Badges. Die Werte sind Freitext, Icons dafür wären Sonderlösungen.

**F-3 Kein Erreichbarkeitsstatus (online, offline) bestätigen?**
- **Empfehlung:** bestätigen. Die Software liest nur und kennt keine Live-Daten (Leitplanke 2). Ein solches Icon würde Überwachung vortäuschen.

**F-4 Wann kommt der endgültige Name?**
- **Empfehlung:** Bildmarke jetzt entwerfen, die Wortmarke erst nach Marken- und Domainprüfung. Die Bildmarke muss allein bestehen (B9).

## 3. Rein gestalterische Entscheidungen

**G-1 Markenfarbe?** Es gibt keine.
- **Empfehlung:** genau eine Akzentfarbe plus die vorhandenen Slate-Grautöne. Die Akzentfarbe nicht aus Grün, Rot oder Gelb wählen, damit sie nicht mit Statusfarben verwechselt wird, und nicht in den Farben der Testfabrik-Hersteller.

**G-2 Outline oder gefüllt als Grundstil?**
- **Empfehlung:** Outline mit Strich 2 für alle Funktions-Icons, gefüllt nur für Status-Badges und das Logo (F4).

**G-3 Eckradius und Strichenden?**
- **Empfehlung:** runde Enden, Eckradius 2 Einheiten. Das passt zu Lucide und Tabler und wirkt bei 16 px ruhiger.

**G-4 Welche Logo-Konzepte gehen in die erste Entwurfsrunde?**
- **Empfehlung:** 1, 3 und 11 aus H4, je in Master- und Kleinvariante, auf hellem und dunklem Grund.

**G-5 Dark Mode für die Oberfläche einplanen?**
- **Empfehlung:** die Icons sofort darauf vorbereiten (`currentColor`, negative Logo-Fassung LOGO-03). Den Dark Mode der Oberfläche als eigene spätere Entscheidung behandeln.

---

## Kurzfazit

| Punkt | Ergebnis |
| --- | --- |
| Icons gesamt | 80 (4 Marke, 76 funktional), davon 24 individuell, 56 aus einer Bibliothek |
| P0 / P1 / P2 | 35 / 21 / 24. In P0 sind nur 8 funktionale Icons und 2 Logo-Fassungen neu zu entwerfen. |
| Logo-Konzepte | 12, davon 3 empfohlen (1, 3, 11) |
| Lizenzen | 11 Bibliotheken gegen die Projektregeln geprüft (`web/scripts/license-rules.txt`, E-25, E-47). 9 sind zulässig, Font Awesome Free und Remix Icon nicht. Die Lizenzangaben selbst sind nach Wissensstand genannt und nicht am Original verifiziert. |
| Ungeklärt | 14 Fragen in H7 (5 technisch, 4 fachlich, 5 gestalterisch) |
| Wichtigste Befunde | Geräte und Anlagen haben kein Typfeld (T-2). `/favicon.ico` liefert heute HTML (T-4). Es gibt keine Farb- und Designvorgaben (G-1). |
