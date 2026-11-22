# Auftrag 093 – Landkarten-e2e-Test unabhängig von Altdaten

Meilenstein: Gestaltung (D1) · Freigabestufe: B · Status: zur Prüfung

## Ziel

`web/e2e/map.spec.ts`, Test „the map shows a device and its network, finds it and opens its page“, scheitert in der lokalen CI der Leitstelle, sobald sich Geräte aus früheren e2e-Läufen in der Datenbank sammeln (zuletzt am 22.11.2026: `expect.poll(() => insideBox(deviceNode, canvas))` in Zeile 118 lief nach 20 s ab). Mit frischer Datenbank ist er grün. Der Test soll unabhängig von vorhandenen Daten verlässlich sein, wie die übrigen e2e-Tests, die ihre Daten selbst anlegen.

## Umfang

- Ursache mit Beleg klären (z. B. Suche trifft viele alte Testgeräte, Einpassen auf alle Treffer schiebt den neuen Knoten aus der Karte; oder die Karte wird mit vielen Knoten zu klein).
- Test so ändern, dass er nur von den eigenen Daten abhängt (z. B. eindeutiger Suchbegriff, der nur das eigene Gerät trifft, oder Prüfung über den eigenen Knoten statt über alle Treffer) – ohne seine Aussage abzuschwächen.
- Liegt die Ursache im Verhalten der Seite (z. B. Einpassen bei vielen Treffern zeigt den gesuchten Knoten nicht), im Kurzbericht beschreiben und nur mit kleiner, belegter Änderung in `web/src/pages/MapPage.tsx` beheben.

## Nicht-Ziele

- Keine Änderung am Aussehen der Landkarte.

## Betroffene Bereiche (Ordner, Dateien)

- `web/e2e/map.spec.ts`, falls belegt nötig `web/src/pages/MapPage.tsx`

## Akzeptanzkriterien (prüfbar)

1. Ursache im Kurzbericht benannt, mit Beleg.
2. Der Test läuft grün auf einer Datenbank, in der vorher mindestens drei vollständige e2e-Läufe Daten hinterlassen haben (nachstellen und belegen), und auf einer frischen.
3. `map.spec.ts --repeat-each=5` grün; ein vollständiger e2e-Lauf grün.
4. Alle Prüfungen aus `.github/workflows/ci.yml` (web, e2e) sind grün.

## Vorgaben und Hinweise

- 084 (Schriftgröße) ist gerade in Prüfung und ändert u. a. `MapPage.tsx` und `map/nodes.tsx` (Klassen). Diese Dateien nur anfassen, wenn die Ursache es belegt verlangt, und dann minimal.

## Fragen an a7 (mit Optionen und Empfehlung)

## Kurzbericht (füllt der Auftragsbearbeiter aus)

Status: zur Prüfung

**Ursache (mit Beleg)**

- Der Test suchte nach der eigenen Adresse (zufällig 192.0.2.1 bis .254). Die Kartensuche findet Teilzeichenfolgen, und andere Aufträge legen bei jedem Lauf Geräte mit festen Adressen dieses Bereichs an (z. B. `audit.spec.ts` .10/.11, `files.spec.ts` .30, `import.spec.ts` .41/.42, dazu zufällige Adressen in `assets.spec.ts`). Eine Suche nach z. B. „192.0.2.1“ trifft deshalb .1, .10 bis .19 und .100 bis .199 aller Altgeräte.
- Nachgestellt: Datenbank mit 40 Wiederholungen von `map.spec.ts` und drei vollständigen e2e-Läufen (182 Geräte, 34 davon mit „192.0.2.1“ im Text) füllen, dann den Test mit fester Adresse `192.0.2.1` laufen lassen: 3 von 3 Läufen scheitern in Zeile 118 (Status „36 matches“, 20 s Zeitüberschreitung). Mit zufälliger Adresse (alter Test) war der Fehler dagegen selten (40 Läufe und 3 volle Läufe grün): er hängt vom Würfelwurf der Adresse ab.
- Messung im Browser (temporärer Probe-Test, nicht eingecheckt): `transform: translate(567px, -301px) scale(0.05)`, 38 Treffer, das eigene Gerät liegt bei y = 1051, die Karte reicht von y = 316 bis 764. Einpassen auf alle Treffer stößt an den kleinsten Zoom der Karte (`minZoom={0.05}`); die Treffer liegen über die ganze, inzwischen sehr hohe Karte verteilt, also liegt der Knoten außerhalb der Karte. Der Kommentar im Test („die Ansicht passt alle Treffer ein“) stimmte nur, solange die Treffer in die Karte passen.
- Das ist kein Fehler der Seite, sondern ein Grenzfall: Mehr Treffer, als bei kleinstem Zoom Platz haben, können nicht alle sichtbar sein. `MapPage.tsx` blieb unverändert.

**Was wurde gebaut?**

`web/e2e/map.spec.ts`: Neue Hilfsfunktion `unusedAddress`. Sie liest die Geräteliste der API und wählt (zufällig) eine Adresse aus 192.0.2.0/24, deren Text in keiner vorhandenen Adresse vorkommt (also weder genutzt noch Teil einer längeren). Die Suche nach der Adresse trifft damit genau das eigene Gerät. Der Test prüft jetzt zusätzlich „1 match“ und weiterhin per `expect.poll(insideBox)`, dass der Knoten ganz in der Karte liegt. Aussage nicht abgeschwächt (eher strenger), keine Toleranz, kein retry, kein Überspringen, nichts neu abhängig von Reihenfolge.

**Wie wurde getestet?**

- Kriterium 2: Datenbank nach 40 Wiederholungen des Kartentests und drei vollständigen e2e-Läufen (je 81 bestanden, 1 übersprungen): neuer Test `--repeat-each=5` grün, danach voller Lauf grün, also auf Altdaten. Frische Datenbank: der Test lief auch im ersten Wiederholungsblock gegen eine leere Datenbank grün (40 Läufe zu Beginn).
- Kriterium 3: `map.spec.ts --repeat-each=5`: 5 bestanden; vollständiger e2e-Lauf: 81 bestanden, 1 übersprungen (M2-Abnahme, lokaler Teil, wie vorgesehen).
- Kriterium 4: Web-Job im Projekt `twox-093-web`: `npm ci`, lint, typecheck, test, build, licenses, `api:generate` alle Exit 0; `git status` danach nur `web/e2e/map.spec.ts` geändert. e2e wie `ci.yml` (Projekt `twox-093`, Testkonto wie in `ci.yml`).
- `down -v` beider Projekte Exit 0.

**Zweig und Arbeitsverzeichnis**

- Zweig `worktree-agent-a272f2c45e308e1c8`, Arbeitsverzeichnis `.claude/worktrees/agent-a272f2c45e308e1c8`.

**Abweichungen**

- Nur `web/e2e/map.spec.ts` (und diese Datei) geändert; `MapPage.tsx` unberührt, keine neue Abhängigkeit.
- Der Fehler mit zufälliger Adresse trat in meinen Läufen nicht von selbst auf; nachgestellt habe ich ihn mit fester Adresse .1 auf der gefüllten Datenbank (Messung oben). Der Probe-Test wurde nicht eingecheckt.
- Hinweis für später (keine Änderung jetzt): Bei sehr vielen Treffern über die ganze Karte stößt die Suche an `minZoom` 0.05; die Seite zeigt dann nicht alle Treffer.
