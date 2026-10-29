/**
 * The second factor's arithmetic, kept out of the screen that shows it (roadmap 36.4).
 *
 * Three decisions are made before anything renders: how a base32 seed is grouped for a
 * human to type, how the ten recovery codes leave the screen in one paste, and what the
 * two code fields refuse locally. The server judges every code -- the screen only refuses
 * a form that cannot pass, so a typo is answered under the field rather than by a round
 * trip that spends a slot of the account's five-a-minute bucket.
 */

import type { TextIssue } from "@/lib/i18n/issue";

/**
 * The seed in groups of four, the spacing every authenticator app prints.
 *
 * The enrollment answer is base32 with no separators; a reader typing it by hand reads
 * four characters at a time, and unstripped whitespace from a paste would make the
 * groups drift. The copy target still carries the bare seed: a phone imports it, and a
 * group boundary is not part of the secret.
 */
export function spacedSecret(secret: string): string {
  return secret.replace(/\s+/g, "").replace(/(.{4})/g, "$1 ").trim();
}

/** The ten codes as one pasteable block, one per line, for "copy all". */
export function recoveryCodesText(codes: string[]): string {
  return codes.join("\n");
}

/**
 * What to show under the activation field, or `undefined` when it can be submitted.
 *
 * `MfaActivateRequest` carries `@Pattern("\\d{6}")`: activation proves the authenticator
 * was provisioned, and only the six digits a TOTP step produces do that. A printed
 * recovery code is deliberately not a way to turn the factor on -- printing the sheet is
 * what activation produces, so accepting one here would be circular.
 */
export function activateCodeIssue(value: string): TextIssue | undefined {
  const code = value.trim();
  if (!code) return { key: "security.issues.codeRequired" };
  return /^\d{6}$/.test(code) ? undefined : { key: "security.issues.codeSixDigits" };
}

/**
 * What to show under a proof field (reprint or turn off), or `undefined` when one is typed.
 *
 * `MfaProofRequest` accepts a six-digit code or a printed recovery code, and the
 * printed form's spelling is normalized on the server (case, hyphens, spaces). The
 * screen therefore checks presence only: a local shape guess would refuse a code the
 * server would have spent.
 */
export function proofCodeIssue(value: string): TextIssue | undefined {
  return value.trim() ? undefined : { key: "security.issues.codeRequired" };
}

/**
 * What to show under the password field of a proof, or `undefined` when something is typed.
 *
 * No minimum: a legacy account may hold a password shorter than today's register floor,
 * and the proof is the account's current password, not a new one. The ceiling is the
 * server's (`@NotBlank`); an empty field is the only refusal the screen can make.
 */
export function proofPasswordIssue(value: string): TextIssue | undefined {
  return value ? undefined : { key: "security.issues.passwordRequired" };
}
