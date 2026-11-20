package com.careeros.report.dto;

import java.util.List;

/**
 * The milestone shelf's wire shapes (Epic 273).
 *
 * The backend answers KEYS and NUMBERS, never sentences: the milestones' words live
 * in the frontend's two locale tables, because a badge earned is rendered in the
 * reader's language and a sentence stored server-side can only be one of the two.
 */
public final class MilestoneDtos {

  private MilestoneDtos() {}

  /** One milestone: done rows carry no progress; working rows carry progress/target. */
  public record Milestone(String key, boolean done, Integer progress, Integer target) {}

  /** The counts the milestones derive from — real numbers, so the shelf stays honest. */
  public record MilestoneCounters(
      long applications,
      long interviewsCompleted,
      long offers,
      long letters,
      long matches,
      int currentStreak,
      int offersOnShelf) {}

  public record MilestonesResponse(List<Milestone> milestones, MilestoneCounters counters) {}
}
