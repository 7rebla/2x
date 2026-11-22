# Theme: colours, font, motion and display settings

Work order 070 (decisions E-50 to E-52). Everything here works offline: the font is bundled, nothing is loaded from a CDN.

## Colour tokens

All colours live in `src/index.css` as custom properties (`--twox-*`) and reach Tailwind through `@theme inline` as colour names. Components use only these names, never Tailwind's palette (`slate`, `red` …) and never hard-coded values; `sourceColours.test.ts` fails otherwise.

| Name | Use |
| --- | --- |
| `canvas` | page background (`bg-canvas`) |
| `surface`, `surface-muted` | cards, header, inputs; hovered rows, muted areas |
| `fg`, `fg-muted` | text; secondary text, labels, hints |
| `line`, `line-strong` | borders of cards and tables; borders of form controls (at least 3:1) |
| `accent`, `accent-strong`, `accent-soft`, `on-accent` | primary buttons, links, navigation line, selected tile; text on `accent` |
| `focus` | focus ring (the accent; set globally for `:focus-visible`) |
| `success`, `warning`, `danger`, `info` with `-soft` and `-line` | status text, message background, message border; independent of the accent |

Typical classes: `bg-surface border border-line`, `text-fg-muted`, `bg-accent text-on-accent hover:bg-accent-strong`, `text-accent underline hover:text-accent-strong`, `border-danger-line bg-danger-soft text-danger`. Icons (work order 071, `../icons/README.md`) take their colour from `currentColor`.

Inline styles that cannot use classes (React Flow on the map) use `var(--twox-…)` directly.

## Colour modes and accents

`<html>` carries three attributes; `index.css` reads them:

- `data-theme`: `light` or `dark` (the resolved mode; "system" follows `prefers-color-scheme`).
- `data-accent`: one of `aubergine` (default), `indigo`, `berry`, `umber`, `graphite`. No free colour choice, no petrol or turquoise.
- `data-motion`: `reduce` if the user or the operating system asks for reduced motion, else `full`.

A new accent needs a block for light and one for dark mode in `index.css` (page selector and `data-accent-preview` selector), its name in `accents` (`settings.ts`), in the inline script of `index.html` and in `locales/*/settings.json`. `contrast.test.ts` then measures it.

### Contrast

`contrast.test.ts` reads the values out of `index.css` (`cssTokens.ts`) and measures every pair the interface uses in both modes with every accent (WCAG 2.2): text at least 4.5:1, focus ring, navigation line and borders of form controls at least 3:1. Keep every value as `#rrggbb` on a line of its own and the token blocks outside of `@layer` and `@media`.

## Display settings

`settings.ts` holds the rules (types, defaults, `localStorage` keys `twox.theme`, `twox.accent`, `twox.reduceMotion`, all access in `try/catch`); `store.ts` holds the live state. Components read it with `useDisplay()` or `useReducedMotion()`; the settings page (`pages/SettingsPage.tsx`, `/settings`, role `read`) changes it with `updateDisplaySettings()`. `installDisplaySettings()` (in `main.tsx`) follows changes of the operating system and of other tabs. The language keeps its own key `twox.language` (`i18n.ts`); the switch in the user menu (in the header before sign-in) and the settings page change the same setting.

### Inline script in `index.html`

A small script in `<head>` sets the three attributes before the first paint, so a dark page never flashes white. It repeats the rules of `settings.ts`; `settings.test.ts` runs it against `applySettings()` for many combinations. It loads nothing and fits a content security policy without `'unsafe-inline'` (milestone M6) through its hash:

```
script-src 'self' 'sha256-21Q8MBuGgh+LjfmXBiHrboYdShIdCd3JR1T2Q7yFueI=';
```

`settings.test.ts` fails when the script changes and this hash does not.

## Font

Inter 4.1 (`assets/fonts/inter/InterVariable.woff2`, unchanged from github.com/rsms/inter, `docs/font-files/`, tag `v4.1`; SIL Open Font License 1.1 in `LICENSE.txt` next to it). One variable file for weights 100–900, `font-display: swap`; the stylistic set `ss02` (I, l and 1 distinguishable) is on for the whole interface.

Identifiers, IP addresses, versions and number columns use the interface font with `tabular-nums slashed-zero`; monospace (`font-mono`) is only for checksums.

## Text animations (E-52)

Pure CSS in `index.css`; only `opacity`, `transform`, `filter`, `background-position` and `background-size` move, so no box changes size. Curve `cubic-bezier(0.22, 1, 0.36, 1)` (`--ease-calm`).

| Pattern | Where | Component or class |
| --- | --- | --- |
| A, words clear up | page headings | `AnimatedHeading` (`components/TextMotion.tsx`) |
| B, line mask | device header, file title | `MaskedTitle` |
| C, navigation line | main navigation, settings link | class `nav-link` around an icon and a `nav-label` with `data-label` (reserves the width of the bold label); the current entry also gets the soft accent background |
| D, loading shimmer | `Loading`, self-test "checking" | `LoadingText` |

With reduced motion (settings page or operating system) the components render plain text without animation classes, and `index.css` switches off every animation and transition.
