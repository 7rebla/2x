# Auftrag 060 – Abnahmelauf M2 in der Testumgebung

Meilenstein: M2 · Freigabestufe: C · Status: wartet auf a7

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

## Kurzbericht (Leitstelle, 22.11.2026)

**Status: wartet auf a7.** Lauf in der Testumgebung „2x“ auf `main` (Stand nach 065, vor 066), Modell bge-m3, Abschnittsgröße 2 000 (E-60). Kriterien 0, 1, 2, 3, 5 erfüllt; Kriterium 4 nicht erfüllt (zwei Befunde zur Suchgüte, siehe unten); Kriterium 6 mit diesem Bericht.

| Nr. | Ergebnis | Nachweis |
| --- | --- | --- |
| 0 | erfüllt | Docker Engine 29.9.3, Compose 5.7.0; `git status` ohne Änderungen an getrackten Dateien |
| 1 | erfüllt | `up -d --wait … docling` Exit 0 (11:02); `check_docling`: `OK: docling-serve 1.38.2`; `check_llm --embed`: `OK: … bge-m3 … 1024 dimensions` |
| 2 | erfüllt | `ingest_versions --missing --commit`: nichts mehr offen. Endzustand aller 223 Aufträge: 221 `done`, 1 `failed`/`docling_unavailable`, 1 `failed`/`conversion_failed` (beide absichtlich). Alle 21 Pflicht-Handbücher (PDF, Fertigungslinie und UR5e) `done`; dazu BetrSichV (Testdatei) und vier OPNsense-Markdown-Seiten `done` |
| 3 | erfüllt | Eigene einseitige PDF bei gestopptem Docling hochgeladen (11:02:59): nach 224 s `failed`/`docling_unavailable`; danach Docling gestartet. Selbst erzeugte beschädigte PDF: nach Sekunden `failed`/`conversion_failed`. Beide stehen in `/ingest` (Vorgabe „Offen“) mit Meldung („Der Umwandlungsdienst (Docling) war nicht erreichbar …“, „Die Umwandlung der Datei ist gescheitert.“), technischen Angaben und „Erneut einlesen“ – in Chrome geprüft |
| 4 | **nicht erfüllt** | Testkonto wie in `ci.yml` angelegt; lokaler Teil (`-g "local part"`, `TWOX_M2_REQUIRED` = 21 Handbücher, `TWOX_M2_FAILED_FILE=abnahme-060-defekt.pdf`) scheitert nach 2,6 min am Schritt „IP address of the central control“: `192.168.0.100` steht nicht unter den ersten 3. Die vorigen Schritte (Pflicht-Handbücher eingelesen, nichts offen) liefen durch. Den CI-Teil der Suite habe ich in „2x“ bewusst nicht laufen lassen (er legt Testgeräte und Dateien an); er ist in der CI grün |
| 5 | erfüllt | `evaluate_search` (Ausgabe unten) |
| 6 | erfüllt | Schrittfolge und Befunde unten |

**`evaluate_search`, Endstand** (Rang der ersten richtigen Fundstelle Stichwort / Vektor / zusammen): ip-ccu 5 / 9 / 4; ip-drill-plc 10 / 11 / 11; question-1 – / 4 / 4; question-3 – / – / –; question-7 – / – / –; question-9 – / 1 / 12; question-10 – / 1 / 3. Zusammen: Recall@5 0,429, Recall@10 0,429, MRR 0,144; Mittel 52 ms je Anfrage.

**Befunde (an a7):**

1. **IP-Adresse:** Für `192.168.0.100` stehen vorne ein Router-Handbuch (TL-WR902AC, S. 57, die Adresse steht dort als Beispiel), auf Rang 2 die **englische** APS-Dokumentation S. 38 (dieselbe Stelle wie die deutsche, mit der Adresse) und auf Rang 4 die deutsche APS-Dokumentation S. 38. Probe und Abnahmetest werten nur die deutsche Ausgabe als richtig. Die Suche findet die richtige Stelle also auf Rang 2 – in der anderen Sprachfassung.
2. **Prüffrage 9 (Traglast UR5e):** In der Vektorsuche auf Rang 1, zusammen auf Rang 12 – auch nach 063 verdrängen Abschnitte mit „UR5e“ (in Stichwort- und exakter Liste zugleich) den besten Treffer. Der Abnahmetest verlangt die ersten 5.
3. Prüffragen 3 und 7 werden in keiner Liste gefunden (bekannt seit 057, nicht Teil des Abnahmetests).

