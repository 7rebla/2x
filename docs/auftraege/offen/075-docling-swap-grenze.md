# Auftrag 075 – Swap-Grenze für Docling

Meilenstein: M2 · Freigabestufe: C (entschieden mit E-62) · Status: offen

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
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
