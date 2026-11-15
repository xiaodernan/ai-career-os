/**
 * CN/EN translations (17.1). The two tables live in ./en.ts and ./zh.ts; this
 * module is the seam -- the export surface every call site and test reads, with the
 * envelope and the key type. Split in Epic 265; behaviour is byte-identical.
 */
import { en } from "./en";
import { zh } from "./zh";

export type Locale = "en" | "zh";

export const translations = { en, zh } as const;

export type TranslationKey = keyof typeof translations.en;
