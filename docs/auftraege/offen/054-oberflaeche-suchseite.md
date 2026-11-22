# Auftrag 054 – Oberfläche: Suchseite

Meilenstein: M2 · Freigabestufe: B · Status: zur Prüfung

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

- **Nachtrag der Leitstelle (aus 071):** `navigation.ts` verlangt je Eintrag ein Pflichtfeld `icon` (Name aus `web/src/icons/names.ts`, jeder Eintrag ein eigenes Icon, `Layout.test.tsx` prüft das). Neue Icon-Namen in `names.ts` ergänzen (gehört zu diesem Auftrag) und `web/e2e/navigation.spec.ts` anpassen (Liste der Einträge; Kopfzeile bleibt bei 1024 px einzeilig in Deutsch und Englisch).

- **Nachtrag der Leitstelle (E-59, KI optional):** Einbettungen, Vektorsuche und alles, was ein Modell braucht, sind eine aktivierbare Zusatzfunktion. Schalter `TWOX_AI_ENABLED` (Einstellung in `settings.py`, Standard `False`; `.env.example` mit Kommentar). Bei „aus“: kein Aufruf von Ollama, keine Einbettungs-Aufgaben, Einlesen endet nach den Abschnitten erfolgreich, die Suche arbeitet nur mit der Stichwortsuche, Selbsttest und Oberfläche zeigen „KI nicht aktiviert“ als neutralen Zustand (kein Fehler, kein Warnsymbol). Jede KI-abhängige Stelle braucht einen Test für beide Zustände; die CI läuft mit „aus“ und mit „an“ plus Attrappe.

Voraussetzung: 052 ist nach `main` zusammengeführt (Endpunkt im erzeugten Client).

- Welle 8, parallel zu 053, falls dieses noch läuft. Ändert `routes.tsx`, `navigation.ts` und `nav.json`; 055 wartet deshalb auf diesen Auftrag.
- **Keine neue Abhängigkeit.**
- Abfragen über die Query-Optionen des erzeugten Clients, wie auf den anderen Seiten.
- Antworten in `page.route` sind selbst geschrieben, ohne Texte aus Herstellerunterlagen.
- Die CI hat nur das Testkonto `e2e-manager`; die Rolle `read` deshalb in Vitest.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

- **Nachtrag der Leitstelle (Prüfung 050):** Die Such-API (052) unterscheidet „KI nicht aktiviert“ von „Sprachmodell nicht erreichbar“. Bei „nicht aktiviert“ zeigt die Seite keinen Fehlerhinweis, höchstens einen neutralen Text (E-59); nur bei „nicht erreichbar“ den Hinweis „Nur Stichwortsuche – Sprachmodell nicht erreichbar“.

- **Nachtrag der Leitstelle (Prüfung 052):** Die Such-API liefert `semantic` dreiwertig (`used`, `disabled`, `unavailable`) statt als Wahrheitswert. Hinweis „Nur Stichwortsuche – Sprachmodell nicht erreichbar“ nur bei `unavailable`; bei `disabled` kein Fehlerhinweis (E-59, neutral, höchstens ein ruhiger Text). `highlights` sind Objekte `{start, end}` in Unicode-Codepoints: den Ausschnitt mit `Array.from(snippet)` zerlegen, sonst verrutschen Markierungen nach Zeichen außerhalb der BMP; Vitest mit Emoji bzw. Zeichen außerhalb der BMP vor einer Markierung. Fundorte haben `version.original_filename` und `plant.id`. Die Vitest-Fälle zu `semantic: false` entsprechend auf die drei Zustände umstellen.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Läufe am 22.11.2026 im Container, Projekte `twox-054` und `twox-054-web`, Port 18054, Docker Engine 29.9.3, Compose v5.7.0. Kriterien 0, 1, 2, 3 und 5 erfüllt; **Kriterium 4 nicht durchgeführt** (siehe Abweichung 1). Keine neue Abhängigkeit, keine Änderung an API, erzeugtem Client oder `test/fakeApi.ts`.

### Was wurde gebaut?

