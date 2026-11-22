# Auftrag 132 – Seite Auskunft mit Quellenanzeige

Meilenstein: M3 · Freigabestufe: B · Status: offen

Voraussetzung: 131 (Antwortstrom und Hook) ist auf `main`; damit auch 130 (API mit SSE und Status-Endpunkt), 126 und 122 (Ereignisvertrag).

## Ziel

Eine neue Seite `/ask` schließt den Weg von der Frage bis in den Browser: Frage stellen, die Antwort erscheint fortlaufend, darunter stehen nachprüfbare Quellen mit Datei, Version, Seite, Überschriftenpfad, Ausschnitt und Fundorten. Die Endzustände „ohne Beleg“, „Widerspruch“, „KI aus“ und „Fehler“ sind auf einen Blick erkennbar. Das ist der sichtbare Teil der ROADMAP-Merkmale „Frage und Antwort“ und „Quellenanzeige“ (`docs/ROADMAP.md:13`, STARTUNTERLAGE Abschnitt 9). Leitplanke 3 gilt auch in der Oberfläche: Eine Aussage ohne nachprüfbare Quelle wird nicht als belegt dargestellt.

## Umfang

1. **Seite und Route**
   - Neue Seite `web/src/pages/AnswerPage.tsx`, Teile unter `web/src/pages/answer/` (z. B. `AnswerForm.tsx`, `AnswerCard.tsx`, `SourceList.tsx`, `answerText.ts`). `events.ts` und `useAnswerStream.ts` stammen aus 131 und werden nur benutzt, nicht geändert.
   - Route `ask` in `web/src/routes.tsx` (Tabelle `pages` mit `lazyPage()`, damit `preloadPages()` sie lädt; `guarded("/ask", …)`). Noch **kein** Eintrag in `web/src/navigation.ts` – den macht 134. Ohne Eintrag gilt nach `requiredRole()` die Rolle `read` (wie `/settings`, `routes.tsx:71-72`).
   - Adressentabelle in `web/src/pages/README.md` (Z. 9-22) um `/ask` ergänzen und einen Abschnitt „Ask“ nach dem Muster „Search“ (Z. 288-316) anlegen.

2. **Formular**
   - Textarea für die Frage (höchstens 500 Zeichen wie die API aus 130; Zähler oder Hinweis bei Überschreitung, Senden dann gesperrt), Knopf „Fragen“ (primary) und während des Stroms „Abbrechen“ (secondary). Bausteine aus `web/src/components/ui/` (`Button.tsx`, `fields.tsx`).
   - Senden per Knopf; Strg+Enter darf zusätzlich senden, Enter allein erzeugt einen Zeilenumbruch.
   - Eine Frage wird nie automatisch abgeschickt, auch nicht nach Neuladen. `?q=` in der Adresse füllt nur das Feld (D14 i). Die Frage selbst wird nicht in die Adresse geschrieben (anders als die Suche, `pages/README.md:293-295`), weil sie nur im POST-Body steht (130, D7).
   - Die Eingrenzung auf Gerät oder Anlage ist **nicht** Teil dieses Auftrags (133). Das Formular gibt dem Hook aber einen Platz für `device`/`plant` mit (Standard: keine Eingrenzung), damit 133 nur die Auswahl ergänzt.

3. **Antwortkarte**
   - Während `streaming`: der gesammelte Text in einem `article` mit `aria-busy="true"`, ohne `aria-live`. Keine Tipp-Animation, kein Cursor-Blinken (E-52/E-64 gelten nur für den Schriftzug).
   - Nach `done` ersetzt `final_text` den gestreamten Text (D9, Hook aus 131). Verworfene Sätze (`removed_sentences` > 0) werden mit einem kurzen Hinweis gekennzeichnet („Nicht belegte Aussagen wurden entfernt.“; D8 c), ohne den verworfenen Text zu zeigen.
   - Der Antworttext wird **nur als Text** gerendert: kein `dangerouslySetInnerHTML`, kein Markdown-Renderer, keine automatische Verlinkung von URLs, keine Bilder. Er geht nicht durch die Interpolation von i18next (wie `SearchHitView.tsx:8-10`).
   - Quellennummern `[n]` im Text werden in eine reine Funktion `answerText.ts` zerlegt (Stücke `text` | `citation`). Eine Nummer, die in der Quellenliste vorkommt **und** im Urteil von `done` als gültig steht (`cited`), wird zu einem Link auf den Anker der Quelle (`#source-n`) mit zugänglichem Namen „Quelle 2: <Titel>, Seite 14“ bzw. „Source 2: <title>, page 14“ (bei Markdown ohne Seite: Überschriftenpfad statt Seite). Jede andere Nummer bleibt Text. Während des Stroms (vor `done`) sind Nummern noch Text oder ein nicht-interaktiver Hinweis – keine Links auf ungeprüfte Zitate.
   - Kein Fokuswechsel bei Zustandswechseln. Nach Klick auf ein Zitat springt die Seite zur Quelle (normaler Anker; Fokus darf auf die Quellenkarte gehen, die dafür `tabIndex={-1}` hat).

