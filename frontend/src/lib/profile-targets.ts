/**
 * The settings profile editor's two target lists, as arithmetic rather than as a screen.
 *
 * Both profile records -- `UpdateProfileRequest` and `UpdateMeRequest`, whichever PATCH the
 * two hooks reach -- carry the same pair of guards on these lists: `@Size(max = 20)` on the
 * list and `@Size(max = 80)`/`@Size(max = 120)` on each entry. Nothing on the screen enforced
 * either, so one over-long role or a 21st comma-separated entry went out and came back as the
 * generic "Request validation failed" 400 whose per-field details nobody opens (#201). The
 * splitter lives here too, so the guard judges exactly the list the payload sends.
 */

import type { TextIssue } from "@/lib/i18n/issue";

export const TARGET_ROLES_MAX_COUNT = 20;
export const TARGET_ROLES_MAX_ITEM = 80;
export const TARGET_LOCATIONS_MAX_COUNT = 20;
export const TARGET_LOCATIONS_MAX_ITEM = 120;

/** `"a, b, c"` -> `["a","b","c"]`, trimmed, blanks dropped -- the entries the guards judge. */
export function splitList(raw: string): string[] {
  return raw.split(",").map((part) => part.trim()).filter(Boolean);
}

/** What to show under the target-roles field, or `undefined` when the list lands in bounds. */
export function targetRolesIssue(items: string[]): TextIssue | undefined {
  if (items.length > TARGET_ROLES_MAX_COUNT) {
    return { key: "profile.issues.tooManyRoles", params: { max: TARGET_ROLES_MAX_COUNT } };
  }
  if (items.some((item) => item.length > TARGET_ROLES_MAX_ITEM)) {
    return { key: "profile.issues.roleTooLong", params: { max: TARGET_ROLES_MAX_ITEM } };
  }
  return undefined;
}

/** What to show under the target-locations field, or `undefined` when the list lands in bounds. */
export function targetLocationsIssue(items: string[]): TextIssue | undefined {
  if (items.length > TARGET_LOCATIONS_MAX_COUNT) {
    return { key: "profile.issues.tooManyLocations", params: { max: TARGET_LOCATIONS_MAX_COUNT } };
  }
  if (items.some((item) => item.length > TARGET_LOCATIONS_MAX_ITEM)) {
    return { key: "profile.issues.locationTooLong", params: { max: TARGET_LOCATIONS_MAX_ITEM } };
  }
  return undefined;
}
