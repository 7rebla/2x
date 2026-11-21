# Auftrag 007 – Prüfung der Erreichbarkeit von Ollama

Meilenstein: M0 · Freigabestufe: B · Status: offen

## Ziel

Ein einzelner Befehl sagt klar, ob die Container den Modell-Dienst unter `host.docker.internal:11434` erreichen – und wenn nicht, woran es liegt. Damit ist das Werkzeug für den Prüfpunkt aus Abschnitt 5.5 („M0 prüft das“) vorhanden. Nichts im Projekt darf davon abhängen, dass Ollama läuft.

## Umfang

- Django-Befehl `check_llm` in der App `answers` (`backend/twox/answers/management/commands/check_llm.py`). Er liest die Adresse aus `settings.TWOX_LLM_BASE_URL` und prüft in drei Schritten:
  1. Der Hostname lässt sich auflösen.
  2. Der Port nimmt Verbindungen an.
  3. Die OpenAI-kompatible Schnittstelle antwortet auf die Modellliste (`GET <Basisadresse>/models`).
- Genau eine Ergebniszeile, Ausgabe auf Englisch, mit eindeutigem Anfang und passendem Exit-Code:
  - `OK: ...` (Exit 0) – erreichbar; nennt Adresse und Anzahl der gemeldeten Modelle.
  - `FAILED: cannot resolve host ...` (Exit 1) – Hinweis auf `extra_hosts` bzw. Docker Desktop.
  - `FAILED: connection refused ...` (Exit 1) – Hinweis: Ollama läuft nicht oder ist nur an 127.0.0.1 gebunden (`OLLAMA_HOST`).
  - `FAILED: timeout ...` (Exit 1) – Hinweis auf Firewall.
  - `FAILED: unexpected response ...` (Exit 1) – etwas antwortet, aber nicht wie erwartet (HTTP-Status wird genannt).
- Zeitlimit je Schritt als Option des Befehls: `--timeout <Sekunden>`, Vorgabe 5.
- Tests unter `backend/tests/answers/` für alle fünf Ausgänge. Sie verwenden einen kleinen Ersatzserver im Test (Standardbibliothek) und sprechen **nie** mit einem echten Ollama.
- Praxisprüfung auf diesem Rechner mit Ergebnis im Kurzbericht (siehe Hinweise).

## Nicht-Ziele

- Ollama installieren, starten oder umstellen; Modelle laden; Windows-Umgebungsvariablen oder die Firewall ändern. Das macht a7.
- Die Modell-Anbindung für Antworten und Einbettungen (M2/M3).
- Prüfung beim Start der Container: Die Dienste starten auch ohne Ollama.
- Änderungen an `settings.py`, `pyproject.toml` oder Compose-Dateien.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/twox/answers/management/**` (neu)
- `backend/tests/answers/` (neu)

## Akzeptanzkriterien (prüfbar)

Alle Befehle im Wurzelverzeichnis. `D` steht für `docker compose -p twox-007`. Vorher `.env.example` nach `.env` kopieren (falls nicht vorhanden).

0. Vorab: `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren oder ausführen; Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. `D run --rm backend-dev pytest tests/answers` endet mit Exit-Code 0; mindestens fünf Tests (je Ausgang einer), 0 übersprungen.
2. `D run --rm backend-dev pytest` (gesamt; `backend-dev` startet `db` mit) endet mit Exit-Code 0, 0 fehlgeschlagen – auch wenn Ollama auf dem Rechner nicht läuft.
3. `D run --rm backend-dev python manage.py check_llm` gibt genau eine Zeile aus, die mit `OK:` (Exit 0) oder `FAILED:` (Exit 1) beginnt. Beide Ausgänge erfüllen das Kriterium; welcher eintrat, steht im Kurzbericht.
4. `D run --rm -e TWOX_LLM_BASE_URL=http://nonexistent.invalid:11434/v1 backend-dev python manage.py check_llm` gibt `FAILED: cannot resolve host` aus und endet mit Exit-Code 1.
5. `D run --rm -e TWOX_LLM_BASE_URL=http://localhost:9/v1 backend-dev python manage.py check_llm` gibt `FAILED: connection refused` aus und endet mit Exit-Code 1.
6. `D run --rm backend-dev python manage.py check_llm --timeout 1` wird angenommen (kein Fehler wegen unbekannter Option).
7. `D run --rm backend-dev ruff check .` meldet `All checks passed!`; `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
8. `git diff --stat main...HEAD` zeigt nur Dateien unter `backend/twox/answers/` und `backend/tests/answers/` sowie diese Auftragsdatei.
9. Abräumen: `D down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

- **Voraussetzung:** Auftrag 001 ist zusammengeführt (Einstellung `TWOX_LLM_BASE_URL`, Dienst `backend-dev` mit `extra_hosts`).
- **Keine neue Abhängigkeit.** Nur die Python-Standardbibliothek (`socket`, `urllib`). Stufe B gilt nur, solange das so bleibt.
- **Ollama ist auf diesem Rechner möglicherweise noch nicht installiert** (a7 installiert es selbst). Dann lautet das Ergebnis der Praxisprüfung „nicht prüfbar – Ollama fehlt“. Der Auftrag ist trotzdem abschließbar. Die Leitstelle führt den offenen Punkt in `docs/STATUS.md` als Bedingung für die Abnahme von M0: `check_llm` ist einmal mit `OK:` gegen das echte Ollama gelaufen.
- **Praxisprüfung, falls Ollama läuft** – Ergebnis jeweils in den Kurzbericht:
  - Ist Ollama mit der Standardbindung (`127.0.0.1:11434`) aus dem Container erreichbar? Die Recherche konnte das nicht belegen; der Schluss aus zwei Quellen lautet: nein, es braucht `OLLAMA_HOST=0.0.0.0` als Windows-Benutzervariable und einen Neustart von Ollama.
  - Antwortet der OpenAI-kompatible Pfad `/v1/models` (ungeprüft)?
  - Ollama-Version.
  - Der Bearbeiter stellt nichts um. Ist eine Umstellung nötig, schreibt er das als Befund in den Kurzbericht. Die Leitstelle legt den Befund a7 unter „Wartet auf a7“ vor (`OLLAMA_HOST=0.0.0.0` öffnet Ollama ins lokale Netz; die Einstellung nimmt a7 selbst vor). Das Zusammenführen des Codes hängt nicht daran.
- Stand der Recherche vom 21.11.2026: Ollama 0.40.17 (MIT), läuft nativ unter Windows. `OLLAMA_ORIGINS` betrifft nur Browser-Zugriffe, nicht den Zugriff aus Containern.
- Der Befehl gibt keine Inhalte der Modellliste aus außer der Anzahl und schickt keine Daten an den Dienst.
- Dieser Auftrag startet den Dienst `api` nicht und braucht keinen Host-Port.
- Sprache: Code und Ausgaben Englisch; jede Funktion hat Typangaben.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle.
- Kein Push. Die Leitstelle committet nach `main` und pusht auf a7s Freigabe.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

Keine zum Start. Ein Befund zur Bindung von Ollama (`OLLAMA_HOST`) kommt über den Kurzbericht und die Leitstelle zu a7.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
