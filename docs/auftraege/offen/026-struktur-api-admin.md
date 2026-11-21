# Auftrag 026 – API und Admin für Standorte, Bereiche, Anlagen, Geräte

Meilenstein: M1 · Freigabestufe: C · Status: zur Prüfung

## Ziel

Die Struktur lässt sich über die API anlegen, lesen und bearbeiten: lesend für „Lesen“, schreibend für „Verwalten“. Der Admin zeigt die Modelle für Superuser.

## Umfang

- Serializer und ViewSets in `backend/twox/assets/` für `Site`, `Area`, `Plant` und `Device`:
  - `GET` für Liste und Einzelobjekt, dazu `POST`, `PUT` und `PATCH`. Kein `DELETE` (Frage 1).
  - Pfade unter `/api/v1/`: `sites/`, `areas/`, `plants/` und `devices/`, über einen Router in `twox/assets/urls.py`.
  - Filter per Abfrageparameter: `areas?site=`, `plants?area=`, `devices?plant=`, `devices?site=` (über die Kette). Ohne neue Abhängigkeit, mit eigener Logik in `get_queryset`.
  - Die Geräte-Antwort enthält die Kette lesbar: `plant`, `area` und `site` je mit `id` und Namen bzw. Kennung, über `select_related`.
  - Rechte: `CanManageOrReadOnly` aus 021.
  - Prüfungen: Eindeutigkeit und Format der Kennung liefern 400 mit Feldfehlern; die IP-Adresse wird geprüft.
  - Fehlermeldungen mit `gettext` markieren (für 034).
- Schema: eindeutige `operation_id`s, alle Felder typisiert. Schema und Client neu erzeugen.
- `backend/twox/assets/admin.py`: die vier Modelle mit Liste, Suche (Name, Kennung, IP) und Filtern. Zugang nur für Superuser (Admin-Seite aus 016).
- Tests `backend/tests/assets/`:
  - Rechte: anonym 403, ohne Rolle 403, `read` liest, schreibt aber nicht, `manage` schreibt.
  - Filter und Validierung.
  - Keine N+1-Abfragen in der Geräteliste (`django_assert_max_num_queries`).
- `backend/tests/config/expected_paths/assets.py`: die neuen Pfade. Der Aufzähl-Test aus 025 bleibt ohne neue Ausnahme grün.

## Nicht-Ziele

