# Auftrag 016 – Backend-Grundlage für M1: Sitzungen, Admin, CSRF, Sprachen, Zwischenspeicher, URL-Aufteilung

Meilenstein: M1 · Freigabestufe: C · Status: offen

## Ziel

Das Django-Projekt bekommt alles, was Anmeldung, Admin, Upload und zwei Sprachen voraussetzen. Danach müssen die folgenden M1-Aufträge `settings.py` und `config/urls.py` nur noch selten anfassen. Enthalten sind die Vormerkungen aus Auftrag 005 (Sitzungen, Admin, Auth-Middleware, Kennwort-Prüfer, Authentifizierung bewusst setzen) und aus Auftrag 013 (`AppDirectoriesFinder` für den Admin).

## Umfang

- `INSTALLED_APPS`: `django.contrib.sessions`, `django.contrib.messages` und der Admin ergänzen. Der Admin kommt nach Frage 3 als eigene Admin-Seite in `backend/twox/config/admin_site.py` (eigene `AdminConfig` mit `default_site`). `has_permission` lässt nur aktive Benutzer mit `is_superuser` zu; `is_staff` allein reicht nicht. Den Kommentar „arrive with milestone M1“ anpassen.
- `MIDDLEWARE` in der Reihenfolge aus der Django-Doku: Security, WhiteNoise, Session, Locale, Common, Csrf, Authentication, Messages, XFrameOptions.
- `TEMPLATES` mit DjangoTemplates, `APP_DIRS=True` und den Kontextprozessoren `request`, `auth` und `messages`. Der Admin und später allauth brauchen das.
- `AUTH_PASSWORD_VALIDATORS` mit den vier Standard-Prüfern von Django. Die Mindestlänge richtet sich nach Frage 5.
- Sitzung und Cookies:
  - `SESSION_COOKIE_AGE` nach Frage 4.
  - `SESSION_COOKIE_SAMESITE` und `CSRF_COOKIE_SAMESITE` ausdrücklich auf `\"Lax\"`, `SESSION_COOKIE_HTTPONLY` auf `True` (beides entspricht dem Django-Standard, wird aber sichtbar gesetzt und getestet).
  - `Secure`-Cookies, `CSRF_TRUSTED_ORIGINS`, HSTS und CSP kommen nicht hierher, sondern in M6 (Vormerkung der Leitstelle).
- Zwischenspeicher:
  - `CACHES[\"default\"]` ist `django.core.cache.backends.redis.RedisCache`. Die Adresse kommt aus der neuen Variable `TWOX_CACHE_URL`, Standard `redis://valkey:6379/2`.
  - Grundlage ist Startunterlage 5.2 („Broker und Zwischenspeicher: Valkey“). Der Client redis-py steht schon im Lock.
  - Der Zwischenspeicher ist für alle API-Prozesse gemeinsam. Er trägt die Ratenbegrenzung der Anmeldung (Auftrag 020).
  - `TWOX_CACHE_URL` kommt in den gemeinsamen Umgebungsblock von `deploy/compose/compose.yaml` und mit Kommentar in `.env.example`.
  - Neu `backend/tests/conftest.py`: stellt für alle Tests auf `LocMemCache` um, damit `pytest` weiter ohne Valkey läuft.
- Statische Dateien:
  - Neu `backend/twox/config/staticfinders.py`: eine Ableitung von `AppDirectoriesFinder`, die nur `django.contrib.admin` durchsucht. Sie kommt zusätzlich zum `FileSystemFinder` in `STATICFILES_FINDERS`.
  - Die Dateien der DRF-Oberfläche bleiben draußen.
  - Die Lizenzdateien der Fremdbibliotheken des Admins (`admin/js/vendor/jquery`, `select2`, `xregexp`) werden mitgesammelt und ausgeliefert.
- DRF:
  - `DEFAULT_AUTHENTICATION_CLASSES` = `rest_framework.authentication.SessionAuthentication` (Frage 1).
  - `DEFAULT_PERMISSION_CLASSES` bleibt `IsAuthenticated`; Auftrag 025 ändert das.
  - Renderer und Parser bleiben JSON.
