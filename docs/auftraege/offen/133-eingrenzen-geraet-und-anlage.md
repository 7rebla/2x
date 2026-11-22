# Auftrag 133 – Eingrenzen auf Gerät und Anlage

Meilenstein: M3 · Freigabestufe: B · Status: zur Prüfung

Voraussetzung: 132 (Seite Auskunft mit Quellenanzeige) ist auf `main`. Damit gibt es auch 130 (API mit `device` und `plant` im POST-Body) und 131 (`useAnswerStream`).

## Ziel

Das ROADMAP-Merkmal von M3 „Eingrenzen auf Gerät“ (`docs/ROADMAP.md:13`) wird in der Oberfläche sichtbar und verlinkbar. Nach D14 (Vorgabe c) gilt die Eingrenzung auch für Anlagen. Die Geräteseite bekommt einen direkten Einstieg „Frage zu diesem Gerät“. Die Eingrenzung steht in der Adresse, die Frage selbst nie.

## Umfang

1. **Gemeinsame Gruppierung auslagern.** `devicesByPlant` (heute privat in `web/src/pages/SearchPage.tsx:56-75`, zusammen mit `sortedDevices`) zieht nach `web/src/components/devicesByPlant.ts` und wird exportiert (Signatur unverändert: `devicesByPlant(devices: readonly Device[]): { plantId: number; plantName: string; devices: Device[] }[]`). `SearchPage.tsx` importiert sie von dort; sonst ändert sich an der Suchseite nichts. Eigener Unit-Test `web/src/components/devicesByPlant.test.ts` (Sortierung Anlage → Name → Kennung, Gruppenbildung, leere Liste).
2. **Auswahl auf der Seite Auskunft.** Im Formular aus 132 (`web/src/pages/answer/AnswerForm*`) zwei Auswahlfelder nach dem Muster von `SearchForm` (`SearchPage.tsx:77-160`, Bausteine `Select` aus `web/src/components/ui/fields.tsx`):
   - **Gerät:** „Alle Geräte“ plus Geräte gruppiert nach Anlage (`<optgroup>`, Daten über `devicesListOptions()`), Anzeige `Name (Kennung)`.
   - **Anlage:** „Alle Anlagen“ plus Anlagen über `plantsListOptions()` (`web/src/api/generated/@tanstack/react-query.gen.ts:551`), sortiert nach Name.
   - Eine in der Adresse genannte, aber unbekannte Kennung erscheint als eigener Eintrag „Unbekanntes Gerät/Anlage (id)“ wie `form.unknownDevice` in der Suche (`SearchPage.tsx:97,141-143`), statt still verworfen zu werden.
   - Gerät und Anlage schließen sich gegenseitig aus: Wird eines gewählt, wird das andere auf „Alle“ zurückgesetzt. Die Such-API kennt beide Filter (`backend/twox/search/api.py:9-11,79`), die Antwort-API aus 130 nimmt beide an; gesendet wird aber höchstens einer, damit die Bedeutung eindeutig bleibt (siehe Vorgaben).
