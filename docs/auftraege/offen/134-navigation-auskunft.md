# Auftrag 134 – Navigation Auskunft

Meilenstein: M3 · Freigabestufe: C · Status: offen

Voraussetzung: 132 (Seite Auskunft unter `/ask`) ist auf `main`. Start erst nach Entscheidung von a7 zu D13 und D14 (Icon); siehe „Fragen an a7“.

## Ziel

Die Auskunft (M3, „Frage und Antwort, Quellenanzeige, Eingrenzen auf Gerät“, `docs/ROADMAP.md:13`) bekommt einen eigenen Eintrag in der Hauptnavigation. Die abgenommene Kopfleiste (E-65 Punkt 3, E-68, Auftrag 082) bleibt dabei ab 768 px einzeilig, ohne Überlauf der Leiste und der Seite und 76 px hoch.

Heute bleiben bei 768 px auf Deutsch mit einem Benutzernamen, der den Knopf ausreizt (192 px), nur 25 px frei (`docs/auftraege/erledigt/082-navigation-schmal.md:86`). Ein achter Eintrag passt dort nicht. Nach D13 (Empfehlung a) zieht deshalb der Selbsttest aus der Kopfleiste ins Benutzermenü, neben die Einstellungen. Die Adresse `/selftest` bleibt.

## Umfang

1. **Eintrag „Auskunft“** in `web/src/navigation.ts` (Liste `navigation`, heute Z. 39-51):
   - `{ path: "/ask", textKey: "ask", icon: "answer", requires: "read" }`.
   - Position: direkt nach „Suche“ (`/search`), weil beide Einstiege in die Unterlagen sind. Weicht der Bearbeiter davon ab, nennt er den Grund im Kurzbericht.
   - Der Eintrag `selftest` (heute Z. 50) wird aus der Liste entfernt. Damit gilt für `/selftest` über `requiredRole()` (Z. 59-61) die Rolle `read`, wie bisher. Das ist zu prüfen: Die Seite bleibt für `read` und `manage` erreichbar und ohne Rolle gesperrt.
   - Kommentar über dem neuen Eintrag mit Verweis auf Auftrag 132 bzw. 134, wie bei den übrigen Einträgen.
2. **Texte** in `web/src/locales/de/nav.json` und `web/src/locales/en/nav.json`:
   - Langtext `ask`: de „Auskunft“, en „Ask“.
   - Kurztext `short.ask`: de „Auskunft“, en „Ask“. Die Regel aus `web/src/pages/README.md:48-50` gilt: höchstens zehn Zeichen und ein Teil des vollen Textes.
   - `short.selftest` entfällt, weil der Selbsttest kein Navigationseintrag mehr ist (`NavEntryKey` in `navigation.ts:20` verlangt einen Kurztext nur für Einträge). Der Langtext `selftest` bleibt, er wird für den Link im Benutzermenü und den Seitentitel gebraucht.
3. **Icon `answer`** in `web/src/icons/names.ts`, Abschnitt Navigation (Z. 66-76):
   - Bis zu einer eigenen Zeichnung ein Lucide-Icon ohne Sprechblase und ohne Funkeln (B6 bzw. D14 Option g). Kein `MessageCircle`, `MessageSquare`, `Bot`, `Sparkles` oder Ähnliches.
   - Vorschlag: ein Icon, das „Frage mit Beleg“ zeigt, etwa `FileQuestionMark` (oder der Name, unter dem Lucide 1.77.0 dieses Icon führt) oder `BookOpenCheck`. Der Bearbeiter prüft, welche Namen es in der installierten Version gibt (`web/node_modules/lucide-react`, nur lesend), und begründet die Wahl im Kurzbericht.
   - Kommentar `// NAV-06 (library icon until an own one is drawn, work order 134)` nach dem Muster von `map` (Z. 68). Das Icon muss sich von allen anderen unterscheiden; das prüft `icons.test.tsx` schon heute.
   - `web/src/icons/README.md` Z. 31 (Tabelle der Navigation) um `answer` ergänzen.
   - Hat 132 bereits Icons in `names.ts` eingetragen (`noEvidence`, `contradiction`), bleiben sie unverändert. Es wird nur `answer` hinzugefügt.
