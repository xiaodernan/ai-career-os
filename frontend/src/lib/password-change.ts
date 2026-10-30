import { ApiError } from "@/lib/api/client";
import { PASSWORD_MAX_LENGTH } from "@/lib/auth-recovery";
import type { TextIssue } from "@/lib/i18n/issue";

/**
 * The password card's arithmetic, held apart from the screen (38.4).
 *
 * The backend's `PasswordChangeRequest` bounds the current password with
 * `@NotBlank @Size(max = 72)` and the new one with `(min = 8, max = 72)`; the new
 * password's bounds are already `passwordIssue`'s, so only the current field needs its
 * own mirror. A server refusal then has to land under the input that caused it:
 * `CURRENT_PASSWORD_INCORRECT` is the current field's, `PASSWORD_UNCHANGED` is the new
 * field's, and everything else (the limiter included) belongs to no single input.
 */

/** What to show under the current-password field. The record sets no minimum there. */
export function currentPasswordIssue(value: string): TextIssue | undefined {
  if (!value) return { key: "auth.issues.passwordRequired" };
  if (value.length > PASSWORD_MAX_LENGTH) {
    return { key: "auth.issues.tooLong", params: { max: PASSWORD_MAX_LENGTH } };
  }
  return undefined;
}

/**
 * Which field a refused change belongs to, or null when the failure belongs to the form.
 * `PASSWORD_UNCHANGED` is a refusal rather than an error: storing the same hash again
 * would sign every other device out for nothing, so the server declines before it writes.
 */
export function passwordChangeRefusal(err: unknown): "current" | "new" | null {
  if (!(err instanceof ApiError)) return null;
  if (err.code === "CURRENT_PASSWORD_INCORRECT") return "current";
  if (err.code === "PASSWORD_UNCHANGED") return "new";
  return null;
}
