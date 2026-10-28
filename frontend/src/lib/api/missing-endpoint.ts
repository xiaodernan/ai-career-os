import { translate } from "@/lib/i18n/locale-context";

/**
 * What a 404 from a route this app calls actually means.
 *
 * Every message that used to live at the call sites said the endpoint "isn't live on the
 * backend yet" or "isn't served yet". Every route the app calls is served, so the sentence
 * was false as a statement about the product, and it left a user staring at a small version
 * mismatch with nothing to do about it: the frontend and the API are different builds. The
 * path is named so the mismatch is diagnosable from a screenshot or a support thread.
 *
 * The sentence is the reader's, read through `translate` rather than a hook: the same
 * function answers a render (a card's description) and an event handler (a failure toast),
 * and only the first has a provider above it. The key names the path as a hole so the
 * route sits in the reader's own word order.
 */
export function missingEndpointMessage(path?: string): string {
  const key = path ? "common.missingEndpointRoute" : "common.missingEndpoint";
  return translate(key, path ? { route: path } : undefined) ?? key;
}
