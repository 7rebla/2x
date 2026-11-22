# Auftrag 089 – Ergebniszahl als Live-Region, Brotkrumen auf der Dateiseite

Meilenstein: Gestaltung (D1) · Freigabestufe: B · Status: zur Prüfung

Voraussetzung: 077, 079 und 083 sind auf `main`.

## Ziel

Gefilterte Listen (Protokoll, Einlesen) melden die Trefferzahl Screenreadern nicht; die Dateiseite zeigt als Brotkrumen nur „Datei“, die Geräteseite den ganzen Pfad.

## Umfang

- Gemeinsamer Baustein „Ergebniszahl“ mit `role="status"` für Protokoll und Einlesen (Struktur macht 083).
- Brotkrumen der Dateiseite: Standort › Bereich › Anlage › Gerät › Datei, gemeinsamer Baustein mit der Geräteseite.
- Tests (Vitest; e2e, wo Layout oder Bedienung sich ändern) für das neue Verhalten; bestehende Tests angepasst, nicht abgeschwächt.
- Doku: `web/src/pages/README.md` bzw. `web/src/theme/README.md` nachziehen, wo betroffen.
- Nachtrag der Leitstelle (Prüfung 068): `IngestError` in `web/src/components/files/IngestStatus.tsx` zeigt den Hinweis „Nur teilweise umgewandelt“ auch, wenn ein Auftrag `failed` ist und `partly_converted` wahr (zusätzlich zur Fehlermeldung), sowie bei wartenden/laufenden Einbettungsaufträgen mit `partly_converted`; Tests anpassen (`IngestStatus.test.tsx`). `IngestStatus.tsx` und der Test gehören dafür zu den betroffenen Bereichen.

## Nicht-Ziele

