# Auftrag 073 – Gerätetyp als Feld, in API, Admin und CSV-Import

Meilenstein: Gestaltung (D1, parallel zu M2) · Freigabestufe: C · Status: zur Prüfung

## Ziel

Geräte bekommen ein Feld „Gerätetyp“ mit fester Auswahl, damit die Oberfläche je Typ ein eigenes Symbol zeigen kann (Auftrag 074). Der Typ ist in API, Admin und Formular pflegbar und kann über eine optionale 14. Spalte im CSV-Import gesetzt werden (E-53).

## Umfang

- Modell `assets.Device`: neues Feld `device_class` (`CharField` mit `TextChoices`): `plc` (SPS), `controller` (Controller/Embedded), `computer` (Rechner/Edge), `router`, `firewall`, `robot`, `other` (Sonstiges); Standard `other`, nicht leer. Anzeigenamen mit `gettext_lazy`, deutsche Übersetzung im Katalog (`makemessages -l de --add-location=file`, siehe README). Migration in `assets`.
- API (`DeviceWrite`/`Device`) und Admin (Liste, Filter): Feld lesen und schreiben; Schema und Client neu erzeugen.
- Protokoll: Änderungen am Feld erscheinen im Änderungsprotokoll (auditlog-Registrierung prüfen, `include_fields` ergänzen).
- CSV-Import: optionale 14. Spalte `device_class` am Ende; Dateien mit 13 Spalten bleiben gültig (Typ dann unverändert bzw. `other` beim Anlegen). Unbekannte Werte sind Fehler mit Zeile und Spalte. Probelauf, alles oder nichts und Zähler wie bisher. Formatbeschreibung in der Import-Oberfläche (de/en) und in README ergänzen.
- Testfabrik: `testfactory/layout/devices.csv` um die Spalte `device_class` ergänzen. Den Typ je Gerät **nur aus vorhandenen Daten** ableiten (Kennung, Modell, Rolle in der Datei bzw. `network-plan.md`); jede Zuordnung im Kurzbericht begründen. Tests und Prüfungen der Testfabrik (`testfactory/tests`, Manifest-/Layout-Prüfungen) und die Abnahmetests von M1 (`backend/tests/acceptance/test_m1.py`, `web/e2e/m1-acceptance.spec.ts`, Import-Tests) anpassen, damit sie mit 14 Spalten grün sind.
- Formular auf der Strukturseite (Gerät anlegen/bearbeiten): Auswahlfeld „Gerätetyp“ (de/en). Das Symbol selbst kommt erst mit 074.
- Tests: Modell/Choices, API lesen/schreiben/ungültiger Wert 400, Admin-Filter, Protokolleintrag, CSV mit 13 und 14 Spalten, unbekannter Typ, Testfabrik-Datei importiert mit den erwarteten Typen.

## Nicht-Ziele

