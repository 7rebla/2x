# Auftrag 028 – Protokoll: wer hat was wann geändert (Backend)

Meilenstein: M1 · Freigabestufe: C · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