- Löschen (Frage 1), Massenänderungen, Import (031).
- Oberfläche (032).
- Protokoll (028). Änderungen über die API laufen über `save()`, damit das Protokoll später greift.
- Seitenweise Ausgabe; die Struktur ist klein, bei Bedarf später.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/assets/`: neu `serializers.py`, `views.py`, `admin.py`; `urls.py` füllen
- `backend/tests/assets/` (neue Testdateien), `backend/tests/config/expected_paths/assets.py`
- `web/openapi/schema.yml`, `web/src/api/generated/**`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-026`, `W` für `docker compose -p twox-026-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18026` setzen.
- Unter Git Bash vor Befehlen mit `/out/…` `MSYS_NO_PATHCONV=1` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Prüfungen und Typen:
   - `D run --rm backend-dev ruff check .` meldet `All checks passed!`.
   - `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0.
   - `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
3. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen. `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
4. `D run --rm backend-dev python manage.py makemigrations --check --dry-run` meldet `No changes detected`.
5. Schema:
   - `D run --rm -v \"$PWD/web/openapi:/out\" backend-dev python manage.py spectacular --file /out/schema.yml` endet ohne Warnungen.
   - Das committete Schema enthält `/api/v1/sites/`, `/api/v1/areas/`, `/api/v1/plants/` und `/api/v1/devices/`.
   - `git diff --exit-code -- web/openapi` zeigt danach keinen Unterschied.
6. Client:
   - `W --profile dev build web-dev`, `W run --rm web-dev npm ci`, `W run --rm web-dev npm run api:generate`; danach zeigt `git diff --exit-code -- web/openapi web/src/api` keinen Unterschied.
   - `W run --rm web-dev npm run typecheck` und `… npm run lint` enden mit Exit-Code 0.
7. Abräumen: `D --profile dev down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); 016, 019, 021 und 025 sind nach `main` zusammengeführt.

- Welle 4, parallel zu 027 (Testkonto und Selbsttest). Beide ändern Schema und Client.
- **Reihenfolge beim Zusammenführen: 026 zuerst.** Danach erzeugt 027 auf dem neuen `main` Schema und Client neu; nichts wird von Hand gemischt.
- Keine Migration in `assets`; die Modelle stehen seit 019. Ist doch eine nötig, vorher Rückfrage an die Leitstelle.
- `settings.py` nicht anfassen.
- **Keine neue Abhängigkeit** (kein django-filter).
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

1. **Löschen von Standorten, Bereichen, Anlagen und Geräten in M1?** („Daten löschen“ ist Stufe C.)
   - (a) Kein Löschen über API und Oberfläche; Superuser können im Admin löschen, soweit `PROTECT` es erlaubt.
   - (b) „Verwalten“ darf leere Objekte (ohne Kinder, ohne Dateien) über die API löschen.
   - Empfehlung: (a). Die Startunterlage verlangt „anlegen, bearbeiten“; Löschen mit Protokoll und Rückfrage kann ein eigener Auftrag werden.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Was wurde gebaut?**

- `twox/assets/serializers.py`:
  - `SiteSerializer`, `AreaSerializer` (`site` als id), `PlantSerializer` (`area` als id).
  - Geräte mit zwei Serializern: `DeviceWriteSerializer` für `POST`/`PUT`/`PATCH` (`plant` als id) und `DeviceSerializer` für jede Antwort, mit `plant` (`id`, `key`, `name`), `area` (`id`, `name`) und `site` (`id`, `name`). Im Schema heißen sie `DeviceWrite`, `PatchedDeviceWrite` und `Device`.
  - Eindeutigkeit mit eigenen, per `gettext_lazy` markierten Meldungen am Feld: Standortname, Anlagen- und Gerätekennung (`UniqueValidator`). Bereichsname je Standort über `validate()` als Fehler am Feld `name`, nicht als allgemeiner `non_field_errors`-Fehler; gilt auch beim Umbenennen und Verschieben.
  - Kennungsformat über `validate_key` aus 019. Die IP-Adresse wird geprüft (IPv4 und IPv6); `""` und `null` werden als „keine Adresse“ (`null`) gespeichert.
- `twox/assets/views.py`: `StructureViewSet` (List, Retrieve, Create, Update; kein Destroy), Rechte `CanManageOrReadOnly`.
  - Filter in `get_queryset` nur bei der Liste: `areas?site=`, `plants?area=`, `devices?plant=`, `devices?site=` (über `plant__area__site`); die Filter für Geräte lassen sich kombinieren.
  - Ungültige Werte (`abc`, leer, `0`, negativ, über bigint) ergeben 400 mit Fehler am Parameter. Eine unbekannte id ergibt eine leere Liste.
  - Geräteliste mit `select_related("plant__area__site")`. Nach einem Schreibzugriff wird das Gerät mit derselben Abfrage neu geladen und als `Device` beantwortet.
  - Die Filter stehen mit `extend_schema` im Schema; die `operation_id`s erzeugt drf-spectacular (`sites_list` … `devices_partial_update`), ein Test hält sie fest.
- `twox/assets/urls.py`: `SimpleRouter` (keine API-Wurzel, keine Format-Endungen) mit `sites`, `areas`, `plants`, `devices`.
- `twox/assets/admin.py`: vier `ModelAdmin` mit Liste, Suche (Name, Kennung; beim Gerät auch die IP; beim Bereich auch der Standortname), Filtern nach den Eltern, `list_select_related`, Zeitstempel nur lesbar. Zugang nur für Superuser über die Admin-Seite aus 016. Löschen geht nur dort, `PROTECT` hält Eltern mit Kindern.
- Tests in `backend/tests/assets/` (`conftest.py` mit kleiner Struktur aus zwei Standorten und den Clients je Rolle; IP-Adressen aus den Dokumentationsbereichen 192.0.2.0/24 und 2001:db8::/32):
  - `test_api_permissions.py`: anonym und ohne Rolle 403 beim Lesen und Schreiben; `read` liest, `POST`/`PUT`/`PATCH` ergeben 403 und ändern nichts; `manage` und Superuser schreiben (201/200); `DELETE` ergibt 405 (für `read` 403) und löscht nichts; `OPTIONS` nennt kein `DELETE`.
  - `test_api.py`: Antworten und Kette; Schreiben und Verschieben; Schreiben läuft über `save()` (`post_save` je Objekt, für 028); alle Filter und ungültige Filterwerte; Eindeutigkeit, Kennungsformat, Länge, IP, unbekannte Eltern, Pflichtfelder; Abfragezahl der Geräteliste mit 34 Geräten höchstens 4 (`django_assert_max_num_queries`); Schema mit `operation_id`s, Typen, Filtern, `DeviceWrite`/`Device` und ohne `delete`.
  - `test_admin.py`: Registrierung; Liste, Anlegen und Ändern für Superuser; `anonymous`, ohne Rolle, `read` und `manage` landen bei `/admin/login/`; Suche nach Name, Kennung, IPv4 und IPv6; Filter nach Eltern; Löschen geschützt bzw. möglich.
- `tests/config/expected_paths/assets.py`: die acht neuen Pfade. `tests/config/test_api.py` bleibt unverändert und ohne neue Ausnahme grün.
- `web/openapi/schema.yml` und `web/src/api/generated/**` neu erzeugt.

**Wie wurde getestet?** `D` = `docker compose -p twox-026`, `W` = `docker compose -p twox-026-web -f deploy/compose/compose.web.yaml`; `.env` aus `.env.example` mit `TWOX_API_PORT=18026`. Docker Engine 29.9.3, Compose v5.7.0.

| AK | Ergebnis |
| --- | --- |
| 0 | erfüllt: `docker version` und `docker compose version` Exit 0 |
| 1 | erfüllt: Bau Exit 0, `up -d --wait` Exit 0 (db, valkey, api, worker healthy); nach dem letzten Code-Stand neu gebaut und gestartet |
| 2 | erfüllt: `All checks passed!`; `103 files already formatted`, Exit 0; `Success: no issues found in 103 source files` |
| 3 | erfüllt: `705 passed, 4 deselected`, 0 fehlgeschlagen, 0 übersprungen; `pytest -m worker`: `4 passed` |
| 4 | erfüllt: `No changes detected` (keine Migration) |
| 5 | erfüllt: `spectacular` ohne Ausgabe, Exit 0; das Schema enthält `/api/v1/sites/`, `/api/v1/areas/`, `/api/v1/plants/`, `/api/v1/devices/` (dazu je `{id}/`); nach dem Commit erneut erzeugt, `git diff --exit-code -- web/openapi` ohne Unterschied |
| 6 | erfüllt: Bau, `npm ci`, `api:generate` Exit 0, danach kein Unterschied in `web/openapi web/src/api` und keine neue Datei; `typecheck` und `lint` Exit 0 |
| 7 | erfüllt: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` Exit 0; danach keine Container und Volumes von `twox-026` |

Zusätzlich wie in der CI: Lizenzprüfung Python `License check passed.` (58 Pakete); web-Job komplett: `test` 73 passed, `build` und `licenses` (`License check passed.`) Exit 0; e2e (`--profile e2e run --rm e2e`) `5 passed`. Am laufenden Dienst: `GET /api/v1/devices/` anonym 403, `/admin/assets/device/` anonym 302.

Gegenprobe Abfragezahl: Mit `Device.objects.all()` statt `select_related` scheitert der Test („Expected to perform 4 queries or less but 106 were done“); danach zurückgesetzt.

**Zweig und Arbeitsverzeichnis:** Zweig `worktree-agent-a7c37676d964be992`, Arbeitsverzeichnis `.claude/worktrees/agent-a7c37676d964be992`. Kein Push, nichts zusammengeführt.

**Abweichungen und Hinweise**

1. Geräte haben zwei Schema-Komponenten: Schreiben mit `DeviceWrite` (`plant` als id), Lesen mit `Device` (`plant`, `area`, `site` als Objekte). Ein Serializer für beides ginge nur mit `COMPONENT_SPLIT_REQUEST` in `settings.py`, das hier nicht geändert werden darf. Bereiche und Anlagen nennen ihre Eltern als id, wie im Auftrag verlangt.
2. `admin.ModelAdmin[...]` ist zur Laufzeit nicht indizierbar (dafür bräuchte das Laufzeit-Image django-stubs-ext). Die Basisklassen werden daher unter `TYPE_CHECKING` typisiert.
3. Fehler bei Filterwerten nutzen die Meldungen von DRF (bereits übersetzt). Eigene Meldungen gibt es nur bei der Eindeutigkeit; sie sind mit `gettext_lazy` markiert. Die Meldung zum Kennungsformat stammt aus dem Modell (019).
4. Grenze: Legen zwei Anfragen gleichzeitig dieselbe Kennung an, greift erst die Datenbank-Constraint; die zweite Anfrage endet dann mit 500 statt 400. Bei einer Verwaltung durch wenige Personen ist das unwahrscheinlich; vorgemerkt für 038 (Doku) oder einen späteren Auftrag.
5. Anlagen- und Gerätekennungen sind je Art eindeutig (Modell aus 019): Ein Gerät darf so heißen wie eine Anlage. Ein Test hält das fest.
6. Für 027: Schema und Client sind neu erzeugt; 027 erzeugt beides nach dem Zusammenführen auf dem neuen `main` neu.
7. Für 032: `""` und `null` als IP-Adresse speichern beide „keine Adresse“; die Antwort enthält dann `null`.

Keine neue Abhängigkeit. `settings.py`, `tests/config/test_api.py`, `docs/DECISIONS.md` und `docs/STATUS.md` nicht geändert. Keine offenen Fragen an a7.
