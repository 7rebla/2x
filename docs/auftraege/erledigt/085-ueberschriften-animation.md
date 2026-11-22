# Auftrag 085 – Überschriften-Animation zurücknehmen

Meilenstein: Gestaltung (D1) · Freigabestufe: C (entschieden mit E-65) · Status: erledigt

Voraussetzung: 076 ist auf `main` (dieselben Dateien).

## Ziel

Muster A aus E-52 lässt jede Seitenüberschrift bei jedem Seitenwechsel mit Unschärfe einblenden – für eine Arbeitsanwendung zu häufig. Nach E-65 (6): nur beim ersten Aufruf je Sitzung, höchstens 400 ms, ohne Unschärfe.

## Umfang

- Muster A ohne `filter: blur`, Dauer höchstens 400 ms; einmal je Sitzung (`sessionStorage` mit try/catch), danach Überschrift sofort.
- `web/src/theme/README.md`: Tabelle der Animationsmuster anpassen.
- Tests (Vitest; e2e, wo Layout oder Bedienung sich ändern) für das neue Verhalten; bestehende Tests angepasst, nicht abgeschwächt.
- Doku: `web/src/pages/README.md` bzw. `web/src/theme/README.md` nachziehen, wo betroffen.

## Nicht-Ziele

- Keine neue Abhängigkeit, keine Änderung an API oder Backend.
- Nur der genannte Bereich; andere Befunde der UI-Analyse haben eigene Aufträge.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/components/TextMotion.tsx`, `web/src/components/TextMotion.test.tsx`, `web/src/index.css` (Abschnitt Muster A), `web/src/theme/README.md`

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

- **Was wurde gebaut?** Muster A (`AnimatedHeading`) blendet nur noch die erste Überschrift einer Browser-Sitzung ein: Schlüssel `twox.heading` in `sessionStorage` (Zugriff in try/catch, neue Exporte `HEADING_STORAGE_KEY`, `headingShown`, `markHeadingShown`). Die Entscheidung fällt beim Einhängen; jede spätere Überschrift (auch auf anderen Seiten) steht sofort als reiner Text da. Ohne nutzbaren Speicher wird nie animiert. Ändert sich der Text einer gezeigten Überschrift (Sprachwechsel), erscheint der neue Text sofort. Bei reduzierter Bewegung gilt die Sitzung als erledigt. CSS: `filter: blur` entfernt, 280 ms je Wort, Versatz 30 ms, höchstens vier Schritte (`min(var(--tx-index), 4)`): fertig nach höchstens 400 ms. Die Ebene (`level`) und Muster E sind unverändert. `web/src/theme/README.md`: Tabellenzeile A und neuer Abschnitt „Heading fade (pattern A)“, `filter` aus der Liste der bewegten Eigenschaften gestrichen.
- **Wie wurde getestet?** Neue Vitest-Fälle in `TextMotion.test.tsx` (einmal je Sitzung, Textwechsel, reduzierte Bewegung, Speicher gesperrt, CSS ohne Unschärfe und ≤ 400 ms). Web-Job wie in `ci.yml` (Projekt `twox-085-web`): lint, typecheck, test (41 Dateien, 798 Tests), build, licenses grün, `api:generate` ohne Unterschied. e2e wie in `ci.yml` (Projekt `twox-085`): 55 bestanden, 1 übersprungen (lokaler M2-Abnahmetest, wie bisher). Im eingebauten Browser gegen das eigene Projekt (Port 18085): Anmeldeseite blendet „Anmelden“ ein (computed `tx-clear 0.28s`, `filter: none`); nach der Anmeldung steht „Struktur“ sofort ohne `tx-`-Klasse; nach Löschen des Schlüssels und Neuladen blendet „Einstellungen“ einmal ein; Verzögerungen bei 7 Wörtern 0 … 0,12 s, danach gedeckelt. Sichtprüfung bei 375 px (hell, Strukturseite), 1024 px (dunkel) und 1600 px (hell und dunkel, Anmeldeseite): Überschrift vollständig, nichts springt. Bildschirmfotos nicht eingecheckt. `docker version`, `docker compose version` und `down -v` beider Projekte mit Exit 0.
- **Zweig und Arbeitsverzeichnis:** `worktree-agent-a9c586e64059e38c6`, `.claude/worktrees/agent-a9c586e64059e38c6`.
- **Abweichungen:** Fremde Datei `web/src/pages/SettingsPage.test.tsx`, eine Zeile: der Test „reduces motion“ leert vorher `sessionStorage` (neue Sitzung), weil frühere Tests der Datei die Sitzung schon markieren. Beobachtung: In der Praxis ist die erste Überschrift einer Sitzung meist die der Anmeldeseite; die erste Seite nach der Anmeldung blendet dann nicht mehr ein. Das entspricht „einmal je Sitzung“; soll stattdessen die erste Seite nach der Anmeldung einblenden, wäre das ein eigener Auftrag. Hinweis: Im eingebauten Browser teilen sich die Projekte anderer Aufträge auf `localhost` die Cookies (Ports trennen Cookies nicht), daher wurde ich zwischendurch abgemeldet.
- **Mögliche Konflikte mit 078:** `TextMotion.tsx` – 078 ändert den Standard `level = 2` in der Signatur von `AnimatedHeading`; ich habe den JSDoc direkt darüber und die ersten Zeilen des Rumpfs (`useHeadingReveal` statt `useReducedMotion`) geändert – benachbarte Zeilen, Zusammenführung von Hand möglich. `TextMotion.test.tsx`: meine neuen Tests erwarten `<h2 …>` im HTML und `level: 2` nur im bestehenden Test; bei Standard `level=1` müssen `innerHTML`-Erwartung im Test „fades in only the first heading“ auf `<h1 …>` angepasst werden. `SettingsPage.test.tsx` und `e2e/settings.spec.ts` (`h2 .tx-word`) können ebenfalls von 078 betroffen sein.