3. **Vorfilter in der Adresse (E-54-Muster der Suche).** `/ask?device=<id>` bzw. `/ask?plant=<id>`. Lesen und Schreiben über reine Hilfsfunktionen analog `readSearchAddress`/`searchAddressParams` (`SearchPage.tsx:35-53`), mit `parseId` aus `web/src/components/files/format.ts:54`; ungültige Werte zählen als „alle“. Eine Änderung der Auswahl schreibt die Adresse (`setSearchParams`, `replace: true`), ohne eine Frage abzuschicken. `?q=` aus 132 bleibt unverändert erhalten (füllt nur das Feld, D14 i). **Die Frage selbst kommt nie in die Adresse**, sie steht nur im POST-Body.
4. **Chip „Eingegrenzt auf: …“.** Ist ein Vorfilter gesetzt, zeigt die Seite über dem Formular bzw. der Antwort einen Hinweis „Eingegrenzt auf: Gerät *Name (Kennung)*“ bzw. „Eingegrenzt auf: Anlage *Name*“ mit dem Knopf „Eingrenzung aufheben“ (`Button` aus `web/src/components/ui/Button.tsx`, Icon `resetFilter` aus `web/src/icons/names.ts:104`, wie `AuditPage.tsx:90`). Der Knopf entfernt `device`/`plant` aus der Adresse und setzt die Auswahl zurück; eine laufende Antwort wird dabei nicht abgebrochen, die nächste Frage gilt für alle Geräte. Ein Chip mit unbekannter Kennung zeigt die Kennung.
5. **Anfrage.** Der Hook aus 131 bekommt `device` bzw. `plant` als Zahl im Body (Feldnamen wie im Serializer aus 130 und im erzeugten Typ; im erzeugten Client nachsehen, nicht raten). Kein Feld, wenn „alle“.
6. **Einstieg auf der Geräteseite.** In `web/src/pages/DevicePage.tsx` im Kopf neben der Überschrift (Block `DevicePage.tsx:91-109`) ein Link im Stil eines Sekundärknopfs „Frage zu diesem Gerät“ auf `/ask?device=<id>`. Da `Button` nur `<button>` rendert, wird ein `Link` aus `react-router` mit `buttonClasses("secondary", "md")` aus `web/src/components/ui/classes.ts` verwendet; Icon nur über `web/src/icons` mit einem vorhandenen Namen (z. B. `search`), kein neues Icon in diesem Auftrag. Zugänglicher Name mit Gerätename („Frage zu Gerät X stellen“). Sichtbar für die Rolle `read` und höher (gleiche Rolle wie die Route `/ask` aus 132), unabhängig vom Knopf „Bearbeiten“. Ist die KI aus (Status-Endpunkt aus 130), bleibt der Link sichtbar; die Seite Auskunft erklärt dort den Zustand (D10).
7. **Texte** in Deutsch und Englisch: `web/src/locales/{de,en}/answers.json` (Auswahl, Chip, Aufheben, unbekannte Kennung) und `web/src/locales/{de,en}/assets.json` (Knopf auf der Geräteseite; die Gerätetexte liegen dort unter `device`/`actions`, eine Datei `devices.json` gibt es nicht).
8. **Doku:** `web/src/pages/README.md` (Abschnitt zur Seite Auskunft aus 132: Adressparameter `device`, `plant`; Einstieg von der Geräteseite).

## Nicht-Ziele

