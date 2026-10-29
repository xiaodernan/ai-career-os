"use client";

import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { pushRecord, type PushRecord, type PushSubscriptionLike } from "@/lib/push";
import type { PushSubscriptionRow } from "@/lib/api/types";

/**
 * The account's side of a browser registration (33.1 registered the routes; 33.4 is
 * their first caller).
 *
 * Keeping the row and holding the subscription are two halves of one promise, and
 * they fail separately. `savePushSubscription` posts what the browser handed over;
 * `forgetPushSubscription` reads the account's registrations and deletes the row whose
 * endpoint is this browser's -- never the whole list, because another browser's row is
 * another browser's consent. `ensurePushRegistration` is the repair path: a renewal
 * that happened while no tab was open, or a database that was reset under an installed
 * app, leaves a subscription the server does not know, and the reader would never learn
 * why the bell stopped.
 */

/** The body is written key by key, so the parity gate can read every name it sends. */
export async function savePushSubscription(
  subscription: PushSubscriptionLike
): Promise<PushSubscriptionRow> {
  const record = pushRecord(subscription);
  if (!record) {
    throw new Error("this browser returned no push keys");
  }
  return api.create<PushSubscriptionRow>(endpoints.pushSubscriptions, {
    endpoint: record.endpoint,
    p256dh: record.p256dh,
    auth: record.auth,
  });
}

/** The account's registrations, newest first. */
export function fetchPushSubscriptions(): Promise<PushSubscriptionRow[]> {
  return api.get<PushSubscriptionRow[]>(endpoints.pushSubscriptions);
}

/**
 * Forget this endpoint's row, if the account still has one.
 *
 * Answers whether a row was deleted. A row that is already gone is not a failure: the
 * registration may have been retired by a `410` between the reader's click and this
 * read, and the browser is unsubscribed either way.
 */
export async function forgetPushSubscription(endpoint: string): Promise<boolean> {
  const rows = await fetchPushSubscriptions();
  const row = rows.find((entry) => entry.endpoint === endpoint);
  if (!row) return false;
  await api.remove(endpoints.pushSubscription(row.id));
  return true;
}

/**
 * Make sure the server knows the subscription this browser already holds.
 *
 * Reads first and writes only when the endpoint is missing, so a visit that has
 * nothing to repair costs one GET and no write.
 */
export async function ensurePushRegistration(
  subscription: PushSubscriptionLike
): Promise<"kept" | "added"> {
  const rows = await fetchPushSubscriptions();
  if (rows.some((entry) => entry.endpoint === subscription.endpoint)) return "kept";
  await savePushSubscription(subscription);
  return "added";
}

/** The switch's registration write, with the pending state the card disables on. */
export function useRegisterPushSubscription() {
  return useMutation({ mutationFn: savePushSubscription });
}

/** A renewal heard from the worker, posted as the upsert the endpoint already is. */
export async function renewPushSubscription(record: PushRecord): Promise<PushSubscriptionRow> {
  return api.create<PushSubscriptionRow>(endpoints.pushSubscriptions, {
    endpoint: record.endpoint,
    p256dh: record.p256dh,
    auth: record.auth,
  });
}
