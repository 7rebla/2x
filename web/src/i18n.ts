// Translation of the user interface (German and English).
//
// The catalogs live in src/locales/<language>/<namespace>.json and are bundled
// with the build; nothing is loaded over the network. This file registers every
// namespace of milestone M1 (and "map" of work order 039, "settings" of 070, "search" of 054, "ingest" of 055, "answers" of 132) once. Later pages only
// fill their own JSON files; neither this file nor src/i18next.d.ts changes for that.
import i18next, { type i18n as I18n } from "i18next";
import { initReactI18next } from "react-i18next";

import deAnswers from "./locales/de/answers.json";
import deAssets from "./locales/de/assets.json";
import deAudit from "./locales/de/audit.json";
import deAuth from "./locales/de/auth.json";
import deCommon from "./locales/de/common.json";
import deFiles from "./locales/de/files.json";
import deImport from "./locales/de/import.json";
import deIngest from "./locales/de/ingest.json";
import deMap from "./locales/de/map.json";
import deNav from "./locales/de/nav.json";
import deSearch from "./locales/de/search.json";
import deSelftest from "./locales/de/selftest.json";
import deSettings from "./locales/de/settings.json";
import enAnswers from "./locales/en/answers.json";
import enAssets from "./locales/en/assets.json";
import enAudit from "./locales/en/audit.json";
import enAuth from "./locales/en/auth.json";
import enCommon from "./locales/en/common.json";
import enFiles from "./locales/en/files.json";
import enImport from "./locales/en/import.json";
import enIngest from "./locales/en/ingest.json";
import enMap from "./locales/en/map.json";
import enNav from "./locales/en/nav.json";
import enSearch from "./locales/en/search.json";
import enSelftest from "./locales/en/selftest.json";
import enSettings from "./locales/en/settings.json";

export const supportedLanguages = ["en", "de"] as const;
export type Language = (typeof supportedLanguages)[number];

/** Used when neither a stored choice nor a browser language matches. */
export const defaultLanguage: Language = "en";

export const namespaces = [
  "common",
  "nav",
  "selftest",
  "auth",
  "assets",
  "audit",
  "import",
  "files",
  "map",
  "settings",
  "search",
  "ingest",
  "answers",
] as const;
export type Namespace = (typeof namespaces)[number];

/** localStorage key of the language the user picked with the switch. */
export const languageStorageKey = "twox.language";

export const resources = {
  en: {
    common: enCommon,
    nav: enNav,
    selftest: enSelftest,
    auth: enAuth,
    assets: enAssets,
    audit: enAudit,
    import: enImport,
    files: enFiles,
    map: enMap,
    settings: enSettings,
    search: enSearch,
    ingest: enIngest,
    answers: enAnswers,
  },
  de: {
    common: deCommon,
    nav: deNav,
    selftest: deSelftest,
    auth: deAuth,
    assets: deAssets,
    audit: deAudit,
    import: deImport,
    files: deFiles,
    map: deMap,
    settings: deSettings,
    search: deSearch,
    ingest: deIngest,
    answers: deAnswers,
  },
} as const satisfies Record<Language, Record<Namespace, object>>;

export function isLanguage(value: unknown): value is Language {
  return typeof value === "string" && (supportedLanguages as readonly string[]).includes(value);
}

/**
 * First supported language in the browser's preference list, compared by the
 * primary subtag ("de-AT" counts as "de"); English if none matches.
 */
export function languageFromPreferences(preferred: readonly string[]): Language {
  for (const tag of preferred) {
    const primary = tag.split("-")[0]?.trim().toLowerCase();
    if (isLanguage(primary)) {
      return primary;
    }
  }
  return defaultLanguage;
}

function browserLanguages(): readonly string[] {
  try {
    if (navigator.languages.length > 0) {
      return navigator.languages;
    }
    return navigator.language === "" ? [] : [navigator.language];
  } catch {
    return [];
  }
}

/** The stored choice, or null if there is none or the storage is not usable. */
export function readStoredLanguage(): Language | null {
  try {
    const stored = window.localStorage.getItem(languageStorageKey);
    return isLanguage(stored) ? stored : null;
  } catch {
    return null;
  }
}

function storeLanguage(language: Language): void {
  try {
    window.localStorage.setItem(languageStorageKey, language);
  } catch {
    // Storage blocked or full: the choice then lasts until the page is reloaded.
  }
}

/** Language at page load: the stored choice first, then the browser languages. */
export function initialLanguage(): Language {
  return readStoredLanguage() ?? languageFromPreferences(browserLanguages());
}

export const i18n: I18n = i18next.createInstance();

i18n.on("languageChanged", (language: string) => {
  document.documentElement.lang = isLanguage(language) ? language : defaultLanguage;
});

void i18n.use(initReactI18next).init({
  resources,
  lng: initialLanguage(),
  fallbackLng: defaultLanguage,
  supportedLngs: supportedLanguages,
  ns: namespaces,
  defaultNS: "common",
  // React escapes every value it renders.
  interpolation: { escapeValue: false },
  // All catalogs are bundled, so the instance is ready right after this call.
  initAsync: false,
  returnNull: false,
});

/** Language currently shown. */
export function currentLanguage(): Language {
  const language = i18n.resolvedLanguage;
  return isLanguage(language) ? language : defaultLanguage;
}

/** Switches the language, remembers the choice and updates <html lang>. */
export async function changeLanguage(language: Language): Promise<void> {
  storeLanguage(language);
  await i18n.changeLanguage(language);
}
