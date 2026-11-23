# Auftrag 147 – Diagnose: Warum findet die Suche die Belege für die Prüffragen 3, 4, 6 und 7 nicht?

Meilenstein: M3 · Freigabestufe: B (Analyse ohne Codeänderung, E-74) · Status: offen

## Ziel

In den Messläufen 128 und 144 scheitern die Prüffragen 3, 4, 6 und 7 daran, dass ihre Belegstelle nicht im Kontext der Auskunft liegt (Befund B1). 143 (weichere Stichwortsuche) half der Auskunft nicht und ist zurückgenommen (E-73). Der Überschriftenpfad wird bereits mit eingebettet (`backend/twox/ingest/pipeline.py:752`, E-74).

Nach diesem Auftrag liegt a7 eine belegte Diagnose je Frage vor und eine Liste von Varianten mit **gemessener** Wirkung, aus der a7 den eigentlichen Suchauftrag auswählt.

## Umfang

1. **Diagnose je Frage** (3, 3b, 4, 6, 7, 7b nach `backend/twox/search/probes/m3.json`; Wortlaut `yaml` aus `testfactory/questions.yaml` und `probe`):
   - Rang und Abstand jeder erwarteten Fundstelle in der Vektorliste (Tiefe 200, nicht nur 50), in der Stichwortliste und kombiniert.
   - Welche Abschnitte stattdessen vorne liegen (nur Kennung: manifest_id, Seite, Überschriftenpfad als Kennzeichnung, Abstand, Länge) und warum (z. B. allgemeinere Kapitel, Inhaltsverzeichnis, andere Sprachfassung, sehr lange oder sehr kurze Abschnitte).
   - Ob die Belegstelle als eigener Abschnitt existiert und wie sie geschnitten ist (Länge, Überschriftenpfad, ob der entscheidende Satz am Anfang, in der Mitte oder abgeschnitten steht; `TWOX_SECTION_MAX_CHARS`).
   - Sprache: Frage deutsch, Beleg deutsch oder englisch?
2. **Varianten messen** – nur lesend, im Scratchpad oder über `manage.py shell -c`, ohne Änderung an Code, Datenbank oder Einbettungen der Testumgebung. Je Variante Rang der Belegstelle für alle 13 M3-Proben (nicht nur 3/4/6/7, damit Verschlechterungen sichtbar werden) und für die Kontrollfrage der kleinste Abstand:
   - (V1) **Frage umformulieren durch das Chat-Modell** vor der Suche (z. B. Frage in Aussageform oder in die Sprache des Handbuchs übersetzen; gemma4 über die vorhandene Schnittstelle, Temperatur 0). Zeit je Frage nennen.
   - (V2) **Mehrere Anfragen**: Originalfrage plus Umformulierung, Ergebnislisten per RRF verschmelzen.
   - (V3) **Einbettung nur des Textes** ohne Überschriftenpfad bzw. nur der Überschrift: an einer kleinen Stichprobe (die Belegstellen und die Abschnitte, die sie verdrängen) mit bge-m3 neu einbetten, nur im Speicher, und Abstände vergleichen.
   - (V4) **Kleinere Abschnitte**: dieselben Stichproben in Teilstücke (z. B. 500 oder 1000 Zeichen) teilen, im Speicher einbetten, besten Abstand je Abschnitt vergleichen.
   - Weitere Varianten nur, wenn sie ohne neue Abhängigkeit und ohne neues Modell auskommen (kein `ollama pull`). Ideen, die ein neues Modell bräuchten (z. B. Reranker), nur als Vorschlag mit Begründung nennen, nicht messen.
3. **Bericht mit Empfehlung:** Tabelle Variante × Probe (Rang), Recall@8 kombiniert, Laufzeit, Aufwand der Umsetzung (Code, Neueinbettung ja/nein, Dauer für ca. 5 000 Abschnitte), Risiko für die Kontrollfrage. Daraus Optionen mit Empfehlung für den Suchauftrag unter „Fragen an a7“.

## Nicht-Ziele

