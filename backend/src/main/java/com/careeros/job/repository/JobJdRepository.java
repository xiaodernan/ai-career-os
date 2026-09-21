package com.careeros.job.repository;

import com.careeros.job.entity.JobJd;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface JobJdRepository extends JpaRepository<JobJd, UUID> {

    Optional<JobJd> findByIdAndUserId(UUID id, UUID userId);

    List<JobJd> findByJobIdAndUserId(UUID jobId, UUID userId);

    Optional<JobJd> findFirstByJobIdAndUserIdOrderByCreatedAtDesc(UUID jobId, UUID userId);
}
