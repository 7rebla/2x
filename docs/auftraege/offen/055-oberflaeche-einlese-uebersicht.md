# Auftrag 055 – Oberfläche: Einlese-Übersicht

Meilenstein: M2 · Freigabestufe: B · Status: zur Prüfung

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

- **Nachtrag der Leitstelle (aus 071):** `navigation.ts` verlangt je Eintrag ein Pflichtfeld `icon` (Name aus `web/src/icons/names.ts`, jeder Eintrag ein eigenes Icon, `Layout.test.tsx` prüft das). Neue Icon-Namen in `names.ts` ergänzen (gehört zu diesem Auftrag) und `web/e2e/navigation.spec.ts` anpassen (Liste der Einträge; Kopfzeile bleibt bei 1024 px einzeilig in Deutsch und Englisch).

- **Nachtrag der Leitstelle (E-59, KI optional):** Einbettungen, Vektorsuche und alles, was ein Modell braucht, sind eine aktivierbare Zusatzfunktion. Schalter `TWOX_AI_ENABLED` (Einstellung in `settings.py`, Standard `False`; `.env.example` mit Kommentar). Bei „aus“: kein Aufruf von Ollama, keine Einbettungs-Aufgaben, Einlesen endet nach den Abschnitten erfolgreich, die Suche arbeitet nur mit der Stichwortsuche, Selbsttest und Oberfläche zeigen „KI nicht aktiviert“ als neutralen Zustand (kein Fehler, kein Warnsymbol). Jede KI-abhängige Stelle braucht einen Test für beide Zustände; die CI läuft mit „aus“ und mit „an“ plus Attrappe.

Voraussetzung: 051, 053 und 054 sind nach `main` zusammengeführt (053 wegen der Bausteine, 054 wegen `routes.tsx`, `navigation.ts` und `nav.json`).

- Welle 9.
- **Keine neue Abhängigkeit.**
- `error_detail` nur als Text darstellen.
- Die CI hat nur das Testkonto `e2e-manager`; die Rolle `read` deshalb in Vitest.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

- **Nachtrag der Leitstelle (Prüfung 054):** Mit sechs Navigationseinträgen bleiben bei 1024 px nur 11 px Reserve in der Kopfzeile (054 hat Abstände in `Layout.tsx` und `index.css` schon verkleinert). Für den siebten Eintrag eine tragfähige Lösung bauen, z. B. Texte der Einträge erst ab `xl` zeigen und darunter nur Icons mit `aria-label` und Tooltip, oder ein Menü „Mehr“; die Kopfzeile bleibt in Deutsch und Englisch einzeilig (`web/e2e/navigation.spec.ts` bei 1024 und 1280 px). `Layout.tsx` und `index.css` gehören dafür zu den betroffenen Bereichen.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Läufe am 22.11.2026 im Container, Projekte `twox-055` und `twox-055-web`, Port 18055, Docker Engine 29.9.3, Compose v5.7.0. Kriterien 0 bis 6 erfüllt, alle Nachträge umgesetzt. Keine neue Abhängigkeit, keine Änderung an API, erzeugtem Client, Suchseite oder `test/fakeApi.ts`.

### Was wurde gebaut?

