# Auftrag 079 – Tabellen am Desktop lesbar

Meilenstein: Gestaltung (D1) · Freigabestufe: B · Status: erledigt

Voraussetzung: 077 ist auf `main`.

## Ziel

Dateien-, Protokoll- und Einlese-Tabellen brechen Datum, Größe, Version und Benutzer um; die Protokolltabelle zeigt Rohfelder (id, blob_key, sha256, Fremdschlüssel) und lange Hashes und ist schon bei 1280 px breiter als der Platz; die Prüfsumme als Dreieck wirkt wie ein Fehler. Danach sind die Tabellen ruhig lesbar.

## Umfang

- `whitespace-nowrap` für Datum, Größe, Version, Benutzer.
- Prüfsumme und Benutzer in der Dateitabelle in eine Detailzeile oder einen Tooltip; „Herunterladen“ als Icon-Knopf mit `aria-label`.
- Dateinamen: `break-words` statt `break-all`, lange Namen gekürzt mit vollem Namen im `title`.
- Änderungsprotokoll: technische Felder standardmäßig unter „Technische Angaben“ einklappen (wie beim Einlesen), Hashes gekürzt, Feldnamen übersetzt; Rohdaten bleiben aufklappbar.
- Tests (Vitest; e2e, wo Layout oder Bedienung sich ändern) für das neue Verhalten; bestehende Tests angepasst, nicht abgeschwächt.
- Doku: `web/src/pages/README.md` bzw. `web/src/theme/README.md` nachziehen, wo betroffen.

## Nicht-Ziele