4. **Selbsttest im Benutzermenü** (`web/src/components/UserMenu.tsx`, `UserMenuContent`, Z. 132-140):
   - Ein zweiter Link nach dem Muster des Einstellungs-Links: `NavLink` auf `/selftest`, Icon `selftest`, Text `nav:selftest`, `data-testid="selftest-link"`.
   - Sichtbar wie die Einstellungen nur mit Rolle (`hasRole(user.role, "read")`).
   - Reihenfolge: Einstellungen, dann Selbsttest. `aria-current="page"` setzt `NavLink` von selbst, wenn `/selftest` offen ist.
   - Der Inhalt erscheint damit auch im Menü unter 768 px, weil `Layout` dort `UserMenuContent` zeigt (082).
5. **Tests anpassen und ergänzen.** Bestehende Prüfungen werden angepasst und nicht abgeschwächt.
   - `web/e2e/navigation.spec.ts`:
     - `ENGLISH_ENTRIES`, `GERMAN_ENTRIES`, `ENGLISH_SHORT` und `GERMAN_SHORT` (Z. 79-82) bekommen den neuen Eintrag und verlieren den Selbsttest.
     - Der erste Test (Z. 25-47) klickt heute in der Leiste auf „Self-test“. Er wechselt auf einen Weg über das Benutzermenü, oder ein neuer Test deckt das ab. Die Prüfungen von `worker-result` und `database-version` bleiben erhalten.
     - Die Einzeilen-Prüfung (Z. 150-209) läuft weiter bei 1280, 1024 und 768 px in de und en. Wo dort auf den Eintrag „Self-test“ bzw. „Selbsttest“ gewartet wird (Z. 159, 167), tritt der letzte Eintrag der Leiste an seine Stelle.
     - Die Prüfung bei 768 px mit langem Benutzernamen (Z. 211-249) muss mit sieben Einträgen bestehen (Auskunft statt Selbsttest, die Zahl bleibt wie heute): Leiste endet vor dem Knopf, `overflow <= 0`, `free >= 0`, eine Zeile, Kopf 76 px, kein Überlauf der Seite. Neu dazu kommt dieselbe Prüfung auf Englisch. Die freie Breite in de und en steht als Anmerkung (`annotations`) im Testbericht und im Kurzbericht.
     - Die Telefonprüfung bei 375 px (Z. 263-404) zählt die Einträge über die Konstanten mit und klickt heute „Self-test“ in der Liste (Z. 315-321). Dieser Schritt geht stattdessen über den Selbsttest-Link im Benutzerteil des Felds oder über „Ask“. Die Tastaturprüfung (Z. 324-375) wird an die neue Reihenfolge angepasst; der Weg zu „Search“ zählt drei Tab-Schritte (Z. 346-349).
     - Neu: ein Test, dass das Benutzermenü ab 768 px den Link „Self-test“ enthält, dass er `/selftest` öffnet und das Menü danach geschlossen ist.
     - Neu: ein Test, dass der Eintrag „Ask“ `/ask` öffnet, `aria-current="page"` trägt und die Überschrift der Seite fokussiert ist (Muster 078, wie Z. 315-319).
   - Weitere e2e-Dateien, die heute den Navigationseintrag „Self-test“ anklicken, laufen sonst rot. Sie werden minimal angepasst, ohne die Aussage des Tests zu ändern:
     - `web/e2e/accessibility.spec.ts:34` und `:49-51`: ein anderer Eintrag, z. B. „Ask“ mit dem Titel aus 132, oder der Weg über das Benutzermenü.
     - `web/e2e/settings.spec.ts:136-137`: Breitenvergleich beim Seitenwechsel über einen anderen Eintrag.
   - `web/src/components/Layout.test.tsx` (Vitest):
     - Die Kurztext-Listen (Z. 101-104, 344-347) werden angepasst.
     - Die Prüfung „marks the current entry“ (Z. 108-115) und der Menütest (Z. 251-256) nutzen heute `/selftest`. Sie wechseln auf einen Eintrag, der in der Leiste bleibt, z. B. `/ask`.
     - Neu: `reader` (Z. 121) und `manager` sehen „Auskunft“. Ohne Rolle gibt es weder den Eintrag noch den Selbsttest-Link.
   - Ein neuer oder ergänzter Vitest für `UserMenu`: der Selbsttest-Link ist bei Rolle `read` und `manage` da und fehlt ohne Rolle. Er hat den deutschen und den englischen Text. Hat `UserMenu` noch keine eigene Testdatei, entsteht `web/src/components/UserMenu.test.tsx`; sonst wird die vorhandene ergänzt.
