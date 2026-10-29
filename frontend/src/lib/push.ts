/**
 * The browser's half of Web Push (roadmap 33.4).
 *
 * Three separate things meet here, and each one is a place the feature can lie:
 *
 * 1. **The key.** A subscription is made with the deployment's VAPID public key. The
 *    backend signs with the matching private half, so a browser subscribed with any
 *    other key is a browser no wake can reach. The value is inlined at build time
 *    (`NEXT_PUBLIC_VAPID_PUBLIC_KEY`); compose passes the backend's own
 *    `APP_PUSH_VAPID_PUBLIC_KEY` into that build arg, so the two halves cannot
 *    disagree in a deployment that filled one variable.
 * 2. **The registration.** `pushManager.subscribe` gives back an endpoint and two
 *    keys, and the account keeps that row (33.1). The subscription is not useful on
 *    its own -- a row the server never kept is a browser nothing rings -- so a failed
 *    registration has to undo the local subscribe, or the switch would show "on"
 *    while the server has no address to wake.
 * 3. **The renewal.** A push service may rotate a registration and fire
 *    `pushsubscriptionchange` while no tab is open. The worker re-subscribes with the
 *    old key and hands the new endpoint to any open client; this module decides what
 *    that message means, and ignores everything else the worker might say.
 *
 * Everything that can be decided without a browser is a pure function here, so the
 * rules are measured in `push.test.ts` rather than by opening a phone.
 */

/** Where a notification lands: the inbox the wake is about. */
export const PUSH_DEEPLINK = "/notifications";

/** The `message` a renewed worker registration carries to its open clients. */
export const PUSH_RENEWED_MESSAGE = "careeros:push-renewed";

/** What the backend keeps for one browser (`PushDtos.PushSubscriptionRequest`). */
export interface PushRecord {
  endpoint: string;
  p256dh: string;
  auth: string;
}

/** The slice of `PushSubscription` this module reads. */
export interface PushSubscriptionLike {
  endpoint: string;
  toJSON: () => { keys?: { p256dh?: string; auth?: string } | null } | null;
  unsubscribe?: () => Promise<boolean>;
}

/** The slice of `PushManager` this module reads. */
export interface PushManagerLike {
  getSubscription: () => Promise<PushSubscriptionLike | null>;
  subscribe: (options: {
    userVisibleOnly: boolean;
    /** `Uint8Array<ArrayBuffer>`, because that is what the DOM's `BufferSource` accepts. */
    applicationServerKey: Uint8Array<ArrayBuffer>;
  }) => Promise<PushSubscriptionLike>;
}

/** The slice of `ServiceWorkerRegistration` this module reads. */
export interface PushRegistrationLike {
  pushManager?: PushManagerLike;
}

/** The slice of `navigator` this module reads, so a test can hand over a stand-in. */
export interface PushHost {
  Notification?: {
    permission: string;
    requestPermission: () => Promise<string>;
  };
  serviceWorker?: {
    getRegistration: () => Promise<PushRegistrationLike | undefined>;
    addEventListener?: (type: "message", listener: (event: { data?: unknown }) => void) => void;
    removeEventListener?: (type: "message", listener: (event: { data?: unknown }) => void) => void;
  };
}

/** What this browser can do right now, as the switch reads it. */
export type PushState =
  /** No `Notification` or no `serviceWorker`: this browser cannot subscribe at all. */
  | { kind: "unsupported" }
  /** Push-capable, but the app's worker is not installed (a dev build, or a first visit). */
  | { kind: "no-worker" }
  /** The reader (or the browser) denied the permission; only the site settings can undo it. */
  | { kind: "blocked" }
  /** Permission is there but this browser holds no subscription. */
  | { kind: "off" }
  /** A subscription exists and is usable. */
  | { kind: "on"; subscription: PushSubscriptionLike };

export type EnableFailure =
  | "unsupported"
  | "no-worker"
  | "unconfigured"
  | "denied"
  | "failed";

export type EnableResult =
  | { ok: true; subscription: PushSubscriptionLike }
  | { ok: false; reason: EnableFailure };

