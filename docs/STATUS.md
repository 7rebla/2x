# Status

Stand: 21.11.2026 · gepflegt von der Leitstelle

## Freigegeben

- Aufträge für M0 und T1 starten ohne Einzelfreigabe (E-21). Die Liste folgt, sobald die Auftragsdateien unter `docs/auftraege/offen/` liegen.

## In Arbeit

- Leitstelle: Aufträge für M0 und T1 werden entworfen und geprüft (noch nicht in `docs/auftraege/offen/`).

## Wartet auf a7

1. **Freigabe für den ersten Push** nach `https://github.com/7rebla/2x` (öffentlich, E-19). Bis dahin liegt alles nur lokal (E-14).

## Erledigt seit dem letzten Bericht

- Startunterlage gelesen, Zusammenfassung von a7 bestätigt.
- Rechner geprüft: Git 2.55, GitHub CLI, WSL 2, Docker Desktop (Client 29.9.3, Compose 5.7.0), Ollama 0.40.17 (noch kein Modell geladen; Modellwahl in M2/M3).
- Grundgerüst angelegt: Git-Repository (`main`), `.gitignore`, `.gitattributes`, `.worktreeinclude`, `LICENSE` (Apache-2.0), `CLAUDE.md`, `.claude/settings.json`, `.claude/agents/auftrag.md`, `docs/DECISIONS.md`, `docs/ROADMAP.md`, `docs/STATUS.md`, `docs/auftraege/VORLAGE.md`.
- Entscheidungen E-14 bis E-22 protokolliert (Push nur auf Freigabe, Desktop-App, öffentliches Repository, Startunterlage bleibt lokal, selbstständiges Bauen, „a7" statt Name).

## Als Nächstes

- Aufträge für M0 und T1 nach `docs/auftraege/offen/` schreiben.
- Erste Welle Auftragsbearbeiter starten (höchstens drei gleichzeitig), Ergebnisse prüfen und nach `main` zusammenführen.
