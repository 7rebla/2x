# Auftrag 066 – Speichergrenze für Docling

Meilenstein: M2 · Freigabestufe: C (entschieden mit E-60) · Status: zur Prüfung

Voraussetzung: E-60.

## Ziel

Docling hat im Messlauf 057 bis 6,6 GiB Speicher belegt (UR5e-Benutzerhandbuch, 267 Seiten). Ohne Grenze kann ein großes Dokument den ganzen Rechner in Bedrängnis bringen. Nach diesem Auftrag läuft Docling mit `mem_limit: 8g` (E-60).

## Umfang

- `deploy/compose/compose.yaml`, Dienst `docling`: `mem_limit: 8g` (Wert über eine Variable `TWOX_DOCLING_MEM_LIMIT` mit Vorgabe `8g` einstellbar, gleiche Art wie die übrigen Docling-Variablen); `.env.example` mit Kommentar.
- Was passiert beim Überschreiten: Der Container wird vom Kernel beendet (OOM), Docker startet ihn neu (`restart`-Regel prüfen und ggf. ergänzen); der Einlese-Auftrag erlebt das als „Docling nicht erreichbar“ bzw. verlorene Aufgabe und wird nach den Regeln aus 046 wiederholt oder beendet. Im Kurzbericht belegen (Quelltext bzw. kurzer Versuch mit kleiner Grenze, z. B. `TWOX_DOCLING_MEM_LIMIT=1g` und BetrSichV aus `testdata/klein/`).
- README (Konfigurationstabelle) und `docs/ARCHITECTURE.md` (Docling-Grenzen, Messwerte 057) nachziehen.
- Ein Test, der die Compose-Konfiguration prüft, falls es für die übrigen Docling-Grenzen schon einen gibt (Muster dort übernehmen); sonst im Kurzbericht `docker compose config` zeigen.

## Nicht-Ziele

- Keine Änderung an Code der Pipeline.
- Keine neue Abhängigkeit.

## Betroffene Bereiche (Ordner, Dateien)

- `deploy/compose/compose.yaml` (nur Dienst `docling`)
- `.env.example`, `README.md`, `docs/ARCHITECTURE.md`
- gegebenenfalls der bestehende Test der Compose-Konfiguration unter `backend/tests/`

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. `docker compose config` zeigt für `docling` die Grenze 8 GiB (Vorgabe) bzw. den Wert der Variable.
2. Alle Prüfungen des backend-Jobs aus `.github/workflows/ci.yml` sind grün.
3. Der Versuch mit kleiner Grenze ist im Kurzbericht beschrieben (Ergebnis des Einlese-Auftrags, Neustart des Containers).
4. `down -v` des eigenen Compose-Projekts endet mit Exit 0.

## Vorgaben und Hinweise

- Herkunft: E-60 (Empfehlung aus 057, von a7 übernommen am 22.11.2026).

## Fragen an a7 (mit Optionen und Empfehlung)

- **Swap mitbegrenzen?** (aus der Bearbeitung) Optionen: (a) so lassen – 8 GiB Speicher plus Swap der Docker-VM; (b) `memswap_limit: ${TWOX_DOCLING_MEM_LIMIT:-8g}` ergänzen, dann ist bei 8 GiB wirklich Schluss. Empfehlung: (b), weil Swap die Umwandlung stark verlangsamt und die Grenze sonst nicht das bedeutet, was die Variable sagt. Kein Hindernis für diesen Auftrag.

## Kurzbericht (füllt der Auftragsbearbeiter aus)

**Was wurde gebaut?**

- `deploy/compose/compose.yaml`, Dienst `docling`: `mem_limit: ${TWOX_DOCLING_MEM_LIMIT:-8g}` mit Kommentar (Messwert 057, Verhalten beim Überschreiten, Swap). Die Regel `restart: unless-stopped` gab es schon; sie greift auch nach dem OOM-Abbruch (Versuch unten), keine Ergänzung nötig.
- `.env.example`: `TWOX_DOCLING_MEM_LIMIT=8g` mit Kommentar.
- `README.md`: Voraussetzung „Memory“ (Grenze statt „offen bei a7“), Zeile in der Konfigurationstabelle.
- `docs/ARCHITECTURE.md`: „Restrictions on Docling“ (Grenze, Verhalten beim Überschreiten, Versuch 066, Swap), Satz unter den Messwerten 057 (E-60 entschieden), Variablentabelle, Abschnitt „Known limits“ (Grenze statt „ohne Speichergrenze“).
- Kein Code der Pipeline geändert, keine neue Abhängigkeit.

**Wie wurde getestet?**

