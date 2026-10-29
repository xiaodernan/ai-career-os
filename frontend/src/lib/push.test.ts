import { describe, expect, it, vi } from "vitest";

import {
  browserPushHost,
  disablePush,
  enablePush,
  onPushRenewal,
  PUSH_DEEPLINK,
  PUSH_RENEWED_MESSAGE,
  pushConfigured,
  pushPublicKey,
  pushRecord,
  readPushState,
  renewalRecord,
  urlBase64ToBytes,
  type PushHost,
  type PushSubscriptionLike,
} from "./push";

/**
 * The browser's half of Web Push (33.4).
 *
 * Every rule here is one a phone would otherwise have to be borrowed to check: the key's
 * alphabet, whether a switch may say "on", what a refused permission reads as, and which
 * worker messages are a renewal. The browser is a stand-in throughout -- `push.ts` reads
 * only the slices its interfaces name -- so no test needs a real `Notification`.
 */

/** One subscription with keys, as `pushManager.subscribe` hands it over. */
function makeSubscription(
  endpoint = "https://push.example/abc",
  keys: { p256dh?: string; auth?: string } | null = { p256dh: "p256", auth: "auth" }
): PushSubscriptionLike {
  return {
    endpoint,
    toJSON: () => (keys ? { keys } : null),
  };
}

/** A host whose `getRegistration` answers `registration`, or throws when given an Error. */
function makeHost(options: {
  permission?: string;
  requestPermission?: () => Promise<string>;
  registration?: unknown;
  registrationThrows?: boolean;
  addEventListener?: (type: "message", listener: (event: { data?: unknown }) => void) => void;
  removeEventListener?: (type: "message", listener: (event: { data?: unknown }) => void) => void;
}): PushHost {
  return {
    Notification: {
      permission: options.permission ?? "granted",
      requestPermission: options.requestPermission ?? (async () => "granted"),
    },
    serviceWorker: {
      getRegistration: async () => {
        if (options.registrationThrows) throw new Error("SecurityError");
        return options.registration as never;
      },
      addEventListener: options.addEventListener,
      removeEventListener: options.removeEventListener,
    },
  };
}

/** A registration holding a push manager, with the subscription it answers. */
function makeRegistration(options: {
  subscription?: PushSubscriptionLike | null;
  getSubscription?: () => Promise<PushSubscriptionLike | null>;
  subscribe?: (init: {
    userVisibleOnly: boolean;
    applicationServerKey: Uint8Array;
  }) => Promise<PushSubscriptionLike>;
}) {
  return {
    pushManager: {
      getSubscription: options.getSubscription ?? (async () => options.subscription ?? null),
      subscribe:
        options.subscribe ??
        (async () => {
          throw new Error("subscribe was not expected");
        }),
    },
  };
}

describe("the deployment's key", () => {
  it("reads the build-time value, trimmed, and an empty string is 'off'", () => {
    expect(pushPublicKey("  BEl6abc  ")).toBe("BEl6abc");
    expect(pushPublicKey("")).toBe("");
    expect(pushPublicKey(undefined)).toBe("");

    expect(pushConfigured("BEl6abc")).toBe(true);
    expect(pushConfigured("   ")).toBe(false);
    expect(pushConfigured(undefined)).toBe(false);
  });

  it("decodes unpadded base64url and refuses anything else instead of throwing", () => {
    // "AQID" is the canonical three-byte vector; the URL alphabet's - and _ stand for + and /.
    expect(Array.from(urlBase64ToBytes("AQID") ?? [])).toEqual([1, 2, 3]);
    expect(Array.from(urlBase64ToBytes("-_8") ?? [])).toEqual([251, 255]);
    expect(Array.from(urlBase64ToBytes(" AQID \n") ?? [])).toEqual([1, 2, 3]);

    expect(urlBase64ToBytes("")).toBeNull();
    expect(urlBase64ToBytes("   ")).toBeNull();
    // A length of 4n+1 cannot be a whole number of bytes, and a key with a space or a
    // foreign character is a build mistake rather than a subscription to attempt.
    expect(urlBase64ToBytes("A")).toBeNull();
    expect(urlBase64ToBytes("AB=C")).toBeNull();
    expect(urlBase64ToBytes("AQ ID")).toBeNull();
    expect(urlBase64ToBytes("AQID!")).toBeNull();
  });
});

