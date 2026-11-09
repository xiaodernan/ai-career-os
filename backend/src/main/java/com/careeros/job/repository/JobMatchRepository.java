package com.careeros.job.repository;

import com.careeros.job.entity.JobMatch;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface JobMatchRepository extends JpaRepository<JobMatch, UUID> {

    Optional<JobMatch> findByIdAndUserId(UUID id, UUID userId);

    Optional<JobMatch> findFirstByUserIdAndJobIdOrderByCreatedAtDesc(UUID userId, UUID jobId);

    List<JobMatch> findByUserIdAndJobIdIn(UUID userId, List<UUID> jobIds);

    Optional<JobMatch> findFirstByUserIdOrderByOverallDesc(UUID userId);

    /**
     * Epic 81: the caller's matches, newest first, ties broken by id, paged by the caller's cap.
     */
    Page<JobMatch> findByUserIdOrderByCreatedAtDescIdAsc(UUID userId, Pageable pageable);
}
