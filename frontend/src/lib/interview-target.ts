/**
 * 56.4: a rehearsal may belong to a tracker card (`SessionItem.applicationId`, 56.1). Three
 * screens point back at it -- the list row, the session header and the finished report -- and
 * they must agree on both the route and the fact that a free rehearsal has none.
 */
export function interviewApplicationHref(
  applicationId: string | null | undefined
): string | null {
  return applicationId ? `/applications?application=${applicationId}` : null;
}