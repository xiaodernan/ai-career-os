/**
 * The erasure card's one non-markup decision.
 *
 * 24.2's route re-authenticates twice: the password, then the account's own address typed
 * back. Each refusal has its own code, and the card puts each sentence under the field
 * that caused it — "that address is not this account's" above a password box would send
 * the reader to edit the wrong thing. Everything else (the limiter, the network, an
 * unexpected body) belongs to the form's shared describer.
 */

import { ApiError } from "@/lib/api/client";

export type EraseRefusalField = "password" | "email";

export function eraseRefusal(err: unknown): EraseRefusalField | null {
  if (!(err instanceof ApiError)) return null;
  if (err.code === "CURRENT_PASSWORD_INCORRECT") return "password";
  if (err.code === "CONFIRMATION_MISMATCH") return "email";
  return null;
}
