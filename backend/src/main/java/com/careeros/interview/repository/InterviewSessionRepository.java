package com.careeros.interview.repository;

import com.careeros.interview.entity.InterviewSession;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface InterviewSessionRepository extends JpaRepository<InterviewSession, UUID> {

    Page<InterviewSession> findByUserIdOrderByStartedAtDescIdAsc(UUID userId, Pageable pageable);

    /**
     * One card's rehearsals (57.1), newest first -- the same order the board
     * uses, so the narrowed list reads like the whole list, only shorter.
     */
    Page<InterviewSession> findByUserIdAndApplicationIdOrderByStartedAtDescIdAsc(
            UUID userId, UUID applicationId, Pageable pageable);

    Optional<InterviewSession> findByIdAndUserId(UUID id, UUID userId);

    long countByUserId(UUID userId);

    /** One card's rehearsals (57.2): the packet's fifth row is this number. */
    long countByApplicationIdAndUserId(UUID applicationId, UUID userId);
}
