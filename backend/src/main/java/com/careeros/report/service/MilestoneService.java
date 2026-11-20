package com.careeros.report.service;

import com.careeros.application.repository.ApplicationLetterRepository;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.interview.repository.InterviewSessionRepository;
import com.careeros.job.repository.JobMatchRepository;
import com.careeros.offer.repository.OfferShelfRepository;
import com.careeros.report.dto.MilestoneDtos.Milestone;
import com.careeros.report.dto.MilestoneDtos.MilestoneCounters;
import com.careeros.report.dto.MilestoneDtos.MilestonesResponse;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The milestone shelf (Epic 273): the reader's progress rendered as a badge strip.
 *
 * Everything here is DERIVED — no milestone table, no earned-rows to migrate, no
 * backfill: a milestone is a threshold over counters the platform already owns
 * (applications filed, rehearsals completed, offers received, letters kept, matches
 * computed, the pace streak). The reader cannot lose a badge by re-running the
 * query, and a new counter the platform gains can become a new badge without a
 * schema change. The keys travel to the frontend, whose locale tables carry the
 * words — the two-language rule decided at the DTO.
 */
@Service
public class MilestoneService {

  private final ApplicationRepository applications;
  private final InterviewSessionRepository interviews;
  private final JobMatchRepository matches;
  private final ApplicationLetterRepository letters;
  private final OfferShelfRepository shelf;
  private final ActivityHeatmapService heatmap;

  public MilestoneService(ApplicationRepository applications,
      InterviewSessionRepository interviews, JobMatchRepository matches,
      ApplicationLetterRepository letters, OfferShelfRepository shelf,
      ActivityHeatmapService heatmap) {
    this.applications = applications;
    this.interviews = interviews;
    this.matches = matches;
    this.letters = letters;
    this.shelf = shelf;
    this.heatmap = heatmap;
  }

  /** key → [target, which counter]. A milestone is done when its counter ≥ its target. */
  private record Step(int target, int counter) {}

  private static final Map<String, Step> STEPS = new LinkedHashMap<>() {
    {
      put("first_step", new Step(1, 0));
      put("ten_steps", new Step(10, 0));
      put("fifty_steps", new Step(50, 0));
      put("grounded", new Step(1, 4));
      put("first_rehearsal", new Step(1, 1));
      put("five_rehearsals", new Step(5, 1));
      put("letter_wright", new Step(3, 3));
      put("first_offer", new Step(1, 2));
      put("shelf_full", new Step(3, 6));
      put("streak_week", new Step(7, 5));
    }
  };

  @Transactional(readOnly = true)
  public MilestonesResponse build(UUID userId) {
    long applicationsCount = applications.countByUserId(userId);
    long rehearsalsCount = interviews.countByUserIdAndStatus(userId, "completed");
    long offersCount = applications.countByUserIdAndStatus(userId, "offer");
    long lettersKept = letters.countByUserId(userId);
    long matchesCount = matches.countByUserId(userId);
    int offersOnShelf = shelf.shelfOrder(userId).size();
    int streak = heatmap.build(userId, 28).streak().current();

    MilestoneCounters snapshot = new MilestoneCounters(
        applicationsCount, rehearsalsCount, offersCount, lettersKept, matchesCount, streak,
        offersOnShelf);

    List<Milestone> milestones = new ArrayList<>();
    for (Map.Entry<String, Step> step : STEPS.entrySet()) {
      String key = step.getKey();
      Step spec = step.getValue();
      long value = counterValue(key, snapshot);
      boolean done = value >= spec.target();
      milestones.add(new Milestone(key, done,
          done ? null : (int) Math.min(value, spec.target()), spec.target()));
    }
    return new MilestonesResponse(milestones, snapshot);
  }

  private static long counterValue(String key, MilestoneCounters c) {
    return switch (key) {
      case "first_step", "ten_steps", "fifty_steps" -> c.applications();
      case "grounded" -> c.matches();
      case "first_rehearsal", "five_rehearsals" -> c.interviewsCompleted();
      case "letter_wright" -> c.letters();
      case "first_offer" -> c.offers();
      case "shelf_full" -> c.offersOnShelf();
      case "streak_week" -> c.currentStreak();
      default -> 0;
    };
  }
}
