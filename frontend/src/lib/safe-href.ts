/**
 * safeHref -- how a link the app did not build itself becomes an href worth rendering.
 *
 * Measured on this repo's own renderer, not assumed:
 * - React rewrites a `javascript:` href to a throw, so the classic "click the stored
 *   script" is already gone at every sink, `<a>` and `<Link>` alike.
 * - `data:`, `file:` and custom schemes (`tg:`, `intent:`) are NOT rewritten: they reach
 *   the DOM verbatim, where they open the reader's local disk or another application.
 * - A value with no scheme -- `www.acme.com/careers`, which is what an LLM writes for a
 *   company site and what a reader pastes from an address bar -- resolves as a RELATIVE
 *   path, so the "Original posting" button walks to `/jobs/www.acme.com/careers` inside
 *   this app instead of opening the posting.
 *
 * So one rule covers all three: a link may only open a page over http(s); a bare host
 * gets the scheme its reader forgot; anything that cannot be a page is no link at all.
 */

/** Schemes a browser can hand to another handler, or run. Anything here is refused unless openable. */
const KNOWN_SCHEMES = new Set([
  "about",
  "blob",
  "callto",
  "chrome",
  "data",
  "file",
  "ftp",
  "ftps",
  "geo",
  "http",
  "https",
  "intent",
  "javascript",
  "magnet",
  "mailto",
  "skype",
  "sms",
  "tg",
  "tel",
  "view-source",
  "vbscript",
  "whatsapp",
  "ws",
  "wss",
]);

const SCHEME_TOKEN = /^[a-z][a-z0-9+.-]*$/i;

function parsesAsPage(value: string): boolean {
  try {
    const url = new URL(value);
    // Userinfo is a spoof: `https://careeros.example.com@evil.com` reads as our own host.
    if (url.username || url.password) return false;
    return (url.protocol === "http:" || url.protocol === "https:") && url.hostname.length > 0;
  } catch {
    return false;
  }
}

/** The href to render, or undefined when the value cannot open a page -- then there is no link. */
export function safeHref(value: string | null | undefined): string | undefined {
  const raw = value?.trim();
  if (!raw) return undefined;

  if (raw.startsWith("#")) return raw;
  if (raw.startsWith("//")) return parsesAsPage(`https:${raw}`) ? `https:${raw}` : undefined;
  if (raw.startsWith("/")) return raw;

  const colon = raw.indexOf(":");
  const slash = raw.indexOf("/");
  const scheme = colon > 0 && (slash === -1 || colon < slash) ? raw.slice(0, colon).toLowerCase() : "";
  if (scheme && SCHEME_TOKEN.test(scheme) && KNOWN_SCHEMES.has(scheme)) {
    const openable = scheme === "http" || scheme === "https";
    return openable && parsesAsPage(raw) ? raw : undefined;
  }

  // No scheme, or a colon-prefix that is really a host:port (`localhost:3000/careers`).
  const absolute = `https://${raw}`;
  return parsesAsPage(absolute) ? absolute : undefined;
}
