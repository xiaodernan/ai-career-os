import type { Locale, LocaleTable } from "./translations";

/**
 * 358: where a table comes from when nothing sent one.
 *
 * In the browser the reader's own table arrives with the HTML -- the server layout
 * reads the cookie, picks `translations[locale]` and hands it to the provider, so
 * neither table is in the client bundle at all. A test renders the provider
 * directly, with no server behind it, and still has to answer strings in both
 * languages; `src/test/locale-tables.ts` installs both here for exactly that.
 *
 * It is a seam and not a shortcut: nothing in a shipped module ever writes this,
 * so a browser that did not receive a table would see keys rather than a wrong
 * language, and the setup file that installs them is test-only by construction.
 */
export interface InstalledTables {
  en: LocaleTable;
  zh: LocaleTable;
}

declare global {
  var __CAREEROS_TABLES__: InstalledTables | undefined;
}

export function installedTables(): InstalledTables | undefined {
  return globalThis.__CAREEROS_TABLES__;
}

export function installedTable(locale: Locale): LocaleTable | undefined {
  return globalThis.__CAREEROS_TABLES__?.[locale];
}