/**
 * The deployment's public key, as the bundle was built with it.
 *
 * Empty is a real answer, not a missing one: a deployment that never generated a
 * VAPID pair has push off, and the settings switch says so instead of subscribing a
 * browser to a key nothing signs with.
 */
export function pushPublicKey(
  env: string | undefined = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY
): string {
  return (env ?? "").trim();
}

/** Whether this bundle carries a key to subscribe with. */
export function pushConfigured(
  env: string | undefined = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY
): boolean {
  return pushPublicKey(env).length > 0;
}

/**
 * A VAPID public key is unpadded base64url; `applicationServerKey` wants the bytes.
 *
 * Returns `null` rather than throwing for anything that is not base64url: a key with a
 * stray space or the wrong alphabet is a build problem, and the switch has a sentence
 * for it -- an exception at the moment the reader flips the switch is not one.
 */
export function urlBase64ToBytes(value: string): Uint8Array<ArrayBuffer> | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const base64 = trimmed.replace(/-/g, "+").replace(/_/g, "/");
  if (base64.length % 4 === 1) return null;
  if (!/^[A-Za-z0-9+/]+={0,2}$/.test(base64)) return null;
  const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
  try {
    const binary = atob(padded);
    return Uint8Array.from(binary, (char) => char.charCodeAt(0));
  } catch {
    return null;
  }
}

/**
 * The three fields the account stores, or `null` when the browser did not hand them
 * over. An empty key would be stored and only discovered by a failing send at 07:30,
 * so it is refused here, where the switch can still say "try again".
 */
export function pushRecord(subscription: PushSubscriptionLike): PushRecord | null {
  const json = subscription.toJSON?.() ?? null;
  const endpoint = subscription.endpoint || "";
  const p256dh = json?.keys?.p256dh ?? "";
  const auth = json?.keys?.auth ?? "";
  if (!endpoint || !p256dh || !auth) return null;
  return { endpoint, p256dh, auth };
}

/**
 * The real browser, read as a host.
 *
 * `Notification` is a global constructor, not a property of `navigator`, so the host
 * cannot simply be `navigator`; and a server render has neither. A host with no
 * `Notification` answers `unsupported`, which is the right sentence on a page that has
 * no browser to ask.
 */
export function browserPushHost(): PushHost {
  if (typeof navigator === "undefined" || typeof Notification === "undefined") return {};
  return { Notification, serviceWorker: navigator.serviceWorker };
}

/** What the browser can do now. Nothing here throws: a refused read is a state. */
export async function readPushState(host: PushHost = browserPushHost()): Promise<PushState> {
  if (!host.Notification || !host.serviceWorker) return { kind: "unsupported" };
  let registration: PushRegistrationLike | undefined;
  try {
    registration = await host.serviceWorker.getRegistration();
  } catch {
    return { kind: "no-worker" };
  }
  if (!registration?.pushManager) return { kind: "no-worker" };
  if (host.Notification.permission === "denied") return { kind: "blocked" };

  let subscription: PushSubscriptionLike | null = null;
  try {
    subscription = await registration.pushManager.getSubscription();
  } catch {
    return { kind: "off" };
  }
  if (subscription && host.Notification.permission === "granted") {
    return { kind: "on", subscription };
  }
  return { kind: "off" };
}

/**
 * Ask, subscribe, and answer the subscription -- or the reason it could not happen.
 *
 * The order is the browser's, not ours: the permission prompt must come from the
 * reader's own gesture (the switch's `onCheckedChange`), and the subscribe call must
 * come from a document that still has the gesture's activation. Doing the permission
 * check first also means a reader who says no is never shown a subscribe error.
 */
