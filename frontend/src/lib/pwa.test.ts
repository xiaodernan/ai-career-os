import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it, vi } from "vitest";

import {
  registerServiceWorker,
  SERVICE_WORKER_PATH,
  shouldRegisterServiceWorker,
  type ServiceWorkerHost,
} from "./pwa";
import { PUSH_DEEPLINK, PUSH_RENEWED_MESSAGE } from "./push";
import { translations } from "@/lib/i18n/translations";

/**
 * The installable shell (19.7).
 *
 * Three files ship together and this gate reads all three from disk, because none of them is
 * imported by the app: `public/sw.js` is fetched by the browser's worker machinery,
 * `public/offline.html` is served by that worker when the network is gone, and the icons are
 * bytes on a disk that a manifest points at by name. A typo in any of them compiles, passes
 * every type check, and shows up only on a phone that has been put in airplane mode -- which is
 * the one moment the product cannot be asked to fix itself.
 *
 * The manifest is the fourth piece and it is imported, because it is a route: its description
 * is a sentence the reader might have to read, so it travels the same locale cookie the
 * document's metadata does.
 */

const ROOT = fileURLToPath(new URL("../../", import.meta.url));

/** Read one of the public files as text. */
function publicFile(name: string): string {
  const path = `${ROOT}public/${name}`;
  expect(existsSync(path), `public/${name} is not on disk`).toBe(true);
  return readFileSync(path, "utf8");
}

/** The pixel width and height out of a PNG's IHDR chunk. */
function pngSize(name: string): [number, number] {
  const bytes = readFileSync(`${ROOT}public/${name}`);
  expect(bytes.subarray(0, 8), `${name} is not a PNG`).toEqual(
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
  );
  // Signature (8) + length (4) + "IHDR" (4), then width and height, big-endian.
  return [bytes.readUInt32BE(16), bytes.readUInt32BE(20)];
}

const manifestResponse = { value: "zh" as string | undefined };
vi.mock("next/headers", () => ({
  cookies: async () => ({
    get: (name: string) => (name === "careeros.locale" ? manifestResponse : undefined),
  }),
}));

