# Auftrag 006 – Lizenzprüfung

Meilenstein: M0 · Freigabestufe: C · Status: zur Prüfung

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

**Nachtrag der Leitstelle (21.11.2026, aus der Prüfung von Auftrag 001):** (1) `pip-licenses` blendet in der Voreinstellung sich selbst, prettytable und wcwidth aus; das Prüfskript ruft es deshalb mit `--with-system` auf (Schalter an der Paketdoku prüfen). tzdata und colorama stehen nur wegen Windows-Markern in `uv.lock` und sind im Container nicht installiert – im Kurzbericht vermerken. (2) PSF-2.0 (typing_extensions, Python selbst) gehört nach E-23 in die Erlaubt-Liste. (3) Zusätzlicher Punkt im Umfang: Lizenzen der in psycopg-binary gebündelten Bibliotheken je Bibliothek an der Originalquelle belegen (libpq, OpenSSL 3, MIT Kerberos, OpenLDAP, Cyrus SASL, keyutils, libxcrypt, libcom_err) und als Entwurf für den psycopg-Eintrag im Entscheidungsprotokoll im Kurzbericht liefern. Findet sich dabei GPL, AGPL oder eine Nutzungsbeschränkung: Status „wartet auf a7" mit Optionen.

**Nachtrag der Leitstelle (21.11.2026, aus der Prüfung von Auftrag 002):** Der Dienst `web-dev` liegt im Profil `dev`. Deshalb gilt abweichend vom Wortlaut dieses Auftrags: Bauen mit `build web-dev` oder `--profile dev build`; Abräumen mit `--profile dev down -v` (bei Playwright zusätzlich `--profile e2e`); den Dienst immer über `run --rm web-dev` ansprechen – ein bloßes `build`, `up` oder `down -v` ohne Profil tut nichts und meldet trotzdem Erfolg. `git check-ignore -q` nimmt nur einen Pfad je Aufruf. Zugelassene Lizenzen bei reinen Entwicklungs- und Build-Paketen zusätzlich: BlueOak-1.0.0, CC-BY-3.0, CC-BY-4.0, CC0-1.0 (E-25).

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

**Status: zur Prüfung.** Alle Akzeptanzkriterien sind erfüllt; die Prüfungen liefen am 21.11.2026 im Container. Für die Leitstelle zu entscheiden: die Einträge zu den in psycopg-binary gebündelten Bibliotheken (zwei davon LGPL, kein GPL/AGPL, keine Nutzungsbeschränkung – siehe unten).

### Was wurde gebaut?

- `backend/scripts/check-licenses.sh` und `backend/scripts/license-rules.txt`
- `web/scripts/check-licenses.sh` und `web/scripts/license-rules.txt`, npm-Skript `licenses` in `web/package.json`

Beide Skripte arbeiten gleich: Das Werkzeug (pip-licenses mit `--with-system --from=mixed --format=csv` bzw. license-checker-rseidelsohn mit `--csv`) liefert nur die Liste; die Bewertung macht das Skript selbst (awk, im Image vorhanden, keine neue Abhängigkeit). Ausgegeben werden alle Pakete mit Lizenz, danach die Zusammenfassung je Lizenz, bei Fehlern jede Beanstandung einzeln. Ein anderer Pfad zur Regeldatei kann als erstes Argument übergeben werden (für Gegenproben).

Regeln:

- `allow | <Lizenz>`: genau eine Schreibweise je Zeile, Vergleich auf exakte Gleichheit, keine Platzhalter. Eine neue Schreibweise lässt die Prüfung fehlschlagen, bis sie bewusst eingetragen ist.
- Ausdrücke: „A OR B“ ist zulässig, wenn eine Seite erlaubt ist; „A AND B“ nur, wenn alle Seiten erlaubt sind. Verschachtelte oder gemischte Ausdrücke und „WITH“ werden nicht ausgewertet und müssten wörtlich eingetragen werden. Mehrere Classifier eines Python-Pakets (von pip-licenses mit „; “ verbunden) gelten nicht als Auswahl und fallen durch.
- `except | Paket | Lizenz | Grund | Entscheidung`: gilt nur für genau dieses Paket mit genau dieser Lizenz; ändert das Paket seine Lizenz, schlägt die Prüfung fehl. Eine Ausnahmezeile ohne Grund oder ohne Verweis wird als fehlerhaft abgelehnt.
- Nur npm: `allow-dev` (E-25) und `except-dev` gelten ausschließlich für Pakete außerhalb des Produktionsbaums (zweiter Lauf des Werkzeugs mit `--production`). Steht ein solches Paket im Produktionsbaum, schlägt die Prüfung fehl.
- `UNKNOWN` und `UNLICENSED` lassen sich nicht pauschal erlauben: Eine solche `allow`-Zeile ist selbst ein Fehler. Möglich ist nur eine benannte Ausnahme.
- Schlägt das Werkzeug fehl, liefert es keine Pakete oder eine nicht lesbare Zeile (zum Beispiel mehrzeiliger Lizenztext), endet das Skript mit Fehler.

