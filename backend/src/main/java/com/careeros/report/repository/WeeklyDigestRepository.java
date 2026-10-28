package com.careeros.report.repository;

import com.careeros.report.entity.WeeklyDigest;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface WeeklyDigestRepository extends JpaRepository<WeeklyDigest, UUID> {

    /**
     * A user's letters, newest week first. `week_start` is unique per user, but the ordering
     * still ends in the id so the window is total for any reader of the derived query rather
     * than only for the one that remembers the unique key.
     */
    List<WeeklyDigest> findByUserIdOrderByWeekStartDescIdDesc(UUID userId, Pageable pageable);

    Optional<WeeklyDigest> findByUserIdAndWeekStart(UUID userId, LocalDate weekStart);
}