- Symbole in der Oberfläche (Auftrag 074), Anlagentypen, weitere Gerätetypen über die sieben hinaus.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/assets/` (models, Migration, serializers, admin, csv_import, integrity falls nötig), `backend/twox/accounts/audit.py` (nur Registrierung des Felds), `backend/locale/de/LC_MESSAGES/django.po`
- `backend/tests/assets/`, `backend/tests/acceptance/test_m1.py`, `backend/tests/config/test_i18n.py` falls betroffen
- `testfactory/layout/devices.csv` und betroffene Tests unter `testfactory/tests/`
- `web/openapi/schema.yml`, `web/src/api/generated/**`, Geräteformular in `web/src/pages/structure/forms.tsx`, `web/src/locales/{de,en}/assets.json`, `web/src/locales/{de,en}/import.json`, Import-Formatbeschreibung, betroffene Tests inkl. `web/e2e/m1-acceptance.spec.ts` und `import.spec.ts`
- `README.md` (Abschnitt Geräteliste/CSV)

## Akzeptanzkriterien (prüfbar)

`D` = `docker compose -p twox-073`, `W` = `docker compose -p twox-073-web -f deploy/compose/compose.web.yaml`, `.env` mit `TWOX_API_PORT=18073`.

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Backend-Job aus `ci.yml` komplett grün (ruff, format, mypy, pytest, pytest -m worker, makemigrations --check, Lizenzen, Schema aktuell, Übersetzungskatalog aktuell).
2. Web-Job komplett grün (lint, typecheck, test, build, licenses, api:generate ohne Unterschied).
3. Testfabrik-Job aus `ci.yml` komplett grün.
4. `import_devices /testfactory/layout/devices.csv --user <manage-Konto> --commit` legt 13 Geräte mit den im Kurzbericht genannten Typen an; ein zweiter Lauf meldet 0 geändert.
5. Browser-Test wie in `ci.yml` (inkl. „Create test account“) bestanden, zweimal ohne `down -v`.
6. Abräumen mit `down -v` endet mit Exit 0.

## Vorgaben und Hinweise

Voraussetzung: E-53 (a7, 22.11.2026). Parallel läuft 070 (nur `web/`, Theme); berühre dessen Dateien nicht (`index.css`, `theme/`, `Layout.tsx`, Einstellungen). M2-Aufträge kommen später hinzu.

- Keine neue Abhängigkeit. Sprache: Code Englisch, Kurzbericht Deutsch. Keine Personennamen, keine lokalen Pfade mit Benutzernamen. Lokale Design-Vorlagen unter `docs/design/bildmarke/` nicht lesen und nicht nennen. Nur ausdrücklich genannte Pfade stagen. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

Entschieden (E-53, 22.11.2026): Feld mit fester Auswahl, pflegbar in Formular und Admin, optionale 14. CSV-Spalte, Geräteliste der Testfabrik wird ergänzt.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Akzeptanzkriterien 0–6 erfüllt, Läufe am 22.11.2026 im Container (Docker Engine 29.9.3, Compose v5.7.0). Keine neue Abhängigkeit, keine offene Frage an a7.

### Was wurde gebaut?

- **Modell** (`backend/twox/assets/models.py`): `DeviceClass(TextChoices)` mit `plc`, `controller`, `computer`, `router`, `firewall`, `robot`, `other`; Feld `Device.device_class` (`CharField(20)`, `choices`, Standard `other`, nicht leer, nicht NULL), Bezeichnung „device class“. Migration `assets/0002_device_class.py` (bestehende Geräte erhalten `other`).
- **Übersetzung** (`django.po`): Gerätetyp, SPS, Controller/Embedded, Rechner/Edge, Router, Firewall, Roboter, Sonstiges sowie die zwei neuen Import-Meldungen.
- **API**: `device_class` in `DeviceWrite`, `PatchedDeviceWrite` und `Device` (nach `name`). Ohne Angabe beim Anlegen `other`, bei PUT bleibt der gespeicherte Wert. Ungültiger Wert ergibt 400 am Feld. Im Schema als `DeviceClassEnum`; Schema und Client neu erzeugt.
- **Admin**: Spalte und Filter „Gerätetyp“ in der Geräteliste; das Änderungsformular zeigt die Auswahl von Django.
- **Protokoll**: `audit.py` registriert alle eigenen Spalten über `tracked_fields()`, das neue Feld ist damit ohne Änderung erfasst (geprüft mit Tests für API, Admin und Import).
- **CSV-Import** (`csv_import.py`):
  - Kopf mit 13 Spalten oder mit `device_class` als 14. Spalte. Jede Zeile braucht so viele Felder wie der Kopf.
  - Wert leer oder Spalte fehlt: Neues Gerät `other`, vorhandenes behält seinen Typ.
  - Unbekannter Wert (auch Großschreibung wie `PLC`) ist ein Fehler an Zeile und Spalte `device_class`; die Meldung nennt die erlaubten Werte.
  - Zeile ohne `device_id` darf keinen Typ haben.
  - Kopffehler nennen zusätzlich „Als letzte Spalte darf device_class folgen.“ Probelauf, alles oder nichts, Zähler unverändert.
- **Testfabrik**: `testfactory/layout/devices.csv` um `device_class` ergänzt (Zuordnung unten); `testfactory/tests/test_layout.py` prüft Kopf, Werte je Gerät und leere Spalte bei der Zeile ohne Gerät.
- **Oberfläche**:
  - `pages/structure/deviceClass.ts` (neu): Liste der sieben Typen mit Prüfung gegen `DeviceClassEnum` durch den Typprüfer und `isDeviceClass`.
  - Geräteformular (`forms.tsx`): Auswahlfeld „Gerätetyp“/„Device class“ nach dem Namen, ohne leere Option, Start `other`. Das Formular wirkt auf der Struktur- und auf der Geräteseite.
  - Import-Seite: Beschreibung der optionalen Spalte, ihrer Werte und des Verhaltens bei leerem Wert (de/en).
  - Locales `assets.json` (`fields.device_class`, `deviceClass.*`) und `import.json`.
- **README** (Abschnitt Device list) und `web/src/pages/README.md` nachgezogen.

**Typzuordnung der Testfabrik** (nur aus Kennung, Modell und Rolle in `devices.csv` und `network-plan.md`):

| Gerät | Typ | Begründung |
| --- | --- | --- |
| `dps-plc`, `hbw-plc`, `drill-plc`, `mill-plc`, `aiqs-plc` | `plc` | Modell „S7-1200“ von Siemens, Name „SPS …“, Kennung `-plc`; im Netzplan „SPS S7-1200 · OPC UA 4840“, je SPS ein OPC-UA-Server |
| `dps-txt`, `aiqs-txt`, `agv-txt`, `cgw-txt` | `controller` | Modell „TXT 4.0 Controller“ von fischertechnik, Name „TXT-Controller …“; im Netzplan „TXT 4.0“, sprechen MQTT mit der Zentralsteuerung. Auch `cgw-txt` ist laut Modell ein TXT 4.0; seine Rolle als Cloud-Gateway (MQTT-Bridge) macht ihn nicht zum Router |
| `ccu-rpi` | `computer` | Modell „Raspberry Pi 4B“, ein Einplatinenrechner; Rolle Zentralsteuerung mit MQTT-Broker, Node-RED, Bedienoberfläche und SSH (Netzplan „Dienste und Ports“), also Rechner/Edge und keine SPS |
| `aps-router` | `router` | Modell „TL-WR902AC (AC750 Wi-Fi Travel Router)“ von TP-Link, Name „WLAN-Router der Fertigungslinie“; im Netzplan Router mit DHCP, Adresse 192.168.0.1 |
| `ur5e` | `robot` | Modell „UR5e (e-Series)“ von Universal Robots, Name „Roboter UR5e“, Anlage „Roboterzelle UR5e“ |
| `opnsense-fw` | `firewall` | Modell „OPNsense (virtuelle Maschine)“, Name „Firewall OPNsense“, Anlage „Firewall zwischen Büronetz und Anlagennetz“ |
| `aps-charging` (Zeile ohne Gerät) | leer | kein Gerät; die Gerätespalten bleiben leer |

Ergebnis: 5 × `plc`, 4 × `controller`, je 1 × `computer`, `router`, `robot`, `firewall`; `other` kommt nicht vor.

### Wie wurde getestet?

`D` = `docker compose -p twox-073`, `W` = `docker compose -p twox-073-web -f deploy/compose/compose.web.yaml`, Testfabrik mit `-p twox-073-tf -f deploy/compose/testfactory.yaml`; `.env` aus `.env.example` (ohne BOM) mit `TWOX_API_PORT=18073`. Die Umgebungen „2x“ und „twox-leit“ wurden nicht berührt.

| AK | Ergebnis |
| --- | --- |
| 0 | erfüllt: `docker version` (29.9.3) und `docker compose version` (v5.7.0), Exit 0 |
| 1 | erfüllt: `ruff check` „All checks passed!“; `ruff format --check` „135 files already formatted“; `mypy` „Success: no issues found in 135 source files“; `pytest` 1169 bestanden, 4 abgewählt, nichts übersprungen; `pytest -m worker` 4 bestanden; Übersetzungskatalog aktuell (`git diff -I POT-Creation-Date` und `git status` leer, nach dem Commit); `makemigrations --check` „No changes detected“; Lizenzprüfung „License check passed.“ (59 Pakete); Schema aktuell (nach dem Commit kein Unterschied) |
| 2 | erfüllt: `W --profile dev build web-dev`, `npm ci`, `lint` und `typecheck` ohne Meldung, `test` 23 Dateien mit 386 Fällen bestanden, `build` Exit 0, `licenses` „License check passed.“, `api:generate` ohne Unterschied zum committeten Stand |
| 3 | erfüllt: `build check`; `ruff check`, `ruff format --check` (18 Dateien), `mypy` (14 Dateien) ohne Befund; `unittest` (check-offline) 216 Tests `OK (skipped=1)` (der Skip ist vorhanden und nicht von diesem Auftrag); Manifest-Prüfungen beider Manifeste OK und in kanonischer Form; `testfactory/extern` existiert nicht |
| 4 | erfüllt: nach `down -v` frische Datenbank, Konto `e2e-manager` mit Rolle manage; erster `import_devices /testfactory/layout/devices.csv --user e2e-manager --commit`: 14 Zeilen, 1/3/10/13 angelegt, „Saved.“; zweiter Lauf: 0 angelegt, 0 geändert, 1/3/10/13 unverändert. In der Datenbank haben alle 13 Geräte den Typ aus der Tabelle oben |
| 5 | erfüllt: Bau `migrate api worker web-dev`, `pull e2e`, `npm ci`, `up -d --wait` (Migration `assets.0002_device_class` angewendet), „Create test account“ („Created account …“), `D --profile e2e run --rm e2e`: 22 bestanden. Zweiter Lauf ohne `down -v` („Updated account …“): 22 bestanden |
| 6 | erfüllt: `D --profile dev --profile e2e down -v`, `W --profile dev down -v` und `down -v` für `twox-073-tf` je Exit 0; danach kein Container und kein Volume mit `twox-073` |

„Create test account“ lief in PowerShell: Werte aus `.env` gelesen, das Kennwort nur als Umgebungsvariable `TWOX_ACCOUNT_PASSWORD` gesetzt und an `docker compose exec -T -e TWOX_ACCOUNT_PASSWORD` nur als Variablenname übergeben.

Neue und geänderte Tests:

- Backend:
  - Modell: sieben Werte und Bezeichnungen, Standard `other`, jeder Wert speicherbar, ungültige Werte (`""`, `PLC`, `switch`, `sps`) von `full_clean` abgewiesen, nicht NULL.
  - API: Feld in der Antwort, Anlegen ohne Typ ergibt `other`, alle sieben Werte schreiben und lesen, PATCH mit Protokolleintrag `{"device_class": ["other", "plc"]}`, PUT ohne Feld behält den Wert. Ungültige Werte (`""`, `PLC`, `sps`, `switch`, `null`, `3`) ergeben 400 nur am Feld. Rolle read erhält 403. Schema mit `DeviceClassEnum`.
  - Admin: Spalte, Filter je Typ, Ändern über das Formular mit Protokolleintrag, unbekannter Wert als Formularfehler.
  - CSV: Testfabrik mit erwarteten Typen, 13 und 14 Spalten, leerer Wert, gespeicherter Typ bleibt bei 13 Spalten und bei leerem Wert, gleicher Wert unverändert, geänderter Typ mit Protokolleintrag, Probelauf, Leerzeichen, sechs unbekannte Werte mit Zeile und Spalte, mehrere Fehlerzeilen, falsche Köpfe mit `device_class` an falscher Stelle, Feldanzahl bei 14 Spalten.
  - Übersetzung: Meldung de/en, deutsche Bezeichnungen.
  - Abnahme M1: Typen aller Geräte, Protokoll `device_class: [null, "plc"]` bei `dps-plc`.
- Vitest:
  - `deviceClass.test.ts`: Reihenfolge, Prüffunktion, Bezeichnungen in beiden Sprachen.
  - Strukturseite: sieben Optionen mit Start `other`, Auswahl gesendet, 400 am Feld mit erhaltener Auswahl, deutsche Bezeichnungen.
  - Geräteseite: gespeicherter Typ vorausgewählt, Änderung gesendet; erwartete Rümpfe um `device_class` ergänzt.
  - Import-Seite: Beschreibung der optionalen Spalte de/en.
- Playwright:
  - `import.spec.ts`: Datei mit 14 Spalten setzt `plc` und `robot`, sichtbar im Bearbeiten-Formular. Dieselbe Datei mit 13 Spalten danach unverändert. Unbekannter Typ `switch` als Fehler in Zeile 3, Spalte `device_class`.
  - `m1-acceptance.spec.ts`: Protokoll „device_class: (empty) → plc“ bei `dps-plc`.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-ae3b742a13499ac02`
- Arbeitsverzeichnis: `.claude/worktrees/agent-ae3b742a13499ac02`
- Commits: `ed4b761` (Backend, Import, Testfabrik, Schema/Client), `7247b7f` (Oberfläche), `fcba430` (README), dazu dieser Kurzbericht. Nicht gepusht, nichts zusammengeführt.

### Abweichungen und Hinweise

1. **Neue Datei `web/src/pages/structure/deviceClass.ts`** (mit Test): gemeinsame Liste der Typen für Formular und Import-Seite; Auftrag 074 kann daran die Symbole hängen. Nicht ausdrücklich genannt, liegt aber neben dem Geräteformular.
2. **Weitere berührte Dateien in `web/`** (betroffene Tests bzw. Doku): `pages/structure/testData.ts` (Testdaten brauchen das Pflichtfeld des Typs `Device`), `pages/StructurePage.test.tsx`, `pages/DevicePage.test.tsx`, `pages/ImportPage.test.tsx`, `pages/README.md`. Keine Datei von 070 (`index.css`, `theme/`, `Layout.tsx`, Einstellungsseite) geändert. Konfliktgefahr mit 070 nur, falls 070 Farbklassen in `forms.tsx` oder `ImportPage.tsx` ändert: Ich habe dort nur Zeilen ergänzt und die vorhandene Klasse `inputClass` wiederverwendet, keine bestehende Zeile mit Farbklassen verändert.
3. **Geräteseite zeigt den Typ nur im Bearbeiten-Formular**, nicht in der Feldliste von `DevicePage.tsx` (nicht im Auftrag genannt; Darstellung mit Symbol folgt in 074). Vorschlag für 074: dort Symbol und Bezeichnung in der Feldliste ergänzen.
4. **Leerer Wert in der 14. Spalte** gilt wie eine fehlende Spalte (neu `other`, vorhanden unverändert). Der Auftrag regelt nur die fehlende Spalte; so kann eine Datei mit 14 Spalten den Typ für einzelne Geräte offen lassen. Werte müssen genau so geschrieben sein (`plc`, nicht `PLC`); Leerzeichen am Rand werden wie bei allen Werten entfernt.
5. **`testfactory/layout/description.md`** (Zeile 13 nennt die Inhalte der Geräteliste) nicht geändert, weil nicht im Auftrag genannt; die Aufzählung dort ist ohnehin nicht vollständig.
6. Der Hinweistext im Schema (`DeviceImportForm.file`) nennt jetzt die optionale Spalte; die Formatversion bleibt 1.