4. **Zustände**
   - Eine `role="status"`-Zeile mit kurzen Meldungen: „Suche Quellen …“, „Antwort wird erstellt …“, „Fertig“, „Abgebrochen“. Nur Zustandswechsel, nicht jedes Textstück.
   - `answered`: Antwort, darunter die Quellenliste. Angezeigt werden die zitierten Quellen; nicht zitierte Quellen aus `sources` erscheinen gar nicht oder eingeklappt unter „Weitere geprüfte Abschnitte“ (Entscheidung des Bearbeiters, im Kurzbericht begründen).
   - `no_evidence`: der feste Satz „Dazu finde ich nichts in den Unterlagen“ mit Icon `noEvidence`, **ohne** Quellenliste, und ein Link zur Suche (`/search?q=<Frage>`; die Frage steht hier nur auf ausdrücklichen Klick in der Adresse, wie bei der Suche üblich).
   - `contradiction`: Antwort mit Icon `contradiction` und Hinweistext; die beiden widersprüchlichen Quellen sind in der Liste hervorgehoben (Rahmen in `warning`-Tokens, Text „Widersprüchliche Stelle“, nicht nur Farbe).
   - `ai_disabled`: Ist die KI aus (Status-Endpunkt aus 130 meldet `enabled=false`, oder der Strom liefert 409 `ai_disabled`), erscheint ein ruhiger Hinweis (Ton `neutral`/`info`, keine Warnung, wie die Suchseite bei `semantic=disabled`, `pages/README.md:298`) mit Link zur Suche; Formular und Knopf sind gesperrt (`disabled`, Grund als Text). Ist `chat_model_configured=false` oder `available=false`, gilt dasselbe mit dem Text „Auskunft derzeit nicht verfügbar“.
   - Fehler: `ErrorMessage` (`web/src/components/ErrorMessage.tsx`, `role="alert"`) mit dem festen Code aus `ErrorEvent` bzw. ApiError (400, 403 über `reportForbidden`, 503). Rohtexte des Servers erscheinen nur, wenn der ApiError-Text dafür vorgesehen ist (wie im übrigen Client).
   - Endzustände tragen immer Icon **und** Text.

5. **Quellenliste**
   - Je Quelle eine Karte mit Anker `id="source-n"` und Nummer `n`, Seite oder Seitenbereich (`PageLabel`), Überschriftenpfad, Ausschnitt und Fundorten (`Locations`, `LocationView`: Datei mit Link auf `/documents/:id`, Version und Dateiname, „Ältere Version“, Gerät mit Link, Anlage).
   - Ausschnitt: Der Abschnittstext wird als Text gekürzt dargestellt (etwa 300 Zeichen, an der Wortgrenze, Unicode-sicher wie `snippet.ts`, mit „…“). Ob `sources` den vollen Text oder schon einen Ausschnitt liefert, ergibt sich aus `events.ts` (131); der Bearbeiter richtet sich danach und nennt es im Kurzbericht. Keine Hervorhebung nötig, `Snippet` darf mit leeren `highlights` verwendet werden.
   - Eine Quelle **ohne Seite und ohne Überschriftenpfad** wird nicht als Beleg dargestellt: kein Zitat-Link, in der Liste nur mit dem Vermerk „Fundstelle ohne Seitenangabe“ bzw. gar nicht (Akzeptanz 3). Markdown-Quellen (ohne Seite, mit Überschriftenpfad, vgl. 120/136) zählen als Beleg.
   - Die Liste ist eine `ol` mit zugänglichem Namen „Quellen“.