Erlaubt-Liste (beide Seiten): MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, PostgreSQL (Leitplanke 7); ISC, 0BSD, PSF-2.0, Python-2.0 (E-23). Zusätzlich nur Python als tatsächlich vorkommende Schreibweisen: „MIT License“, „BSD License“. Nur npm, nur außerhalb des Produktionsbaums: BlueOak-1.0.0, CC-BY-3.0, CC-BY-4.0, CC0-1.0 (E-25).

Ausnahmen: psycopg, psycopg-binary (LGPL-3.0-only); pathspec (pip-licenses meldet „Mozilla Public License 2.0 (MPL 2.0)“); lightningcss, lightningcss-linux-x64-gnu, lightningcss-linux-arm64-gnu (MPL-2.0, nur außerhalb des Produktionsbaums); twox-web (das eigene Paket, vom Werkzeug als UNLICENSED gemeldet).

### Wie wurde getestet?

`B` = `docker compose -p twox-006`, `W` = `docker compose -p twox-006 -f deploy/compose/compose.web.yaml`; Docker Engine 29.9.3, Compose v5.7.0. Gebaut mit `B build backend-dev` und `W build web-dev`.

| Nr. | Ergebnis | Tatsächliche Ausgabe (gekürzt) |
| --- | --- | --- |
| 0 | erfüllt | `docker version` und `docker compose version`: Exit-Code 0 |
| 1 | erfüllt | Exit-Code 0; 24 Pakete mit Lizenz gelistet, „License check passed.“ |
| 2 | erfüllt | `npm ci`: „added 371 packages“, Exit-Code 0. `npm run licenses`: Exit-Code 0, 348 Pakete, Zusammenfassung je Lizenz, „License check passed.“ |
| 3 | erfüllt | Exit-Code 1, „License check FAILED (12)“, unter anderem `mypy 2.4.1: license "MIT" is not allowed` |
| 4 | erfüllt | Exit-Code 1, „License check FAILED (221)“, unter anderem `react@19.3.1: license "MIT" is not allowed` und `spdx-ranges@2.1.1: license "(MIT AND CC-BY-3.0)" is not allowed` |
| 5 | erfüllt | 6 Treffer, alle Ausnahmezeilen: psycopg, psycopg-binary, pathspec; lightningcss und die zwei Plattformpakete |
| 6 | erfüllt | kein Treffer (Exit-Code 1 von `git grep`) |
| 7 | erfüllt | Gegenproben, siehe unten |
| 8 | erfüllt | alle vier Dateien `i/lf w/lf` |
| 9 | erfüllt | `B down -v` und `W --profile dev down -v`: Exit-Code 0; danach keine Container, Volumes oder Netze des Projekts twox-006 mehr. Die Images `twox-006-backend-dev` und `twox-006-web-dev` liegen noch lokal vor |

Aufrufe der Gegenproben (die verkürzten Regeldateien lagen nur im Wegwerf-Container unter `/tmp`):

