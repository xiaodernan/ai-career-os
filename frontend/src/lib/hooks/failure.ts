"use client";

import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { missingEndpointMessage } from "@/lib/api/missing-endpoint";

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

/** The server's message when it has one, and a plain sentence when it does not. */
export function describe(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    if (err.isNotFound) return missingEndpointMessage();
    return err.message || fallback;
  }
  if (err instanceof TypeError) return "Cannot reach the API — is the backend running?";
  return err instanceof Error && err.message ? err.message : fallback;
}

/**
 * The failure handler for a mutation: it announces the error and hands the
 * error back, so a caller that rolls back an optimistic update still can.
 */
export function fail(fallback: string) {
  return (err: unknown) => toast.error(describe(err, fallback));
}