describe("the installable shell", () => {
  it("declares a manifest whose description is the table's sentence", async () => {
    const { default: manifest } = await import("@/app/manifest");
    const answer = await manifest();

    expect(answer.name, "the brand, in every language").toBe("AI Career OS");
    expect(answer.short_name).toBe("CareerOS");
    // zh via the cookie mock above: the description is a sentence, and a sentence is the
    // reader's. The English table is the control in the assertion below.
    expect(answer.description).toBe(translations.zh.common.metaDescription);
    expect(answer.description).not.toBe(translations.en.common.metaDescription);
    expect(answer.lang).toBe("zh");

    expect(answer.start_url, "an install opens on the board, not the pitch").toBe("/dashboard");
    expect(answer.scope).toBe("/");
    expect(answer.display).toBe("standalone");
  });

  it("names icons that exist, at the sizes the manifest promises", async () => {
    const { default: manifest } = await import("@/app/manifest");
    const answer = await manifest();
    const icons = answer.icons ?? [];
    expect(icons.length, "a manifest with no icons cannot be installed").toBeGreaterThan(0);

    const declared = icons.map((icon) => {
      const path = icon.src ?? "";
      expect(path.startsWith("/icons/"), `${path} is not under /icons/`).toBe(true);
      const name = `icons/${path.split("/")[2]}`;
      const [width, height] = pngSize(name);
      return { name, sizes: `${width}x${height}`, purpose: icon.purpose ?? "any" };
    });

    // Both roads -- the manifest and the document's `icons` metadata -- name files that exist.
    expect(declared).toEqual([
      { name: "icons/icon-192.png", sizes: "192x192", purpose: "any" },
      { name: "icons/icon-512.png", sizes: "512x512", purpose: "any" },
      { name: "icons/icon-maskable-512.png", sizes: "512x512", purpose: "maskable" },
    ]);
    expect(pngSize("icons/apple-touch-icon.png"), "the image iOS uses").toEqual([180, 180]);
  });

  it("precaches the offline page and the icons, and nothing that can go stale", () => {
    const worker = publicFile("sw.js");

    expect(worker, "the worker's own script URL").toContain(SERVICE_WORKER_PATH.slice(1));
    expect(worker).toContain("/offline.html");
    expect(worker).toContain("icon-192.png");
    expect(worker).toContain("icon-512.png");
    // The cache is versioned, so a release drops the previous shell on activate.
    expect(worker).toMatch(/SHELL_CACHE\s*=\s*`careeros-shell-\$\{SHELL_VERSION\}`/);
    expect(worker).toContain("caches.delete");

    // A navigation falls back to the offline page; the API is never answered from a cache.
    expect(worker).toContain('request.mode === "navigate"');
    expect(worker).toContain("OFFLINE_URL");
    expect(worker).toMatch(/startsWith\("\/api\/"\)/);
    // And only the build's content-hashed chunks are kept.
    expect(worker).toContain('startsWith("/_next/static/")');
  });

  it("wakes for a push without ever holding the account's token", () => {
    const worker = publicFile("sw.js");

    // The three events 33.4 promised: the wake, the click, and the browser rotating the
    // registration while no tab is open.
    expect(worker).toContain('addEventListener("push"');
    expect(worker).toContain("showNotification");
    expect(worker).toContain('addEventListener("notificationclick"');
    expect(worker).toContain("openWindow");
    expect(worker).toContain('addEventListener("pushsubscriptionchange"');
    expect(worker).toContain("postMessage");
    expect(worker).toContain(PUSH_RENEWED_MESSAGE);

    // The notification lands on the inbox and is one bubble rather than one per event.
    expect(worker).toContain(PUSH_DEEPLINK);
    expect(worker).toContain("careeros-inbox");

    // The sentence is in the worker because the app's table is not reachable there, and
    // both languages ship because the browser's own setting picks one.
    expect(worker, "the English sentence").toContain("Something new is waiting in your inbox.");
    expect(worker, "the Chinese sentence").toContain("收件箱里有新东西。");

    // The whole point of the design: a worker that keeps no token cannot leak one account's
    // inbox to another account's tab, and cannot revoke the token family the page is using.
    expect(worker).not.toContain("localStorage");
    expect(worker).not.toContain("accessToken");
    expect(worker).not.toContain("refreshToken");

    // Nor does it ask the API: the tab the click opens reads the authenticated inbox.
    const wake = worker.slice(
      worker.indexOf('addEventListener("push"'),
      worker.indexOf('addEventListener("notificationclick"')
    );
    expect(wake, "the wake handler must not fetch").not.toContain("fetch(");
  });

  it("carries an offline page that can be read with nothing else fetched", () => {
    const page = publicFile("offline.html");

    expect(page).toContain("data-offline-shell");
    expect(page).toContain("data-retry");
    // Every string is in the file: the app's table is not reachable before the network is.
    expect(page, "the English sentence").toContain("You're offline");
    expect(page, "the Chinese sentence").toContain("当前离线");
    // Nothing external: no stylesheet, no script, no font, no image URL.
    expect(page).not.toMatch(/<link[^>]+rel="stylesheet"/i);
    expect(page).not.toMatch(/<script[^>]+src=/i);
    expect(page).not.toMatch(/https?:\/\//i);
  });

  it("registers a worker only in a production build, and never fails the app", async () => {
    expect(shouldRegisterServiceWorker("production")).toBe(true);
    expect(shouldRegisterServiceWorker("development")).toBe(false);
    expect(shouldRegisterServiceWorker("test")).toBe(false);
    expect(shouldRegisterServiceWorker(undefined)).toBe(false);

    const calls: Array<{ url: string; scope?: string }> = [];
    const host: ServiceWorkerHost = {
      serviceWorker: {
        register: async (url, options) => {
          calls.push({ url, scope: options?.scope });
          return { scope: options?.scope };
        },
      },
    };
    await registerServiceWorker(host, "production");
    expect(calls).toEqual([{ url: SERVICE_WORKER_PATH, scope: "/" }]);

    // A browser that has no worker: nothing happens, and nothing throws.
    const bare = await registerServiceWorker({}, "production");
    expect(bare).toBeUndefined();
    // A refused install (private window, insecure origin): the app still opens.
    const refused = await registerServiceWorker(
      {
        serviceWorker: {
          register: async () => {
            throw new Error("SecurityError");
          },
        },
      },
      "production"
    );
    expect(refused).toBeUndefined();

    // The dev server is not given a worker at all.
    const devCalls: string[] = [];
    await registerServiceWorker(
      {
        serviceWorker: {
          register: async (url) => {
            devCalls.push(url);
          },
        },
      },
      "development"
    );
    expect(devCalls).toEqual([]);
  });
});
