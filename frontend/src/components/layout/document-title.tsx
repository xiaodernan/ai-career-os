"use client";

import * as React from "react";
import { usePathname } from "next/navigation";
import { useLocale } from "@/lib/i18n/locale-context";
import { routeTitle } from "./nav";

/**
 * The browser tab's title, in the reader's language.
 *
 * Next.js reads a route's title from the `metadata` export, which is
 * evaluated on the server -- and the server cannot know the language,
 * because this product keeps the locale in the browser's own storage, not
 * in a cookie the server could read. So every route's title was English,
 * whatever the reader chose, and the title was the one thing on the page
 * that never changed.
 *
 * This sets it from the same table the top bar reads, in the reader's
 * language, and keeps the "· AI Career OS" suffix the root layout's
 * template gives. The server's title is what the reader sees for the
 * moment before this runs -- which is the honest answer to a locale the
 * server cannot read.
 */
export function DocumentTitle() {
  const pathname = usePathname();
  const { t, locale } = useLocale();

  React.useEffect(() => {
    // `routeTitle` answers `null` for a path the product does not name --
    // a 404, a route that does not exist yet. Setting the title for those
    // would overwrite the server's own, which is the right one.
    const title = routeTitle(pathname, t);
    if (!title) return;
    document.title = title === "AI Career OS" ? title : `${title} · AI Career OS`;
  }, [pathname, t, locale]);

  return null;
}