- **Seite `web/src/pages/SearchPage.tsx`** unter `/search` (Rolle `read`), in `routes.tsx` per `lazy()` geladen wie `/map`.
  - Formular (`role="search"`): Suchfeld (höchstens 500 Zeichen), Auswahl „Gerät“ aus `GET /api/v1/devices/` (nach Anlage gruppiert, „Alle Geräte“ zuerst), Knopf „Suchen“; Abschicken mit Enter. Suchtext (gekürzt) und Gerät stehen in der Adresse (`/search?q=…&device=…`, Frage 1 aus 052 = Option b, E-54): verlinkbar, neu ladbar, „Zurück“ stellt die vorige Suche samt Feldern wieder her. Ein Gerätewert, der keine ID sein kann, wird ignoriert; ein Gerät, das nicht in der Liste steht, erscheint als „Gerät Nr. …“.
  - Abfrage über `searchOptions` des erzeugten Clients (TanStack Query), nur mit Suchtext.
  - Zustände: leer (Hinweis, keine Anfrage), lädt („Wird gesucht…“), keine Treffer, Fehler (`ErrorMessage`), Treffer mit Anzahl.
  - `semantic` dreiwertig: `unavailable` → Hinweis „Nur Stichwortsuche – Sprachmodell nicht erreichbar“ (Warnfarbe, Icon, `role="status"`); `disabled` → nur eine ruhige graue Zeile „Stichwortsuche (KI nicht aktiviert)“ ohne Icon und ohne Warnung (E-59); `used` → nichts.
- **Treffer `web/src/pages/search/SearchHitView.tsx`** als Karte: Seite („S. 31“ bzw. „S. 31–32“, englisch „p. 31“/„pp. 31–32“; ohne Seite entfällt die Angabe), Überschriftenpfad („Kapitel › Abschnitt“, auch wenn es eine Seite gibt), Art des Treffers als kleine Marken (Exakt, Stichwort, Bedeutung), Ausschnitt mit `<mark>`, darunter je Fundort: Dateititel mit Link auf `/documents/:id`, „Version n · Dateiname“ (`original_filename`), Marke „Ältere Version“ (mit Tooltip), wenn `is_latest` falsch ist, Gerät mit Link auf `/devices/:id` und Kennung, Anlage. Alles aus der Antwort wird als Text gerendert, kein `dangerouslySetInnerHTML`, nichts geht durch die Interpolation von i18next.
- **Markierungen `web/src/pages/search/snippet.ts`:** `snippetPieces()` zerlegt den Ausschnitt mit `Array.from` in Codepoints und schneidet nach `highlights` `{start, end}`; Positionen außerhalb werden gekappt, leere/umgekehrte verworfen, überlappende und angrenzende zusammengefasst; die Teile ergeben zusammen immer den Ausschnitt. `pageRange()` für die Seitenangabe.
- **Navigation:** Eintrag „Suche“/„Search“ hinter „Landkarte“, Rolle `read`, Icon `search` (siehe Abweichung 3). Texte in `locales/{de,en}/nav.json`, neuer Namensraum `search.json`, eingetragen in `i18n.ts` und `i18next.d.ts`.
- **Kopfzeile (Nachtrag aus 071):** Mit sechs Einträgen lief die deutsche Kopfzeile bei 1024 px um 41 px über. Abstände verkleinert (siehe Abweichung 2), danach einzeilig in Deutsch und Englisch.
- **Doku:** `web/src/pages/README.md` (Adressentabelle, Abschnitt „Search“), ein Halbsatz in `web/src/locales/README.md` (Namensraum).

### Wie wurde getestet?

`D` = `docker compose -p twox-054`, `W` = `docker compose -p twox-054-web -f deploy/compose/compose.web.yaml`; `.env` aus `.env.example` (ohne BOM) mit `TWOX_API_PORT=18054`, KI an, aber `TWOX_LLM_BASE_URL=http://127.0.0.1:9/v1` (dort antwortet nichts – kein Test erreicht das Ollama am Host, wie in der CI ohne Ollama). Vor jedem Build `web/dist` gelöscht. Die Umgebungen „2x“ und „twox-leit“ wurden nicht berührt.

