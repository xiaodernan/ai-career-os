package com.careeros.interview.repository;

import jakarta.persistence.EntityManager;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Repository;

/**
 * Per-session aggregates for the interview list: how many questions were asked, and the score
 * the report computed. Both live in child tables, so the list could not name a session's length
 * or result without a read of its own — two grouped queries for a whole page, never one per row.
 */
@Repository
public class InterviewDigestRepository {

    /**
     * A session with no turns really does have zero questions, while a session nobody finalised
     * has no score at all — so `overall` stays null instead of reporting an unattempted 0.
     */
    public record Digest(Integer questions, Float overall) {
        /** Nothing was aggregated for this row: report no count rather than a false zero. */
        public static final Digest UNKNOWN = new Digest(null, null);
    }

    private static final String QUESTION_COUNTS = """
            SELECT t.session_id, count(*) FROM interview_turns t
             WHERE t.session_id IN (:ids) AND t.role = 'interviewer'
             GROUP BY t.session_id
            """;

    /**
     * `summary` is jsonb written from a model-produced evaluation, so 'overall' can be absent or
     * non-numeric; casting a string would fail every row of the list, hence the type guard.
     */
    private static final String OVERALL_SCORES = """
            SELECT e.session_id,
                   CASE WHEN jsonb_typeof(e.summary -> 'overall') = 'number'
                        THEN (e.summary ->> 'overall')::real END
              FROM interview_evaluations e
             WHERE e.session_id IN (:ids)
            """;

    private final EntityManager em;

    public InterviewDigestRepository(EntityManager em) {
        this.em = em;
    }

    public Map<UUID, Digest> forSessions(Collection<UUID> sessionIds) {
        Map<UUID, Digest> out = new HashMap<>();
        if (sessionIds == null || sessionIds.isEmpty()) {
            return out;
        }
        Map<UUID, Integer> questions = new HashMap<>();
        for (Object[] row : rows(QUESTION_COUNTS, sessionIds)) {
            questions.put((UUID) row[0], ((Number) row[1]).intValue());
        }
        Map<UUID, Float> scores = new HashMap<>();
        for (Object[] row : rows(OVERALL_SCORES, sessionIds)) {
            if (row[1] != null) {
                scores.put((UUID) row[0], ((Number) row[1]).floatValue());
            }
        }
        for (UUID id : sessionIds) {
            out.put(id, new Digest(questions.getOrDefault(id, 0), scores.get(id)));
        }
        return out;
    }

    @SuppressWarnings("unchecked")
    private List<Object[]> rows(String sql, Collection<UUID> sessionIds) {
        jakarta.persistence.Query query = em.createNativeQuery(sql);
        query.setParameter("ids", sessionIds);
        return (List<Object[]>) query.getResultList();
    }
}
