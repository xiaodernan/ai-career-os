import type { Viewport } from "next";
import { cookies, headers } from "next/headers";
// Self-hosted fonts (@fontsource-variable), not next/font/google: the Docker
// build has no route to fonts.googleapis.com, and the browser should not
// fetch its front-door type from a third party at all. Variable axes match
// what next/font loaded (Inter 100-900, Newsreader incl. italic, JetBrains Mono).
import "@fontsource-variable/inter";
import "@fontsource-variable/newsreader";
import "@fontsource-variable/jetbrains-mono";
import "./globals.css";
import { RootDocument } from "@/components/root-document";
import { rootMetadata } from "@/lib/i18n/metadata";
import { LOCALE_COOKIE, localeFromCookie } from "@/lib/i18n/locale-cookie";

/**
 * The root's metadata.
 *
 * The product's name and the title template are the brand's -- the same
 * in every language -- but the description is a sentence, and it is
 * read by a search engine rather than by the page, so it is in the
 * reader's language. The locale travels in a cookie, so the server can
 * read it and put the sentence in the head it sends.
 */
export const generateMetadata = rootMetadata();


export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fcfcfd" },
    { media: "(prefers-color-scheme: dark)", color: "#141518" },
  ],
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  // The same cookie the page's metadata reads: the body, like the title, is English until
  // the reader's language is known, and the only place it can be known before hydration is
  // the request. `localeFromCookie` maps anything unknown back to English.
  const store = await cookies();
  const locale = localeFromCookie(store.get(LOCALE_COOKIE)?.value);
  // The middleware stamped this answer's nonce on the request. Next puts it on the
  // scripts it emits, but next-themes writes its own theme bootstrap, so the nonce
  // has to travel to that one by hand or the policy blocks the reader's first paint.
  const nonce = (await headers()).get("x-nonce") ?? undefined;
  return (
    <RootDocument
      locale={locale}
      nonce={nonce}
      bodyClassName="min-h-dvh bg-background text-foreground"
    >
      {children}
    </RootDocument>
  );
}
