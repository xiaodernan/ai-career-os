package com.careeros.report.repository;

import jakarta.persistence.EntityManager;
import jakarta.persistence.Query;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Repository;

/**
 * The activity heatmap's four daily counts, read in one round trip (Epic 184).
 *
 * <p>Each arm filters by (user_id, its own clock) — the composite shape V39 indexes —
 * and the union groups once, so the endpoint never fans out per day or per table. The
 * arms' clocks are deliberately their tables' own: a recruiter reply is dated by when
 * it was received, not when the row landed; an interview by when it started, not when
 * it was finally scored; an application by when the reader filed it.
 */
@Repository
public class ActivityHeatmapRepository {

  private final EntityManager em;

  public ActivityHeatmapRepository(EntityManager em) {
    this.em = em;
  }

  public record DayCount(LocalDate day, String kind, long count) {}

  /** Sparse (day, kind, count) rows for every day in the window that has any activity. */
  public List<DayCount> dailyCounts(UUID userId, LocalDate since) {
    Query query = em.createNativeQuery(
        """
        SELECT day, kind, COUNT(*) FROM (
          SELECT CAST(created_at AT TIME ZONE 'UTC' AS date) AS day, 'application' AS kind
            FROM applications WHERE user_id = :userId AND created_at >= :since
          UNION ALL
          SELECT CAST(started_at AT TIME ZONE 'UTC' AS date), 'interview'
            FROM interview_sessions WHERE user_id = :userId AND started_at >= :since
          UNION ALL
          SELECT CAST(received_at AT TIME ZONE 'UTC' AS date), 'reply'
            FROM inbound_mails WHERE user_id = :userId AND received_at >= :since
          UNION ALL
          SELECT CAST(created_at AT TIME ZONE 'UTC' AS date), 'ai_call'
            FROM ai_usage_events WHERE user_id = :userId AND created_at >= :since
        ) s GROUP BY day, kind ORDER BY day
        """);
    query.setParameter("userId", userId);
    query.setParameter("since", java.sql.Timestamp.valueOf(since.atStartOfDay()));
    @SuppressWarnings("unchecked")
    List<Object[]> rows = query.getResultList();
    return rows.stream()
        .map(row -> new DayCount(
            ((java.sql.Date) row[0]).toLocalDate(),
            (String) row[1],
            ((Number) row[2]).longValue()))
        .toList();
  }
}