- Nr. 3: `B run --rm --no-deps backend-dev sh -c 'grep -v "^allow | MIT" scripts/license-rules.txt > /tmp/r.txt; sh scripts/check-licenses.sh /tmp/r.txt'`
- Nr. 4: `W run --rm web-dev sh -c 'grep -v "^allow | MIT" scripts/license-rules.txt > /tmp/r.txt; npm run licenses -- /tmp/r.txt'`
- Nr. 7, Python: Im Wegwerf-Container ein erfundenes Paket ohne Lizenzangabe angelegt (`fakepkg-0.0.1.dist-info/METADATA` mit Name und Version). Ergebnis: `fakepkg 0.0.1: license "UNKNOWN" is not allowed`, Exit-Code 1. Mit zusätzlicher Zeile `allow | UNKNOWN`: weiterhin Fehler, dazu `rule file line 40: UNKNOWN cannot be allowed in general`. Erst mit einer vollständigen `except`-Zeile für fakepkg besteht die Prüfung.
- Nr. 7, npm: `allow | UNKNOWN` und `allow-dev | UNLICENSED` werden als Fehler der Regeldatei gemeldet. Ohne die Ausnahme für twox-web: `twox-web@0.0.0: license "UNLICENSED" is not allowed`. Ein erfundenes npm-Paket wurde nicht angelegt (das Werkzeug liest nur den Abhängigkeitsbaum aus `package.json`).

Weitere Gegenproben, alle mit erwartetem Fehler: Lizenz in der psycopg-Ausnahme geändert (`differs from the named exception`); Ausnahme ohne Verweis (`not understood`); fehlende Regeldatei (Exit-Code 2); npm: `except-dev` für ein Paket im Produktionsbaum (`valid for development and build only`); MIT nur als `allow-dev` (react, react-dom, scheduler fallen durch); CC-BY-3.0 entfernt (spdx-exceptions und spdx-ranges fallen durch).

Bestehende Prüfungen laufen weiter: Backend `ruff check`, `ruff format --check`, `mypy`, `pytest` (16 bestanden); Oberfläche `npm run lint`, `npm run typecheck`, `npm test` (2 bestanden).

### Lizenzbefunde: alles außerhalb MIT, Apache-2.0, BSD, PostgreSQL-Lizenz

Python (24 installierte Pakete; Zusammenfassung: MIT 10 · BSD-3-Clause 3 · BSD License 2 · LGPL-3.0-only 2 · MIT License 2 · Apache-2.0 1 · Apache-2.0 OR BSD-2-Clause 1 · BSD-2-Clause 1 · MPL-2.0 1 · PSF-2.0 1):

| Paket | Lizenz | mitgezogen von | Deckung |
| --- | --- | --- | --- |
| psycopg 3.3.9 | LGPL-3.0-only | direkt | benannte Ausnahme |
| psycopg-binary 3.3.9 | LGPL-3.0-only | psycopg (Extra `binary`) | benannte Ausnahme |
| pathspec 1.1.1 | MPL-2.0 | mypy | benannte Ausnahme, nur Entwicklung |
| typing_extensions 4.16.0 | PSF-2.0 | mypy, django-stubs | E-23 |

tzdata und colorama stehen nur wegen Windows-Markern in `uv.lock` und sind im Container nicht installiert; die Prüfung sieht sie deshalb nicht. Mit `--with-system` erscheinen pip-licenses, prettytable und wcwidth in der Liste (alle MIT oder BSD-3-Clause).

npm (348 Pakete; Zusammenfassung: MIT 220 · ISC 65 · Apache-2.0 27 · BlueOak-1.0.0 14 · BSD-2-Clause 10 · BSD-3-Clause 4 · MPL-2.0 2 · (MIT AND CC-BY-3.0) 1 · 0BSD 1 · CC-BY-3.0 1 · CC-BY-4.0 1 · CC0-1.0 1 · UNLICENSED 1). Im Produktionsbaum liegen nur react, react-dom und scheduler (MIT) sowie das eigene Paket. Alles Folgende liegt außerhalb des Produktionsbaums; „mitgezogen von“ nennt die direkten Abhängigkeiten laut `package-lock.json`:

