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

    Optional<InterviewSession> findByIdAndUserId(UUID id, UUID userId);

    long countByUserId(UUID userId);
}
