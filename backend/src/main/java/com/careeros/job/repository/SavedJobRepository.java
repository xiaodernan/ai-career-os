package com.careeros.job.repository;

import com.careeros.job.entity.SavedJob;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SavedJobRepository extends JpaRepository<SavedJob, SavedJob.SavedJobId> {

    List<SavedJob> findByUserIdOrderByCreatedAtDesc(UUID userId);

    boolean existsByUserIdAndJobId(UUID userId, UUID jobId);
}