export async function enablePush(
  options: { host?: PushHost; key?: string } = {}
): Promise<EnableResult> {
  const host = options.host ?? browserPushHost();
  const key = (options.key ?? pushPublicKey()).trim();
  if (!host.Notification || !host.serviceWorker) return { ok: false, reason: "unsupported" };
  if (!key) return { ok: false, reason: "unconfigured" };

  let permission = host.Notification.permission;
  if (permission !== "granted") {
    try {
      permission = await host.Notification.requestPermission();
    } catch {
      return { ok: false, reason: "denied" };
    }
    if (permission !== "granted") return { ok: false, reason: "denied" };
  }

  let registration: PushRegistrationLike | undefined;
  try {
    registration = await host.serviceWorker.getRegistration();
  } catch {
    return { ok: false, reason: "no-worker" };
  }
  if (!registration?.pushManager) return { ok: false, reason: "no-worker" };

  try {
    const existing = await registration.pushManager.getSubscription();
    if (existing) return { ok: true, subscription: existing };
  } catch {
    /* a read that failed is not a subscription; the subscribe below is the answer */
  }

  const applicationServerKey = urlBase64ToBytes(key);
  if (!applicationServerKey) return { ok: false, reason: "unconfigured" };
  try {
    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey,
    });
    return { ok: true, subscription };
  } catch {
    return { ok: false, reason: "failed" };
  }
}

/**
 * Forget this browser locally.
 *
 * The endpoint comes back so the caller can delete the account's row: a server that
 * still holds it will ring a browser that has already unsubscribed, and the push
 * service's `410` is a worse way to learn the reader meant it. A browser with nothing
 * to forget answers `{ok: true, endpoint: null}` -- opting out twice is not a failure.
 */
export async function disablePush(
  host: PushHost = browserPushHost()
): Promise<{ ok: boolean; endpoint: string | null }> {
  if (!host.serviceWorker) return { ok: false, endpoint: null };
  let registration: PushRegistrationLike | undefined;
  try {
    registration = await host.serviceWorker.getRegistration();
  } catch {
    return { ok: false, endpoint: null };
  }
  if (!registration?.pushManager) return { ok: true, endpoint: null };
  let subscription: PushSubscriptionLike | null;
  try {
    subscription = await registration.pushManager.getSubscription();
  } catch {
    return { ok: false, endpoint: null };
  }
  if (!subscription) return { ok: true, endpoint: null };
  try {
    if (subscription.unsubscribe) await subscription.unsubscribe();
    return { ok: true, endpoint: subscription.endpoint };
  } catch {
    return { ok: false, endpoint: null };
  }
}

/**
 * The registration a worker's renewal message carries, or `null` for any other message.
 *
 * The worker posts on the same channel anything else it might need to say later, so
 * the type is checked before the shape: a client that registered every message would
 * hand the backend a body without an endpoint.
 */
export function renewalRecord(data: unknown): PushRecord | null {
  if (!data || typeof data !== "object") return null;
  const message = data as { type?: unknown; subscription?: unknown };
  if (message.type !== PUSH_RENEWED_MESSAGE) return null;
  const subscription = message.subscription;
  if (!subscription || typeof subscription !== "object") return null;
  const payload = subscription as {
    endpoint?: unknown;
    keys?: { p256dh?: unknown; auth?: unknown } | null;
  };
  if (typeof payload.endpoint !== "string" || !payload.endpoint) return null;
  const p256dh = payload.keys?.p256dh;
  const auth = payload.keys?.auth;
  if (typeof p256dh !== "string" || !p256dh) return null;
  if (typeof auth !== "string" || !auth) return null;
  return { endpoint: payload.endpoint, p256dh, auth };
}

/**
 * Listen for a renewal, and answer with the record to re-register.
 *
 * Returns the unsubscriber, so the layout's effect can clean up. A host with no
 * worker (a dev build, or a browser that refused the install) simply never calls.
 */
export function onPushRenewal(
  handler: (record: PushRecord) => void,
  host: PushHost = browserPushHost()
): () => void {
  const container = host.serviceWorker;
  if (!container?.addEventListener) return () => undefined;
  const listener = (event: { data?: unknown }) => {
    const record = renewalRecord(event.data);
    if (record) handler(record);
  };
  container.addEventListener("message", listener);
  return () => container.removeEventListener?.("message", listener);
}
