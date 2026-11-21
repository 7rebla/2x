# Auftrag 006 – Lizenzprüfung

Meilenstein: M0 · Freigabestufe: C · Status: offen

## Ziel

Eine automatische Prüfung stellt sicher, dass jede direkte und jede mitgezogene Abhängigkeit eine nach Leitplanke 7 zulässige Lizenz hat. Sie läuft lokal im Container und schlägt bei jeder unbekannten oder unzulässigen Lizenz fehl. In die CI hängt sie Auftrag 011 ein.

## Umfang

- `backend/scripts/check-licenses.sh`: prüft die installierte Python-Umgebung mit pip-licenses gegen eine Erlaubt-Liste.
- `web/scripts/check-licenses.sh`: prüft die npm-Abhängigkeiten mit license-checker-rseidelsohn gegen dieselbe Regel. Dazu ein npm-Skript `licenses` in `web/package.json`.
- Eine lesbare Regeldatei je Seite (Erlaubt-Liste und Ausnahmeliste). Jede Ausnahme nennt Paket, Lizenz, Grund und verweist auf den Eintrag im Entscheidungsprotokoll.
- Vollständige Liste aller Pakete mit Lizenz als Ausgabe der Skripte; im Kurzbericht einzeln alles, was nicht MIT, Apache-2.0, BSD oder PostgreSQL-Lizenz ist, jeweils mit dem Paket, das es mitzieht.

## Nicht-Ziele

- Ein Workflow für GitHub Actions: Die Prüfung läuft als Job in `ci.yml` (Auftrag 011), damit die Images je Lauf nur einmal gebaut werden.
- Lizenzen von Container-Images, Betriebssystempaketen und im Image enthaltenen Modellen: Die prüft jeweils der Auftrag, der sie einführt (zum Beispiel Auftrag 009 für Docling). Chat- und Einbettungsmodelle folgen in M2/M3.
- `actions/dependency-review-action` (braucht in privaten Repositories vermutlich GitHub Advanced Security – ungeprüft).
- Suche nach Geheimnissen (Auftrag 003).
- Neue Werkzeuge: pip-licenses und license-checker-rseidelsohn sind durch die Aufträge 001 und 002 installiert.

## Betroffene Bereiche (Ordner, Dateien)

- `backend/scripts/` (neu: Skript und Regeldatei)
- `web/scripts/` (neu: Skript und Regeldatei), `web/package.json` (nur das Skript `licenses`)

## Akzeptanzkriterien (prüfbar)

`B` steht für `docker compose -p twox-006`, `W` für `docker compose -p twox-006 -f deploy/compose/compose.web.yaml`.

0. Vorab: `docker version` und `docker compose version` enden mit Exit-Code 0. Sonst nichts unter Windows installieren oder ausführen; Status „wartet auf a7“ mit dem Satz „Docker Desktop fehlt“.
1. `B run --rm backend-dev sh scripts/check-licenses.sh` endet mit Exit-Code 0 und gibt die Liste aller Pakete mit Lizenz aus.
2. `W run --rm web-dev npm ci` und danach `W run --rm web-dev npm run licenses` enden mit Exit-Code 0; ausgegeben wird eine Zusammenfassung je Lizenz.
3. Gegenprobe Python: Mit einer Regeldatei, aus der MIT entfernt ist, endet der Aufruf mit Exit-Code ungleich 0 und nennt mindestens ein betroffenes Paket. (Aufruf im Kurzbericht; die verkürzte Datei wird nicht eingecheckt.)
4. Gegenprobe npm: dasselbe für die npm-Prüfung.
5. LGPL und MPL stehen nie als pauschal erlaubte Lizenz in einer Regeldatei, sondern nur als Ausnahme je Paket mit Begründung: `git grep -n -i -E 'lgpl|mpl' -- backend/scripts web/scripts` zeigt nur Ausnahmeeinträge (psycopg, psycopg-binary; bei Zustimmung zu Frage 2: pathspec, lightningcss).
6. GPL, AGPL und Lizenzen mit Nutzungsbeschränkung stehen nirgends in einer Erlaubt-Liste: `git grep -n -i -E 'agpl|[^l]gpl|sspl|busl|commons clause' -- backend/scripts web/scripts` zeigt keine Erlaubt-Einträge.
7. Pakete ohne erkennbare Lizenz (`UNKNOWN`) lassen die Prüfung fehlschlagen, bis sie einzeln geklärt und als Ausnahme eingetragen sind (Nachweis: Gegenprobe mit einem erfundenen Eintrag oder Durchsicht der Skriptlogik im Kurzbericht).
8. Beide Skripte haben LF-Zeilenenden: `git ls-files --eol backend/scripts web/scripts` zeigt `i/lf w/lf`.
9. Abräumen: `B down -v` und `W down -v` enden mit Exit-Code 0.

## Vorgaben und Hinweise