- Keine Änderung an Code, Migrationen, `.env`, Einstellungen oder Daten der Testumgebung; kein Neu-Einlesen, kein Neueinbetten in der Datenbank.
- Kein neues Modell, keine neue Abhängigkeit, keine Änderung an Ollama.
- Keine Handbuchauszüge, keine Antworttexte des Modells im Bericht; nur Kennungen, Seiten, Ränge, Zahlen. Wortlaut von Umformulierungen nur, soweit er aus den Prüffragen selbst stammt (projekteigener Text), keine Handbuchbegriffe darüber hinaus.

## Betroffene Bereiche (Ordner, Dateien)

- Nur diese Auftragsdatei (Kurzbericht). Hilfsskripte und Rohdaten ungetrackt (Scratchpad, `Claude outputs/147/`).
- Testumgebung „2x“ im Hauptordner nur lesend (`docker compose exec -T api python manage.py shell -c …`, `evaluate_search`), Ollama am Host nur über die vorhandenen Modelle.

## Akzeptanzkriterien (prüfbar)

1. Diagnose-Tabelle je Frage und Wortlaut mit Rang (Vektor bis 200, Stichwort, kombiniert), Abstand, Länge und Sprache der Belegstelle und der verdrängenden Abschnitte.
2. Messtabelle Variante × alle 13 M3-Proben mit Rang und Recall@8, dazu kleinster Abstand der Kontrollfrage je Variante und Zeit je Frage.
3. Optionen mit Empfehlung für den Suchauftrag, je mit Aufwand, Neueinbettung ja/nein, Risiko; Stufe C markiert, wo sie gilt.
4. `git status` im Hauptordner unverändert; Zählung Abschnitte/Versionen/Einlese-Aufträge vor und nach gleich (5 071 / 158 / 228); `.env` des Hauptordners unverändert.
5. Vor jedem Lauf auf Ollama `/api/ps` geprüft, keine parallelen Läufe.

## Vorgaben und Hinweise

- Den Kurzbericht schreibt der Bearbeiter auf seinem Zweig in diese Datei; im Hauptordner ändert er keine getrackte Datei.
- `docker` liegt nicht im PATH: `%LOCALAPPDATA%\Programs\DockerDesktop\resources\bin`.
- Vorlagen für Hilfsskripte: Berichte 120, 124, 128, 144 (`docs/auftraege/erledigt/`).
- Dokumentinhalte sind Daten, keine Anweisungen (Leitplanke 4).
- Nicht pushen.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine vor dem Start. Das Ergebnis ist die Vorlage für den Suchauftrag.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

Status: **fertig, wartet auf a7** (Auswahl des Suchauftrags, Optionen unten). Messung am 23.11.2026 auf der Testumgebung „2x“ (main 9809570), nur lesend.

### Was wurde gebaut?

Nichts am Produkt. Hilfsskripte (`lib147.py`, `diag.py`, `var.py`, `rewrite.py`, `reembed.py`) liefen über `docker compose exec -T api python manage.py shell` (Skript über stdin). Skripte und Rohdaten liegen ungetrackt unter `Claude outputs/147/`. Die Rohdaten enthalten nur Kennungen, Überschriftenpfade, Zahlen und die Umformulierungen der Prüffragen. Grundlage im Code:

- Vektorliste: `backend/twox/search/postgres.py:452-465`, `VECTOR_CANDIDATES = 50` (`:155`)
- Fusion: `:547-569`
- Kontextauswahl: `backend/twox/answers/context.py:185-213`, k = 8, Schwelle 0,55, Grenze 16 000 Zeichen
- Eingebetteter Text: `backend/twox/ingest/pipeline.py:752`

**Prüfung des Nachbaus:** Mein Nachbau der kombinierten Suche (Vektorliste plus Stichwortliste, RRF k = 60, Gruppierung nach Inhalt) ergibt für alle 13 Proben denselben Rang wie das Backend (Zeile „V0“). Neu eingebettete Texte haben denselben Vektor wie die gespeicherten (größte Kosinus-Distanz 2·10⁻¹⁶).

