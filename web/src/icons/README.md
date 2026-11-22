# Icons

Work order 071 (decision E-51). Basis: `docs/design/icon-bedarfsanalyse.md`, parts F (rules), H2 (inventory, IDs) and H5 (first set).

## Use

```tsx
import { Icon } from "../icons/Icon.tsx";

<button type="button" className="inline-flex items-center gap-2 …">
  <Icon name="upload" size={20} decorative />
  {t("upload.submit")}
</button>
```

- **By name only.** Code never imports from `lucide-react`; `names.ts` is the only file that does (checked by `git grep -n "lucide-react" -- web/src`). A later change of library or drawing is a change in one table.
- **Meaning is required by the type.** `decorative` hides the icon from assistive technology (`aria-hidden`), for every icon next to a text that says the same. `label="…"` makes it an image with that name, for an icon that stands alone. An icon-only button keeps `decorative` on the icon and gets its own `aria-label`.
- **Sizes** 16 (text, tables, status; default), 20 (navigation, buttons), 24 (headings, nodes). Stroke width 2 units of the 24 grid for all of them (`ICON_STROKE_WIDTH`), so it scales: about 1.33 px at 16 px, 1.67 px at 20 px.
- **Colour** only through `currentColor`: the icon takes the colour of the text around it, or a token class such as `text-success` (see `../theme/README.md`). No fixed colours.
- **Status never by colour alone:** a status icon always stands next to its text (success, warning, error, info, loading, no permission).
- **Outline everywhere.** The current navigation entry is shown by a soft background (`.nav-link[aria-current="page"]` in `index.css`), not by a filled icon.

## Names

`names.ts` lists every `IconName` with the ID from part H2 of the analysis:

| Group | Names |
| --- | --- |
| Navigation | `structure`, `map`, `import`, `audit`, `selftest`, `settings`, `user` |
| Objects | `site`, `area`, `plant` (own), `device` (own, generic), `network`, `document`, `version` |
| Device classes (own) | `devicePlc`, `deviceController`, `deviceComputer`, `deviceRouter`, `deviceRobot`, `deviceFirewall` |
| Actions | `create`, `edit`, `upload`, `download`, `retry`, `apply`, `filter`, `resetFilter`, `search`, `fitView`, `previous`, `next`, `signOut` |
| Status | `success`, `error`, `warning`, `loading`, `noPermission`, `info`, `queued`, `skipped`, `notIngested` (the last three for ingest jobs, work order 053) |

The navigation entries name their icon in `../navigation.ts` (`icon`).

## Own drawings (work order 074 and later)

Own icons are React components on the frame `SvgGlyph` (`glyph.tsx`): view box `0 0 24 24`, no fill, stroke in `currentColor`, round caps and joins. They pass only their shapes, without colours, and are added to the table in `names.ts` next to the Lucide icons, under a new name. `icons.test.tsx` then checks them like every other icon (24 grid, `currentColor`, no own colours, a drawing different from all others).

`industrial/` holds the eight own icons approved by a7: plant (OBJ-03), generic device (OBJ-04) and the device classes PLC, controller, computer, router, robot and firewall (DEV-01 to DEV-06).

- The `.svg` files there are the approved drawings, unchanged byte for byte. They are not imported by the application; they are the reference.
- `industrial/glyphs.tsx` repeats the shapes of each file as a component. `industrial/glyphs.test.tsx` compares every component with its file shape by shape and checks that each file holds nothing but `path`, `rect` and `circle` on the rules above. A changed drawing therefore means: replace the file, then the shapes in `glyphs.tsx`, until the test passes.
- They are the project's own work under the licence of the repository.

The mapping from device class to icon (`device_class` → `IconName`) is `deviceClassIcon()` in `../pages/structure/deviceClass.ts`, the only place that knows it. `other`, a missing and an unknown class show `device`; plants show `plant` (`PLANT_ICON`). Every place that shows a class icon also writes the class out (tree row, field on the device page, tooltip and label of the map node), because the icon is decorative.

## Library

`lucide-react` 1.77.0 (ISC; some icons derived from Feather, MIT; both texts in the package's licence file), no dependencies. Only named imports, so the build keeps only the icons in `names.ts`. The licence text reaches `/static/THIRD-PARTY-NOTICES.txt` through `backend/Dockerfile` (stage `web-build`).
