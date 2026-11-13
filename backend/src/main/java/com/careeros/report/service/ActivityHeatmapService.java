package com.careeros.report.service;

import com.careeros.report.dto.ActivityHeatmapDtos.ActivityHeatmapResponse;
import com.careeros.report.dto.ActivityHeatmapDtos.HeatmapDay;
import com.careeros.report.dto.ActivityHeatmapDtos.HeatmapStreak;
import com.careeros.report.repository.ActivityHeatmapRepository;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;

/**
 * GET /api/v1/reports/activity-heatmap — the reader's job-search pace as one dense
 * day-grid (Epic 184).
 *
 * <p>The SQL answers sparsely (only days with activity); this service fills the
 * window densely, because a grid that skips quiet days lies by omission — a week of
 * silence between two busy ones must read as silence. The streaks are the reason the
 * grid exists at all: momentum is the thing a job search leaks fastest, and a reader
 * who sees "current streak: 6 days" keeps the loop moving. The longest streak walks
 * the dense grid once; the current streak walks backward from the window's end but
 * forgives today — the reader has not yet had the chance to act on the day they are
 * in, so a chain ending yesterday still counts.
 */
@Service
public class ActivityHeatmapService {

  static final int MIN_DAYS = 14;
  static final int MAX_DAYS = 366;

  private final ActivityHeatmapRepository repository;

  public ActivityHeatmapService(ActivityHeatmapRepository repository) {
    this.repository = repository;
  }

  public ActivityHeatmapResponse build(UUID userId, int days) {
    int window = Math.clamp(days, MIN_DAYS, MAX_DAYS);
    LocalDate today = LocalDate.now(ZoneOffset.UTC);
    LocalDate since = today.minusDays(window - 1L);

    Map<LocalDate, long[]> byDay = new HashMap<>();
    for (ActivityHeatmapRepository.DayCount row : repository.dailyCounts(userId, since)) {
      byDay.computeIfAbsent(row.day(), k -> new long[4])[
          switch (row.kind()) {
            case "application" -> 0;
            case "interview" -> 1;
            case "reply" -> 2;
            case "ai_call" -> 3;
            default -> throw new IllegalStateException("unknown heatmap kind " + row.kind());
          }] += row.count();
    }

    var grid = new java.util.ArrayList<HeatmapDay>(window);
    int grandTotal = 0;
    for (LocalDate day = since; !day.isAfter(today); day = day.plusDays(1)) {
      long[] counts = byDay.getOrDefault(day, new long[4]);
      int dayTotal = (int) (counts[0] + counts[1] + counts[2] + counts[3]);
      grandTotal += dayTotal;
      grid.add(new HeatmapDay(day.toString(), (int) counts[0], (int) counts[1],
          (int) counts[2], (int) counts[3]));
    }
    return new ActivityHeatmapResponse(window, grid,
        new HeatmapStreak(currentStreak(grid), longestStreak(grid)), grandTotal);
  }

  /** Consecutive active days walking backward from the end, forgiving the last day. */
  static int currentStreak(java.util.List<HeatmapDay> grid) {
    int streak = 0;
    for (int i = grid.size() - 1; i >= 0; i--) {
      if (grid.get(i).total() == 0) {
        if (i == grid.size() - 1) {
          continue; // today is not over yet; an inactive today does not break the chain
        }
        break;
      }
      streak++;
    }
    return streak;
  }

  /** The longest run of consecutive active days anywhere in the grid. */
  static int longestStreak(java.util.List<HeatmapDay> grid) {
    int longest = 0;
    int run = 0;
    for (HeatmapDay day : grid) {
      run = day.total() > 0 ? run + 1 : 0;
      longest = Math.max(longest, run);
    }
    return longest;
  }
}