6. **Gemeinsame Bausteine aus der Suche**
   - `PageLabel`, `LocationView`, `Locations` (mit `hiddenPlacesKind`) und `Snippet` (mit `MARK_CLASS`) ziehen aus `web/src/pages/search/SearchHitView.tsx` (Z. 31-187) nach `web/src/components/sources/` (z. B. `PageLabel.tsx`, `Locations.tsx`, `Snippet.tsx`, `index.ts`) und werden dort exportiert. `PageLabel` nimmt dafür nur `page_start`/`page_end` statt eines ganzen `SearchHit`.
   - `snippet.ts` und `snippet.test.ts` ziehen mit nach `components/sources/` (Inhalt unverändert, nur Importpfade), damit `components/` nicht aus `pages/` importiert. Die Testdaten `pages/search/testData.ts` bleiben.
   - Die Bausteine behalten ihre `data-testid` (`search-snippet`, `search-hit-page`, `search-location*`, `search-more-locations`, `search-older-version`) und ihre Schlüssel im Namespace `search` (`page.*`, `version`, `olderVersion*`, `moreLocations.*`, `device`, `plant`, `locations`, `headingPath`). Keine Schlüssel werden verschoben; die Seite Auskunft nutzt sie über den bereits registrierten Namespace `search`.
   - `SearchHitView.tsx` importiert sie von dort. Die Suchseite bleibt sichtbar unverändert; ihre Vitest- und e2e-Tests bleiben ohne inhaltliche Änderung grün.
   - Die Fundort-Typen: `SearchLocation` aus dem generierten Client. Hat die Quelle aus 122/131 einen eigenen, gleich gebauten Typ (`HitLocation` im Schema), nimmt `Locations` einen strukturellen Typ (`Pick`), der beide abdeckt; keine Typumwandlung mit `as`.
   - Festlegung der Leitstelle nach der Prüfung von 122: Die Quellen im SSE-Ereignis `sources` tragen die Fundorte in der flachen Form von `source_ref_to_json()` (122), nicht in der verschachtelten Form von `SearchLocation`. 131 oder 132 bildet sie mit einer kleinen, getesteten Funktion auf die Form ab, die `Locations` braucht (ohne `as`).

