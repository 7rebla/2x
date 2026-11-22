# Auftrag 066 – Speichergrenze für Docling

Meilenstein: M2 · Freigabestufe: C (entschieden mit E-60) · Status: offen

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

Keine.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
