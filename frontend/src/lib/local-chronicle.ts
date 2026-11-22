/**
 * The local chronicler (Epic 380).
 *
 * The Career Chronicle card asks the model to write the reader's book. When the
 * provider is closed — which it is on this install — the timeline is left with a
 * button that cannot answer. This module writes the same book from the ledger
 * itself: no model, no network, no invented milestone. Every sentence is a
 * function of the events the page already drew.
 *
 * It is not a replacement for the model's prose. It is the floor: the reader can
 * always turn their own rows into chapters, and the model's version is the
 * ceiling when it is available.
 */

import type { TimelineEntry } from "@/lib/api/types";

/** The regions the atlas knows, in the order a book would open them. */
export const CHRONICLE_REGIONS = [
  "match",
  "application",
  "interview",
  "contact",
  "resume_version",
  "note",
] as const;

export interface ChronicleVar {
  [key: string]: string | number;
}

export interface LocalLore {
  key: string;
  vars: ChronicleVar;
}

export interface LocalChapter {
  id: string;
  titleKey: string;
  titleVars: ChronicleVar;
  bodyKey: string;
  bodyVars: ChronicleVar;
  lore: LocalLore[];
  /** The atlas regions this chapter stands in; empty for the opening/closing. */
  regions: string[];
}

export interface LocalChronicle {
  chapters: LocalChapter[];
  epilogueKey: string;
  epilogueVars: ChronicleVar;
  /** Regions no event has opened yet, in book order. */
  frontier: string[];
  empty: boolean;
}

interface Dated {
  event: TimelineEntry;
  at: number;
}

function dated(events: TimelineEntry[]): Dated[] {
  return (events ?? [])
    .map((event) => ({ event, at: new Date(event.at ?? "").getTime() }))
    .filter((row) => Number.isFinite(row.at))
    .sort((a, b) => a.at - b.at);
}

function lore(key: string, rows: Dated[], limit: number): LocalLore[] {
  return rows.slice(-limit).reverse().map((row) => ({
    key,
    vars: { title: row.event.title || row.event.summary || "—" },
  }));
}

/**
 * Compose the book. Chapters with no rows are absent rather than empty: a
 * chapter that says "0 applications" is a chapter the reader did not write.
 */
export function buildLocalChronicle(
  events: TimelineEntry[],
  options: { now?: number } = {},
): LocalChronicle {
  const rows = dated(events);
  if (rows.length === 0) {
    return {
      chapters: [],
      epilogueKey: "timeline.localEmpty",
      epilogueVars: {},
      frontier: [...CHRONICLE_REGIONS],
      empty: true,
    };
  }
  const now = options.now ?? Date.now();
  const first = rows[0];
  const last = rows[rows.length - 1];
  const days = Math.max(1, Math.round((last.at - first.at) / 86_400_000) + 1);
  const byKind = (kind: string) => rows.filter((row) => row.event.kind === kind);
  const charted = new Set(rows.map((row) => row.event.kind));
  const frontier = CHRONICLE_REGIONS.filter((kind) => !charted.has(kind));
  const chapters: LocalChapter[] = [];

  chapters.push({
    id: "opening",
    titleKey: "timeline.localOpeningTitle",
    titleVars: { days },
    bodyKey: "timeline.localOpeningBody",
    bodyVars: {
      first: first.event.at,
      last: last.event.at,
      total: rows.length,
      regions: charted.size,
    },
    lore: [],
    regions: [],
  });

  const applications = byKind("application");
  if (applications.length > 0) {
    chapters.push({
      id: "applications",
      titleKey: "timeline.localApplicationsTitle",
      titleVars: { count: applications.length },
      bodyKey: "timeline.localApplicationsBody",
      bodyVars: {
        count: applications.length,
        first: applications[0].event.at,
        last: applications[applications.length - 1].event.at,
      },
      lore: lore("timeline.localLoreApplication", applications, 3),
      regions: ["application"],
    });
  }

  const interviews = byKind("interview");
  if (interviews.length > 0) {
    chapters.push({
      id: "interviews",
      titleKey: "timeline.localInterviewsTitle",
      titleVars: { count: interviews.length },
      bodyKey: "timeline.localInterviewsBody",
      bodyVars: {
        count: interviews.length,
        last: interviews[interviews.length - 1].event.at,
      },
      lore: lore("timeline.localLoreInterview", interviews, 3),
      regions: ["interview"],
    });
  }

  const contacts = byKind("contact");
  if (contacts.length > 0) {
    chapters.push({
      id: "people",
      titleKey: "timeline.localPeopleTitle",
      titleVars: { count: contacts.length },
      bodyKey: "timeline.localPeopleBody",
      bodyVars: {
        count: contacts.length,
        last: contacts[contacts.length - 1].event.at,
      },
      lore: lore("timeline.localLoreContact", contacts, 3),
      regions: ["contact"],
    });
  }

  const notes = byKind("note");
  const versions = byKind("resume_version");
  if (notes.length + versions.length > 0) {
    const written = [...notes, ...versions].sort((a, b) => a.at - b.at);
    chapters.push({
      id: "record",
      titleKey: "timeline.localRecordTitle",
      titleVars: { count: notes.length + versions.length },
      bodyKey: "timeline.localRecordBody",
      bodyVars: {
        notes: notes.length,
        versions: versions.length,
        last: written[written.length - 1].event.at,
      },
      lore: lore("timeline.localLoreRecord", written, 3),
      regions: ["note", "resume_version"],
    });
  }

  chapters.push({
    id: "now",
    titleKey: "timeline.localNowTitle",
    titleVars: { title: last.event.title || last.event.summary || "—" },
    bodyKey: "timeline.localNowBody",
    bodyVars: {
      days: Math.max(0, Math.round((now - last.at) / 86_400_000)),
      regions: charted.size,
    },
    lore: [],
    regions: [],
  });

  return {
    chapters,
    epilogueKey: "timeline.localEpilogue",
    epilogueVars: { days, total: rows.length },
    frontier,
    empty: false,
  };
}
