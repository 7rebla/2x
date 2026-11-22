# Auftrag 072 – Marke: Bildmarke im Kopf, Favicon und Touch-Icon

Meilenstein: Gestaltung (D1, parallel zu M2) · Freigabestufe: C · Status: zur Prüfung

## Ziel

Die von a7 ausgewählte Bildmarke erscheint im Kopf der Oberfläche neben dem Schriftzug „2x“, dazu Favicon (SVG und ICO) und Apple-Touch-Icon. Der künftige Produktname wird **nicht** eingebaut (E-52).

## Umfang

- Dateien unverändert aus der lokalen Design-Vorlage übernehmen (Liste unten) nach `web/src/assets/brand/` (Bildmarken für die Komponente) bzw. `web/public/` (Favicon, Touch-Icon), sodass Django/WhiteNoise sie ausliefert. Nur diese Dateien:
  - `bildmarke.svg` (Master, 64er-Raster, `currentColor`) und `bildmarke-16.svg` (Kleinform, `currentColor`)
  - `favicon.svg` (Kleinform; Farbe folgt `prefers-color-scheme`), `favicon.ico` (16/32/48), `apple-touch-icon.png` (180 px)
- Komponente `BrandMark` (typisiert): wählt unter 24 px die Kleinform, sonst den Master; Farbe über ein Token (Marke hell `#765477`, Marke dunkel `#B496B8` – auf dunklem Grund nie `#765477`), dekorativ `aria-hidden` neben dem sichtbaren Text, als Link zur Startseite mit zugänglichem Namen aus `common.json`/`appTitle` („2x“).
- Kopfzeile in `Layout.tsx`: Bildmarke links, daneben der Schriftzug „2x“ wie bisher (UI-Schrift, keine Wortmarken-Schrift). Schutzzone und Mindestgröße nach der README der Vorlage.
- `web/index.html`: `<link rel="icon" href="/favicon.svg" type="image/svg+xml">`, `<link rel="icon" href="/favicon.ico" sizes="16x16 32x32 48x48">`, `<link rel="apple-touch-icon" href="/apple-touch-icon.png">`; Seitentitel bleibt „2x“. Prüfen, dass die Pfade in Produktion (WhiteNoise unter `/`) und im Entwicklungsserver stimmen; Django-Fallback für die Oberfläche darf `/favicon.ico` nicht als `index.html` ausliefern.
- Lizenz: Die Bildmarke ist eigenes Werk des Projekts (Apache-2.0 wie das Repository); kein Eintrag in den Drittanbieter-Hinweisen.
- Tests: Vitest für `BrandMark` (Größenwahl, `aria-hidden`, Link-Name „2x“); Backend-Test oder Playwright: `GET /favicon.ico` liefert `image/x-icon` (bzw. `image/vnd.microsoft.icon`), `/favicon.svg` liefert `image/svg+xml`, beide 200; Playwright: Kopf zeigt die Bildmarke (SVG) und den Text „2x“ in hell und dunkel.

## Nicht-Ziele

