# Auftrag 092 – Wackeligen e2e-Test des Strukturbaums stabilisieren

Meilenstein: Gestaltung (D1) · Freigabestufe: B · Status: in Arbeit

## Ziel

`web/e2e/structure-tree.spec.ts`, Test „devices of a plant stand in fixed columns at 1024/1600 px“ (aus 083), schlug in den Läufen von 080 und 081 vereinzelt fehl (Abstand der Zeilen 14 statt unter 8 px), einzeln wiederholt war er grün. Der Test soll verlässlich laufen, ohne seine Aussage abzuschwächen.

## Umfang

- Ursache klären. Vermutung der Leitstelle: Der Test misst sofort nach dem Eintippen der Suche, ohne auf das gefilterte Ergebnis zu warten (der Test für 375 px wartet auf „2 devices shown“). Möglich sind auch Umbrüche, solange Schrift oder Daten noch laden.
- Test so ändern, dass er auf einen stabilen Zustand wartet (Suchstatus, `expect.poll` für Lagen) – nicht durch größere Toleranzen.
- Liegt die Ursache in der Seite selbst (z. B. Zeilen springen nach dem Laden), im Kurzbericht beschreiben und nur mit kleiner, belegter Änderung in `web/src/pages/StructurePage.tsx` beheben.

## Nicht-Ziele

- Keine Änderung am Aussehen des Strukturbaums.

## Betroffene Bereiche (Ordner, Dateien)

- `web/e2e/structure-tree.spec.ts`, falls belegt nötig `web/src/pages/StructurePage.tsx`

## Akzeptanzkriterien (prüfbar)

1. Ursache im Kurzbericht benannt, mit Beleg (z. B. Trace oder Messung).
2. Die Grenzen (gleiche linke Kante < 1 px, eine Zeile < 8 px) bleiben gleich streng.
3. Die Datei `structure-tree.spec.ts` läuft mindestens zehnmal hintereinander grün (`--repeat-each=10`), zusätzlich ein vollständiger e2e-Lauf grün.
4. Alle Prüfungen aus `.github/workflows/ci.yml` (web, e2e) sind grün.

## Vorgaben und Hinweise

- Parallel laufen 082 (Layout.tsx, Navigation) und 086 (LoginPage). Diese Dateien nicht anfassen.

## Fragen an a7 (mit Optionen und Empfehlung)

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