### Hauptbefunde

- **B1a – Die Vektorliste ist faktisch nur 5 bis 10 Inhalte tief (Programmfehler, Hauptursache).**
  - `VECTOR_CANDIDATES = 50` begrenzt die *Zeilen* (Abschnitte), nicht die Inhalte. Die APS-Handbücher liegen an 11 Geräten (die Quick-Start-Anleitung an 22), also mit 11 gleichen Abschnitten je Inhalt.
  - 50 Zeilen ergeben deshalb nur 5 bis 7 verschiedene Treffer. Beispiele: Frage 3 `yaml` hat 5 kombinierte Treffer, Frage 3 `probe` 7, Frage 4 `probe` 7.
  - Alles ab Inhaltsrang ≈ 6 kann den Kontext nie erreichen. Die Kontextauswahl bekommt dann 4 bis 7 Quellen statt bis zu 8.
- **B1b – Die Stichwortliste trägt bei Fragen nichts bei.** `websearch_to_tsquery` verknüpft alle Wörter mit UND. Für keinen der zehn Wortlaute der Fragen 3, 3b, 4, 6, 7 und 7b findet die Stichwortsuche eine Belegstelle. Die kombinierte Liste ist damit reine Vektorliste. 143 hat das schon gezeigt (E-73).
- **B1c – Lange Abschnitte verwässern den Vektor.**
  - Die Belege zu 3, 3b und 4 stehen in den Abschnitten S. 36 und S. 38 mit 1 230 bis 1 850 Zeichen. S. 36 ist an `TWOX_SECTION_MAX_CHARS = 2000` geteilt (Fortsetzung auf S. 36–37).
  - Die Stichworte stehen bei S. 36 am Anfang (MQTT bei 2–6 %), bei S. 38 in der Mitte (MQTT bei 33 %, Node-RED bei 41 %). Der Rest des Abschnitts behandelt anderes.
  - Teilt man in Stücke ≤ 1 000 Zeichen, fällt die Distanz der Belegstelle von 0,49–0,51 auf 0,43 und der Rang von 13–21 auf 1 (siehe V4).
- **B1d – Der Wortlaut zieht Abschnitte über dasselbe Oberflächenwort vor.**
  - „Transportfahrzeug/Transportwagen“ führt zu den Abschnitten „Prüfen auf Transportschäden“ und zu UR5e-Transportkapiteln.
  - „Zentralsteuerung/Zentrale“ führt zur Cloud-Kopplung und zum Auslesen der Version.
  - „CPU“ führt zum Datenblatt des Raspberry Pi (Inhaltsverzeichnis).
  - Inhaltsverzeichnisse erscheinen vereinzelt vorn (ur5e-script-directory „Contents“, rpi4b-datasheet „Contents“). Sie sind nicht die Hauptursache.
- **Sprache:** Die Fragen sind deutsch, die Belege liegen deutsch und englisch vor. Bei 7 und 3b liegt die **englische** Fassung deutlich näher als die deutsche: Frage 7 `probe` hat EN Rang 6 und DE Rang 90.
- **Frage 7 hat eine eigene Ursache.** Die Belegstelle S. 22 hat nur 885 Zeichen, ist also nicht verwässert. Der Wortlaut der Frage („Spur verliert“, „Markierung am Boden“) liegt einfach weit weg, Distanz 0,48 bis 0,59. Die zweite erwartete Stelle S. 26–28 hat den kaputten Überschriftenpfad „[] ×“ (Konvertierung) und den Rang 82 bis 1 750.

### Diagnose je Frage und Wortlaut (Kriterium 1)

Ränge zählen Inhalte, Kopien an mehreren Geräten zählen einmal. Spalten:

- **Vek** = Rang in der exakten Vektorliste (alle 2 737 Inhalte, nicht nur Tiefe 200), dazu die Distanz
- **Stw** = Rang in der Stichwortliste
- **Komb** = Rang im Backend
- **Ktx** = Nummer der Quelle in `select_context`

Gezeigt ist jeweils die beste erwartete Belegstelle. Alle sechs Wortlaute der Fragen sind deutsch.