- Wortmarke/Schriftzug mit dem künftigen Produktnamen, Lockups, Share-Tech-Schrift (erst nach Veröffentlichung des Namens durch a7).
- Geräte-Icons (eigener Auftrag mit Typfeld).

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/assets/brand/` (neu), `web/public/` (Favicon, Touch-Icon), `web/index.html`
- `web/src/components/BrandMark.tsx` (neu, mit Test), `web/src/components/Layout.tsx`, Theme-Token für die Markenfarbe in `web/src/index.css` bzw. `web/src/theme/`
- falls nötig `backend/twox/config/urls.py` bzw. Auslieferung statischer Dateien (nur für Favicon-Pfade, mit Test)
- `web/e2e/` (Prüfung im bestehenden oder neuen Spec)

## Akzeptanzkriterien (prüfbar)

`W` = `docker compose -p twox-072-web -f deploy/compose/compose.web.yaml`, `D` = `docker compose -p twox-072`, `.env` mit `TWOX_API_PORT=18072`.

0. `docker version` und `docker compose version` enden mit Exit 0.
1. `W --profile dev build web-dev`, `npm ci`, `lint`, `typecheck`, `test`, `build`, `licenses` je Exit 0.
2. Die übernommenen Dateien sind byte-gleich mit der Vorlage (SHA-256 je Datei im Kurzbericht).
3. `D --profile dev build migrate api worker web-dev backend-dev` Exit 0; Backend-Prüfungen aus `ci.yml` grün, falls Backend berührt.
4. Am laufenden Dienst: `/favicon.ico`, `/favicon.svg`, `/apple-touch-icon.png` liefern 200 mit passendem Inhaltstyp.
5. Browser-Test wie in `ci.yml` (inkl. „Create test account“) bestanden, zweimal ohne `down -v`.
6. Abräumen mit `down -v` endet mit Exit 0.

## Vorgaben und Hinweise

Voraussetzung: Auftrag 070 ist auf `main` (Tokens, hell/dunkel).

- Vorlage liegt NUR im Hauptordner des Projekts (ignoriert): `docs/design/bildmarke/logo-paket-l/` – Regeln in `README.md` dort lesen. **In diesem Ordner enthalten viele Dateien den künftigen Produktnamen** (Lockups, Wortmarken-Pfade, Skripte, Vorschauen, READMEs). Diesen Namen nie in Code, Kommentare, Tests, Commits, Kurzbericht oder Schlussantwort schreiben; ausschließlich die oben genannten sechs Dateien übernehmen und vor dem Commit prüfen, dass keine übernommene Datei Text außer SVG-/Bilddaten enthält (keine `<title>`/`<desc>`/Kommentare mit Namen; falls doch: nicht übernehmen, Frage in den Auftrag).
- Sprache: Code Englisch, Kurzbericht Deutsch. Keine Personennamen, keine lokalen Pfade mit Benutzernamen. Nur ausdrücklich genannte Pfade stagen. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

Entschieden (E-52, 22.11.2026): Bildmarke öffentlich im Kopf, Schriftzug „2x“ bis zur Veröffentlichung des Namens.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Status: zur Prüfung.** Alle Kriterien 0–6 erfüllt; alle Läufe am 22.11.2026 im Container (Docker Engine 29.9.3, Compose v5.7.0). Keine neue Abhängigkeit. Keine offene Frage an a7.

### Was wurde gebaut?

- **Dateien, unverändert übernommen:** `web/src/assets/brand/bildmarke.svg`, `web/src/assets/brand/bildmarke-16.svg`, `web/public/favicon.svg`, `web/public/favicon.ico`, `web/public/apple-touch-icon.png`. Vor dem Commit gesichtet: die SVGs enthalten nur Zeichenelemente (`mask`, `rect`, `polyline`, `circle`, im Favicon ein `<style>` für das Farbschema), kein `<title>`, `<desc>`, `<text>` oder Kommentar; PNG und ICO ohne Textblöcke (`tEXt`/`iTXt`/`zTXt`).
- **Token `brand`** in `web/src/index.css`: hell `#765477`, dunkel `#b496b8`, unabhängig vom Akzent (Tailwind `text-brand`). `theme/contrast.test.ts`: neues Paar „Marke auf Fläche/Hintergrund“ (mindestens 3:1, gemessen hell 6,35/5,91, dunkel 6,01/6,77) und ein Test, dass die Markenfarbe in jedem Modus und mit jedem Akzent genau diesen Wert hat.
- **Komponente `web/src/components/BrandMark.tsx`:** Link zu `/` mit Bildmarke und dem Text aus `common:appTitle` („2x“). Unter 24 px die Kleinform, sonst der Master (`brandForm`). Die SVG wird per `?raw` eingebunden und eingebettet (nur so wirkt `currentColor`), `aria-hidden`, Farbe `text-brand`; die Masken-IDs bekommen je Instanz ein eindeutiges Präfix (`useId`). Größe im Kopf 36 px (Master, so hoch wie die Zeile von „2x“). Abstand zum Schriftzug nach der Lockup-Regel 16 Rastereinheiten ab sichtbarer Marke (= 5,6 px Lücke bei 36 px); die Schutzzone von 16 Einheiten (9 px) halten Polster des Kopfs (16 px) und Abstand zur Navigation (32 px) ein. Schriftzug bleibt in der UI-Schrift.
- **`Layout.tsx`:** nur der Markenbereich (`<h1>` enthält jetzt `<BrandMark />`) und die Importzeilen (`Link` entfällt, `BrandMark` kommt dazu).
- **`web/index.html`:** die drei `<link>`-Zeilen wie im Auftrag, Titel bleibt „2x“. Vite setzt beim Bau die Basis davor (`/static/favicon.svg` usw.); im Entwicklungsserver gilt dieselbe Basis für `public/`.
- **Backend (`backend/twox/config/webui.py`, `urls.py`):** Die Auffangregel der Oberfläche hat `/favicon.ico` bisher mit `index.html` beantwortet. Neue Ansicht `web_root_file` liefert genau `favicon.ico` (`image/x-icon`), `favicon.svg` (`image/svg+xml`) und `apple-touch-icon.png` (`image/png`) aus `STATIC_ROOT`, nur GET/HEAD, `Cache-Control: public, max-age=86400`, ohne CSRF-Cookie; fehlt die Datei: 404, nie die Oberfläche. Drei feste `path()`-Einträge vor der Auffangregel. Unter `/static/` liefert WhiteNoise dieselben Dateien.
- **Tests:** Vitest `BrandMark.test.tsx` (17 Fälle: Größenwahl inkl. Grenze 24 px, eindeutige IDs, Abstand, Link-Name „2x“ auch auf Deutsch, `aria-hidden`, kein Text in der Marke, Master/Kleinform). pytest `tests/config/test_webui.py` (+15 Fälle: drei Icons an der Wurzel mit Inhaltstyp und Inhalt, dieselben unter `/static/`, HEAD/POST, 404 ohne Build statt Oberfläche, andere Namen wie `/favicon.png` bleiben Seitenpfade). Playwright `web/e2e/brand.spec.ts` (7 Fälle: Kopf mit SVG-Marke links neben „2x“ in hell und dunkel mit gemessener Farbe, Farbe bleibt bei Akzentwechsel, Links im `<head>` liefern 200 mit Inhaltstyp, die drei Wurzelpfade liefern 200 mit Inhaltstyp und nicht die Oberfläche).
- **Doku:** `web/src/theme/README.md` (Token `brand`, Abschnitt Bildmarke/Favicon/Touch-Icon). Lizenz: eigenes Werk, kein Eintrag in den Drittanbieter-Hinweisen.

