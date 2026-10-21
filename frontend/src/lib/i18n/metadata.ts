import type { Metadata } from "next";
import { cookies } from "next/headers";

import { LOCALE_COOKIE, localeFromCookie } from "./locale-cookie";
import { translations, type Locale } from "./translations";

/**
 * The page's title, from the reader's language.
 *
 * Next.js reads a route's title from `metadata` -- either a literal export
 * or a `generateMetadata` function -- and renders it into the document's
 * head. The literal export can only ever be English: the server does not
 * know which language the reader chose, because the product keeps the
 * locale in the browser's own storage.
 *
 * The client cannot do it either, and this is the part that is easy to get
 * wrong. A `useEffect` that writes `document.title` does run, and the title
 * does change -- and then React's own metadata reconciliation resets it,
 * because the `<title>` element is part of the tree it just hydrated. The
 * write is undone a moment after it happens, and the reader sees the
 * server's English title for the whole visit.
 *
 * So the locale goes into a cookie as well as into localStorage, and the
 * server reads it. The title is then right in the HTML the server sends,
 * which is the only place a title can be right: it is the head the browser
 * paints before any script runs, and the head a crawler reads.
 */

/** Read a key out of the table, in the reader's language. */
function read(locale: Locale, key: string): string {
  let value: unknown = translations[locale];
  for (const part of key.split(".")) {
    if (value != null && typeof value === "object") {
      value = (value as Record<string, unknown>)[part];
    } else {
      return key;
    }
  }
  return typeof value === "string" ? value : key;
}

/**
 * A `generateMetadata` for a route whose title is one of the table's
 * strings.
 *
 * The root layout's `title.template` gives the suffix, so a section's
 * title reads "Jobs · AI Career OS" in English and "职位 · AI Career OS"
 * in Chinese -- the same shape in both.
 */
export function sectionMetadata(key: string): () => Promise<Metadata> {
  return async function generateMetadata(): Promise<Metadata> {
    const store = await cookies();
    const locale = localeFromCookie(store.get(LOCALE_COOKIE)?.value);
    return { title: read(locale, key) };
  };
}

/**
 * A `generateMetadata` for a route whose title stands on its own.
 *
 * The landing page's title is the product's pitch, not a section name, so
 * it does not take the template's suffix. The description travels with it:
 * a search engine reads the description, not the page, so it is in the
 * reader's language too.
 */
export function absoluteMetadata(
  key: string,
  description?: string
): () => Promise<Metadata> {
  return async function generateMetadata(): Promise<Metadata> {
    const store = await cookies();
    const locale = localeFromCookie(store.get(LOCALE_COOKIE)?.value);
    return { title: { absolute: read(locale, key) }, description };
  };
}

/**
 * The root's metadata: the product's name, the title template every
 * section's title takes, and the site's own description.
 *
 * The name and the template are the brand's -- they are the same in
 * every language -- but the description is a sentence, and a sentence
 * the reader might not read is a sentence that should be in their
 * language. So the description travels the same road the titles do.
 */
export function rootMetadata(): () => Promise<Metadata> {
  return async function generateMetadata(): Promise<Metadata> {
    const store = await cookies();
    const locale = localeFromCookie(store.get(LOCALE_COOKIE)?.value);
    return {
      title: {
        default: "AI Career OS",
        template: "%s · AI Career OS",
      },
      description: read(locale, "common.metaDescription"),
    };
  };
}