- **Voraussetzung:** Die Aufträge 001 und 002 sind zusammengeführt.
- **Keine neue Abhängigkeit.** Braucht die Prüfung ein weiteres Werkzeug: Frage in den Auftrag.
- **Stufe C**, weil der Auftrag festlegt, welche Lizenzen zulässig sind (Lizenzfrage nach Abschnitt 8.2).
- **Stand der Recherche vom 21.11.2026:** pip-licenses 5.5.5 (MIT) liest die installierte Umgebung, also im Container mit der Projektumgebung ausführen. Die Schalter zum Scharfschalten (`--allow-only`, `--fail-on`) sind ungeprüft – an der Paketdoku prüfen. license-checker-rseidelsohn 5.0.1 (BSD-3-Clause) verlangt Node >=24 und npm >=11.
- **Belegte Fälle außerhalb der Bevorzugt-Liste (Prüfbefund vom 21.11.2026, an PyPI und npm-Registry):** psycopg / psycopg-binary (LGPL-3.0-only) · pathspec 1.1.1 (MPL-2.0; mypy 2.4.1 verlangt `pathspec>=1.0.0`; nur Entwicklung) · lightningcss 1.33.0 (MPL-2.0; fest verlangt von `@tailwindcss/node` 4.3.5 und von vite 8.3.8; Build-Werkzeug, gelangt nicht in die ausgelieferten Dateien).
- Lizenzangaben in Paketen sind uneinheitlich geschrieben („BSD License“, „BSD-3-Clause“, „Apache Software License“). Schreibweisen ausdrücklich zuordnen, nicht mit einem Platzhalter alles durchlassen, was „BSD“ enthält.
- Doppellizenzen („MIT OR Apache-2.0“) sind zulässig, wenn mindestens eine Seite erlaubt ist.
- Die Kriterien 1 und 2 (Exit-Code 0) setzen a7s Antworten nach den Empfehlungen voraus. **Fehlt eine Antwort oder lehnt a7 ab:** Skripte und Regeldateien nur mit den Lizenzen aus Leitplanke 7 liefern, die vollständige Liste der nicht gedeckten Pakete in den Kurzbericht, Status „wartet auf a7“. Nichts eigenmächtig erlauben.
- Auftrag 005 läuft gleichzeitig und fügt DRF, drf-spectacular und den ASGI-Server hinzu. Spätere Aufträge (008, 012, 013, 014) führen die Prüfung als eigenes Kriterium aus; findet sich dort eine nicht gedeckte Lizenz, geht das als Frage an a7.
- Vermutlich MPL-2.0 (ungeprüft): certifi – kommt erst mit späteren Paketen.
- `docs/DECISIONS.md` und `docs/STATUS.md` ändert nur die Leitstelle. Im Kurzbericht die Einträge für alle Ausnahmen als Entwurf liefern.
- Kein Push. Die Leitstelle committet nach `main` und pusht auf a7s Freigabe.

## Fragen an a7 (mit Optionen und Empfehlung)

**Antwort der Leitstelle (21.11.2026, nach E-21 und E-23):** Alle Fragen dieses Auftrags sind gemäß der jeweiligen Empfehlung entschieden. Der Auftrag darf damit starten. a7 kann jede dieser Entscheidungen nachträglich ändern.

1. **Freizügige Lizenzen, die Leitplanke 7 nicht nennt.** In jedem npm- und Python-Baum kommen Lizenzen wie ISC, 0BSD, PSF-2.0 und Python-2.0 vor. Sie sind so freizügig wie MIT und BSD, stehen aber nicht in der Liste.
   - (a) ISC, 0BSD, PSF-2.0 und Python-2.0 als gleichwertig in die Erlaubt-Liste aufnehmen, mit einem Sammeleintrag im Entscheidungsprotokoll. Alles Weitere (zum Beispiel Unlicense, CC0, BlueOak, CC-BY) bleibt Einzelfall.
   - (b) Jede nicht genannte Lizenz je Paket einzeln freigeben.
   - Empfehlung: (a). Sonst wartet praktisch jede Aktualisierung auf eine Einzelfreigabe.
2. **MPL-2.0 für zwei benannte Pakete als Einzelausnahme mit Eintrag im Entscheidungsprotokoll?** Leitplanke 7 lässt MPL als unverändert eingebundene Bibliothek zu.
   - pathspec: nur Entwicklung, über mypy. Bei Nein ist mypy nicht nutzbar; dann wäre die Typprüfung neu zu entscheiden (Auftrag 001 Frage 2).
   - lightningcss: Build-Werkzeug, über Tailwind CSS 4 und Vite 8. Bei Nein sind Tailwind 4 und Vite 8 in dieser Form nicht nutzbar.
   - (a) Ja, beide als benannte Ausnahme.
   - (b) Nein.
   - Empfehlung: (a). Beide werden unverändert genutzt, und keines gelangt in den ausgelieferten Code.
3. **psycopg und psycopg-binary (LGPL-3.0-only)** als benannte Ausnahme bestätigen – die Unterlage nennt psycopg selbst als Beispiel (Leitplanke 7). Empfehlung: ja.

## Kurzbericht (füllt der Auftragsbearbeiter aus)
- Was wurde gebaut?
- Wie wurde getestet?
- Zweig und Arbeitsverzeichnis
- Abweichungen