- **Seite `web/src/pages/IngestPage.tsx`** unter `/ingest` (Rolle `read`), in `routes.tsx` per `lazy()` geladen.
  - Tabelle aus `GET /api/v1/ingest-jobs/` (`ingestJobsListOptions`), neueste zuerst, 50 je Seite mit „Vorherige/Nächste Seite“, „Seite x von y“ und Gesamtzahl wie `/audit`. Spalten: Gerät (Link auf die Geräteseite, Schlüssel darunter), Datei (Link auf die Dateiseite, darunter „Version n · Dateiname“), Status (Abzeichen mit Schritt und bei „Eingelesen“ Seiten und Abschnitte, darunter die übersetzte Fehlermeldung mit „Technische Angaben“ zum Aufklappen, darunter die Schaltfläche), Zeitpunkte (Angelegt, Beendet / „noch nicht“), „Angestoßen von“ (nur `manage`, `null` als „System“).
  - Filter Status und Gerät als Auswahlfelder, wirken sofort und stehen in der Adresse (`/ingest?status=…&device=…`, Zurück funktioniert). Status: „Offen (Fehler, läuft, wartet)“ = Vorgabe ohne Parameter (API-Anfrage `status=failed&status=running&status=queued`), einzelne Zustände, „Alle“ (`status=all`, ohne Statusfilter an die API). Unbekannter Status → Vorgabe, Gerätewert ohne gültige ID → alle Geräte, unbekanntes Gerät → „Gerät Nr. …“. Neuer Filter beginnt auf Seite 1.
  - Leere Liste: ohne Filter „Nichts offen: …“, sonst „Kein Einlese-Auftrag passt zu diesem Filter.“; Laden, Fehler (`ErrorMessage`; ein gescheitertes Nachladen lässt die Liste stehen).
  - Abfrage alle 5 s nur, solange ein angezeigter Auftrag `queued` oder `running` ist; dann steht ein ruhiger Hinweis über der Tabelle.
  - Bausteine aus 053 wiederverwendet: `IngestStatusBadge`, `IngestError`, `IngestRetryButton`, `isIngestActive`, `INGEST_POLL_INTERVAL_MS`. „Erneut einlesen“ für `manage` auf jeder Zeile ohne aktiven Auftrag. Steht ein neuerer Auftrag derselben Version auf derselben Seite, zeigt die ältere Zeile „Älterer Versuch: Ein neuerer Auftrag dieser Version steht weiter oben.“ und keine Schaltfläche (je Einlese-Versuch eine Zeile, E-55).
  - `error_detail`, Titel, Datei- und Gerätenamen nur als Text, nichts durch die Interpolation von i18next.
- **Navigation:** Eintrag „Einlesen“/„Ingestion“ hinter „Suche“, Rolle `read`, eigenes Icon `ingest` (Lucide `ScanText`, NAV-07) in `icons/names.ts` und `icons/README.md`. Texte in `nav.json`, neuer Namensraum `ingest.json` (de, en), eingetragen in `i18n.ts` und `i18next.d.ts`.
- **Kopfzeile (Nachtrag aus der Prüfung von 054):** Texte der Einträge erst ab 1280 px (`xl`), darunter nur Icons mit Text als zugänglichem Namen (`sr-only`) und Tooltip (`title`). Ab `xl` ist der Kopf breiter als der Seiteninhalt (`xl:max-w-7xl` statt `max-w-5xl`), sonst passten die sieben Texte nicht (der Inhalt ist auch bei 1280 px nur 1024 px breit). Gemessene Reserve rechts in der Navigation (Benutzer `e2e-manager`): 1280 px Englisch 260 px, Deutsch 160 px; 1024 px (nur Icons) 489 px in beiden Sprachen. Damit ist auch für einen achten Eintrag Platz. `index.css` blieb unverändert.
- **Doku:** `web/src/pages/README.md` (Adressentabelle, Rahmen und Navigation, Abschnitt „Ingest overview“).

### Wie wurde getestet?

`D` = `docker compose -p twox-055`, `W` = `docker compose -p twox-055-web -f deploy/compose/compose.web.yaml`; `.env` aus `.env.example` (ohne BOM) mit `TWOX_API_PORT=18055`, KI an, aber `TWOX_LLM_BASE_URL=http://127.0.0.1:9/v1` (dort antwortet nichts – kein Test erreicht das Ollama am Host, wie bei 054). Vor jedem Build `web/dist` und `web/playwright-report` gelöscht. Die Umgebungen „2x“ und „twox-leit“ wurden nicht berührt.

