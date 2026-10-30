/**
 * The address-move letter, as arithmetic rather than as a screen.
 *
 * 26.1 mails a link to `<app.web.base-url>/confirm-email?token=…`, and until 38.1 that
 * route did not exist: the product sent readers to a 404. The landing page's job is to
 * answer the link, and the two decisions worth testing are not the ones that render —
 * where the token comes from, and which refusal earns which sentence. They live here, out
 * of the component, the way the reset screen's do in `auth-recovery.ts`.
 */

import { ApiError } from "@/lib/api/client";

/**
 * The token the letter carries, read out of a location search string.
 *
 * The tokens are base64url (`TokenHasher.generateOpaqueToken`), so the alphabet has no `+`
 * and `URLSearchParams` has nothing to misread as a space. `null` means "this link cannot
 * work on its own" — the screen offers the paste field instead of pretending otherwise.
 */
export function emailChangeTokenFrom(search: string): string | null {
  const token = new URLSearchParams(search).get("token")?.trim();
  return token ? token : null;
}

/**
 * Which refusal the API sent, or `null` when it is not one of the two the page can
 * explain.
 *
 * `EMAIL_CHANGE_INVALID` is deliberately one answer for unknown, spent, expired and
 * ownerless links, so the route is no oracle for which links were real; the page repeats
 * that single answer rather than inventing a finer one. `EMAIL_ALREADY_REGISTERED` is the
 * other terminal case: the token was spent before the address was checked (26.2), so the
 * same link cannot succeed on a retry and the screen must not offer one. Everything else
 * — the network, a 401 from a stale tab, a validation 400 — is retryable or belongs to
 * the toast, and `null` sends it there.
 */
export function emailChangeOutcome(err: unknown): "invalid" | "registered" | null {
  if (!(err instanceof ApiError)) return null;
  if (err.code === "EMAIL_CHANGE_INVALID") return "invalid";
  if (err.code === "EMAIL_ALREADY_REGISTERED") return "registered";
  return null;
}

/**
 * Which field a refused address-move belongs under (38.2), or `null` when the server's
 * answer is not one the form can attribute.
 *
 * The API names the reason on the code, not on a field: a wrong password and an address
 * it will not take arrive as bare bodies. The form puts each sentence under the field
 * that caused it, because "that email address is already registered" above a password box
 * would send the reader to edit the wrong thing. The limiter's 429 belongs to no field at
 * all — asking again too soon is about the whole form — so it keeps the form-level line.
 * Anything else (the network, an unexpected refusal) is the caller's generic failure.
 */
export type AddressMoveField = "password" | "email" | "form";

export function addressMoveRefusal(err: unknown): AddressMoveField | null {
  if (!(err instanceof ApiError)) return null;
  if (err.code === "CURRENT_PASSWORD_INCORRECT") return "password";
  if (err.code === "EMAIL_UNCHANGED" || err.code === "EMAIL_ALREADY_REGISTERED") return "email";
  if (err.code === "RATE_LIMITED") return "form";
  return null;
}
