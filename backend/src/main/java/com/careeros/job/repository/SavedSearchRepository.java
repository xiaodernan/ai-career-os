package com.careeros.job.repository;

import com.careeros.job.entity.SavedSearch;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * The saved-search reads: one user's named questions, newest first, and the
 * user-scoped find every delete is anchored on.
 */
public interface SavedSearchRepository extends JpaRepository<SavedSearch, UUID> {

    List<SavedSearch> findByUserIdOrderByCreatedAtDesc(UUID userId);

    Optional<SavedSearch> findByIdAndUserId(UUID id, UUID userId);
}