6. **Doku:** In `web/src/pages/README.md` (Abschnitt „Frame and navigation“, Z. 41-64) die Zahl der Einträge nachziehen. Dazu Auskunft als Eintrag, Selbsttest im Benutzermenü, Kurztexte und die gemessene freie Breite bei 768 px. Z. 46 („the seven entries of M2“) wird entsprechend angepasst.

## Nicht-Ziele

- Keine Änderung an der Seite Auskunft selbst (`web/src/pages/AnswerPage.tsx`, `web/src/pages/answer/*`, 132), an der Eingrenzung (133) oder an der Antwort-API (130).
- Kein Link „Als Frage stellen“ unter den Suchtreffern. Der Gesamtplan nennt ihn als optional. Er würde die Suchseite berühren, die 133 gleichzeitig ändert (`SearchPage.tsx`); deshalb kommt er als eigener kleiner Folgeauftrag nach 133.
- Keine eigene Zeichnung für NAV-06 (`docs/design/icon-bedarfsanalyse.md:319`, `:634`). Sie folgt nur nach D14 Option h als eigener Auftrag.
- Keine Assistentenfigur (D17, nach der Abnahme von M3).
- Keine Änderung an `/selftest`, `SelftestPage.tsx`, an Routen (`web/src/routes.tsx`) oder an Rollen (E-40). Anmeldung und Rechte bleiben unberührt (Stufe-C-Thema außerhalb dieses Auftrags).
- Kein neuer Seitentitel und kein neuer Text der Seite Auskunft (Namespace `answers` gehört 132).
- Keine Änderung an Backend, API oder Schema; keine neue Abhängigkeit.
- Keine Änderung der Breakpoints, Abstände oder Schriftgrößen der Kopfleiste. Passt der Eintrag nur mit solchen Änderungen, ist das eine Rückfrage an a7, keine eigenmächtige Lösung.

## Betroffene Bereiche (Ordner, Dateien)

Vorhanden, werden geändert:

- `web/src/navigation.ts`
- `web/src/locales/de/nav.json`, `web/src/locales/en/nav.json`
- `web/src/components/UserMenu.tsx` (nur `UserMenuContent`: Selbsttest-Link)
- `web/src/icons/names.ts` (nur `answer`), `web/src/icons/README.md` (Navigationszeile)
- `web/e2e/navigation.spec.ts`
- `web/e2e/accessibility.spec.ts`, `web/e2e/settings.spec.ts` (nur die Stellen, die den Navigationseintrag „Self-test“ anklicken)
- `web/src/components/Layout.test.tsx`
- `web/src/pages/README.md` (Abschnitt „Frame and navigation“)

Neu, falls noch nicht vorhanden:

- `web/src/components/UserMenu.test.tsx`

