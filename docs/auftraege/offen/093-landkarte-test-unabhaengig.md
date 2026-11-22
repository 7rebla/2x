# Auftrag 093 – Landkarten-e2e-Test unabhängig von Altdaten

Meilenstein: Gestaltung (D1) · Freigabestufe: B · Status: in Arbeit

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