- Keine Änderung am Backend, an der Antwort-API, am OpenAPI-Schema oder am erzeugten Client (`web/openapi/schema.yml`, `web/src/api/generated/**`).
- Keine Mehrfachauswahl (mehrere Geräte oder Anlagen gleichzeitig), kein Filter nach Standort oder Bereich.
- Kein Navigationseintrag (Auftrag 134), keine Änderung an `navigation.ts`, `UserMenu.tsx`, `nav.json`, `web/e2e/navigation.spec.ts`.
- Kein neues Icon, keine Änderung an `web/src/icons/names.ts` (132 und 134 ändern die Datei).
- Kein Umbau von Antwortkarte, Quellenliste oder `useAnswerStream` über das Durchreichen von `device`/`plant` hinaus.
- `IngestPage.tsx` hat eine eigene Kopie von `devicesByPlant` (`IngestPage.tsx:135-149`); sie bleibt in diesem Auftrag unberührt (Folgepunkt im Kurzbericht vermerken).
- Keine neue Abhängigkeit.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/components/devicesByPlant.ts` (neu) und `web/src/components/devicesByPlant.test.ts` (neu)
- `web/src/pages/SearchPage.tsx` (nur Auslagerung und Import)
- `web/src/pages/answer/AnswerForm*` (aus 132; nur Eingrenzung) und gegebenenfalls eine kleine Datei für Adresse und Chip unter `web/src/pages/answer/` (z. B. `scope.ts`, `ScopeChip.tsx`) mit Tests
- `web/src/pages/AnswerPage.tsx` nur, soweit Adresse und Chip dort verdrahtet werden müssen; `AnswerPage.test.tsx` erweitern
- `web/src/pages/DevicePage.tsx` und `web/src/pages/DevicePage.test.tsx`
- `web/src/locales/{de,en}/answers.json`, `web/src/locales/{de,en}/assets.json`
- `web/src/pages/README.md`
- optional `web/e2e/` nur dann, wenn 137 noch nicht begonnen ist und ein eigener kleiner Fall nötig erscheint – sonst gehören Browserfälle zu 137 (`web/e2e/answer.spec.ts`)

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Alle Prüfungen aus `.github/workflows/ci.yml` sind grün, insbesondere der Web-Job: `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`, `npm run licenses` (jeweils über `docker compose -f "$WEB_COMPOSE" run --rm web-dev …`, `ci.yml:118-133`), `api:generate` ohne Unterschied; e2e wie in `ci.yml:211-250` grün.
2. Vitest: Ein Vorfilter aus der Adresse (`?device=`, `?plant=`) ist in der Auswahl gesetzt, als Chip mit Namen sichtbar und lässt sich mit „Eingrenzung aufheben“ aufheben; danach sind `device` und `plant` nicht mehr in der Adresse.
3. Vitest: Die abgeschickte Anfrage trägt `device` bzw. `plant` im Body (fetch-Stub), bei „alle“ keines der Felder; die Frage steht nie in der Adresse (Prüfung von `location.search` nach dem Absenden).
4. Vitest: Gerät und Anlage schließen sich aus; die Wahl des einen setzt das andere zurück.
5. Vitest: Ein ungültiger Wert (`?device=abc`, `?device=0`) zählt als „alle“, eine unbekannte Kennung erscheint als eigener Eintrag und im Chip.
6. Vitest: Der Knopf auf der Geräteseite verlinkt auf `/ask?device=<id>` und hat einen zugänglichen Namen mit dem Gerätenamen; er erscheint für die Rolle `read` und `manage`.
7. Unit-Test für `devicesByPlant` (Sortierung, Gruppen, leere Liste).
8. Die bestehenden Tests der Suchseite (`SearchPage.test.tsx`, `web/e2e/search.spec.ts`) sind unverändert grün; `git diff` an `SearchPage.tsx` zeigt nur Auslagerung und Import.
9. `web/src/i18n.test.ts` ist grün (de und en mit denselben Schlüsseln).
10. Keine Änderung an `package.json` oder `package-lock.json`.
11. Sichtprüfung im eigenen Compose-Projekt im Browser bei 375, 768 und 1280 px, hell und dunkel, de und en: Auswahlfelder brechen bei 375 px um, keine waagrechte Überbreite, Chip lesbar, Knopf auf der Geräteseite neben „Bearbeiten“ ohne Überlauf. Tastatur: Auswahl, Chip-Knopf und Link erreichbar, Fokus sichtbar. Beobachtungen im Kurzbericht (Bildschirmfotos nur lokal, nicht eingecheckt).
12. `down -v` der eigenen Compose-Projekte endet mit Exit 0.

## Vorgaben und Hinweise

- **Herkunft:** M3 „Auskunft mit Quellen“, Gesamtplan der Leitstelle; Merkmal „Eingrenzen auf Gerät“ aus `docs/ROADMAP.md:13` und Startunterlage Abschnitt 9. Erweiterung auf Anlagen nach D14 (Vorgabe c, Empfehlung der Leitstelle).
- **Adresse statt Zustand (E-54-Muster der Suche):** Filter in die Adresse, damit die Eingrenzung verlinkbar, neu ladbar und mit „Zurück“ erreichbar ist (`SearchPage.tsx:4-7`). Die Frage gehört dagegen nur in den POST-Body (130); sie darf weder in der Adresse noch im Verlauf des Browsers landen – außer dem bewusst vorbelegten `?q=` aus 132, das nur das Feld füllt und nie automatisch absendet (D14 i).
- **Gerät oder Anlage, nicht beides:** Die Such-API verknüpft mehrere Filter mit UND (`backend/twox/search/api.py:9-11`); eine Kombination aus Gerät und fremder Anlage ergäbe stets „nichts gefunden“ und würde die Kontrollfrage verfälschen. Darum höchstens ein Filter je Anfrage.
- **Fundorte (E-55):** Ein Abschnitt kann an mehreren Geräten liegen. Die Eingrenzung filtert serverseitig (125, 130); die Oberfläche filtert die Quellen nicht nachträglich.
- **KI aus (E-59, D10):** Die Auswahl und der Chip bleiben sichtbar, das Formular ist nach 132 gesperrt; „KI nicht aktiviert“ ist ein neutraler Zustand, kein Fehler.
- **Gestaltung:** Tokens aus 070, Icons nur über `web/src/icons` (071), Bausteine aus `web/src/components/ui/` (077), Steuerhöhen 36/28 px, Metadaten 13–14 px (E-65 Punkt 5), Gestaltung D1 abgenommen (E-68). Keine Animation über das Vorhandene hinaus (E-52).
- **Barrierefreiheit:** Beschriftete Auswahlfelder (`label`/`htmlFor` mit `useId`), der Chip ist kein Live-Bereich; „Eingrenzung aufheben“ ist ein echter Knopf mit Text. Kein Fokuswechsel beim Ändern der Auswahl.
- **Abgrenzung zu parallelen Aufträgen:** 134 (Navigation) läuft gleichzeitig und ändert `navigation.ts`, `UserMenu.tsx`, `nav.json`, `icons/names.ts`, `e2e/navigation.spec.ts` – diese Dateien hier nicht anfassen. 137 (Abnahmetests) baut auf diesem Auftrag auf und prüft den Eingrenzungs-Chip im Browser; stabile `data-testid` vergeben (z. B. `answer-device`, `answer-plant`, `answer-scope`, `answer-scope-reset`, `device-ask`) und im Kurzbericht nennen.
- **Leitplanken:** Keine Herstellertexte und keine echten Betriebsdaten in Tests; Testgeräte und -anlagen frei erfunden benennen wie in den bestehenden Vitest-Fällen. Keine Personennamen, keine lokalen Pfade mit Benutzernamen in Dateien oder Commits. Alles über `docker compose`, nichts unter Windows installieren.
- Texte in Deutsch und Englisch; Bezeichner, Kommentare und Doku in `web/src/pages/README.md` auf Englisch.

## Fragen an a7 (mit Optionen und Empfehlung)

- **D14 Eingrenzung (c oder d):** (c) Gerät und Anlage, (d) nur Gerät wie in der ROADMAP. Empfehlung: (c) – die Such-API kann Anlagen schon filtern, der Mehraufwand ist klein. Der Auftrag ist mit der Vorgabe (c) startbar; entscheidet a7 (d), entfällt nur die Anlagenauswahl samt Chip-Variante.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Was wurde gebaut?**

- `web/src/components/devicesByPlant.ts` (neu): `devicesByPlant` samt privatem `sortedDevices` aus `SearchPage.tsx` ausgelagert, Signatur unverändert. `SearchPage.tsx` importiert nur noch (Diff: Import und Löschung, sonst nichts; der Typimport `Device` entfällt dort, weil unbenutzt).
- `web/src/pages/answer/scope.ts` (neu): reine Hilfsfunktionen `readScopeAddress` (liest `?device=`/`?plant=` mit `parseId`; ungültig → „alle“; stehen beide gültig in der Adresse, gewinnt das Gerät), `withScopeAddress` (setzt höchstens eins, lässt `?q=` und alles andere stehen), `chooseDevice`/`choosePlant` (die Wahl des einen setzt das andere zurück), `ALL_DEVICES`.
- `AnswerForm.tsx`: neue Props `scope` und `onScopeChange`; Baustein `ScopeChoice` mit zwei beschrifteten `Select` (`useId`): „Gerät“ (Alle Geräte + `<optgroup>` je Anlage, `Name (Kennung)`) und „Anlage“ (Alle Anlagen + Anlagen nach Name, Anzeige `Name (Kennung)` zur Unterscheidung gleichnamiger Anlagen). Unbekannte Kennung aus der Adresse als eigener Eintrag „Unbekanntes Gerät (id)“/„Unbekannte Anlage (id)“. `answerScopeOf()` macht daraus `AnswerScope`; der Body trägt `device: [id]` bzw. `plant: [id]` (im erzeugten Typ `AnswerRequest` sind beide `Array<number>`), bei „alle“ keines. Die Auswahl bleibt bei KI aus und während einer laufenden Antwort bedienbar; Ladefehler der Listen über `ErrorMessage`.
- `web/src/pages/answer/ScopeChip.tsx` (neu): Kasten „Eingegrenzt auf: Gerät **Name (Kennung)**“ bzw. „Anlage **Name**“, unbekannt → Text mit Kennung, während die Liste lädt „Nr. id“. Knopf „Eingrenzung aufheben“ (`Button` size sm, Icon `resetFilter`). Kein Live-Bereich.
- `AnswerPage.tsx`: liest die Eingrenzung aus der Adresse, schreibt Änderungen mit `setSearchParams(…, { replace: true })`; Aufheben bricht eine laufende Antwort nicht ab. Es wird nie etwas automatisch abgeschickt, die Frage kommt nie in die Adresse.
- `DevicePage.tsx`: im Kopf neben „Bearbeiten“ ein `Link` mit `buttonClasses("secondary", "md")`, Icon `search`, Text „Frage zu diesem Gerät“, zugänglicher Name „Frage zu Gerät X stellen“, Ziel `/ask?device=<id>` (`askPath()`), für `read` und `manage` (`canRead`).
- Texte de/en in `answers.json` (`scope.*`) und `assets.json` (`actions.askDevice`, `actions.askDeviceNamed`); Doku in `web/src/pages/README.md` (Abschnitte „Ask“ und Geräteseite).
- Stabile `data-testid` für 137: `answer-device`, `answer-plant`, `answer-scope`, `answer-scope-name`, `answer-scope-reset`, `device-ask`.

**Wie wurde getestet?** (Compose-Projekte `twox-133` und `twox-133-web`, API-Port 18133)

- 0: `docker version` und `docker compose version` Exit 0.
- 1: Web-Job: `npm ci`, `lint`, `typecheck`, `test` (56 Dateien, 1120 Tests), `build`, `licenses` grün; `api:generate` ohne Unterschied. e2e wie in `ci.yml`: 85 bestanden, 1 übersprungen (`m2-acceptance.spec.ts:487`, lokaler Teil mit Herstellerunterlagen, wie bisher). Nach der Sichtprüfung wurde nur noch eine Klasse im Chip geändert (`min-w-48`); danach lint, typecheck und Vitest erneut grün, e2e nicht erneut gelaufen.
- 2–5: `AnswerPage.test.tsx`, neuer Block „limit to one device or one plant“ (15 Fälle): Vorfilter `?device=`/`?plant=` in Auswahl und Chip mit Namen, Aufheben entfernt beide aus der Adresse (und behält `?q=`); Body mit `device`/`plant`, bei „alle“ ohne, `location.search` nach dem Absenden ohne Frage; Auswahl schreibt die Adresse per REPLACE ohne POST; gegenseitiger Ausschluss; `abc`, `0`, `-1`, `1.5` zählen als „alle“; unbekannte Gerät- und Anlagenkennung als eigener Eintrag und im Chip; Aufheben bricht laufende Antwort nicht ab; bei KI aus bleiben Auswahl und Chip. Dazu `answer/scope.test.ts` (15 Fälle).
- 6: `DevicePage.test.tsx`: Link `/ask?device=1000` mit Namen „Ask a question about device Test controller“ für `read` und `manage`, deutscher Name, Klick öffnet `/ask?device=1000` ohne POST.
- 7: `components/devicesByPlant.test.ts` (Sortierung Anlage → Name → Kennung, Gruppen, leere Liste, Eingabe unverändert).
- 8: `SearchPage.test.tsx` und `e2e/search.spec.ts` unverändert grün.
- 9: `i18n.test.ts` grün.
- 10: `package.json`/`package-lock.json` unverändert.
- 11: Sichtprüfung im eingebauten Browser auf `twox133.localhost:18133` mit den e2e-Daten (KI an, ohne Chat-Modell → „Auskunft derzeit nicht verfügbar“): 375 px hell de, 375 px dunkel en, 768 px hell en, 1280 px dunkel de und hell en. Keine waagrechte Überbreite (`scrollWidth` = Breite). Bei 375 px stehen die Auswahlfelder untereinander; der Chip quetschte den Text zunächst in eine schmale Spalte neben den Knopf – behoben (Text mindestens 12rem, der Knopf bricht darunter um). Geräteseite: bei 1280 px „Frage zu diesem Gerät“ neben „Bearbeiten“, bei 375 px untereinander, ohne Überlauf. Tastatur: Chip-Knopf, Geräteauswahl, Anlagenauswahl und Link nacheinander erreichbar, `:focus-visible` mit 2 px Rahmen. Auswahl eines Geräts bei gesetzter Anlage setzt die Anlage zurück, Adresse `?device=44`.
- 12: `down -v` beider Projekte Exit 0.

**Zweig und Arbeitsverzeichnis:** `worktree-agent-a0a6979cd04c9c3c2`, `.claude/worktrees/agent-a0a6979cd04c9c3c2`.

**Abweichungen und Hinweise**

- Keine Datei außerhalb der „Betroffenen Bereiche“ geändert; kein e2e-Fall ergänzt (Browserfälle gehören zu 137).
- Stehen `device` und `plant` beide in der Adresse, gewinnt das Gerät (der Auftrag nennt den Fall nicht; so bleibt die Bedeutung eindeutig).
- Optionen der Anlagenauswahl zeigen `Name (Kennung)`, der Chip nach Vorgabe nur den Namen.
- Der zugängliche Name des Links („Frage zu Gerät X stellen“) enthält den sichtbaren Text „Frage zu diesem Gerät“ nicht wörtlich (wie bei „Bearbeiten“/„Gerät X bearbeiten“); nach Vorgabe des Auftrags so umgesetzt.
- `buttonClasses` setzt den Hover-Hintergrund nur über `enabled:`; am Link (kein `:enabled`) gibt es daher keinen Hover-Wechsel. Nicht geändert, weil `extra` nur für Layout gedacht ist.
- Aufheben und Auswahländerung ersetzen den Verlaufseintrag (`replace`); „Zurück“ führt so zur Geräteseite zurück.
- Folgepunkt: `IngestPage.tsx:135-149` hat noch eine eigene Kopie von `devicesByPlant` und kann auf `components/devicesByPlant.ts` umgestellt werden.

**Nachbesserung (auf Hinweis der Leitstelle)**

- `main` (mit 134) konfliktfrei in den Zweig zusammengeführt.
- Label in Name (WCAG 2.5.3): Der zugängliche Name des Links auf der Geräteseite beginnt jetzt mit dem sichtbaren Text, de „Frage zu diesem Gerät: {{name}}“, en „Ask about this device: {{name}}“ (`actions.askDeviceNamed`). `DevicePage.test.tsx` prüft, dass der Name mit dem sichtbaren Text beginnt und den Gerätenamen enthält. Der Chip-Knopf „Eingrenzung aufheben“ hat kein `aria-label`, sein Name ist der sichtbare Text; `AnswerPage.test.tsx` prüft das jetzt.
- Hover am Link: `buttonClasses("secondary", "md", "hover:bg-surface-muted")` nur in `DevicePage.tsx`, gleiche Farbe wie `enabled:hover` des Sekundärknopfs; der Baustein bleibt unverändert. README nachgezogen.
- Prüfungen danach: Web-Job grün (`npm ci`, lint, typecheck, test mit 1132 Tests, build, licenses, `api:generate` ohne Unterschied); e2e wie in `ci.yml`: 88 bestanden, 1 übersprungen (`m2-acceptance` lokal, wie bisher); `down -v` von `twox-133` und `twox-133-web` Exit 0.
