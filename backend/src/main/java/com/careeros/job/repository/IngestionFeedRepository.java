package com.careeros.job.repository;

import com.careeros.job.entity.IngestionFeed;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IngestionFeedRepository extends JpaRepository<IngestionFeed, UUID> {

    List<IngestionFeed> findByUserIdOrderByCreatedAtDesc(UUID userId);

    Optional<IngestionFeed> findByIdAndUserId(UUID id, UUID userId);

    /** The nightly sweep's work list: every subscriber's enabled feeds, oldest first. */
    List<IngestionFeed> findByEnabledTrueOrderByCreatedAtAsc();

    long countByUserId(UUID userId);
}
