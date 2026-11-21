/**
 * 369: the one direction the world is pointing, read off the reader's own ledger.
 *
 * Brief VI asks for a world that feels endless AND for enough guidance that a reader never
 * feels lost. Those are the same requirement seen from two sides: a world you can always
 * find your way in. The tour (Epic 235) walks nine fixed rooms, which teaches the map but
 * cannot say where THIS reader is. This module reads what the reader has actually done and
 * names the single next thing worth doing, with the reason it chose that one.
 *
 * The rules are ordered by what costs the reader most to leave undone, not by what is
 * easiest to measure. An interview to prepare for outranks a resume to polish, because a
 * missed rehearsal is a door that closes while a resume edit is not. Every rule names the
 * facts that fired it; a rule that cannot see its input stays silent, and when nothing fires
 * the answer is the honest one -- the ledger says nothing is waiting, which is not the same
 * as there being nothing to do.
 *
 * Pure and deterministic: the same ledger always answers the same direction, so it can be
 * tested without a browser and never surprises a reader by changing its mind on reload.
 */

export interface FrontierInput {
  /** Rehearsals that started and have not been finished -- the ones a reader walked away from. */
  openRehearsals?: number;
  /** Applications sitting in a stage where the next move is the reader's, not the employer's. */
  applicationsAwaitingReader?: number;
  /** Applications whose stage says the employer answered and nobody has replied yet. */
  repliesToSend?: number;
  /** Saved searches with new matches nobody has looked at. */
  unreadMatches?: number;
  /** Knowledge notes kept from a rehearsal that have never been read back. */
  unreadNotes?: number;
}

export interface Frontier {
  id: string;
  titleKey: string;
  bodyKey: string;
  vars: Record<string, string | number>;
  href: string;
  ctaKey: string;
}

const num = (v: number | undefined): number =>
  typeof v === "number" && Number.isFinite(v) && v > 0 ? Math.floor(v) : 0;

/**
 * The rules, most expensive to leave undone first.
 *
 * Each is a function of the input rather than a sentence: a rule that fires names the number
 * that fired it, and a number that is zero leaves the rule silent. That is the whole
 * discipline -- silence reads as "nothing measured", never as "all is well".
 */
export function nextFrontier(input: FrontierInput): Frontier | null {
  const openRehearsals = num(input.openRehearsals);
  const repliesToSend = num(input.repliesToSend);
  const applicationsAwaitingReader = num(input.applicationsAwaitingReader);
  const unreadMatches = num(input.unreadMatches);
  const unreadNotes = num(input.unreadNotes);

  if (openRehearsals > 0) {
    return {
      id: "finish-rehearsal",
      titleKey: "frontier.finishRehearsalTitle",
      bodyKey: "frontier.finishRehearsalBody",
      vars: { count: openRehearsals },
      href: "/interviews",
      ctaKey: "frontier.finishRehearsalCta",
    };
  }
  if (repliesToSend > 0) {
    return {
      id: "answer-reply",
      titleKey: "frontier.answerReplyTitle",
      bodyKey: "frontier.answerReplyBody",
      vars: { count: repliesToSend },
      href: "/replies",
      ctaKey: "frontier.answerReplyCta",
    };
  }
  if (applicationsAwaitingReader > 0) {
    return {
      id: "move-application",
      titleKey: "frontier.moveApplicationTitle",
      bodyKey: "frontier.moveApplicationBody",
      vars: { count: applicationsAwaitingReader },
      href: "/applications",
      ctaKey: "frontier.moveApplicationCta",
    };
  }
  if (unreadMatches > 0) {
    return {
      id: "read-matches",
      titleKey: "frontier.readMatchesTitle",
      bodyKey: "frontier.readMatchesBody",
      vars: { count: unreadMatches },
      href: "/jobs",
      ctaKey: "frontier.readMatchesCta",
    };
  }
  if (unreadNotes > 0) {
    return {
      id: "read-notes",
      titleKey: "frontier.readNotesTitle",
      bodyKey: "frontier.readNotesBody",
      vars: { count: unreadNotes },
      href: "/knowledge",
      ctaKey: "frontier.readNotesCta",
    };
  }
  return null;
}