describe("the record the account keeps", () => {
  it("is endpoint plus both keys", () => {
    expect(pushRecord(makeSubscription())).toEqual({
      endpoint: "https://push.example/abc",
      p256dh: "p256",
      auth: "auth",
    });
  });

  it("is null when any of the three is missing -- an empty key only fails at 07:30", () => {
    expect(pushRecord(makeSubscription("", { p256dh: "p", auth: "a" }))).toBeNull();
    expect(pushRecord(makeSubscription("https://push.example/abc", { p256dh: "", auth: "a" }))).toBeNull();
    expect(pushRecord(makeSubscription("https://push.example/abc", { p256dh: "p", auth: "" }))).toBeNull();
    expect(pushRecord(makeSubscription("https://push.example/abc", null))).toBeNull();
  });
});

describe("what the switch reads", () => {
  it("says unsupported where there is no Notification or no worker container", async () => {
    expect(await readPushState({})).toEqual({ kind: "unsupported" });
    expect(
      await readPushState({
        Notification: { permission: "default", requestPermission: async () => "default" },
      })
    ).toEqual({ kind: "unsupported" });
    expect(
      await readPushState({ serviceWorker: { getRegistration: async () => undefined } })
    ).toEqual({ kind: "unsupported" });
  });

  it("says no-worker when the registration is missing, empty or unreadable", async () => {
    const host = makeHost({ registration: undefined });
    expect(await readPushState(host)).toEqual({ kind: "no-worker" });
    expect(await readPushState(makeHost({ registration: {} }))).toEqual({ kind: "no-worker" });
    expect(await readPushState(makeHost({ registrationThrows: true }))).toEqual({ kind: "no-worker" });
  });

  it("says blocked on a denied permission, before it asks for a subscription", async () => {
    const getSubscription = vi.fn(async () => makeSubscription());
    const host = makeHost({
      permission: "denied",
      registration: makeRegistration({ getSubscription }),
    });
    expect(await readPushState(host)).toEqual({ kind: "blocked" });
    expect(getSubscription, "a blocked browser has no subscription worth reading").not.toHaveBeenCalled();
  });

  it("says on only with permission *and* a subscription", async () => {
    const subscription = makeSubscription();
    expect(
      await readPushState(makeHost({ registration: makeRegistration({ subscription }) }))
    ).toEqual({ kind: "on", subscription });

    // Permission granted but nothing held: the switch is off and can be flipped on.
    expect(
      await readPushState(makeHost({ registration: makeRegistration({ subscription: null }) }))
    ).toEqual({ kind: "off" });

    // A subscription with permission still pending is not one this app may use.
    expect(
      await readPushState(
        makeHost({ permission: "default", registration: makeRegistration({ subscription }) })
      )
    ).toEqual({ kind: "off" });
  });

  it("reads a failed subscription query as off rather than throwing", async () => {
    const host = makeHost({
      registration: makeRegistration({
        getSubscription: async () => {
          throw new Error("InvalidStateError");
        },
      }),
    });
    expect(await readPushState(host)).toEqual({ kind: "off" });
  });
});

