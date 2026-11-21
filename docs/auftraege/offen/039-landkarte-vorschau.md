# Auftrag 039 – Landkarte als interaktive Vorschau

Meilenstein: M1b (vorgezogene Vorschau auf M7, E-48) · Freigabestufe: C · Status: offen

## Ziel

Eine interaktive Landkarte der erfassten Struktur in der Oberfläche: Standort, Bereiche, Anlagen und Geräte als Knoten, zusätzlich die IP-Netze der Geräte. Man kann verschieben, zoomen, Knoten anklicken und kommt zur Geräteseite. Die Karte zeigt nur, was in der Datenbank steht; Verbindungen aus Konfigurationen kommen erst mit M5/M7.

## Umfang

- Neue Seite `/map` mit Navigationseintrag „Landkarte" / „Map" (Rolle `read` genügt).
- Darstellung mit `@xyflow/react` (React Flow, MIT, E-48). Version exakt festlegen; Lizenz und mitgezogene Pakete an der Quelle prüfen und im Kurzbericht nennen. Laufzeitliste und `THIRD-PARTY-NOTICES.txt` in der Stufe `web-build` von `backend/Dockerfile` nachziehen; die CSS-Datei der Bibliothek einbinden.
- Daten nur aus den vorhandenen Endpunkten (`sites`, `areas`, `plants`, `devices`) über den erzeugten TanStack-Query-Client. Keine Änderung am Backend, an Schema oder Client.
- Knoten:
  - Standort und Bereiche als Gruppen (Parent-Knoten), Anlagen als Gruppen in ihrem Bereich, Geräte als Knoten in ihrer Anlage. Beschriftung: Name, darunter Kennung; bei Geräten zusätzlich IP-Adresse und Modell, wenn vorhanden.
  - Netze: Für jedes IPv4-/24-Netz, in dem mindestens ein Gerät liegt, ein Netz-Knoten (z. B. „192.168.0.0/24"); IPv6 nach /64. Kanten nur „Gerät gehört zu Netz", gestrichelt und als solche beschriftet. Geräte ohne IP haben keine Netzkante. **Keine Verbindungen erfinden**: keine Kanten zwischen Geräten, keine abgeleiteten Beziehungen.
- Bedienung: Verschieben, Zoomen, „Ansicht einpassen", Minikarte, Steuerelemente; Klick oder Enter auf einen Geräteknoten öffnet `/devices/:id`; Auswahl hebt das Gerät und seine Netzkante hervor. Suchfeld (Name, Kennung, IP) zentriert und markiert Treffer. Ein-/Ausblenden der Netz-Knoten.
- Anordnung automatisch und stabil: gleiche Daten ergeben dieselbe Anordnung (deterministisch, ohne Zufall); verschobene Knoten werden nicht gespeichert (kein Speichern von Positionen in M1b).
- Zweisprachig (neue Locale-Datei `map.json`, de/en), Texte aus Daten nur als Text.
- Leerer Zustand („Noch keine Struktur erfasst") mit Link zur Strukturseite; Lade- und Fehlerzustände wie auf den anderen Seiten.
- Tests: Vitest für die Umrechnung API-Daten → Knoten/Kanten (Netzbildung, Geräte ohne IP, IPv6, Leerfall, Determinismus) und für die Seite (Rolle `read` sieht die Karte, Klick führt zur Geräteseite). Playwright: Struktur über die API mit `testName()`/`testIp()` anlegen, `/map` öffnen, Geräteknoten und Netz-Knoten sichtbar, Klick führt zur Geräteseite, Suche findet das Gerät.

## Nicht-Ziele

- Verbindungen aus Konfigurationen, Protokolle, MQTT-Topics (M5/M7).
- Speichern von Positionen oder eigenen Layouts, Bearbeiten in der Karte.
- Geräte-Icons nach Typ (es gibt noch kein Typfeld; siehe `docs/design/icon-bedarfsanalyse.md`, H7 T-2). Einheitliche Knotenform genügt.
- Backend-Änderungen, neue Endpunkte.

## Betroffene Bereiche (Ordner, Dateien)

- `web/package.json`, `web/package-lock.json`
- `web/src/pages/MapPage.tsx` (neu), `web/src/pages/map/` (neu: Umrechnung, Knotentypen, Tests)
- `web/src/routes.tsx`, `web/src/navigation.ts` (ein Eintrag), `web/src/locales/{de,en}/map.json` (neu), `web/src/locales/{de,en}/nav.json` (ein Schlüssel), `web/src/i18n.ts` (Namensraum registrieren)
- `web/e2e/map.spec.ts` (neu), betroffene Tests in `web/src/routes.test.tsx`
- `backend/Dockerfile`, nur Stufe `web-build`

## Akzeptanzkriterien (prüfbar)

`W` = `docker compose -p twox-039-web -f deploy/compose/compose.web.yaml`, `D` = `docker compose -p twox-039`, `.env` mit `TWOX_API_PORT=18039`.

0. `docker version` und `docker compose version` enden mit Exit 0.
1. `W --profile dev build web-dev`, `W run --rm web-dev npm ci`, dann `lint`, `typecheck`, `test`, `build`, `licenses` je Exit 0.
2. `W run --rm web-dev npm run api:generate`, danach `git diff --exit-code -- web/openapi web/src/api` ohne Unterschied.
3. `D --profile dev build migrate api worker web-dev` Exit 0 (Laufzeitliste stimmt); `THIRD-PARTY-NOTICES.txt` im Image enthält `@xyflow/react` und alle mitgezogenen Laufzeitpakete.
4. Browser-Test wie in `ci.yml` (inkl. „Create test account") meldet alle Tests bestanden, auch `map.spec.ts`; ein zweiter Lauf ohne `down -v` ebenfalls.
5. Abräumen mit `down -v` beider Projekte endet mit Exit 0.

## Vorgaben und Hinweise

Voraussetzung: E-48 (a7, 22.11.2026). Kann parallel zu 034 (Backend) und 035 (Import-Oberfläche) laufen; 035 ändert weder `package.json` noch `routes.tsx`/`navigation.ts`.

- Einzige neue Abhängigkeit: `@xyflow/react` samt dem, was es mitzieht. Keine Layout-Bibliothek (dagre, elk) – die Anordnung ist eine eigene, kleine, getestete Funktion (Gitter je Gruppe). Sollte React Flow ohne zusätzliche Pakete nicht sinnvoll anordnen lassen: Frage in den Auftrag, Status „wartet auf a7".
- Prüfe, dass die Bibliothek keine Netzanfragen, Telemetrie oder Lizenzschlüssel-Prüfung zur Laufzeit macht (Leitplanke 6) und dass das Wasserzeichen/„attribution" der MIT-Version zulässig ausgeblendet werden darf oder sichtbar bleibt – im Kurzbericht nennen.
- Barrierefreiheit: Knoten per Tastatur erreichbar, Geräteknoten haben einen zugänglichen Namen; die Karte ersetzt nicht den Baum – auf der Seite ein Link zur Strukturseite als Listenansicht.
- Bundle wächst; Vite-Warnung über 500 kB ist zulässig, im Kurzbericht die neue Größe nennen. Wenn einfach möglich, die Kartenseite per `lazy()` nachladen.
- Sprache: Code und Kommentare Englisch, Kurzbericht Deutsch. Keine Personennamen, keine lokalen Pfade mit Benutzernamen.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push.

## Fragen an a7 (mit Optionen und Empfehlung)

Entschieden am 22.11.2026 (E-48): interaktive Vorschau vorziehen, Darstellung mit React Flow; Netze aus IP-Adressen gruppieren (Empfehlung der Leitstelle, ohne Widerspruch von a7).

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
