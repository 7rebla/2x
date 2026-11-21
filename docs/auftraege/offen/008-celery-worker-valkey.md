# Auftrag 008 – Celery-Worker mit Valkey

Meilenstein: M0 · Freigabestufe: C · Status: offen

## Ziel

Ein Celery-Worker läuft als eigener Container, nutzt Valkey als Broker und Ergebnisspeicher und bedient drei getrennte Warteschlangen. Ein Rauchtest belegt, dass ein Auftrag hin- und das Ergebnis zurückkommt.

## Umfang

- `backend/twox/config/celery.py` (Celery-Anwendung) und Anbindung in `backend/twox/config/__init__.py`.
- Celery-Einstellungen in `settings.py` aus Umgebungsvariablen (`TWOX_CELERY_BROKER_URL`, `TWOX_CELERY_RESULT_BACKEND`); Serialisierung nur JSON.
- Drei Warteschlangen nach Abschnitt 5.2 mit englischen Namen: `ingest` (Einlesen), `embed` (Einbetten), `default` (Sonstiges). Ohne Angabe landet ein Auftrag in `default`.
- Eine Aufgabe `ping` im Paket `twox.config`, die die Zeichenkette `pong` zurückgibt.
- `deploy/compose/compose.yaml`: Dienste `valkey` (festes Versions-Tag, Healthcheck, kein Host-Port) und `worker` (Stufe `runtime`, bedient alle drei Warteschlangen, Healthcheck, `extra_hosts` wie bei `api`, kein Host-Port). `api`, `worker` und `backend-dev` erhalten die Broker-Variablen.
- `.env.example` um die neuen Variablen ergänzen.
- pytest-Konfiguration: Markierung `worker` für Tests, die einen laufenden Worker brauchen. Der Lauf ohne Angabe (`pytest`) wählt sie ab (`addopts` mit `-m "not worker"`); `pytest -m worker` führt genau sie aus.
- Tests unter `backend/tests/config/`:
  - Einheitstest: `ping` liefert `pong`; die drei Warteschlangen sind konfiguriert; Standard-Warteschlange ist `default`.
  - Integrationstest (Markierung `worker`): schickt `ping` an den laufenden Worker und liest das Ergebnis innerhalb von 10 Sekunden. Läuft kein Worker, schlägt der Test mit einer klaren Meldung fehl – er wird nicht übersprungen.

## Nicht-Ziele

