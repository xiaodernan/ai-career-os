/**
 * CN/EN translations (17.1). The two tables live in ./en.ts and ./zh.ts; this
 * module is the seam -- the export surface every call site and test reads, with the
 * envelope and the key type. Split in Epic 265; behaviour is byte-identical.
 *
 * 358: the seam is a *type* seam for the browser now. The tables are the heaviest
 * thing in the client bundle (~170 kB gzip for the two) and every route paid for
 * both, whatever language it paints. `LocaleTable` is therefore exported as a type
 * only: the server layout imports the values and hands the reader's own table down
 * with the HTML, and no client module statically imports a table any more. The
 * runtime value (`translations`) is what the server and the tests read.
 */
import { en } from "./en";
import { zh } from "./zh";

export type Locale = "en" | "zh";

export const translations = { en, zh } as const;

export type TranslationKey = keyof typeof translations.en;

/**
 * One language's table: every key the product speaks, in one language.
 *
 * The union, not `typeof en`: the two tables hold the same keys with different words,
 * and a reader whose table is the Chinese one has to be able to hand it to the same
 * provider the English reader uses.
 */
export type LocaleTable = (typeof translations)[Locale];
