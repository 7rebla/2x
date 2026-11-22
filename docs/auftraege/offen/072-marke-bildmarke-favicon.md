# Auftrag 072 – Marke: Bildmarke im Kopf, Favicon und Touch-Icon

Meilenstein: Gestaltung (D1, parallel zu M2) · Freigabestufe: C · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