**Schrittfolge für a7 im eigenen Browser** (http://127.0.0.1:8000, eigenes Konto):

1. **Eingelesen:** „Einlesen“ → Status „Alle“: alle Handbücher mit „Eingelesen“, Seiten und Abschnitten; Gerät z. B. „Zentralsteuerung“ oder „UR5e“ öffnen → Spalte „Einlesen“ der Dateien.
2. **IP-Adresse:** „Suche“ → `192.168.0.100` → Treffer mit Marke „Exakt“, darunter APS-Dokumentation S. 38 (en Rang 2, de Rang 4); Link zur Datei.
3. **Sinngemäße Frage:** „Suche“ → z. B. „Wie viel darf der Roboterarm tragen?“ oder eine eigene Frage ohne die Wörter der Fundstelle → Treffer mit Marke „Bedeutung“, Seitenangabe.
4. **Fehler sichtbar:** „Einlesen“ (Vorgabe „Offen“) → die zwei Aufträge „Abnahme 060“ mit Meldung, „Technische Angaben“ und „Erneut einlesen“; dieselben auf der Geräteseite „SPS Bohrstation“.

**Laufzeiten:** Einlesen insgesamt aus 057 (21 min für 1 099 Seiten); Fehlerprobe Docling aus 224 s, beschädigte PDF wenige Sekunden; lokaler Abnahmetest 2,6 min bis zum Abbruch.

**Offen:** Entscheidung zu den Befunden 1 und 2 (STATUS „Wartet auf a7“, Punkt 14); danach den lokalen Teil erneut laufen lassen.

### Wiederholung nach 067 (22.11.2026, 13:11–13:15)

Stand `main` nach 067 und 075, Testumgebung neu gebaut, Testkonto aktualisiert, lokaler Teil wie oben.

- **Bestanden:** kein Auftrag offen; alle 21 Pflicht-Handbücher eingelesen; IP-Adresse `192.168.0.100` unter den ersten 3 (Rang 2, englische APS-Dokumentation S. 38); Prüffrage 9 (Traglast, eigene Formulierung des Tests) unter den ersten 5 (Rang 1).
- **Nicht bestanden:** Prüffrage 10 in der Formulierung des Tests („Wie gibt man den UR5e wieder frei, wenn eine Schutzeinrichtung ihn angehalten hat?“) – die richtige Fundstelle (Software-Handbuch S. 46) steht erst auf Rang 10, verlangt sind die ersten 5. In der Formulierung der Probe (`m2.json`, mit „Safeguard Stop“) steht dieselbe Stelle auf Rang 1. Die Treffer hängen also stark von der Wortwahl ab.
- **Nicht erreicht:** Der letzte Schritt (absichtlich gescheiterter Auftrag mit Meldung) lief wegen des Abbruchs nicht; ihn hat die Leitstelle im ersten Lauf in Chrome geprüft (Kriterium 3).
- **`evaluate_search`:** kombiniert Recall@5 0,571, Recall@10 0,857, MRR 0,535 (Ränge: ip-ccu 2, ip-drill-plc 10, question-1 1, question-3 –, question-7 7, question-9 1, question-10 1).

**Bewertung der Leitstelle:** Das Abnahmekriterium der ROADMAP („die Suche findet eine IP-Adresse und eine sinngemäß gestellte Frage“) ist erfüllt (IP Rang 2, Prüffrage 9 Rang 1); der Abnahmetest verlangt zusätzlich Prüffrage 10 in einer zweiten Formulierung. Entscheidung über die Abnahme von M2 bei a7 (STATUS „Wartet auf a7“, Punkt 16).
