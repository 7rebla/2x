# Auftrag 026 – API und Admin für Standorte, Bereiche, Anlagen, Geräte

Meilenstein: M1 · Freigabestufe: C · Status: offen

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

1. **Löschen von Standorten, Bereichen, Anlagen und Geräten in M1?** („Daten löschen“ ist Stufe C.)
   - (a) Kein Löschen über API und Oberfläche; Superuser können im Admin löschen, soweit `PROTECT` es erlaubt.
   - (b) „Verwalten“ darf leere Objekte (ohne Kinder, ohne Dateien) über die API löschen.
   - Empfehlung: (a). Die Startunterlage verlangt „anlegen, bearbeiten“; Löschen mit Protokoll und Rückfrage kann ein eigener Auftrag werden.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
