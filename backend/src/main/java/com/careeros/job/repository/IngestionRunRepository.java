package com.careeros.job.repository;

import com.careeros.job.entity.IngestionRun;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IngestionRunRepository extends JpaRepository<IngestionRun, UUID> {

    /**
     * The run history, newest first. `id` is the tiebreak because `started_at` is not unique:
     * a sweep that pulls two feeds in the same millisecond otherwise leaves their order to the
     * plan, and the same page answers different rows on two visits.
     */
    Page<IngestionRun> findByUserIdOrderByStartedAtDescIdDesc(UUID userId, Pageable pageable);

    Optional<IngestionRun> findFirstByFeedIdOrderByStartedAtDesc(UUID feedId);

    Optional<IngestionRun> findByIdAndUserId(UUID id, UUID userId);
}