- Sprachen: `LANGUAGES` = Deutsch und Englisch, `LocaleMiddleware`, `LOCALE_PATHS = [BASE_DIR / \"locale\"]`. `LANGUAGE_CODE` bleibt `en`. Kataloge folgen in Auftrag 034.
- Dateien (nur Einstellungen):
  - `TWOX_MEDIA_ROOT` als `Path`, Standard `/data/media`.
  - `TWOX_UPLOAD_MAX_BYTES` als ganze Zahl, Standard nach der Antwort zu Auftrag 029, Frage 1.
  - Beide werden aus der Umgebung gelesen, mit Prüfung auf gültige Werte.
  - Kein `MEDIA_URL`: Dateien verlassen den Server nur über die API.
  - Volume, Compose-Einträge und `.env.example` für diese beiden Variablen folgen in Auftrag 022.
- `config/urls.py`:
  - `admin/` für die Admin-Seite aus `admin_site.py`.
  - `api/v1/` bindet je App ein eigenes `urls.py` ein: `twox.accounts.urls`, `twox.assets.urls`, `twox.files.urls`. Die drei Dateien entstehen hier mit leerer, typisierter `urlpatterns`-Liste.
  - Kein `importers/urls.py`: Der CSV-Import der Geräteliste gehört nach Startunterlage 6 zu `assets`; `importers` bleibt den Einlese-Modulen vorbehalten.
  - Oberfläche nach Frage 2: `web_index` liefert `index.html` für `/` und für alle Pfade außer denen, die mit `api`, `static`, `admin`, `_allauth` oder `accounts` beginnen, jeweils gefolgt von `/` oder dem Ende des Pfads. Nur GET und HEAD.
  - Die Ansicht der Oberfläche setzt das CSRF-Cookie (`ensure_csrf_cookie`).
- Erwartete Schema-Pfade je App aufteilen:
  - Neu `backend/tests/config/expected_paths/` mit `__init__.py`, `config.py`, `accounts.py`, `assets.py` und `files.py`, je mit einer Liste `EXPECTED_PATHS: list[str]`.
  - `test_schema_lists_exactly_the_known_paths` vergleicht mit der Vereinigung dieser Listen.
  - Spätere Aufträge ändern nur die Datei ihrer App.
- Tests unter `backend/tests/config/`:
  - `test_settings.py`: Apps, Reihenfolge der Middleware, Sprachen, Zwischenspeicher-Einstellung, Medien-Einstellungen (Standard und ungültiger Wert), Prüfer, Sitzungsdauer, SameSite.
  - `test_webui.py`: `test_unknown_paths_are_404_not_the_ui` wird ersetzt.
    - Mit gebauter Oberfläche liefern `/devices/1`, `/selftest` und `/apix/` `index.html`.
    - `/api`, `/api/`, `/api/v1/unknown`, `/static`, `/static/missing.js`, `/_allauth/x` und `/accounts/x` liefern kein `index.html`.
    - `/admin` leitet auf `/admin/` um.
    - `/` setzt `csrftoken`. Ein POST auf einen Oberflächen-Pfad ergibt 405.
  - Neu `test_admin.py`:
    - Anonym leitet `/admin/` auf `/admin/login/` um.
    - Ein Superuser bekommt 200.
    - Ein Benutzer mit `is_staff` ohne `is_superuser` und ein normaler aktiver Benutzer bekommen keinen Zugang.
  - `test_api.py`:
    - Das 403 für anonyme Aufrufe bleibt.
    - Eine angemeldete Sitzung (`force_login`) bekommt bei der Test-Ansicht `ProbeView` 200.
    - Mit `APIClient(enforce_csrf_checks=True)` wird ein POST ohne `X-CSRFToken` mit 403 abgewiesen, mit Token angenommen.
    - Liste der Schema-Pfade wie oben aufgeteilt.

