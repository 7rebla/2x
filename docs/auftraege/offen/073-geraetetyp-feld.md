# Auftrag 073 – Gerätetyp als Feld, in API, Admin und CSV-Import

Meilenstein: Gestaltung (D1, parallel zu M2) · Freigabestufe: C · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
