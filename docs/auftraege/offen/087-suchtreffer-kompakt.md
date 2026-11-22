# Auftrag 087 – Suchtreffer kompakter

Meilenstein: Gestaltung (D1) · Freigabestufe: B · Status: zur Prüfung

Voraussetzung: 077 ist auf `main`.

## Ziel

Ein Suchtreffer listet dieselbe Datei für bis zu elf Geräte untereinander und verdrängt den Treffertext; `<mark>` mit Polster zerreißt Wörter („IP - Adressen“); die Marken „Stichwort“ und „Bedeutung“ sind unerklärt.

## Umfang

- Erste Fundstelle zeigen, weitere als „+N weitere Geräte“ ausklappbar (`aria-expanded`).
- `<mark>` ohne seitliches Polster (`px-0`, `box-decoration-clone`).
- Marken mit Erklärung (`title` und für Screenreader `sr-only`-Text) in de/en.
- Tests (Vitest; e2e, wo Layout oder Bedienung sich ändern) für das neue Verhalten; bestehende Tests angepasst, nicht abgeschwächt.
- Doku: `web/src/pages/README.md` bzw. `web/src/theme/README.md` nachziehen, wo betroffen.

## Nicht-Ziele

- Keine neue Abhängigkeit, keine Änderung an API oder Backend.
- Nur der genannte Bereich; andere Befunde der UI-Analyse haben eigene Aufträge.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/pages/search/SearchHitView.tsx`, `web/src/pages/SearchPage.tsx`, `web/src/locales/*/search.json`, Tests

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

Status: zur Prüfung

- **Was wurde gebaut?**
  - `SearchHitView.tsx`: Ein Treffer zeigt nur die erste Fundstelle (Datei, Version, Gerät, Anlage mit Links). Weitere Fundstellen liegen hinter einem `Button` (ghost, sm) „+10 weitere Geräte“ / „+10 more devices“ mit `aria-expanded` und `aria-controls` auf die Liste; nach dem Öffnen heißt er „Weniger anzeigen“ / „Show fewer“. Liegt der Text auf einem Gerät mehrfach vor (mehrere Dateien oder Versionen), heißt es „weitere Fundstellen“ / „more places“ (`hiddenPlacesKind`), damit die Zahl stimmt. Ein Treffer mit einer Fundstelle hat keinen Knopf. Keine Animation (E-52 unberührt).
  - `<mark>` ohne seitliches Polster: `px-0 box-decoration-clone` (`MARK_CLASS`); „IP-Addresses“ ohne Lücken.
  - Marken „Exakt / Stichwort / Bedeutung“: Erklärung als `title` und als `sr-only`-Text nach dem Namen, de und en (`matchKind.hint.*`). Die Erklärungen folgen der Beschreibung der Suchwege in `backend/twox/search/postgres.py` (Zeilen 10–30). `data-testid="search-match-kind"` sitzt jetzt auf dem sichtbaren Namen (Text unverändert, bestehende e2e-Prüfungen gelten weiter), das `li` heißt `search-match-kind-item`.
  - Texte in `locales/de|en/search.json`, Doku in `web/src/pages/README.md` (Abschnitt Search). `SearchPage.tsx` brauchte keine Änderung.
- **Wie wurde getestet?**
  - Kriterium 0: `docker version` und `docker compose version` Exit 0.
  - Kriterium 1: Web-Job wie in `ci.yml` (Projekt `twox-087-web`): lint, typecheck, test (41 Dateien, 801 Tests), build, licenses grün; `api:generate` ohne Unterschied.
  - Kriterium 2: e2e wie in `ci.yml` (Projekt `twox-087`, Port 18087): 56 bestanden, 1 übersprungen (lokaler Teil von `m2-acceptance.spec.ts` ohne Handbücher). `m2-acceptance` prüft Seite und Link zur Datei über die erste, sichtbare Fundstelle – das funktioniert weiter, weil die erste Fundstelle immer im DOM steht.
  - Neue Vitest-Fälle: Aufklappen/Zuklappen mit `aria-expanded`/`aria-controls`, kein Knopf bei einer Fundstelle, 11 Geräte → „+10 more devices“, „places“-Fall, deutsche Texte (Singular/Plural), Erklärungen der Marken (title, sr-only, de/en), `<mark>` ohne seitliches Polster. Bestehende Tests zu allen Fundstellen öffnen die Liste jetzt zuerst und prüfen dasselbe wie vorher.
  - Neuer e2e-Fall (375 px): erste Fundstelle mit Seite und Dateilink, Knopf auf/zu, Fokus bleibt auf dem Knopf, `mark` mit 0px Polster, `title` der Marke, keine waagrechte Überbreite.
  - Kriterium 3: im eigenen Projekt im eingebauten Browser mit Wegwerf-Testdaten (eine Datei mit gleichem Inhalt auf 11 Geräten, nur in der eigenen Datenbank) bei 1600 px hell und dunkel, 1024 px dunkel, 375 px hell und dunkel. Beobachtungen: Treffertext steht direkt unter der Kopfzeile, darunter eine Fundstelle und „+10 weitere Geräte“; aufgeklappt 11 Zeilen, „Weniger anzeigen“ klappt zurück. „IP-Addresses“ ohne Lücke an der Hervorhebung. Bei 375 px bricht die Fundstelle in vier Zeilen um, keine waagrechte Überbreite (scrollWidth 375). Kontraste im dunklen Modus wirken unauffällig (Tokens unverändert). Am Rande (nicht dieser Auftrag): bei 375 px ist die Hauptnavigation im Kopf rechts abgeschnitten; die Fundstellen kommen vom Server nach Gerätenamen als Text sortiert („Test station 1, 10, 11, 2 …“).
  - Kriterium 4: `down -v` für `twox-087` und `twox-087-web` Exit 0.
- **Zweig und Arbeitsverzeichnis:** `worktree-agent-a62093e879769e6a1`, `.claude/worktrees/agent-a62093e879769e6a1`
- **Abweichungen:** Neben den genannten Dateien geändert: `web/e2e/search.spec.ts` (neuer Testfall) und `web/src/pages/README.md` (Doku, im Umfang genannt). Kein neues Icon, keine neue Abhängigkeit, keine API-Änderung. Zusätzlich zur Vorgabe „+N weitere Geräte“ die Variante „+N weitere Fundstellen“ für den Fall, dass ein Gerät mehrfach vorkommt.