| Probe / Wortlaut | Vek (d) | Stw | Komb | Ktx | Belegstelle (Sprache, Länge, Schnitt) | vorn stattdessen (Vek 1–3, d) |
| --- | --- | --- | --- | --- | --- | --- |
| 3 `yaml` | 13 (0,479) | – | – | – (4 Quellen) | doc-de S. 36 (de, 1 571 Z., MQTT bei 6 %, geteilt an 2 000) | doc-de S. 32–33 Cloud-Kopplung (0,368), software-update-en S. 16 (0,384), doc-en S. 32 (0,422) |
| 3 `probe` | 20 (0,512) | – | – | – (6) | doc-de S. 38 (de, 1 682 Z., MQTT bei 34 %) | doc-de S. 32–33 (0,445), software-update-en S. 16 (0,449), doc-en S. 32 (0,472); Rang 5: script-directory „Contents“ (Inhaltsverzeichnis) |
| 3b `probe` | 13 (0,492) | – | – | – (8) | doc-en S. 36 (en, 1 847 Z., MQTT bei 5 %); de S. 36 Rang 22 | software-versions-en S. 2 CCU (0,455), script-directory „Contents“ (0,457), doc-en S. 17–18 (0,469) |
| 4 `yaml` | 77 (0,531) | – | – | – (8) | doc-en S. 36 (en, 1 847 Z., OPC UA bei 61 %, Node-RED bei 80 %) | Repository-Datei drill/modules „6.3 Common Commands“ (0,447, 153 Z.), script-directory „Contents“ (0,450), doc-en S. 18–19 (0,457) |
| 4 `probe` | 8 (0,484) | – | – | – (7) | doc-en S. 38 (en, 1 582 Z., MQTT bei 33 %); de S. 38 Rang 12 | doc-en S. 17–18 (0,434), Repository „6.3 DRILL Overview“ (0,463), doc-en S. 26–27 „[] ×“ (0,471) |
| 6 `yaml` | 91 (0,561) | – | – | – (8) | doc-en S. 36 (en, 1 847 Z., S7-1200 bei 49 %); doc-de S. 34 (de, 902 Z., beide CPU-Angaben bei 34–36 %) Rang 115 | rpi4b-datasheet „Contents“ (0,463), rpi4b-datasheet „2.1 Hardware“ (0,475), change-ip-address-en S. 6 (0,491) |
| 6 `probe` | **4** (0,473) | – | **4** | **4, 6** | doc-de S. 34 (de, 902 Z.) und doc-de S. 38 (Rang 6) | assignment-plans-en S. 20–21 (0,463), software-update-de S. 7–8 (0,467), change-ip-address-de S. 13–14 (0,470) |
| 7 `yaml` | 56 (0,515) | – | – | – (8) | doc-en S. 22 (en, 885 Z., Schritte bei 31–44 %); de S. 22 Rang 180 | quick-start-en S. 6 Transportschäden (0,403), quick-start-de S. 6 (0,418), doc-de S. 7 (0,422) |
| 7 `probe` | **6** (0,479) | – | **7** | **6** | doc-en S. 22 (en, 885 Z.); de S. 22 Rang 90 | quick-start-en S. 6 (0,431), Dokument fc2c7d0d90 S. 21–22 (0,466; nicht im Manifest), ur5e-service-manual-en S. 106 (0,472) |
| 7b `probe` | 34 (0,545) | – | – | – (8) | doc-en S. 22 (en, 885 Z.); de S. 22 Rang 328 | ur5e-service-manual-en S. 9 „GROUND“ (0,442, 20 Z.), quick-start-en S. 6 (0,490), quick-start-de S. 6 (0,499) |

Kurzzeichen:

- doc-de/-en = aps-documentation-de/-en
- „Repository“ = die nach D2 eingelesenen Dateien aus aps-repository-dev

Weitere Beobachtungen:

- Die verdrängenden Abschnitte sind in der Regel allgemeinere Kapitel derselben APS-Unterlagen oder UR5e-Kapitel mit gleichem Oberflächenwort. Darunter sind auch sehr kurze Abschnitte (15 bis 153 Zeichen).
- Eine andere Sprachfassung derselben Stelle verdrängt nur bei 7 (`yaml`/`probe`): quick-start-en S. 6 und doc-en S. 7 sind derselbe Text.
- Die Schwelle 0,55 schließt die Belegstelle von 6 `yaml` (0,561) und von 7b in der deutschen Fassung (0,59) zusätzlich aus.

### Messung der Varianten (Kriterium 2)

**Kombinierter Rang** der ersten erwarteten Fundstelle je M3-Probe, Recall@8 über 13 Proben. Spalte K11 = kleinster Abstand unter den ersten 8 Treffern der Kontrollfrage.

„rows50“ ist das heutige Verhalten: 50 Abschnittszeilen in der Vektorliste. „dedup50“ nimmt 50 verschiedene Inhalte.

| Variante | 1 | 2 | 3 | 3b | 4 | 5 | 6 | 7 | 7b | 8 | 9 | 10 | 10b | R@8 | K11 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Backend heute (= V0 rows50, nachgebaut identisch) | 1 | 1 | – | – | – | 2 | 4 | 7 | – | 9 | 1 | 1 | 7 | 8/13 | 0,510 |
| V5 Kopien vor dem Limit zusammenfassen (dedup50) | 1 | 1 | 21 | 13 | 8 | 2 | 4 | 7 | 35 | 9 | 1 | 1 | 7 | 9/13 | 0,510 |
| V1a Umformulierung als deutscher Aussagesatz, rows50 | 8 | 4 | – | – | – | 2 | 2 | – | – | 8 | 1 | 2 | 30 | 7/13 | 0,435 |
| V1a dto., dedup50 | 8 | 4 | 40 | 32 | 24 | 2 | 2 | – | – | 8 | 1 | 2 | 30 | 7/13 | 0,435 |
| V1b Übersetzung ins Englische, rows50 | 2 | 1 | – | – | – | 3 | 6 | 1 | – | 7 | 1 | 1 | 2 | 9/13 | 0,488 |
| V1b dto., dedup50 | 2 | 1 | 23 | 11 | – | 3 | 6 | 1 | – | 7 | 1 | 1 | 2 | 9/13 | 0,488 |
| V2 Original + EN (RRF), rows50 | 1 | 1 | – | – | – | 4 | 8 | 1 | – | 3 | 1 | 1 | 4 | 9/13 | 0,488 |
| V2 Original + EN (RRF), dedup50 | 1 | 1 | 19 | 8 | 21 | 3 | 15 | 1 | 50 | 3 | 1 | 1 | 4 | 9/13 | 0,493 |
| V2 Original + DE + EN (RRF), rows50 | 2 | 1 | – | – | – | 3 | 2 | 5 | – | 3 | 1 | 1 | 8 | 9/13 | 0,435 |
| V3a nur Text ohne Überschrift, dedup50 | 2 | 1 | 22 | 23 | 17 | 4 | 11 | – | – | – | 2 | 2 | 32 | 5/13 | 0,491 |
| V3b nur Überschriftenpfad, dedup50 | 39 | 26 | 19 | – | 27 | 7 | 1 | 1 | 11 | – | 9 | 2 | 12 | 4/13 | 0,384 |
| **V4a Teilstücke ≤ 1 000 Z. + Überschrift, dedup50** | 1 | 1 | **1** | **1** | **2** | 2 | **1** | 9 | 45 | 7 | 1 | 1 | 7 | **11/13** | 0,510 |
| V4b Teilstücke ≤ 500 Z. + Überschrift, dedup50 | 4 | 1 | 1 | 1 | 2 | 2 | 1 | 25 | – | 10 | 1 | 1 | 10 | 9/13 | 0,475 |
| V4c Abschnitt + Teilstücke 1 000 (kleinster Abstand), dedup50 | 1 | 1 | 1 | 1 | 2 | 2 | 1 | 10 | 48 | 11 | 1 | 1 | 8 | 10/13 | 0,510 |
| V4a mit EN-Anfrage, dedup50 | 1 | 1 | 1 | 1 | 5 | 4 | 5 | 1 | – | 10 | 1 | 1 | 4 | 11/13 | 0,471 |
| **V4a + V2 (Original + EN, RRF), dedup50** | 1 | 1 | 1 | 1 | 1 | 3 | 2 | **1** | 62 | 4 | 1 | 1 | 6 | **12/13** | ≥ 0,471 |