| Nr. | Ergebnis | Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | Engine 29.9.3, Compose v5.7.0, je Exit 0 |
| 1 | erfüllt | `build web-dev`, `npm ci` („added 446 packages“), `lint`, `typecheck`, `test` (36 Dateien, 681 Tests), `build`, `licenses` („License check passed.“) je Exit 0. Suchseite als eigener Teil `SearchPage-….js` 8,83 kB (gzip 2,89 kB). Keine Vite-Warnung mehr, Hauptbündel `index-….js` 345,75 kB – aber siehe Abweichung 4 zur Bündelgröße |
| 2 | erfüllt | `npm run api:generate` Exit 0; `git diff --exit-code -- web/openapi web/src/api` Exit 0, `git status --porcelain` dazu leer |
| 3 | erfüllt | `build migrate api worker web-dev`, `pull e2e`, `npm ci`, `up -d --wait …` je Exit 0; „Create test account“ wörtlich mit `D`. Erster Lauf: 46 bestanden, 2 fehlgeschlagen (`navigation.spec.ts`, Kopfzeile bei 1280 und 1024 px: 41 px Überlauf); nach der Korrektur zweiter Lauf: **48 passed**; nach dem letzten Code-Commit Neubau, „Updated account …“, dritter Lauf ohne `down -v`: **48 passed**, Exit 0, darunter die vier Fälle aus `search.spec.ts` |
| 4 | **nicht durchgeführt** | siehe Abweichung 1 |
| 5 | erfüllt | `D --profile dev --profile e2e down -v` und `W --profile dev down -v` je Exit 0; danach kein Container, Volume oder Netz mit `twox-054` |

Zusätzlich: Im Protokoll des `api`-Dienstes nach dem e2e-Lauf steht der Suchtext der echten Suche 0-mal, die Zeilen lauten `"GET /api/v1/search/ HTTP/1.1" 200 OK` (Logfilter aus 052).

**Vitest neu:** `pages/search/snippet.test.ts` (Zerlegen, leer, Emoji vor der Markierung, Zeichen außerhalb der BMP als Ganzes markiert, unsortierte/überlappende/angrenzende/außerhalb liegende Positionen, Markup bleibt Text, `pageRange`). `pages/SearchPage.test.tsx` (33 Fälle): leerer Zustand ohne Anfrage; Geräteliste nach Anlage; Parameter aus der Adresse (q, device) gehen in die Anfrage und ins Formular; ungültiges Gerät ignoriert, Suchtext gekürzt; unbekanntes Gerät; Abschicken schreibt `?q=…&device=…` und sucht (Submit-Knopf im Formular = Enter); leerer Text leert die Adresse; „Zurück“ stellt den vorigen Text her; Laden; keine Treffer (englisch, deutsch); Fehler 500 mit Text, 400, keine Antwort; `semantic` `unavailable` (englisch und deutsch, nur dort der Hinweis), `disabled` (ruhige Zeile, kein Icon, keine Warnung, kein `alert`), `used` (nichts); Art des Treffers (englisch, deutsch); Anzahl und Reihenfolge; `<mark>` im Ausschnitt; Markierung nach Emoji und Zeichen außerhalb der BMP; `<img onerror>`, `<b>`, `<script>` im Ausschnitt und `<i>` im Überschriftenpfad nur als Text; Seite, Seitenbereich, ohne Seite nur Überschriftenpfad (englisch, deutsch); mehrere Fundorte mit Datei, Version, Dateiname, Gerät, Anlage; Links auf Datei- und Geräteseite, Klick führt zur Dateiseite; „Ältere Version“ nur am betroffenen Fundort (englisch, deutsch); Navigationseintrag für `reader` und `manager` (Link, Icon, Seite, `aria-current`, kein „keine Berechtigung“). Angepasst: `routes.test.tsx` (deutsche Liste, Adresse `/search`), `session.test.tsx` (Listen je Rolle, `requiredRole("/search")`), `i18n.test.ts` (11 Namensräume). `Layout.test.tsx` prüft das eigene Icon je Eintrag unverändert und besteht.

