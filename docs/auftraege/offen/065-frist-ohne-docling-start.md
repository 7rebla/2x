# Auftrag 065 – Frist für Einlese-Aufträge, deren Docling-Aufgabe nie startet

Meilenstein: M2 · Freigabestufe: B · Status: zur Prüfung

Voraussetzung: 048 und 049 sind nach `main` zusammengeführt.

## Ziel

Die Frist eines Einlese-Auftrags zählt ab dem ersten `started` von Docling (046). Bleibt eine Docling-Aufgabe dauerhaft `pending` (Docling hängt, Warteschlange verloren), hat der Auftrag keine Frist: `poll` fragt weiter ab, schreibt bei jeder Abfrage `updated_at` (seit 048), und `ingest_versions --stuck` greift deshalb auch nicht. Nach diesem Auftrag endet ein solcher Auftrag nach einer festen Zeit mit `timeout`.

## Umfang

- `backend/twox/ingest/pipeline.py`, `_deadline_passed`: Gibt es kein `docling_started_at`, gilt eine Frist ab dem Einreichen bei Docling (bzw. ab `started_at` des Auftrags, falls kein eigener Zeitpunkt vorliegt) von `TWOX_INGEST_TIMEOUT_SECONDS`. Die bestehende Frist ab `docling_started_at` bleibt unverändert. Ergebnis bei Ablauf wie bisher `failed`/`timeout` mit verständlichem `error_detail` („Docling hat die Aufgabe nicht begonnen“ sinngemäß, Englisch im Code, übersetzt wie die übrigen Meldungen, falls Meldungen übersetzt werden).
- Docstring und Hilfe von `ingest_versions` (`--stuck`) an das Verhalten seit 048 anpassen: `poll` schreibt `updated_at` bei jeder Abfrage; `--stuck` erfasst Aufträge, die gar nicht mehr abgefragt werden (z. B. nach hartem Abbruch des Workers).
- Tests: Docling bleibt `pending` über die Frist → `timeout`; bleibt `pending` kürzer → weiter `running`; `started` später → Frist ab `docling_started_at` wie bisher; Fall „Docling war zwischen zwei Abfragen schon fertig“ (kein `started` gesehen) endet `done`.

## Nicht-Ziele

