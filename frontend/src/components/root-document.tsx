import * as React from "react";

import { Providers } from "@/components/providers";
import { LocaleProvider } from "@/lib/i18n/locale-context";
import { translations, type Locale } from "@/lib/i18n/translations";

/**
 * The document shell: `<html lang>` and the providers around every page.
 *
 * Separate from `app/layout.tsx` so the shell can be rendered without the router's
 * machinery (fonts, metadata, `cookies()`). The layout reads the locale cookie and hands
 * the result here, so both the `lang` attribute and the provider's first render are in the
 * reader's language in the HTML the server sends — not one effect later.
 *
 * 358: and the table rides along, for the same reason. This module is a server component,
 * so importing both tables here costs the server everything and the browser nothing: the
 * reader's own table crosses into the payload with the HTML, and neither language's words
 * are in the JavaScript the route loads.
 */
export function RootDocument({
  locale,
  nonce,
  bodyClassName,
  children,
}: {
  locale: Locale;
  /** The answer's content security nonce; absent outside the request shell (tests). */
  nonce?: string;
  bodyClassName: string;
  children: React.ReactNode;
}) {
  return (
    <html lang={locale} suppressHydrationWarning>
      <body className={bodyClassName}>
        <LocaleProvider initialLocale={locale} table={translations[locale]}>
          <Providers nonce={nonce}>{children}</Providers>
        </LocaleProvider>
      </body>
    </html>
  );
}