- Fachliche Aufgaben (Einlesen, Einbetten) – ab M2.
- Mehrere Worker-Container je Warteschlange, Zeitplaner (Celery Beat), Überwachungsoberfläche (Flower).
- Die Testseite (Aufträge 010 und 012).
- Das Paket `valkey` (valkey-py) oder `celery-redis-plus`: kombu nutzt sie nicht bzw. sie wären zusätzliche Abhängigkeiten.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/pyproject.toml`, `backend/uv.lock`
- `backend/twox/config/celery.py` (neu), `backend/twox/config/__init__.py`, `backend/twox/config/settings.py`, Datei für die Aufgabe `ping` in `backend/twox/config/`
- `backend/tests/config/` (neue Testdateien)
- `backend/scripts/` (nur die Regeldatei der Lizenzprüfung, falls ein mitgezogenes Paket eine bereits genehmigte Lizenz in neuer Schreibweise trägt)
- `deploy/compose/compose.yaml`
- `.env.example`

## Akzeptanzkriterien (prüfbar)

Alle Befehle im Wurzelverzeichnis. `D` steht für `docker compose -p twox-008`. Vorher `.env.example` nach `.env` kopieren (falls nicht vorhanden) und darin `TWOX_API_PORT=18008` setzen.

0. Vorab: `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren oder ausführen; Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. `D up -d --wait` (ohne Dienstnamen) endet mit Exit-Code 0; `D ps` zeigt `db`, `valkey`, `worker` und `api` als `healthy`.
2. `D exec worker celery -A twox.config inspect ping` antwortet mit `pong`.
3. `D exec worker celery -A twox.config inspect active_queues` nennt `ingest`, `embed` und `default`.
4. `D run --rm backend-dev pytest` endet mit Exit-Code 0, 0 fehlgeschlagen, 0 übersprungen; die Ausgabe nennt die abgewählten Worker-Tests als `deselected`.
5. `D run --rm backend-dev pytest -m worker` endet bei laufendem Worker mit Exit-Code 0, mindestens 1 Test bestanden.
6. Gegenprobe: Nach `D stop worker` schlägt `D run --rm backend-dev pytest -m worker` fehl, und die Meldung nennt den nicht erreichbaren Worker. Danach `D start worker`.
7. `D run --rm backend-dev ruff check .` meldet `All checks passed!`; `D run --rm backend-dev ruff format --check .` endet mit Exit-Code 0; `D run --rm backend-dev mypy .` meldet `Success: no issues found`.
8. `D exec worker python -c "from django.conf import settings; print(settings.CELERY_BROKER_URL)"` zeigt eine Adresse mit dem Schema `redis://` und dem Host `valkey`.
9. `D ps --format json` zeigt für `valkey` und `worker` keinen veröffentlichten Host-Port.
10. Lizenzprüfung: `D run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0. Meldet sie ein mitgezogenes Paket mit nicht gedeckter Lizenz: nichts in die Erlaubt-Liste schreiben, Frage in den Auftrag, Status „wartet auf a7“.
11. Abräumen: `D down -v` endet mit Exit-Code 0.

## Vorgaben und Hinweise

- **Voraussetzung:** Auftrag 005 ist zusammengeführt (und damit 001); die Lizenzprüfung aus Auftrag 006 liegt auf `main`.
- **Abhängigkeiten.** Mit der Freigabe der Auftragsliste genehmigt a7 diese direkten Abhängigkeiten: `celery[redis]` (zieht kombu und den Client redis-py nach), `celery-types` (nur Entwicklung) und das Image `valkey/valkey`. Mitgezogene Pakete (zum Beispiel billiard, vine, amqp, click) sind mitgenehmigt, soweit die Lizenzprüfung sie durchlässt (Kriterium 10). Jede weitere direkte Abhängigkeit ist nicht genehmigt.
- **Versionen (Stand der Recherche vom 21.11.2026, belegt):** celery 5.7.0 (BSD-3-Clause) · kombu 5.7.0 (BSD-3-Clause; das Extra `redis` verlangt redis >=6.4,<9) · redis-py 8.1.0 (MIT) · celery-types 0.26.0 (Apache-2.0) · Valkey 9.2.0 vom 19.11.2026 (BSD-3-Clause), gepflegt außerdem 9.1.4.
- **Celery kennt kein `valkey://`.** Valkey läuft über den Redis-Transport: Adresse `redis://valkey:6379/0`, Ergebnisse zum Beispiel in Datenbank 1. Die Celery-Doku nennt offiziell nur Redis.
- **Ungeprüft und hier zu prüfen:** ob redis-py 8.x fehlerfrei mit der gewählten Valkey-Version arbeitet. Der Integrationstest ist der Nachweis; das Ergebnis mit den genauen Versionen gehört in den Kurzbericht. Klappt es nicht: nicht auf andere Pakete ausweichen, sondern Frage in den Auftrag. Ebenso: Lizenz des Images `valkey/valkey` an der Quelle bestätigen.
- Die mitgezogenen Pakete von Celery im Kurzbericht mit Lizenz auflisten.
- Djangos eingebautes Tasks-Framework wird nicht verwendet; die Unterlage legt Celery fest. Im Kurzbericht einen Satz für das Entscheidungsprotokoll vorschlagen.
- Zugriffe auf die Warteschlange laufen später über eine eigene Schnittstelle (Abschnitt 7). Hier nur die Grundkonfiguration, keine fachliche Schnittstelle erfinden.
- Die Regel für alle späteren Aufträge: `pytest` ohne Angabe braucht nur die Datenbank; der volle Lauf besteht aus `pytest` und `pytest -m worker` bei laufendem Worker (so auch in der CI).
- Parallele Arbeitsverzeichnisse: immer mit `-p twox-008` und Port 18008 arbeiten.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle.
- Kein Push. Die Leitstelle committet nach `main` und pusht auf a7s Freigabe.
- Die Frage unten beantwortet a7 mit der Freigabe der Liste. Fehlt die Antwort: nicht raten, Status „wartet auf a7“.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

1. **Valkey-Version.**
   - (a) 9.1.x (aktuell 9.1.4), fest auf die Unterversion gelegt.
   - (b) 9.2.0 – erst am 19.11.2026 erschienen.
   - Empfehlung: (a), aus demselben Grund wie bei PostgreSQL 19: zwei Tage alt ist für ein Gerüst zu frisch. Der Bearbeiter prüft das genaue Tag auf Docker Hub.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