7. **Texte und Namespace**
   - Neuer Namespace `answers`: `web/src/locales/de/answers.json` und `web/src/locales/en/answers.json`, registriert in `web/src/i18n.ts` (Liste `namespaces` Z. 41-53 und Ressourcen Z. 60-90, Kommentar Z. 5 nachziehen) und `web/src/i18next.d.ts`. Das ist der eigene Auftrag, den `web/src/locales/README.md:16` für einen neuen Namespace verlangt; die Liste der Namespaces in `locales/README.md:8` ergänzen.
   - Der feste Satz „Dazu finde ich nichts in den Unterlagen“ steht im Katalog (de wörtlich nach CLAUDE.md Leitplanke 3; en „I can't find anything on this in the documents.“). Kommt `final_text` mit dem Satz vom Server, zeigt die Seite für `no_evidence` trotzdem den Katalogtext in der gewählten Sprache.
   - Seitentitel „Auskunft“ / „Ask“ und Überschrift mit der vorhandenen Überschriften-Animation wie die anderen Seiten (E-65 Punkt 6).

8. **Icons**
   - In `web/src/icons/names.ts` unter „Status (STA)“ zwei Einträge: `noEvidence` und `contradiction`, jeweils ein Lucide-Icon **ohne Sprechblase, ohne Funkeln oder Stern** (`docs/design/icon-bedarfsanalyse.md:183-185`, B6), z. B. `SearchX` bzw. `FileX` für `noEvidence` und `GitCompareArrows` oder `Scale` für `contradiction`. Lucide wird nur in `names.ts` importiert. `web/src/icons/README.md` nachziehen. Das Navigations-Icon `answer` (NAV-06) macht 134.

9. **Tests**
   - `web/src/pages/AnswerPage.test.tsx` (Vitest, über `web/src/test/renderApp.tsx` und `fakeApi.ts`; Strom über einen fetch-Stub mit `ReadableStream` wie in den Tests aus 131), Tests der reinen Funktionen in `pages/answer/` (`answerText.test.ts`) und für die verschobenen Bausteine (bestehende Tests der Suche dürfen nur Importpfade ändern).
   - Alle Testtexte (Fragen, Antworten, Abschnitte) sind selbst geschrieben, keine Auszüge aus Herstellerunterlagen.
   - Ein e2e-Fall `web/e2e/answer-page.spec.ts` (klein): `/ask` lädt ohne Konsolenfehler, Formular mit Beschriftung, Zugänglichkeit in de und en nach Art von `web/e2e/accessibility.spec.ts` geprüft (Rollen und zugängliche Namen über `getByRole`, `role="status"` für den Zustand, Hinweis bei KI aus mit Link zur Suche, gesperrtes Formular, Bedienung mit der Tastatur), keine waagrechte Überbreite bei 375 px. **Kein axe:** Im Repository gibt es kein axe-Paket; `@axe-core/playwright` wäre eine neue Abhängigkeit (MPL-2.0, Stufe C, siehe 137 Frage 2). Entscheidet a7 dort für axe, ergänzt der dafür vorgesehene Auftrag die Prüfung in `answer-page.spec.ts`. In der CI ist kein Chat-Modell vorhanden (`TWOX_CHAT_MODEL` leer nach 121); der Test prüft deshalb den gesperrten Zustand „nicht verfügbar“ über den echten Status-Endpunkt. Den vollständigen Ablauf mit abgefangenem Strom (`page.route`) baut 137 in `web/e2e/answer.spec.ts` – nicht hier.

## Nicht-Ziele

- Keine Änderung an Backend, API, OpenAPI-Schema oder generiertem Client (`web/openapi/schema.yml`, `web/src/api/generated/**`), an `web/src/api/answers.ts`, `pages/answer/events.ts` oder `pages/answer/useAnswerStream.ts` (131). Fehlt dort etwas, Frage in diesen Auftrag schreiben, nicht selbst ändern.
- Keine Eingrenzung auf Gerät oder Anlage in der Oberfläche, kein Knopf auf der Geräteseite, keine Auslagerung von `devicesByPlant` (133).
- Kein Navigationseintrag, kein Icon `answer`, keine Änderung an `navigation.ts`, `nav.json`, `UserMenu.tsx` (134).
- Kein Sprung zur PDF-Seite, keine eingebettete Dokumentansicht (D14 f).
- Kein Verlauf, kein Speichern von Fragen oder Antworten, auch nicht in `localStorage` (D7). Ein nicht abgeschickter Entwurf im Feld darf beim Neuladen verloren gehen.
- Keine Assistentenfigur (D17), keine Chat-Optik (Sprechblasen, Avatare).
- Kein Abnahmetest M3, keine `answer.spec.ts` mit festem SSE-Strom (137).
- Keine neue Abhängigkeit (kein Markdown-Renderer, kein SSE-Paket, kein axe-Paket).

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/pages/AnswerPage.tsx` (neu), `web/src/pages/AnswerPage.test.tsx` (neu)
- `web/src/pages/answer/*` (neu, **ohne** `events.ts` und `useAnswerStream.ts`), mit Tests
- `web/src/components/sources/*` (neu: verschobene Bausteine, `snippet.ts`, `snippet.test.ts`)
- `web/src/pages/search/SearchHitView.tsx` (nur Importe, Bausteine entfernt), `web/src/pages/search/snippet.ts` und `snippet.test.ts` (verschoben)
- `web/src/routes.tsx`
- `web/src/locales/de/answers.json`, `web/src/locales/en/answers.json` (neu), `web/src/locales/README.md` (Namespace-Liste)
- `web/src/i18n.ts`, `web/src/i18next.d.ts`
- `web/src/icons/names.ts` (nur `noEvidence`, `contradiction`), `web/src/icons/README.md`
- `web/src/pages/README.md` (Adressentabelle, Abschnitt „Ask“, Verweis im Abschnitt „Search“ auf `components/sources/`)
- `web/e2e/answer-page.spec.ts` (neu)

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Vitest prüft die Zustände: streaming (Text wächst, `aria-busy`, Abbrechen sichtbar); answered mit Quellenliste und Zitat-Links mit zugänglichem Namen „Quelle n: <Titel>, Seite x“ (de) bzw. „Source n: …“ (en); no_evidence mit dem festen Satz und **ohne** Quellenliste; contradiction mit beiden Quellen hervorgehoben (Text, nicht nur Farbe); ai_disabled als Hinweis mit gesperrtem Formular und Link zur Suche; Fehler mit `role="alert"`.
2. HTML im Antworttext erscheint als Text: Ein Test mit `<img src=x onerror=…>` und `<a href=…>` im Strom findet kein `img`- und kein fremdes `a`-Element im Antwortbereich.
3. Eine Quelle ohne Seite und ohne Überschriftenpfad wird nicht als Beleg dargestellt (kein Zitat-Link, Test); eine Markdown-Quelle mit Überschriftenpfad ohne Seite schon (Test).
4. Eine Nummer `[9]`, die nicht in `cited` steht, und Nummern während des Stroms sind keine Links (Test).
5. `?q=` füllt das Feld, ohne abzusenden: Der fetch-Stub wird nicht aufgerufen (Test).
6. `final_text` ersetzt den gestreamten Text; bei `removed_sentences` > 0 erscheint der Hinweis (Test).
7. Die bestehenden Tests der Suchseite (`SearchPage.test.tsx`, Tests von `snippet.ts`, `web/e2e/search.spec.ts`, `web/e2e/m2-acceptance.spec.ts`) sind ohne inhaltliche Änderung grün; geänderte Zeilen dort betreffen nur Importpfade.
8. `i18n.test.ts` ist grün (de und en haben dieselben Schlüssel in `answers`); `icons.test.tsx` ist grün.
9. Web-Job aus `.github/workflows/ci.yml` grün: lint, typecheck, test, build, licenses; `api:generate` ohne Unterschied (der Client bleibt unverändert).
10. Backend-Job aus `ci.yml` unverändert grün (keine Backend-Änderung; ruff, mypy, pytest, OpenAPI-Schema ohne Unterschied).
11. e2e wie in `ci.yml` grün, einschließlich `answer-page.spec.ts` (Rollen, zugängliche Namen, `role="status"`, gesperrtes Formular und Tastaturbedienung in de und en ohne Befund, 375 px ohne Überbreite; ohne axe-Paket).
12. Sichtprüfung im eigenen Compose-Projekt im Browser bei 375, 768 und 1280 px, hell und dunkel, de und en: gesperrter Zustand (ohne Modell) und – mit `fakeApi`-gestützter Vitest-Vorschau oder abgefangenem Strom – answered, no_evidence und contradiction. Beobachtungen im Kurzbericht (Bildschirmfotos nur lokal, nicht eingecheckt).
13. `git diff --stat main` zeigt nur Pfade aus „Betroffene Bereiche“; `package.json` und `package-lock.json` unverändert.
14. `down -v` der eigenen Compose-Projekte endet mit Exit 0.

## Vorgaben und Hinweise

- **Herkunft:** Gesamtplan M3 der Leitstelle; ROADMAP M3 „Frage und Antwort, Quellenanzeige, Eingrenzen auf Gerät“ (`docs/ROADMAP.md:13`); STARTUNTERLAGE Abschnitte 4, 9 und 10.2 (nur lokal, nicht zitieren).
- **Leitplanke 3** (Antworten nur mit Quelle): Die Oberfläche zeigt eine Antwort nur mit Quellen, die der Server geprüft hat (`cited` aus `done`, Zitatprüfung 123). Ein Satz ohne Quelle wird nicht als belegt dargestellt.
- **Leitplanke 4** (Dokumentinhalte sind Daten): Antworttext, Abschnittstexte, Titel, Dateinamen, Geräte- und Anlagennamen sind Daten. React rendert sie als Text, nie als HTML; keine i18next-Interpolation mit ihnen als Schlüssel; Werte in `{{…}}`-Platzhaltern nur mit der Standard-Escape-Einstellung. Keine Links aus dem Antworttext (der Prompt aus 122 verbietet sie, die Oberfläche setzt es zusätzlich durch).
- **Leitplanke 6** (ohne Internet): keine externen Ressourcen, Schriften oder Icons aus dem Netz.
- **E-59** (KI optional): Bei ausgeschalteter KI gibt es keine Auskunft, die Suche bleibt der Weg (D10 a). Kein Fehlerton, sondern ein ruhiger Hinweis.
- **E-55** (mehrere Fundorte): Fundorte bleiben wie in der Suche kompakt (erste sichtbar, weitere ausklappbar, Auftrag 087).
- **E-61** (Sprachfassungen): Die Quellenliste zeigt, was der Server liefert; Zusammenlegen der Sprachfassungen ist Sache von 125.
- **E-62 / D7:** Nichts speichern, keine Frage in die Adresse außer `?q=` beim ausdrücklichen Vorbelegen.
- **E-52, E-64, E-65, E-68:** Bewegung dezent und über „Bewegung reduzieren“ abschaltbar; keine Tipp-Animation für den Antwortstrom; Raster `max-w-7xl`, Fließtext `max-w-prose`; Metadaten 13–14 px; Steuerhöhen der Bausteine 36/28 px (077); Icons nur über `web/src/icons` (071, E-51). Die abgenommene Gestaltung D1 (E-68) wird nicht verändert.
- **B6** (`docs/design/icon-bedarfsanalyse.md:183-185`): keine Sprechblase, kein Funkeln oder Stern.
- **Rollen:** Die Seite ist für `read` und `manage` erreichbar; Anmeldung und Rechte bleiben unberührt (Stufe C wäre sonst nötig).
- **Abgrenzung zu parallelen Aufträgen:** 128 (Messlauf) läuft gleichzeitig ohne Codeänderung. 133 und 134 starten erst nach diesem Auftrag; sie ändern `pages/answer/AnswerForm*`, `locales/*/answers.json` (133) bzw. `icons/names.ts` (134, nur `answer`). Deshalb das Formular so schneiden, dass 133 die Eingrenzung in `AnswerForm*` ergänzen kann, ohne `AnswerPage.tsx` umzubauen. `icons/names.ts` ändert 132 vor 134.
- **Vorbilder:** `web/src/pages/SearchPage.tsx` (Zustände, Hinweis bei `semantic=disabled`), `web/src/pages/search/SearchHitView.tsx` (Quellenkarte), Auftrag 087 (kompakte Fundorte), Auftrag 054 (Suchseite).
- **Arbeitsweise:** Alles über `docker compose` (Web-Compose wie im Web-Job von `ci.yml`, eigenes Projekt `twox-132`, eigener Port); kein npm unter Windows. Commits klein auf dem Auftragszweig, kein Push (E-14). Keine Personennamen, keine lokalen Pfade mit Benutzernamen in Dateien oder Commits (E-22).

## Fragen an a7 (mit Optionen und Empfehlung)

Keine, die den Auftrag aufhalten. Umgesetzt wird die Vorgabe aus D14:

- **D14 Details der Oberfläche** (nur die Punkte für 132): Sprung zur PDF-Seite (e) in M3 oder (f) später; Adresse (i) `?q=` füllt nur das Feld oder (j) kein `?q=`. Empfehlung und Vorgabe: (f) und (i). Für den Seitensprung bräuchte es eine eingebettete Anzeige trotz CSP sandbox; eine Frage wird nie automatisch abgeschickt.
- **D10 Auskunft bei ausgeschalteter KI:** (a) Hinweis, gesperrtes Formular, Link zur Suche oder (b) Fundstellen ohne Antworttext. Empfehlung und Vorgabe: (a).
- **D8 Teilantworten:** (c) entfernen und kennzeichnen oder (d) ganz verwerfen. Vorgabe: (c); bei (d) entfällt nur der Hinweis auf entfernte Aussagen.
- **Zugänglichkeitsprüfung mit axe** (entschieden in 137 Frage 2, betrifft auch 132 und 134): (a) ohne axe mit Rollen, Namen, `role="status"`/`role="alert"`, `aria-busy` und Tastatur oder (b) `@axe-core/playwright` als neue Entwicklungsabhängigkeit in eigenem Stufe-C-Auftrag mit Lizenzeintrag (MPL-2.0). Vorgabe für 132: (a); der Auftrag bleibt Stufe B und fügt keine Abhängigkeit hinzu. Die Frage gehört in die Entscheidungsliste für a7 (im Gesamtplan bisher nicht unter D1–D17).

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
