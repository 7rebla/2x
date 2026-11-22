# Auftrag 055 – Oberfläche: Einlese-Übersicht

Meilenstein: M2 · Freigabestufe: B · Status: offen

## Ziel

Eine Seite `/ingest` zeigt alle Einlese-Aufträge über alle Geräte; gescheiterte und laufende stehen vorne. Man sieht auf einen Blick, welche Handbücher eingelesen sind und wo es hakt. Verwalter können von dort erneut anstoßen.

## Umfang

- Seite `web/src/pages/IngestPage.tsx`, per `lazy()` geladen.
- Route in `routes.tsx`, Eintrag „Einlesen“ in `navigation.ts` (Rolle `read`), Texte in `nav.json` und neuer Namensraum `ingest.json` (de, en).
- Tabelle aus `GET /api/v1/ingest-jobs/`: Gerät, Datei (Link auf die Dateiseite), Version, Dateiname, Status mit Schritt, Fehlermeldung (übersetzte Fehlerart, technischer Text aufklappbar), Seiten und Abschnitte, Zeitpunkte; Spalte „angestoßen von“ nur, wenn die API einen Namen liefert (nach Frage 1 in 051 nur für `manage`).
- Filter nach Status (Vorgabe: Fehler, läuft, in Warteschlange) und Gerät, in der Adresse; „Alle“ zeigt auch fertige und übersprungene.
- Seiten mit 50 Einträgen wie `/audit`.
- Schaltfläche „Erneut einlesen“ je Zeile für `manage`, wie in 053.
- Solange Aufträge laufen, fragt die Seite alle 5 Sekunden neu ab.
- Statusabzeichen und Fehlermeldung aus `web/src/components/files/IngestStatus.tsx` (053) wiederverwenden, nicht kopieren.
- `web/src/pages/README.md` ergänzen.
- **Tests:**
  - Vitest: Filter, Seiten, Zustände, Schaltfläche und Spalte „angestoßen von“ je Rolle.
  - Playwright `web/e2e/ingest.spec.ts` (als `e2e-manager`): Eine im Test erzeugte `.txt`-Datei hochladen; sie erscheint unter „Alle“ als „Übersprungen“ mit Gerät und Link zur Datei; der Navigationseintrag ist sichtbar.

## Nicht-Ziele

- Kein Abbrechen und kein Löschen von Aufträgen.
- Keine Änderung an API, Client und Suchseite.

## Betroffene Bereiche (Ordner, Dateien)

- neu: `web/src/pages/IngestPage.tsx`, `web/src/pages/IngestPage.test.tsx`
- `web/src/routes.tsx`, `web/src/routes.test.tsx`, `web/src/navigation.ts`
- `web/src/locales/{de,en}/nav.json`; neu: `web/src/locales/{de,en}/ingest.json`; gegebenenfalls `web/src/i18n.ts`, `web/src/i18next.d.ts`
- `web/src/pages/README.md`
- neu: `web/e2e/ingest.spec.ts`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-055`, `W` für `docker compose -p twox-055-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18055` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. Oberfläche wie im CI-Job `web`: `W --profile dev build web-dev` und `W run --rm web-dev npm ci`, danach `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build` und `npm run licenses`, je über `W run --rm web-dev …`, mit Exit-Code 0. Das Hauptbündel bleibt unter 500 kB.
2. `W run --rm web-dev npm run api:generate`, danach `git diff --exit-code -- web/openapi web/src/api` ohne Unterschied.
3. Browser-Test wie im CI-Job `e2e`: `D --profile dev build migrate api worker web-dev`, `D --profile e2e pull e2e`, `D --profile dev run --rm web-dev npm ci`, `D up -d --wait --wait-timeout 300 db valkey worker api`; dann der Schritt „Create test account“ aus `ci.yml` wörtlich, nur mit `D` statt `docker compose` (Kennwort nur über den Variablennamen `TWOX_ACCOUNT_PASSWORD`); dann `D --profile e2e run --rm e2e`: alle Fälle bestanden, darunter `ingest.spec.ts`, Exit-Code 0.
4. Ein zweiter Lauf von Kriterium 3 ohne `down -v` bleibt grün.
5. Lokal: Bei gestopptem Docling (`D stop docling`) zeigt eine hochgeladene PDF-Datei nach den Wiederholungen in der Übersicht „Fehler“ mit der Meldung zu `docling_unavailable`. Nach `D start docling` und „Erneut einlesen“ zeigt sie „Eingelesen“.
6. Abräumen: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: 051, 053 und 054 sind nach `main` zusammengeführt (053 wegen der Bausteine, 054 wegen `routes.tsx`, `navigation.ts` und `nav.json`).

- Welle 9.
- **Keine neue Abhängigkeit.**
- `error_detail` nur als Text darstellen.
- Die CI hat nur das Testkonto `e2e-manager`; die Rolle `read` deshalb in Vitest.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