## Nicht-Ziele

- django-allauth und Ratenbegrenzung der Anmeldung (020). Rollen (021). Standard-Rechteklasse (025).
- Volume und Speicher-Schnittstelle für Dateien (022).
- Übersetzungskataloge und gettext (034).
- Der Selbsttest bleibt bis Auftrag 027 offen (`AllowAny`).
- Anmeldung am Admin über die Anmeldeseite der Oberfläche (030); bis dahin gilt das Anmeldeformular des Admins.
- `Secure`-Cookies, HSTS, CSP, `CSRF_TRUSTED_ORIGINS` (M6).
- Neue Abhängigkeiten.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/config/settings.py`, `backend/twox/config/urls.py`, `backend/twox/config/webui.py`
- neu: `backend/twox/config/staticfinders.py`, `backend/twox/config/admin_site.py`
- neu: `backend/twox/accounts/urls.py`, `backend/twox/assets/urls.py`, `backend/twox/files/urls.py`
- `deploy/compose/compose.yaml` (nur `TWOX_CACHE_URL` im gemeinsamen Umgebungsblock), `.env.example` (nur `TWOX_CACHE_URL`)
- neu: `backend/tests/conftest.py`, `backend/tests/config/test_admin.py`, `backend/tests/config/expected_paths/`
- `backend/tests/config/test_settings.py`, `test_webui.py`, `test_api.py`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-016`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18016` setzen.
- Unter Git Bash vor Befehlen mit `/out/…` `MSYS_NO_PATHCONV=1` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren, sondern Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0. `D logs migrate` zeigt die Migrationen von `sessions` und `admin` als angewendet.
2. `D exec api python -c \"import urllib.request as u; print(u.urlopen('http://localhost:8000/static/admin/css/base.css').status)\"` gibt `200` aus.
3. `D exec api python -c \"import urllib.request as u; r=u.urlopen('http://localhost:8000/admin/'); print(r.url)\"` gibt eine Adresse mit `/admin/login/` aus.
4. Im Image liegt nichts unter `staticfiles/rest_framework/`: `D exec api sh -c \"test ! -e staticfiles/rest_framework\"` endet mit Exit-Code 0.
5. `D exec api sh -c \"ls staticfiles/admin/js/vendor/*/LICENSE*\"` listet je eine Lizenzdatei für `jquery`, `select2` und `xregexp`.
6. `D exec api python manage.py shell -c \"from django.core.cache import cache; cache.set('probe', 1, 5); print(cache.get('probe'))\"` gibt `1` aus (Zwischenspeicher in Valkey).
7. Prüfungen und Typen:
   - `D run --rm backend-dev ruff check .` meldet `All checks passed!`.
   - `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0.
   - `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
8. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen. `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
9. `D run --rm backend-dev python manage.py makemigrations --check --dry-run` meldet `No changes detected`.
10. `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0.
11. `D run --rm -v \"$PWD/web/openapi:/out\" backend-dev python manage.py spectacular --file /out/schema.yml` endet ohne Warnungen. Danach zeigt `git diff --exit-code -- web/openapi` keinen Unterschied.
12. Der Browser-Test bleibt grün:
    - `D --profile dev build migrate api worker web-dev`
    - `D --profile e2e pull e2e`
    - `D --profile dev run --rm web-dev npm ci`
    - `D up -d --wait --wait-timeout 300 db valkey worker api`
    - `D --profile e2e run --rm e2e` meldet `1 passed`.
