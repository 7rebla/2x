# Building blocks: button, field, choice

Work order 077. Every button, one-line text field, drop-down choice and text area of the app comes from this folder. Pages do not write their own button or field classes; `sourceControls.test.ts` fails otherwise. Colours come only from the theme tokens (`../../theme/README.md`), icons only through `../../icons` (`../../icons/README.md`). Pure Tailwind classes, no library.

| File | Content |
| --- | --- |
| `Button.tsx` | `Button` |
| `fields.tsx` | `Input`, `Select`, `Textarea` |
| `classes.ts` | the classes behind them (`buttonClasses`, `fieldClasses`, `textareaClasses`), `CONTROL_HEIGHT_PX`, `joinClasses` |

## Sizes

One control height per size, for buttons and fields alike:

| Size | Height | Text | Button icon | Use |
| --- | --- | --- | --- | --- |
| `md` (default) | 36 px | 16 px | 20 px | forms, filter bars, page actions, pagination |
| `sm` | 28 px | 14 px | 16 px | actions inside a row of the tree or a table, the user menu and the language switch in the header |

Fields always use 16 px text in `md`, so phones do not zoom in on focus. A button keeps its height for one line (`min-h-9`, `min-h-7`) and grows if a long label wraps on a narrow screen. A text area has the border, padding and text of an `md` field; its height follows `rows`.

The sizes 36/28 px are the proposal of the UI analysis (finding Ü4); a7 can change them in `classes.ts`.

## Button

```tsx
import { Button } from "../components/ui/Button.tsx";

<Button type="submit" variant="primary" icon="upload" loading={pending}>
  {pending ? t("upload.submitting") : t("upload.submit")}
</Button>

<Button type="button" icon="next" iconPosition="end" disabled={!hasNext} onClick={next}>
  {t("pagination.next")}
</Button>

<Button type="button" size="sm" icon="edit" aria-label={t("actions.editDevice", { name })} onClick={edit}>
  {t("actions.edit")}
</Button>
```

- **`type` is required** (`button`, `submit` or `reset`), so no button submits a form by accident.
- **Variants:** `primary` (accent background, the one main action of a form or page), `secondary` (default; border `line-strong` on `surface`), `ghost` (no border or background until hovered, for quiet controls such as the user menu), `danger` (error colour on `danger-soft` with a border in the error colour, for actions that remove something). Every variant has a border (transparent where none shows), so all variants of one size have the same box.
- **Icon:** `icon` names a decorative icon (`aria-hidden`); the label says the same. `iconPosition="end"` puts it after the label ("Next"). An icon-only button keeps the label out of sight with `aria-label`, see `../../icons/README.md`. An icon of another size goes in as a child (the user menu keeps its 20 px header icon in size `sm`).
- **Disabled:** `disabled` gives every variant half opacity and the "not allowed" cursor; hover changes nothing then.
- **Loading:** `loading` disables the button, sets `aria-busy="true"` and shows the turning `loading` icon at the start in place of its icon. The label stays the caller's (for example "Saving…"). The icon stands still with reduced motion, like every animation.
- `className` is for layout only (width, margin, alignment, `whitespace-nowrap`); colours, height and padding come from variant and size. Every other attribute (`aria-*`, `data-testid`, `ref`, `onClick` …) goes to the native `<button>`.

## Fields

```tsx
import { Input, Select, Textarea } from "../components/ui/fields.tsx";

<label htmlFor={id}>{t("fields.name")}</label>
<Input id={id} name="name" invalid={errors.length > 0} aria-describedby={errorId} className="w-full" />

<Select id={deviceId} value={device} onChange={onDevice} className="max-w-72">
  <option value="">{t("form.allDevices")}</option>
</Select>

<Textarea id={notesId} name="notes" rows={4} invalid={invalid} aria-describedby={errorId} className="w-full" />
```

- **Label, hint and error list stay with the caller** and are tied to the field by `id`, `htmlFor` and `aria-describedby`.
- **Error state:** `invalid` sets `aria-invalid` (`true`, or `false` for a checked field), which colours the border with `danger`. The message itself stands next to the field in text, never by colour alone.
- **Size:** `size="md"` (default) or `"sm"`; it replaces the native `size` attribute. `Select` allows one value (no `multiple`).
- **`Input` types:** only one-line text types (`text` by default, `search`, `password`, `email`, `url`, `tel`, `number`). Check boxes, radio buttons and file choosers stay native `<input>` elements with their own look; they are the only native inputs outside this folder.
- `className` is for layout only (width, `tabular-nums slashed-zero` for identifiers).

## Contrast

`../../theme/contrast.test.ts` measures every pair the building blocks use, in both modes and with every accent: text on `accent` and `accent-strong` (primary), `fg` on `surface` and `surface-muted` (secondary, ghost, fields), `danger` on `danger-soft` and `danger-line` (danger, hovered), the borders `line-strong` and `danger` on the page and on cards (3:1). Disabled controls are exempt from the contrast rules (WCAG 1.4.3).

## Tests

`Button.test.tsx` (variants, sizes, icon, disabled, loading, ref and attributes), `fields.test.tsx` (sizes, error state, types, disabled, heights shared with the buttons) and `sourceControls.test.ts` (no native button, select or text area outside this folder, native inputs only for check boxes, radio buttons and files, no copies of the old button classes).
