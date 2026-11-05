package com.careeros.interview.repository;

import com.careeros.interview.entity.InterviewEvaluation;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface InterviewEvaluationRepository extends JpaRepository<InterviewEvaluation, UUID> {

    Optional<InterviewEvaluation> findBySessionId(UUID sessionId);

    /**
     * Every grade earned on one card (59.2). The session is the join: a session that never
     * finished has no evaluation row, so this returns the graded rehearsals and nothing else.
     * The caller is named twice on purpose -- on the session and on the evaluation -- so a
     * rehearsal of somebody else's card cannot lend its score to this one.
     */
    @Query("""
            SELECT e FROM InterviewEvaluation e, InterviewSession s
             WHERE e.sessionId = s.id
               AND s.userId = :userId
               AND e.userId = :userId
               AND s.applicationId = :applicationId
            """)
    List<InterviewEvaluation> findForApplication(UUID userId, UUID applicationId);
}
