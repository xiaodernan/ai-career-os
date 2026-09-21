package com.careeros.interview.repository;

import com.careeros.interview.entity.InterviewEvaluation;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface InterviewEvaluationRepository extends JpaRepository<InterviewEvaluation, UUID> {

    Optional<InterviewEvaluation> findBySessionId(UUID sessionId);
}
