# Auftrag 071 – Icon-Schicht mit Lucide für Navigation, Aktionen, Status und Struktur

Meilenstein: Gestaltung (D1, parallel zu M2) · Freigabestufe: C · Status: offen

## Ziel

Eine zentrale, typisierte Icon-Schicht in der Oberfläche und die ersten Icons aus Lucide (`lucide-react`) für Navigation, wiederkehrende Aktionen, Statusanzeigen und die Struktur-Ebenen. Grundlage ist die Bedarfsanalyse `docs/design/icon-bedarfsanalyse.md` (P0-Satz ohne Marke und ohne eigene Geräteklassen-Icons).

## Umfang

- Abhängigkeit `lucide-react`: Version exakt festlegen; Lizenz (ISC) und mitgezogene Pakete an der Quelle prüfen; Laufzeitliste und `THIRD-PARTY-NOTICES.txt` in Stufe `web-build` von `backend/Dockerfile` nachziehen. Nur benannte Einzelimporte (Tree-Shaking), kein dynamisches Laden aller Icons.
- `web/src/icons/` (neu): `Icon`-Komponente mit festen Größen 16/20/24 px, `currentColor`, Strichstärke einheitlich; dekorativ `aria-hidden`, bedeutungstragend mit `aria-label` (Pflicht über den Typ). Ein Namens-Mapping `IconName → Komponente` als einzige Stelle, an der Lucide importiert wird (später ergänzt um eigene Industrie-Icons).
- Einsatz (P0 laut Bedarfsanalyse, H5; IDs NAV-, OBJ-, ACT-, STA-):
  - Navigation: Struktur, Landkarte, Import, Änderungsprotokoll, Selbsttest, Einstellungen (falls 070 schon auf main), Benutzermenü/Abmelden.
  - Struktur-Ebenen im Baum, in Brotkrumen und auf der Landkarte: Standort, Bereich, Anlage, generisches Gerät, Netz; Dokument/Datei, Version.
  - Aktionen: Anlegen, Bearbeiten, Hochladen, Herunterladen, Suchen, Filtern/Zurücksetzen, Ansicht einpassen, Netze ein/aus.
  - Status: Erfolg, Warnung, Fehler, Info, Laden – immer zusammen mit Text, nie nur Farbe.
- Aktiver Navigationspunkt per dezentem Hintergrund statt gefülltem Icon.
- Tests: Vitest für das Mapping (jeder Name rendert ein SVG, `aria-hidden`/`aria-label` korrekt), Snapshot-freie Prüfungen; bestehende Tests anpassen. Playwright: Navigation zeigt Icons mit verborgenem SVG und lesbarem Text.

## Nicht-Ziele

- Eigene Industrie-Icons je Geräteklasse (SPS, Router, Roboter …): brauchen ein Typfeld am Gerät (eigener Auftrag, Datenmodell, Stufe C) und die freigegebenen Entwürfe.
- Logo und Favicon (Auftrag 072). Online/Offline-Status (es gibt kein Monitoring).

## Betroffene Bereiche (Ordner, Dateien)

- `web/package.json`, `web/package-lock.json`, `backend/Dockerfile` (nur Stufe `web-build`)
- `web/src/icons/` (neu), `web/src/components/` (Layout, Navigation, Benutzermenü, Lade-/Fehleranzeigen), `web/src/pages/` (Struktur, Gerät, Datei, Import, Protokoll, Landkarte-Knoten)
- `web/src/navigation.ts` (Icon-Feld je Eintrag), betroffene Tests, `web/e2e/navigation.spec.ts`

## Akzeptanzkriterien (prüfbar)

`W` = `docker compose -p twox-071-web -f deploy/compose/compose.web.yaml`, `D` = `docker compose -p twox-071`, `.env` mit `TWOX_API_PORT=18071`.

0. `docker version` und `docker compose version` enden mit Exit 0.
1. `W --profile dev build web-dev`, `npm ci`, `lint`, `typecheck`, `test`, `build`, `licenses` je Exit 0.
2. `git grep -n "lucide-react" -- web/src` findet Importe nur in `web/src/icons/`.
3. `D --profile dev build migrate api worker web-dev` Exit 0; `THIRD-PARTY-NOTICES.txt` enthält `lucide-react` mit ISC-Text.
4. Browser-Test wie in `ci.yml` (inkl. „Create test account“) bestanden, zweimal ohne `down -v`.
5. Bündelgröße im Kurzbericht (vorher/nachher).
6. Abräumen mit `down -v` endet mit Exit 0.

## Vorgaben und Hinweise

Voraussetzung: Auftrag 070 ist auf `main` (Tokens, Farben über `currentColor`); a7 hat Frage 1 beantwortet.

- Icon-Größen und Strich nach `docs/design/icon-bedarfsanalyse.md`, Teil F. Lokale, ungetrackte Design-Vorlagen unter `docs/design/bildmarke/` nicht ins Repository übernehmen und nicht nennen; dort vorkommende Produktnamen nie in Code, Commits oder Kurzbericht.
- Sprache: Code Englisch, Kurzbericht Deutsch. Keine Personennamen, keine lokalen Pfade mit Benutzernamen. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Empfehlungen übernommen (E-50 bis E-52).

1. **Lucide (`lucide-react`, ISC) als Icon-Bibliothek zulassen?** (a) Ja; (b) eigene SVGs ohne Bibliothek. Empfehlung: (a) – laut Design-Übergabe bereits akzeptiert; ISC ist nach E-23 zulässig.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