**SHA-256 der übernommenen Dateien** (Vorlage = Repository = Auslieferung im laufenden Dienst):

| Datei | SHA-256 |
| --- | --- |
| `bildmarke.svg` | `0cc12bc191b42998d58b411ee83b09baddbde31d92e2482ccbf7601e5bab361c` |
| `bildmarke-16.svg` | `7a5d6c16cf1e3afd85ab358173f5a87dda67b94fcaf01f23f85777f50e21fbd0` |
| `favicon.svg` | `2a1905e15efa02b39fddcfbf8adc9bb588fd9ff65a965ae8bd1a6c81321aba47` |
| `favicon.ico` | `4f853d0225884648406f4c3100fc0c3944911ec614e5940719b8a9eec0a763f0` |
| `apple-touch-icon.png` | `ee6c0feb87e371eacb710615db9eafe24d7e08d7c50f93179159e3c0733c23ab` |

### Wie wurde getestet?

`W` = `docker compose -p twox-072-web -f deploy/compose/compose.web.yaml`, `D` = `docker compose -p twox-072`, `.env` aus `.env.example` mit `TWOX_API_PORT=18072`. „2x“ und „twox-leit“ nicht berührt; `web/dist` vor dem Bau gelöscht.

| AK | Ergebnis |
| --- | --- |
| 0 | erfüllt: Server 29.9.3, Compose v5.7.0, beide Exit 0 |
| 1 | erfüllt: `build web-dev`, `npm ci` (445 Pakete), `lint`, `typecheck` Exit 0; `test` 30 Dateien, 472 Fälle bestanden; `build` Exit 0 (`dist/` mit den drei Icons, byte-gleich); `licenses` „422 packages … License check passed.“; `api:generate` ohne Unterschied |
| 2 | erfüllt: SHA-256 je Datei siehe Tabelle, Vorlage und Kopie gleich |
| 3 | erfüllt: Bau Exit 0. Backend-Prüfungen aus `ci.yml`: `ruff check` „All checks passed!“, `ruff format --check` „137 files already formatted“, `mypy` „no issues found in 137 source files“, `pytest` „1189 passed, 4 deselected“, `pytest -m worker` „4 passed“, `makemessages` ohne Unterschied in `backend/locale`, `makemigrations --check` ohne Änderung, Lizenzprüfung „License check passed.“, OpenAPI-Schema ohne Unterschied |
| 4 | erfüllt: `/favicon.ico` 200 `image/x-icon`, `/favicon.svg` 200 `image/svg+xml`, `/apple-touch-icon.png` 200 `image/png` (je mit der SHA-256 der Vorlage); ebenso unter `/static/…`; `/favicon.png` bleibt eine Seite der Oberfläche |
| 5 | erfüllt: `pull e2e`, `npm ci`, `up -d --wait`, „Create test account“ wie in `ci.yml` („Created account …“), dann `run --rm e2e` zweimal ohne `down -v`: je **37 passed** (davon 7 aus `brand.spec.ts`) |
| 6 | erfüllt: `D --profile dev --profile e2e down -v` und `W --profile dev down -v` Exit 0; kein Container oder Volume von `twox-072` übrig |

