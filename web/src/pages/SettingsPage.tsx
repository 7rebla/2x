// Settings of this browser (address /settings, work order 070): appearance,
// accent colour, language and reduced motion. Every change takes effect at once
// and is stored in localStorage (theme/settings.ts, i18n.ts); nothing goes to
// the server.
import { type ChangeEvent, type ReactElement, useId } from "react";
import { useTranslation } from "react-i18next";

import { AnimatedHeading } from "../components/TextMotion.tsx";
import { usePageTitle } from "../hooks/usePageTitle.ts";
import { Select } from "../components/ui/fields.tsx";
import { changeLanguage, currentLanguage, isLanguage, supportedLanguages } from "../i18n.ts";
import { type Accent, accents, defaultSettings, themeModes } from "../theme/settings.ts";
import { updateDisplaySettings, useDisplay } from "../theme/store.ts";

const fieldsetClass = "space-y-3 rounded border border-line bg-surface p-4";
const legendClass = "px-1 font-semibold";

export function SettingsPage(): ReactElement {
  const { t } = useTranslation(["settings", "nav"]);
  usePageTitle(t("nav:settings"));
  // A form page: a narrow column (42rem) at the left edge of the page grid (E-65 point 1, work order 080).
  return (
    <section data-testid="settings-page" className="w-full max-w-2xl space-y-6">
      <AnimatedHeading text={t("nav:settings")} />
      <p className="text-fg-muted">{t("settings:intro")}</p>
      <AppearanceSetting />
      <AccentSetting />
      <LanguageSetting />
      <MotionSetting />
    </section>
  );
}

function AppearanceSetting(): ReactElement {
  const { t } = useTranslation("settings");
  const display = useDisplay();
  const name = useId();
  return (
    <fieldset className={fieldsetClass} data-testid="settings-appearance">
      <legend className={legendClass}>{t("appearance.legend")}</legend>
      <div className="flex flex-wrap gap-x-6 gap-y-2">
        {themeModes.map((mode) => (
          <label key={mode} className="flex cursor-pointer items-center gap-2">
            <input
              type="radio"
              name={name}
              value={mode}
              checked={display.settings.mode === mode}
              onChange={() => {
                updateDisplaySettings({ mode });
              }}
              data-testid={`settings-mode-${mode}`}
              className="size-4 accent-accent"
            />
            {t(`appearance.${mode}`)}
          </label>
        ))}
      </div>
      {display.settings.mode === "system" ? (
        <p className="text-sm text-fg-muted" data-testid="settings-system-mode">
          {t(`appearance.systemCurrent.${display.system.dark ? "dark" : "light"}`)}
        </p>
      ) : null}
    </fieldset>
  );
}

function AccentSetting(): ReactElement {
  const { t } = useTranslation("settings");
  const display = useDisplay();
  const name = useId();
  const hintId = useId();
  const accentName = (accent: Accent): string => {
    const label = t(`accent.names.${accent}`);
    return accent === defaultSettings.accent ? t("accent.default", { name: label }) : label;
  };
  return (
    <fieldset className={fieldsetClass} aria-describedby={hintId} data-testid="settings-accent">
      <legend className={legendClass}>{t("accent.legend")}</legend>
      <p id={hintId} className="text-sm text-fg-muted">
        {t("accent.hint")}
      </p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3">
        {accents.map((accent) => {
          const checked = display.settings.accent === accent;
          return (
            <label
              key={accent}
              className={`flex cursor-pointer items-center gap-3 rounded border p-3 ${
                checked ? "border-accent bg-accent-soft" : "border-line-strong bg-surface hover:bg-surface-muted"
              }`}
            >
              <input
                type="radio"
                name={name}
                value={accent}
                checked={checked}
                onChange={() => {
                  updateDisplaySettings({ accent });
                }}
                data-testid={`settings-accent-${accent}`}
                className="size-4 accent-accent"
              />
              {/* Preview of the accent in the current mode: accent, its text and its soft background. */}
              <span
                aria-hidden="true"
                data-accent-preview={accent}
                className="flex h-8 w-14 shrink-0 overflow-hidden rounded border border-line"
              >
                <span className="flex flex-1 items-center justify-center bg-accent text-meta font-semibold text-on-accent">
                  Aa
                </span>
                <span className="flex-1 bg-accent-soft" />
              </span>
              <span>{accentName(accent)}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

function LanguageSetting(): ReactElement {
  // Re-renders on every language change, also when the switch in the header is used.
  const { t } = useTranslation(["settings", "common"]);
  const selectId = useId();
  const hintId = useId();
  const onChange = (event: ChangeEvent<HTMLSelectElement>): void => {
    const picked = event.target.value;
    if (isLanguage(picked)) {
      void changeLanguage(picked);
    }
  };
  return (
    <fieldset className={fieldsetClass} data-testid="settings-language">
      <legend className={legendClass}>{t("settings:language.legend")}</legend>
      <div className="space-y-1">
        <label htmlFor={selectId} className="block text-sm text-fg-muted">
          {t("settings:language.label")}
        </label>
        <Select
          id={selectId}
          value={currentLanguage()}
          onChange={onChange}
          aria-describedby={hintId}
          data-testid="settings-language-select"
        >
          {supportedLanguages.map((option) => (
            <option key={option} value={option} lang={option}>
              {t(`common:language.${option}`)}
            </option>
          ))}
        </Select>
        <p id={hintId} className="text-sm text-fg-muted">
          {t("settings:language.hint")}
        </p>
      </div>
    </fieldset>
  );
}

function MotionSetting(): ReactElement {
  const { t } = useTranslation("settings");
  const display = useDisplay();
  const checkboxId = useId();
  const hintId = useId();
  return (
    <fieldset className={fieldsetClass} data-testid="settings-motion">
      <legend className={legendClass}>{t("motion.legend")}</legend>
      <div className="flex items-center gap-2">
        <input
          id={checkboxId}
          type="checkbox"
          checked={display.settings.reduceMotion}
          onChange={(event) => {
            updateDisplaySettings({ reduceMotion: event.target.checked });
          }}
          aria-describedby={hintId}
          data-testid="settings-reduce-motion"
          className="size-4 accent-accent"
        />
        <label htmlFor={checkboxId}>{t("motion.label")}</label>
      </div>
      <p id={hintId} className="text-sm text-fg-muted">
        {t("motion.hint")}
      </p>
      {display.system.reduceMotion ? (
        <p className="text-sm text-fg-muted" data-testid="settings-system-motion">
          {t("motion.system")}
        </p>
      ) : null}
    </fieldset>
  );
}
