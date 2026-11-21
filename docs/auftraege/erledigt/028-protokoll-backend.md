# Auftrag 028 – Protokoll: wer hat was wann geändert (Backend)

Meilenstein: M1 · Freigabestufe: C · Status: zur Prüfung

## Ziel

Jede Änderung an Standorten, Bereichen, Anlagen, Geräten, Dateien und Dateiversionen wird mit Benutzer, Zeitpunkt und geänderten Feldern protokolliert. Nach Frage 4 gilt das auch für Konten und Rollen (Startunterlage 4: „Ein Protokoll zeigt, wer was geändert hat“; 5.7: „wer darf was, wer hat was getan“). Die API liefert das Protokoll seitenweise und filterbar. Im Admin lässt es sich nicht ändern.

## Umfang

- Nach Frage 1 (Empfehlung) `django-auditlog` 3.4.2:
  - `auditlog` in `INSTALLED_APPS`.
  - `auditlog.middleware.AuditlogMiddleware` hinter der Authentication-Middleware.
  - `AUDITLOG_DISABLE_REMOTE_ADDR = True` nach Frage 2 (keine IP-Adresse im Protokoll).
- Registrierung an einer Stelle: `backend/twox/accounts/audit.py`, aufgerufen in `AccountsConfig.ready()`.
  - `Site`, `Area`, `Plant`, `Device`, `Document`, `DocumentVersion`.
  - Nach Frage 4 zusätzlich `accounts.User` mit `exclude_fields` für `password` und `last_login` und mit `m2m_fields={\"groups\"}`. Damit sind Rollenwechsel, `is_active`, `is_staff` und `is_superuser` protokolliert.
- `acting_as(user)` in `audit.py`: ein Kontextmanager für Vorgänge außerhalb einer Anfrage (Management-Befehle, Import). Grundlage ist `set_actor` aus `auditlog.context` (laut auditlog-Doku).
- Admin, in `backend/twox/accounts/admin.py`: Die Admin-Ansicht der Protokolleinträge ist nur lesend, auch für Superuser (`has_add_permission`, `has_change_permission` und `has_delete_permission` liefern `False`). Die mitgelieferte Ansicht von auditlog wird dafür ersetzt.
- Endpunkt `GET /api/v1/audit-log/` in `twox/accounts/urls.py`:
  - Seitenweise (`PageNumberPagination`, feste Seitengröße), neueste zuerst.
  - Felder: `id`, `timestamp`, `actor` (Benutzername oder `null`), `action` (`create`, `update`, `delete`), `object_type` (z. B. `assets.device`), `object_id`, `object_repr`, `changes` (Feld → [alt, neu]).
  - Filter: `object_type`, `object_id`, `actor`.
  - Rechte nach Frage 3.
- Tests `backend/tests/accounts/test_audit.py`:
  - Parametrisiert über alle registrierten Modelle: Anlegen und Ändern ergibt je einen Eintrag mit Akteur und Feldänderungen.
  - Über die API (026): Anlegen und Ändern eines Geräts mit Sitzung ergibt einen Eintrag mit dem angemeldeten Benutzer.
  - Eine zweite Version über den Dienst aus 024 in `acting_as` ergibt einen Eintrag mit Akteur.
  - Ein Rollenwechsel über `create_account --update` ergibt einen Eintrag; kein Eintrag enthält einen Kennwort-Hash.
  - Es wird keine IP-Adresse gespeichert.
  - Die Admin-Ansicht ist nur lesend.
  - Rechte, Filter und Seiten des Endpunkts.
- `backend/tests/config/test_settings.py` anpassen. `backend/tests/config/expected_paths/accounts.py`: `/api/v1/audit-log/`. Schema und Client neu erzeugen.

## Nicht-Ziele

