import type { MetadataRoute } from "next";
import { cookies } from "next/headers";

import { LOCALE_COOKIE, localeFromCookie } from "@/lib/i18n/locale-cookie";
import { readKey } from "@/lib/i18n/metadata";

/**
 * The installable app's own metadata (19.7).
 *
 * Next serves this at `/manifest.webmanifest` and writes the `<link rel="manifest">` into the
 * document head itself, so the browser's install prompt has a name, a start URL, a scope and a
 * set of icons without the document restating any of them.
 *
 * The name and the short name are the brand's -- the same two words in every language, like the
 * document title. The description is a sentence, so it travels the road every sentence in this
 * product travels: the locale cookie, read on the server, rendered through the table. A browser
 * that fetches the manifest without the cookie (a first visit, an install from a link) gets
 * English, which is the same default the document shows before the reader picks a language.
 *
 * `start_url` is the dashboard rather than `/`: `/` is the pitch and a signed-out reader lands
 * there, while an installed app is opened by someone who already has a session, and the shell
 * they want is the board. The scope stays `/` so every route the sidebar reaches is inside the
 * installed window.
 */
export default async function manifest(): Promise<MetadataRoute.Manifest> {
  const store = await cookies();
  const locale = localeFromCookie(store.get(LOCALE_COOKIE)?.value);
  return {
    id: "/",
    name: "AI Career OS",
    short_name: "CareerOS",
    description: readKey(locale, "common.metaDescription"),
    lang: locale,
    start_url: "/dashboard",
    scope: "/",
    display: "standalone",
    orientation: "any",
    // The light theme's own two tokens (`globals.css`), so the launch screen and the status bar
    // are the paper the app already paints rather than a flash of white on a dark phone.
    background_color: "#fcfcfd",
    theme_color: "#fcfcfd",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      // Android masks an icon to its own shape; a full-bleed square with the sparkle inside the
      // 80% safe zone is the declaration that lets it, instead of a rounded tile inside a circle.
      {
        src: "/icons/icon-maskable-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
