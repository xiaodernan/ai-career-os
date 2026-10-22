/**
 * Auth-screen validation, as arithmetic rather than as screens.
 *
 * The forgot/reset pair spent a while documented-but-unreachable: the API served it, the ops
 * runbook used it by hand, and no screen ever called it. The parts worth testing are not the
 * ones that render — they are the ones that decide whether a submit is allowed, where the
 * token comes from, and what a failure says — so they live here, out of the components.
 * Every length ceiling below mirrors the bound its record carries (the auth-controller
 * contract gate pins both ends), and the email rule is shared with the sign-in form rather
 * than written twice.
 */

import { ApiError } from "@/lib/api/client";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** Mirrors `@Size(max = 255)` on the three records that carry a user-typed email. */
export const EMAIL_MAX_LENGTH = 255;

/** What to show under an email field, or `undefined` when it looks like an address. */
export function emailIssue(value: string): string | undefined {
  if (!value) return "Email is required";
  if (value.length > EMAIL_MAX_LENGTH) {
    return `Use at most ${EMAIL_MAX_LENGTH} characters`;
  }
  return EMAIL_RE.test(value) ? undefined : "Enter a valid email address";
}

/**
 * What to show under the password field, or `undefined` when the value is acceptable.
 *
 * Mirrors the bounds the three auth records carry: `(min = 8, max = 72)` on
 * `RegisterRequest`/`ResetPasswordRequest`, and `max = 72` on `LoginRequest`; the sign-in
 * screen keeps the register minimum as its own floor. The upper bound is not decoration:
 * BCrypt reads at most 72 bytes, so the backend rejects anything longer instead of
 * silently truncating it; a screen that only checked the minimum would turn a pasted
 * passphrase into a 400 with no explanation the user could act on.
 */
export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_LENGTH = 72;

/**
 * What to show under the reset-token field, or `undefined` when it holds something usable.
 *
 * The token has no local shape to check -- the API decides whether it is real, and folding a
 * guess about the alphabet into the screen would reject a token the server would have spent.
 * The screen refuses only emptiness and the record's own ceiling (`@Size(max = 512)`); the
 * mailed tokens are 43 chars (32 random bytes, base64url), so the ceiling only catches a
 * paste that swallowed the whole mail. Length is judged as typed; the screen trims before
 * sending.
 */
export const RESET_TOKEN_MAX_LENGTH = 512;

export function tokenIssue(value: string): string | undefined {
  if (!value.trim()) return "Paste the token from your email";
  if (value.length > RESET_TOKEN_MAX_LENGTH) {
    return `Use at most ${RESET_TOKEN_MAX_LENGTH} characters`;
  }
  return undefined;
}

/** What to show under the password field, or `undefined` when the value is acceptable. */
export function passwordIssue(value: string): string | undefined {
  if (!value) return "Password is required";
  if (value.length < PASSWORD_MIN_LENGTH) {
    return `Use at least ${PASSWORD_MIN_LENGTH} characters`;
  }
  if (value.length > PASSWORD_MAX_LENGTH) {
    return `Use at most ${PASSWORD_MAX_LENGTH} characters`;
  }
  return undefined;
}

/**
 * Mirrors `@NotBlank @Size(max = 120)` on `RegisterRequest.displayName`. A longer paste
 * would otherwise come back as the generic validation 400 with no field named (#201).
 */
export const DISPLAY_NAME_MAX_LENGTH = 120;

/** What to show under the register screen's name field, or `undefined` when acceptable. */
export function displayNameIssue(value: string): string | undefined {
  if (!value.trim()) return "Name is required";
  if (value.length > DISPLAY_NAME_MAX_LENGTH) {
    return `Use at most ${DISPLAY_NAME_MAX_LENGTH} characters`;
  }
  return undefined;
}

/** What to show under the confirmation field, or `undefined` when the two agree. */
export function confirmationIssue(value: string, password: string): string | undefined {
  if (!value) return "Confirm your new password";
  return value === password ? undefined : "Passwords do not match";
}

/**
 * The token the reset mail carries, read out of a location search string.
 *
 * `null` means "this link cannot work", and the screen says so before the user picks a
 * password for a form that could only fail. The tokens are base64url
 * (`TokenHasher.generateOpaqueToken`: `Base64.getUrlEncoder().withoutPadding()`), so the
 * alphabet contains no `+` and `URLSearchParams` has nothing to misread as a space.
 */
export function resetTokenFrom(search: string): string | null {
  const token = new URLSearchParams(search).get("token")?.trim();
  return token ? token : null;
}

/**
 * One sentence for a failed recovery call.
 *
 * `RESET_TOKEN_INVALID` is the interesting case: the API answers it for a token that is
 * unknown, already spent, or past its 30 minutes, and its own message ("Invalid reset token")
 * tells the user nothing about what to do next — which is to ask for another one.
 */
export function recoveryErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.code === "RESET_TOKEN_INVALID") {
      return "That reset link is invalid or has expired. Request a new one.";
    }
    return err.message;
  }
  if (err instanceof TypeError) return UNREACHABLE_MESSAGE;
  return "Something went wrong. Please try again.";
}

/** The one spelling of the network-failure sentence, shared by every describer. */
export const UNREACHABLE_MESSAGE = "Cannot reach the API — is the backend running?";

/**
 * The sign-in/sign-up form's sentence for a failed call.
 *
 * A 401 is the one API answer whose own message helps nobody: the form cannot say
 * which of the two fields was wrong without telling an attacker which one was
 * right, so the API's "Invalid credentials" and the form's "Incorrect email or
 * password" are the same claim at different volumes — one friendly, one a leak.
 * Everything else (validation messages, the network, the unknown) is the recovery
 * describer's answer, composed rather than re-spelled.
 */
export function authFormErrorMessage(err: unknown): string {
  if (err instanceof ApiError
      && (err.code === "INVALID_CREDENTIALS" || err.status === 401)) {
    return "Incorrect email or password.";
  }
  return recoveryErrorMessage(err);
}