- Kein neues Datenbankfeld, keine Migration (falls für den Einreichezeitpunkt ein Feld fehlt: `started_at` des Auftrags verwenden und das im Kurzbericht begründen).
- Keine Änderung an Oberfläche oder API.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/ingest/pipeline.py`
- `backend/twox/ingest/management/commands/ingest_versions.py` (nur Docstring und Hilfe)
- `backend/tests/ingest/test_pipeline.py`, gegebenenfalls `backend/tests/ingest/test_ingest_versions_command.py`
- `backend/locale/de/LC_MESSAGES/django.po` (nur falls neue übersetzte Meldung)
- `docs/ARCHITECTURE.md` (nur der Satz zur Grenze „pending ohne Frist“)

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. Alle Prüfungen des backend-Jobs aus `.github/workflows/ci.yml` sind grün.
2. Die vier Testfälle aus „Umfang“ bestehen.
3. `down -v` des eigenen Compose-Projekts endet mit Exit 0.

## Vorgaben und Hinweise

- Herkunft: Kurzbericht von 059 (Ungereimtheit 2), Entscheidung der Leitstelle.
- Tests nie gegen echtes Docling (`backend/tests/ingest/fake_converter.py`, `fake_docling.py`).

## Fragen an a7 (mit Optionen und Empfehlung)

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Was wurde gebaut?**

- `pipeline.py`: `_deadline_passed` (Frist ab `docling_started_at`) ist unverändert. Neu ist `_start_deadline_passed`: Ohne `docling_started_at` gilt `TWOX_INGEST_TIMEOUT_SECONDS` ab `started_at` des Auftrags. Ein eigenes Feld für das Einreichen bei Docling gibt es nicht. `convert` setzt `started_at` und reicht unmittelbar danach ein, deshalb ist `started_at` der passende Ersatz, ohne Migration. Ein nach verlorener Aufgabe neu eingereichter Auftrag behält sein erstes `started_at`; die Zahl solcher Neueinreichungen ist über `TWOX_INGEST_MAX_RETRIES` ohnehin begrenzt.
- Reihenfolge in `_poll`: Die Frist ab `started` wird wie bisher vor der Abfrage geprüft. Die neue Frist wird erst nach der Abfrage geprüft und nur, wenn die Aufgabe weder fertig ist noch gerade erstmals `started` meldet. Ein Auftrag, dessen Aufgabe zwischen zwei Abfragen fertig wurde oder gerade begonnen hat, endet also nicht fälschlich mit `timeout`. Bei Ablauf: `failed`/`timeout` mit `error_detail` „Docling did not start the conversion within 9000 seconds after the upload“. Die Meldungen in `error_detail` werden nicht übersetzt (wie die bestehende Fristmeldung), deshalb keine Änderung an `django.po`.
- `ingest_versions`: Docstring und Hilfe zu `--stuck` sagen jetzt, dass jede Abfrage `updated_at` schreibt (seit 048), dass `--stuck` Aufträge erfasst, die gar nicht mehr abgefragt werden (z. B. nach hartem Abbruch des Workers), und dass noch abgefragte Aufträge von selbst enden. Mehr als `TWOX_INGEST_TIMEOUT_SECONDS` bleibt als sichere Wahl genannt (wie im README).
- `docs/ARCHITECTURE.md`: nur der Punkt unter „Known limits“ (bisher „Deadline only from the start at Docling“), jetzt „Deadline from the start at Docling, or from the start of the job“.

**Wie wurde getestet?**

- Neue Tests in `backend/tests/ingest/test_pipeline.py`: `pending` über die Frist → `timeout`; `pending` kürzer → weiter `running`; `started` nach langer Wartezeit → kein `timeout`, danach gilt die Frist ab `docling_started_at`; fertig zwischen zwei Abfragen ohne `started` (auch nach Ablauf der Startfrist) → `done`. Der alte Test „lange Wartezeit in der Docling-Warteschlange ist kein timeout“ prüfte das Gegenteil des neuen Verhaltens und wurde durch den Fall „kürzer als die Frist“ ersetzt.
- Alle Prüfungen des backend-Jobs aus `ci.yml` im eigenen Projekt `twox-065` (Port 18065): ruff check, ruff format, mypy, pytest (2326 bestanden), pytest -m worker (6 bestanden), Übersetzungskatalog, Migrationen, Lizenzen, OpenAPI-Schema – alle Exit 0. `docker version`/`docker compose version` Exit 0, `down -v` Exit 0. Kein echtes Docling, kein Ollama.

**Zweig und Arbeitsverzeichnis:** `worktree-agent-a57c71ffebb303424`, `.claude/worktrees/agent-a57c71ffebb303424`

**Abweichungen**

- Statt `_deadline_passed` zu erweitern, steht die neue Frist in einer eigenen Funktion `_start_deadline_passed`, die nach der Abfrage geprüft wird (Begründung oben: ein fertiger Auftrag soll nicht an der Frist scheitern). Verhalten wie im Umfang verlangt.

**Hinweise für die Leitstelle (nicht geändert, außerhalb des Bereichs)**

- Drei Stellen sagen noch, die Wartezeit in der Docling-Warteschlange zähle nicht: `docs/ARCHITECTURE.md` Abschnitt „Convert and poll“ (Zeile 303) und Tabelle der Zeiten (Zeile 494), `.env.example` Kommentar zu `TWOX_INGEST_TIMEOUT_SECONDS`. Für die Frist ab `started` stimmt das weiterhin, für eine nie gestartete Aufgabe nicht mehr. Vorschlag: in einem kleinen Doku-Auftrag ergänzen.
- Folge der neuen Frist: Bei einem großen Stapel (z. B. `ingest_versions --all`) reicht `convert` alle Aufträge sofort bei Docling ein; mit einem Docling-Worker warten sie nacheinander. Braucht der Stapel in Docling mehr als 2,5 h (bei ~5 s je Seite etwa 1 800 Seiten), enden die letzten Aufträge mit `timeout` und lassen sich mit `ingest_versions --failed` neu starten. In ARCHITECTURE beschrieben. Falls a7 das vermeiden will, wäre eine eigene, längere Startfrist eine neue Einstellung (nicht Teil dieses Auftrags).

Keine offene Frage an a7.
