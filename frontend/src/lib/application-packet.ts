import type { Application } from "@/lib/api/types";

/** The three pipeline artifacts an application can carry, in the order the dialog shows them. */
export const PACKET_LINKS = ["resume", "jd", "match"] as const;
export type PacketLink = (typeof PACKET_LINKS)[number];

export interface PacketCompleteness {
  linked: number;
  total: number;
  missing: PacketLink[];
}

/**
 * How many of the three links the pipeline can attach are on this application.
 *
 * The board reads the same three ids the packet route resolves; it cannot know whether a linked
 * row is still readable without spending a request per card, so the badge speaks only about the
 * columns. "2/3" means one artifact was never attached, not that one is broken.
 */
export function packetCompleteness(app: Application): PacketCompleteness {
  const present: Record<PacketLink, boolean> = {
    resume: Boolean(app.resumeVersionId),
    jd: Boolean(app.jdId),
    match: Boolean(app.matchId),
  };
  const missing = PACKET_LINKS.filter((link) => !present[link]);
  return { linked: PACKET_LINKS.length - missing.length, total: PACKET_LINKS.length, missing };
}