Sichtprüfung im eingebauten Browser (`/login`, Dunkelmodus): Marke im Markenton links neben „2x“, mittig zur Schrift.

### Zweig und Arbeitsverzeichnis

Zweig `worktree-agent-a2683aae86f752d0a`, Arbeitsverzeichnis `.claude/worktrees/agent-a2683aae86f752d0a`. Nicht gepusht, nicht zusammengeführt.

### Abweichungen und Hinweise

1. **Backend berührt** (im Auftrag als „falls nötig“ genannt): ohne die neue Ansicht hätte `/favicon.ico` die `index.html` geliefert.
2. **Erster Ansatz mit Regex-Pfad** (`re_path` mit Gruppe) brach die Pfadprüfung in `tests/config/test_api.py` (Platzhalter ohne Beispielwert). Gelöst durch drei feste `path()`-Einträge; `test_api.py` ist unverändert.
3. **Erster Browser-Lauf:** 4 neue Fälle schlugen fehl, weil Playwrights eigener HTTP-Client die Umleitung von `localhost` auf den Dienst `api` nicht kennt (nur Chromium hat sie). Die Prüfungen laufen jetzt per `fetch` in der Seite; danach zweimal grün.
4. **Gebaute Links zeigen auf `/static/…`** (Vite-Basis), nicht auf `/…`; beide Adressen liefern die Dateien. `/static/…` hat mit `TWOX_DEBUG=true` `max-age=0` (WhiteNoise-Vorgabe), die Wurzelpfade einen Tag.
5. **Mögliche Überschneidung mit 071:** `Layout.tsx` Importzeile `react-router` (hier `Link` entfernt) und `theme/contrast.test.ts`/`index.css` (Token `brand`), falls 071 dort ebenfalls ändert.
6. **`dangerouslySetInnerHTML`** nur für die eigenen SVG-Dateien aus `src/assets/brand`, damit `currentColor` greift und die Dateien unverändert bleiben.
7. `docs/DECISIONS.md`, `docs/STATUS.md`, `docs/ROADMAP.md` nicht geändert.
