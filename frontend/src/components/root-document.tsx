import * as React from "react";

import { Providers } from "@/components/providers";
import { LocaleProvider } from "@/lib/i18n/locale-context";
import type { Locale } from "@/lib/i18n/translations";

/**
 * The document shell: `<html lang>` and the providers around every page.
 *
 * Separate from `app/layout.tsx` so the shell can be rendered without the router's
 * machinery (fonts, metadata, `cookies()`). The layout reads the locale cookie and hands
 * the result here, so both the `lang` attribute and the provider's first render are in the
 * reader's language in the HTML the server sends — not one effect later.
 */
export function RootDocument({
  locale,
  bodyClassName,
  children,
}: {
  locale: Locale;
  bodyClassName: string;
  children: React.ReactNode;
}) {
  return (
    <html lang={locale} suppressHydrationWarning>
      <body className={bodyClassName}>
        <LocaleProvider initialLocale={locale}>
          <Providers>{children}</Providers>
        </LocaleProvider>
      </body>
    </html>
  );
}
