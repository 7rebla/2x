# Auftrag 007 – Prüfung der Erreichbarkeit von Ollama

Meilenstein: M0 · Freigabestufe: B · Status: erledigt

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

### Was wurde gebaut?

- `backend/twox/answers/management/commands/check_llm.py` (dazu zwei `__init__.py`): Django-Befehl `check_llm`. Er liest `settings.TWOX_LLM_BASE_URL` und prüft nacheinander Namensauflösung (`socket.getaddrinfo`), TCP-Verbindung (`socket.create_connection`) und `GET <Basisadresse>/models` (`urllib`, ausdrücklich ohne Proxy). Ausgabe: genau eine Zeile auf stdout, `OK: …` mit Exit-Code 0 oder `FAILED: …` mit Exit-Code 1. Option `--timeout <Sekunden>`, Vorgabe 5, gilt je Schritt.
- Nur Standardbibliothek, keine neue Abhängigkeit. Der Befehl sendet außer der GET-Anfrage nichts und gibt von der Antwort nur die Anzahl der Modelle aus. Er braucht keine Datenbank (`requires_system_checks = []`).
- `backend/tests/answers/test_check_llm.py`: 15 Testfälle für alle fünf Ausgänge. Ersatzserver aus `http.server` auf 127.0.0.1 im Testcontainer; kein Test spricht mit Ollama oder löst einen Namen im Netz auf.

### Wie wurde getestet?

Alle Befehle mit `docker compose -p twox-007` im Wurzelverzeichnis des Arbeitsverzeichnisses, Docker Engine 29.9.3, Compose v5.7.0. `.env` war vorhanden (Kopie von `.env.example`).

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version` und `docker compose version` Exit-Code 0 |
| 1 | erfüllt | `15 passed in 3.68s`, Exit-Code 0, nichts übersprungen |
| 2 | erfüllt, mit Einschränkung | `31 passed in 9.00s`, Exit-Code 0. Gemessen bei laufendem Ollama; der Fall „Ollama läuft nicht“ ist nicht eigens nachgestellt (Ollama wurde nicht angehalten). Die Tests benutzen nur 127.0.0.1 im Container. |
| 3 | erfüllt, Ausgang `OK:` | `OK: http://host.docker.internal:11434/v1/models is reachable, 0 model(s) reported`, Exit-Code 0, eine Zeile, stderr leer |
| 4 | erfüllt | `FAILED: cannot resolve host 'nonexistent.invalid' (Name or service not known) - check extra_hosts (host.docker.internal:host-gateway) in the compose file and that Docker Desktop is running`, Exit-Code 1 |
| 5 | erfüllt | `FAILED: connection refused by localhost:9 - Ollama is not running or is bound to 127.0.0.1 only (see OLLAMA_HOST)`, Exit-Code 1 |
| 6 | erfüllt | `--timeout 1` angenommen; Ausgabe wie Nr. 3, Exit-Code 0 |
| 7 | erfüllt | `All checks passed!`; `Success: no issues found in 31 source files`; zusätzlich `ruff format --check .`: `31 files already formatted` |
| 8 | erfüllt | fünf Dateien unter `backend/twox/answers/management/` und `backend/tests/answers/`, dazu diese Auftragsdatei |
| 9 | erfüllt | `--profile dev down -v` Exit-Code 0; Projekt `twox-007` und sein Volume sind entfernt |

Die Ausgänge `FAILED: timeout` und `FAILED: unexpected response` sind nur durch Tests belegt, nicht gegen den echten Dienst.

### Praxisprüfung auf diesem Rechner (21.11.2026)

- **Ollama-Version:** 0.40.17 (`/api/version`, aus dem Container abgefragt).
- **Bindung:** Ollama lauscht nur an `127.0.0.1:11434`; `OLLAMA_HOST` ist weder als Benutzer- noch als Systemvariable gesetzt (nur gelesen, nichts geändert).
- **Erreichbar aus dem Container: ja, mit der Standardbindung.** `host.docker.internal` löst im Container auf 192.168.65.254 und fdc4:f303:9324::254 auf; Docker Desktop leitet die Verbindung an den Rechner weiter. Die Vermutung aus der Recherche (es brauche `OLLAMA_HOST=0.0.0.0`) trifft auf diesem Rechner nicht zu. **a7 muss nichts umstellen**; Ollama bleibt für das lokale Netz geschlossen.
- **`/v1/models` antwortet:** HTTP 200, `application/json`, `{"object":"list","data":[]}` – kein Modell geladen, daher 0.
- Nicht geprüft: eine Anfrage an ein Modell (keines geladen) und das Verhalten ohne Docker Desktop (z. B. Docker direkt unter Linux, CI). Dass die Standardbindung dort nicht genügt, ist eine Vermutung, kein Befund.
- Die Bedingung für M0 („`check_llm` ist einmal mit `OK:` gegen das echte Ollama gelaufen“) ist mit Nr. 3 eingetreten.

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-acd2e2fd93211b896`
- Arbeitsverzeichnis: `.claude/worktrees/agent-acd2e2fd93211b896` (relativ zum Projektordner)

### Abweichungen

- **Zwei zusätzliche `FAILED:`-Ausgänge** neben den vier genannten, damit kein Fall mit einer Fehlerspur endet: `FAILED: invalid address …` (Adresse ohne Schema oder Host) und `FAILED: connection error to …` (anderer Netzfehler beim Verbinden, z. B. Netz nicht erreichbar). Beide Exit-Code 1. Der erste ist getestet, der zweite nicht.
- `FAILED: timeout` gibt es in zwei Wortlauten: `timeout connecting to …` (Schritt 2) und `timeout waiting for an answer from …` (Schritt 3, Port offen, keine Antwort). Antwortet etwas ohne gültiges HTTP, lautet die Zeile `unexpected response …: no valid HTTP answer (…)` ohne HTTP-Status; dieser Zweig ist nicht getestet.
- Der Exit-Code 1 entsteht über `sys.exit(1)` nach der Ausgabe, nicht über `CommandError`: Sonst stünde die Zeile mit dem Vorsatz `CommandError:` auf stderr. Bei `call_command` aus Python heißt das `SystemExit`.
- Ein ungültiger Wert für `--timeout` (0, negativ, keine Zahl) endet mit der üblichen Fehlermeldung von Django, nicht mit einer `FAILED:`-Zeile.
- Abgeräumt wurde mit `--profile dev down -v` (Hinweis der Leitstelle) statt `down -v`. Das Image `twox-007-backend-dev` liegt noch lokal vor.
- Keine offenen Fragen.
