import { absoluteMetadata } from "@/lib/i18n/metadata";
import TourPage from "./tour-page";

/**
 * /tour — the ten-minute start (Epic 244).
 *
 * The public front door for the reader who wants to know what walking
 * through the door means before they register. Eight beats, in order,
 * each naming the real screen it opens. Bilingual by the same table the
 * signed-in app reads, printable, and it never asks for a login.
 */
export const generateMetadata = absoluteMetadata("tour.pageTitle", "tour.description");

export default function Tour() {
  return <TourPage />;
}
