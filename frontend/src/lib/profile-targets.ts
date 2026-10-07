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

export const TARGET_ROLES_MAX_COUNT = 20;
export const TARGET_ROLES_MAX_ITEM = 80;
export const TARGET_LOCATIONS_MAX_COUNT = 20;
export const TARGET_LOCATIONS_MAX_ITEM = 120;

/** `"a, b, c"` -> `["a","b","c"]`, trimmed, blanks dropped -- the entries the guards judge. */
export function splitList(raw: string): string[] {
  return raw.split(",").map((part) => part.trim()).filter(Boolean);
}

/** What to show under the target-roles field, or `undefined` when the list lands in bounds. */
export function targetRolesIssue(items: string[]): string | undefined {
  if (items.length > TARGET_ROLES_MAX_COUNT) {
    return `Use at most ${TARGET_ROLES_MAX_COUNT} target roles`;
  }
  if (items.some((item) => item.length > TARGET_ROLES_MAX_ITEM)) {
    return `Each role can be at most ${TARGET_ROLES_MAX_ITEM} characters`;
  }
  return undefined;
}

/** What to show under the target-locations field, or `undefined` when the list lands in bounds. */
export function targetLocationsIssue(items: string[]): string | undefined {
  if (items.length > TARGET_LOCATIONS_MAX_COUNT) {
    return `Use at most ${TARGET_LOCATIONS_MAX_COUNT} target locations`;
  }
  if (items.some((item) => item.length > TARGET_LOCATIONS_MAX_ITEM)) {
    return `Each location can be at most ${TARGET_LOCATIONS_MAX_ITEM} characters`;
  }
  return undefined;
}
