# Auftrag 075 – Swap-Grenze für Docling

Meilenstein: M2 · Freigabestufe: C (entschieden mit E-62) · Status: erledigt

Voraussetzung: E-62; 066 ist auf `main`.

## Ziel

`mem_limit: ${TWOX_DOCLING_MEM_LIMIT:-8g}` (066) begrenzt nur den Arbeitsspeicher; Docker erlaubt zusätzlich Swap in gleicher Höhe. Nach E-62 schließt die Grenze Swap ein.

## Umfang

- `deploy/compose/compose.yaml`, Dienst `docling`: `memswap_limit: ${TWOX_DOCLING_MEM_LIMIT:-8g}` (derselbe Wert, also kein zusätzlicher Swap).
- `.env.example`, README (Konfigurationstabelle, Voraussetzung „Memory“) und `docs/ARCHITECTURE.md` (Docling-Grenzen, Known limits): Swap-Hinweis aus 066 ersetzen.
- Nachweis mit `docker compose config docling` und `docker inspect` (Memory = MemorySwap) im eigenen Projekt.

## Nicht-Ziele

- Keine Änderung am Wert 8 GiB, kein Code.

## Betroffene Bereiche (Ordner, Dateien)

- `deploy/compose/compose.yaml` (nur Dienst `docling`), `.env.example`, `README.md`, `docs/ARCHITECTURE.md`

## Akzeptanzkriterien (prüfbar)

0. `docker version` und `docker compose version` enden mit Exit 0.
1. `docker compose config docling` zeigt `mem_limit` und `memswap_limit` mit gleichem Wert (Vorgabe und mit gesetzter Variable).
2. `docker inspect` des laufenden Docling-Containers im eigenen Projekt: `Memory` gleich `MemorySwap`.
3. Alle Prüfungen des backend-Jobs aus `.github/workflows/ci.yml` sind grün.
4. `down -v` des eigenen Compose-Projekts endet mit Exit 0.

## Vorgaben und Hinweise

- Herkunft: E-62 (c), Frage aus 066.

## Fragen an a7 (mit Optionen und Empfehlung)

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut? Dienst `docling` hat jetzt `memswap_limit: ${TWOX_DOCLING_MEM_LIMIT:-8g}` neben `mem_limit`. Kommentar in `compose.yaml`, `.env.example`, README (Voraussetzung „Memory“, Konfigurationstabelle) und `docs/ARCHITECTURE.md` (Docling-Grenzen, Konfigurationszeile, Known limits): Swap-Hinweis aus 066 ersetzt, die Grenze schließt Swap ein.
- Wie wurde getestet? (0) `docker version`/`docker compose version` Exit 0. (1) `docker compose -p twox-075 config docling`: Vorgabe 8589934592/8589934592, mit `TWOX_DOCLING_MEM_LIMIT=12g` 12884901888/12884901888. (2) `docker inspect` von `twox-075-docling-1`: Memory 8589934592 = MemorySwap 8589934592. (3) backend-Job im Projekt `twox-075`: Build, up, ruff, ruff format, mypy, pytest (2341 bestanden), pytest -m worker (6), makemessages ohne Diff, makemigrations --check, Lizenzprüfung, OpenAPI-Schema ohne Diff – alle Exit 0. (4) `down -v` Exit 0.
- Zweig und Arbeitsverzeichnis: `worktree-agent-aea37d28e2449daff`, `.claude/worktrees/agent-aea37d28e2449daff`
- Abweichungen: keine.

Status: zur Prüfung
