package com.careeros.job.repository;

import com.careeros.job.entity.IngestionFeed;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface IngestionFeedRepository extends JpaRepository<IngestionFeed, UUID> {

    List<IngestionFeed> findByUserIdOrderByCreatedAtDesc(UUID userId);

    Optional<IngestionFeed> findByIdAndUserId(UUID id, UUID userId);

    /** The nightly sweep's work list: every subscriber's enabled feeds, oldest first. */
    List<IngestionFeed> findByEnabledTrueOrderByCreatedAtAsc();

    long countByUserId(UUID userId);

    /**
     * Every account that subscribes to a feed -- the signal mail's second half of the audience
     * (22.1). A night that failed or proposed postings is a signal for its owner even when the
     * account has no application on the board.
     */
    @Query("SELECT DISTINCT f.userId FROM IngestionFeed f")
    List<UUID> distinctUserIds();
}
