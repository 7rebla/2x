# Auftrag 054 – Oberfläche: Suchseite

Meilenstein: M2 · Freigabestufe: B · Status: offen

## Ziel

Die Oberfläche bekommt eine Suchseite `/search`. Man gibt einen Begriff, eine Kennung oder eine Frage ein und grenzt optional auf ein Gerät ein. Die Treffer zeigen Fundorte (Dokument, Gerät, Anlage), Seite, Überschriftenpfad und Ausschnitt mit Hervorhebung und führen per Link zur Datei und zum Gerät.

## Umfang

- Seite `web/src/pages/SearchPage.tsx`, per `lazy()` geladen wie `/map`, damit das Hauptbündel unter 500 kB bleibt.
- Route in `web/src/routes.tsx`, Eintrag „Suche“ in `web/src/navigation.ts` (Rolle `read`), Texte in `web/src/locales/{de,en}/nav.json` und neuer Namensraum `search.json`.
- Formular: Suchfeld und Auswahl eines Geräts (aus `GET /api/v1/devices/`); Suchbegriff und Gerät in der Adresse (`?q=…&device=…`), sofern Frage 1 in 052 so entschieden ist; Abschicken mit Enter.
- Treffer: je Fundort Titel des Dokuments mit Link auf `/documents/:id`, Version, Gerät mit Link auf `/devices/:id`, Anlage; Kennzeichnung „ältere Version“, wenn `is_latest` falsch ist; Seite („S. 31“ bzw. „S. 31–32“, ohne Seite der Überschriftenpfad); Ausschnitt mit Hervorhebung aus `highlights` als React-Textknoten, nie `dangerouslySetInnerHTML`; Art des Treffers (exakt, Stichwort, Bedeutung).
- Hinweis bei `semantic: false`: „Nur Stichwortsuche – Sprachmodell nicht erreichbar“.
- Zustände: leer, lädt, keine Treffer, Fehler.
- `web/src/pages/README.md` um die Seite ergänzen.
- **Tests:**
  - Vitest: Hervorhebung, Seitenangabe, mehrere Fundorte, „ältere Version“, Links, Hinweis bei `semantic: false`, Parameter in der Adresse, Fehlerfall, Navigationseintrag für `reader` und `manager`.
  - Playwright `web/e2e/search.spec.ts` (als `e2e-manager`): Navigation zur Suche; ohne Sitzung führt die Seite zur Anmeldung; Suche ohne Treffer zeigt „keine Treffer“; Suche mit Antwort über `page.route` (selbst geschriebene Antwort) zeigt Seite, Gerät und Links; Konsole fehlerfrei.

## Nicht-Ziele

- Keine Einlese-Übersicht (055), keine Antworten mit Sprachmodell (M3).
- Kein PDF-Betrachter und kein Sprung auf eine Seite im PDF (Seitenvorschau gehört zur Quellenanzeige in M3).
- Keine Änderung an API und Client; keine Änderung an `web/src/test/fakeApi.ts` (053 läuft gleichzeitig).

## Betroffene Bereiche (Ordner, Dateien)

- neu: `web/src/pages/SearchPage.tsx`, `web/src/pages/SearchPage.test.tsx`, gegebenenfalls `web/src/pages/search/` (Teile, Testdaten)
- `web/src/routes.tsx`, `web/src/routes.test.tsx`, `web/src/navigation.ts`
- `web/src/locales/{de,en}/nav.json`; neu: `web/src/locales/{de,en}/search.json`; gegebenenfalls `web/src/i18n.ts` und `web/src/i18next.d.ts` (Namensraum)
- `web/src/pages/README.md`
- neu: `web/e2e/search.spec.ts`; `web/e2e/navigation.spec.ts`

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Wurzelverzeichnis des Arbeitsverzeichnisses, in der Form aus `.github/workflows/ci.yml` und `README.md`.

- `D` steht für `docker compose -p twox-054`, `W` für `docker compose -p twox-054-web -f deploy/compose/compose.web.yaml`.
- Vorher `.env.example` nach `.env` kopieren und darin `TWOX_API_PORT=18054` setzen.

0. `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst Status „wartet auf a7“ mit „Docker Desktop fehlt“.
1. Oberfläche wie im CI-Job `web`: `W --profile dev build web-dev` und `W run --rm web-dev npm ci`, danach `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build` und `npm run licenses`, je über `W run --rm web-dev …`, mit Exit-Code 0. Der Build zeigt die Suchseite als eigenen Teil; das Hauptbündel bleibt unter 500 kB; Größen im Kurzbericht.
2. `W run --rm web-dev npm run api:generate`, danach `git diff --exit-code -- web/openapi web/src/api` ohne Unterschied.
3. Browser-Test wie im CI-Job `e2e`: `D --profile dev build migrate api worker web-dev`, `D --profile e2e pull e2e`, `D --profile dev run --rm web-dev npm ci`, `D up -d --wait --wait-timeout 300 db valkey worker api`; dann der Schritt „Create test account“ aus `ci.yml` wörtlich, nur mit `D` statt `docker compose` (Kennwort nur über den Variablennamen `TWOX_ACCOUNT_PASSWORD`); dann `D --profile e2e run --rm e2e`: alle Fälle bestanden, darunter `search.spec.ts`, Exit-Code 0.
4. Lokal, mit eingelesener BetrSichV (wie 048, Kriterium 6): Die Suche nach einem Begriff aus dem Text zeigt den Treffer mit Seitenzahl; der Link führt zur Dateiseite.
5. Abräumen: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

Voraussetzung: 052 ist nach `main` zusammengeführt (Endpunkt im erzeugten Client).

- Welle 8, parallel zu 053, falls dieses noch läuft. Ändert `routes.tsx`, `navigation.ts` und `nav.json`; 055 wartet deshalb auf diesen Auftrag.
- **Keine neue Abhängigkeit.**
- Abfragen über die Query-Optionen des erzeugten Clients, wie auf den anderen Seiten.
- Antworten in `page.route` sind selbst geschrieben, ohne Texte aus Herstellerunterlagen.
- Die CI hat nur das Testkonto `e2e-manager`; die Rolle `read` deshalb in Vitest.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
