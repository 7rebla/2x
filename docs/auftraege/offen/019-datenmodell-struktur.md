# Auftrag 019 – Datenmodell Standort, Bereich, Anlage, Gerät

Meilenstein: M1 · Freigabestufe: C · Status: offen

## Ziel

Die Struktur des Betriebs (Startunterlage 4 und 5.7: Standort > Bereich > Anlage > Gerät) steht als Datenmodell in der App `assets`. Die Geräteliste der Testfabrik (`testfactory/layout/devices.csv`) passt ohne Informationsverlust hinein.

## Umfang

- Modelle in `backend/twox/assets/models.py`, englische Bezeichner, Felder nach Frage 1 (Empfehlung):
  - `Site`: `name`, eindeutig.
  - `Area`: `site` (FK, `PROTECT`), `name`; eindeutig je Standort.
  - `Plant`: `area` (FK, `PROTECT`), `key` (Kennung wie `aps-dps`), `name`, `notes` (Freitext, leer erlaubt).
  - `Device`: `plant` (FK, `PROTECT`), `key` (Kennung wie `dps-plc`), `name`, `manufacturer`, `model`, `software_version`, `ip_address`, `address_source`, `protocols`, `notes`.
    - `ip_address` ist ein `GenericIPAddressField`, leer erlaubt.
    - Die übrigen Freitextfelder erlauben leere Werte.
- Freitext als `TextField`: Die Werte in `devices.csv` sind teils über 300 Zeichen lang (Notizen, Adressherkunft, Softwarestand). Namen und Kennungen bleiben `CharField` mit fester Länge.
- Eindeutigkeit der Kennungen nach Frage 2.
- Kennungen werden geprüft: Kleinbuchstaben, Ziffern, Bindestrich. Alle Kennungen der Testfabrik erfüllen das.
- Für alle Modelle:
  - `created_at`, `updated_at`, `__str__`, `Meta.ordering`.
  - `verbose_name` mit `gettext_lazy` (für Auftrag 034).
  - Eindeutigkeit über `UniqueConstraint` mit Namen.
- Eine Migration `assets/migrations/0001_initial.py`.
- Tests `backend/tests/assets/` (neu, mit `__init__.py`):
  - die Kette anlegen;
  - Eindeutigkeit: ein doppelter Bereichsname am selben Standort schlägt fehl, am anderen nicht;
  - `PROTECT` verhindert das Löschen eines Standorts mit Bereichen;
  - eine ungültige IP-Adresse weist `full_clean()` ab, eine leere ist erlaubt;
  - eine ungültige Kennung wird abgewiesen;
  - ein Notiztext mit über 1000 Zeichen wird unverändert gespeichert.
- Die Datei `testfactory/layout/devices.csv` liegt in diesem Auftrag nicht im Container. Die Zuordnung der 13 Spalten zu den Feldern steht als Tabelle im Kurzbericht.

## Nicht-Ziele

- API, Admin, Oberfläche (Aufträge 026, 032).
- CSV-Import (Auftrag 031).
- Strukturierte Protokoll-Listen oder mehrere Adressen je Gerät (Steckbrief, M4).
- Rechte je Standort.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/assets/models.py`, `backend/twox/assets/migrations/` (neu)
- neu: `backend/tests/assets/` (`__init__.py`, Testdateien)

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-019`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18019` setzen.
- Unter Git Bash vor Befehlen mit `/out/…` `MSYS_NO_PATHCONV=1` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0. `D logs migrate` zeigt `assets.0001_initial` als angewendet.
2. Prüfungen und Typen:
   - `D run --rm backend-dev ruff check .` meldet `All checks passed!`.
   - `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0.
   - `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
3. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen. `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
4. `D run --rm backend-dev python manage.py makemigrations --check --dry-run` meldet `No changes detected`.
5. `D run --rm -v \"$PWD/web/openapi:/out\" backend-dev python manage.py spectacular --file /out/schema.yml`, danach zeigt `git diff --exit-code -- web/openapi` keinen Unterschied.
6. Abräumen: `D --profile dev down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); Antworten von a7 auf Frage 1 und 2 (Datenmodell, Stufe C).

- Welle 1. Einziger Auftrag mit Migrationen der App `assets`.
- `settings.py` und `urls.py` nicht anfassen; `twox/assets/urls.py` legt 016 an.
- **Keine neue Abhängigkeit**, keine Baum-Bibliothek: Die Tiefe ist fest, einfache Fremdschlüssel genügen.
- Grundlage der Felder sind die 13 Spalten von `testfactory/layout/devices.csv`: `site, area, plant_id, plant_name, device_id, device_name, manufacturer, model, software_version, ip_address, address_source, protocols, notes`.
- Erwartete Zahlen laut Datei: 14 Datenzeilen, 1 Standort, 3 Bereiche, 10 Anlagen, 13 Geräte.
- Besonderheiten der Datei:
  - Die Zeile `aps-charging` hat kein Gerät, nur `notes`; deshalb gibt es `Plant.notes`.
  - `ip_address` ist bei sechs Geräten leer.
- Laut Auftrag 106 und `testfactory/layout/description.md` legen die Spalten das Datenmodell nicht fest; das entscheidet a7 hier.
- Laut Startunterlage 5.7 kommen später Dateien (Auftrag 024), Steckbrief-Felder (M4) und Beziehungen (M7) an das Gerät. Nichts davon hier anlegen.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

1. **Felder und Kennungen der Struktur**
   - (a) Wie im Umfang:
     - Standort und Bereich nur mit Namen.
     - Anlage und Gerät mit Kennung (`key`) und Namen.
     - Gerätefelder 1:1 aus der CSV als Freitext, die IP-Adresse als geprüftes Feld.
     - `Plant.notes` für Anlagen ohne Gerät.
   - (b) Alle vier Ebenen mit Kennung. Die CSV braucht dann zwei Spalten mehr; Testfabrik-Datei und ihre Tests müssten angepasst werden.
   - (c) Gerätefelder schon strukturiert (Protokolle als Liste, mehrere Adressen).
   - Empfehlung: (a). Passt ohne Änderung an `devices.csv`; die Strukturierung gehört zum Steckbrief (M4).
2. **Eindeutigkeit der Kennungen**
   - (a) `Plant.key` und `Device.key` sind im ganzen System eindeutig.
   - (b) Eindeutig nur je Standort.
   - Empfehlung: (a). Ein Betrieb, keine Mandanten (Startunterlage 4, „Nicht in Stufe 1“). (b) braucht Prüfungen über die Kette, die die Datenbank nicht direkt abbildet.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