**Playwright neu `web/e2e/search.spec.ts`** (als `e2e-manager`): Navigation zur Suche (leerer Zustand, Formular); ohne Sitzung → `/login?next=%2Fsearch`; echte Suche nach einem Wort ohne Treffer mit Enter → 200, „No hits…“, Suchtext in der Adresse, Neuladen wiederholt die Suche; Antwort über `page.route` (selbst geschrieben, Testsätze) mit echtem Testgerät: Gerät gewählt und Enter → Anfrage mit `q` und `device`, Adresse, Hinweis „unavailable“, „pp. 31–32“, Überschriftenpfad, `<mark>` nach einem Emoji, Art, „Older version“, Dateiname, Anlage, Link auf die Dateiseite, Klick auf das Gerät öffnet dessen Seite, „Zurück“ zeigt wieder die Treffer mit gewähltem Gerät; Konsole jeweils fehlerfrei. **Angepasst `web/e2e/navigation.spec.ts`:** Listen der Einträge in Englisch und Deutsch.

**Sichtprüfung:** Mit einer vorübergehenden, nicht eingecheckten Playwright-Datei Bildschirmfotos der Seite mit Treffern (1024 px Englisch und Deutsch, 375 px Deutsch) angesehen; danach Fundorte durch dünne Linien getrennt und das Gerätefeld an die Höhe des Suchfelds angeglichen.

**Bündelgröße** (`npm run build`, vorher `web/dist` und `web/playwright-report` gelöscht, siehe Abweichung 5):

| Teil | `main` (`a1917c1`) | Zweig 054 |
| --- | --- | --- |
| `index-….js` | 560,93 kB (gzip 169,61) | 345,75 kB (gzip 102,00) |
| `react-query.gen-….js` (neu abgetrennt, per `modulepreload` beim Start geladen) | – | 218,44 kB (gzip 70,28) |
| `rolldown-runtime-….js` (beim Start geladen) | – | 0,59 kB (gzip 0,36) |
| **beim Start geladenes JS zusammen** | **560,93 kB (gzip 169,61)** | **564,78 kB (gzip 172,64)** |
| `SearchPage-….js` (nur bei `/search`) | – | 8,83 kB (gzip 2,89) |
| `MapPage-….js` | 261,29 kB | 261,39 kB |
| `index-….css` | 27,76 kB (gzip 6,56) | 29,00 kB (gzip 6,79) |

