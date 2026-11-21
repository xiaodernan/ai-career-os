/**
 * 358: the tables a test renders the provider with.
 *
 * In the browser the reader's own table arrives with the HTML, so no shipped module
 * imports one. A test renders `<LocaleProvider>` directly, with no server behind it,
 * and still has to answer strings in both languages -- so the two tables are installed
 * here for the run. Nothing in `src/lib` or `src/components` writes this; it is the
 * test's own seam, and a browser that received no table would show keys rather than a
 * language it was never given.
 */
import { translations } from "@/lib/i18n/translations";

(globalThis as { __CAREEROS_TABLES__?: unknown }).__CAREEROS_TABLES__ = translations;
