package com.careeros.report.repository;

import com.careeros.common.Times;
import com.careeros.report.dto.DashboardDtos.RecommendedJob;
import jakarta.persistence.EntityManager;
import jakarta.persistence.Query;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Repository;

/** Reads for the dashboard: recommended open jobs with the viewer's latest match attached. */
@Repository
public class DashboardRepository {

    private final EntityManager em;

    public DashboardRepository(EntityManager em) {
        this.em = em;
    }

    /**
     * Open jobs the user has not applied to, newest first, with their latest match score attached.
     * Single query (company join + lateral match) so there is no per-row N+1.
     */
    public List<RecommendedJob> recommendedJobs(UUID userId, int limit) {
        String sql = """
                SELECT j.id, j.title, c.name, j.location, j.remote_type, j.posted_at, m.overall, m.id
                  FROM jobs j
                  JOIN companies c ON c.id = j.company_id
                  LEFT JOIN LATERAL (
                        SELECT jm.overall, jm.id FROM job_matches jm
                         WHERE jm.job_id = j.id AND jm.user_id = :userId
                         ORDER BY jm.created_at DESC LIMIT 1) m ON TRUE
                 WHERE j.status = 'open'
                   AND NOT EXISTS (SELECT 1 FROM applications a
                                    WHERE a.user_id = :userId AND a.job_id = j.id)
                 ORDER BY m.overall DESC NULLS LAST, j.posted_at DESC
                 LIMIT :limit
                """;
        Query query = em.createNativeQuery(sql);
        query.setParameter("userId", userId);
        query.setParameter("limit", limit);
        return ((List<Object[]>) query.getResultList()).stream()
                .map(row -> new RecommendedJob(
                        (UUID) row[0], (String) row[1], (String) row[2], (String) row[3],
                        (String) row[4], Times.offset(row[5]),
                        row[6] == null ? null : ((Number) row[6]).floatValue(),
                        (UUID) row[7]))
                .toList();
    }

    /**
     * Mean of the *newest* match per scored job. Re-running a match on the same job re-scores the
     * same role, so counting every run would weight the jobs the user re-checked most rather than
     * the jobs themselves. Null when nothing is scored yet: "no average" and "average of zero"
     * are different claims, and the card on the other end hides on null.
     */
    public Float averageMatch(UUID userId) {
        String sql = """
                SELECT avg(latest.overall) FROM (
                      SELECT DISTINCT ON (jm.job_id) jm.job_id, jm.overall
                        FROM job_matches jm
                       WHERE jm.user_id = :userId
                       ORDER BY jm.job_id, jm.created_at DESC, jm.id DESC
                ) latest
                """;
        Query query = em.createNativeQuery(sql);
        query.setParameter("userId", userId);
        Object single = query.getSingleResult();
        return single == null ? null : ((Number) single).floatValue();
    }

    /**
     * Open applications waiting on the user: nothing logged for {@code staleDays}, or a reminder
     * date that has arrived. `offer` and `rejected` are excluded because the stage taxonomy the
     * frontend freezes (`lib/pipeline.ts`) treats those as closed out — a decision already made is
     * not an outstanding item, and counting it would make the number grow as the user finishes work.
     */
    public long needsAttention(UUID userId, int staleDays) {
        String sql = """
                SELECT count(*) FROM applications a
                 WHERE a.user_id = :userId
                   AND a.status NOT IN ('offer', 'rejected')
                   AND (a.updated_at < now() - make_interval(days => :staleDays)
                        OR (a.reminder_at IS NOT NULL AND a.reminder_at <= now()))
                """;
        Query query = em.createNativeQuery(sql);
        query.setParameter("userId", userId);
        query.setParameter("staleDays", staleDays);
        return ((Number) query.getSingleResult()).longValue();
    }
}