Zuwachs durch 054 beim Start: **+3,85 kB JS (gzip +3,03 kB)** und +1,24 kB CSS; dazu 8,83 kB, die erst beim Öffnen der Suche geladen werden.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-abea2797bd6970a41`
- Arbeitsverzeichnis: `.claude/worktrees/agent-abea2797bd6970a41` (relativ zum Projektordner)
- Commits: `Split search snippets into marked pieces by Unicode code points`, `Add the search page /search with hits, pages, places and links`, `Add a browser test for the search page and its navigation entry`, `Tighten the header spacing so six navigation entries fit at 1024 px`, `Separate the places of a hit by lines and align the search form`, dazu dieser Kurzbericht. Nicht gepusht, nichts zusammengeführt.

### Abweichungen und Hinweise

1. **Kriterium 4 nicht durchgeführt.** Dafür hätte ich in `twox-054` einen eigenen Docling-Dienst starten und die BetrSichV (rund 5 min volle CPU, über 5 GB Speicher) einlesen müssen. Beim Start der Arbeit lief `2x-docling-1` mit über 1100 % CPU (Messlauf); ein zweiter Docling hätte die Zeiten des Messlaufs verfälschen und den Speicher (15,5 GB) knapp machen können. Vorschlag: Die Leitstelle prüft Kriterium 4 nach dem Zusammenführen in der Testumgebung „2x“, wo die BetrSichV schon eingelesen ist (z. B. `/search?q=Prüfung`: Treffer mit Seitenangabe wie „S. 30–31“, der Link mit dem Dateititel öffnet die Dateiseite). Optionen: (a) so (Empfehlung), (b) ich hole es in `twox-054` nach, wenn der Messlauf beendet ist.
2. **Dateien außerhalb der genannten Liste, nötig für den Nachtrag „Kopfzeile bleibt einzeilig“:** `web/src/components/Layout.tsx` (Abstand der Kopfzeile `gap-x-6` → `gap-x-4`) und `web/src/index.css` (`.nav-link`: Innenabstand seitlich 0,5 → 0,375 rem, Abstand Icon–Text 0,375 → 0,25 rem); zusammen 52 px gewonnen bei 41 px Überlauf. Die Marge ist knapp (11 px bei Benutzername `e2e-manager`); ein siebter Eintrag (055) braucht eine andere Lösung (z. B. Texte erst ab `xl` oder kürzere Bezeichnung „Protokoll“). Ebenfalls außerhalb: `web/src/session.test.tsx` und `web/src/i18n.test.ts` (Listen bzw. Anzahl der Namensräume), `web/src/locales/README.md` (ein Halbsatz).
3. **Icon:** Für den Eintrag nutze ich den vorhandenen Namen `search` (Lupe, in `names.ts` schon als NAV-05 vermerkt) statt eines neuen Namens. Unter den Navigationseinträgen ist er eindeutig (`Layout.test.tsx` besteht); ein zweiter Name auf dieselbe Zeichnung würde den Test „alle Zeichnungen verschieden“ in `icons.test.tsx` brechen. `names.ts` ist deshalb unverändert. Dieselbe Lupe steht auch an den Suchfeldern von Struktur und Landkarte und am Knopf „Suchen“.
4. **Bündelgröße:** Das Hauptbündel `index-….js` liegt jetzt bei 345,75 kB und Vite warnt nicht mehr. Das ist aber eine Nebenwirkung der Aufteilung durch Rolldown: Weil jetzt zwei nachgeladene Seiten und das Hauptbündel den erzeugten Client und TanStack Query teilen, liegt dieser Teil in einem eigenen Stück (`react-query.gen-….js`, 218 kB), das `index.html` beim Start sofort mitlädt. Beim Start werden also weiterhin rund 565 kB JS geladen (+3,85 kB gegenüber `main`). 062 bleibt damit nötig.
5. **Tailwind und `web/playwright-report/`:** Wie in 070 für `web/dist/` beschrieben, durchsucht Tailwind im Container `web-dev` auch den HTML-Bericht von Playwright, wenn er nach einem e2e-Lauf in `web/` liegt; die CSS-Datei wuchs dadurch einmal auf 31,44 kB. Für Messungen vorher auch `web/playwright-report/` löschen. Das Image (`backend/Dockerfile`) ist nicht betroffen, wenn es ohne diesen Ordner baut (nicht geprüft).
6. **Wackeliger Test außerhalb meines Bereichs:** `session.test.tsx` › „signs out at allauth with the CSRF token and leads to /login“ schlug in 2 von 10 vollen Vitest-Läufen auf dem Zweig fehl (`/login?next=%2Fselftest` statt `/login`), in 4 Läufen mit dem Stand von `main` nicht; alle Läufe nach dem letzten Commit (5) waren grün. Ursache vermutlich ein Wettlauf in `UserMenu.tsx`: Nach `forgetSession()` leitet `RequireSession` mit `next` um, zugleich ruft `navigate("/login")`; welches zuletzt wirkt, hängt vom Zeitpunkt ab. Die zwei Fehlläufe fielen in die Zeit, in der der Rechner durch den Messlauf stark ausgelastet war. Nicht geändert (nicht mein Bereich); Vorschlag: kleiner Folgeauftrag oder die Prüfung im Test auf `pathname` beschränken.
7. **Gerät wirkt erst beim Abschicken:** Die Auswahl des Geräts startet keine Suche von selbst, sondern mit Enter oder „Suchen“ (wie der Filter des Änderungsprotokolls).
8. **Überschriftenpfad auch mit Seite:** „ohne Seite der Überschriftenpfad“ habe ich so umgesetzt, dass der Pfad immer erscheint (er ist laut Ziel Teil jedes Treffers) und die Seitenangabe nur, wenn es eine gibt.
9. **Gerät ohne Gerätetyp-Icon:** Die Such-API liefert kein `device_class`; die Fundorte zeigen deshalb das allgemeine Geräte-Icon.

### Fragen an a7

Keine blockierenden (Option zu Kriterium 4 siehe Abweichung 1).