- Keine neue Abhängigkeit, keine Änderung an API oder Backend.
- Nur der genannte Bereich; andere Befunde der UI-Analyse haben eigene Aufträge.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/components/AuditTrail.tsx`, `web/src/pages/IngestPage.tsx`, `web/src/pages/DocumentPage.tsx`, `web/src/pages/DevicePage.tsx`, neu Baustein unter `web/src/components/`, Tests

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

- Neuer Baustein `web/src/components/ResultCount.tsx`: `ResultCount` (Region mit `role="status"`, höflich; Zahl klein in `fg-muted`, bei null Treffern der Leertext an Stelle der Liste) sowie `useResultCount`/`useReportCount`. Die Region liegt außerhalb des Teils, den ein neuer Filter per `key` neu aufbaut, damit Screenreader die neue Zahl ansagen; während ein neuer Filter lädt, ist sie leer. Unveränderte Zahl (Abfrage alle 5 s, Blättern) ändert nichts im DOM und wird nicht erneut vorgelesen.
- Änderungsprotokoll (`AuditTrail`, also `/audit` und Dateiseite) und `/ingest`: Ergebniszahl über der Liste („120 Einträge gefunden“, „3 Aufträge gefunden“, Einzahl/Mehrzahl, de und en). Die bisherige Gesamtzahl in der Seitennavigation („Einträge: 120“) entfällt, weil sie doppelt wäre; „Seite 1 von 3“ bleibt. Die Leertexte stehen jetzt in der Region (vorher hatte nur `/ingest` dafür eine eigene `role="status"`, das Protokoll keine). Testkennungen `audit-total`, `audit-empty`, `ingest-total`, `ingest-empty` bleiben.
- Neuer Baustein `web/src/components/Breadcrumb.tsx`: `Breadcrumb` (benannte `nav`, geordnete Liste, Icon je Ebene, „›“ aus dem Stylesheet, letzte Ebene `aria-current="page"`) und `useDeviceCrumbs`. Geräteseite nutzt ihn unverändert im Ergebnis; die Dateiseite zeigt statt „Datei“ jetzt Struktur › Standort › Bereich › Anlage (Kennung) › Gerät (Link) › Datei („Ort der Datei“ / „Location of the file“). Solange das Gerät nicht geladen ist oder nicht geladen werden kann: Struktur › „Gerät 12“ (Link) › Datei.
- Nachtrag 068: `IngestError` zeigt „Nur teilweise umgewandelt“ als eigenen Absatz (`warning`, Icon) bei jedem Auftrag mit `partly_converted`: allein bei erledigten sowie wartenden/laufenden Einbettungsaufträgen, unter der Fehlermeldung bei gescheiterten. Testkennung des Hinweises jetzt `ingest-partly-converted` (vorher `ingest-error-message` bei erledigten Aufträgen; kein e2e-Test nutzte das).
- Doku: `web/src/pages/README.md` (Brotkrumen, Dateiseite, IngestError, Ingest-Übersicht, Änderungsprotokoll, neuer Abschnitt „Result count“). `theme/README.md` nicht betroffen (keine neuen Tokens, kein neues Icon).

**Wie wurde getestet?**

- Alle Schritte des Web-Jobs aus `ci.yml` in Containern (Projekt `twox-089-web`): lint, typecheck, test (46 Dateien, 923 Tests grün), build, licenses, `api:generate` ohne Unterschied. `components/ui/sourceControls.test.ts` grün.
- Neue/angepasste Vitest-Tests: `ResultCount.test.tsx` (neu), „result count“ in `AuditTrail.test.tsx` (Region bleibt beim Filterwechsel dasselbe Element, leer während des Ladens, Blättern behält die Zahl, Einzahl, Deutsch mit Tausenderpunkt) und `IngestPage.test.tsx`, Brotkrumen in `DocumentPage.test.tsx` (vollständig, Ersatz bei Gerätefehler, Deutsch), `IngestStatus.test.tsx` (gescheitert + teilweise, wartend/laufend mit Einbettung, gescheitert ohne Hinweis).
- e2e wie in `ci.yml` (Projekt `twox-089`, Testkonto per „Create test account“): 73 bestanden. Ergänzt: `files.spec.ts` (Brotkrumen der Dateiseite), `ingest.spec.ts` und `audit.spec.ts` (Ergebniszahl als `role="status"`).
- Sichtprüfung im eingebauten Browser bei 375, 1024 und 1600 px, je hell und dunkel (Dateiseite, `/ingest`, `/audit`, Geräteseite): kein waagrechtes Scrollen (scrollWidth ≤ Fensterbreite), Brotkrumen bei 375 px über mehrere Zeilen umbrochen, lange Namen umbrechen, bei 1024/1600 px zwei Zeilen; Ergebniszahl klein und ruhig zwischen Filter und Liste, Leertext an derselben Stelle; auf `/ingest` mit leerem Filter genau eine `role="status"`-Region. Bildschirmfotos nur lokal.
- `down -v` beider Compose-Projekte mit Exit 0.

**Zweig und Arbeitsverzeichnis**

Zweig `worktree-agent-aee428b1b67e16bbe`, Arbeitsverzeichnis `.claude/worktrees/agent-aee428b1b67e16bbe`.

**Abweichungen**

- Strukturseite nicht auf `ResultCount` umgestellt (gehört zu 083, Datei parallel von 092 berührt); ihre Region hat dieselbe Form und kann später wechseln.
- Gesamtzahl aus der Seitennavigation von Protokoll und Einlesen entfernt (in die Ergebniszahl verschoben), Texte `pagination.total` gestrichen.
- Sichtprüfung: Die Überschrift (`MaskedTitle`, Muster aus 072/078) stand im verborgenen Browserbereich mitten in der Animation; nach Abschluss der Animationen per Skript sichtbar. Bekannt aus der UI-Analyse, nicht durch diesen Auftrag verursacht.
- Für die Sichtprüfung lief die Anmeldung über `twox089.localhost:18089` statt `127.0.0.1`, weil sich die Sitzungs-Cookies mit parallelen Prüfungen auf `127.0.0.1` (andere Ports) überschrieben; dafür stand der Name vorübergehend in `TWOX_ALLOWED_HOSTS` der lokalen, ungetrackten `.env` (danach zurückgesetzt).
- Keine fremden Dateien außerhalb des Auftrags außer Locales (`audit.json`, `ingest.json`, `files.json`) und den drei e2e-Dateien.
