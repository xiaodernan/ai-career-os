import { sectionMetadata } from "@/lib/i18n/metadata";
import AdminPage from "./admin-page";

/**
 * /admin — the operator's ledger (Epic 250).
 *
 * Public route (no token); the passphrase is a single word this install's operator
 * already chose. Counts only — no user, no name, no content reaches this surface.
 */
export const generateMetadata = sectionMetadata("admin.title");

export default function Admin() {
  return <AdminPage />;
}
