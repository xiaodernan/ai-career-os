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
 * write came from — the server's own wording when it has one, a plain sentence
 * when it does not.
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
 * The server's own wording is the fallback, for a code this build does not
 * know: a newer service, or one the table has not caught up with. The
 * services' codes are not in the table yet — their wording is more specific
 * than one sentence per code can be, and a generic sentence in place of
 * "Start the interview with an opening question first" would be a loss.
 */
export function describe(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    if (err.isNotFound) return missingEndpointMessage();
    const sentence = translate(`errorCodes.${err.code}`);
    if (sentence) return sentence;
    return err.message || fallback;
  }
  if (err instanceof TypeError) {
    return (
      translate("errorCodes.NETWORK_ERROR") ??
      "Cannot reach the API — is the backend running?"
    );
  }
  return err instanceof Error && err.message ? err.message : fallback;
}

/**
 * The failure handler for a mutation: it announces the error and hands the
 * error back, so a caller that rolls back an optimistic update still can.
 */
export function fail(fallback: string) {
  return (err: unknown) => toast.error(describe(err, fallback));
}
