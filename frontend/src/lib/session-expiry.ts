/**
 * What the app says when a session dies mid-task.
 *
 * The refresh-failed 401 path takes the browser to /login itself -- a full navigation, so
 * the `ApiError` thrown beside it fires a toast the navigation kills. The reason has to
 * travel in the bounce URL instead: `client.ts` appends `reason=<SESSION_EXPIRED_REASON>`,
 * the login page reads the parameter back through `sessionNotice`, and the form renders
 * the sentence in a banner. Both spellings live here and nowhere else; the gate pins the
 * writer importing the reason and the reader rejecting every other value.
 */

/** The `reason` value the refresh-failed bounce puts on the /login URL. */
export const SESSION_EXPIRED_REASON = "expired";

/** What the login screen announces when it finds that reason. */
export const SESSION_EXPIRED_MESSAGE = "Your session has expired — sign in again.";

/** The sentence for a `reason` search parameter, or `undefined` for anything else. */
export function sessionNotice(reason: unknown): string | undefined {
  return reason === SESSION_EXPIRED_REASON ? SESSION_EXPIRED_MESSAGE : undefined;
}
