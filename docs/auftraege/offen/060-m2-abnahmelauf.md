# Auftrag 060 – Abnahmelauf M2 in der Testumgebung

Meilenstein: M2 · Freigabestufe: C · Status: offen

## Ziel

Der Nachweis der Abnahme von M2 in der Testumgebung, in der a7 abnimmt: „Handbücher der Fertigungslinie und des Roboters eingelesen; die Suche findet eine IP-Adresse und eine sinngemäß gestellte Frage; Fehler sind sichtbar“. Die Leitstelle führt den lokalen Teil der Abnahmetests (058) mit den echten Handbüchern aus und legt a7 Ergebnis und Schrittfolge vor. Die Abnahme selbst entscheidet a7.

## Umfang

- Testumgebung mit dem Stand von `main` und dem von a7 gewählten Modell (Frage 2 in 057) neu bauen und starten, Docling eingeschlossen.
- Einlesen vervollständigen: `ingest_versions --missing --commit --user …`, bei Bedarf `--failed`; nach einem Modellwechsel `embed_sections --all --commit --user …`.
- Fehler sichtbar machen nach Frage 2: Docling kurz stoppen und eine eigene Datei hochladen (`docling_unavailable`); eine selbst erzeugte beschädigte PDF-Datei hochladen (`conversion_failed`). Beides ohne Herstellermaterial.
- Lokalen Teil der Browser-Tests ausführen (Testkonto nach Frage 1 in 057).
- `evaluate_search` mit `backend/twox/search/probes/m2.json` als Endstand.
- Ergebnis an a7: Endzustand aller Aufträge, Ergebnis der Tests, Ausgabe von `evaluate_search`, Laufzeiten, Schrittfolge zum Nachmachen im Browser.

## Nicht-Ziele

- Kein Code; gefundene Fehler werden als neue Aufträge vorgeschlagen.
- Keine Abnahme durch die Leitstelle (Stufe C, nur a7).
- Keine Zitate oder Ausschnitte aus Herstellerunterlagen im Bericht.

## Betroffene Bereiche (Ordner, Dateien)

- Testumgebung im Hauptordner (Container, Volumes, lokale `.env`, nicht im Repository)
- `docs/auftraege/offen/060-m2-abnahmelauf.md` (Kurzbericht)

## Akzeptanzkriterien (prüfbar)

Alle Befehle laufen in Git Bash im Hauptordner auf `main`, Compose-Projekt der Testumgebung (ohne `-p`).

0. `docker version` und `docker compose version` enden mit Exit-Code 0; `git status` zeigt `main` ohne lokale Änderungen an getrackten Dateien.
1. `docker compose up -d --wait --wait-timeout 600 db valkey worker api docling` endet mit Exit-Code 0; `check_docling` und `check_llm --embed` (über `docker compose exec -T api python manage.py …`) melden `OK:`.
2. Nach dem Durchlauf steht kein Auftrag in `queued` oder `running`; alle Pflicht-Handbücher nach Frage 1 sind `done`; alle übrigen haben einen sichtbaren Endzustand. Tabelle im Kurzbericht.
3. Die beiden absichtlichen Fehler aus Frage 2 stehen in `/ingest` mit Meldung.
4. Schritt „Create test account“ wie in `ci.yml` (Kennwort nur über den Variablennamen), dann `TWOX_M2_LOCAL=1 TWOX_M2_REQUIRED=<dateinamen> TWOX_M2_FAILED_FILE=<dateiname> docker compose --profile e2e run --rm e2e` (die Variablen reicht `compose.web.yaml` aus 058 durch): alle Fälle bestanden, lokaler Teil von `m2-acceptance.spec.ts` bestanden, Exit-Code 0.
5. `docker compose exec -T api python manage.py evaluate_search < backend/twox/search/probes/m2.json`: Ausgabe im Kurzbericht.
6. Der Kurzbericht enthält die Schrittfolge, mit der a7 die drei Teile der Abnahme im eigenen Browser nachvollzieht, und eine Liste offener Befunde.

## Vorgaben und Hinweise

- **Nachtrag der Leitstelle (E-59, KI optional):** Einbettungen, Vektorsuche und alles, was ein Modell braucht, sind eine aktivierbare Zusatzfunktion. Schalter `TWOX_AI_ENABLED` (Einstellung in `settings.py`, Standard `False`; `.env.example` mit Kommentar). Bei „aus“: kein Aufruf von Ollama, keine Einbettungs-Aufgaben, Einlesen endet nach den Abschnitten erfolgreich, die Suche arbeitet nur mit der Stichwortsuche, Selbsttest und Oberfläche zeigen „KI nicht aktiviert“ als neutralen Zustand (kein Fehler, kein Warnsymbol). Jede KI-abhängige Stelle braucht einen Test für beide Zustände; die CI läuft mit „aus“ und mit „an“ plus Attrappe.

Voraussetzung: 057, 058 und 059 sind nach `main` zusammengeführt bzw. abgeschlossen; a7 hat Frage 2 in 057 (Modell und Abschnittsgröße) entschieden, ein etwaiger Folgeauftrag dazu ist auf `main`. Fragen 1 und 2 hier sind entschieden.

- Welle 12. Ausgeführt von der Leitstelle (Frage 1 in 057).
- **Keine neue Abhängigkeit.**
- Lange Läufe als Hintergrundbefehl.
- Die Handbücher wurden vor M2 hochgeladen und haben nach 057 schon Aufträge; ZIP-Dateien sind `skipped` (sichtbarer Endzustand).
- Pfade mit Benutzernamen nie in Dateien oder Commits.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Kein Push (E-14).

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort a7, 22.11.2026:** Alle Empfehlungen übernommen (E-54 bis E-58).

1. **Welche Handbücher müssen für die Abnahme „eingelesen“ sein?** (ROADMAP: „Handbücher der Fertigungslinie und des Roboters“.)
   - (a) alle PDF- und Office-Handbücher, die in der Testumgebung Geräten der Fertigungslinie und dem UR5e zugeordnet sind (ZIP-Archive ausgenommen, sie sind sichtbar übersprungen);
   - (b) nur die sieben APS-Unterlagen je DE und EN sowie UR5e-Benutzerhandbuch (de) und Software-Handbuch (en); Service-Handbuch und Script-Verzeichnis nur mit sichtbarem Endzustand. Das engt das Abnahmekriterium ein (Änderung am Umfang eines Meilensteins).
   Empfehlung: (a). So wird das Kriterium aus der ROADMAP wörtlich erfüllt; scheitert ein großes Handbuch, kommt der Befund mit Ursache zu a7, statt das Kriterium vorab zu verkleinern.
2. **Wie wird „Fehler sind sichtbar“ belegt?**
   - (a) Docling kurz stoppen und eine Datei hochladen → „Umwandlungsdienst nicht erreichbar“;
   - (b) eine selbst erzeugte, beschädigte PDF-Datei hochladen → „Umwandlung gescheitert“;
   - (c) beides.
   Empfehlung: (c). (a) prüft Netz und Wiederholungen, (b) die Fehlermeldung von Docling; beides mit eigenen Dateien.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
