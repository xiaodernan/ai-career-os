import { sectionMetadata } from "@/lib/i18n/metadata";
import { NotFoundBody } from "@/components/common/not-found-body";

/**
 * The 404 page.
 *
 * The body it renders is a client component, because the body reads the
 * locale table and the locale table is a context -- and because the body
 * is what knows the route did not resolve, which is what the tab's title
 * says. The server cannot read the locale, so it cannot name the page.
 */
export const generateMetadata = sectionMetadata("common.pageNotFound");

export default function NotFound() {
  return <NotFoundBody />;
}