| Nr. | Ergebnis | Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version` (Engine 29.9.3) Exit 0, `docker compose version` v5.7.0 Exit 0 |
| 1 | erfüllt | `build web-dev`, `npm ci` („added 446 packages“), `lint`, `typecheck`, `test` (37 Dateien, 711 Tests), `build`, `licenses` („License check passed.“) je Exit 0, auf dem Endstand wiederholt. Keine Vite-Warnung; Hauptbündel `index-….js` 348,46 kB |
| 2 | erfüllt | `npm run api:generate` Exit 0; `git diff --exit-code -- web/openapi web/src/api` Exit 0, `git status --porcelain` dazu leer |
| 3 | erfüllt | `build migrate api worker web-dev`, `pull e2e`, `npm ci`, `up -d --wait …` je Exit 0; „Create test account“ wörtlich mit `D`: „Created account 'e2e-manager' …“. Erster Lauf: **52 passed**. Nach der letzten Code-Änderung zusätzlich frisch (nach `down -v`): „Created account …“, **53 passed**, Exit 0, darunter die vier Fälle aus `ingest.spec.ts` und die geänderten aus `navigation.spec.ts` |
| 4 | erfüllt | ohne `down -v`: „Updated account …“, **52 passed**; auf dem Endstand zweimal hintereinander „Updated account …“, je **53 passed**, Exit 0 |
| 5 | erfüllt (mit Abweichung 3) | siehe unten |
| 6 | erfüllt | `D --profile dev --profile e2e down -v` und `W --profile dev down -v` je Exit 0; danach kein Container, Volume oder Netz mit `twox-055` |

**Vitest neu `pages/IngestPage.test.tsx` (26 Fälle):** Adresse lesen/schreiben, Statusliste je Auswahl; Vorgabe-Filter (Anfrage mit drei Zuständen, Reihenfolge); Auswahl englisch und deutsch; „Alle“ ohne Statusfilter mit „Eingelesen · 60 pages, 140 sections“ und „Skipped“; Statuswahl schreibt `?status=skipped`, Zurück stellt wieder her; Geräteliste nach Anlage und Gerätefilter; ungültige Werte und unbekanntes Gerät; Tabelle mit Gerät, Links, Version, Dateiname, Status mit Schritt, Meldung, Technische Angaben, Zeitpunkte; Klick auf die Datei; `<img onerror>`, `<script>`, `<b>`, `<i>` nur als Text; deutsch (Spalten, Zustände, „noch nicht“, „System“, Seiten); Laden, „Nichts offen“, „kein Treffer für Filter“, Fehler 500; Seiten (120 Aufträge: 1 von 3, weiter, zurück, letzte Seite) und Neustart auf Seite 1 bei neuem Filter; Rollen: `reader` ohne Schaltfläche und ohne Spalte, `manager` mit Spalte und Schaltfläche nur ohne aktiven Auftrag; Erneut einlesen → POST, neue Zeile oben, ältere Zeile markiert und ohne Schaltfläche; Abfrage mit künstlicher Uhr alle 5 s bei aktivem Auftrag, Ende danach, keine Abfrage ohne aktiven Auftrag; Navigationseintrag für `reader` und `manager` mit Icon `ingest`. Angepasst: `routes.test.tsx` (Liste deutsch, Fall `/ingest`), `session.test.tsx` (Listen je Rolle, `requiredRole("/ingest")`), `i18n.test.ts` (12 Namensräume), `components/Layout.test.tsx` (`max-xl:sr-only`); `icons.test.tsx` (alle Zeichnungen verschieden) besteht unverändert.

**Playwright neu `web/e2e/ingest.spec.ts`** (als `e2e-manager`): Navigationseintrag sichtbar mit Icon, Klick → `/ingest`, Anfrage mit `failed, running, queued`; bei 375 px keine seitliche Seitenverschiebung, Filter passen; im Test erzeugte `.txt` über das Formular hochgeladen → mit Gerätefilter in „Offen“ leer, unter „Alle“ eine Zeile „Skipped“ mit Meldung, Gerätename und -schlüssel, „Version 1 · e2e-file-….txt“, „Angestoßen von“ = Testkonto, Link öffnet die Dateiseite, Zurück stellt die Ansicht her; „Ingest version 1 again“ schickt den echten POST (202), neue Zeile oben wird „Skipped“, ältere zeigt den Hinweis und keine Schaltfläche. Kein Test wartet auf Docling oder Ollama. **Angepasst `web/e2e/navigation.spec.ts`:** Listen mit sieben Einträgen (en, de, auch `title`); bei 1280 px alle Texte sichtbar, bei 1024 px nur Icons (Textbreite ≤ 1 px), beide Sprachen einzeilig, kein Überlauf, gleiche Höhe; neuer Fall: bei 1024 px öffnet das Icon „Ingestion“ die Seite.

**Kriterium 5 (lokal):** Mit einer vorübergehenden, nicht eingecheckten Playwright-Datei. Worker und API mit `TWOX_AI_ENABLED=false` neu erzeugt (siehe Abweichung 3), `D up -d docling`, dann `D stop docling`. Eine im Test geschriebene einseitige PDF (eigener Testtext) über das Formular hochgeladen; die Übersicht (deutsch, Gerätefilter) zeigte erst den laufenden Auftrag und fragte alle 5 s neu ab, nach 3,7 min „Fehler“ mit „Der Umwandlungsdienst (Docling) war nicht erreichbar. Bitte später erneut versuchen.“ und Technische Angaben „the host name of docling-serve does not resolve (gave up after 5 retries)“. Dann `D start docling` (gesund), „Version 1 erneut einlesen“ geklickt: neue Zeile oben, nach rund 15 s ohne Neuladen „Eingelesen · 1 Seite, 1 Abschnitt“; die ältere Zeile „Fehler“ mit „Älterer Versuch …“. Bildschirmfotos angesehen; dabei bei 375 px eine zu breite Statusauswahl gefunden und behoben (Commit „Keep the ingest filters within a phone screen …“, mit e2e-Fall).

**Bündelgröße** (`npm run build`, vorher `web/dist` und `web/playwright-report` gelöscht; Vergleich mit den Zahlen aus dem Kurzbericht 054, nicht selbst auf `main` gemessen):

| Teil | 054 | 055 |
| --- | --- | --- |
| `index-….js` | 345,75 kB (gzip 102,00) | 348,46 kB (gzip 102,69) |
| `react-query.gen-….js` (beim Start geladen) | 218,44 kB (gzip 70,28) | 219,12 kB (gzip 70,38) |
| `rolldown-runtime-….js` | 0,59 kB | 0,59 kB |
| **beim Start geladenes JS zusammen** | **564,78 kB (gzip 172,64)** | **568,17 kB (gzip 173,43)** |
| `IngestPage-….js` (nur bei `/ingest`) | – | 8,40 kB (gzip 2,74) |
| `index-….css` | 29,00 kB | 29,23 kB (gzip 6,82) |

Zuwachs durch 055 beim Start: **+3,39 kB JS (gzip +0,79 kB)** (Navigation, Texte beider Sprachen, Route) und +0,23 kB CSS; dazu 8,40 kB, die erst beim Öffnen von `/ingest` geladen werden. Die Startlast bleibt Thema von 062.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a52a2ec4cb9b8e136`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a52a2ec4cb9b8e136` (relativ zum Projektordner)
- Commits: `Let the ingest retry button take any version with id, number and newest job`, `Add the ingest overview /ingest with filters, pages, polling and retry`, `Show navigation texts from 1280 px in a wider header, icons below`, `Add a browser test for the ingest overview`, `Keep the ingest filters within a phone screen and shorten the open label`, dazu dieser Kurzbericht. Nicht gepusht, nichts zusammengeführt.

### Abweichungen und Hinweise

1. **`web/src/components/files/IngestStatus.tsx` geändert (außerhalb der Liste):** nur der Typ der Schaltfläche. `IngestRetryButton` verlangte eine vollständige `DocumentVersion`; jetzt genügt `IngestRetryTarget` = `id`, `number`, `ingest` (eine Zeile der Auftragsliste liefert genau das). Verhalten unverändert, die Tests von 053 bestehen. Ohne diese Änderung hätte ich die Schaltfläche kopieren oder eine Version mit erfundenen Feldern bauen müssen.
2. **Kopfzeile breiter als der Inhalt ab 1280 px:** Der Vorschlag „Texte erst ab `xl`“ allein reicht nicht, weil Kopf und Seite bis 1280 px und darüber 1024 px breit sind (`max-w-5xl`). Ab `xl` ist deshalb nur der Kopf `max-w-7xl` breit; die Marke steht damit bei breiten Fenstern weiter links als die Überschrift der Seite (sichtbar, aber üblich). Zwischen 1024 und 1279 px stehen nur Icons (mit Tooltip). Alternative wäre ein Menü „Mehr“ gewesen; das hätte viele bestehende e2e-Fälle berührt, die Einträge direkt anklicken.
3. **Kriterium 5 mit KI aus:** Mit KI an und ohne erreichbares Modell (wie in meiner `.env`) endet ein neuer Auftrag mit `embedding_unavailable` statt „Eingelesen“; das Ollama am Host wollte ich wegen des Messlaufs nicht nutzen. Für Kriterium 5 liefen Worker und API deshalb mit `TWOX_AI_ENABLED=false` (E-59: Einlesen endet nach den Abschnitten erfolgreich). Danach wieder mit `.env` (KI an) für die Läufe 3 und 4.
4. **Offene Aufträge nach erfolgreichem Neueinlesen (Rückfrage, nicht blockierend):** Weil jede Ausführung eine eigene Zeile ist (E-55) und die API keinen Filter „nur neuester Auftrag je Version“ hat, bleibt ein gescheiterter Versuch in der Vorgabe-Ansicht „Offen“ stehen, auch wenn ein späterer Versuch eingelesen hat (der erfolgreiche fällt aus dem Filter). Die Zeile markiert „Älterer Versuch“ nur, wenn der neuere Auftrag auf derselben Seite steht. Optionen: (a) Folgeauftrag Backend: Filter `latest=true` oder Feld `is_latest` an `GET /api/v1/ingest-jobs/`, die Übersicht nutzt ihn für „Offen“ (Empfehlung); (b) so lassen und in der Doku erklären (steht schon in `web/src/pages/README.md`).
5. **Englischer Eintrag „Ingestion“** (statt „Ingest“), Statusauswahl „Error / Ingesting / Queued / Ingested / Skipped“ wie die Abzeichen; Vorgabe „Open (error, running, queued)“ bzw. „Offen (Fehler, läuft, wartet)“ kurz gehalten, damit die Auswahl auf dem Telefon passt.
6. **Spalte „Angestoßen von“ nach Rolle statt nach Inhalt:** Die Spalte erscheint für `manage` (nur dann liefert die API Namen, E-57), auch wenn alle Aufträge der Seite vom System stammen („System“). So springt die Tabelle nicht je Seite.
7. **Reihenfolge:** Die API sortiert nur nach Zeit; „gescheiterte und laufende vorne“ leistet die Vorgabe-Ansicht „Offen“. Unter „Alle“ steht alles nach Zeit.
8. **Zusätzliche Dateien außerhalb der Liste:** `IngestStatus.tsx` (Abweichung 1), `web/src/icons/names.ts` und `web/src/icons/README.md` (Icon, laut Nachtrag), `web/src/components/Layout.tsx` und `Layout.test.tsx` (Kopfzeile, laut Nachtrag), `web/e2e/navigation.spec.ts` (laut Nachtrag), `web/src/session.test.tsx` und `web/src/i18n.test.ts` (Listen, Zahl der Namensräume). `web/src/index.css` nicht geändert.
9. Bei einem ersten Build schrieb ich versehentlich eine Protokolldatei außerhalb des Projektordners; sie wurde sofort gelöscht.

### Fragen an a7

Keine blockierenden (Option zu Hinweis 4 siehe oben).
