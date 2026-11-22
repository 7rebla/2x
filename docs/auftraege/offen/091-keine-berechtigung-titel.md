# Auftrag 091 – Seite „keine Berechtigung“ mit Titel und Überschrift

Meilenstein: Gestaltung (D1) · Freigabestufe: B · Status: zur Prüfung

## Ziel

Lücke aus 078: Ruft ein angemeldeter Benutzer eine Seite auf, die seine Rolle nicht erlaubt, zeigt `RequireRole` nur den Hinweis `NoPermission`. Die Seite hat dann weder einen eigenen Seitentitel (Browser-Tab) noch eine h1. Alle anderen Seiten haben beides seit 078.

## Umfang

- Wenn `RequireRole` eine ganze Seite ersetzt, setzt es den Seitentitel über `usePageTitle` (z. B. „Keine Berechtigung – 2x“) und zeigt eine h1 über dem Hinweis. Die h1 nutzt dieselbe Komponente und dieselben Klassen wie die anderen Seiten (078/085).
- `NoPermission` als Hinweis innerhalb einer Seite (für einzelne Aktionen, falls so verwendet) bleibt ohne h1 und ohne Titeländerung. Prüfe die Aufrufer und trenne bei Bedarf „ganze Seite“ und „Hinweis“.
- Texte de und en.

## Nicht-Ziele

- Keine Änderung an Rollen, Rechten oder Weiterleitungen (Stufe C).
- Kein Umbau von Layout.tsx oder routes.tsx über das Nötige hinaus.

## Betroffene Bereiche (Ordner, Dateien)

- `web/src/components/SessionGuards.tsx`, `web/src/locales/*/auth.json`, `web/src/routes.test.tsx` oder ein eigener Test, falls nötig ein e2e-Schritt in einer bestehenden Rollen-Spezifikation, `web/src/pages/README.md`

## Akzeptanzkriterien (prüfbar)

1. Als Benutzer ohne die nötige Rolle zeigt eine geschützte Seite eine h1 „Keine Berechtigung“ / „No permission“ und den bisherigen Hinweis. Der Browser-Tab heißt „Keine Berechtigung – 2x“ (bzw. englisch).
2. Hinweise innerhalb einer Seite (falls vorhanden) bleiben unverändert.
3. Vitest deckt beides ab; bestehende Tests sind nicht abgeschwächt.
4. Alle Prüfungen aus `.github/workflows/ci.yml` (web, e2e) sind grün.

## Vorgaben und Hinweise

- Seitentitel über `web/src/hooks/usePageTitle.ts` (078), Überschrift wie auf den anderen Seiten.
- Parallel laufen 080 (Layout.tsx, SelftestPage, SettingsPage, MapPage) und 081 (DeviceFiles, DocumentPage, IngestPage, AuditTrail). Diese Dateien nicht anfassen.

## Fragen an a7 (mit Optionen und Empfehlung)

## Kurzbericht (füllt der Auftragsbearbeiter aus)

Status: zur Prüfung

- Was wurde gebaut? `RequireRole` zeigt statt der Seite jetzt `NoPermissionPage`: `usePageTitle` („Keine Berechtigung – 2x“ / „No permission – 2x“), `AnimatedHeading` als einzige h1 und darunter der bisherige Hinweis. `NoPermission` bleibt der reine Hinweis (ohne h1, ohne Titel); einziger bisheriger Aufrufer war `RequireRole`, ein weiterer Aufrufer für einzelne Aktionen existiert nicht. Neuer Schlüssel `noPermissionHeading` in de und en. `web/src/pages/README.md` ergänzt.
- Wie wurde getestet? Vitest in `web/src/session.test.tsx`: Leser auf `/import` und `/audit` (h1 und Titel englisch), Deutsch (h1 und Titel), `NoPermission` allein ohne Überschrift und Titel; bestehende Prüfungen unverändert. Container: lint, typecheck, test (880 grün), build, licenses grün; e2e 66 bestanden, 1 übersprungen (bereits vorher so). Neuer e2e-Schritt nicht nötig (keine Rollen-Spezifikation mit Leser-Konto vorhanden).
- Zweig und Arbeitsverzeichnis: Zweig worktree-agent-acbc9b0d1843ccc44, Arbeitsverzeichnis .claude/worktrees/agent-acbc9b0d1843ccc44
- Abweichungen: keine.
