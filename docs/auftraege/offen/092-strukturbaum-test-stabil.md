# Auftrag 092 – Wackeligen e2e-Test des Strukturbaums stabilisieren

Meilenstein: Gestaltung (D1) · Freigabestufe: B · Status: zur Prüfung

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
**Ursache (mit Beleg)**

- Das Symptom „14 px“ ist genau der Versatz, der entsteht, wenn der Gerätename in zwei Zeilen umbricht: Link 2 × 24 px = 48 px hoch, die Kennung (20 px) steht mittig, also 14 px tiefer als die Oberkante des Links. Bei einer Zeile sind es 2 px.
- Der Name steht in der Spalte `minmax(0,1fr)` des Geräteraster; die Kennungsspalte ist `minmax(8rem,auto)` und wächst mit der längsten Kennung. Die Namenspalte ist also der Rest. Mit den Testnamen `e2e-device-<Lauf-ID aus 16 Zeichen>-<Zähler>` liegt der Name bei 1024 px nur wenige Pixel vor dem Umbruch; je nach zufälliger Lauf-ID (Breite der Buchstaben) bricht er um.
- Messung (im Browser, 1024 px, Name und Kennung 20 000 Mal mit zufälliger Lauf-ID wie in `fixtures.ts` neu gesetzt, Höhe des Links gelesen): 16 von 20 000 Umbrüchen (Höhe 48 px), kleinster Rest 0,7 px. Mit dem kurzen Namensbestandteil `e2e-d-…`: 0 von 20 000, kleinster Rest 66,7 px.
- Die Vermutung der Leitstelle (Messen vor dem gefilterten Zustand, Schrift noch nicht geladen) ist nicht die Ursache der 14 px: Auch bei 20-facher CPU-Drosselung (CDP) und bei künstlich um 4 s verzögerter Schrift (Notschrift schmaler) lief der alte Test grün. Die Messung nach dem Eintippen und mit einzelnen `boundingBox`-Aufrufen ist trotzdem ein echtes Risiko (Zeilen verschieben sich, wenn der Filter greift) und wurde mit behoben.
- Die Ursache liegt in den Testdaten, nicht in der Seite: Ein langer Name darf umbrechen. `StructurePage.tsx` blieb unverändert.
- Nicht nachgestellt: Der Fehler selbst trat bei mir weder mit `--repeat-each=20` und 4 Workern noch gedrosselt auf (er ist mit etwa 0,08 % je Zeile selten). Die Ursache ist durch die Messung des Umbruchs belegt, nicht durch einen beobachteten Fehlschlag.

**Was wurde gebaut?**

`web/e2e/structure-tree.spec.ts`:
1. Geräte der Hilfsfunktion `createPlant` heißen `e2e-d-…` statt `e2e-device-…` (Muster `e2e-<kind>-<suffix>` bleibt); Kommentar nennt den Grund.
2. Der Spaltentest wartet auf den gesetzten Zustand: Suchstatus „2 devices shown“ (wie der Test für 375 px) und Schrift Inter geladen (`document.fonts.load`/`ready`); alle sechs Zellen sichtbar.
3. Alle Boxen werden mit einem Aufruf (`page.evaluate`, `getBoundingClientRect`) gelesen, damit kein Rendern zwischen zwei Messungen liegt.
Grenzen unverändert: gleiche linke Kante < 1 px, eine Zeile < 8 px. Keine Toleranz erhöht, kein `retry`, kein Überspringen.

**Wie wurde getestet?**

- Kriterium 1: siehe Ursache (Messung, 20 000 Versuche vorher/nachher).
- Kriterium 2: Grenzen im Diff unverändert (`toBeLessThan(1)` und `toBeLessThan(8)`).
- Kriterium 3: `structure-tree.spec.ts --repeat-each=10`: 60 bestanden. Voller e2e-Lauf wie `ci.yml` (Projekt `twox-092`, Testkonto `e2e-manager` angelegt wie in `ci.yml`): 72 bestanden, 1 übersprungen (M2-Abnahme, lokaler Teil, wie vorgesehen).
- Kriterium 4: Web-Job im Projekt `twox-092-web`: `npm ci`, lint, typecheck, test, build, licenses, `api:generate` alle Exit 0, `git status` danach ohne Unterschied in `web/openapi` und `web/src/api`. e2e siehe oben.
- `down -v` beider Projekte beide Projekte (`twox-092`, `twox-092-web`) Exit 0.

**Zweig und Arbeitsverzeichnis**

- Zweig `worktree-agent-a605da99518a72f86`, Arbeitsverzeichnis `.claude/worktrees/agent-a605da99518a72f86`.

**Abweichungen**

- Nur eine Datei im Produktbereich geändert (`web/e2e/structure-tree.spec.ts`); keine neue Abhängigkeit.
- Ein hilfsweise geschriebener Mess-Test (`probe.spec.ts`) und `.env` (ungetrackt) wurden nicht eingecheckt.
- Ein gedrosselter Messlauf (CPU 40-fach) wurde von mir selbst abgebrochen bzw. lief in Zeitüberschreitungen; er hat für die Aussage keine Bedeutung.
