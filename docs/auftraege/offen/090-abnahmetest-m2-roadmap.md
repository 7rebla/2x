# Auftrag 090 – Abnahmetest M2 auf das ROADMAP-Kriterium zurückführen

Meilenstein: M2 · Freigabestufe: C (entschieden mit E-67) · Status: zur Prüfung

Voraussetzung: E-67; 058 und 067 sind auf `main`.

## Ziel

Der lokale Teil des Abnahmetests (`web/e2e/m2-acceptance.spec.ts`) verlangt zwei sinngemäße Fragen (Prüffragen 9 und 10) unter den ersten fünf Treffern. Die ROADMAP verlangt eine. Nach E-67 prüft der Test das ROADMAP-Kriterium; Prüffrage 10 bleibt als bekannte Schwäche für M3 dokumentiert.

## Umfang

- `web/e2e/m2-acceptance.spec.ts`, lokaler Teil: Prüffrage 9 bleibt Pflicht (erste 5). Prüffrage 10 wird nicht mehr als Bedingung geprüft, sondern ihr Rang wird nur ausgegeben (z. B. `test.info().annotations`), damit er im Bericht sichtbar bleibt. Die übrigen Schritte (eingelesen, IP-Adresse, gescheiterter Auftrag) bleiben unverändert.
- Kommentar im Test mit Verweis auf E-67.
- `docs/ARCHITECTURE.md`, Grenzen der Suche: Wortwahl-Abhängigkeit mit dem Beispiel Prüffrage 10 (Rang 10 bzw. 1 je nach Formulierung) als bekannte Grenze, Verweis auf M3.

## Nicht-Ziele

- Keine Änderung an Suche, Probe `m2.json` oder CI-Teil des Tests.

## Betroffene Bereiche (Ordner, Dateien)

- `web/e2e/m2-acceptance.spec.ts`
- `docs/ARCHITECTURE.md` (nur der Grenzen-Punkt zur Suche)

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Web-Job (lint, typecheck) und e2e wie in `ci.yml` grün (lokaler Teil übersprungen).
2. `down -v` der eigenen Compose-Projekte endet mit Exit 0.

Den lokalen Teil gegen die Handbücher führt die Leitstelle danach in „2x“ aus.

## Vorgaben und Hinweise

- Herkunft: E-67 (a7, 22.11.2026).

## Fragen an a7 (mit Optionen und Empfehlung)

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- **Was wurde gebaut?** `web/e2e/m2-acceptance.spec.ts`: `Probe` hat das Feld `required`. Prüffrage 1 und 9 bleiben Pflicht (erste 3 bzw. 5). Prüffrage 10 wird weiter gestellt, ihr Rang über alle Treffer (oder „not found“) steht als Annotation `rank` im Bericht; keine Bedingung mehr. Für jede Probe wird der Rang ausgegeben. Kommentare mit Verweis auf E-67. Übrige Schritte unverändert. `docs/ARCHITECTURE.md`, Abschnitt „Limits and known gaps / Search“: neuer Punkt „Depends on the wording“ mit Prüffrage 10 (Rang 1 bzw. 10 je nach Formulierung), Verweis auf M3.
- **Wie wurde getestet?** Kriterium 0: `docker version` und `docker compose version` Exit 0. Kriterium 1: Web-Job (Projekt twox-090-web) lint Exit 0, typecheck Exit 0; e2e wie in `ci.yml` (Projekt twox-090, API-Port 18090, Testkonto angelegt) Exit 0, 55 bestanden, 1 übersprungen (lokaler Teil). Kriterium 2: `down -v` beider Projekte Exit 0.
- **Zweig und Arbeitsverzeichnis:** `worktree-agent-afdbbd679a813b012`, `.claude/worktrees/agent-afdbbd679a813b012`
- **Abweichungen:** keine. Die Rang-Annotation gilt auch für die Pflicht-Proben (zusätzliche Ausgabe, keine Änderung der Bedingung).

Status: zur Prüfung
