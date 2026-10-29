package com.careeros.job.repository;

import com.careeros.job.entity.SavedSearch;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

/**
 * The saved-search reads: one user's named questions, newest first, the
 * user-scoped find every delete is anchored on, and the distinct owners the
 * morning sweep asks after (29.2).
 */
public interface SavedSearchRepository extends JpaRepository<SavedSearch, UUID> {

    List<SavedSearch> findByUserIdOrderByCreatedAtDesc(UUID userId);

    Optional<SavedSearch> findByIdAndUserId(UUID id, UUID userId);

    /**
     * Every account keeping at least one saved search. The letter's audience
     * used to be applications and feeds, and an account that only browses with
     * saved questions is in neither -- its morning would have been silent even
     * though the search had news.
     */
    @Query("SELECT DISTINCT s.userId FROM SavedSearch s")
    List<UUID> distinctUserIds();
}
