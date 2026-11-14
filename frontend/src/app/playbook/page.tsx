import { absoluteMetadata } from "@/lib/i18n/metadata";
import PlaybookPage from "./playbook-page";

/**
 * The playbook (Epic 214): the reader's manual, in-app and printable.
 *
 * A public page — the product is only as legible as its front door allows it
 * to be — carrying the full loop, room by room, in both languages. Every
 * sentence that ships is bilingual in the same table the signed-in app reads.
 */
export const generateMetadata = absoluteMetadata(
  "playbook.title",
  "playbook.description"
);

export default function Playbook() {
  return <PlaybookPage />;
}
