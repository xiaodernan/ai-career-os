/*
 * The offline shell (19.7).
 *
 * This file is served as-is from `public/sw.js` -- it is not part of the Next bundle, because a
 * service worker runs on its own thread, outlives the page, and has to be fetched by the browser
 * before any app code can ask for it. `src/lib/pwa.ts` is the only client that registers it, and
 * only a production build does.
 *
 * What it caches is deliberately small: the offline page and the two install icons. It does NOT
 * cache pages or API answers. A cached board would show yesterday's postings as today's, and a
 * cached `/api` response would show a quota from last night as this morning's -- a stale figure
 * the reader has no way to tell from a live one. Pages are authenticated and personal, so the
 * worker's job on a navigation is to try the network and, when there is none, to say so in the
 * product's own words instead of the browser's grey error page.
 *
 * `_next/static` chunks are content-hashed by the build, so a cached copy can never be stale:
 * the hash in the URL changes whenever the bytes do. Those are served cache-first with a
 * background refresh, which is what makes a second visit fast and a flaky connection usable.
 */

const SHELL_VERSION = "1";
const SHELL_CACHE = `careeros-shell-${SHELL_VERSION}`;
const OFFLINE_URL = "/offline.html";
const SHELL_ASSETS = [OFFLINE_URL, "/icons/icon-192.png", "/icons/icon-512.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      // One asset at a time: a single 404 must not reject the install and take the worker with
      // it -- the offline page is still worth having when an icon is missing.
      .then((cache) => Promise.all(SHELL_ASSETS.map((url) => cache.add(url).catch(() => undefined))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => key !== SHELL_CACHE).map((key) => caches.delete(key)))
      )
      .then(() => self.clients.claim())
  );
});

/* ---------------------------------------------------------------------------------------------
 * The bell outside the tab (33.4).
 *
 * The worker holds no account token, and must not: replaying the page's refresh token from here
 * would revoke the token family the page is still using, and one browser can have tabs open under
 * different accounts. So the notification is one sentence in the browser's own language -- no
 * count, no title, no name -- and the tab it opens reads the authenticated inbox itself.
 *
 * `pushsubscriptionchange` reports the new subscription to the page by message for the same
 * reason: only the page knows whose subscription it is. If no tab is open the message is lost and
 * the settings switch re-registers on its next visit.
 */

const PUSH_DEEPLINK = "/notifications";
const PUSH_RENEWED_MESSAGE = "careeros:push-renewed";
const PUSH_TITLE = "AI Career OS";
const PUSH_BODY = {
  en: "Something new is waiting in your inbox.",
  zh: "收件箱里有新东西。",
};

/** The one sentence, in whichever language the browser is set to. */
function pushCopy() {
  const language = (self.navigator.language || "").toLowerCase();
  return language.startsWith("zh") ? PUSH_BODY.zh : PUSH_BODY.en;
}

self.addEventListener("push", (event) => {
  event.waitUntil(
    self.registration.showNotification(PUSH_TITLE, {
      body: pushCopy(),
      icon: "/icons/icon-192.png",
      badge: "/icons/icon-192.png",
      // One bubble per inbox, not one per event: a morning with five additions is still one
      // sentence, and the deep link is the same for all of them.
      tag: "careeros-inbox",
      data: { url: PUSH_DEEPLINK },
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || PUSH_DEEPLINK;
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
      // A tab already on the inbox is the reader's own; focus it instead of stacking another.
      const open = windows.find((client) => {
        try {
          return new URL(client.url).pathname === target;
        } catch {
          return false;
        }
      });
      if (open) return open.focus();
      // `openWindow` is allowed from a notification click and nowhere else, which is exactly
      // where this runs.
      return self.clients.openWindow(target);
    })
  );
});

self.addEventListener("pushsubscriptionchange", (event) => {
  const old = event.oldSubscription;
  // Without the old options there is no key to subscribe with; the switch on the settings page
  // is the repair path, so this event simply gives up.
  if (!old || !old.options) return;

  const renewed = event.newSubscription
    ? Promise.resolve(event.newSubscription)
    : self.registration.pushManager.subscribe(old.options);

  event.waitUntil(
    renewed
      .then((subscription) =>
        self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((windows) => {
          for (const client of windows) {
            client.postMessage({
              type: PUSH_RENEWED_MESSAGE,
              subscription: subscription.toJSON(),
            });
          }
        })
      )
      .catch(() => undefined)
  );
});

/** The build's own immutable chunks and the install icons -- the only things safe to keep. */
function isImmutableAsset(url) {
  return url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/icons/");
}

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // The API is the one thing the shell must never answer from a cache: a figure read before the
  // connection dropped is indistinguishable from a live one once it is on the page.
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/internal/")) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).catch(() =>
        caches
          .match(OFFLINE_URL)
          // No cached shell means the install never completed; the browser's own network error is
          // more honest than a page pretending to be the app.
          .then((cached) => cached ?? Response.error())
      )
    );
    return;
  }

  if (!isImmutableAsset(url)) return;

  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(SHELL_CACHE).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() => undefined);
      // A cached chunk is already the right bytes; the refresh above updates the copy for the
      // next visit without making this one wait for the network.
      return cached ?? network.then((response) => response ?? Response.error());
    })
  );
});