13. Abräumen: `D --profile dev --profile e2e down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: M1-Liste von a7 freigegeben (`docs/STATUS.md`, „Freigegeben“); Antworten von a7 auf die Fragen 1 bis 5 dieses Auftrags und auf Auftrag 029, Frage 1 (Standardwert der Obergrenze).

- Welle 1. Gleichzeitig laufen 017 (`taskqueue.py`), 018 (Oberfläche, `backend/Dockerfile`) und 019 (`assets`-Modelle).
- In dieser Welle ändert nur dieser Auftrag `settings.py`, `config/urls.py`, `compose.yaml` und `.env.example`.
- `twox/assets/models.py`, Migrationen und `backend/Dockerfile` nicht anfassen.
- **Keine neue Abhängigkeit.** Der Valkey-Zwischenspeicher nutzt Djangos eingebautes `RedisCache` mit dem vorhandenen redis-py.
- Stufe C wegen Anmeldung (Authentifizierungsart, Sitzungsdauer, Kennwortregeln), Rechte (Admin nur für Superuser) und Architektur (Auslieferung der Oberfläche für alle Pfade).
- Vormerkungen:
  - Auftrag 005, Kurzbericht: „Authentifizierung ist ausdrücklich leer“; keine Sitzungen, kein Admin, keine Prüfer.
  - Auftrag 013 und der Kommentar zu `STATICFILES_FINDERS`: `AppDirectoriesFinder` für den Admin.
- Die Fremdbibliotheken des Admins kommen mit Django. Im Kurzbericht Name, Version und Lizenz von jQuery, Select2 und XRegExp nennen, abgelesen an den mitgelieferten Lizenzdateien. Den Eintrag in `docs/DECISIONS.md` macht die Leitstelle.
- `docs/ARCHITECTURE.md` sagt heute „Only / maps to the UI“. Die Doku zieht Auftrag 038 nach.
- Sprache: Code und Kommentare Englisch; jede Funktion hat Typangaben.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.
- Fehlt eine Antwort von a7: nicht raten, Status „wartet auf a7“.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 21.11.2026:** Alle Empfehlungen übernommen (E-37). Jede Frage unten ist nach ihrer Empfehlung entschieden.

1. **Wie authentifiziert sich die Oberfläche bei der API?**
   - (a) Django-Sitzung mit Cookie und CSRF-Schutz am selben Ursprung (DRF `SessionAuthentication`).
   - (b) Token im Browser (JWT oder `X-Session-Token`).
   - Empfehlung: (a). Die Oberfläche kommt von Django am selben Ursprung (Startunterlage 5.2). Es liegt kein Token im Browser, und Abmelden macht die Sitzung sofort ungültig. Tokens erst für Nicht-Browser-Clients (MCP, M10).
2. **Seiten der Oberfläche direkt aufrufbar machen?**
   - (a) Django liefert `index.html` für alle Pfade außer `api`, `static`, `admin`, `_allauth` und `accounts`.
   - (b) Hash-Routing (`/#/devices`); Django bleibt bei genau `/`.
   - Empfehlung: (a). Lesbare, teilbare Adressen; API und statische Dateien behalten ihr 404.
3. **Django-Admin in M1?**
   - (a) Unter `/admin/`, nur für Superuser (`is_superuser`, nicht schon `is_staff`), als Werkzeug für Benutzer und Notfälle. Ab Auftrag 030 meldet man sich am Admin über die Anmeldeseite der Oberfläche an, mit derselben Ratenbegrenzung.
   - (b) Für `is_staff`-Benutzer mit Modellrechten.
   - (c) Kein Admin.
   - Empfehlung: (a). Benutzerverwaltung ohne eigenen Code und kein zweiter, ungeschützter Anmeldeweg.
4. **Wie lange bleibt eine Sitzung gültig?**
   - (a) 8 Stunden ab Anmeldung.
   - (b) 12 Stunden.
   - (c) Django-Standard, 2 Wochen.
   - Empfehlung: (a), etwa eine Arbeitsschicht. Der Wert ist ein Vorschlag der Leitstelle; die Startunterlage nennt keinen.
5. **Mindestlänge für Kennwörter?**
   - (a) 12 Zeichen.
   - (b) 8 Zeichen (Django-Standard).
   - Empfehlung: (a), weil es in M1 noch keine Zwei-Faktor-Anmeldung gibt. Ebenfalls ein Vorschlag der Leitstelle.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