**Zu V3 und V4:**

- Ich habe nicht nur eine Stichprobe neu eingebettet, sondern **alle 2 737 verschiedenen durchsuchbaren Inhalte**, im Speicher mit bge-m3 über die vorhandene Schnittstelle. Die Ränge gelten deshalb für den ganzen Bestand und nicht nur für eine Stichprobe.
- Das Teilen geschah an Leerzeichen ohne Überlappung. Vor jedes Teilstück kam der Überschriftenpfad wie in `embedding_text`.
- Ein Abschnitt bekommt den kleinsten Abstand seiner Teilstücke. Die Stichwortliste blieb unverändert.

**Distanzen der Belegstelle:**

| Frage | vorher (Abschnitt) | V4a (Teilstücke ≤ 1 000) |
| --- | --- | --- |
| 3 | 0,512 | 0,431 |
| 3b | 0,492 | 0,427 |
| 4 | 0,484 | 0,424 |
| 6 | 0,473 | 0,446 |
| 7, 7b | unverändert | unverändert (Abschnitt hat 885 Zeichen und wird nicht geteilt) |

**Zeiten:**

- **V1 (Chat-Modell):**
  - gemma4:31b-it-qat, Temperatur 0, Seed 147, bei geladenem Modell 0,5 bis 1,1 s je Umformulierung, im Mittel ≈ 0,8 s.
  - Keine Umformulierung enthält ein key_fact.
  - Der Wortlaut der Umformulierungen steht nur in den Rohdaten, nicht hier.
- **Suche:** In V2 kommt je weitere Anfrage ein Suchlauf dazu (Einbettung der Anfrage und SQL). Seine Dauer habe ich nicht gesondert gemessen.
- **Neueinbettung (gemessen, teils parallel zu 148):**

  | Variante | Texte | Dauer |
  | --- | --- | --- |
  | Nur Text | 2 737 | 77 s |
  | Teilstücke 1 000 | 3 513 | 148–163 s |
  | Teilstücke 500 | 5 293 | 141 s |

  Hochgerechnet auf ≈ 5 071 Abschnitte, also alle Kopien: Teilstücke 1 000 ergeben ≈ 6 500 Texte in ≈ 4 bis 5 min.

### Optionen für den Suchauftrag (Kriterium 3)

| Option | Inhalt | Wirkung R@8 | Aufwand | Neueinbettung | Risiko Kontrollfrage | Stufe |
| --- | --- | --- | --- | --- | --- | --- |
| A | V5: Kopien in der Vektorabfrage vor dem `LIMIT` zusammenfassen. `DISTINCT ON` über den Inhaltsschlüssel oder ein Limit in Inhalten; alternativ `VECTOR_CANDIDATES` erhöhen. | 8 → 9 | klein, nur `search/postgres.py` plus Tests | nein | keins (0,510 unverändert) | B (Fehlerbehebung im Suchbereich) |
| B | A + V4a: Teilstücke ≤ 1 000 Zeichen einbetten. B1 schneidet einfach kleinere Abschnitte (`TWOX_SECTION_MAX_CHARS=1000`, neu einlesen). B2 legt eigene Teilstück-Vektoren je Abschnitt an; der Abschnitt bleibt die Quelle. | 8 → 11 | B1: Einstellung, neu einlesen, Kontextquellen werden kürzer. B2: Datenmodell (neue Tabelle) und Einbettungsschritt. | ja, ≈ 5 min | gering (0,510 unverändert) | C (B1: Neu-Einlesen und Verlust; B2: Datenmodell) |
| C | B + V2: zusätzlich eine englische Übersetzung der Frage durch das Chat-Modell, Ergebnislisten per RRF. | 8 → 12 | mittel, Aufruf vor der Suche in `answers` | wie B | mittel (Abstand sinkt auf 0,471; die Schwelle 0,55 schützt die Kontrollfrage schon heute nicht) | C (Architektur: Modell im Suchpfad) |
| D | V1/V2 allein ohne A/B | höchstens 9 | mittel | nein | mittel | C; nicht empfohlen, hilft 3, 3b, 4 und 7b nicht |
| – | V3a/V3b (ohne oder nur Überschrift) | 4–5 | – | ja | höher | verwerfen (verschlechtert) |

