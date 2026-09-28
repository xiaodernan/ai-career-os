/**
 * What a 404 from a route this app calls actually means.
 *
 * Every message that used to live at the call sites said the endpoint "isn't live on the
 * backend yet" or "isn't served yet". Every route the app calls is served, so the sentence
 * was false as a statement about the product, and it left a user staring at a small version
 * mismatch with nothing to do about it: the frontend and the API are different builds. The
 * path is named so the mismatch is diagnosable from a screenshot or a support thread.
 */
export function missingEndpointMessage(path?: string): string {
  const route = path ? `${path} answered 404` : "A route this screen needs answered 404";
  return `${route}, so this frontend and the backend it is talking to are different versions. Nothing is shown in place of the real data.`;
}
