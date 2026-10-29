import type { Viewport } from "next";
import { cookies, headers } from "next/headers";
import { Inter, Newsreader, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { RootDocument } from "@/components/root-document";
import { rootMetadata } from "@/lib/i18n/metadata";
import { LOCALE_COOKIE, localeFromCookie } from "@/lib/i18n/locale-cookie";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const newsreader = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
  style: ["normal", "italic"],
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
  display: "swap",
});

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
      bodyClassName={`${inter.variable} ${newsreader.variable} ${jetbrains.variable} min-h-dvh bg-background text-foreground`}
    >
      {children}
    </RootDocument>
  );
}
