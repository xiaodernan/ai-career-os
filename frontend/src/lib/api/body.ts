/**
 * Request-body assembly for AI Career OS. Reading the wire is normalize.ts's job; this file is
 * the writing half, so the one rule that a caller must not break lives where a caller looks.
 *
 * A Spring request record accepts a field under its own name or under any `@JsonAlias`, but not
 * under both at once: both spellings resolve to the same constructor property, a record has no
 * setter to absorb the second value, and Jackson then aborts binding the entire body. Before this
 * helper the client posted `resumeVersionId` *and* `resume_version_id` on five AI actions, so
 * match / tailor / suggestions / set-current / save-draft failed on the request itself.
 */

/** `{ key: value }`, or nothing at all when the caller has no value for that field. */
export function field<T>(key: string, value: T | null | undefined): Record<string, T> {
  return value === null || value === undefined || value === "" ? {} : { [key]: value };
}