| Nr. | Ergebnis | Nachweis |
| --- | --- | --- |
| 0 | erfüllt | `docker version` (Server 29.9.3) und `docker compose version` (v5.7.0), beide Exit 0 |
| 1 | erfüllt | `docker compose -p twox-066 config docling` (Exit 0): ohne Variable `mem_limit: "8589934592"` (8 GiB), mit `TWOX_DOCLING_MEM_LIMIT=1g` `mem_limit: "1073741824"`; `restart: unless-stopped`. `docker inspect` des laufenden Containers mit 1g: `Memory=1073741824 MemorySwap=2147483648 Restart=unless-stopped` |
| 2 | erfüllt | Alle Schritte des backend-Jobs im Projekt `twox-066`: ruff check, ruff format --check (193 Dateien), mypy (192 Dateien, keine Fehler), pytest `2338 passed, 5 deselected`, `pytest -m worker` `5 passed`, makemessages ohne Unterschied in `backend/locale`, makemigrations --check, Lizenzprüfung, OpenAPI-Schema ohne Unterschied – jeweils Exit 0 |
| 3 | erfüllt | Versuch unten |
| 4 | erfüllt | `docker compose -p twox-066 --profile dev down -v` Exit 0 (Container, Netze, drei Volumes entfernt) |

Einen Test der Compose-Konfiguration gibt es für die übrigen Docling-Grenzen nicht (die Datei ist in `backend-dev` nicht eingebunden); deshalb wie im Auftrag vorgesehen `docker compose config` oben.

**Versuch mit kleiner Grenze** (`TWOX_DOCLING_MEM_LIMIT=1g`, KI aus, BetrSichV aus `testdata/klein/`, 60 Seiten, Upload über die echte Datei-API im `api`-Container, Testclient mit `force_login`):

- 10:04:06 Upload (201), Einlese-Auftrag 1 an Docling übergeben. Docling erreicht 1 024 MiB und wird beendet; `docker events` (live mitgeschnitten bei einem späteren Durchgang): `oom`, `die exitCode=137`, `start` innerhalb von 0,7 s. Docling meldet sich etwa 0,4 s später wieder bereit.
- Worker-Protokoll: `retry 1 of 5 after: docling-serve refused the connection`, dann `retry 2 of 5 after: docling-serve does not know the task`, `submitted to Docling as task …` (neu eingereicht), und so fort. Jeder der sechs Durchgänge endete 20 bis 30 s nach dem Einreichen mit einem OOM-Abbruch; `RestartCount` am Ende 5.
- 10:10:32 `ingest: job 1 failed (docling_unavailable): docling-serve does not know the task (gave up after 5 retries)`. In der Datenbank: `status=failed`, `step=convert`, `attempts=5`, `docling_started_at` leer. Dauer 6,5 Minuten. Docling lief danach wieder (healthy).
- Damit gilt die Regel aus 046 wie erwartet: verlorene Aufgabe → neu einreichen, nach `TWOX_INGEST_MAX_RETRIES` Ende mit `docling_unavailable`. Keine Endlosschleife.

**Zweig und Arbeitsverzeichnis**

Zweig `worktree-agent-ad7fb46098acacbdf`, Arbeitsverzeichnis `.claude/worktrees/agent-ad7fb46098acacbdf`. Nicht gepusht, nicht zusammengeführt. Die Testumgebungen „2x“ und „twox-leit“ wurden nicht berührt. Die gebauten Images des Projekts `twox-066` liegen noch in Docker (keine Volumes).

**Abweichungen und Hinweise**

1. **Swap:** Mit nur `mem_limit` erlaubt Docker zusätzlich dieselbe Menge als Swap (`MemorySwap` = 2 × Grenze), soweit die Docker-VM Swap hat (hier 4 GiB). Bei 8g kann Docling also bis 8 GiB Speicher plus bis zu 4 GiB Swap belegen. Ich habe nichts ergänzt, weil der Auftrag nur `mem_limit` nennt; dokumentiert in compose.yaml und ARCHITECTURE. Falls die Grenze Speicher plus Swap begrenzen soll: `memswap_limit` gleich `mem_limit` setzen (Stufe C, Frage unten).
2. Die Fehlermeldung des Auftrags nennt den Speicher nicht („docling-serve does not know the task“). Der Grund ist nur über `docker events`/`docker inspect` sichtbar; `State.OOMKilled` steht nach dem Neustart wieder auf `false`. In „Known limits“ beschrieben. Eine Erkennung im Code wäre Pipeline-Änderung und ist Nicht-Ziel.
3. Bei einem OOM-Abbruch verlieren auch andere in Docling wartende Aufgaben ihren Platz und verbrauchen je einen Versuch (dokumentiert).
4. Frage zum Swap steht oben unter „Fragen an a7“.
