# Auftrag 051 – Einlese-API: Status, Verlauf, erneut anstoßen

Meilenstein: M2 · Freigabestufe: C · Status: offen

## Ziel

Die API zeigt je Dokumentversion den Einlese-Status mit Fehlerart, listet alle Einlese-Aufträge mit Filtern und erlaubt Verwaltern, das Einlesen erneut anzustoßen. Benutzernamen sieht nur, wer auch das Änderungsprotokoll lesen darf (Frage 1). Grundlage für die Oberfläche (053, 055).

## Umfang

- Die Version im Datei-Endpunkt (`GET /api/v1/documents/{document_id}/`) bekommt ein Feld `ingest` mit dem neuesten Auftrag oder `null`: `id`, `status`, `step`, `error_code`, `error_detail` (nach Frage 2), `section_count`, `page_count`, `created_at`, `finished_at`. Gleiches Feld in der Dateiliste eines Geräts für die neueste Version. Nur ein zusätzlicher Abfragesatz, kein N+1; ein Test zählt die Abfragen.
- `POST /api/v1/document-versions/{version_id}/ingest/`: `CanManage`; 202 mit dem neuen Auftrag; 409, wenn schon ein Auftrag läuft; 400 für Dokumente der Art `configuration`. Nutzt `request_ingest` aus 049; `requested_by` ist der angemeldete Benutzer.
- `GET /api/v1/ingest-jobs/`: `CanRead`, 50 je Seite, neueste zuerst; Filter `status` (mehrfach), `device`, `document`, `version`. Jeder Eintrag trägt Dokument (Kennung, Titel), Version (Kennung, Nummer, Dateiname), Gerät (Kennung, Schlüssel, Name) und `requested_by` (Benutzername für `manage`, für `read` immer `null` – nach Frage 1).
- Neue Datei `backend/twox/ingest/urls.py`, eingebunden in `backend/twox/config/urls.py`. Views und Serializer in `backend/twox/ingest/api.py`.
- `backend/tests/config/expected_paths/ingest.py` und `__init__.py`; der Pfadtest aus 025 bleibt grün (anonym und ohne Rolle 403).
- OpenAPI-Schema (`web/openapi/schema.yml`) und Client (`web/src/api/generated/`) neu erzeugen und einchecken.
- Neue Meldungen (z. B. für 409) in `backend/locale/de/LC_MESSAGES/django.po` übersetzen.
- **Tests:** Rechte je Rolle; 202, 409 und 400; Filter und Seiten; `requested_by` je Rolle; `error_detail` je Rolle; Felder im Schema.

## Nicht-Ziele

- Keine Oberfläche (053, 055).
- Kein Abbrechen, kein Löschen von Aufträgen oder Abschnitten.
- Kein Herunterladen der Docling-Antwort.

## Betroffene Bereiche (Ordner, Dateien)

- neu: `backend/twox/ingest/api.py`, `backend/twox/ingest/urls.py`
- `backend/twox/config/urls.py`
- `backend/twox/files/serializers.py` (Feld `ingest`), gegebenenfalls `backend/twox/files/views.py` (Abfrage vorladen)
- neu: `backend/tests/config/expected_paths/ingest.py`; `backend/tests/config/expected_paths/__init__.py`
- neu: `backend/tests/ingest/test_api.py`; `backend/tests/files/test_api.py`
- `backend/locale/de/LC_MESSAGES/django.po`
- `web/openapi/schema.yml`, `web/src/api/generated/**`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-051`, `W` für `docker compose -p twox-051-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18051` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. `D --profile dev build migrate api worker backend-dev web-dev` und `D up -d --wait --wait-timeout 300 db valkey worker api` enden mit Exit-Code 0.
2. Tests:
   - `D run --rm backend-dev pytest tests/ingest tests/files tests/config -v` endet mit Exit-Code 0.
   - `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen.
   - `D run --rm backend-dev pytest -m worker` endet mit Exit-Code 0.
3. `D run --rm backend-dev ruff check .` meldet `All checks passed!`, `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0, `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
4. Weitere Prüfungen wie in `ci.yml`, jeweils ohne Unterschied zum eingecheckten Stand:
   - `D run --rm backend-dev python manage.py makemessages -l de --add-location=file`, danach `git diff --exit-code -I '^"POT-Creation-Date:' -- backend/locale`;
   - `D run --rm backend-dev python manage.py makemigrations --check --dry-run` endet mit Exit-Code 0;
   - `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0;
   - `D run --rm -v "$PWD/web/openapi:/out" backend-dev python manage.py spectacular --file /out/schema.yml` (unter Git Bash mit vorangestelltem `MSYS_NO_PATHCONV=1`), danach `git diff --exit-code -- web/openapi` ohne Unterschied zum eingecheckten neuen Stand.
5. Oberfläche wie im CI-Job `web`: `W --profile dev build web-dev` und `W run --rm web-dev npm ci`, danach `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build` und `npm run licenses`, je über `W run --rm web-dev …`, mit Exit-Code 0. `W run --rm web-dev npm run api:generate`, danach `git diff --exit-code -- web/openapi web/src/api` ohne Unterschied.
6. Browser-Test wie im CI-Job `e2e`: `D --profile e2e pull e2e`, `D --profile dev run --rm web-dev npm ci`; dann der Schritt „Create test account“ aus `ci.yml` wörtlich, nur mit `D` statt `docker compose` (Kennwort nur über den Variablennamen `TWOX_ACCOUNT_PASSWORD`); dann `D --profile e2e run --rm e2e`: alle Fälle bestanden, Exit-Code 0.
7. Abräumen: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: 049 ist nach `main` zusammengeführt. Fragen 1 und 2 sind entschieden.

- Welle 6. Einziger Auftrag seiner Zeit, der `urls.py`, Schema, Client, `django.po` und `expected_paths/__init__.py` ändert; 052 wartet auf ihn.
- **Keine neue Abhängigkeit.**
- Rechte wie bisher (E-40): Lesen dürfen beide Rollen, erneut anstoßen nur `manage`. Benutzernamen nur für `manage` wie beim Änderungsprotokoll (E-43, `/audit`).
- Stufe C, weil neue Endpunkte Rechte festlegen.
- Konflikte in `web/src/api/generated` und `schema.yml` beim Zusammenführen immer durch Neuerzeugen lösen, nie von Hand.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

1. **Wer sieht, wer ein Einlesen angestoßen hat (`requested_by`)?** (E-43: das Änderungsprotokoll lesen nur Verwalter.)
   - (a) nur `manage`; `read` bekommt `null`;
   - (b) alle Rollen, als ausdrückliche Abweichung von E-43.
   Empfehlung: (a). Gleiche Linie wie `/audit`; für die Arbeit mit Lesezugriff ist der Name nicht nötig.
2. **Darf die Rolle „Lesen“ den technischen Fehlertext (`error_detail`) sehen?**
   - (a) ja, alle Rollen sehen Fehlerart und Text;
   - (b) „Lesen“ sieht nur die übersetzte Fehlerart.
   Empfehlung: (a). Der Text ist nach 046 bereinigt (keine Pfade, Adressen, Dateinamen, Inhalte) und hilft bei der Meldung an den Verwalter.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
