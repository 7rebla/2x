// Type extension of i18next: the keys of every namespace come from the English
// catalogs, so TypeScript reports an unknown key (or a missing namespace) as
// an error. The German catalogs must have the same keys; a test checks that.
import "i18next";

import type assets from "./locales/en/assets.json";
import type audit from "./locales/en/audit.json";
import type auth from "./locales/en/auth.json";
import type common from "./locales/en/common.json";
import type files from "./locales/en/files.json";
import type importCatalog from "./locales/en/import.json";
import type ingest from "./locales/en/ingest.json";
import type map from "./locales/en/map.json";
import type nav from "./locales/en/nav.json";
import type search from "./locales/en/search.json";
import type selftest from "./locales/en/selftest.json";
import type settings from "./locales/en/settings.json";

declare module "i18next" {
  interface CustomTypeOptions {
    defaultNS: "common";
    resources: {
      common: typeof common;
      nav: typeof nav;
      selftest: typeof selftest;
      auth: typeof auth;
      assets: typeof assets;
      audit: typeof audit;
      import: typeof importCatalog;
      files: typeof files;
      map: typeof map;
      settings: typeof settings;
      search: typeof search;
      ingest: typeof ingest;
    };
    returnNull: false;
  }
}