- Oberfläche (033). Protokoll von Anmeldungen; fehlgeschlagene Anmeldungen stehen seit 020 im Serverprotokoll.
- Löschen oder Bereinigen von Protokolleinträgen.
- Schutz auf Datenbankebene (Frage 5).
- Massenänderungen ohne `save()`: `bulk_create` und `QuerySet.update` erzeugen keine Einträge. Der Import (031) speichert deshalb einzeln.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/pyproject.toml`, `backend/uv.lock`
- `backend/twox/config/settings.py`
- `backend/twox/accounts/` (neu `audit.py`; `apps.py`, `admin.py`, `urls.py`; Serializer und Ansicht des Protokolls)
- `backend/tests/accounts/test_audit.py` (neu), `backend/tests/config/test_settings.py`, `backend/tests/config/expected_paths/accounts.py`
- `web/openapi/schema.yml`, `web/src/api/generated/**`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-028`, `W` für `docker compose -p twox-028-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18028` setzen.
- Unter Git Bash vor Befehlen mit `/out/…` `MSYS_NO_PATHCONV=1` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0. `D logs migrate` zeigt die Migrationen von `auditlog` als angewendet.
2. Prüfungen und Typen:
   - `D run --rm backend-dev ruff check .` meldet `All checks passed!`.
   - `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0.
   - `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
3. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen. `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
4. `D run --rm backend-dev python manage.py makemigrations --check --dry-run` meldet `No changes detected`.
5. `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0. Im Kurzbericht stehen alle neu im Lock stehenden Pakete mit Version und Lizenz.
6. Schema:
   - `D run --rm -v \"$PWD/web/openapi:/out\" backend-dev python manage.py spectacular --file /out/schema.yml` endet ohne Warnungen.
   - Das committete Schema enthält `/api/v1/audit-log/`.
   - `git diff --exit-code -- web/openapi` zeigt danach keinen Unterschied.
7. Client:
   - `W --profile dev build web-dev`, `W run --rm web-dev npm ci`, `W run --rm web-dev npm run api:generate`; danach zeigt `git diff --exit-code -- web/openapi web/src/api` keinen Unterschied.
   - `W run --rm web-dev npm run typecheck` endet mit Exit-Code 0.
8. Abräumen: `D --profile dev down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); 020, 021, 024 und 026 sind nach `main` zusammengeführt; Antworten von a7 auf Frage 1 bis 4.

- Welle 5, parallel zu 029 (Datei-API) und 030 (Anmeldung in der Oberfläche).
- Einziger Auftrag der Welle mit `settings.py`, `pyproject.toml` und `uv.lock`.
- `twox/files/` und `twox/assets/` nicht anfassen; die Registrierung steht zentral in `accounts/audit.py`.
- **Reihenfolge beim Zusammenführen: 028 vor 029.** 029 erzeugt danach Schema und Client neu.
- **Neue Abhängigkeit (nur nach Frage 1):** django-auditlog 3.4.2.
  - Lizenz MIT; an PyPI geprüft: Python 3.10 bis 3.14, Django 4.2 bis 6.1, Upload 08.11.2026.
  - Verlangt `Django>=4.2` und `python-dateutil>=2.7.0`; python-dateutil steht über Celery schon im Lock.
- Ungeprüft ist, wie die Admin-Ansicht von auditlog 3.4.2 Rechte vergibt. Deshalb wird sie ersetzt und getestet.
- Der Befehl `auditlogflush` (laut Doku: löscht Einträge, nicht umkehrbar) bleibt nach Frage 5 ungesperrt. Im Kurzbericht nennen, damit 038 ihn in der Doku erwähnt.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

1. **Protokoll-Mechanismus (neue Abhängigkeit)**
   - (a) django-auditlog 3.4.2: MIT, eine Tabelle mit Feldänderungen und Akteur, erklärt für Django 6.1 und Python 3.14.
   - (b) django-simple-history 3.13.0: BSD-3-Clause laut README, eine Schattentabelle je Modell; Django 6.1 nur im Changelog genannt.
   - (c) django-pghistory 3.9.2: BSD-3-Clause, über Trigger; Django 6.1 nicht erklärt.
   - (d) Eigenes Modell mit Signalen, ohne Abhängigkeit.
   - Empfehlung: (a). Einzige Variante mit erklärter Unterstützung für Django 6.1 und Python 3.14, keine weitere neue Abhängigkeit.
2. **IP-Adresse im Protokoll speichern?**
   - (a) Nein (`AUDITLOG_DISABLE_REMOTE_ADDR`).
   - (b) Ja.
   - Empfehlung: (a). Ein personenbezogenes Datum ohne Nutzen für die Abnahme.
3. **Wer darf das Protokoll lesen?**
   - (a) Nur „Verwalten“.
   - (b) „Verwalten“ und „Lesen“.
   - Empfehlung: (a). Das Protokoll nennt Benutzer; „Lesen“ braucht es für die Auskunft nicht.
4. **Konten und Rollen mitprotokollieren?**
   - (a) Ja: Benutzer (ohne Kennwort-Hash und letzte Anmeldung) samt Gruppenzugehörigkeit, also Rollenwechsel, Sperren und Superuser-Recht.
   - (b) Nein, nur Struktur und Dateien. Die Lücke wird festgehalten.
   - Empfehlung: (a). Startunterlage 5.7 zählt „wer darf was“ zum Protokoll.
5. **Schutz der Protokolleinträge über den Admin hinaus?**
   - (a) In M1 nur: Der Admin ist lesend, und es gibt keinen API-Weg zum Ändern. Wer Zugang zu Datenbank oder Container hat, kann weiter alles ändern, auch über `auditlogflush`; das wird dokumentiert.
   - (b) Zusätzlich ein Schutz in der Datenbank (Trigger oder entzogene Rechte für `UPDATE` und `DELETE`) in einem eigenen Auftrag.
   - Empfehlung: (a) für M1; (b) vor Version 0.1 erneut prüfen.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Akzeptanzkriterien erfüllt; Läufe am 21.11.2026 im Container auf dem committeten Stand. Keine offene Frage, die den Auftrag aufhält.

### Was wurde gebaut?

- `backend/pyproject.toml`, `backend/uv.lock`: `django-auditlog>=3.4.2,<3.5`. `uv lock` im Builder-Image (wie in 020) hat genau ein Paket ergänzt. mypy-Override `follow_untyped_imports` für `auditlog.*` (kein `py.typed`), wie für allauth.
- `backend/twox/config/settings.py`:
  - `auditlog` in `INSTALLED_APPS`, vor den Projekt-Apps (damit `accounts/admin.py` die Admin-Ansicht von auditlog ersetzen kann).
  - `auditlog.middleware.AuditlogMiddleware` direkt nach `AuthenticationMiddleware`.
  - `AUDITLOG_DISABLE_REMOTE_ADDR = True` (Frage 2).
  - `AUDITLOG_STORE_JSON_CHANGES = True` (siehe Abweichung 2).
  - `SPECTACULAR_SETTINGS["ENUM_NAME_OVERRIDES"]`: die Aktionen heißen im Schema `AuditActionEnum` statt des allgemeinen `ActionEnum`.
- `backend/twox/accounts/audit.py` (neu), aufgerufen in `AccountsConfig.ready()`:
  - `register_models()` registriert `Site`, `Area`, `Plant`, `Device`, `Document`, `DocumentVersion` und `accounts.User` (`exclude_fields` `password`, `last_login`; `m2m_fields={"groups"}`). `AUDITED_MODELS` nennt alle.
  - Jede Registrierung mit `include_fields` = eigene Spalten des Modells (siehe Abweichung 3).
  - `acting_as(user)`: Kontextmanager auf Grundlage von `auditlog.context.set_actor`; stellt danach den Akteur von außen (z. B. der Middleware) wieder her (siehe Abweichung 4).
- `backend/twox/accounts/admin.py`: Die Admin-Ansicht von auditlog wird abgemeldet und durch `AuditLogEntryAdmin` ersetzt: `has_add_permission`, `has_change_permission`, `has_delete_permission` immer `False`; Liste mit Zeit, Aktion, Typ, Objekt, Akteur; Filter, Suche; Detail zeigt nur Zeit, Akteur, Aktion, Typ, Objekt-ID, Objekt und Änderungen (nicht `remote_addr`, `remote_port`, `cid`, `actor_email`).
- `backend/twox/accounts/serializers.py`, `views.py`, `urls.py`: `GET /api/v1/audit-log/` (`AuditLogView`, `operation_id` `audit_log_list`):
  - Rechte `CanManage` (Frage 3). Nur GET; POST, PUT, PATCH, DELETE ergeben 405.
  - `PageNumberPagination` mit fester Seitengröße 50 (`?page_size` wird ignoriert), neueste zuerst (`-timestamp`, `-pk`), Antwort `count`, `next`, `previous`, `results`.
  - Felder `id`, `timestamp`, `actor` (Benutzername oder `null`), `action` (`create`, `update`, `delete`), `object_type` (`app_label.model`, z. B. `assets.device`), `object_id` (Zahl), `object_repr`, `changes`.
  - `changes`: Feld → `[alt, neu]`; beim Anlegen alt `null`, beim Löschen neu `null`. Gruppen eines Benutzers (Rolle) im Format von auditlog: `{"type": "m2m", "operation": "add"|"delete", "objects": [Gruppennamen]}`. Beides steht als `oneOf` im Schema, der erzeugte Client hat dafür einen Union-Typ.
  - Filter `object_type` (Muster `^[a-z0-9_]+\.[a-z0-9_]+$`), `object_id` (1 bis 2^63−1), `actor` (1 bis 150 Zeichen). Ungültige Werte ergeben 400 mit Fehler am Parameter, unbekannte eine leere Liste. Einträge der Art „access“ blendet die API aus (nichts im Projekt erzeugt sie).
  - Eine Seite braucht höchstens 6 Abfragen (getestet mit 55 Einträgen).
- `backend/twox/accounts/management/commands/create_account.py`: entfernt nur Rollengruppen, die das Konto wirklich hat (siehe Abweichung 1).
- Tests:
  - neu `backend/tests/accounts/test_audit.py` (68 Fälle).
  - `backend/tests/config/test_settings.py`: `auditlog` installiert, Middleware-Liste, `AUDITLOG_DISABLE_REMOTE_ADDR` und `AUDITLOG_STORE_JSON_CHANGES`, Middleware nach Authentication.
  - `backend/tests/config/expected_paths/accounts.py`: `/api/v1/audit-log/`.
  - `tests/config/test_api.py` bleibt unverändert und ohne neue Ausnahme grün.
- `web/openapi/schema.yml` und `web/src/api/generated/**` neu erzeugt (`AuditLogEntry`, `AuditActionEnum`, `PaginatedAuditLogEntryList`, `auditLogList`).

**Inhalt von `test_audit.py`:**
- Registriert sind genau die sieben Modelle; Benutzer ohne `password` und `last_login`, mit `groups`.
- Parametrisiert über alle Modelle: Anlegen in `acting_as` ergibt genau einen Eintrag mit Akteur, `object_id`, `object_repr` und Feldwerten, nur eigene Spalten. Ändern (alle außer `DocumentVersion`) ergibt genau einen Eintrag mit Akteur und `{feld: [alt, neu]}`. Ein Test prüft, dass die Fälle alle registrierten Modelle abdecken.
- Version: Ändern scheitert mit `VersionImmutableError`, kein Änderungseintrag. Löschen ergibt einen Eintrag mit alten Werten. Speichern ohne Änderung ergibt keinen Eintrag. Leerer Wert ist `null`, nicht der Text „None“.
- Ohne Anfrage und ohne `acting_as` kein Akteur. `acting_as` verschachtelt: danach gilt wieder der äußere Akteur.
- API (026): Gerät anlegen und ändern mit Sitzung ergibt zwei Einträge mit dem angemeldeten Benutzer.
- Dienst (024): `create_document` und `add_version` in `acting_as` ergeben Einträge mit Akteur, Version 2 mit `number [null, 2]`.
- `create_account --update` von `read` auf `manage` ergibt die Einträge „Gruppe read entfernt“ und „Gruppe manage hinzugefügt“. `--update` mit gleicher Rolle (nur neues Kennwort) ergibt keinen Eintrag.
- Kein Kennwort-Hash: Nach Anlegen, Rollenwechsel, `set_password`, Änderung von `is_staff` und einer Anmeldung (setzt `last_login`) kommt in keiner Spalte eines Eintrags ein Hash oder ein Testkennwort vor. Kein Eintrag hat `password` oder `last_login` in `changes`; `serialized_data` und `additional_data` sind immer leer.
- Keine IP-Adresse: Anfrage mit `REMOTE_ADDR` und `X-Forwarded-For` speichert `remote_addr = NULL`, keine der Adressen steht irgendwo im Eintrag, auch nicht der Sitzungsschlüssel.
- Admin: die eigene Ansicht ist registriert; alle drei Rechte `False`, keine Massenlöschung. Superuser sieht Liste und Detail (ohne Änderungsrecht). Hinzufügen, Ändern, Löschen (einzeln und als Massenaktion) ergeben 403 bzw. ändern nichts. Rollen ohne Superuser-Recht landen bei `/admin/login/`.
- Endpunkt: anonym, ohne Rolle und `read` 403, `manage` und Superuser 200; Schreibmethoden 405, nichts geändert; Felder der Antwort; Aktionen und fehlender Akteur; Rollenwechsel mit Gruppennamen; neueste zuerst; alle Filter, unbekannte Werte leere Liste, 11 ungültige Werte 400; Seiten zu 50 mit `next`/`previous`, Seite 3 ergibt 404; höchstens 6 Abfragen je Seite; Schema mit `operation_id`, Parametern, Feldern, `AuditActionEnum` und ohne Fehler von drf-spectacular auf stderr.

**Neue Pakete im Lock**

| Paket | Version | Lizenz | mitgezogen von |
| --- | --- | --- | --- |
| django-auditlog | 3.4.2 | MIT (Metadaten „License: MIT“, Klassifikator „MIT License“, `LICENSE` im Rad); `check-licenses.sh` liest „MIT License“ | direkt |

Sonst nichts: Django und python-dateutil (2.9.0.post0) standen schon im Lock. Lizenzprüfung: 59 Pakete (vorher 58).

**Prüfung des Pakets** (Quelltext 3.4.2 im Container gelesen):
- Keine Netzzugriffe, keine Telemetrie: kein `urllib.request`, `requests`, `http.client`, `socket` (nur `urllib.parse.unquote` in `mixins.py`). Das Rad enthält nur Python-Code, Vorlagen und Übersetzungen (de, ja, ko), keine statischen Dateien.
- `LogEntry` hat die Spalten `remote_addr`, `remote_port`, `cid`, `actor_email`, `serialized_data`, `additional_data`. Mit `AUDITLOG_DISABLE_REMOTE_ADDR` schreibt die Middleware keine IP-Adresse, auch nicht aus `X-Forwarded-For` (getestet). `serialized_data` bleibt leer (`serialize_data` nicht gesetzt), `additional_data` ebenso (kein Modell hat `get_additional_data`). Sitzungsdaten speichert auditlog nicht. Was die übrigen Spalten trotzdem speichern, steht unter „Hinweise“.

### Wie wurde getestet?

`D` = `docker compose -p twox-028`, `W` = `docker compose -p twox-028-web -f deploy/compose/compose.web.yaml`; `.env` aus `.env.example` mit `TWOX_API_PORT=18028`. Docker Engine 29.9.3, Compose v5.7.0.

| AK | Ergebnis |
| --- | --- |
| 0 | erfüllt: `docker version` und `docker compose version` Exit 0 |
| 1 | erfüllt: Bau Exit 0, `up -d --wait` Exit 0; nach `down -v` und neuem Start zeigt `D logs migrate` 17 Migrationen `auditlog.0001_initial` bis `auditlog.0017_add_actor_email ... OK` |
| 2 | erfüllt: `All checks passed!`; `105 files already formatted`, Exit 0; `Success: no issues found in 105 source files` |
| 3 | erfüllt: `781 passed, 4 deselected`, 0 fehlgeschlagen, 0 übersprungen (`-rs` ohne Eintrag); `pytest -m worker`: `4 passed` |
| 4 | erfüllt: `No changes detected` |
| 5 | erfüllt: `License check passed.` (59 Pakete); neues Paket siehe Tabelle |
| 6 | erfüllt: `spectacular` ohne Ausgabe, Exit 0; Schema enthält `/api/v1/audit-log/`; nach dem Commit erneut erzeugt, `git diff --exit-code -- web/openapi` Exit 0, keine neue Datei |
| 7 | erfüllt: Bau, `npm ci`, `api:generate` Exit 0, danach `git diff --exit-code -- web/openapi web/src/api` Exit 0, keine neue Datei; `typecheck` Exit 0 |
| 8 | erfüllt: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` Exit 0 |

Zusätzlich wie in der CI: web-Job komplett (`lint`, `typecheck`, `test` 73 passed, `build`, `licenses` mit `License check passed.`, `api:generate` ohne Unterschied). e2e: Bau mit `web-dev`, `pull e2e`, `npm ci`, `up`, Schritt „Create test account“ wie in `ci.yml` (Kennwort nur als Variablenname), `run e2e`: `8 passed`. Am laufenden Dienst: `GET /api/v1/audit-log/` anonym 403, `/admin/auditlog/logentry/` anonym 302; Anmeldungen der Browsertests (setzen `last_login`) erzeugten keinen Eintrag.

Gegenproben während der Arbeit: Ohne `include_fields` enthielt der Eintrag beim Anlegen auch Rückwärtsbeziehungen als Text (z. B. `documents: [null, "files.Document.None"]`); mit `extend_schema` an der Klasse meldete drf-spectacular einen Fehler auf stderr, den der erste Schematest nicht sah (jetzt prüft der Test auch `sys.stderr`).

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a61d7bda9bf7cda53`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a61d7bda9bf7cda53` (relativ zum Projektordner)
- Nicht gepusht, nichts zusammengeführt.

### Abweichungen

1. **Rollenwechsel ergibt zwei Einträge, nicht einen.** auditlog schreibt je Gruppenoperation einen Eintrag: „read entfernt“ und „manage hinzugefügt“. Außerdem protokolliert auditlog bei `remove()` jede übergebene Gruppe, auch eine, die das Konto gar nicht hatte. `create_account` entfernte bisher immer beide Rollengruppen; jedes `--update` (z. B. in jedem e2e-Lauf) hätte „manage und read entfernt, manage hinzugefügt“ geschrieben. Deshalb entfernt der Befehl jetzt nur Rollengruppen, die das Konto hat (drei Zeilen in `create_account.py`, nicht ausdrücklich im Umfang, aber in `twox/accounts/`). Ergebnis: Rollenwechsel = zwei zutreffende Einträge, gleiche Rolle = kein Eintrag. Ein einziger Eintrag je Rollenwechsel ginge nur mit eigenem Protokollcode neben auditlog.
2. **`AUDITLOG_STORE_JSON_CHANGES = True`** (nicht im Umfang genannt). Ohne die Einstellung speichert auditlog alle Werte als Text: `null` wäre `"None"`, `true` wäre `"True"`, ein Gerät namens „None“ wäre von einem leeren Wert nicht zu unterscheiden. Mit ihr stehen `null`, Wahrheitswerte und Zahlen als JSON-Werte in `changes`; Zeiten bleiben Text (UTC ohne Zonenangabe, z. B. `2026-11-21 22:09:19.347373`), Fremdschlüssel sind die id.
3. **`include_fields` je Modell** (eigene Spalten aus `_meta.concrete_fields`) zusätzlich zur Vorgabe. Grund siehe Gegenprobe oben. Neue Spalten eines Modells kommen dadurch automatisch ins Protokoll.
4. **`acting_as` stellt den äußeren Akteur wieder her.** `set_actor` von auditlog setzt eine Kontextvariable und setzt sie nach dem Block nicht zurück. Ohne Gegenmaßnahme verlören Änderungen nach einem `acting_as`-Block innerhalb einer Anfrage ihren Akteur. Getestet.
5. **`object_id` ist eine Zahl** (`LogEntry.object_id`, im Schema `nullable`, weil auditlog es nur bei ganzzahligen Schlüsseln füllt; alle registrierten Modelle haben solche).
6. **`DocumentVersion` kennt nur „Anlegen“**: Versionen sind unveränderlich (024), der parametrisierte Änderungstest läuft deshalb über sechs Modelle; für Versionen prüft ein eigener Test, dass Ändern scheitert und keinen Eintrag erzeugt.
7. **Schema-Name `AuditActionEnum`** über `ENUM_NAME_OVERRIDES` in `settings.py`, damit spätere Felder namens `action` (z. B. 029, 031) nicht mit diesem Enum kollidieren.

### Hinweise (für Leitstelle, 033 und 038)

- **`auditlogflush`** (auditlog 3.4.2, `auditlog/management/commands/auditlogflush.py`) löscht Protokolleinträge und ist nicht gesperrt (Frage 5). Ebenso `auditlogmigratejson`. Für die Doku in 038.
- **Was auditlog außer den Änderungen speichert:**
  - `actor_email`: die E-Mail-Adresse des Akteurs zum Zeitpunkt der Änderung (bei unseren Konten leer, `create_account` setzt keine).
  - `remote_port`: die Zahl aus dem Kopf `X-Forwarded-Port`, falls ein Client ihn mitschickt. `AUDITLOG_DISABLE_REMOTE_ADDR` schaltet das nicht ab. Keine IP-Adresse, aber vom Client gesetzt.
  - `cid`: der Wert des Kopfs `X-Correlation-ID`, falls mitgeschickt (bis 255 Zeichen).
  - Keine dieser Spalten erscheint in API oder Admin. Abschalten ginge für `cid` über `AUDITLOG_CID_HEADER = None`, für `remote_port` und `actor_email` nur mit eigener Middleware. Nicht umgesetzt, weil nicht verlangt; bitte entscheiden, ob das nötig ist.
- **Grenzen von auditlog** (für 038):
  - `bulk_create` und `QuerySet.update` schreiben nichts (Nicht-Ziel des Auftrags).
  - `groups.clear()` protokolliert als „entfernt“ alle Gruppen des Systems, nicht nur die des Kontos (auditlog nimmt bei `post_clear` alle Gruppen).
  - Eine Änderung von der Gruppenseite aus (`group.user_set.add(user)`) erzeugt einen Eintrag am Gruppenobjekt (nicht registriert), nicht am Benutzer.
  - Wird ein Benutzer gelöscht, setzt auditlog `actor` auf `NULL`; der Name des Akteurs geht dann verloren.
- **Für 029:** Nach dem Zusammenführen dieses Zweigs Schema und Client neu erzeugen. Neue Datei-Endpunkte erzeugen über die Dienste aus 024 automatisch Einträge mit dem angemeldeten Benutzer (Middleware).
- **Für 031:** Der Import speichert einzeln und läuft, falls außerhalb einer Anfrage (Worker), in `acting_as(user)`.
- **Für 033:** `changes` hat zwei Formen (siehe Schema, `oneOf`); Zeiten in `changes` sind Text in UTC ohne Zonenangabe.

Keine weitere neue Abhängigkeit. `docs/DECISIONS.md` und `docs/STATUS.md` nicht geändert. Kein Push.

### Nacharbeit (nach Prüfung der Leitstelle)

**Befund:** auditlog 3.4.2 übernimmt zwei Kopfzeilen ungeprüft in den Eintrag:
- `X-Correlation-ID` als `cid` (`CharField(255)`).
- `X-Forwarded-Port` als `remote_port` (`int(...)`, auch mit `AUDITLOG_DISABLE_REMOTE_ADDR`).

Ein zu langer `cid` oder ein negativer bzw. zu großer Port lässt das Schreiben des Eintrags scheitern. Das geschieht in `post_save`, also nach dem Speichern der Änderung: Die Änderung bleibt ohne Eintrag gespeichert, die Antwort ist 500. Damit ließ sich das Protokoll umgehen. Die Punkte unter „Hinweise“ zu `cid` und `remote_port` sind damit erledigt.

**Änderungen (Commit `eba5d56`):**
- `settings.py`: `AUDITLOG_CID_HEADER = None`. `set_cid` liest dann keinen Kopf mehr und setzt `cid` immer auf `None` (`auditlog/cid.py`, 3.4.2).
- `twox/accounts/audit.py`: `AuditMiddleware`, Unterklasse von `auditlog.middleware.AuditlogMiddleware`. `_get_remote_addr` und `_get_remote_port` liefern immer `None`; übernommen wird nur der angemeldete Benutzer (`_get_actor`). Sie ersetzt in `MIDDLEWARE` die Middleware von auditlog an derselben Stelle (nach `AuthenticationMiddleware`).
- `tests/config/test_settings.py`: Middleware-Liste; `AUDITLOG_CID_HEADER is None`; die Middleware von auditlog selbst steht nicht in der Liste.
- `tests/accounts/test_audit.py`, 12 neue Fälle:
  - Je Anfrage über die API (Standort anlegen, dann ändern) mit `X-Correlation-ID` aus 300 Zeichen, kurzem `X-Correlation-ID`, `X-Forwarded-Port` „abc“, „-1“, „99999999999“ und „8443“, `X-Forwarded-For` und allem zusammen: Die Änderung ist gespeichert (201/200, Name geändert), beide Einträge sind geschrieben, mit dem angemeldeten Benutzer und mit `cid`, `remote_port`, `remote_addr` = `None`. Die Werte von Korrelations-ID und Adressen stehen in keiner Spalte.
  - Kein Eintrag in der Tabelle hat danach `cid`, `remote_port` oder `remote_addr`.
  - Gegenprobe im Test: Die Middleware von auditlog liefert für „-1“ und „99999999999“ diese Zahlen, `AuditMiddleware` liefert `None`. `set_cid` liest mit dem Standardkopf den 300-Zeichen-Wert, mit `None` nichts.

**Gegenprobe gegen den alten Stand** (Einstellungen kurz zurückgestellt, danach wiederhergestellt, nicht committet): Die neuen Tests scheitern.
- 300-Zeichen-`cid`: `DataError: value too long for type character varying(255)`.
- Port „-1“: `IntegrityError … auditlog_logentry_remote_port_check`.
- Kurzer `cid`: wird gespeichert (`'client-value'`).
- Folgefehler: Läuft der Fall mit 300 Zeichen vorher, scheitern auch die übrigen Fälle derselben Sitzung mit `DataError`; die Ursache habe ich nicht untersucht. Einzeln geht „abc“ durch.

**Gelangt noch ein anderer Wert aus der Anfrage in den Eintrag?** Am Quelltext 3.4.2 abgelesen: nein.
- Die Middleware gibt nur `remote_addr`, `remote_port` und `actor` weiter; die ersten beiden sind jetzt `None`, `actor` ist der Benutzer der Sitzung. `_set_extra_data` setzt nur diese Schlüssel.
- `log_create` und `log_m2m_changes` füllen sonst `content_type`, `object_pk`/`object_id` (Primärschlüssel), `object_repr` (`str()` des Objekts, `TextField`), `changes` (Feldwerte nach der Prüfung durch Serializer und Modell, `JSONField`), `cid` (jetzt immer `None`). `serialized_data` und `additional_data` bleiben leer.
- **`actor_email` bleibt:** die E-Mail-Adresse des Akteurs aus seinem Konto, nicht aus der Anfrage. Höchstens 254 Zeichen wie `EmailField`, passt also in die Spalte. Bei unseren Konten ist sie leer.
- Inhalte wie Namen oder Notizen stehen weiter in `object_repr` und `changes`. Das sind die protokollierten Daten selbst, ohne Längengrenze in der Spalte.

**Prüfungen** nach der Nacharbeit, `docker compose -p twox-028`, `.env` mit `TWOX_API_PORT=18028`:

| Prüfung | Ergebnis |
| --- | --- |
| Bau `migrate api worker backend-dev`, `up -d --wait` | Exit 0; `logs migrate` zeigt 17 Migrationen von auditlog |
| `ruff check` | `All checks passed!` |
| `ruff format --check` | 105 Dateien, Exit 0 |
| `mypy` | `Success: no issues found in 105 source files` |
| `pytest` | `793 passed, 4 deselected`, nichts übersprungen |
| `pytest -m worker` | `4 passed` |
| `makemigrations --check --dry-run` | `No changes detected` |
| Lizenzprüfung | `License check passed.` |
| `spectacular` | Exit 0, ohne Ausgabe; `git diff --exit-code -- web/openapi` Exit 0 (API unverändert, Client daher nicht neu erzeugt) |
| `--profile dev --profile e2e down -v`, `W --profile dev down -v` | Exit 0, kein Container und kein Volume von twox-028 übrig |

Zusätzlich am laufenden Dienst (uvicorn, Laufzeit-Image): als Testkonto angemeldet, fünf `POST /api/v1/sites/` mit je einer der Kopfzeilen (300-Zeichen-Korrelations-ID, Port „-1“, „99999999999“, „abc“, `X-Forwarded-For`). Alle 201, fünf Standorte und fünf Einträge mit Akteur, `cid`, `remote_port` und `remote_addr` leer.

`main` (026, 027) habe ich nicht eingeführt; Schema und Client erzeugt die Leitstelle beim Zusammenführen neu. e2e und web-Job liefen in der Nacharbeit nicht erneut; es gibt keine Änderung an API, Schema oder Oberfläche.