Nicht berühren: `web/src/pages/AnswerPage.tsx`, `web/src/pages/answer/**`, `web/src/pages/SearchPage.tsx`, `web/src/pages/DevicePage.tsx`, `web/src/components/devicesByPlant.ts`, `web/src/locales/*/answers.json` (132, 133).

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Web-Job aus `.github/workflows/ci.yml` grün: `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`, `npm run licenses` über `docker compose -f "$WEB_COMPOSE" run --rm web-dev …`. Dazu `npm run api:generate` ohne Unterschied unter `web/openapi` und `web/src/api`.
2. e2e wie in `ci.yml` grün (`docker compose --profile e2e run --rm e2e`). Erlaubt ist nur das Überspringen der lokalen Abnahmeteile (`TWOX_M2_LOCAL`, ggf. `TWOX_M3_LOCAL`).
3. Insbesondere `docker compose --profile e2e run --rm e2e npx playwright test e2e/navigation.spec.ts` ist grün, und zwar so:
   - bei 768, 1024 und 1280 px in de und en eine Zeile, `overflow <= 0`, `free >= 0`, Kopf 76 px, kein Überlauf der Seite;
   - bei 768 px mit Rolle `manage` und langem Benutzernamen (Knopf 192 px) in de **und** en kein Überlauf und `free >= 0`;
   - die gemessenen freien Breiten stehen im Kurzbericht.
4. Die Auskunft ist für die Rollen `read` und `manage` über die Navigation erreichbar (Vitest mit `reader` und `manager`). Ohne Rolle erscheint der Eintrag nicht.
5. Der Selbsttest ist über das Benutzermenü erreichbar: ab 768 px im Feld des Benutzerknopfs, unter 768 px im Menüfeld (e2e). `/selftest` öffnet sich unverändert direkt (`selftest.spec.ts`, `login.spec.ts`, `i18n.spec.ts` unverändert grün).
6. Die Prüfungen mit Tastatur (Menü unter 768 px, Fokus auf der Überschrift nach Seitenwechsel) und die Zugänglichkeitsprüfungen in `web/e2e/accessibility.spec.ts` (Rollen, Namen, Fokus; ohne axe, keine neue Abhängigkeit) sind ohne Befund.
7. Das Icon `answer` steht immer mit Text: ab 1280 px neben dem Langtext, von 768 bis 1279 px über dem Kurztext, unter 768 px mit vollem Text. Es ist `aria-hidden`. Der Test in `navigation.spec.ts` Z. 137-148 deckt das ab, sobald die Konstanten angepasst sind.
8. `git grep -n "lucide-react" -- web/src` findet weiterhin nur `web/src/icons/names.ts`.
9. Sichtprüfung im eigenen Compose-Projekt im Browser bei 375, 768, 1024 und 1280 px, hell und dunkel, de und en, mit langem Benutzernamen bei 768 px. Die Beobachtungen stehen im Kurzbericht; Bildschirmfotos bleiben lokal und werden nicht eingecheckt.
10. Keine neue Abhängigkeit (`web/package.json` und `web/package-lock.json` unverändert).
11. `down -v` der eigenen Compose-Projekte endet mit Exit 0.

## Vorgaben und Hinweise