| Lizenz | Pakete | mitgezogen von | Deckung |
| --- | --- | --- | --- |
| MPL-2.0 | lightningcss 1.33.0, lightningcss-linux-x64-gnu 1.33.0 | @tailwindcss/vite, vite (damit auch @vitejs/plugin-react, vitest) | benannte Ausnahme |
| ISC (65) | @npmcli/*, pacote, cacache, semver 7, nopt, which 6, ssri, minipass 3, yallist 4, signal-exit und weitere | license-checker-rseidelsohn (semver 7 auch typescript-eslint) | E-23 |
| ISC | flatted, glob-parent, isexe 2, which 2 | eslint (damit auch typescript-eslint, eslint-plugin-react-hooks) | E-23 |
| ISC | electron-to-chromium, lru-cache 5, semver 6, yallist 3 | eslint-plugin-react-hooks | E-23 |
| ISC | picocolors | vite, vitest, @testing-library/dom und weitere | E-23 |
| ISC | saxes | jsdom | E-23 |
| 0BSD | tslib 2.8.1 | @tailwindcss/vite | E-23 |
| BlueOak-1.0.0 (insgesamt 14) | chownr, common-ancestor-path, glob 13, isexe 4, minimatch 10, minipass 7, minipass-flush, path-scurry, tar, yallist 5 | license-checker-rseidelsohn | E-25 |
| BlueOak-1.0.0 | @isaacs/nonrecursive-glob-match, minimatch 11 | eslint | E-25 |
| BlueOak-1.0.0 | lru-cache 11 | jsdom, vitest, license-checker-rseidelsohn | E-25 |
| BlueOak-1.0.0 | graceful-fs | @tailwindcss/vite, license-checker-rseidelsohn | E-25 |
| CC-BY-4.0 | caniuse-lite | eslint-plugin-react-hooks | E-25 |
| CC-BY-3.0 | spdx-exceptions | license-checker-rseidelsohn | E-25 |
| CC0-1.0 | spdx-license-ids | license-checker-rseidelsohn | E-25 |
| (MIT AND CC-BY-3.0) | spdx-ranges | license-checker-rseidelsohn | E-23 und E-25 (beide Seiten erlaubt) |
| UNLICENSED | twox-web 0.0.0 | das eigene Paket | benannte Ausnahme |

Kein Fremdpaket ohne erkennbare Lizenz, weder in Python noch in npm.

### In psycopg-binary gebündelte Bibliotheken

Im Rad `psycopg_binary-3.3.9-cp314-cp314-manylinux2014_x86_64` liegen unter `psycopg_binary.libs` 14 Dateien. Versionen aus den Dateien selbst gelesen (Zeichenketten in den Bibliotheken, `psycopg.pq.version()`), Herkunft aus dem Bauskript von psycopg (`tools/ci/build_libpq.sh`, Hauptzweig – der Stand zu Version 3.3.9 war nicht abrufbar) und der SBOM im Rad. Abruf der Lizenzquellen am 21.11.2026.

| Bibliothek (Dateien) | Version, Herkunft | Lizenz | Quelle |
| --- | --- | --- | --- |
| libpq | PostgreSQL 18.6, aus den Quellen gebaut | PostgreSQL-Lizenz | https://www.postgresql.org/about/licence/ |
| OpenSSL (libssl, libcrypto) | 3.5.9, aus den Quellen gebaut | Apache-2.0 (ab 3.0) | https://openssl-library.org/source/license/ |
| MIT Kerberos (libkrb5, libgssapi_krb5, libk5crypto, libkrb5support, libcom_err.so.3) | 1.22.2, aus den Quellen gebaut | freizügig, MIT-artig, mit mehreren Einzelvermerken (teils BSD mit Nennungsklausel); kein Copyleft. Das mitgelieferte libev ist wahlweise BSD oder GPL-2.0-or-later und gehört zum Server, nicht zu den Client-Bibliotheken | https://web.mit.edu/kerberos/krb5-latest/doc/mitK5license.html |
| OpenLDAP (libldap, liblber) | Version nicht aus der Datei lesbar (Bauskript des Hauptzweigs: 2.6.16), aus den Quellen gebaut | OpenLDAP Public License 2.8 (OLDAP-2.8), freizügig, BSD-artig | https://www.openldap.org/software/release/license.html |
| Cyrus SASL (libsasl2) | 2.1.26, Paket cyrus-sasl-lib aus CentOS 7 | BSD-artig mit vier Bedingungen, darunter eine Nennungsklausel (Carnegie Mellon University); kein Copyleft | https://github.com/cyrusimap/cyrus-sasl/blob/master/COPYING |
| keyutils (libkeyutils) | 1.5.8, Paket keyutils-libs aus CentOS 7 | **Bibliothek LGPL-2.0-or-later**; die Kommandozeilenwerkzeuge (GPL-2.0-or-later) sind nicht im Rad | nur Zweitquelle: https://metadata.ftp-master.debian.org/changelogs/main/k/keyutils/unstable_copyright – die Originalquelle (git.kernel.org) verweigerte den automatischen Abruf |
| libxcrypt (libcrypt.so.1) | Version nicht aus der Datei lesbar; stammt aus dem manylinux2014-Bau-Image, das libxcrypt aus den Quellen baut | **LGPL-2.1-or-later**, einzelne Dateien BSD, 0BSD, gemeinfrei. GPL nur bei Autoconf-Makros (mit Autoconf-Ausnahme), die nicht Teil der Bibliothek sind | https://github.com/besser82/libxcrypt/blob/develop/LICENSING ; Bau im Image: https://github.com/pypa/manylinux/blob/main/docker/build_scripts/install-libxcrypt.sh |
| libcom_err.so.2 | Paket libcom_err 1.42.9 aus CentOS 7 (e2fsprogs, `lib/et`) | MIT-artig | https://github.com/tytso/e2fsprogs/blob/master/NOTICE (Spiegel des Betreuers; git.kernel.org verweigerte den Abruf) |

Ergebnis: kein GPL, kein AGPL, keine Nutzungsbeschränkung in den gebündelten Bibliotheken. Zwei Bibliotheken stehen unter LGPL (keyutils, libxcrypt); beide sind unverändert und als eigene, dynamisch geladene Dateien eingebunden – derselbe Fall wie psycopg selbst nach Leitplanke 7. Die SBOM im Rad nennt nur libcom_err, cyrus-sasl-lib und keyutils-libs und keine Lizenzen.

Einschränkungen dieser Belege: Die Lizenztexte wurden an den genannten Seiten gelesen, nicht gegen die Quellarchive der genauen Versionen geprüft. Für keyutils liegt nur eine Zweitquelle vor (Debian nennt „LGPL-2+“; die genaue Fassung im Dateikopf von `keyutils.c` ist ungeprüft). Geprüft wurde nur das Rad für linux/x86_64 mit glibc; andere Plattformen (arm64, musl) bündeln möglicherweise anderes.

### Entwürfe fürs Entscheidungsprotokoll

Tabelle „Abhängigkeiten“, Zeile psycopg ersetzen durch:

| Name | Lizenz | Zweck | Auftrag | Freigabe |
| --- | --- | --- | --- | --- |
| psycopg 3.3.9, psycopg-binary 3.3.9 | LGPL-3.0-only. Im Rad psycopg-binary (linux/x86_64, glibc) gebündelt und unverändert: libpq 18.6 (PostgreSQL-Lizenz), OpenSSL 3.5.9 (Apache-2.0), MIT Kerberos 1.22.2 (MIT-artig), OpenLDAP (OLDAP-2.8), Cyrus SASL 2.1.26 (BSD-artig mit Nennungsklausel), libcom_err (MIT-artig), keyutils 1.5.8 (Bibliothek LGPL-2.0-or-later; Zweitquelle), libxcrypt (LGPL-2.1-or-later). Quellen im Kurzbericht von Auftrag 006 | PostgreSQL-Treiber, unverändert eingebunden | 001, 006 | benannte Ausnahme nach Leitplanke 7 und E-23; gebündelte LGPL-Bibliotheken: von a7 zu bestätigen |

Neue Zeilen:

| Name | Lizenz | Zweck | Auftrag | Freigabe |
| --- | --- | --- | --- | --- |
| Lizenzprüfung (`backend/scripts/check-licenses.sh`, `web/scripts/check-licenses.sh` mit je einer Regeldatei) | eigener Code; nutzt pip-licenses und license-checker-rseidelsohn, keine neue Abhängigkeit | schlägt bei jeder nicht gedeckten oder unbekannten Lizenz fehl | 006 | nach E-23 |
| Eigenes npm-Paket twox-web (`private`, in `package.json` Apache-2.0) | vom Werkzeug als UNLICENSED gemeldet | in der npm-Regeldatei als benannte Ausnahme von der Prüfung ausgenommen | 006 | Hinweis der Leitstelle zu Auftrag 006 |
| lightningcss-linux-x64-gnu, lightningcss-linux-arm64-gnu 1.33.0 | MPL-2.0 | Plattformpakete zu lightningcss, nur Build | 006 | wie lightningcss (benannte Ausnahme nach E-23) |

Vorschlag für einen Zusatz bei E-23 oder E-25: „Die Regeldateien unter `backend/scripts/` und `web/scripts/` sind die maschinenlesbare Fassung dieser Festlegungen; jede Ausnahmezeile verweist auf einen Eintrag hier.“

### Zweig und Arbeitsverzeichnis

- Zweig: `worktree-agent-a5dfcca35ccdad34f`
- Arbeitsverzeichnis: `.claude/worktrees/agent-a5dfcca35ccdad34f` (relativ zum Projektordner)

### Abweichungen und Hinweise

- **Bewertung im Skript statt über `--allow-only` und `--onlyAllow`.** Geprüft am Quelltext von pip-licenses 5.5.5: `--allow-only` vergleicht den ganzen Lizenztext ohne Auswertung von „OR“, lässt ein Paket mit mehreren Classifiern durch, sobald einer erlaubt ist, und bricht beim ersten Fund ab. Ausnahmen je Paket mit fester Lizenz und die Trennung nach Produktionsbaum lassen sich mit den Schaltern nicht ausdrücken. Die Werkzeuge liefern deshalb nur die Liste. `--with-system` ist an der Hilfe des Werkzeugs geprüft und gesetzt.
- **Laufzeit und Entwicklung werden nur bei npm getrennt.** Auf der Python-Seite gibt es keine Dev-Liste; die Ausnahme für pathspec („nur Entwicklung“) wird dort nicht technisch erzwungen. Zöge ein Laufzeitpaket später pathspec mit, bliebe die Prüfung grün. Erzwingen ließe sich das über `uv export --no-dev`; das habe ich nicht gebaut.
- **Zwei Regeldateien statt einer gemeinsamen:** Jeder Container bindet nur seinen eigenen Ordner ein. Die Erlaubt-Listen stimmen bis auf die Python-Schreibweisen („MIT License“, „BSD License“) und die `allow-dev`-Zeilen überein und müssen bei Änderungen von Hand gleich gehalten werden.
- **„BSD License“** (Classifier von pytest-django und sqlparse) nennt keine Klauselzahl. Beide Pakete sind laut ihren Lizenztexten BSD-3-Clause; die Schreibweise ist deshalb erlaubt, würde aber auch ein Paket mit BSD-4-Clause durchlassen, das nur diesen Classifier trägt.
- **lightningcss-linux-arm64-gnu** steht als Ausnahme in der Regeldatei, ist auf diesem Rechner aber nicht installiert (Hinweiszeile in der Ausgabe). Lizenz laut `package-lock.json` MPL-2.0. Andere Plattformpakete (musl, macOS, Windows) sind nicht eingetragen, weil die Prüfung im glibc-Container läuft.
- **Ausnahme für twox-web** verweist mangels Eintrag auf diesen Auftrag statt auf das Entscheidungsprotokoll (Entwurf oben).
- **Die Skripte haben keine automatischen Tests** in pytest oder Vitest; geprüft sind sie durch die oben genannten Gegenproben von Hand. Ein dauerhafter Selbsttest (zum Beispiel in der CI aus Auftrag 011) fehlt.
- `license-checker-rseidelsohn --help` nennt sich selbst „4.4.2“, installiert ist laut `package-lock.json` 5.0.1; nicht weiter untersucht.
- Die mitgezogenen ISC- und BlueOak-Pakete kommen fast vollständig über license-checker-rseidelsohn selbst (npm-Bibliotheken).
- `pyproject.toml`, `uv.lock` und die Compose-Dateien sind nicht angefasst. Nach dem Zusammenführen von Auftrag 005 muss die Python-Prüfung erneut laufen (DRF, drf-spectacular, uvicorn und deren Abhängigkeiten sind hier nicht geprüft).
- Nicht geprüft: Lauf unter Linux/CI (Auftrag 011), Lizenzen der Basis-Images und Betriebssystempakete (Nicht-Ziel).
