# Auftrag 088 – Einheitliche Dateiauswahl

Meilenstein: Gestaltung (D1) · Freigabestufe: B · Status: zur Prüfung

Voraussetzung: 077 ist auf `main`.

## Ziel

Die native Dateiauswahl („Datei auswählen – Keine ausgewählt“) passt nicht zu den übrigen Steuerelementen und ist in dunkel kaum als Bedienelement erkennbar; „Hochladen“ ist aktiv, auch wenn keine Datei gewählt ist.

## Umfang

- Baustein `components/ui/FileInput` (versteckter Input, Sekundärknopf, gewählter Dateiname, optional Ablegen per Drag & Drop), verwendet in Import, Upload am Gerät und neuer Version.
- Primärknopf deaktiviert mit Hinweis („Erst eine Datei wählen“), solange keine Datei gewählt ist.
- Tests (Vitest; e2e, wo Layout oder Bedienung sich ändern) für das neue Verhalten; bestehende Tests angepasst, nicht abgeschwächt.
- Doku: `web/src/pages/README.md` bzw. `web/src/theme/README.md` nachziehen, wo betroffen.

## Nicht-Ziele

- Keine neue Abhängigkeit, keine Änderung an API oder Backend.
- Nur der genannte Bereich; andere Befunde der UI-Analyse haben eigene Aufträge.

## Betroffene Bereiche (Ordner, Dateien)

- neu `web/src/components/ui/FileInput.tsx`, `web/src/components/files/UploadForm.tsx`, `web/src/pages/ImportPage.tsx`, Tests, `locales`

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

