# Auftrag 019 – Datenmodell Standort, Bereich, Anlage, Gerät

Meilenstein: M1 · Freigabestufe: C · Status: zur Prüfung

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

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

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

### Was wurde gebaut?

- `backend/twox/assets/models.py`: `Site`, `Area`, `Plant`, `Device` nach Frage 1 (a) und 2 (a), gemeinsame abstrakte Basis `TimestampedModel` (`created_at`, `updated_at`).
  - Fremdschlüssel mit `PROTECT` und `related_name` (`areas`, `plants`, `devices`).
  - Benannte `UniqueConstraint`: `assets_site_name_unique`, `assets_area_site_name_unique` (Standort + Name), `assets_plant_key_unique`, `assets_device_key_unique` (beide systemweit).
  - Kennungen: `CharField(64)` mit `RegexValidator` `^[a-z0-9-]+$` (Code `invalid_key`). Namen: `CharField(200)`.
  - Gerätefelder `manufacturer`, `model`, `software_version`, `address_source`, `protocols`, `notes` und `Plant.notes` als `TextField(blank=True)`.
  - `ip_address`: `GenericIPAddressField(blank=True, null=True)`; leer wird als NULL gespeichert (Django verlangt `null=True`, weil ein leerer Text kein gültiger `inet`-Wert ist).
  - `__str__`: Standort und Bereich zeigen den Namen, Anlage und Gerät `Name (Kennung)`. `Meta.ordering`: Name bzw. Kennung. `verbose_name` und `verbose_name_plural` (Modelle) sowie die Feldbezeichnungen mit `gettext_lazy`.
- `backend/twox/assets/migrations/0001_initial.py` (von `makemigrations` erzeugt, mit `ruff format` formatiert) und `migrations/__init__.py`.
- `backend/tests/assets/__init__.py`, `backend/tests/assets/test_models.py`: 23 Testfälle (mit Parametrisierung). Abgedeckt: Kette anlegen; Anlage ohne Gerät mit Notiz; doppelter Bereichsname am selben Standort schlägt fehl (Datenbank und `full_clean`), am anderen nicht; Standortname eindeutig; Anlagen- und Gerätekennung systemweit eindeutig; `PROTECT` bei Standort, Bereich und Anlage; ungültige IP von `full_clean()` abgewiesen, leere erlaubt; ungültige Kennungen (Großbuchstaben, Unterstrich, Leerzeichen, Punkt, Umlaut, leer) bei Anlage und Gerät abgewiesen, Kennungen der Testfabrik angenommen; Notiz und Adressherkunft mit über 1000 Zeichen unverändert gespeichert; leere Freitextfelder erlaubt; `ordering`, `verbose_name` und Constraint-Namen vorhanden.

**Zuordnung der 13 Spalten von `testfactory/layout/devices.csv`** (längster Wert in der Datei in Klammern):

| Spalte | Feld | Typ |
| --- | --- | --- |
| `site` (10) | `Site.name` | `CharField(200)`, eindeutig |
| `area` (15) | `Area.name` | `CharField(200)`, eindeutig je Standort |
| `plant_id` (14) | `Plant.key` | `CharField(64)`, Kennung, systemweit eindeutig |
| `plant_name` (42) | `Plant.name` | `CharField(200)` |
| `device_id` (11) | `Device.key` | `CharField(64)`, Kennung, systemweit eindeutig |
| `device_name` (40) | `Device.name` | `CharField(200)` |
| `manufacturer` (31) | `Device.manufacturer` | `TextField`, leer erlaubt |
| `model` (60) | `Device.model` | `TextField`, leer erlaubt |
| `software_version` (105) | `Device.software_version` | `TextField`, leer erlaubt |
| `ip_address` (13) | `Device.ip_address` | `GenericIPAddressField`, leer = NULL |
| `address_source` (155) | `Device.address_source` | `TextField`, leer erlaubt |
| `protocols` (108) | `Device.protocols` | `TextField`, leer erlaubt |
| `notes` (319) | `Device.notes`; bei der Zeile ohne Gerät (`aps-charging`) `Plant.notes` | `TextField`, leer erlaubt |

Alle 10 Anlagen- und 13 Gerätekennungen der Datei erfüllen das Kennungsmuster und sind eindeutig; die 7 belegten Adressen sind gültige IPv4-Adressen, die 6 (plus Zeile ohne Gerät) leeren werden NULL. Ein Import ist nicht gebaut (Auftrag 031).

### Wie wurde getestet?

Alle Befehle mit `D` = `docker compose -p twox-019` im Wurzelverzeichnis des Arbeitsverzeichnisses, `.env` aus `.env.example` mit `TWOX_API_PORT=18019`. Docker Engine 29.9.3, Compose v5.7.0. Die Läufe fanden auf dem Stand des Commits mit Modellen, Migration und Tests statt.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version` (29.9.3), `docker compose version` (v5.7.0), Exit-Code 0 |
| 1 | erfüllt | Build Exit-Code 0; `up -d --wait …` Exit-Code 0; `D logs migrate`: `Applying assets.0001_initial... OK` |
| 2 | erfüllt | `All checks passed!`; `57 files already formatted`, Exit-Code 0; `Success: no issues found in 57 source files` |
| 3 | erfüllt | `133 passed, 4 deselected`, Exit-Code 0, nichts übersprungen (`-rs` ohne Eintrag); `pytest -m worker`: `4 passed, 133 deselected`, Exit-Code 0 |
| 4 | erfüllt | `No changes detected` |
| 5 | erfüllt | `spectacular` Exit-Code 0; `git diff --exit-code -- web/openapi` Exit-Code 0, keine neue Datei |
| 6 | erfüllt | `D --profile dev --profile e2e down -v` Exit-Code 0; keine Container und Volumes des Projekts `twox-019` mehr |

Zusätzlich wie in der CI: `sh scripts/check-licenses.sh` meldet `License check passed.` (keine neue Abhängigkeit).

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-ab59c12bd071e1006`
- Arbeitsverzeichnis: `.claude/worktrees/agent-ab59c12bd071e1006` (relativ zum Projektordner)
- Nicht gepusht, nichts zusammengeführt.

### Abweichungen und Hinweise

- **`manufacturer` und `model` sind `TextField`**, nicht `CharField`. Der Umfang nennt nur Namen und Kennungen als `CharField`; die übrigen Gerätefelder sind laut E-41 Freitext 1:1 aus der CSV. So gibt es keine Längengrenze, die ein späterer Import verletzen könnte.
- **Kennungsmuster wörtlich nach Umfang** (`^[a-z0-9-]+$`): Ein Bindestrich am Anfang oder Ende, doppelte Bindestriche oder nur `-` wären damit erlaubt. Soll das strenger sein (`^[a-z0-9]+(-[a-z0-9]+)*$`), ist es eine Zeile plus neue Migration; alle Kennungen der Testfabrik erfüllen beide Muster. Die Prüfung läuft in `full_clean()` (Validator), nicht als Datenbank-Constraint.
- **`Meta.ordering` und `Meta.constraints` als Tupel**, weil Ruff (`RUF012`) Listen als veränderliche Klassenattribute bemängelt.
- **Reihenfolge in der Migration:** Django legt `Area`, `Plant`, `Device`, `Site` an und ergänzt danach `Area.site` und die Constraints. Das ist die unveränderte Ausgabe von `makemigrations`.
- **`twox.assets` stand schon in `INSTALLED_APPS`**; `settings.py` und `urls.py` sind nicht berührt.
- Lokal liegen noch die Images `twox-019-*`; Container, Netze und Volumes sind entfernt.
- Keine offenen Fragen an a7.