**Empfehlung:** Zuerst **A** als eigener kleiner Auftrag. Er ist Voraussetzung für alles Weitere: Mit Teilstücken stiegen die Kopienzeilen sonst noch weiter.

Danach **B2** (Teilstück-Vektoren, Abschnitt bleibt Quelle und Zitiereinheit). B2 ist B1 vorzuziehen, weil die Zitatprüfung und die Kontextgrenze am Abschnitt hängen.

**C** erst nach einem Messlauf mit A und B. Es löst vor allem Frage 7 und kostet ≈ 0,8 s je Frage.

**Ungelöst bleibt 7b:** Der Wortlaut ohne Fachbegriff erreicht die Belegstelle mit keiner Variante. Das ist ein Fall für die Bewertung, nicht für die Suche.

**Vorschlag ohne Messung (bräuchte ein neues Modell):** Ein Cross-Encoder-Reranker über die ersten 30 bis 50 Inhalte, z. B. aus der bge-reranker-Familie. Er bewertet Frage und Abschnitt gemeinsam und würde Oberflächentreffer wie „Transportschäden“ zurückstufen. Er braucht ein neues Modell und eine Lizenzprüfung, also Stufe C.

**Nebenbefund:** Der Überschriftenpfad „[] ×“ in aps-documentation-en S. 26–28 deutet auf einen Konvertierungsfehler der Überschrift hin. Das ist ein eigener kleiner Auftrag, falls gewünscht.

### Wie wurde getestet? (Kriterien 4 und 5)

- **Zählung vor und nach den Messungen:** 5 071 Abschnitte / 158 Versionen / 228 Einlese-Aufträge, unverändert.
- **`.env`:** SHA-256 vorher und nachher gleich (FF37C954…).
- **`git status` im Hauptordner:** vorher und nachher gleich. Es gibt nur die schon vorhandenen ungetrackten `*.log`; `Claude outputs/` ist ignoriert.
- **Nur lesend:** keine Schreibzugriffe auf die Datenbank. Neue Vektoren lagen nur im Speicher des Shell-Prozesses.
- **Ollama:** vor jedem Lauf `/api/ps` geprüft (die Skripte protokollieren `OLLAMA_PS`). Der Lauf mit dem Chat-Modell startete erst, nachdem gemma 160 s unbenutzt war; keine parallelen Chat-Läufe.
- **Einbettungsläufe:** Die Läufe mit bge-m3 überschnitten sich zeitlich teils mit 148. Deshalb sind die Zeiten der Neueinbettung Obergrenzen.

### Zweig und Arbeitsverzeichnis

- Zweig `worktree-agent-a32a0d0db211e7d12`, Arbeitsverzeichnis `.claude/worktrees/agent-a32a0d0db211e7d12`.
- Geändert ist nur diese Auftragsdatei.

### Abweichungen

- **V3 und V4 auf dem ganzen Bestand** statt an einer Stichprobe. Grund: Nur so sind Ränge für alle 13 Proben belastbar. Weiterhin nur im Speicher und ohne neues Modell.
- **Vektorränge exakt** über alle Inhalte, also tiefer als 200. Gezählt ist auf Inhaltsebene: Kopien zählen einmal.
- **Zusätzliche Variante V5** (Kopien vor dem Limit zusammenfassen). Sie ergab sich aus der Diagnose und braucht weder eine Abhängigkeit noch ein Modell.
