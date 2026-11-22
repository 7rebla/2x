import type { ChangeEvent, ReactElement } from "react";
import { useTranslation } from "react-i18next";

import { Select } from "./components/ui/fields.tsx";
import { changeLanguage, currentLanguage, isLanguage, supportedLanguages } from "./i18n.ts";

/** Language switch in the page header; the choice is remembered in the browser. */
export function LanguageSwitch(): ReactElement {
  // Re-renders on every language change.
  const { t } = useTranslation("common");
  const language = currentLanguage();

  const onChange = (event: ChangeEvent<HTMLSelectElement>): void => {
    const picked = event.target.value;
    if (isLanguage(picked)) {
      void changeLanguage(picked);
    }
  };

  return (
    <label className="flex items-center gap-2 text-sm text-fg-muted">
      {t("language.label")}
      <Select size="sm" value={language} onChange={onChange} data-testid="language-switch">
        {supportedLanguages.map((option) => (
          <option key={option} value={option} lang={option}>
            {t(`language.${option}`)}
          </option>
        ))}
      </Select>
    </label>
  );
}