- Keine neue Abhängigkeit, keine Änderung an API oder Backend.
- Nur der genannte Bereich; andere Befunde der UI-Analyse haben eigene Aufträge.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/components/DeviceFiles.tsx`, `web/src/pages/DocumentPage.tsx`, `web/src/pages/IngestPage.tsx`, `web/src/components/AuditTrail.tsx`, zugehörige Tests und `locales`

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Web-Job aus `.github/workflows/ci.yml` grün (lint, typecheck, test, build, licenses), `api:generate` ohne Unterschied.
2. e2e wie in `ci.yml` grün.
3. Im eigenen Projekt im Browser geprüft bei 375, 1024 und 1600 px, hell und dunkel; Beobachtungen im Kurzbericht (Bildschirmfotos nur lokal, nicht eingecheckt).
4. `down -v` der eigenen Compose-Projekte endet mit Exit 0.

## Vorgaben und Hinweise

- Herkunft: UI-Analyse der Sitzung „UI-Analyse“ (22.11.2026, lokal), Entscheidung von a7 E-65 bzw. Stufe B der Leitstelle.
- Gestaltung: Tokens aus 070, Icons nur über `web/src/icons` (071), Bausteine aus `web/src/components/ui/` (077). Bewegung reduzierbar (E-52).
- Texte in Deutsch und Englisch (`web/src/locales/`).

## Fragen an a7 (mit Optionen und Empfehlung)

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Was wurde gebaut?**

- Dateitabelle (Geräteseite, `DeviceFiles.tsx`): sieben statt neun Spalten (Titel, Art, Version, Hochgeladen, Größe, Einlesen, Herunterladen). Benutzer steht als Detailzeile mit Personen-Icon unter dem Zeitpunkt („Benutzer:" nur für Screenreader), die Prüfsumme als ruhige Detailzeile „SHA-256 1a2b…" unter dem Titel – ohne Dreieck, gepunktet unterstrichen, voller Wert als Tooltip und per Klick. Version, Datum, Größe und Benutzer mit `whitespace-nowrap`. Herunterladen als Icon-Knopf (28 px, `aria-label` und Tooltip „Version N herunterladen"); die Spaltenüberschrift ist nur für Screenreader. Titel mit `break-words`, zwei Zeilen, voller Titel im `title`.
- Versionstabelle (`DocumentPage.tsx`): gleiches Muster; Dateiname mit `break-words` statt `break-all`, nach zwei Zeilen gekürzt, voller Name im `title`; Prüfsumme darunter.
- Einlesen (`IngestPage.tsx`): Zeile „Version N · Dateiname" mit `break-words`, zwei Zeilen, Dateiname im `title`, „Version N" ohne Umbruch (Zeit- und Benutzerspalte waren schon `nowrap`).
- Änderungsprotokoll (`AuditTrail.tsx`): Feldnamen übersetzt (de/en, API-Name als Tooltip; unbekannte Felder wie bisher roh). Technische Felder (id, blob_key, sha256, Fremdschlüssel site/area/plant/device/document/uploaded_by/created_by) standardmäßig unter „Technische Angaben" eingeklappt. Hashes (≥ 32 Hex-Zeichen) gekürzt wie in der Dateitabelle, voller Wert im Tooltip. **Rohdaten bleiben aufklappbar:** unter „Technische Angaben" steht das vollständige `changes` des Eintrags als JSON (eine Zeile je Feld), auch die sonst ausgelassenen leeren Paare – es geht nichts verloren. Zeitpunkt, Benutzer, Aktion, Objektart ohne Umbruch.
- Bausteine in `components/files/parts.tsx`: `Checksum` (neu gestaltet), `FileName`, `DownloadIconLink`, `UploadedBy`. `DownloadLink` bleibt unverändert (wird in `UploadForm.tsx` genutzt, Bereich von 088).
- Doku: `web/src/pages/README.md` (Abschnitt Files ergänzt, neuer Abschnitt „Change log entries"), `web/src/theme/README.md` (Monospace auch für die Rohdaten).

**Wie wurde getestet?**

- Vitest: neue Tests für Spalten, `nowrap`, Detailzeilen, Icon-Knopf, Dateinamen (Tooltip, `break-words`, kein `break-all`), Prüfsumme ohne Dreieck, technische Felder eingeklappt, Hash-Kürzung, Rohdaten vollständig, nur technische Änderungen, deutsche Texte. Bestehende Tests an die übersetzten Feldnamen und die neuen Spalten angepasst (gleiche Aussagen, nicht abgeschwächt). 799 Tests grün.
- e2e: `files.spec.ts` (Prüfsumme aufklappen, Icon-Knopf, Dateiname im `title`), `audit.spec.ts` (übersetzte Namen, „Technische Angaben" eingeklappt, nach Klick ID, Anlage-ID und Rohdaten sichtbar), `m1-acceptance.spec.ts` (übersetzte Feldnamen „IP address", „Device class").
- Kriterium 0: `docker version` und `docker compose version` Exit 0.
- Kriterium 1: Web-Job wie in `ci.yml` (Projekt `twox-079-web`): lint, typecheck, test, build, licenses grün; `api:generate` ohne Unterschied.
- Kriterium 2: e2e wie in `ci.yml` (Projekt `twox-079`, API-Port 18079, Testkonto per `create_account`): 55 bestanden, 1 übersprungen (lokaler Teil der M2-Abnahme, wie in der CI).
- Kriterium 3: Sichtprüfung im eingebauten Browser gegen das eigene Projekt bei 1600, 1280, 1024 und 375 px, hell und dunkel. 1600/1280/1024 px: alle vier Tabellen passen in ihren Rahmen (Dateien 958/958 px bzw. 943/943, Versionen ebenso, Protokoll 992/992 bzw. 977/977 auch mit allen „Technischen Angaben" aufgeklappt, vorher laut Analyse 1209/992); Dateizeilen einzeilig (54 px hoch), Datum, Größe, Benutzer brechen nicht mehr um. Dunkel: Detailzeilen und Rohdaten gut lesbar. 375 px: Tabellen scrollen wie bisher waagerecht in ihrem Kasten (Karten-Darstellung ist Ü3, eigener Auftrag); dabei gefunden und behoben: die neuen Screenreader-Texte (absolut positioniert) verbreiterten die Seite auf 723 px – der Scrollkasten ist jetzt `relative`, danach Seitenbreite 375 px.
- Kriterium 4: `down -v` beider Projekte Exit 0.

**Zweig und Arbeitsverzeichnis**

Zweig `worktree-agent-a709f7ae915f9b033`, Arbeitsverzeichnis `.claude/worktrees/agent-a709f7ae915f9b033`. Nicht gepusht.

**Abweichungen**

- Zusätzlich berührt (eng zugehörig, nicht in der Liste): `components/files/parts.tsx` (Bausteine der Dateitabellen), `pages/AuditPage.test.tsx` (eine Erwartung auf übersetzten Feldnamen), `e2e/m1-acceptance.spec.ts` und `e2e/audit.spec.ts` (übersetzte Feldnamen), `e2e/files.spec.ts`.
- Die Prüfsumme steht auch auf der Dateiseite als Detailzeile (unter dem Dateinamen), und der Download ist dort ebenfalls ein Icon-Knopf – einheitlich mit der Gerätetabelle.
- Für die Sichtprüfung habe ich in meiner lokalen `.env` (nicht eingecheckt) `twox079.localhost` zu `TWOX_ALLOWED_HOSTS` ergänzt: parallele Projekte auf 127.0.0.1 teilen sich Cookies (Port zählt nicht), die Anmeldung wurde ständig überschrieben.
- Hinweis am Rande (nicht geändert): Werte wie die Art einer Datei („document") oder Geräteklasse („plc") erscheinen im Protokoll weiter als API-Wert.
