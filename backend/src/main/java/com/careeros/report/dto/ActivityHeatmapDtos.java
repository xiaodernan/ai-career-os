package com.careeros.report.dto;

import java.util.List;

/** The activity heatmap's wire shapes (Epic 184): one dense day-grid plus the streaks. */
public final class ActivityHeatmapDtos {

  private ActivityHeatmapDtos() {}

  /** One calendar day, present even when nothing happened — the grid needs the zero. */
  public record HeatmapDay(String date, int applications, int interviews, int replies, int aiCalls) {
    public int total() {
      return applications + interviews + replies + aiCalls;
    }
  }

  public record HeatmapStreak(int current, int longest) {}

  public record ActivityHeatmapResponse(
      int days, List<HeatmapDay> grid, HeatmapStreak streak, int grandTotal) {}
}