- **Was wurde gebaut?**
  - Neuer Baustein `web/src/components/ui/FileInput.tsx`: das native `<input type="file">` bleibt im Dokument, visuell versteckt (`sr-only`), aber fokussierbar und über das Label des Aufrufers benannt (Tastatur, Screenreader, Formulardaten und `setInputFiles` unverändert). Sichtbar: gestrichelter Rahmen (`line-strong`, bei Fehler `danger`), darin ein Knopf im Aussehen eines sekundären md-Knopfs („Datei wählen …", Icon `document`, 36 px, Fokusring des Inputs über `peer-focus-visible`, gesperrt über `peer-disabled`), der gewählte Dateiname bzw. „Keine Datei gewählt" (mind. 160 px, rutscht am Telefon unter den Knopf, lange Namen mit Auslassung und Tooltip) und ab 640 px „oder hier ablegen". Ablegen per Drag & Drop: erste Datei wird übernommen und auch in das Input gesetzt; beim Darüberziehen `accent` auf `accent-soft`, Nebentext dann in `fg` (Kontrast gemessen). Keine Animation (E-52 unberührt).
  - Klassen `fileButtonClasses`, `fileDropClasses` in `components/ui/classes.ts`; Texte unter `fileInput` in `locales/{de,en}/common.json` (inkl. „Erst eine Datei wählen." / „Choose a file first.").
  - `UploadForm.tsx` (neue Datei am Gerät, neue Version) und `ImportPage.tsx` nutzen `FileInput`. Der Primärknopf („Hochladen", „Probelauf starten") ist gesperrt, solange keine Datei gewählt ist, mit dem Hinweis daneben (per `aria-describedby` verknüpft). Nach jedem Hochladen ist die Auswahl wieder leer. Die bisherige Prüfung „Bitte eine Datei wählen." bleibt als Schutz für ein Absenden auf anderem Weg.
  - `sourceControls.test.ts`: native Inputs nur noch für Checkboxen und Radiobuttons; neue Regel „Dateien nur über FileInput".
  - Doku: `web/src/components/ui/README.md` (Abschnitt „File chooser", Tabellen, Tests), `web/src/pages/README.md` (Dateien, Import). `theme/README.md` war nicht betroffen.
- **Wie wurde getestet?**
  - Kriterium 0: `docker version` und `docker compose version` Exit 0.
  - Kriterium 1: Web-Job im Projekt `twox-088-web`: lint, typecheck, test (42 Dateien, 806 Tests), build, licenses grün; `api:generate` ohne Unterschied in `web/openapi` und `web/src/api`.
  - Kriterium 2: e2e wie in `ci.yml` im Projekt `twox-088` (API-Port 18088): 56 bestanden, 1 übersprungen (M2-Abnahme, lokaler Teil mit Testfabrik – bereits vorher übersprungen).
  - Neue/angepasste Tests: `FileInput.test.tsx` (9 Fälle: verstecktes, beschriftetes, fokussierbares Input; Knopf; Klick öffnet Auswahl; Name; Ablegen; leeres Ablegen; gesperrt; Fehlerzustand; Deutsch). `DeviceFiles.test.tsx`: „asks for a file before calling the API" prüft jetzt gesperrten Knopf, Hinweis, `aria-describedby` und weiterhin die Fehlermeldung bei Absenden ohne Datei (per `submit`) ohne API-Aufruf; neu: deutsche Texte, Hochladen einer abgelegten Datei (gesendeter Inhalt geprüft, danach leer und gesperrt). `ImportPage.test.tsx`: Hinweis und Name im ersten Fall, neu: abgelegte CSV geht in den Probelauf. e2e: `files.spec.ts` (gesperrt mit Hinweis, Name nach Auswahl, leer nach Hochladen), `import.spec.ts` (gesperrt mit Hinweis; neuer Test: echtes Ablegen per `DataTransfer` im Browser bis zum Probelauf). Alle bestehenden `setInputFiles`-Aufrufe über das Label blieben unverändert.
  - Kriterium 3: Sichtprüfung im eingebauten Browser gegen das eigene Projekt (Testkonto aus `.env.example`), Import und Geräteseite: 1600 px hell (Rahmen, Knopf, Name und „oder hier ablegen" in einer Zeile; abgelegte Datei mit langem Namen wird abgeschnitten, Knopf aktiv, Hinweis weg, das Input hält die Datei), 1024 px dunkel (Knopf klar als Bedienelement erkennbar, Fokusring 2 px Akzent sichtbar, Höhe 36 px, kein waagrechtes Scrollen), 375 px dunkel (Name rutscht unter den Knopf, Ablege-Hinweis ausgeblendet, „Hochladen" gesperrt mit Hinweis darunter, kein waagrechtes Scrollen). Befund bei 375 px – zuerst „Keine …" abgeschnitten – wurde behoben (Mindestbreite des Namens). Bildschirmfotos nur lokal.
  - Kriterium 4: `down -v` von `twox-088` und `twox-088-web` Exit 0.
- **Zweig und Arbeitsverzeichnis:** `worktree-agent-a7a1cc8e77f96cce6`, `.claude/worktrees/agent-a7a1cc8e77f96cce6`.
- **Abweichungen:**
  - Zusätzlich zu den genannten Dateien berührt: `components/ui/classes.ts`, `components/ui/README.md`, `components/ui/sourceControls.test.ts` (Regel angepasst wie vom Auftrag verlangt), `components/DeviceFiles.test.tsx`, `pages/ImportPage.test.tsx`, `e2e/files.spec.ts`, `e2e/import.spec.ts`, `pages/README.md`. `DocumentPage.test.tsx` blieb unberührt (Form der neuen Version ist dieselbe Komponente, e2e deckt sie ab).
  - Kein neues Icon: der Knopf nutzt das vorhandene `document`.
  - Hinweis zur Sichtprüfung: Unter `127.0.0.1` wurde die Anmeldung wiederholt verloren, vermutlich weil parallele Projekte auf anderen Ports desselben Hosts dasselbe Sitzungs-Cookie setzen (Cookies unterscheiden keine Ports). Unter `localhost:18088` ging es. Kein Fehler dieses Auftrags.
