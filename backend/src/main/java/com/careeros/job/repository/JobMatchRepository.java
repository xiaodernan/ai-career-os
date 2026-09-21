package com.careeros.job.repository;

import com.careeros.job.entity.JobMatch;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface JobMatchRepository extends JpaRepository<JobMatch, UUID> {

    Optional<JobMatch> findFirstByUserIdAndJobIdOrderByCreatedAtDesc(UUID userId, UUID jobId);

    List<JobMatch> findByUserIdAndJobIdIn(UUID userId, List<UUID> jobIds);

    Optional<JobMatch> findFirstByUserIdOrderByOverallDesc(UUID userId);
}