describe("turning the wake on", () => {
  it("refuses without a browser: unsupported", async () => {
    expect(await enablePush({ host: {}, key: "AQID" })).toEqual({
      ok: false,
      reason: "unsupported",
    });
  });

  it("refuses before asking permission when the build carries no key", async () => {
    const requestPermission = vi.fn(async () => "granted");
    const result = await enablePush({
      host: makeHost({ requestPermission }),
      key: "   ",
    });
    expect(result).toEqual({ ok: false, reason: "unconfigured" });
    expect(requestPermission, "a prompt with no key behind it is a question with no answer").not.toHaveBeenCalled();
  });

  it("asks permission first, and a no is a denial rather than a subscribe error", async () => {
    const subscribe = vi.fn(async () => makeSubscription());
    const host = makeHost({
      permission: "default",
      requestPermission: async () => "denied",
      registration: makeRegistration({ subscribe }),
    });
    expect(await enablePush({ host, key: "AQID" })).toEqual({ ok: false, reason: "denied" });
    expect(subscribe).not.toHaveBeenCalled();

    const thrown = makeHost({
      permission: "default",
      requestPermission: async () => {
        throw new Error("NotAllowedError");
      },
      registration: makeRegistration({ subscribe }),
    });
    expect(await enablePush({ host: thrown, key: "AQID" })).toEqual({
      ok: false,
      reason: "denied",
    });
    expect(subscribe).not.toHaveBeenCalled();
  });

  it("does not prompt again when permission is already granted", async () => {
    const requestPermission = vi.fn(async () => "granted");
    const host = makeHost({
      permission: "granted",
      requestPermission,
      registration: makeRegistration({ subscription: makeSubscription() }),
    });
    expect(await enablePush({ host, key: "AQID" })).toMatchObject({ ok: true });
    expect(requestPermission).not.toHaveBeenCalled();
  });

  it("answers no-worker when the app's worker is not installed", async () => {
    expect(await enablePush({ host: makeHost({ registration: undefined }), key: "AQID" })).toEqual({
      ok: false,
      reason: "no-worker",
    });
    expect(await enablePush({ host: makeHost({ registrationThrows: true }), key: "AQID" })).toEqual({
      ok: false,
      reason: "no-worker",
    });
  });

  it("keeps an existing subscription instead of subscribing twice", async () => {
    const subscription = makeSubscription();
    const subscribe = vi.fn(async () => makeSubscription("https://push.example/other"));
    const host = makeHost({ registration: makeRegistration({ subscription, subscribe }) });
    expect(await enablePush({ host, key: "AQID" })).toEqual({ ok: true, subscription });
    expect(subscribe).not.toHaveBeenCalled();
  });

  it("subscribes with the bytes of the key, visible-only, and answers the subscription", async () => {
    const created = makeSubscription();
    const calls: Array<{ userVisibleOnly: boolean; applicationServerKey: Uint8Array }> = [];
    const host = makeHost({
      registration: makeRegistration({
        subscribe: async (init) => {
          calls.push(init);
          return created;
        },
      }),
    });
    expect(await enablePush({ host, key: "AQID" })).toEqual({ ok: true, subscription: created });
    expect(calls).toHaveLength(1);
    expect(calls[0].userVisibleOnly, "a push with nothing shown violates the browser's contract").toBe(true);
    expect(Array.from(calls[0].applicationServerKey)).toEqual([1, 2, 3]);
  });

  it("reads through a failed subscription query and still subscribes", async () => {
    const created = makeSubscription();
    const host = makeHost({
      registration: makeRegistration({
        getSubscription: async () => {
          throw new Error("InvalidStateError");
        },
        subscribe: async () => created,
      }),
    });
    expect(await enablePush({ host, key: "AQID" })).toEqual({ ok: true, subscription: created });
  });

  it("reads a refused subscribe and an undecodable key as sentences, not exceptions", async () => {
    const refused = makeHost({
      registration: makeRegistration({
        subscribe: async () => {
          throw new Error("AbortError");
        },
      }),
    });
    expect(await enablePush({ host: refused, key: "AQID" })).toEqual({
      ok: false,
      reason: "failed",
    });

    const brokenKey = makeHost({ registration: makeRegistration({}) });
    expect(await enablePush({ host: brokenKey, key: "not a key!" })).toEqual({
      ok: false,
      reason: "unconfigured",
    });
  });
});

