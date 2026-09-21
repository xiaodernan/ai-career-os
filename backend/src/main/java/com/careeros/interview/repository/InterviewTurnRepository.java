package com.careeros.interview.repository;

import com.careeros.interview.entity.InterviewTurn;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface InterviewTurnRepository extends JpaRepository<InterviewTurn, UUID> {

    List<InterviewTurn> findBySessionIdOrderBySeqAsc(UUID sessionId);

    Optional<InterviewTurn> findFirstBySessionIdOrderBySeqDesc(UUID sessionId);
}
