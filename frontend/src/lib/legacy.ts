/**
 * 371: what one search leaves behind for the next one.
 *
 * Brief VI asks for a world with "新的后续环节" — and the honest one is that a search
 * ends and another begins. The ceremony (Epic 212) says what the loop WAS; this module
 * reads the same ledger and says what it LEFT: the material worth reusing, the stages
 * that cost the most, and the one lesson the numbers actually support.
 *
 * Three rules, each naming the facts that fired it, and each silent when its input is
 * absent — an empty ledger gets no legacy rather than an invented one. Nothing here
 * scores the reader and nothing leaves the browser: it is arithmetic over rows the
 * account already owns.
 */

export interface LegacyInput {
  /** Applications by stage, as the board already counts them. */
  stages?: Record<string, number>;
  /** Rehearsals taken, and how many produced a report. */
  rehearsals?: number;
  reportsWritten?: number;
  /** Letters kept. */
  letters?: number;
  /** Notes kept from a rehearsal's advice. */
  notesKept?: number;
  /** Offers that reached the shelf. */
  offers?: number;
}

export interface Legacy {
  /** The material a next search starts from rather than from scratch. */
  reuse: Array<{ id: string; count: number; titleKey: string; bodyKey: string; href: string }>;
  /** The stage that cost the most, and how many applications it took. */
  costliestStage: { id: string; count: number } | null;
  /** One lesson the numbers support, or null when they support none. */
  lesson: { titleKey: string; bodyKey: string } | null;
}

const num = (v: number | undefined): number =>
  typeof v === "number" && Number.isFinite(v) && v > 0 ? Math.floor(v) : 0;

/** The stage a reader loses the most applications at, named by the board's own ids. */
function costliestStage(stages: Record<string, number>): { id: string; count: number } | null {
  const rows = Object.entries(stages)
    .filter(([, count]) => num(count) > 0)
    .map(([id, count]) => ({ id, count: num(count) }))
    .sort((a, b) => b.count - a.count || a.id.localeCompare(b.id));
  return rows[0] ?? null;
}

/**
 * The one lesson the numbers support.
 *
 * Ordered by what the ledger can actually prove, and silent when it proves nothing:
 * a reader who rehearsed far more than they reported has a lesson about finishing,
 * and a reader who kept many notes has one about reading them back. A thin ledger
 * gets no lesson at all rather than a platitude.
 */
function lessonOf(input: LegacyInput): { titleKey: string; bodyKey: string } | null {
  const rehearsals = num(input.rehearsals);
  const reports = num(input.reportsWritten);
  const notes = num(input.notesKept);
  const letters = num(input.letters);

  if (rehearsals >= 3 && reports * 2 < rehearsals) {
    return {
      titleKey: "legacy.lessonUnfinishedTitle",
      bodyKey: "legacy.lessonUnfinishedBody",
    };
  }
  if (notes >= 5 && letters === 0) {
    return { titleKey: "legacy.lessonUnusedTitle", bodyKey: "legacy.lessonUnusedBody" };
  }
  if (letters >= 3) {
    return { titleKey: "legacy.lessonReusedTitle", bodyKey: "legacy.lessonReusedBody" };
  }
  return null;
}

export function legacyOf(input: LegacyInput): Legacy {
  const stages = input.stages ?? {};
  const reports = num(input.reportsWritten);
  const letters = num(input.letters);
  const notes = num(input.notesKept);
  const offers = num(input.offers);

  const reuse = [
    reports > 0
      ? { id: "reports", count: reports, titleKey: "legacy.reuseReportsTitle", bodyKey: "legacy.reuseReportsBody", href: "/interviews" }
      : null,
    letters > 0
      ? { id: "letters", count: letters, titleKey: "legacy.reuseLettersTitle", bodyKey: "legacy.reuseLettersBody", href: "/letters" }
      : null,
    notes > 0
      ? { id: "notes", count: notes, titleKey: "legacy.reuseNotesTitle", bodyKey: "legacy.reuseNotesBody", href: "/knowledge" }
      : null,
    offers > 0
      ? { id: "offers", count: offers, titleKey: "legacy.reuseOffersTitle", bodyKey: "legacy.reuseOffersBody", href: "/offers" }
      : null,
  ].filter((row): row is NonNullable<typeof row> => row !== null);

  return {
    reuse,
    costliestStage: costliestStage(stages),
    lesson: lessonOf(input),
  };
}