describe("turning the wake off", () => {
  it("forgets the browser's own subscription and names the endpoint", async () => {
    const unsubscribe = vi.fn(async () => true);
    const subscription = { ...makeSubscription(), unsubscribe };
    const host = makeHost({ registration: makeRegistration({ subscription }) });
    expect(await disablePush(host)).toEqual({ ok: true, endpoint: subscription.endpoint });
    expect(unsubscribe).toHaveBeenCalledTimes(1);
  });

  it("opting out twice is not a failure, and a browser with no subscription has nothing to name", async () => {
    expect(await disablePush(makeHost({ registration: makeRegistration({ subscription: null }) }))).toEqual({
      ok: true,
      endpoint: null,
    });
    expect(await disablePush(makeHost({ registration: {} }))).toEqual({ ok: true, endpoint: null });
  });

  it("a browser without a worker cannot unsubscribe, but does not throw", async () => {
    expect(await disablePush({})).toEqual({ ok: false, endpoint: null });
    expect(await disablePush(makeHost({ registrationThrows: true }))).toEqual({
      ok: false,
      endpoint: null,
    });
  });

  it("a failed unsubscribe is reported, because the browser may still ring", async () => {
    const subscription = {
      ...makeSubscription(),
      unsubscribe: async () => {
        throw new Error("InvalidStateError");
      },
    };
    expect(
      await disablePush(makeHost({ registration: makeRegistration({ subscription }) }))
    ).toEqual({ ok: false, endpoint: null });
  });
});

describe("a renewal from the worker", () => {
  it("is recognised only by its own type and a whole record", () => {
    expect(PUSH_DEEPLINK).toBe("/notifications");
    expect(PUSH_RENEWED_MESSAGE).toBe("careeros:push-renewed");

    expect(
      renewalRecord({
        type: PUSH_RENEWED_MESSAGE,
        subscription: { endpoint: "https://push.example/new", keys: { p256dh: "p", auth: "a" } },
      })
    ).toEqual({ endpoint: "https://push.example/new", p256dh: "p", auth: "a" });
  });

  it("refuses another message type, a missing shape, and empty fields", () => {
    const good = { endpoint: "https://push.example/new", keys: { p256dh: "p", auth: "a" } };
    expect(renewalRecord({ type: "careeros:something-else", subscription: good })).toBeNull();
    expect(renewalRecord({ subscription: good })).toBeNull();
    expect(renewalRecord({ type: PUSH_RENEWED_MESSAGE })).toBeNull();
    expect(renewalRecord({ type: PUSH_RENEWED_MESSAGE, subscription: "https://push.example" })).toBeNull();
    expect(
      renewalRecord({ type: PUSH_RENEWED_MESSAGE, subscription: { endpoint: "", keys: { p256dh: "p", auth: "a" } } })
    ).toBeNull();
    expect(
      renewalRecord({ type: PUSH_RENEWED_MESSAGE, subscription: { endpoint: "https://push.example/new", keys: { p256dh: "p" } } })
    ).toBeNull();
    expect(renewalRecord(null)).toBeNull();
    expect(renewalRecord("careeros:push-renewed")).toBeNull();
  });

  it("reaches the handler through the worker's message channel, and only with a record", () => {
    const listeners: Array<(event: { data?: unknown }) => void> = [];
    const removed: Array<(event: { data?: unknown }) => void> = [];
    const host = makeHost({
      addEventListener: (type, listener) => {
        expect(type).toBe("message");
        listeners.push(listener);
      },
      removeEventListener: (type, listener) => {
        expect(type).toBe("message");
        removed.push(listener);
      },
    });

    const seen: Array<{ endpoint: string }> = [];
    const off = onPushRenewal((record) => seen.push(record), host);
    expect(listeners).toHaveLength(1);

    listeners[0]({ data: { type: "careeros:other" } });
    listeners[0]({ data: { type: PUSH_RENEWED_MESSAGE, subscription: { endpoint: "" } } });
    expect(seen, "a foreign message must not reach the API").toEqual([]);

    listeners[0]({
      data: {
        type: PUSH_RENEWED_MESSAGE,
        subscription: { endpoint: "https://push.example/new", keys: { p256dh: "p", auth: "a" } },
      },
    });
    expect(seen).toEqual([{ endpoint: "https://push.example/new", p256dh: "p", auth: "a" }]);

    off();
    expect(removed).toEqual([listeners[0]]);
  });

  it("is a no-op where there is no worker to listen to", () => {
    const off = onPushRenewal(() => {
      throw new Error("nothing should arrive");
    }, {});
    expect(off, "the effect still gets a clean-up function").toBeTypeOf("function");
    expect(() => off()).not.toThrow();
  });
});

describe("the real browser as a host", () => {
  it("has nothing to offer outside a browser", () => {
    // Vitest's node environment: no `navigator`, no `Notification`.
    expect(browserPushHost()).toEqual({});
  });
});
