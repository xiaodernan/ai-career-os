/**
 * The service worker's client half (19.7).
 *
 * The worker itself is `public/sw.js` -- a plain file the browser fetches and runs on its own,
 * outside the bundle. This module is the one place the app asks for it, and it exists as a
 * function rather than an effect so the decision can be measured without a browser.
 *
 * Two rules the rest of the app depends on:
 *
 * 1. **Only a production build registers it.** A worker on a dev server caches the app's
 *    `_next/static` chunks ahead of HMR, so the next refresh serves the code the worker saved
 *    rather than the code just written -- the classic "my change is not showing up". The worker
 *    is part of the shipped shell, not part of the editing loop.
 * 2. **A failed install is not an app failure.** Registration rejects in private windows, on
 *    browsers that have disabled storage, and whenever the origin is not secure. The app keeps
 *    working without a worker; only the offline shell is lost, so the failure is swallowed
 *    rather than surfaced as an error on a screen that has nothing to do with it.
 */

/** Where `public/sw.js` is served from. The worker's own scope is `/`. */
export const SERVICE_WORKER_PATH = "/sw.js";

/** The environments whose build ships a worker; the dev server's does not. */
export function shouldRegisterServiceWorker(nodeEnv: string | undefined): boolean {
  return nodeEnv === "production";
}

/** The part of `navigator` this module needs, so a test can hand over a stand-in. */
export interface ServiceWorkerHost {
  serviceWorker?: {
    register: (scriptURL: string, options?: { scope?: string }) => Promise<unknown>;
  };
}

/**
 * Register the offline shell, if this browser has one to register.
 *
 * Answers the registration when it happened and `undefined` when it did not -- a browser with
 * no `serviceWorker`, a development build, or a rejected install. Nothing here throws.
 */
export async function registerServiceWorker(
  host: ServiceWorkerHost = navigator,
  nodeEnv: string | undefined = process.env.NODE_ENV
): Promise<unknown | undefined> {
  if (!shouldRegisterServiceWorker(nodeEnv)) return undefined;
  if (!host.serviceWorker) return undefined;
  try {
    return await host.serviceWorker.register(SERVICE_WORKER_PATH, { scope: "/" });
  } catch {
    return undefined;
  }
}
