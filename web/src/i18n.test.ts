import { afterEach, describe, expect, it, vi } from "vitest";

import {
  i18n,
  initialLanguage,
  languageFromPreferences,
  languageStorageKey,
  namespaces,
  readStoredLanguage,
  resources,
  supportedLanguages,
} from "./i18n.ts";

afterEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
  document.documentElement.lang = "en";
});

function stubBrowserLanguages(languages: readonly string[]): void {
  vi.spyOn(window.navigator, "languages", "get").mockReturnValue(languages);
}

describe("language from the browser preferences", () => {
  it.each([
    [["de-DE", "en-US"], "de"],
    [["de"], "de"],
    [["DE-at"], "de"],
    [["en-GB", "de"], "en"],
    [["fr-FR", "de-CH", "en"], "de"],
    [["fr", "it"], "en"],
    [[], "en"],
  ] as const)("picks the first supported language of %j: %s", (preferred, expected) => {
    expect(languageFromPreferences(preferred)).toBe(expected);
  });
});

describe("first choice at page load", () => {
  it("follows navigator.languages when nothing is stored", () => {
    stubBrowserLanguages(["de-AT", "en"]);
    expect(initialLanguage()).toBe("de");

    stubBrowserLanguages(["es", "en-US"]);
    expect(initialLanguage()).toBe("en");

    stubBrowserLanguages(["es"]);
    expect(initialLanguage()).toBe("en");
  });

  it("prefers a stored choice over the browser languages", () => {
    stubBrowserLanguages(["de-DE"]);
    window.localStorage.setItem(languageStorageKey, "en");
    expect(initialLanguage()).toBe("en");
  });

  it("ignores an invalid stored value", () => {
    stubBrowserLanguages(["de-DE"]);
    window.localStorage.setItem(languageStorageKey, "klingon");
    expect(readStoredLanguage()).toBeNull();
    expect(initialLanguage()).toBe("de");
  });

  it("falls back to the browser languages when the storage throws", () => {
    stubBrowserLanguages(["de-DE"]);
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    expect(readStoredLanguage()).toBeNull();
    expect(initialLanguage()).toBe("de");
  });

  it("starts the app in the browser language and sets <html lang>", async () => {
    stubBrowserLanguages(["de-DE", "en"]);
    vi.resetModules();
    const fresh = await import("./i18n.ts");

    expect(fresh.currentLanguage()).toBe("de");
    expect(document.documentElement.lang).toBe("de");
    expect(fresh.i18n.t("heading", { ns: "selftest" })).toBe("Selbsttest");
  });

  it("starts in English for an unsupported browser language", async () => {
    stubBrowserLanguages(["fr-FR"]);
    document.documentElement.lang = "xx";
    vi.resetModules();
    const fresh = await import("./i18n.ts");

    expect(fresh.currentLanguage()).toBe("en");
    expect(document.documentElement.lang).toBe("en");
  });
});

describe("switching the language", () => {
  it("still switches when the storage cannot be written", async () => {
    const fresh = await freshModule();
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("full", "QuotaExceededError");
    });

    await fresh.changeLanguage("de");

    expect(fresh.currentLanguage()).toBe("de");
    expect(document.documentElement.lang).toBe("de");
  });
});

async function freshModule(): Promise<typeof import("./i18n.ts")> {
  stubBrowserLanguages(["en-US"]);
  vi.resetModules();
  return import("./i18n.ts");
}

/** All key paths of a catalog, nested objects joined with dots. */
function keyPaths(catalog: unknown, prefix = ""): string[] {
  if (typeof catalog !== "object" || catalog === null) {
    return [prefix];
  }
  return Object.entries(catalog)
    .flatMap(([key, value]) => keyPaths(value, prefix === "" ? key : `${prefix}.${key}`))
    .sort();
}

function leafValues(catalog: unknown): unknown[] {
  if (typeof catalog !== "object" || catalog === null) {
    return [catalog];
  }
  return Object.values(catalog).flatMap(leafValues);
}

const catalogFiles =import.meta.glob<unknown>("./locales/*/*.json", {
  eager: true,
  import: "default",
});

describe("catalogs", () => {
  it("has a JSON file for every namespace in both languages, and no others", () => {
    const expected = supportedLanguages
      .flatMap((language) => namespaces.map((ns) => `./locales/${language}/${ns}.json`))
      .sort();
    expect(Object.keys(catalogFiles).sort()).toEqual(expected);
    expect(namespaces).toHaveLength(11);
  });

  it.each(namespaces)("namespace %s has the same keys in German and English", (ns) => {
    const english = catalogFiles[`./locales/en/${ns}.json`];
    const german = catalogFiles[`./locales/de/${ns}.json`];
    expect(english).toBeDefined();
    expect(german).toBeDefined();
    expect(keyPaths(german)).toEqual(keyPaths(english));
  });

  it("has only non-empty strings as values", () => {
    for (const [file, catalog] of Object.entries(catalogFiles)) {
      expect(typeof catalog, file).toBe("object");
      for (const value of leafValues(catalog)) {
        expect(typeof value === "string" && value.trim() !== "", `${file}: ${String(value)}`).toBe(
          true,
        );
      }
    }
  });

  it("registers every namespace of both languages with i18next", () => {
    for (const language of supportedLanguages) {
      expect(Object.keys(resources[language]).sort()).toEqual([...namespaces].sort());
      for (const ns of namespaces) {
        expect(i18n.hasResourceBundle(language, ns), `${language}/${ns}`).toBe(true);
      }
    }
  });
});
