"use client";

import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { missingEndpointMessage } from "@/lib/api/missing-endpoint";
import { translate } from "@/lib/i18n/locale-context";

/**
 * The one place a write's failure becomes a sentence the user reads.
 *
 * A mutation that fails silently is the worst kind of failure: the button
 * stops working and the user has no idea why. Every mutation hook announces
 * its failure through {@link fail}, so the message is the same wherever the
 * write came from — the server's own wording when it has one, a plain
 * sentence when it does not.
 *
 * It lives in its own module so a hook that only needs the handler does not
 * pull the whole write surface in with it, and so the one implementation is
 * somewhere every hook can name.
 */

/**
 * The sentence for an error, in the reader's language.
 *
 * The *code* is the contract — the enum's own comment says "never rename an
 * emitted code" — and it is the only part of an error that does not change
 * with the wording. So the sentence comes from the code, out of the locale
 * table, and the reader sees it in the language they chose.
 *
 * The code is also the only part that says *which* thing is missing: the
 * backend answers a 404 for a route that is not served and for a record
 * that is gone, and only the first is a version mismatch. So the table's
 * sentence comes first, and the version sentence is the fallback for a 404
 * this build has no sentence for.
 *
 * The server's own wording is the last fallback, for a code this build does
 * not know: a newer service, or one the table has not caught up with.
 *
 * The fallback the caller passes is a translation *key*, not a sentence. A
 * write that breaks with nothing of its own to say still has to speak the
 * reader's language, and an English literal here would be one sentence that
 * never changes language. The key is resolved at the moment the toast is
 * raised — that is the moment that knows the reader's choice, not the
 * render that started the write.
 */
export function describe(err: unknown, fallbackKey?: string): string {
  const fallback = fallbackKey ? translate(fallbackKey) ?? fallbackKey : "";
  if (err instanceof ApiError) {
    const sentence = translate(`errorCodes.${err.code}`);
    if (sentence) return sentence;
    if (err.isNotFound) return missingEndpointMessage();
    return err.message || fallback;
  }
  if (err instanceof TypeError) {
    return translate("errorCodes.NETWORK_ERROR") ?? "errorCodes.NETWORK_ERROR";
  }
  return err instanceof Error && err.message ? err.message : fallback;
}

/**
 * The failure handler for a mutation: it announces the error and hands the
 * error back, so a caller that rolls back an optimistic update still can.
 *
 * The key names the sentence for a failure that has none of its own; see
 * {@link describe} for which sentence wins.
 */
export function fail(fallbackKey: string) {
  return (err: unknown) => toast.error(describe(err, fallbackKey));
}
