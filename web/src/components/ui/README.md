# Building blocks: button, field, choice

Work order 077. Every button, one-line text field, drop-down choice and text area of the app comes from this folder. Pages do not write their own button or field classes; `sourceControls.test.ts` fails otherwise. Colours come only from the theme tokens (`../../theme/README.md`), icons only through `../../icons` (`../../icons/README.md`). Pure Tailwind classes, no library.

| File | Content |
| --- | --- |
| `Button.tsx` | `Button` |
| `fields.tsx` | `Input`, `Select`, `Textarea` |
| `FileInput.tsx` | `FileInput` (work order 088) |
| `ResponsiveTable.tsx` | `ResponsiveTable`, `useWideTable`, `WIDE_TABLE_QUERY` (work order 081) |
| `classes.ts` | the classes behind them (`buttonClasses`, `fieldClasses`, `textareaClasses`, `fileButtonClasses`, `fileDropClasses`), `CONTROL_HEIGHT_PX`, `joinClasses` |

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
- **`Input` types:** only one-line text types (`text` by default, `search`, `password`, `email`, `url`, `tel`, `number`). Check boxes and radio buttons stay native `<input>` elements with their own look; they are the only native inputs outside this folder. Files are chosen with `FileInput`.
- `className` is for layout only (width, `tabular-nums slashed-zero` for identifiers).

## File chooser

```tsx
import { FileInput } from "../components/ui/FileInput.tsx";

const [file, setFile] = useState<File | null>(null);

<label htmlFor={id}>{t("import:file.label")}</label>
<FileInput id={id} name="file" accept=".csv,text/csv" file={file} onFileChange={setFile} disabled={running} />

<Button type="submit" variant="primary" disabled={file === null} aria-describedby={file === null ? hintId : undefined}>…</Button>
{file === null ? <p id={hintId} className="text-sm text-fg-muted">{t("common:fileInput.chooseFirst")}</p> : null}
```

- **One control, the native one:** the `<input type="file">` stays in the page, visually hidden (`sr-only`) but focusable. The caller's label names it; keyboard (Tab, Space), screen readers, form data and the e2e tests (`setInputFiles` on the label) use it as before. Every other attribute (`name`, `accept`, `data-testid`, `aria-describedby` …) goes to it.
- **What shows:** a frame with a dashed border (`line-strong`, `danger` with `invalid`), in it a button that looks like a secondary `md` button ("Choose file…", icon `document`), the chosen file name (or "No file chosen"; at least 160 px wide, so on a phone it moves below the button; a longer name is cut off with an ellipsis, full name as tooltip) and, from 640 px, the hint "or drop it here". The button is a decorative `span` (`aria-hidden`) that opens the input on click and shows the input's focus ring (`peer-focus-visible`) and disabled state (`peer-disabled`).
- **Drag and drop:** a file dropped on the frame becomes the choice (the first one if several); the frame turns `accent` on `accent-soft` while a file is over it, secondary text then uses `fg` (measured on `accent-soft`). No animation. Disabled, the frame takes no drop.
- **Controlled:** the caller keeps the file (`file`, `onFileChange`); `onFileChange(null)` when the choice is cleared. A dropped file is put into the input as well, so the form data holds it; where that is not possible (jsdom) only the callback has it.
- **A primary button waits for the file:** disabled while `file` is null, with the hint `common:fileInput.chooseFirst` ("Choose a file first.") next to it, tied by `aria-describedby`. Texts live in `locales/*/common.json` under `fileInput`.

## Data tables and cards

Decision E-65 (2): below 768 px a data table becomes a list of stacked cards. `ResponsiveTable` takes the rows and a description of the columns once and renders either a `<table>` (from 768 px, Tailwind `md`) or a `<ul>` of cards, never both, so a screen reader meets a table with column headings or a list with one heading per card. It follows the window width (`matchMedia("(min-width: 48rem)")`); without media queries (jsdom) it is a table.

```tsx
import { ResponsiveTable, type TableColumn } from "../components/ui/ResponsiveTable.tsx";

const columns: TableColumn<Document>[] = [
  { key: "title", header: t("columns.title"), card: "title", cell: (item) => <TitleWithChecksum item={item} />,
    cardCell: (item) => <Title item={item} /> },
  { key: "kind", header: t("columns.kind"), testId: "file-kind", cell: (item) => <KindLabel kind={item.kind} /> },
  { key: "ingest", header: t("columns.ingest"), card: "status", cell: (item) => <IngestStatusBadge … /> },
  { key: "download", header: t("columns.download"), headerHidden: true, card: "action", cell: … },
  { key: "checksum", header: t("columns.checksum"), table: false, card: "detail", cell: … },
];

<ResponsiveTable label={t("listLabel")} testId="device-files-table" rows={documents} rowKey={(item) => item.id}
  columns={columns} rowAttributes={(item) => ({ "data-testid": "device-file" })} cardHeadingLevel={3} />
```

- **Table:** every column with `table` not `false` is a `<th scope="col">` with its `header` (`headerHidden`: for screen readers only) and a `<td>` per row. Classes of headings, cells, rows and the table come from the caller (`headerClassName`, `className`, `rowClassName`, `tableClassName`), so each table keeps its look from work order 079. The table sits in a positioned scroll box (`relative overflow-x-auto`).
- **Card:** a list item with border `line` on `surface`, padding 12 px. `card` places each column: `title` is the heading (level `cardHeadingLevel`, one below the heading of the section around it), `action` stands next to it on the right (the download icon button), `status` below it with its column name for screen readers only, `field` and `wide` are label/value pairs of a description list (`wide` over the full width, for long content such as the changes of a log entry), `detail` follows without a label (the checksum names itself), `none` leaves the column out. `cardCell` replaces the cell content on a card (a title without the detail line the table shows below it).
- **Names and test ids:** the list has the same accessible name and `data-testid` as the table; a row's attributes (`rowAttributes`) go to the `<tr>` or the `<li>`, and a column's `testId` to its `<td>` or to its value on the card, so tests and queries find the same things in both forms.
- **A note for a row:** `rowNote` replaces the columns from `from` on with one text ("No version"): one cell with `colspan` in the table, a paragraph on the card.
- No animation; the switch at 768 px happens at once.

## Contrast

`../../theme/contrast.test.ts` measures every pair the building blocks use, in both modes and with every accent: text on `accent` and `accent-strong` (primary), `fg` on `surface` and `surface-muted` (secondary, ghost, fields), `danger` on `danger-soft` and `danger-line` (danger, hovered), the borders `line-strong` and `danger` on the page and on cards (3:1). Disabled controls are exempt from the contrast rules (WCAG 1.4.3).

## Tests

`Button.test.tsx` (variants, sizes, icon, disabled, loading, ref and attributes), `fields.test.tsx` (sizes, error state, types, disabled, heights shared with the buttons), `FileInput.test.tsx` (hidden but labelled and focusable input, visible button, chosen name, drop, disabled, error state, German), `ResponsiveTable.test.tsx` (table without media queries and from 768 px, cards below, heading levels, places on the card, row note, switching with the window width) and `sourceControls.test.ts` (no native button, select or text area outside this folder, native inputs only for check boxes and radio buttons, files only through `FileInput`, no copies of the old button classes).
