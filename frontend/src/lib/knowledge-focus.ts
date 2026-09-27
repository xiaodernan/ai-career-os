/**
 * The rule `/knowledge?src=` needs before it asks the backend for anything: the value is a document id,
 * and a blank is the absence of one — `buildUrl` sends any value that is not `undefined`, so an empty
 * `?src=` left as typed would reach Spring's UUID binder as `documentId=` and answer a half-written
 * link with a 400 instead of a list.
 *
 * It lives here rather than in the page because a Next route module may export nothing besides its
 * default and its route config, which `tsc` checks against the generated `.next/types` validator.
 */
export function knowledgeFocus(raw?: string): string | undefined {
  return raw || undefined;
}