- **Herkunft:** Gesamtplan M3 der Leitstelle, Entscheidungen D13 und D14. Der ROADMAP-Eintrag für M3 steht in `docs/ROADMAP.md:13`, die Prüffragen und Abnahme stehen in STARTUNTERLAGE Abschnitt 9 (lokal, nicht zitieren).
- **Kopfleiste:** Die Messung und die Regeln stammen aus 082: Kurztexte als CSS-`::before` in einem `aria-hidden`-Element, Fokusrahmen innen unter 1280 px, `overflow-x-auto` nur als Rückfall (`docs/auftraege/erledigt/082-navigation-schmal.md:50`, `:84-87`; `web/src/pages/README.md:41-64`). Das Kriterium „ab 768 px einzeilig, ohne Scrollen“ ist mit E-65 Punkt 3 und E-68 abgenommen. Scrollen der Leiste zwischen 768 und etwa 830 px (D13 Option b) ist nicht freigegeben.
- **Rollen:** E-40. `navigation.ts` bestimmt die Rolle einer Seite über `requiredRole()`. Pages ohne Eintrag bekommen `read`; das gilt danach auch für `/selftest`.
- **Icons:** E-51 und Auftrag 071. Lucide wird nur in `names.ts` importiert. Größe 20 in der Navigation, Outline, aktueller Eintrag über den weichen Hintergrund (`web/src/icons/README.md:18-23`). NAV-06 ist in der Bedarfsanalyse als „optional eigenes Icon“ geführt (`docs/design/icon-bedarfsanalyse.md:319`, `:634`).
- **Gestaltung:** Tokens aus 070, Bausteine aus `web/src/components/ui/` (077), Bewegung reduzierbar (E-52). Der neue Link im Benutzermenü nutzt dieselben Klassen wie der Einstellungs-Link (`nav-link`, `nav-label` mit `data-label`), damit die fette Breite reserviert bleibt.
- **Texte** gibt es in Deutsch und Englisch. `i18n.test.ts` prüft gleiche Schlüssel in de und en.
- **Abgrenzung zu parallelen Aufträgen:** 133 läuft parallel und ändert Formular, `devicesByPlant`, `SearchPage.tsx`, `DevicePage.tsx`, `answers.json` und `assets.json`. Gemeinsame Datei ist nur `web/src/pages/README.md`: 134 ändert dort den Abschnitt „Frame and navigation“, 133 den Abschnitt zur Seite Auskunft. Die Leitstelle führt beide zusammen. `icons/names.ts` ändern 132 und 134 nacheinander. 134 setzt 132 auf `main` voraus, damit die Route `/ask` und ihr Seitentitel existieren.
- **Leitplanken:** Keine Personennamen, keine lokalen Pfade mit Benutzernamen und kein anderer Produktname als „2x“ in Dateien oder Commits (E-22). Der lange Testname in `navigation.spec.ts` bleibt generisch (`e2e-manager-with-a-very-long-user-name`). Alles läuft in Containern, nichts unter Windows direkt. Kein Push ohne Freigabe von a7 (E-14).
- **Freigabestufe C**, weil D13 die abgenommene Navigation (E-65, E-68) ändert und D14 die Icon-Frage betrifft. Der Auftrag startet erst, wenn a7 beides entschieden hat. Entscheidet a7 bei D13 anders als empfohlen, passt die Leitstelle diesen Auftrag vorher an.

## Fragen an a7 (mit Optionen und Empfehlung)

**D13 – Navigationsplatz bei 768 px**

- (a) Der Selbsttest wandert aus der Kopfleiste ins Benutzermenü, wie die Einstellungen. Die Auskunft bekommt einen eigenen Menüpunkt.
- (b) Die Leiste darf zwischen 768 und etwa 830 px scrollen. Das widerspricht dem Kriterium aus 082.
- (c) Kein Menüpunkt; der Einstieg läuft nur über Suche und Geräteseite.

Empfehlung: (a). Bei 768 px und langem Namen sind heute nur 25 px frei, ein achter Eintrag passt nicht. Der Selbsttest ist eine Betriebsseite und kein Arbeitsweg.

**D14 (Teil Icon) – Icon NAV-06**

- (g) Vorerst ein Lucide-Icon ohne Sprechblase und ohne Funkeln.
- (h) Jetzt eine eigene Zeichnung (`industrial/`, Muster 074).

Empfehlung: (g). Eine eigene Zeichnung trägt nichts zur Abnahme von M3 bei und kann als Gestaltungsauftrag nach M3 folgen, zusammen mit der Assistentenfigur (D17).

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
