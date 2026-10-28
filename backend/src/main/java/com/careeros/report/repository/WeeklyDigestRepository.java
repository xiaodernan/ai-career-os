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

    /**
     * The retry clock's queue (21.3): undelivered letters that were actually attempted, oldest
     * week first, bounded by the caller's window. The lower bound is what keeps a dashboard
     * compose out of the queue -- its zero attempts mean "nobody tried", and that route's
     * promise is that composing is not sending -- and the upper bound is the cap past which a
     * letter is left on its row with its error rather than retried forever. The ordering ends
     * in the id because two accounts share a week: without it, the window's last key would not
     * separate them and the same pass could see the same letter twice or miss another.
     */
    List<WeeklyDigest> findByDeliveredAtIsNullAndDeliveryAttemptsGreaterThanAndDeliveryAttemptsLessThanOrderByWeekStartAscIdAsc(
            int above, int below, Pageable pageable);
}
