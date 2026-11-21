# Translation catalogs

The web UI shows every text in German or English (i18next with react-i18next).

## Layout

- One JSON file per language and namespace: `<de|en>/<namespace>.json`.
- Namespaces of milestone M1: `common`, `nav`, `selftest`, `auth`, `assets`, `audit`, `import`, `files`. Unused ones hold `{}`.
- `../i18n.ts` registers all namespaces and sets up i18next; `../i18next.d.ts` derives the key types from the English files.
- The catalogs are bundled with the build. Nothing is loaded over the network.

## Adding texts for a page

1. Put the keys into `en/<namespace>.json` and the same keys into `de/<namespace>.json`.
2. In the component: `const { t } = useTranslation("<namespace>");` and `t("some.key")`.
3. Leave `i18n.ts` and `i18next.d.ts` alone. A new namespace is an architecture change and needs its own work order.

TypeScript rejects a key that is missing in the English file. A test (`../i18n.test.ts`) fails if a namespace file is missing or if German and English differ in their keys.

## Rules

- Placeholders use `{{name}}`. Numbers go through `Intl` with the shown language, for example `{{duration, number}}`.
- Texts from the API (error messages, versions) are data and are shown as sent.
- Language at page load: the stored choice (`localStorage`, key `twox.language`), otherwise the first of `navigator.languages` that is German or English, otherwise English. `<html lang>` follows the shown language.
