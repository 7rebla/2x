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
| `brand` | the brand mark only: `#765477` in light mode, `#b496b8` in dark mode, independent of the accent (never `#765477` on a dark background) |

Typical classes: `bg-surface border border-line`, `text-fg-muted`, `text-accent underline hover:text-accent-strong`, `border-danger-line bg-danger-soft text-danger`. Buttons and form fields take their classes from the building blocks in `../components/ui/` (work order 077), not from copies. Icons (work order 071, `../icons/README.md`) take their colour from `currentColor`.

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

Identifiers, IP addresses, versions and number columns use the interface font with `tabular-nums slashed-zero`; monospace (`font-mono`) is only for checksums and the raw data of a change log entry (work order 079).

### Small text (E-65 point 5, work order 084)

| Size | Class | Use |
| --- | --- | --- |
| 13 px on 18 px | `text-meta` (token `--text-meta` in the `@theme` block of `index.css`) | metadata: times, status details and badges, identifiers below a name, user, checksum, change log fields and raw data, hints in a table cell, the short texts of the navigation (there on a 16 px line with `leading-4`), the legend and node details of the map |
| 12 px | `text-xs` | labels in capitals only (`uppercase tracking-wide`): the kind of an entry in the structure tree and on the map |

Body text stays 16 px, tables and the `sm` building blocks 14 px (`text-sm`). `sourceTypography.test.ts` fails when `text-xs` appears without `uppercase` in the same class list, when a size is written in pixels (`text-[13px]`) instead of a named size, or when the token changes. Small text has the same contrast rule as all text (4.5:1); `contrast.test.ts` lists the colour pairs of small text and checks that each is measured.

## Brand mark, favicon and touch icon (E-52)

Work order 072. The files are the project's own work (Apache-2.0 like the repository) and are kept byte for byte as designed; change them only together with the design source.

- `assets/brand/bildmarke.svg` (master, 64 grid, visible mark 6…58) and `assets/brand/bildmarke-16.svg` (small form, 16 grid), both in `currentColor`. `components/BrandMark.tsx` inlines one of them: the small form below 24 px, else the master. The mark takes the token `brand`, is `aria-hidden` and sits in a link to `/` next to the visible name „2x“ (`common:appTitle`), which gives the link its accessible name. The ids of the SVG mask get a unique prefix per instance.
- Header: mark 36 px (master). Between the visible mark and the name 16 grid units, as in the design rules; the same 16 units (a quarter of the grid) are the minimum clear space around the mark. The name stays in the interface font, no word mark.
- Sign-in card (work order 086, E-65 point 7): mark 48 px (master) with the name in `text-4xl`, centred above the card. `BrandMark` with `link={false}` draws the same lockup without a link (`data-testid="brand-lockup"`), so the header keeps the only link named „2x“. Its name stands still (only the name in the header types, E-64), and the lockup is `aria-hidden`, because it repeats the header's link and would otherwise be read twice; it holds nothing focusable.
- `public/favicon.svg` (small form, colour follows `prefers-color-scheme`), `public/favicon.ico` (16/32/48, colour `#957597` for light and dark tab bars) and `public/apple-touch-icon.png` (180 px). Vite copies them to the top of the build; the built `index.html` links them below `/static/`. Django also serves them at `/favicon.ico`, `/favicon.svg` and `/apple-touch-icon.png` (`backend/twox/config/webui.py`), where browsers look without reading the page.

## Text animations (E-52)

Pure CSS in `index.css`; only `opacity`, `transform`, `background-position` and `background-size` move, so no box changes size. Curve `cubic-bezier(0.22, 1, 0.36, 1)` (`--ease-calm`).

| Pattern | Where | Component or class |
| --- | --- | --- |
| A, words fade in (E-65, work order 085) | the first page heading of a browser session; every later heading stands there at once | `AnimatedHeading` (`components/TextMotion.tsx`) |
| B, line mask | device header, file title | `MaskedTitle` |
| C, navigation line | main navigation, settings link | class `nav-link` around an icon and a `nav-label` with `data-label` (reserves the width of the bold label); the current entry also gets the soft accent background. From 768 to 1279 px the entry stands as a column, icon above the short text `nav-short` (drawn from `data-short`, bold width reserved the same way, work order 082) |
| D, loading shimmer | `Loading`, self-test "checking" | `LoadingText` |
| E, typing (E-64, work order 076) | the name next to the brand mark in the header (not the one above the sign-in card) | `TypedText` (via `BrandMark` with `typing`, set in `Layout.tsx`) |

With reduced motion (settings page or operating system) the components render plain text without animation classes, and `index.css` switches off every animation and transition.

### Heading fade (pattern A)

| | |
| --- | --- |
| When | Once per browser session (E-65): only the first `AnimatedHeading` that mounts fades in; it sets `twox.heading` in `sessionStorage` (access in `try/catch`). Every later heading, on any page of the same session, renders plain text at once. Without a usable storage headings never fade. A heading whose text changes while it is shown (language switch) shows the new text at once. |
| Duration | 280 ms per word, words start 30 ms apart, at most four steps (`min(var(--tx-index), 4)`): the whole heading is done within 400 ms. |
| Look | Opacity and a short rise (`translateY(0.3em)`), no blur. |
| Switched off | With reduced motion the heading is plain text and the session counts as done, so switching reduced motion off later does not start the fade. |

### Typing (pattern E)

| | |
| --- | --- |
| When | Once per browser session and run: on the sign-in page (run `sign-in`, also when the session cannot be loaded) and on the first page after signing in (run `app`). The runs already typed are kept in `sessionStorage` under `twox.typed` (access in `try/catch`; without a storage the name types on every page load). Page changes never type again, because the header stays mounted. While the session loads, the place of the name stays empty if nothing has typed yet in this session, else the name stands there at once. |
| Duration | Start after 300 ms (`--tx-type-start`), then one character every 120 ms (`--tx-type-step`), hard, without fading; afterwards the cursor blinks three times (300 ms on, 300 ms off) and disappears. For "2x": about 0.5 s of typing plus 1.8 s of cursor. Any length of name works: each character (grapheme) gets its position as `--tx-char`. |
| Look | Interface font (Inter), no monospace. The cursor is a narrow bar (`max(2px, 0.07em)`) in the token `brand`; it waits before the first character and follows each typed character. The brand mark is visible from the start; only the name types. |
| Layout and accessibility | The name itself (`.tx-type-text`) stays in the flow, reserves the full width and remains the accessible name of the link, but is not drawn while the typed layer (`.tx-type-layer`, `aria-hidden`, absolute on top of it) shows the characters through `::before { content: attr(data-char) }`. The text of the page therefore stays the name, and the navigation never moves. |
| Switched off | With reduced motion (settings page or operating system) `TypedText` renders the plain name and the run counts as done; the global rules in `index.css` would also leave every character visible and every cursor hidden. |
